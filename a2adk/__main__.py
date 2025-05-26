import logging
import os
from dotenv import load_dotenv
import click
import uvicorn
from starlette.middleware.cors import CORSMiddleware
from urllib.parse import urlparse
from starlette.datastructures import State

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

@click.command()
@click.option('--host', 'host', default=DEFAULT_HOST)
@click.option('--port', 'port', default=DEFAULT_PORT)
@click.option('--agent', 'agent', default='root_agent')
def main(host: str, port: int, agent: str):
    # Verify an API key is set. Not required if using Vertex AI APIs, since those can use gcloud credentials.
    if not os.getenv('GOOGLE_GENAI_USE_VERTEXAI') == 'TRUE':
        if not os.getenv('GOOGLE_API_KEY'):
            raise Exception(
                'GOOGLE_API_KEY environment variable not set and GOOGLE_GENAI_USE_VERTEXAI is not TRUE.'
            )

    agent_executor = ADKAgentExecutor(agent)
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
        app = a2a_app_config.build(routes=routes)
    else:
        # 최종 Starlette 앱 빌드
        app = a2a_app_config.build()
    
    # State 객체 생성 및 설정
    app_state = State()
    app_state.session_service = agent_executor._runner.session_service
    app.state = app_state # 빌드된 Starlette 앱에 state 할당

    # CORS 미들웨어 추가 (최종 앱 인스턴스에)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 실제 운영 환경에서는 구체적인 도메인을 지정하세요
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    uvicorn.run(app, host=host, port=port)

if __name__ == '__main__':
    main()