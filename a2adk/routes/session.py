import json
from starlette.responses import Response
from starlette.requests import Request
from starlette.exceptions import HTTPException

from google.adk.sessions.base_session_service import BaseSessionService

async def list_sessions(request: Request):
    """
    지정된 앱과 사용자에 대한 모든 세션의 목록을 반환합니다.
    """
    session_service = request.app.state.session_service
    if not isinstance(session_service, BaseSessionService):
        raise HTTPException(status_code=500, detail="Session service is not available.")
    
    app_name = request.path_params["app_name"]
    user_id = request.path_params["user_id"]
    
    sessions_response = await session_service.list_sessions(app_name=app_name, user_id=user_id)
    return Response(
        content=json.dumps(sessions_response.model_dump(mode='json')),
        media_type="application/json"
    )

async def get_session_messages(request: Request):
    """
    지정된 앱과 사용자에 대한 세션의 메시지를 반환합니다.
    """
    session_service = request.app.state.session_service
    if not isinstance(session_service, BaseSessionService):
        raise HTTPException(status_code=500, detail="Session service is not available.")
    
    app_name = request.path_params["app_name"]
    user_id = request.path_params["user_id"]
    session_id = request.path_params["session_id"]
    
    session = session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
    messages = []
    for event in session.events:
        if event.content.parts[0].text:
            # Construct the base message dictionary
            base_message = {
                'messageId': event.id,
                'role': 'user' if event.content.role == 'user' else 'agent',
                'timestamp': event.timestamp,
                'parts': []
            }

            # Iterate over parts and add them to the message
            for part in event.content.parts:
                if hasattr(part, 'text'):
                    base_message['parts'].append({'type': 'text', 'text': part.text})
                else:
                    # Fallback for unknown part types
                    base_message['parts'].append({'type': 'unknown', 'content': str(part)})
            
            # Add message to messages list if it has parts
            if base_message['parts']:
                messages.append(base_message)
            
    return Response(
        content=json.dumps(messages),
        media_type="application/json"
    )