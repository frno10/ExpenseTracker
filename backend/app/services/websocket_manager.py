"""
WebSocket connection manager for real-time features.
"""
import json
import logging
from typing import Dict, List, Set, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
import asyncio
from enum import Enum

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """WebSocket message types."""
    EXPENSE_CREATED = "expense_created"
    EXPENSE_UPDATED = "expense_updated"
    EXPENSE_DELETED = "expense_deleted"
    BUDGET_ALERT = "budget_alert"
    BUDGET_UPDATED = "budget_updated"
    IMPORT_PROGRESS = "import_progress"
    IMPORT_COMPLETED = "import_completed"
    ANALYTICS_UPDATED = "analytics_updated"
    NOTIFICATION = "notification"
    HEARTBEAT = "heartbeat"
    ERROR = "error"


class WebSocketManager:
    """Manages WebSocket connections and real-time messaging."""
    
    def __init__(self):
        # Store active connections by user ID
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Store connection metadata
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
        # Store subscriptions (user_id -> set of topics)
        self.subscriptions: Dict[str, Set[str]] = {}
        
    async def connect(self, websocket: WebSocket, user_id: str, client_info: Optional[Dict] = None):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        
        # Initialize user connections if not exists
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        # Add connection
        self.active_connections[user_id].add(websocket)
        
        # Store metadata
        self.connection_metadata[websocket] = {
            "user_id": user_id,
            "connected_at": datetime.utcnow(),
            "client_info": client_info or {},
            "last_heartbeat": datetime.utcnow()
        }
        
        # Initialize subscriptions
        if user_id not in self.subscriptions:
            self.subscriptions[user_id] = set()
        
        logger.info(f"WebSocket connected for user {user_id}")
        
        # Send welcome message
        await self.send_personal_message({
            "type": "connected",
            "message": "WebSocket connection established",
            "timestamp": datetime.utcnow().isoformat()
        }, websocket)
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if websocket in self.connection_metadata:
            user_id = self.connection_metadata[websocket]["user_id"]
            
            # Remove from active connections
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                
                # Clean up empty user entries
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
                    if user_id in self.subscriptions:
                        del self.subscriptions[user_id]
            
            # Remove metadata
            del self.connection_metadata[websocket]
            
            logger.info(f"WebSocket disconnected for user {user_id}")
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send a message to a specific WebSocket connection."""
        try:
            await websocket.send_text(json.dumps(message, default=str))
        except Exception as e:
            logger.error(f"Error sending message to WebSocket: {e}")
            self.disconnect(websocket)
    
    async def send_to_user(self, message: Dict[str, Any], user_id: str):
        """Send a message to all connections for a specific user."""
        if user_id in self.active_connections:
            disconnected_connections = []
            
            for websocket in self.active_connections[user_id].copy():
                try:
                    await websocket.send_text(json.dumps(message, default=str))
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id}: {e}")
                    disconnected_connections.append(websocket)
            
            # Clean up disconnected connections
            for websocket in disconnected_connections:
                self.disconnect(websocket)
    
    async def broadcast_to_all(self, message: Dict[str, Any]):
        """Broadcast a message to all connected users."""
        for user_id in list(self.active_connections.keys()):
            await self.send_to_user(message, user_id)
    
    async def subscribe_to_topic(self, user_id: str, topic: str):
        """Subscribe a user to a specific topic."""
        if user_id not in self.subscriptions:
            self.subscriptions[user_id] = set()
        
        self.subscriptions[user_id].add(topic)
        logger.info(f"User {user_id} subscribed to topic: {topic}")
    
    async def unsubscribe_from_topic(self, user_id: str, topic: str):
        """Unsubscribe a user from a specific topic."""
        if user_id in self.subscriptions:
            self.subscriptions[user_id].discard(topic)
            logger.info(f"User {user_id} unsubscribed from topic: {topic}")
    
    async def send_to_topic(self, message: Dict[str, Any], topic: str):
        """Send a message to all users subscribed to a topic."""
        for user_id, topics in self.subscriptions.items():
            if topic in topics:
                await self.send_to_user(message, user_id)
    
    async def handle_message(self, websocket: WebSocket, data: str):
        """Handle incoming WebSocket messages."""
        try:
            message = json.loads(data)
            message_type = message.get("type")
            
            if message_type == "heartbeat":
                await self.handle_heartbeat(websocket)
            elif message_type == "subscribe":
                await self.handle_subscription(websocket, message)
            elif message_type == "unsubscribe":
                await self.handle_unsubscription(websocket, message)
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received from WebSocket")
            await self.send_personal_message({
                "type": MessageType.ERROR,
                "message": "Invalid JSON format"
            }, websocket)
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            await self.send_personal_message({
                "type": MessageType.ERROR,
                "message": "Internal server error"
            }, websocket)
    
    async def handle_heartbeat(self, websocket: WebSocket):
        """Handle heartbeat messages."""
        if websocket in self.connection_metadata:
            self.connection_metadata[websocket]["last_heartbeat"] = datetime.utcnow()
            
            await self.send_personal_message({
                "type": MessageType.HEARTBEAT,
                "timestamp": datetime.utcnow().isoformat()
            }, websocket)
    
    async def handle_subscription(self, websocket: WebSocket, message: Dict[str, Any]):
        """Handle subscription requests."""
        if websocket in self.connection_metadata:
            user_id = self.connection_metadata[websocket]["user_id"]
            topic = message.get("topic")
            
            if topic:
                await self.subscribe_to_topic(user_id, topic)
                await self.send_personal_message({
                    "type": "subscribed",
                    "topic": topic,
                    "message": f"Subscribed to {topic}"
                }, websocket)
    
    async def handle_unsubscription(self, websocket: WebSocket, message: Dict[str, Any]):
        """Handle unsubscription requests."""
        if websocket in self.connection_metadata:
            user_id = self.connection_metadata[websocket]["user_id"]
            topic = message.get("topic")
            
            if topic:
                await self.unsubscribe_from_topic(user_id, topic)
                await self.send_personal_message({
                    "type": "unsubscribed",
                    "topic": topic,
                    "message": f"Unsubscribed from {topic}"
                }, websocket)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get statistics about active connections."""
        total_connections = sum(len(connections) for connections in self.active_connections.values())
        
        return {
            "total_connections": total_connections,
            "unique_users": len(self.active_connections),
            "connections_by_user": {
                user_id: len(connections) 
                for user_id, connections in self.active_connections.items()
            },
            "total_subscriptions": sum(len(topics) for topics in self.subscriptions.values())
        }
    
    async def cleanup_stale_connections(self, max_age_minutes: int = 30):
        """Clean up stale connections that haven't sent heartbeat."""
        current_time = datetime.utcnow()
        stale_connections = []
        
        for websocket, metadata in self.connection_metadata.items():
            last_heartbeat = metadata.get("last_heartbeat", metadata["connected_at"])
            age_minutes = (current_time - last_heartbeat).total_seconds() / 60
            
            if age_minutes > max_age_minutes:
                stale_connections.append(websocket)
        
        for websocket in stale_connections:
            logger.info(f"Cleaning up stale WebSocket connection")
            self.disconnect(websocket)
            try:
                await websocket.close()
            except Exception:
                pass  # Connection might already be closed


# Global WebSocket manager instance
websocket_manager = WebSocketManager()


# Real-time event functions
async def notify_expense_created(user_id: str, expense_data: Dict[str, Any]):
    """Notify about new expense creation."""
    message = {
        "type": MessageType.EXPENSE_CREATED,
        "data": expense_data,
        "timestamp": datetime.utcnow().isoformat()
    }
    await websocket_manager.send_to_user(message, user_id)
    await websocket_manager.send_to_topic(message, "expenses")


async def notify_expense_updated(user_id: str, expense_data: Dict[str, Any]):
    """Notify about expense updates."""
    message = {
        "type": MessageType.EXPENSE_UPDATED,
        "data": expense_data,
        "timestamp": datetime.utcnow().isoformat()
    }
    await websocket_manager.send_to_user(message, user_id)
    await websocket_manager.send_to_topic(message, "expenses")


async def notify_expense_deleted(user_id: str, expense_id: str):
    """Notify about expense deletion."""
    message = {
        "type": MessageType.EXPENSE_DELETED,
        "data": {"expense_id": expense_id},
        "timestamp": datetime.utcnow().isoformat()
    }
    await websocket_manager.send_to_user(message, user_id)
    await websocket_manager.send_to_topic(message, "expenses")


async def notify_budget_alert(user_id: str, budget_data: Dict[str, Any], alert_type: str):
    """Notify about budget alerts."""
    message = {
        "type": MessageType.BUDGET_ALERT,
        "data": {
            "budget": budget_data,
            "alert_type": alert_type
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    await websocket_manager.send_to_user(message, user_id)
    await websocket_manager.send_to_topic(message, "budgets")


async def notify_budget_updated(user_id: str, budget_data: Dict[str, Any]):
    """Notify about budget updates."""
    message = {
        "type": MessageType.BUDGET_UPDATED,
        "data": budget_data,
        "timestamp": datetime.utcnow().isoformat()
    }
    await websocket_manager.send_to_user(message, user_id)
    await websocket_manager.send_to_topic(message, "budgets")


async def notify_import_progress(user_id: str, import_id: str, progress: int, status: str, details: Optional[Dict] = None):
    """Notify about import progress."""
    message = {
        "type": MessageType.IMPORT_PROGRESS,
        "data": {
            "import_id": import_id,
            "progress": progress,
            "status": status,
            "details": details or {}
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    await websocket_manager.send_to_user(message, user_id)
    await websocket_manager.send_to_topic(message, f"import_{import_id}")


async def notify_import_completed(user_id: str, import_id: str, result: Dict[str, Any]):
    """Notify about import completion."""
    message = {
        "type": MessageType.IMPORT_COMPLETED,
        "data": {
            "import_id": import_id,
            "result": result
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    await websocket_manager.send_to_user(message, user_id)
    await websocket_manager.send_to_topic(message, f"import_{import_id}")


async def notify_analytics_updated(user_id: str, analytics_data: Dict[str, Any]):
    """Notify about analytics updates."""
    message = {
        "type": MessageType.ANALYTICS_UPDATED,
        "data": analytics_data,
        "timestamp": datetime.utcnow().isoformat()
    }
    await websocket_manager.send_to_user(message, user_id)
    await websocket_manager.send_to_topic(message, "analytics")


async def send_notification(user_id: str, notification: Dict[str, Any]):
    """Send a general notification."""
    message = {
        "type": MessageType.NOTIFICATION,
        "data": notification,
        "timestamp": datetime.utcnow().isoformat()
    }
    await websocket_manager.send_to_user(message, user_id)