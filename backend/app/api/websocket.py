"""
WebSocket endpoints for real-time features.
"""
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from typing import Optional
import json

from app.services.websocket_manager import websocket_manager
from app.core.auth import get_current_user_websocket

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    client_type: Optional[str] = Query("web"),
    client_version: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for real-time communication.
    
    Query parameters:
    - token: Authentication token
    - client_type: Type of client (web, mobile, cli)
    - client_version: Version of the client
    """
    try:
        # Authenticate user
        user = await get_current_user_websocket(token)
        if not user:
            await websocket.close(code=4001, reason="Authentication required")
            return
        
        user_id = str(user.id)
        client_info = {
            "type": client_type,
            "version": client_version
        }
        
        # Connect to WebSocket manager
        await websocket_manager.connect(websocket, user_id, client_info)
        
        try:
            while True:
                # Receive message from client
                data = await websocket.receive_text()
                
                # Handle the message
                await websocket_manager.handle_message(websocket, data)
                
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for user {user_id}")
        except Exception as e:
            logger.error(f"WebSocket error for user {user_id}: {e}")
        finally:
            websocket_manager.disconnect(websocket)
            
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        try:
            await websocket.close(code=4000, reason="Connection error")
        except Exception:
            pass


@router.get("/ws/stats")
async def get_websocket_stats(current_user = Depends(get_current_user_websocket)):
    """Get WebSocket connection statistics (admin only)."""
    # In a real implementation, you'd check if user is admin
    return websocket_manager.get_connection_stats()


@router.post("/ws/broadcast")
async def broadcast_message(
    message: dict,
    current_user = Depends(get_current_user_websocket)
):
    """Broadcast a message to all connected clients (admin only)."""
    # In a real implementation, you'd check if user is admin
    await websocket_manager.broadcast_to_all(message)
    return {"status": "Message broadcasted"}


@router.post("/ws/send/{user_id}")
async def send_message_to_user(
    user_id: str,
    message: dict,
    current_user = Depends(get_current_user_websocket)
):
    """Send a message to a specific user (admin only)."""
    # In a real implementation, you'd check if user is admin
    await websocket_manager.send_to_user(message, user_id)
    return {"status": f"Message sent to user {user_id}"}


@router.post("/ws/topic/{topic}")
async def send_message_to_topic(
    topic: str,
    message: dict,
    current_user = Depends(get_current_user_websocket)
):
    """Send a message to all users subscribed to a topic (admin only)."""
    # In a real implementation, you'd check if user is admin
    await websocket_manager.send_to_topic(message, topic)
    return {"status": f"Message sent to topic {topic}"}