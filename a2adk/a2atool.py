import httpx
from uuid import uuid4
import asyncio
import logging
from typing import Any

from google.adk.tools import BaseTool, ToolContext

from a2a.types import (
    AgentCard,
    SendMessageRequest,
    MessageSendParams,
    Message,
    Role,
    Part,
    TextPart,
    SendMessageSuccessResponse,
    Task,
    TaskState,
    GetTaskRequest,
    GetTaskSuccessResponse,
    TaskQueryParams,
    TextPart,
)
from a2a.client import A2AClient, A2ACardResolver
from a2a.utils import get_text_parts

logger = logging.getLogger(__name__)

class A2ATool(BaseTool):
    def __init__(self, agent_url: str):
        self._agent_endpoint = agent_url
        self._agent_card = self._get_agent_card()
        super().__init__(
            name=self._agent_card.name,
            description=self._agent_card.description,
            is_long_running=self._agent_card.capabilities.pushNotifications,
        )

    async def __call__(self, message: str, tool_context: ToolContext):
        """Send a message to the calendar agent."""
        # We take an overly simplistic approach to the A2A state machine:
        # - All requests to the calendar agent use the current session ID as the context ID.
        # - If the last response from the calendar agent (in this session) produced a non-terminal
        #   task state, the request references that task.
        request = SendMessageRequest(
            params=MessageSendParams(
                message=Message(
                    contextId=tool_context._invocation_context.session.id,
                    taskId=tool_context.state.get('task_id'),
                    messageId=str(uuid4()),
                    role=Role.user,
                    parts=[Part(TextPart(text=message))],
                )
            )
        )
        response = await self._send_agent_message(request)
        logger.debug('[A2A Client] Received response: %s', response)
        task_id = None
        content = []
        if isinstance(response.root, SendMessageSuccessResponse):
            if isinstance(response.root.result, Task):
                task = response.root.result
                if task.artifacts:
                    for artifact in task.artifacts:
                        content.extend(get_text_parts(artifact.parts))
                if not content:
                    content.extend(get_text_parts(task.status.message.parts))
                # Ideally should be "is terminal state"
                if task.status.state != TaskState.completed:
                    task_id = task.id
                if task.status.state == TaskState.auth_required:
                    tool_context.state['task_suspended'] = True
                    tool_context.state['dependent_task'] = task.model_dump()
            else:
                content.extend(get_text_parts(response.root.result.parts))
        tool_context.state['task_id'] = task_id
        # Just turn it all into a string.
        return {'response': '\n'.join(content)}

    async def _send_agent_message(self, request: SendMessageRequest):
        async with httpx.AsyncClient() as client:
            calendar_agent_client = A2AClient(
                httpx_client=client, url=self._agent_endpoint
            )
            return await calendar_agent_client.send_message(request)
        
    async def _auth_required_task(self,tool_context: ToolContext) -> dict | None:
        """Handle requests that return auth-required"""
        if not tool_context.state.get('task_suspended'):
            return None
        dependent_task = Task.model_validate(
            tool_context.state['dependent_task']
        )
        if dependent_task.status.state != TaskState.auth_required:
            return None
        task_updater = tool_context._invocation_context.run_config.current_task_updater
        task_updater.update_status(
            dependent_task.status.state, message=dependent_task.status.message
        )
        # This is not a robust solution. We expect that the calendar agent will only
        # ever go from auth-required -> completed. A more robust solution would have
        # more complete state transition handling.
        task = await self._wait_for_dependent_task(dependent_task)
        task_updater.update_status(
            TaskState.working,
            message=task_updater.new_agent_message(
                [Part(TextPart(text='Checking calendar agent output'))]
            ),
        )
        tool_context.state['task_suspended'] = False
        tool_context.state['dependent_task'] = None
        content = []
        if task.artifacts:
            for artifact in task.artifacts:
                content.extend(get_text_parts(artifact.parts))
        return {'response': '\n'.join(content)}
    
    async def _wait_for_dependent_task(self, dependent_task: Task):
        async with httpx.AsyncClient() as client:
            # Subscribe would be good. We'll poll instead.
            a2a_client = A2AClient(
                httpx_client=client, url=self._agent_endpoint
            )
            # We want to wait until the task is in a terminal state.
            while not self._is_task_complete(dependent_task):
                await asyncio.sleep(0.2)  # AUTH_TASK_POLLING_DELAY_SECONDS
                response = await a2a_client.get_task(
                    GetTaskRequest(params=TaskQueryParams(id=dependent_task.id))
                )
                if not isinstance(response.root, GetTaskSuccessResponse):
                    logger.debug('Getting dependent task failed: %s', response)
                    # In a real scenario, may want to feed this response back to
                    # the agent loop to decide what to do. We'll just fail the
                    # task.
                    raise Exception('Getting dependent task failed')
                dependent_task = response.root.result
            return dependent_task

    def _is_task_complete(self, task: Task) -> bool:
        return task.status.state == TaskState.completed

    def _get_agent_card(self, agent_card_path: str = '/.well-known/agent.json', http_kwargs: dict[str, Any] | None = None) -> AgentCard:
        async def _get():
            async with httpx.AsyncClient() as client:
                agent_card = A2ACardResolver(
                    client, base_url=self._agent_endpoint, agent_card_path=agent_card_path
                )
                return await agent_card.get_agent_card(http_kwargs=http_kwargs)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            return asyncio.run_coroutine_threadsafe(_get(), loop).result()
        else:
            return asyncio.run(_get())
