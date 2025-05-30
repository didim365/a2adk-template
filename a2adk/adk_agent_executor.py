import logging
from collections.abc import AsyncGenerator
from typing import Any, AsyncIterable
from pydantic import ConfigDict

from google.adk import Runner
from google.adk.agents import RunConfig
from google.adk.artifacts import InMemoryArtifactService, BaseArtifactService
from google.adk.events import Event
from google.adk.memory import InMemoryMemoryService, BaseMemoryService
from google.adk.sessions import InMemorySessionService, BaseSessionService
from google.adk.tools import ToolContext
from google.adk.tools.load_memory_tool import load_memory_tool, LoadMemoryTool
from google.adk.tools.preload_memory_tool import preload_memory_tool, PreloadMemoryTool
from google.genai import types

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    Artifact,
    Part,
    TaskState,
    TaskStatus,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils.errors import ServerError

from a2adk.utils import (
    convert_a2a_parts_to_genai,
    convert_genai_parts_to_a2a,
)
from a2adk.agents import get_agent

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

AUTH_TASK_POLLING_DELAY_SECONDS = 0.2


class A2ARunConfig(RunConfig):
    """Custom override of ADK RunConfig to smuggle extra data through the event loop"""

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )
    current_task_updater: TaskUpdater


class ADKAgentExecutor(AgentExecutor):
    """An AgentExecutor that runs an ADK-based Agent."""

    def __init__(self, 
                 agent_name: str, 
                 *, 
                 artifact_service: BaseArtifactService,
                 session_service: BaseSessionService,
                 memory_service: BaseMemoryService,
    ):
        self._agent = get_agent(agent_name)
        if (memory_service is not None) and (not isinstance(memory_service, InMemoryMemoryService)):
            if self._agent.tools is None:
                self._agent.tools = [load_memory_tool, preload_memory_tool]
            else:
                if not any(isinstance(tool, LoadMemoryTool) for tool in self._agent.tools):
                    self._agent.tools.append(load_memory_tool)
                if not any(isinstance(tool, PreloadMemoryTool) for tool in self._agent.tools):
                    self._agent.tools.append(preload_memory_tool)
        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=artifact_service if artifact_service else InMemoryArtifactService(),
            session_service=session_service if session_service else InMemorySessionService(),
            memory_service=memory_service if memory_service else InMemoryMemoryService(),
        )
        self._save_as_artifacts = (artifact_service is not None) and (not isinstance(artifact_service, InMemoryArtifactService))

    def _run_agent(
        self,
        session_id,
        new_message: types.Content,
        task_updater: TaskUpdater,
    ) -> AsyncGenerator[Event, None]:
        return self._runner.run_async(
            session_id=session_id,
            user_id='self',
            new_message=new_message,
            run_config=A2ARunConfig(current_task_updater=task_updater, save_input_blobs_as_artifacts=self._save_as_artifacts),
        )

    def _get_task_updater(self, tool_context: ToolContext):
        return tool_context._invocation_context.run_config.current_task_updater


    def _upsert_session(self, session_id: str):
        return self._runner.session_service.get_session(
            app_name=self._runner.app_name, user_id='self', session_id=session_id
        ) or self._runner.session_service.create_session(
            app_name=self._runner.app_name, user_id='self', session_id=session_id
        )
    
    async def _process_request(
        self,
        new_message: types.Content,
        session_id: str,
        task_updater: TaskUpdater,
    ) -> AsyncIterable[TaskStatus | Artifact]:
        session_id = self._upsert_session(
            session_id,
        ).id
        async for event in self._run_agent(session_id, new_message, task_updater):
            logger.debug('Received ADK event: %s', event)
            if event.is_final_response():
                response = convert_genai_parts_to_a2a(event.content.parts)
                logger.debug('Yielding final response: %s', response)
                task_updater.add_artifact(response)
                task_updater.complete()
                break
            elif calls := event.get_function_calls():
                for call in calls:
                    # Provide an update on what we're doing.
                    if call.name == 'message_calendar_agent':
                        task_updater.update_status(
                            TaskState.working,
                            message=task_updater.new_agent_message(
                                [
                                    Part(
                                        root=TextPart(
                                            text='Messaging the calendar agent'
                                        )
                                    )
                                ]
                            ),
                        )
            elif not event.get_function_calls():
                logger.debug('Yielding update response')
                task_updater.update_status(
                    TaskState.working,
                    message=task_updater.new_agent_message(
                        convert_genai_parts_to_a2a(event.content.parts)
                    ),
                )
            else:
                logger.debug('Skipping event')

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ):
        # Run the agent until either complete or the task is suspended.
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        # Immediately notify that the task is submitted.
        if not context.current_task:
            updater.submit()
        updater.start_work()
        await self._process_request(
            types.UserContent(
                parts=convert_a2a_parts_to_genai(context.message.parts),
            ),
            context.context_id,
            updater,
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        # Ideally: kill any ongoing tasks.
        raise ServerError(error=UnsupportedOperationError())

