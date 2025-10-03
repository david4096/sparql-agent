"""
Unit Tests for WebSocket System.

This module provides comprehensive test coverage for the WebSocket
real-time communication system.
"""

import asyncio
import json
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from .websocket import (
    WebSocketManager,
    MessageType,
    QueryProgress,
    ConnectionState,
    ConnectionInfo,
    Room,
    MessageQueue,
)


# Fixtures

@pytest.fixture
async def ws_manager():
    """Create a WebSocket manager for testing."""
    manager = WebSocketManager(
        heartbeat_interval=1,
        heartbeat_timeout=2,
        rate_limit_per_minute=60,
    )
    await manager.start()
    yield manager
    await manager.shutdown()


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket."""
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive_json = AsyncMock()
    ws.close = AsyncMock()
    ws.client = Mock()
    ws.client.host = "127.0.0.1"
    return ws


# Test Connection Management

@pytest.mark.asyncio
async def test_connect(ws_manager, mock_websocket):
    """Test WebSocket connection."""
    connection_id = await ws_manager.connect(
        websocket=mock_websocket,
        user_id="test_user",
        user_name="Test User",
    )

    assert connection_id in ws_manager.connections
    assert ws_manager.connections[connection_id].user_id == "test_user"
    assert ws_manager.connections[connection_id].user_name == "Test User"
    assert ws_manager.connections[connection_id].state == ConnectionState.CONNECTED

    # Check connection acknowledgment was sent
    mock_websocket.send_json.assert_called_once()
    call_args = mock_websocket.send_json.call_args[0][0]
    assert call_args["type"] == MessageType.CONNECTION_ACK


@pytest.mark.asyncio
async def test_disconnect(ws_manager, mock_websocket):
    """Test WebSocket disconnection."""
    connection_id = await ws_manager.connect(
        websocket=mock_websocket,
        user_id="test_user",
    )

    await ws_manager.disconnect(connection_id)

    assert connection_id not in ws_manager.connections
    mock_websocket.close.assert_called_once()


@pytest.mark.asyncio
async def test_multiple_connections_same_user(ws_manager, mock_websocket):
    """Test multiple connections for the same user."""
    ws1 = mock_websocket
    ws2 = AsyncMock()
    ws2.accept = AsyncMock()
    ws2.send_json = AsyncMock()
    ws2.client = Mock()
    ws2.client.host = "127.0.0.1"

    conn1 = await ws_manager.connect(ws1, user_id="user1")
    conn2 = await ws_manager.connect(ws2, user_id="user1")

    assert len(ws_manager.user_connections["user1"]) == 2
    assert conn1 in ws_manager.user_connections["user1"]
    assert conn2 in ws_manager.user_connections["user1"]


# Test Messaging

@pytest.mark.asyncio
async def test_send_to_connection(ws_manager, mock_websocket):
    """Test sending message to specific connection."""
    connection_id = await ws_manager.connect(mock_websocket)

    message = {"type": "test_message", "payload": {"data": "test"}}
    result = await ws_manager.send_to_connection(connection_id, message)

    assert result is True
    assert mock_websocket.send_json.call_count == 2  # 1 ack + 1 test message


@pytest.mark.asyncio
async def test_send_to_user(ws_manager):
    """Test sending message to all user connections."""
    ws1 = AsyncMock()
    ws1.accept = AsyncMock()
    ws1.send_json = AsyncMock()
    ws1.client = Mock()
    ws1.client.host = "127.0.0.1"

    ws2 = AsyncMock()
    ws2.accept = AsyncMock()
    ws2.send_json = AsyncMock()
    ws2.client = Mock()
    ws2.client.host = "127.0.0.1"

    await ws_manager.connect(ws1, user_id="user1")
    await ws_manager.connect(ws2, user_id="user1")

    message = {"type": "test_message", "payload": {"data": "test"}}
    count = await ws_manager.send_to_user("user1", message)

    assert count == 2
    assert ws1.send_json.call_count == 2  # 1 ack + 1 test message
    assert ws2.send_json.call_count == 2  # 1 ack + 1 test message


@pytest.mark.asyncio
async def test_broadcast(ws_manager):
    """Test broadcasting message to all connections."""
    ws1 = AsyncMock()
    ws1.accept = AsyncMock()
    ws1.send_json = AsyncMock()
    ws1.client = Mock()
    ws1.client.host = "127.0.0.1"

    ws2 = AsyncMock()
    ws2.accept = AsyncMock()
    ws2.send_json = AsyncMock()
    ws2.client = Mock()
    ws2.client.host = "127.0.0.1"

    await ws_manager.connect(ws1, user_id="user1")
    await ws_manager.connect(ws2, user_id="user2")

    message = {"type": "broadcast", "payload": {"data": "test"}}
    count = await ws_manager.broadcast(message)

    assert count == 2


@pytest.mark.asyncio
async def test_message_queue_offline_user(ws_manager, mock_websocket):
    """Test message queuing for offline users."""
    message = {"type": "test_message", "payload": {"data": "test"}}

    # Send to offline user
    count = await ws_manager.send_to_user("offline_user", message, queue_if_offline=True)
    assert count == 0

    # Verify message was queued
    assert "offline_user" in ws_manager.message_queues
    assert ws_manager.message_queues["offline_user"].has_messages()

    # Connect user
    connection_id = await ws_manager.connect(mock_websocket, user_id="offline_user")

    # Wait a bit for queued messages to be sent
    await asyncio.sleep(0.1)

    # Verify message was sent
    assert mock_websocket.send_json.call_count >= 2  # ack + queued message


# Test Room Management

@pytest.mark.asyncio
async def test_create_room(ws_manager):
    """Test room creation."""
    room = await ws_manager.create_room(
        room_id="test_room",
        name="Test Room",
        max_members=10,
    )

    assert room.room_id == "test_room"
    assert room.name == "Test Room"
    assert room.max_members == 10
    assert "test_room" in ws_manager.rooms


@pytest.mark.asyncio
async def test_join_room(ws_manager, mock_websocket):
    """Test joining a room."""
    # Create room
    await ws_manager.create_room(
        room_id="test_room",
        name="Test Room",
    )

    # Connect user
    connection_id = await ws_manager.connect(mock_websocket, user_id="user1")

    # Join room
    result = await ws_manager.join_room(connection_id, "test_room")

    assert result is True
    assert connection_id in ws_manager.rooms["test_room"].members
    assert "test_room" in ws_manager.connections[connection_id].rooms


@pytest.mark.asyncio
async def test_leave_room(ws_manager, mock_websocket):
    """Test leaving a room."""
    # Create room
    await ws_manager.create_room(room_id="test_room", name="Test Room")

    # Connect and join
    connection_id = await ws_manager.connect(mock_websocket, user_id="user1")
    await ws_manager.join_room(connection_id, "test_room")

    # Leave room
    result = await ws_manager.leave_room(connection_id, "test_room")

    assert result is True
    assert connection_id not in ws_manager.rooms["test_room"].members
    assert "test_room" not in ws_manager.connections[connection_id].rooms


@pytest.mark.asyncio
async def test_send_to_room(ws_manager):
    """Test sending message to room."""
    # Create room
    await ws_manager.create_room(room_id="test_room", name="Test Room")

    # Connect users
    ws1 = AsyncMock()
    ws1.accept = AsyncMock()
    ws1.send_json = AsyncMock()
    ws1.client = Mock()
    ws1.client.host = "127.0.0.1"

    ws2 = AsyncMock()
    ws2.accept = AsyncMock()
    ws2.send_json = AsyncMock()
    ws2.client = Mock()
    ws2.client.host = "127.0.0.1"

    conn1 = await ws_manager.connect(ws1, user_id="user1")
    conn2 = await ws_manager.connect(ws2, user_id="user2")

    # Join room
    await ws_manager.join_room(conn1, "test_room")
    await ws_manager.join_room(conn2, "test_room")

    # Send to room
    message = {"type": "room_message", "payload": {"data": "test"}}
    count = await ws_manager.send_to_room("test_room", message)

    assert count == 2


@pytest.mark.asyncio
async def test_room_max_members(ws_manager, mock_websocket):
    """Test room max members limit."""
    # Create room with max 1 member
    await ws_manager.create_room(
        room_id="test_room",
        name="Test Room",
        max_members=1,
    )

    # Connect two users
    ws1 = mock_websocket
    ws2 = AsyncMock()
    ws2.accept = AsyncMock()
    ws2.send_json = AsyncMock()
    ws2.client = Mock()
    ws2.client.host = "127.0.0.1"

    conn1 = await ws_manager.connect(ws1, user_id="user1")
    conn2 = await ws_manager.connect(ws2, user_id="user2")

    # First user joins successfully
    result1 = await ws_manager.join_room(conn1, "test_room")
    assert result1 is True

    # Second user should fail
    result2 = await ws_manager.join_room(conn2, "test_room")
    assert result2 is False


@pytest.mark.asyncio
async def test_delete_room(ws_manager, mock_websocket):
    """Test room deletion."""
    # Create room and add member
    await ws_manager.create_room(room_id="test_room", name="Test Room")
    connection_id = await ws_manager.connect(mock_websocket, user_id="user1")
    await ws_manager.join_room(connection_id, "test_room")

    # Delete room
    result = await ws_manager.delete_room("test_room")

    assert result is True
    assert "test_room" not in ws_manager.rooms
    assert "test_room" not in ws_manager.connections[connection_id].rooms


# Test Rate Limiting

@pytest.mark.asyncio
async def test_rate_limit(ws_manager, mock_websocket):
    """Test rate limiting."""
    connection_id = await ws_manager.connect(mock_websocket)
    connection = ws_manager.connections[connection_id]

    # Exhaust rate limit tokens
    connection.rate_limit_tokens = 0

    result = await ws_manager._check_rate_limit(connection)
    assert result is False


@pytest.mark.asyncio
async def test_rate_limit_refill(ws_manager, mock_websocket):
    """Test rate limit token refill."""
    connection_id = await ws_manager.connect(mock_websocket)
    connection = ws_manager.connections[connection_id]

    # Set low tokens
    connection.rate_limit_tokens = 10

    # Wait for refill
    await asyncio.sleep(2)

    # Tokens should be refilled
    assert connection.rate_limit_tokens > 10


# Test Message Handlers

@pytest.mark.asyncio
async def test_register_handler(ws_manager):
    """Test registering message handlers."""
    handler_called = False

    async def test_handler(connection_id: str, message: dict):
        nonlocal handler_called
        handler_called = True

    ws_manager.register_handler(MessageType.QUERY_REQUEST, test_handler)

    # Verify handler is registered
    assert MessageType.QUERY_REQUEST in ws_manager.message_handlers
    assert test_handler in ws_manager.message_handlers[MessageType.QUERY_REQUEST]


@pytest.mark.asyncio
async def test_handle_message(ws_manager, mock_websocket):
    """Test message handling."""
    handler_called = False
    received_message = None

    async def test_handler(connection_id: str, message: dict):
        nonlocal handler_called, received_message
        handler_called = True
        received_message = message

    ws_manager.register_handler(MessageType.QUERY_REQUEST, test_handler)

    connection_id = await ws_manager.connect(mock_websocket)

    message = {
        "type": MessageType.QUERY_REQUEST,
        "payload": {"natural_language": "test query"}
    }

    await ws_manager.handle_message(connection_id, message)

    assert handler_called
    assert received_message == message


@pytest.mark.asyncio
async def test_handle_ping_pong(ws_manager, mock_websocket):
    """Test ping/pong heartbeat."""
    connection_id = await ws_manager.connect(mock_websocket)

    # Send ping
    await ws_manager.handle_message(connection_id, {"type": MessageType.PING})

    # Should send pong
    calls = [call[0][0] for call in mock_websocket.send_json.call_args_list]
    pong_sent = any(call.get("type") == MessageType.PONG for call in calls)
    assert pong_sent


# Test Metrics

@pytest.mark.asyncio
async def test_metrics(ws_manager, mock_websocket):
    """Test metrics collection."""
    initial_metrics = ws_manager.get_metrics()
    assert "total_connections" in initial_metrics
    assert "active_connections" in initial_metrics

    # Connect a user
    await ws_manager.connect(mock_websocket, user_id="user1")

    updated_metrics = ws_manager.get_metrics()
    assert updated_metrics["total_connections"] == initial_metrics["total_connections"] + 1
    assert updated_metrics["active_connections"] == 1


@pytest.mark.asyncio
async def test_connection_info(ws_manager, mock_websocket):
    """Test getting connection information."""
    connection_id = await ws_manager.connect(
        mock_websocket,
        user_id="user1",
        user_name="Test User",
    )

    info = ws_manager.get_connection_info(connection_id)

    assert info is not None
    assert info["connection_id"] == connection_id
    assert info["user_id"] == "user1"
    assert info["user_name"] == "Test User"
    assert info["authenticated"] is False
    assert info["state"] == ConnectionState.CONNECTED.value


@pytest.mark.asyncio
async def test_room_info(ws_manager):
    """Test getting room information."""
    await ws_manager.create_room(
        room_id="test_room",
        name="Test Room",
        max_members=10,
    )

    info = ws_manager.get_room_info("test_room")

    assert info is not None
    assert info["room_id"] == "test_room"
    assert info["name"] == "Test Room"
    assert info["max_members"] == 10
    assert info["member_count"] == 0


# Test MessageQueue

def test_message_queue():
    """Test message queue functionality."""
    queue = MessageQueue(user_id="user1", max_size=3)

    # Add messages
    queue.add({"msg": 1})
    queue.add({"msg": 2})
    queue.add({"msg": 3})

    assert queue.has_messages()

    # Get all messages
    messages = queue.get_all()
    assert len(messages) == 3
    assert not queue.has_messages()

    # Queue overflow
    queue.add({"msg": 1})
    queue.add({"msg": 2})
    queue.add({"msg": 3})
    queue.add({"msg": 4})  # Should push out first message

    messages = queue.get_all()
    assert len(messages) == 3
    assert messages[0]["msg"] == 2  # First message was dropped


# Test Cleanup

@pytest.mark.asyncio
async def test_disconnect_cleanup(ws_manager, mock_websocket):
    """Test cleanup on disconnect."""
    # Create room and join
    await ws_manager.create_room(room_id="test_room", name="Test Room")
    connection_id = await ws_manager.connect(mock_websocket, user_id="user1")
    await ws_manager.join_room(connection_id, "test_room")

    # Disconnect
    await ws_manager.disconnect(connection_id)

    # Verify cleanup
    assert connection_id not in ws_manager.connections
    assert connection_id not in ws_manager.rooms["test_room"].members


@pytest.mark.asyncio
async def test_shutdown_cleanup(ws_manager, mock_websocket):
    """Test cleanup on manager shutdown."""
    # Connect users
    conn1 = await ws_manager.connect(mock_websocket)

    ws2 = AsyncMock()
    ws2.accept = AsyncMock()
    ws2.send_json = AsyncMock()
    ws2.close = AsyncMock()
    ws2.client = Mock()
    ws2.client.host = "127.0.0.1"
    conn2 = await ws_manager.connect(ws2)

    # Shutdown
    await ws_manager.shutdown()

    # Verify all connections closed
    assert len(ws_manager.connections) == 0
    mock_websocket.close.assert_called()
    ws2.close.assert_called()


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
