# Deploying ADK Agent to Operating Environment

## Agent Development
Develop using [ADK](https://google.github.io/adk-docs/).

## Agent Environment Configuration
1. ADK Environment
- The ADK agent runs in a runner. The runner uses [artifact_service](https://google.github.io/adk-docs/artifacts/), [session_service, and memory_service](https://google.github.io/adk-docs/sessions/) to provide documents, short-term memory, and long-term memory.
The default configuration in the sample is InMemory...(). Modify it according to your individual environment.

```python
# a2adk/adk_agent_executor.py
...
class ADKAgentExecutor(AgentExecutor):
    """An AgentExecutor that runs an ADK-based Agent."""

    def __init__(self, agent_name):
        self._agent = get_agent(agent_name)
        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )
...
```
- artifact_service
```python
from google.adk.artifacts import GcsArtifactService
...
artifact_service=GcsArtifactService(bucket_name="...")
...
```
- session_service
```python
from google.adk.sessions import DatabaseSessionService
...
session_service=DatabaseSessionService(db_url="...")
...
```
```python
from google.adk.sessions import VertexAiSessionService
...
session_service=VertexAiSessionService(project="...", location="...")
...
```
- memory_service
```python
from google.adk.memory import VertexAiRagMemoryService
...
memory_service=VertexAiRagMemoryService(rag_corpus="...", similarity_top_k=5, vector_distance_threshold=10)
...
```

2. Using .env  
Set the GCS_ARTIFACT_SERVICE, DATABASE_SESSION_SERVICE, and VERTEXAIRAG_MEMORY_SERVICE values in the .env file to use their respective environments. (The default is to use InMemory...())

## A2A Environment Configuration
To run A2A Server's Tasks for a long time, configure [task_store and queue_manager](https://google.github.io/A2A/sdk/python/#a2a.server.request_handlers.DefaultRequestHandler) in an environment capable of long-term storage. The default configuration in the sample is InMemory...(). Modify it according to your individual environment.
```python
# a2adk/__main__.py
...
def main(host: str, port: int, agent: str):
...
    agent_executor = ADKAgentExecutor(agent)
    agent_card = get_agent_card(host, port)
    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor,
        task_store=InMemoryTaskStore(),
        queue_manager=InMemoryQueueManager()
    )
...
```
DatabaseTaskStore() and DatabaseQueueManager() are not yet provided. (As of 25.5.25)
