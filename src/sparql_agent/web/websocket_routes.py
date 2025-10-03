"""
WebSocket Routes and Integration with FastAPI.

This module provides FastAPI route definitions for WebSocket endpoints,
integrating the WebSocketManager with the SPARQL agent query pipeline.

Features:
- Query WebSocket endpoint with real-time progress
- Collaboration rooms for multi-user query building
- Live ontology suggestions
- Endpoint health monitoring
- Admin WebSocket for system management
"""

import asyncio
import logging
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException
from fastapi.responses import JSONResponse

from .websocket import (
    WebSocketManager,
    MessageType,
    QueryProgress,
    websocket_connection,
    websocket_message_loop,
)


logger = logging.getLogger(__name__)


def create_websocket_routes(
    manager: WebSocketManager,
    generator: Any,
    executor: Any,
    ols_client: Any,
) -> APIRouter:
    """
    Create WebSocket routes integrated with SPARQL agent components.

    Args:
        manager: WebSocket manager instance
        generator: SPARQL generator instance
        executor: Query executor instance
        ols_client: OLS client instance

    Returns:
        FastAPI router with WebSocket endpoints
    """
    router = APIRouter()

    # Register message handlers
    _register_query_handlers(manager, generator, executor)
    _register_ontology_handlers(manager, ols_client)
    _register_collaboration_handlers(manager)

    # WebSocket Endpoints

    @router.websocket("/ws/query")
    async def websocket_query_endpoint(
        websocket: WebSocket,
        user_id: Optional[str] = Query(None),
        user_name: Optional[str] = Query(None),
    ):
        """
        Main WebSocket endpoint for query operations.

        Supports:
        - Real-time query generation and execution
        - Progress updates during query processing
        - Query result streaming
        - Ontology suggestions
        - Error notifications

        Query parameters:
            user_id: Optional user identifier
            user_name: Optional user name

        Message types:
            query_request: Submit a natural language query
            query_cancel: Cancel a running query
            ontology_search: Search for ontology terms
            ping: Heartbeat ping
        """
        async with websocket_connection(manager, websocket, user_id, user_name) as connection_id:
            logger.info(f"Query WebSocket client connected: {connection_id}")

            try:
                await websocket_message_loop(manager, connection_id)
            except Exception as e:
                logger.error(f"Error in query WebSocket loop: {e}")
            finally:
                logger.info(f"Query WebSocket client disconnected: {connection_id}")

    @router.websocket("/ws/room/{room_id}")
    async def websocket_room_endpoint(
        websocket: WebSocket,
        room_id: str,
        user_id: Optional[str] = Query(None),
        user_name: Optional[str] = Query(None),
    ):
        """
        WebSocket endpoint for collaborative rooms.

        Allows multiple users to collaborate on query building in real-time.

        Supports:
        - Room-based messaging
        - Typing indicators
        - Shared query state
        - Member presence

        Path parameters:
            room_id: Room identifier

        Query parameters:
            user_id: Optional user identifier
            user_name: Optional user name
        """
        async with websocket_connection(manager, websocket, user_id, user_name) as connection_id:
            logger.info(f"Room WebSocket client connected to {room_id}: {connection_id}")

            # Join the room
            success = await manager.join_room(connection_id, room_id)

            if not success:
                # Room doesn't exist, try to create it
                try:
                    await manager.create_room(
                        room_id=room_id,
                        name=f"Room {room_id}",
                        owner_id=user_id,
                    )
                    await manager.join_room(connection_id, room_id)
                except Exception as e:
                    logger.error(f"Failed to create/join room {room_id}: {e}")
                    await websocket.close(code=1008, reason="Failed to join room")
                    return

            try:
                await websocket_message_loop(manager, connection_id)
            except Exception as e:
                logger.error(f"Error in room WebSocket loop: {e}")
            finally:
                await manager.leave_room(connection_id, room_id)
                logger.info(f"Room WebSocket client disconnected from {room_id}: {connection_id}")

    @router.websocket("/ws/admin")
    async def websocket_admin_endpoint(
        websocket: WebSocket,
        api_key: Optional[str] = Query(None),
    ):
        """
        Admin WebSocket endpoint for system monitoring and management.

        Requires authentication via API key.

        Supports:
        - Real-time system metrics
        - Connection monitoring
        - Room management
        - Broadcast messages

        Query parameters:
            api_key: Admin API key (required)
        """
        # TODO: Implement proper API key verification
        if not api_key:
            await websocket.close(code=1008, reason="Authentication required")
            return

        async with websocket_connection(manager, websocket, user_id="admin") as connection_id:
            logger.info(f"Admin WebSocket client connected: {connection_id}")

            try:
                while True:
                    message = await manager.receive_message(connection_id)
                    if message is None:
                        break

                    action = message.get("action")

                    if action == "get_metrics":
                        metrics = manager.get_metrics()
                        await manager.send_to_connection(
                            connection_id,
                            {
                                "type": "metrics",
                                "payload": metrics,
                            }
                        )

                    elif action == "list_connections":
                        connections = [
                            manager.get_connection_info(conn_id)
                            for conn_id in manager.connections.keys()
                        ]
                        await manager.send_to_connection(
                            connection_id,
                            {
                                "type": "connections",
                                "payload": {"connections": connections},
                            }
                        )

                    elif action == "list_rooms":
                        rooms = manager.list_rooms(public_only=False)
                        await manager.send_to_connection(
                            connection_id,
                            {
                                "type": "rooms",
                                "payload": {"rooms": rooms},
                            }
                        )

                    elif action == "broadcast":
                        message_payload = message.get("message", {})
                        count = await manager.broadcast(message_payload)
                        await manager.send_to_connection(
                            connection_id,
                            {
                                "type": "broadcast_result",
                                "payload": {"sent_count": count},
                            }
                        )

            except Exception as e:
                logger.error(f"Error in admin WebSocket loop: {e}")
            finally:
                logger.info(f"Admin WebSocket client disconnected: {connection_id}")

    # REST API Endpoints for WebSocket Management

    @router.get("/ws/rooms")
    async def list_rooms():
        """List all public rooms."""
        rooms = manager.list_rooms(public_only=True)
        return {"rooms": rooms}

    @router.post("/ws/rooms")
    async def create_room(
        room_id: str,
        name: str,
        max_members: int = 50,
        is_public: bool = True,
    ):
        """Create a new room."""
        try:
            room = await manager.create_room(
                room_id=room_id,
                name=name,
                max_members=max_members,
                is_public=is_public,
            )
            return manager.get_room_info(room.room_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("/ws/rooms/{room_id}")
    async def get_room(room_id: str):
        """Get room information."""
        room_info = manager.get_room_info(room_id)
        if not room_info:
            raise HTTPException(status_code=404, detail="Room not found")
        return room_info

    @router.delete("/ws/rooms/{room_id}")
    async def delete_room(room_id: str):
        """Delete a room."""
        success = await manager.delete_room(room_id)
        if not success:
            raise HTTPException(status_code=404, detail="Room not found")
        return {"success": True}

    @router.get("/ws/metrics")
    async def get_metrics():
        """Get WebSocket metrics."""
        return manager.get_metrics()

    @router.get("/ws/connections")
    async def list_connections():
        """List all active connections (admin only)."""
        # TODO: Add authentication
        connections = [
            manager.get_connection_info(conn_id)
            for conn_id in manager.connections.keys()
        ]
        return {"connections": connections}

    return router


def _register_query_handlers(
    manager: WebSocketManager,
    generator: Any,
    executor: Any,
) -> None:
    """Register handlers for query-related messages."""

    async def handle_query_request(connection_id: str, message: Dict[str, Any]) -> None:
        """Handle query request message."""
        payload = message.get("payload", {})
        correlation_id = message.get("correlation_id") or message.get("message_id")

        natural_language = payload.get("natural_language")
        if not natural_language:
            await manager.send_to_connection(
                connection_id,
                {
                    "type": MessageType.ERROR_MESSAGE,
                    "correlation_id": correlation_id,
                    "payload": {
                        "error": "natural_language is required",
                    }
                }
            )
            return

        endpoint_url = payload.get("endpoint_url")
        endpoint_id = payload.get("endpoint_id")
        execute = payload.get("execute", True)
        limit = payload.get("limit", 100)
        timeout = payload.get("timeout")

        query_id = correlation_id

        try:
            # Send progress: parsing
            await manager.send_to_connection(
                connection_id,
                {
                    "type": MessageType.QUERY_PROGRESS,
                    "correlation_id": correlation_id,
                    "payload": {
                        "query_id": query_id,
                        "stage": QueryProgress.PARSING,
                        "progress": 0.1,
                        "message": "Parsing natural language query...",
                    }
                }
            )

            # Send progress: generating
            await manager.send_to_connection(
                connection_id,
                {
                    "type": MessageType.QUERY_PROGRESS,
                    "correlation_id": correlation_id,
                    "payload": {
                        "query_id": query_id,
                        "stage": QueryProgress.GENERATING,
                        "progress": 0.3,
                        "message": "Generating SPARQL query...",
                    }
                }
            )

            # Generate query
            start_time = time.time()

            generated = generator.generate(
                natural_language=natural_language,
                constraints={"limit": limit} if limit else {},
            )

            # Send progress: validating
            await manager.send_to_connection(
                connection_id,
                {
                    "type": MessageType.QUERY_PROGRESS,
                    "correlation_id": correlation_id,
                    "payload": {
                        "query_id": query_id,
                        "stage": QueryProgress.VALIDATING,
                        "progress": 0.5,
                        "message": "Validating generated query...",
                    }
                }
            )

            # Execute if requested
            result_data = None
            execution_time = None
            row_count = None

            if execute and (endpoint_url or endpoint_id):
                # Send progress: executing
                await manager.send_to_connection(
                    connection_id,
                    {
                        "type": MessageType.QUERY_PROGRESS,
                        "correlation_id": correlation_id,
                        "payload": {
                            "query_id": query_id,
                            "stage": QueryProgress.EXECUTING,
                            "progress": 0.7,
                            "message": "Executing query...",
                        }
                    }
                )

                # Import here to avoid circular dependency
                from ..core.types import EndpointInfo

                endpoint = EndpointInfo(
                    url=endpoint_url if endpoint_url else f"https://sparql.{endpoint_id}.org/sparql",
                    timeout=timeout or 60,
                )

                result = executor.execute(
                    query=generated.query,
                    endpoint=endpoint,
                )

                execution_time = result.execution_time
                row_count = result.row_count

                result_data = {
                    "bindings": result.bindings[:100],  # Limit for WebSocket
                    "variables": result.variables,
                    "row_count": result.row_count,
                }

            # Send progress: formatting
            await manager.send_to_connection(
                connection_id,
                {
                    "type": MessageType.QUERY_PROGRESS,
                    "correlation_id": correlation_id,
                    "payload": {
                        "query_id": query_id,
                        "stage": QueryProgress.FORMATTING,
                        "progress": 0.9,
                        "message": "Formatting results...",
                    }
                }
            )

            total_time = time.time() - start_time

            # Send result
            await manager.send_to_connection(
                connection_id,
                {
                    "type": MessageType.QUERY_RESULT,
                    "correlation_id": correlation_id,
                    "payload": {
                        "query_id": query_id,
                        "query": generated.query,
                        "results": result_data,
                        "execution_time": execution_time or total_time,
                        "row_count": row_count,
                        "explanation": generated.explanation,
                        "confidence": generated.confidence,
                    }
                }
            )

            # Send progress: completed
            await manager.send_to_connection(
                connection_id,
                {
                    "type": MessageType.QUERY_PROGRESS,
                    "correlation_id": correlation_id,
                    "payload": {
                        "query_id": query_id,
                        "stage": QueryProgress.COMPLETED,
                        "progress": 1.0,
                        "message": "Query completed successfully",
                    }
                }
            )

        except Exception as e:
            logger.error(f"Error processing query request: {e}")

            # Send error
            await manager.send_to_connection(
                connection_id,
                {
                    "type": MessageType.ERROR_MESSAGE,
                    "correlation_id": correlation_id,
                    "payload": {
                        "query_id": query_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    }
                }
            )

            # Send progress: failed
            await manager.send_to_connection(
                connection_id,
                {
                    "type": MessageType.QUERY_PROGRESS,
                    "correlation_id": correlation_id,
                    "payload": {
                        "query_id": query_id,
                        "stage": QueryProgress.FAILED,
                        "progress": 0.0,
                        "message": f"Query failed: {str(e)}",
                    }
                }
            )

    manager.register_handler(MessageType.QUERY_REQUEST, handle_query_request)


def _register_ontology_handlers(
    manager: WebSocketManager,
    ols_client: Any,
) -> None:
    """Register handlers for ontology-related messages."""

    async def handle_ontology_search(connection_id: str, message: Dict[str, Any]) -> None:
        """Handle ontology search message."""
        payload = message.get("payload", {})
        correlation_id = message.get("correlation_id") or message.get("message_id")

        query = payload.get("query")
        ontology = payload.get("ontology")
        limit = payload.get("limit", 10)

        if not query:
            await manager.send_to_connection(
                connection_id,
                {
                    "type": MessageType.ERROR_MESSAGE,
                    "correlation_id": correlation_id,
                    "payload": {
                        "error": "query is required",
                    }
                }
            )
            return

        try:
            results = ols_client.search(
                query=query,
                ontology=ontology,
                limit=limit,
            )

            await manager.send_to_connection(
                connection_id,
                {
                    "type": MessageType.ONTOLOGY_SUGGESTION,
                    "correlation_id": correlation_id,
                    "payload": {
                        "query_text": query,
                        "suggestions": results,
                    }
                }
            )

        except Exception as e:
            logger.error(f"Error processing ontology search: {e}")

            await manager.send_to_connection(
                connection_id,
                {
                    "type": MessageType.ERROR_MESSAGE,
                    "correlation_id": correlation_id,
                    "payload": {
                        "error": str(e),
                        "error_type": type(e).__name__,
                    }
                }
            )

    manager.register_handler(MessageType.ONTOLOGY_SEARCH, handle_ontology_search)


def _register_collaboration_handlers(manager: WebSocketManager) -> None:
    """Register handlers for collaboration messages."""

    async def handle_typing_indicator(connection_id: str, message: Dict[str, Any]) -> None:
        """Handle typing indicator message."""
        payload = message.get("payload", {})

        connection = manager.connections.get(connection_id)
        if not connection:
            return

        is_typing = payload.get("is_typing", False)
        room_id = payload.get("room_id")

        # Broadcast typing indicator
        if room_id and room_id in connection.rooms:
            # Send to room
            await manager.send_to_room(
                room_id,
                {
                    "type": MessageType.TYPING_INDICATOR,
                    "payload": {
                        "user_id": connection.user_id,
                        "user_name": connection.user_name,
                        "is_typing": is_typing,
                        "room_id": room_id,
                    }
                },
                exclude_connection=connection_id,
            )

    async def handle_room_message(connection_id: str, message: Dict[str, Any]) -> None:
        """Handle room message broadcast."""
        payload = message.get("payload", {})

        connection = manager.connections.get(connection_id)
        if not connection:
            return

        room_id = payload.get("room_id")
        if not room_id or room_id not in connection.rooms:
            return

        # Broadcast to room
        await manager.send_to_room(
            room_id,
            {
                "type": MessageType.ROOM_MESSAGE,
                "payload": {
                    "room_id": room_id,
                    "user_id": connection.user_id,
                    "user_name": connection.user_name,
                    "message": payload.get("message"),
                    "timestamp": time.time(),
                }
            },
            exclude_connection=connection_id,
        )

    manager.register_handler(MessageType.TYPING_INDICATOR, handle_typing_indicator)
    manager.register_handler(MessageType.ROOM_MESSAGE, handle_room_message)


# Monitoring and Health Check

async def websocket_health_check(manager: WebSocketManager) -> Dict[str, Any]:
    """
    Perform WebSocket health check.

    Returns:
        Health status information
    """
    metrics = manager.get_metrics()

    return {
        "status": "healthy" if metrics["active_connections"] >= 0 else "unhealthy",
        "active_connections": metrics["active_connections"],
        "active_rooms": metrics["active_rooms"],
        "total_connections": metrics["total_connections"],
        "total_messages_sent": metrics["total_messages_sent"],
        "total_messages_received": metrics["total_messages_received"],
    }
