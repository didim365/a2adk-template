import logging
import os
from dotenv import load_dotenv
import uvicorn
from starlette.middleware.cors import CORSMiddleware
from urllib.parse import urlparse
from starlette.datastructures import State

from google.adk.artifacts.gcs_artifact_service import GcsArtifactService
from google.adk.memory.vertex_ai_rag_memory_service import VertexAiRagMemoryService
from google.adk.sessions.database_session_service import DatabaseSessionService
from google.adk.sessions.vertex_ai_session_service import VertexAiSessionService
from google.adk.sessions.in_memory_session_service import InMemorySessionService

from a2a.server.apps import A2AStarletteApplication
from a2a.server.events import InMemoryQueueManager
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore

env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
print(".env path: ", env_path)
load_dotenv(env_path)

logging.basicConfig()

from a2adk.adk_agent_executor import ADKAgentExecutor
from a2adk.agents.card import get_agent_card
from a2adk.routes import get_routes

A2A_SERVER_URL = os.getenv("VITE_A2A_SERVER_URL")
# A2A_SERVER_URL에서 호스트와 포트 추출
parsed_url = urlparse(A2A_SERVER_URL)
DEFAULT_HOST = parsed_url.hostname if parsed_url.hostname else 'localhost'
DEFAULT_PORT = parsed_url.port if parsed_url.port else 10008
ROOT_AGENT_NAME = os.getenv("ROOT_AGENT_NAME") or "root_agent"
UVICORN_WORKERS = int(os.getenv("UVICORN_WORKERS") or 4)

def create_app(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, agent: str = ROOT_AGENT_NAME):
    # Verify an API key is set. Not required if using Vertex AI APIs, since those can use gcloud credentials.
    if not os.getenv('GOOGLE_GENAI_USE_VERTEXAI') == 'TRUE':
        if not os.getenv('GOOGLE_API_KEY'):
            raise Exception(
                'GOOGLE_API_KEY environment variable not set and GOOGLE_GENAI_USE_VERTEXAI is not TRUE.'
            )
        
    if os.getenv('GCS_ARTIFACT_SERVICE'):
        artifact_service = GcsArtifactService(bucket_name=os.getenv('GCS_ARTIFACT_SERVICE'))
    else:
        artifact_service = None

    if os.getenv('DATABASE_SESSION_SERVICE'):
        session_service = DatabaseSessionService(db_url=os.getenv('DATABASE_SESSION_SERVICE'))
    elif os.getenv('VERTEXAI_SESSION_SERVICE'):
        vertexai_value = os.getenv('VERTEXAI_SESSION_SERVICE').split(":")
        if len(vertexai_value) == 2:
            session_service = VertexAiSessionService(project=vertexai_value[0], location=vertexai_value[1])
        else:
            session_service = VertexAiSessionService(project=vertexai_value[0])
    else:
        session_service = None
        
    if os.getenv('VERTEXAIRAG_MEMORY_SERVICE'):
        memory_service = VertexAiRagMemoryService(rag_corpus=os.getenv('VERTEXAIRAG_MEMORY_SERVICE'))
    else:
        memory_service = None

    agent_executor = ADKAgentExecutor(
        agent_name=agent,
        artifact_service=artifact_service,
        session_service=session_service,
        memory_service=memory_service,
    )
    agent_card = get_agent_card(host, port)
    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor, 
        task_store=InMemoryTaskStore(), 
        queue_manager=InMemoryQueueManager()
    )
    
    # A2AStarletteApplication 인스턴스 생성 (빌더 역할)
    a2a_app_config = A2AStarletteApplication(
        agent_card=agent_card, 
        http_handler=request_handler
    )
    
    custom_routes = get_routes()
    if custom_routes and len(custom_routes) > 0:
        routes = a2a_app_config.routes() # 빌더에서 기본 라우트 가져오기
        routes.extend(custom_routes)
        # 최종 Starlette 앱 빌드
        app_instance = a2a_app_config.build(routes=routes)
    else:
        # 최종 Starlette 앱 빌드
        app_instance = a2a_app_config.build()
    
    # State 객체 생성 및 설정
    app_state = State()
    app_state.session_service = agent_executor._runner.session_service
    app_instance.state = app_state # 빌드된 Starlette 앱에 state 할당

    # CORS 미들웨어 추가 (최종 앱 인스턴스에)
    app_instance.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 실제 운영 환경에서는 구체적인 도메인을 지정하세요
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app_instance

def create_app_for_uvicorn():
    return create_app()

def main():
    uvicorn.run("a2adk.__main__:create_app_for_uvicorn", host=DEFAULT_HOST, port=DEFAULT_PORT, workers=UVICORN_WORKERS, factory=True)

if __name__ == '__main__':
    main()