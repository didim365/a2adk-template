from starlette.routing import Route
from a2adk.routes.bucket import get_bucket_file
from a2adk.routes.session import list_sessions, get_session_messages

def get_routes():
    return [
        Route("/buckets/{filepath:path}", get_bucket_file, methods=["GET"]),
        Route("/apps/{app_name:path}/users/{user_id:path}/sessions/{session_id:path}/messages", get_session_messages, methods=["GET"]),
        Route("/apps/{app_name:path}/users/{user_id:path}/sessions", list_sessions, methods=["GET"]),
    ]