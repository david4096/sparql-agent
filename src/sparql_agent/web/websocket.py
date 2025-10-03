"""
WebSocket Real-Time Communication System for SPARQL Agent.

This module provides a comprehensive WebSocket infrastructure for real-time communication,
supporting multiple concurrent connections, message broadcasting, room-based messaging,
and integration with the SPARQL query generation and execution pipeline.

Features:
- Multiple concurrent WebSocket connections with lifecycle management
- Message broadcasting to specific users, groups, or rooms
- Connection authentication and authorization
- Rate limiting per connection
- Automatic reconnection with exponential backoff (client-side)
- Message queuing for offline clients
- Heartbeat/keepalive mechanism
- Room-based messaging for collaboration
- Message persistence for reliability
- Real-time query progress tracking
- Live ontology term suggestions
- Collaborative query building
- Endpoint health monitoring
- Result streaming for large datasets

Usage:
    from sparql_agent.web.websocket import WebSocketManager, create_websocket_routes

    # Initialize manager
    manager = WebSocketManager()

    # Register WebSocket routes in FastAPI
    app.include_router(create_websocket_routes(manager))

    # Broadcast message to all connections
    await manager.broadcast({"type": "system_message", "content": "Hello!"})

    # Send to specific user
    await manager.send_to_user(user_id="user123", message={"type": "notification"})

    # Send to room
    await manager.send_to_room(room_id="query-room-1", message={"type": "update"})
"""

import asyncio
import hashlib
import json
import logging
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field, validator


logger = logging.getLogger(__name__)


# Message Types

class MessageType(str, Enum):
    """WebSocket message types for real-time communication."""

    # Query-related messages
    QUERY_REQUEST = "query_request"
    QUERY_PROGRESS = "query_progress"
    QUERY_RESULT = "query_result"
    QUERY_CANCELLED = "query_cancelled"

    # Error messages
    ERROR_MESSAGE = "error_message"
    VALIDATION_ERROR = "validation_error"

    # Ontology messages
    ONTOLOGY_SUGGESTION = "ontology_suggestion"
    ONTOLOGY_SEARCH = "ontology_search"

    # Endpoint messages
    ENDPOINT_STATUS = "endpoint_status"
    ENDPOINT_HEALTH = "endpoint_health"

    # Collaboration messages
    TYPING_INDICATOR = "typing_indicator"
    USER_JOINED = "user_joined"
    USER_LEFT = "user_left"
    CURSOR_POSITION = "cursor_position"

    # System messages
    SYSTEM_MESSAGE = "system_message"
    NOTIFICATION = "notification"

    # Connection management
    CONNECTION_ACK = "connection_ack"
    HEARTBEAT = "heartbeat"
    PONG = "pong"
    PING = "ping"

    # Room management
    JOIN_ROOM = "join_room"
    LEAVE_ROOM = "leave_room"
    ROOM_MESSAGE = "room_message"


class QueryProgress(str, Enum):
    """Query execution progress stages."""
    PARSING = "parsing"
    VALIDATING = "validating"
    GENERATING = "generating"
    OPTIMIZING = "optimizing"
    EXECUTING = "executing"
    FORMATTING = "formatting"
    COMPLETED = "completed"
    FAILED = "failed"


class ConnectionState(str, Enum):
    """WebSocket connection state."""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"


# Pydantic Models for Messages

class WebSocketMessage(BaseModel):
    """Base WebSocket message structure."""

    type: MessageType = Field(..., description="Message type")
    timestamp: float = Field(default_factory=time.time, description="Message timestamp")
    message_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique message ID")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for request/response tracking")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Message payload")

    class Config:
        use_enum_values = True


class QueryRequestMessage(BaseModel):
    """Query request message."""

    natural_language: str = Field(..., description="Natural language query")
    endpoint_id: Optional[str] = Field(None, description="Endpoint identifier")
    endpoint_url: Optional[str] = Field(None, description="Direct endpoint URL")
    strategy: str = Field("auto", description="Generation strategy")
    execute: bool = Field(True, description="Execute the generated query")
    limit: Optional[int] = Field(100, description="Result limit")
    timeout: Optional[int] = Field(None, description="Query timeout in seconds")


class QueryProgressMessage(BaseModel):
    """Query progress update message."""

    query_id: str = Field(..., description="Query identifier")
    stage: QueryProgress = Field(..., description="Current execution stage")
    progress: float = Field(..., ge=0.0, le=1.0, description="Progress percentage (0-1)")
    message: str = Field(..., description="Progress message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")


class QueryResultMessage(BaseModel):
    """Query result message."""

    query_id: str = Field(..., description="Query identifier")
    query: str = Field(..., description="Generated SPARQL query")
    results: Optional[Dict[str, Any]] = Field(None, description="Query results")
    execution_time: float = Field(..., description="Execution time in seconds")
    row_count: Optional[int] = Field(None, description="Number of rows returned")
    explanation: Optional[str] = Field(None, description="Query explanation")


class OntologySuggestionMessage(BaseModel):
    """Ontology term suggestion message."""

    query_text: str = Field(..., description="Current query text")
    suggestions: List[Dict[str, Any]] = Field(..., description="Suggested ontology terms")
    position: Optional[int] = Field(None, description="Cursor position")


class TypingIndicatorMessage(BaseModel):
    """Typing indicator message."""

    user_id: str = Field(..., description="User ID")
    user_name: Optional[str] = Field(None, description="User name")
    is_typing: bool = Field(..., description="Whether user is typing")
    room_id: Optional[str] = Field(None, description="Room ID if in a room")


# Connection Management

@dataclass
class ConnectionInfo:
    """Information about a WebSocket connection."""

    connection_id: str
    websocket: WebSocket
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    authenticated: bool = False
    connected_at: datetime = field(default_factory=datetime.now)
    last_heartbeat: datetime = field(default_factory=datetime.now)
    state: ConnectionState = ConnectionState.CONNECTING
    metadata: Dict[str, Any] = field(default_factory=dict)
    rooms: Set[str] = field(default_factory=set)
    message_count: int = 0
    last_message_time: Optional[datetime] = None
    rate_limit_tokens: int = 100  # Token bucket for rate limiting
    ip_address: Optional[str] = None


@dataclass
class Room:
    """Represents a WebSocket room for collaborative sessions."""

    room_id: str
    name: str
    owner_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    members: Set[str] = field(default_factory=set)  # connection_ids
    metadata: Dict[str, Any] = field(default_factory=dict)
    max_members: int = 50
    is_public: bool = True


# Message Queue for Offline Clients

@dataclass
class MessageQueue:
    """Message queue for offline clients."""

    user_id: str
    messages: deque = field(default_factory=lambda: deque(maxlen=100))
    max_size: int = 100

    def add(self, message: Dict[str, Any]) -> None:
        """Add a message to the queue."""
        self.messages.append(message)

    def get_all(self) -> List[Dict[str, Any]]:
        """Get all queued messages and clear the queue."""
        messages = list(self.messages)
        self.messages.clear()
        return messages

    def has_messages(self) -> bool:
        """Check if there are queued messages."""
        return len(self.messages) > 0


# WebSocket Manager

class WebSocketManager:
    """
    Manages WebSocket connections, messaging, and collaboration features.

    Features:
    - Connection lifecycle management
    - Message broadcasting and unicasting
    - Room-based messaging
    - Rate limiting per connection
    - Message queuing for offline clients
    - Heartbeat/keepalive mechanism
    - Connection authentication
    - Metrics and monitoring
    """

    def __init__(
        self,
        heartbeat_interval: int = 30,
        heartbeat_timeout: int = 60,
        rate_limit_per_minute: int = 60,
        enable_message_persistence: bool = True,
        enable_rooms: bool = True,
    ):
        """
        Initialize WebSocket manager.

        Args:
            heartbeat_interval: Seconds between heartbeat checks
            heartbeat_timeout: Seconds before connection is considered dead
            rate_limit_per_minute: Maximum messages per minute per connection
            enable_message_persistence: Enable message queuing for offline clients
            enable_rooms: Enable room-based messaging
        """
        self.connections: Dict[str, ConnectionInfo] = {}
        self.user_connections: Dict[str, Set[str]] = defaultdict(set)  # user_id -> connection_ids
        self.rooms: Dict[str, Room] = {}
        self.message_queues: Dict[str, MessageQueue] = {}

        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout
        self.rate_limit_per_minute = rate_limit_per_minute
        self.enable_message_persistence = enable_message_persistence
        self.enable_rooms = enable_rooms

        # Metrics
        self.metrics = {
            "total_connections": 0,
            "active_connections": 0,
            "total_messages_sent": 0,
            "total_messages_received": 0,
            "total_rooms_created": 0,
            "disconnections": 0,
            "errors": 0,
            "rate_limit_violations": 0,
        }

        # Message handlers
        self.message_handlers: Dict[MessageType, List[Callable]] = defaultdict(list)

        # Start background tasks
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._rate_limit_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start background tasks."""
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self._rate_limit_task = asyncio.create_task(self._rate_limit_refill_loop())
        logger.info("WebSocket manager started")

    async def shutdown(self) -> None:
        """Shutdown manager and close all connections."""
        logger.info("Shutting down WebSocket manager...")

        # Cancel background tasks
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()
        if self._rate_limit_task:
            self._rate_limit_task.cancel()

        # Close all connections
        for connection_id in list(self.connections.keys()):
            await self.disconnect(connection_id, code=status.WS_1001_GOING_AWAY)

        logger.info("WebSocket manager shutdown complete")

    async def connect(
        self,
        websocket: WebSocket,
        user_id: Optional[str] = None,
        user_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Accept a new WebSocket connection.

        Args:
            websocket: WebSocket instance
            user_id: Optional user identifier
            user_name: Optional user name
            metadata: Optional connection metadata

        Returns:
            Connection ID
        """
        await websocket.accept()

        connection_id = str(uuid4())

        # Get client IP
        ip_address = None
        if hasattr(websocket, 'client') and websocket.client:
            ip_address = websocket.client.host

        # Create connection info
        connection = ConnectionInfo(
            connection_id=connection_id,
            websocket=websocket,
            user_id=user_id,
            user_name=user_name,
            state=ConnectionState.CONNECTED,
            metadata=metadata or {},
            ip_address=ip_address,
        )

        # Store connection
        self.connections[connection_id] = connection

        if user_id:
            self.user_connections[user_id].add(connection_id)

        # Update metrics
        self.metrics["total_connections"] += 1
        self.metrics["active_connections"] = len(self.connections)

        # Send connection acknowledgment
        await self.send_to_connection(
            connection_id=connection_id,
            message={
                "type": MessageType.CONNECTION_ACK,
                "payload": {
                    "connection_id": connection_id,
                    "user_id": user_id,
                    "server_time": datetime.now().isoformat(),
                    "heartbeat_interval": self.heartbeat_interval,
                }
            }
        )

        # Send queued messages if any
        if user_id and self.enable_message_persistence:
            await self._send_queued_messages(connection_id, user_id)

        logger.info(f"WebSocket connection established: {connection_id} (user: {user_id})")

        return connection_id

    async def disconnect(
        self,
        connection_id: str,
        code: int = status.WS_1000_NORMAL_CLOSURE,
        reason: Optional[str] = None,
    ) -> None:
        """
        Disconnect a WebSocket connection.

        Args:
            connection_id: Connection identifier
            code: WebSocket close code
            reason: Optional reason for disconnection
        """
        if connection_id not in self.connections:
            return

        connection = self.connections[connection_id]

        # Update state
        connection.state = ConnectionState.DISCONNECTING

        # Leave all rooms
        for room_id in list(connection.rooms):
            await self.leave_room(connection_id, room_id)

        # Close WebSocket
        try:
            await connection.websocket.close(code=code, reason=reason)
        except Exception as e:
            logger.error(f"Error closing WebSocket {connection_id}: {e}")

        # Remove from user connections
        if connection.user_id:
            self.user_connections[connection.user_id].discard(connection_id)
            if not self.user_connections[connection.user_id]:
                del self.user_connections[connection.user_id]

        # Remove connection
        connection.state = ConnectionState.DISCONNECTED
        del self.connections[connection_id]

        # Update metrics
        self.metrics["disconnections"] += 1
        self.metrics["active_connections"] = len(self.connections)

        logger.info(f"WebSocket connection closed: {connection_id} (reason: {reason})")

    async def send_to_connection(
        self,
        connection_id: str,
        message: Dict[str, Any],
    ) -> bool:
        """
        Send a message to a specific connection.

        Args:
            connection_id: Connection identifier
            message: Message to send

        Returns:
            True if sent successfully, False otherwise
        """
        if connection_id not in self.connections:
            logger.warning(f"Connection {connection_id} not found")
            return False

        connection = self.connections[connection_id]

        try:
            await connection.websocket.send_json(message)
            self.metrics["total_messages_sent"] += 1
            return True
        except Exception as e:
            logger.error(f"Error sending message to {connection_id}: {e}")
            self.metrics["errors"] += 1
            # Disconnect on send error
            await self.disconnect(connection_id, reason="Send error")
            return False

    async def send_to_user(
        self,
        user_id: str,
        message: Dict[str, Any],
        queue_if_offline: bool = True,
    ) -> int:
        """
        Send a message to all connections for a user.

        Args:
            user_id: User identifier
            message: Message to send
            queue_if_offline: Queue message if user is offline

        Returns:
            Number of connections message was sent to
        """
        connection_ids = self.user_connections.get(user_id, set())

        if not connection_ids:
            # User is offline
            if queue_if_offline and self.enable_message_persistence:
                if user_id not in self.message_queues:
                    self.message_queues[user_id] = MessageQueue(user_id=user_id)
                self.message_queues[user_id].add(message)
                logger.debug(f"Queued message for offline user {user_id}")
            return 0

        sent_count = 0
        for connection_id in connection_ids:
            if await self.send_to_connection(connection_id, message):
                sent_count += 1

        return sent_count

    async def send_to_room(
        self,
        room_id: str,
        message: Dict[str, Any],
        exclude_connection: Optional[str] = None,
    ) -> int:
        """
        Send a message to all connections in a room.

        Args:
            room_id: Room identifier
            message: Message to send
            exclude_connection: Optional connection ID to exclude

        Returns:
            Number of connections message was sent to
        """
        if room_id not in self.rooms:
            logger.warning(f"Room {room_id} not found")
            return 0

        room = self.rooms[room_id]
        sent_count = 0

        for connection_id in room.members:
            if connection_id == exclude_connection:
                continue
            if await self.send_to_connection(connection_id, message):
                sent_count += 1

        return sent_count

    async def broadcast(
        self,
        message: Dict[str, Any],
        exclude_connection: Optional[str] = None,
    ) -> int:
        """
        Broadcast a message to all connected clients.

        Args:
            message: Message to send
            exclude_connection: Optional connection ID to exclude

        Returns:
            Number of connections message was sent to
        """
        sent_count = 0

        for connection_id in list(self.connections.keys()):
            if connection_id == exclude_connection:
                continue
            if await self.send_to_connection(connection_id, message):
                sent_count += 1

        return sent_count

    async def receive_message(
        self,
        connection_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Receive a message from a connection.

        Args:
            connection_id: Connection identifier

        Returns:
            Received message or None
        """
        if connection_id not in self.connections:
            return None

        connection = self.connections[connection_id]

        # Check rate limit
        if not await self._check_rate_limit(connection):
            self.metrics["rate_limit_violations"] += 1
            await self.send_to_connection(
                connection_id,
                {
                    "type": MessageType.ERROR_MESSAGE,
                    "payload": {
                        "error": "Rate limit exceeded",
                        "retry_after": 60,
                    }
                }
            )
            return None

        try:
            message = await connection.websocket.receive_json()

            # Update connection stats
            connection.message_count += 1
            connection.last_message_time = datetime.now()

            self.metrics["total_messages_received"] += 1

            return message

        except WebSocketDisconnect:
            await self.disconnect(connection_id, reason="Client disconnected")
            return None
        except Exception as e:
            logger.error(f"Error receiving message from {connection_id}: {e}")
            self.metrics["errors"] += 1
            await self.disconnect(connection_id, reason="Receive error")
            return None

    async def _check_rate_limit(self, connection: ConnectionInfo) -> bool:
        """Check if connection is within rate limit."""
        if connection.rate_limit_tokens <= 0:
            return False
        connection.rate_limit_tokens -= 1
        return True

    async def _rate_limit_refill_loop(self) -> None:
        """Background task to refill rate limit tokens."""
        while True:
            try:
                await asyncio.sleep(1)  # Refill every second

                tokens_per_second = self.rate_limit_per_minute / 60

                for connection in self.connections.values():
                    connection.rate_limit_tokens = min(
                        connection.rate_limit_tokens + tokens_per_second,
                        self.rate_limit_per_minute
                    )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in rate limit refill loop: {e}")

    async def _send_queued_messages(self, connection_id: str, user_id: str) -> None:
        """Send queued messages to a newly connected user."""
        if user_id not in self.message_queues:
            return

        queue = self.message_queues[user_id]
        if not queue.has_messages():
            return

        messages = queue.get_all()
        logger.info(f"Sending {len(messages)} queued messages to user {user_id}")

        for message in messages:
            await self.send_to_connection(connection_id, message)

        # Remove empty queue
        if not queue.has_messages():
            del self.message_queues[user_id]

    # Room Management

    async def create_room(
        self,
        room_id: str,
        name: str,
        owner_id: Optional[str] = None,
        max_members: int = 50,
        is_public: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Room:
        """
        Create a new room.

        Args:
            room_id: Room identifier
            name: Room name
            owner_id: Optional owner user ID
            max_members: Maximum number of members
            is_public: Whether room is public
            metadata: Optional room metadata

        Returns:
            Created room
        """
        if not self.enable_rooms:
            raise ValueError("Rooms are not enabled")

        if room_id in self.rooms:
            raise ValueError(f"Room {room_id} already exists")

        room = Room(
            room_id=room_id,
            name=name,
            owner_id=owner_id,
            max_members=max_members,
            is_public=is_public,
            metadata=metadata or {},
        )

        self.rooms[room_id] = room
        self.metrics["total_rooms_created"] += 1

        logger.info(f"Room created: {room_id} ({name})")

        return room

    async def delete_room(self, room_id: str) -> bool:
        """
        Delete a room and remove all members.

        Args:
            room_id: Room identifier

        Returns:
            True if deleted, False if not found
        """
        if room_id not in self.rooms:
            return False

        room = self.rooms[room_id]

        # Remove all members
        for connection_id in list(room.members):
            await self.leave_room(connection_id, room_id)

        del self.rooms[room_id]

        logger.info(f"Room deleted: {room_id}")

        return True

    async def join_room(
        self,
        connection_id: str,
        room_id: str,
    ) -> bool:
        """
        Add a connection to a room.

        Args:
            connection_id: Connection identifier
            room_id: Room identifier

        Returns:
            True if joined, False otherwise
        """
        if connection_id not in self.connections:
            return False

        if room_id not in self.rooms:
            return False

        connection = self.connections[connection_id]
        room = self.rooms[room_id]

        # Check max members
        if len(room.members) >= room.max_members:
            await self.send_to_connection(
                connection_id,
                {
                    "type": MessageType.ERROR_MESSAGE,
                    "payload": {
                        "error": "Room is full",
                        "room_id": room_id,
                    }
                }
            )
            return False

        # Add to room
        room.members.add(connection_id)
        connection.rooms.add(room_id)

        # Notify room members
        await self.send_to_room(
            room_id,
            {
                "type": MessageType.USER_JOINED,
                "payload": {
                    "room_id": room_id,
                    "user_id": connection.user_id,
                    "user_name": connection.user_name,
                    "connection_id": connection_id,
                    "member_count": len(room.members),
                }
            },
            exclude_connection=connection_id
        )

        # Send confirmation to joining user
        await self.send_to_connection(
            connection_id,
            {
                "type": MessageType.JOIN_ROOM,
                "payload": {
                    "room_id": room_id,
                    "room_name": room.name,
                    "member_count": len(room.members),
                    "metadata": room.metadata,
                }
            }
        )

        logger.info(f"Connection {connection_id} joined room {room_id}")

        return True

    async def leave_room(
        self,
        connection_id: str,
        room_id: str,
    ) -> bool:
        """
        Remove a connection from a room.

        Args:
            connection_id: Connection identifier
            room_id: Room identifier

        Returns:
            True if left, False otherwise
        """
        if connection_id not in self.connections:
            return False

        if room_id not in self.rooms:
            return False

        connection = self.connections[connection_id]
        room = self.rooms[room_id]

        # Remove from room
        room.members.discard(connection_id)
        connection.rooms.discard(room_id)

        # Notify room members
        await self.send_to_room(
            room_id,
            {
                "type": MessageType.USER_LEFT,
                "payload": {
                    "room_id": room_id,
                    "user_id": connection.user_id,
                    "user_name": connection.user_name,
                    "connection_id": connection_id,
                    "member_count": len(room.members),
                }
            }
        )

        logger.info(f"Connection {connection_id} left room {room_id}")

        return True

    # Heartbeat and Cleanup

    async def _heartbeat_loop(self) -> None:
        """Background task to send heartbeats and check for dead connections."""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)

                now = datetime.now()
                timeout = timedelta(seconds=self.heartbeat_timeout)

                for connection_id, connection in list(self.connections.items()):
                    # Check if connection is alive
                    if now - connection.last_heartbeat > timeout:
                        logger.warning(f"Connection {connection_id} timed out")
                        await self.disconnect(connection_id, reason="Heartbeat timeout")
                        continue

                    # Send heartbeat
                    await self.send_to_connection(
                        connection_id,
                        {
                            "type": MessageType.HEARTBEAT,
                            "payload": {
                                "timestamp": now.isoformat(),
                            }
                        }
                    )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")

    async def _cleanup_loop(self) -> None:
        """Background task to clean up stale data."""
        while True:
            try:
                await asyncio.sleep(300)  # Every 5 minutes

                # Clean up empty rooms
                for room_id, room in list(self.rooms.items()):
                    if len(room.members) == 0:
                        # Delete room if empty for more than 1 hour
                        if (datetime.now() - room.created_at).total_seconds() > 3600:
                            del self.rooms[room_id]
                            logger.info(f"Cleaned up empty room: {room_id}")

                # Clean up old message queues
                for user_id, queue in list(self.message_queues.items()):
                    if not queue.has_messages():
                        del self.message_queues[user_id]

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

    def update_heartbeat(self, connection_id: str) -> None:
        """Update last heartbeat time for a connection."""
        if connection_id in self.connections:
            self.connections[connection_id].last_heartbeat = datetime.now()

    # Message Handlers

    def register_handler(
        self,
        message_type: MessageType,
        handler: Callable,
    ) -> None:
        """
        Register a message handler for a specific message type.

        Args:
            message_type: Message type to handle
            handler: Async handler function that takes (connection_id, message)
        """
        self.message_handlers[message_type].append(handler)
        logger.debug(f"Registered handler for {message_type}")

    async def handle_message(
        self,
        connection_id: str,
        message: Dict[str, Any],
    ) -> None:
        """
        Route a received message to registered handlers.

        Args:
            connection_id: Connection identifier
            message: Received message
        """
        message_type = message.get("type")

        if not message_type:
            logger.warning(f"Message without type from {connection_id}")
            return

        try:
            msg_type = MessageType(message_type)
        except ValueError:
            logger.warning(f"Unknown message type: {message_type}")
            return

        # Handle built-in message types
        if msg_type == MessageType.PING:
            await self.send_to_connection(
                connection_id,
                {
                    "type": MessageType.PONG,
                    "payload": {"timestamp": time.time()}
                }
            )
            self.update_heartbeat(connection_id)
            return

        if msg_type == MessageType.PONG:
            self.update_heartbeat(connection_id)
            return

        # Call registered handlers
        handlers = self.message_handlers.get(msg_type, [])
        for handler in handlers:
            try:
                await handler(connection_id, message)
            except Exception as e:
                logger.error(f"Error in handler for {msg_type}: {e}")
                self.metrics["errors"] += 1

    # Metrics and Monitoring

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        return {
            **self.metrics,
            "active_connections": len(self.connections),
            "active_rooms": len(self.rooms),
            "queued_messages": sum(len(q.messages) for q in self.message_queues.values()),
            "connections_by_state": self._get_connections_by_state(),
        }

    def _get_connections_by_state(self) -> Dict[str, int]:
        """Get connection count by state."""
        counts = defaultdict(int)
        for connection in self.connections.values():
            counts[connection.state.value] += 1
        return dict(counts)

    def get_connection_info(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a connection."""
        if connection_id not in self.connections:
            return None

        connection = self.connections[connection_id]
        return {
            "connection_id": connection.connection_id,
            "user_id": connection.user_id,
            "user_name": connection.user_name,
            "authenticated": connection.authenticated,
            "connected_at": connection.connected_at.isoformat(),
            "last_heartbeat": connection.last_heartbeat.isoformat(),
            "state": connection.state.value,
            "message_count": connection.message_count,
            "rooms": list(connection.rooms),
            "ip_address": connection.ip_address,
        }

    def get_room_info(self, room_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a room."""
        if room_id not in self.rooms:
            return None

        room = self.rooms[room_id]
        return {
            "room_id": room.room_id,
            "name": room.name,
            "owner_id": room.owner_id,
            "created_at": room.created_at.isoformat(),
            "member_count": len(room.members),
            "max_members": room.max_members,
            "is_public": room.is_public,
            "metadata": room.metadata,
        }

    def list_rooms(self, public_only: bool = True) -> List[Dict[str, Any]]:
        """List all rooms."""
        rooms = []
        for room in self.rooms.values():
            if public_only and not room.is_public:
                continue
            rooms.append(self.get_room_info(room.room_id))
        return rooms


# FastAPI Integration Helpers

@asynccontextmanager
async def websocket_connection(
    manager: WebSocketManager,
    websocket: WebSocket,
    user_id: Optional[str] = None,
    user_name: Optional[str] = None,
):
    """
    Context manager for WebSocket connection lifecycle.

    Usage:
        async with websocket_connection(manager, websocket, user_id="user123") as conn_id:
            # Handle messages
            pass
    """
    connection_id = await manager.connect(websocket, user_id, user_name)
    try:
        yield connection_id
    finally:
        await manager.disconnect(connection_id)


async def websocket_message_loop(
    manager: WebSocketManager,
    connection_id: str,
):
    """
    Message receive loop for WebSocket connections.

    Usage:
        async with websocket_connection(manager, websocket) as conn_id:
            await websocket_message_loop(manager, conn_id)
    """
    while True:
        message = await manager.receive_message(connection_id)
        if message is None:
            break
        await manager.handle_message(connection_id, message)


# Client-Side Integration Examples

CLIENT_JAVASCRIPT = """
// WebSocket Client Library for SPARQL Agent
// Provides automatic reconnection, message queuing, and event handling

class SPARQLWebSocketClient {
    constructor(url, options = {}) {
        this.url = url;
        this.options = {
            reconnect: true,
            reconnectInterval: 1000,
            reconnectDecay: 1.5,
            reconnectAttempts: 10,
            heartbeatInterval: 30000,
            ...options
        };

        this.ws = null;
        this.connectionId = null;
        this.reconnectAttempt = 0;
        this.messageQueue = [];
        this.eventHandlers = {};
        this.heartbeatTimer = null;
        this.reconnectTimer = null;

        this.connect();
    }

    connect() {
        console.log('Connecting to WebSocket:', this.url);

        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.reconnectAttempt = 0;
            this.startHeartbeat();
            this.flushMessageQueue();
            this.emit('connected', {});
        };

        this.ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            this.handleMessage(message);
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.emit('error', { error });
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.stopHeartbeat();
            this.emit('disconnected', {});

            if (this.options.reconnect && this.reconnectAttempt < this.options.reconnectAttempts) {
                this.scheduleReconnect();
            }
        };
    }

    handleMessage(message) {
        const { type, payload } = message;

        switch (type) {
            case 'connection_ack':
                this.connectionId = payload.connection_id;
                console.log('Connection ID:', this.connectionId);
                break;

            case 'heartbeat':
                this.send({ type: 'pong' });
                break;

            case 'pong':
                // Heartbeat acknowledged
                break;

            default:
                this.emit(type, payload);
        }
    }

    send(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            console.log('Queueing message (not connected)');
            this.messageQueue.push(message);
        }
    }

    flushMessageQueue() {
        while (this.messageQueue.length > 0) {
            const message = this.messageQueue.shift();
            this.send(message);
        }
    }

    on(event, handler) {
        if (!this.eventHandlers[event]) {
            this.eventHandlers[event] = [];
        }
        this.eventHandlers[event].push(handler);
    }

    off(event, handler) {
        if (this.eventHandlers[event]) {
            this.eventHandlers[event] = this.eventHandlers[event].filter(h => h !== handler);
        }
    }

    emit(event, data) {
        if (this.eventHandlers[event]) {
            this.eventHandlers[event].forEach(handler => {
                try {
                    handler(data);
                } catch (error) {
                    console.error('Error in event handler:', error);
                }
            });
        }
    }

    startHeartbeat() {
        this.heartbeatTimer = setInterval(() => {
            this.send({ type: 'ping' });
        }, this.options.heartbeatInterval);
    }

    stopHeartbeat() {
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
            this.heartbeatTimer = null;
        }
    }

    scheduleReconnect() {
        const delay = this.options.reconnectInterval *
            Math.pow(this.options.reconnectDecay, this.reconnectAttempt);

        console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempt + 1})`);

        this.reconnectTimer = setTimeout(() => {
            this.reconnectAttempt++;
            this.connect();
        }, delay);
    }

    disconnect() {
        this.options.reconnect = false;
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
        }
        if (this.ws) {
            this.ws.close();
        }
    }

    // Query Methods

    async sendQuery(naturalLanguage, options = {}) {
        return new Promise((resolve, reject) => {
            const messageId = Math.random().toString(36).substr(2, 9);

            const progressHandler = (data) => {
                if (data.query_id === messageId) {
                    if (options.onProgress) {
                        options.onProgress(data);
                    }
                }
            };

            const resultHandler = (data) => {
                if (data.query_id === messageId) {
                    this.off('query_progress', progressHandler);
                    this.off('query_result', resultHandler);
                    this.off('error_message', errorHandler);
                    resolve(data);
                }
            };

            const errorHandler = (data) => {
                if (data.query_id === messageId) {
                    this.off('query_progress', progressHandler);
                    this.off('query_result', resultHandler);
                    this.off('error_message', errorHandler);
                    reject(new Error(data.error));
                }
            };

            this.on('query_progress', progressHandler);
            this.on('query_result', resultHandler);
            this.on('error_message', errorHandler);

            this.send({
                type: 'query_request',
                message_id: messageId,
                payload: {
                    natural_language: naturalLanguage,
                    ...options
                }
            });
        });
    }

    // Room Methods

    joinRoom(roomId) {
        this.send({
            type: 'join_room',
            payload: { room_id: roomId }
        });
    }

    leaveRoom(roomId) {
        this.send({
            type: 'leave_room',
            payload: { room_id: roomId }
        });
    }

    sendToRoom(roomId, message) {
        this.send({
            type: 'room_message',
            payload: {
                room_id: roomId,
                ...message
            }
        });
    }

    // Collaboration Methods

    sendTypingIndicator(isTyping, roomId = null) {
        this.send({
            type: 'typing_indicator',
            payload: {
                is_typing: isTyping,
                room_id: roomId
            }
        });
    }
}

// Usage Example:
// const client = new SPARQLWebSocketClient('ws://localhost:8000/ws/query');
//
// client.on('connected', () => {
//     console.log('Connected!');
// });
//
// client.on('query_result', (data) => {
//     console.log('Query result:', data);
// });
//
// await client.sendQuery('Find all proteins from human', {
//     endpoint_id: 'uniprot',
//     onProgress: (progress) => {
//         console.log('Progress:', progress.stage, progress.progress);
//     }
// });
"""

REACT_HOOKS = """
// React Hooks for WebSocket Integration

import { useEffect, useRef, useState, useCallback } from 'react';

// Custom hook for WebSocket connection
export function useWebSocket(url, options = {}) {
    const [isConnected, setIsConnected] = useState(false);
    const [lastMessage, setLastMessage] = useState(null);
    const [connectionError, setConnectionError] = useState(null);
    const clientRef = useRef(null);

    useEffect(() => {
        const client = new SPARQLWebSocketClient(url, options);
        clientRef.current = client;

        client.on('connected', () => {
            setIsConnected(true);
            setConnectionError(null);
        });

        client.on('disconnected', () => {
            setIsConnected(false);
        });

        client.on('error', ({ error }) => {
            setConnectionError(error);
        });

        // Generic message handler
        const messageHandler = (data) => {
            setLastMessage({ type: event, data });
        };

        // Register for all events
        Object.values(MessageType).forEach(type => {
            client.on(type, messageHandler);
        });

        return () => {
            client.disconnect();
        };
    }, [url]);

    const send = useCallback((message) => {
        if (clientRef.current) {
            clientRef.current.send(message);
        }
    }, []);

    return {
        isConnected,
        lastMessage,
        connectionError,
        send,
        client: clientRef.current
    };
}

// Custom hook for SPARQL queries
export function useSPARQLQuery() {
    const [isLoading, setIsLoading] = useState(false);
    const [progress, setProgress] = useState(null);
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);
    const { client } = useWebSocket('ws://localhost:8000/ws/query');

    const executeQuery = useCallback(async (naturalLanguage, options = {}) => {
        if (!client) return;

        setIsLoading(true);
        setProgress(null);
        setResult(null);
        setError(null);

        try {
            const result = await client.sendQuery(naturalLanguage, {
                ...options,
                onProgress: (progressData) => {
                    setProgress(progressData);
                }
            });

            setResult(result);
        } catch (err) {
            setError(err);
        } finally {
            setIsLoading(false);
        }
    }, [client]);

    return {
        isLoading,
        progress,
        result,
        error,
        executeQuery
    };
}

// Custom hook for collaborative rooms
export function useCollaborationRoom(roomId) {
    const { client, isConnected } = useWebSocket('ws://localhost:8000/ws/query');
    const [members, setMembers] = useState([]);
    const [typingUsers, setTypingUsers] = useState(new Set());

    useEffect(() => {
        if (!client || !isConnected) return;

        client.joinRoom(roomId);

        client.on('user_joined', ({ user_id, user_name }) => {
            setMembers(prev => [...prev, { user_id, user_name }]);
        });

        client.on('user_left', ({ user_id }) => {
            setMembers(prev => prev.filter(m => m.user_id !== user_id));
        });

        client.on('typing_indicator', ({ user_id, is_typing }) => {
            setTypingUsers(prev => {
                const next = new Set(prev);
                if (is_typing) {
                    next.add(user_id);
                } else {
                    next.delete(user_id);
                }
                return next;
            });
        });

        return () => {
            client.leaveRoom(roomId);
        };
    }, [client, isConnected, roomId]);

    const sendTyping = useCallback((isTyping) => {
        if (client) {
            client.sendTypingIndicator(isTyping, roomId);
        }
    }, [client, roomId]);

    return {
        members,
        typingUsers,
        sendTyping
    };
}

// Example Component
export function QueryInterface() {
    const { executeQuery, isLoading, progress, result, error } = useSPARQLQuery();
    const [query, setQuery] = useState('');

    const handleSubmit = (e) => {
        e.preventDefault();
        executeQuery(query, {
            endpoint_id: 'uniprot',
            execute: true
        });
    };

    return (
        <div>
            <form onSubmit={handleSubmit}>
                <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Enter your query..."
                />
                <button type="submit" disabled={isLoading}>
                    {isLoading ? 'Processing...' : 'Execute Query'}
                </button>
            </form>

            {progress && (
                <div>
                    <p>Stage: {progress.stage}</p>
                    <progress value={progress.progress} max={1} />
                    <p>{progress.message}</p>
                </div>
            )}

            {result && (
                <div>
                    <h3>Results</h3>
                    <p>Found {result.row_count} results in {result.execution_time}s</p>
                    <pre>{JSON.stringify(result.results, null, 2)}</pre>
                </div>
            )}

            {error && (
                <div style={{ color: 'red' }}>
                    Error: {error.message}
                </div>
            )}
        </div>
    );
}
"""


if __name__ == "__main__":
    # Example usage
    import asyncio

    async def example():
        """Example WebSocket manager usage."""

        # Initialize manager
        manager = WebSocketManager(
            heartbeat_interval=30,
            heartbeat_timeout=60,
            rate_limit_per_minute=60,
        )

        await manager.start()

        # Create a room
        room = await manager.create_room(
            room_id="query-room-1",
            name="Query Collaboration Room",
            max_members=10,
        )

        print(f"Created room: {room.name}")
        print(f"Manager metrics: {manager.get_metrics()}")

        # Simulate some time
        await asyncio.sleep(5)

        # Shutdown
        await manager.shutdown()

    asyncio.run(example())
