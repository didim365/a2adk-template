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
    sessions_data = sessions_response.model_dump(mode='json')
    if "sessions" in sessions_data and isinstance(sessions_data["sessions"], list):
        all_sessions = sessions_data["sessions"]
        sorted_sessions = sorted(all_sessions, key=lambda s: s.get("last_update_time", 0), reverse=True)
        limited_sessions = []
        for session in sorted_sessions[:5]:
            session_response = await session_service.get_session(app_name=app_name, user_id=user_id, session_id=session["id"])
            session_data = session_response.model_dump(mode='json')
            if "events" in session_data and isinstance(session_data["events"], list):
                user_events = [event for event in session_data["events"] if event.get("content", {}).get("role") == "user"]
                user_events.sort(key=lambda e: e.get("timestamp", 0), reverse=True)                # 최신 5개의 'user' 이벤트만 유지
                latest_user_events = user_events[:5]
                session_data["events"] = latest_user_events
            limited_sessions.append(session_data)
        sessions_data["sessions"] = limited_sessions
        
    return Response(
        content=json.dumps(sessions_data),
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
    
    session = await session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
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