# ADK Agent 운영환경 배포

## Agent 개발
[ADK](https://google.github.io/adk-docs/)를 사용해 개발 합니다.

## Agent 환경 구성
1. ADK 환경
- adk agent는 runner에서 수행한다. runner는 [artifact_service](https://google.github.io/adk-docs/artifacts/), [session_service, memory_service](https://google.github.io/adk-docs/sessions/)를 이용해 문서, 단기 기역, 장기 기역을 제공한다.
샘플의 기본 구성은 InMemory...()입니다. 개별 환경에 맞추어 수정합니다.

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

## A2A 환경 구성
A2A Server의 Task를 장기 수행하기 위해서는 [task_store, queue_manager](https://google.github.io/A2A/sdk/python/#a2a.server.request_handlers.DefaultRequestHandler)를 장기 보관가능한 환경으로 구성합니다. 샘플의 기본 구성은 InMemory...()입니다. 개별 환경에 맞추어 수정합니다.
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
아직 DatabaseTaskStore()나 DatabaseQueueManager()를 제공하지 않습니다. (25.5.25 현재)
