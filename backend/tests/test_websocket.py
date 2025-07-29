"""
Tests for WebSocket functionality.
"""
import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket

from app.main import app
from app.services.websocket_manager import (
    WebSocketManager, 
    MessageType,
    notify_expense_created,
    notify_budget_alert,
    notify_import_progress
)


class TestWebSocketManager:
    """Test WebSocket manager functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = WebSocketManager()
        self.mock_websocket = MagicMock(spec=WebSocket)
        self.mock_websocket.send_text = AsyncMock()
        self.user_id = "test-user-123"
    
    @pytest.mark.asyncio
    async def test_connect_websocket(self):
        """Test WebSocket connection."""
        await self.manager.connect(self.mock_websocket, self.user_id)
        
        # Check that connection was added
        assert self.user_id in self.manager.active_connections
        assert self.mock_websocket in self.manager.active_connections[self.user_id]
        assert self.mock_websocket in self.manager.connection_metadata
        
        # Check welcome message was sent
        self.mock_websocket.send_text.assert_called_once()
        call_args = self.mock_websocket.send_text.call_args[0][0]
        message = json.loads(call_args)
        assert message["type"] == "connected"
    
    def test_disconnect_websocket(self):
        """Test WebSocket disconnection."""
        # First connect
        asyncio.run(self.manager.connect(self.mock_websocket, self.user_id))
        
        # Then disconnect
        self.manager.disconnect(self.mock_websocket)
        
        # Check that connection was removed
        assert self.user_id not in self.manager.active_connections
        assert self.mock_websocket not in self.manager.connection_metadata
    
    @pytest.mark.asyncio
    async def test_send_to_user(self):
        """Test sending message to specific user."""
        await self.manager.connect(self.mock_websocket, self.user_id)
        
        test_message = {"type": "test", "data": "test_data"}
        await self.manager.send_to_user(test_message, self.user_id)
        
        # Check that message was sent (welcome message + test message)
        assert self.mock_websocket.send_text.call_count == 2
        
        # Check the test message
        call_args = self.mock_websocket.send_text.call_args[0][0]
        sent_message = json.loads(call_args)
        assert sent_message == test_message
    
    @pytest.mark.asyncio
    async def test_subscribe_to_topic(self):
        """Test topic subscription."""
        await self.manager.connect(self.mock_websocket, self.user_id)
        await self.manager.subscribe_to_topic(self.user_id, "expenses")
        
        assert "expenses" in self.manager.subscriptions[self.user_id]
    
    @pytest.mark.asyncio
    async def test_send_to_topic(self):
        """Test sending message to topic subscribers."""
        await self.manager.connect(self.mock_websocket, self.user_id)
        await self.manager.subscribe_to_topic(self.user_id, "expenses")
        
        test_message = {"type": "expense_created", "data": {"id": "123"}}
        await self.manager.send_to_topic(test_message, "expenses")
        
        # Check that message was sent to subscriber
        assert self.mock_websocket.send_text.call_count == 2  # welcome + topic message
    
    @pytest.mark.asyncio
    async def test_handle_heartbeat_message(self):
        """Test heartbeat message handling."""
        await self.manager.connect(self.mock_websocket, self.user_id)
        
        heartbeat_message = json.dumps({"type": "heartbeat"})
        await self.manager.handle_message(self.mock_websocket, heartbeat_message)
        
        # Should send heartbeat response
        assert self.mock_websocket.send_text.call_count == 2  # welcome + heartbeat response
    
    @pytest.mark.asyncio
    async def test_handle_subscribe_message(self):
        """Test subscription message handling."""
        await self.manager.connect(self.mock_websocket, self.user_id)
        
        subscribe_message = json.dumps({"type": "subscribe", "topic": "budgets"})
        await self.manager.handle_message(self.mock_websocket, subscribe_message)
        
        # Check subscription was added
        assert "budgets" in self.manager.subscriptions[self.user_id]
        
        # Should send subscription confirmation
        assert self.mock_websocket.send_text.call_count == 2  # welcome + confirmation
    
    @pytest.mark.asyncio
    async def test_handle_invalid_json(self):
        """Test handling of invalid JSON messages."""
        await self.manager.connect(self.mock_websocket, self.user_id)
        
        invalid_message = "invalid json"
        await self.manager.handle_message(self.mock_websocket, invalid_message)
        
        # Should send error message
        assert self.mock_websocket.send_text.call_count == 2  # welcome + error
        
        # Check error message
        call_args = self.mock_websocket.send_text.call_args[0][0]
        error_message = json.loads(call_args)
        assert error_message["type"] == MessageType.ERROR
    
    def test_get_connection_stats(self):
        """Test connection statistics."""
        # Connect multiple users
        asyncio.run(self.manager.connect(self.mock_websocket, self.user_id))
        
        mock_websocket2 = MagicMock(spec=WebSocket)
        mock_websocket2.send_text = AsyncMock()
        asyncio.run(self.manager.connect(mock_websocket2, "user2"))
        
        stats = self.manager.get_connection_stats()
        
        assert stats["total_connections"] == 2
        assert stats["unique_users"] == 2
        assert self.user_id in stats["connections_by_user"]
        assert "user2" in stats["connections_by_user"]


class TestWebSocketNotifications:
    """Test WebSocket notification functions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = WebSocketManager()
        self.mock_websocket = MagicMock(spec=WebSocket)
        self.mock_websocket.send_text = AsyncMock()
        self.user_id = "test-user-123"
    
    @pytest.mark.asyncio
    async def test_notify_expense_created(self):
        """Test expense creation notification."""
        await self.manager.connect(self.mock_websocket, self.user_id)
        
        expense_data = {
            "id": "expense-123",
            "amount": 25.50,
            "description": "Coffee",
            "category": "Food"
        }
        
        await notify_expense_created(self.user_id, expense_data)
        
        # Check that notification was sent
        assert self.mock_websocket.send_text.call_count == 2  # welcome + notification
        
        # Check notification content
        call_args = self.mock_websocket.send_text.call_args[0][0]
        message = json.loads(call_args)
        assert message["type"] == MessageType.EXPENSE_CREATED
        assert message["data"] == expense_data
    
    @pytest.mark.asyncio
    async def test_notify_budget_alert(self):
        """Test budget alert notification."""
        await self.manager.connect(self.mock_websocket, self.user_id)
        
        budget_data = {
            "id": "budget-123",
            "name": "Monthly Budget",
            "percentage_used": 85.5
        }
        
        await notify_budget_alert(self.user_id, budget_data, "warning")
        
        # Check that notification was sent
        assert self.mock_websocket.send_text.call_count == 2  # welcome + notification
        
        # Check notification content
        call_args = self.mock_websocket.send_text.call_args[0][0]
        message = json.loads(call_args)
        assert message["type"] == MessageType.BUDGET_ALERT
        assert message["data"]["budget"] == budget_data
        assert message["data"]["alert_type"] == "warning"
    
    @pytest.mark.asyncio
    async def test_notify_import_progress(self):
        """Test import progress notification."""
        await self.manager.connect(self.mock_websocket, self.user_id)
        
        import_id = "import-123"
        progress = 75
        status = "Processing transactions"
        
        await notify_import_progress(self.user_id, import_id, progress, status)
        
        # Check that notification was sent
        assert self.mock_websocket.send_text.call_count == 2  # welcome + notification
        
        # Check notification content
        call_args = self.mock_websocket.send_text.call_args[0][0]
        message = json.loads(call_args)
        assert message["type"] == MessageType.IMPORT_PROGRESS
        assert message["data"]["import_id"] == import_id
        assert message["data"]["progress"] == progress
        assert message["data"]["status"] == status


class TestWebSocketEndpoints:
    """Test WebSocket API endpoints."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_websocket_endpoint_without_token(self):
        """Test WebSocket endpoint without authentication token."""
        with pytest.raises(Exception):  # Should fail due to missing auth
            with self.client.websocket_connect("/api/ws"):
                pass
    
    def test_websocket_stats_endpoint(self):
        """Test WebSocket stats endpoint."""
        # This would require proper authentication setup
        # For now, just test that the endpoint exists
        response = self.client.get("/api/ws/stats")
        # Will return 401 without proper auth, which is expected
        assert response.status_code in [401, 422]  # 422 for missing dependencies


class TestWebSocketIntegration:
    """Test WebSocket integration with services."""
    
    @pytest.mark.asyncio
    async def test_expense_service_websocket_integration(self):
        """Test that expense service sends WebSocket notifications."""
        # This would require mocking the expense service and database
        # For now, just test that the notification functions exist and are callable
        
        expense_data = {
            "id": "test-expense",
            "amount": 100.0,
            "description": "Test expense"
        }
        
        # These should not raise exceptions
        await notify_expense_created("user-123", expense_data)
        # No assertions needed - just testing that functions are callable
    
    @pytest.mark.asyncio
    async def test_budget_service_websocket_integration(self):
        """Test that budget service sends WebSocket notifications."""
        budget_data = {
            "id": "test-budget",
            "name": "Test Budget",
            "percentage_used": 90.0
        }
        
        # These should not raise exceptions
        await notify_budget_alert("user-123", budget_data, "warning")
        # No assertions needed - just testing that functions are callable


@pytest.mark.asyncio
async def test_websocket_cleanup():
    """Test WebSocket connection cleanup."""
    manager = WebSocketManager()
    
    # Create mock connections with old timestamps
    mock_websocket = MagicMock(spec=WebSocket)
    mock_websocket.send_text = AsyncMock()
    mock_websocket.close = AsyncMock()
    
    await manager.connect(mock_websocket, "test-user")
    
    # Manually set old timestamp
    from datetime import datetime, timedelta
    old_time = datetime.utcnow() - timedelta(minutes=35)
    manager.connection_metadata[mock_websocket]["last_heartbeat"] = old_time
    
    # Run cleanup
    await manager.cleanup_stale_connections(max_age_minutes=30)
    
    # Connection should be removed
    assert "test-user" not in manager.active_connections
    assert mock_websocket not in manager.connection_metadata


if __name__ == "__main__":
    pytest.main([__file__])