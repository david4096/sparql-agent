"""
WebSocket Examples and Usage Demonstrations.

This module provides comprehensive examples of using the WebSocket system
for real-time SPARQL query processing and collaboration.

Examples:
1. Basic WebSocket connection and query execution
2. Real-time progress tracking
3. Collaborative room usage
4. Advanced features (reconnection, message queuing, etc.)
5. Production deployment patterns
"""

import asyncio
import logging
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .websocket import WebSocketManager
from .websocket_routes import create_websocket_routes


logger = logging.getLogger(__name__)


# Example 1: Basic WebSocket Integration with FastAPI

def create_websocket_app() -> FastAPI:
    """
    Create a FastAPI application with WebSocket support.

    This example shows how to integrate the WebSocket manager
    with an existing FastAPI application.

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="SPARQL Agent with WebSocket",
        description="Real-time SPARQL query processing with WebSocket support",
        version="1.0.0",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialize WebSocket manager
    ws_manager = WebSocketManager(
        heartbeat_interval=30,
        heartbeat_timeout=60,
        rate_limit_per_minute=60,
        enable_message_persistence=True,
        enable_rooms=True,
    )

    # Store manager in app state
    app.state.ws_manager = ws_manager

    # Initialize components (mock for example)
    # In production, these would be your actual components
    from unittest.mock import Mock

    generator = Mock()
    executor = Mock()
    ols_client = Mock()

    # Create and include WebSocket routes
    ws_router = create_websocket_routes(
        manager=ws_manager,
        generator=generator,
        executor=executor,
        ols_client=ols_client,
    )

    app.include_router(ws_router, prefix="/api", tags=["WebSocket"])

    # Startup and shutdown events
    @app.on_event("startup")
    async def startup_event():
        """Start WebSocket manager on application startup."""
        await ws_manager.start()
        logger.info("WebSocket manager started")

    @app.on_event("shutdown")
    async def shutdown_event():
        """Shutdown WebSocket manager on application shutdown."""
        await ws_manager.shutdown()
        logger.info("WebSocket manager shutdown complete")

    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "name": "SPARQL Agent WebSocket API",
            "version": "1.0.0",
            "websocket_endpoints": [
                "/api/ws/query",
                "/api/ws/room/{room_id}",
                "/api/ws/admin",
            ],
            "rest_endpoints": [
                "/api/ws/rooms",
                "/api/ws/metrics",
            ],
        }

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        from .websocket_routes import websocket_health_check

        health = await websocket_health_check(ws_manager)
        return health

    return app


# Example 2: Client Usage with asyncio

async def example_websocket_client():
    """
    Example WebSocket client using Python asyncio.

    This demonstrates how to connect to the WebSocket API
    and send/receive messages programmatically.
    """
    import websockets
    import json

    uri = "ws://localhost:8000/api/ws/query?user_id=example_user"

    async with websockets.connect(uri) as websocket:
        print("Connected to WebSocket")

        # Receive connection acknowledgment
        ack = await websocket.recv()
        print(f"Received: {ack}")

        # Send a query request
        query_request = {
            "type": "query_request",
            "message_id": "example-query-1",
            "payload": {
                "natural_language": "Find all proteins from human",
                "endpoint_id": "uniprot",
                "execute": True,
                "limit": 10,
            }
        }

        await websocket.send(json.dumps(query_request))
        print(f"Sent query: {query_request['payload']['natural_language']}")

        # Receive messages
        while True:
            try:
                message = await websocket.recv()
                data = json.loads(message)

                msg_type = data.get("type")

                if msg_type == "query_progress":
                    progress = data["payload"]
                    print(f"Progress: {progress['stage']} - {progress['message']} ({progress['progress']*100:.0f}%)")

                elif msg_type == "query_result":
                    result = data["payload"]
                    print(f"\nQuery Result:")
                    print(f"  SPARQL: {result['query']}")
                    print(f"  Rows: {result['row_count']}")
                    print(f"  Time: {result['execution_time']:.2f}s")
                    print(f"  Confidence: {result['confidence']:.2%}")
                    break

                elif msg_type == "error_message":
                    error = data["payload"]
                    print(f"Error: {error['error']}")
                    break

                elif msg_type == "heartbeat":
                    # Respond to heartbeat
                    await websocket.send(json.dumps({"type": "pong"}))

            except websockets.exceptions.ConnectionClosed:
                print("Connection closed")
                break


# Example 3: Collaborative Room Usage

async def example_collaborative_room():
    """
    Example of using collaborative rooms for multi-user query building.

    This demonstrates how multiple users can collaborate in real-time
    on building and executing SPARQL queries.
    """
    import websockets
    import json

    room_id = "example-room-1"
    uri = f"ws://localhost:8000/api/ws/room/{room_id}?user_id=user1&user_name=Alice"

    async with websockets.connect(uri) as websocket:
        print(f"Connected to room: {room_id}")

        # Message handler
        async def handle_messages():
            while True:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)

                    msg_type = data.get("type")

                    if msg_type == "user_joined":
                        payload = data["payload"]
                        print(f"User joined: {payload['user_name']} (members: {payload['member_count']})")

                    elif msg_type == "user_left":
                        payload = data["payload"]
                        print(f"User left: {payload['user_name']} (members: {payload['member_count']})")

                    elif msg_type == "typing_indicator":
                        payload = data["payload"]
                        if payload["is_typing"]:
                            print(f"{payload['user_name']} is typing...")

                    elif msg_type == "room_message":
                        payload = data["payload"]
                        print(f"{payload['user_name']}: {payload['message']}")

                except websockets.exceptions.ConnectionClosed:
                    break

        # Message sender
        async def send_messages():
            await asyncio.sleep(2)

            # Send typing indicator
            await websocket.send(json.dumps({
                "type": "typing_indicator",
                "payload": {
                    "is_typing": True,
                    "room_id": room_id,
                }
            }))

            await asyncio.sleep(1)

            # Send room message
            await websocket.send(json.dumps({
                "type": "room_message",
                "payload": {
                    "room_id": room_id,
                    "message": "Hello everyone!",
                }
            }))

            # Stop typing
            await websocket.send(json.dumps({
                "type": "typing_indicator",
                "payload": {
                    "is_typing": False,
                    "room_id": room_id,
                }
            }))

        # Run concurrently
        await asyncio.gather(
            handle_messages(),
            send_messages(),
        )


# Example 4: Advanced Features Demo

async def example_advanced_features():
    """
    Demonstration of advanced WebSocket features:
    - Automatic reconnection
    - Message queuing
    - Rate limiting
    - Connection pooling
    """
    import websockets
    import json
    from websockets.exceptions import ConnectionClosed

    class ResilientWebSocketClient:
        """WebSocket client with automatic reconnection."""

        def __init__(self, uri: str, max_reconnect_attempts: int = 10):
            self.uri = uri
            self.max_reconnect_attempts = max_reconnect_attempts
            self.websocket: Optional[websockets.WebSocketClientProtocol] = None
            self.reconnect_attempt = 0
            self.message_queue = []
            self.connected = False

        async def connect(self):
            """Connect with exponential backoff."""
            while self.reconnect_attempt < self.max_reconnect_attempts:
                try:
                    print(f"Connecting to {self.uri} (attempt {self.reconnect_attempt + 1})")
                    self.websocket = await websockets.connect(self.uri)
                    self.connected = True
                    self.reconnect_attempt = 0
                    print("Connected successfully")

                    # Flush queued messages
                    await self.flush_queue()

                    return

                except Exception as e:
                    self.reconnect_attempt += 1
                    backoff = min(2 ** self.reconnect_attempt, 60)
                    print(f"Connection failed: {e}. Retrying in {backoff}s...")
                    await asyncio.sleep(backoff)

            raise ConnectionError("Max reconnection attempts reached")

        async def send(self, message: dict):
            """Send message with queuing for offline state."""
            if self.connected and self.websocket:
                try:
                    await self.websocket.send(json.dumps(message))
                except ConnectionClosed:
                    self.connected = False
                    self.message_queue.append(message)
                    await self.connect()
            else:
                self.message_queue.append(message)

        async def flush_queue(self):
            """Send all queued messages."""
            while self.message_queue and self.websocket:
                message = self.message_queue.pop(0)
                await self.websocket.send(json.dumps(message))

        async def receive(self):
            """Receive message with reconnection handling."""
            if not self.websocket:
                await self.connect()

            try:
                message = await self.websocket.recv()
                return json.loads(message)
            except ConnectionClosed:
                self.connected = False
                await self.connect()
                return None

        async def close(self):
            """Close connection."""
            if self.websocket:
                await self.websocket.close()
                self.connected = False

    # Usage
    client = ResilientWebSocketClient("ws://localhost:8000/api/ws/query?user_id=resilient_user")

    await client.connect()

    # Send queries
    for i in range(5):
        await client.send({
            "type": "query_request",
            "message_id": f"query-{i}",
            "payload": {
                "natural_language": f"Example query {i}",
                "endpoint_id": "uniprot",
            }
        })

        # Receive response
        response = await client.receive()
        if response:
            print(f"Response {i}: {response.get('type')}")

    await client.close()


# Example 5: Production Deployment with Load Balancing

class ProductionWebSocketDeployment:
    """
    Production deployment pattern for WebSocket system.

    Features:
    - Redis pub/sub for multi-instance scaling
    - Connection pooling
    - Monitoring and metrics
    - Health checks
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        enable_redis: bool = False,
    ):
        """
        Initialize production deployment.

        Args:
            redis_url: Redis connection URL for pub/sub
            enable_redis: Enable Redis for cross-instance messaging
        """
        self.redis_url = redis_url
        self.enable_redis = enable_redis
        self.manager: Optional[WebSocketManager] = None

        if enable_redis:
            self._setup_redis()

    def _setup_redis(self):
        """Set up Redis pub/sub for cross-instance messaging."""
        try:
            import redis.asyncio as redis

            self.redis = redis.from_url(self.redis_url)
            self.pubsub = self.redis.pubsub()
            logger.info("Redis pub/sub initialized")

        except ImportError:
            logger.warning("redis package not installed, disabling Redis support")
            self.enable_redis = False

    async def start(self):
        """Start production deployment."""
        # Initialize WebSocket manager
        self.manager = WebSocketManager(
            heartbeat_interval=30,
            heartbeat_timeout=90,
            rate_limit_per_minute=100,
            enable_message_persistence=True,
            enable_rooms=True,
        )

        await self.manager.start()

        # Subscribe to Redis channels if enabled
        if self.enable_redis:
            await self._subscribe_redis_channels()

        logger.info("Production WebSocket deployment started")

    async def _subscribe_redis_channels(self):
        """Subscribe to Redis channels for cross-instance messaging."""
        await self.pubsub.subscribe("websocket:broadcast")

        # Background task to handle Redis messages
        asyncio.create_task(self._redis_message_handler())

    async def _redis_message_handler(self):
        """Handle messages from Redis pub/sub."""
        import json

        async for message in self.pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    # Broadcast to local connections
                    await self.manager.broadcast(data)
                except Exception as e:
                    logger.error(f"Error handling Redis message: {e}")

    async def broadcast_via_redis(self, message: dict):
        """Broadcast message via Redis to all instances."""
        if self.enable_redis:
            import json
            await self.redis.publish("websocket:broadcast", json.dumps(message))

    async def shutdown(self):
        """Shutdown production deployment."""
        if self.manager:
            await self.manager.shutdown()

        if self.enable_redis:
            await self.pubsub.unsubscribe()
            await self.redis.close()

        logger.info("Production WebSocket deployment shutdown complete")


# Example 6: Complete Integration Example

async def complete_integration_example():
    """
    Complete example showing all features working together.

    This demonstrates a realistic scenario of:
    1. Starting the WebSocket server
    2. Connecting multiple clients
    3. Creating a collaborative room
    4. Executing queries with real-time progress
    5. Broadcasting system messages
    """
    print("Starting complete integration example...\n")

    # Create FastAPI app with WebSocket support
    app = create_websocket_app()

    # Note: In production, you would run this with uvicorn:
    # uvicorn websocket_examples:app --reload --port 8000

    print("Server would be started with:")
    print("  uvicorn sparql_agent.web.websocket_examples:app --reload --port 8000")
    print("\nClient examples:")
    print("  1. Basic query execution")
    print("  2. Collaborative room usage")
    print("  3. Advanced features (reconnection, queuing)")
    print("\nRun the individual example functions to see them in action:")
    print("  await example_websocket_client()")
    print("  await example_collaborative_room()")
    print("  await example_advanced_features()")


# Example 7: Testing WebSocket Endpoints

async def test_websocket_endpoints():
    """
    Example test cases for WebSocket endpoints.

    This shows how to test WebSocket functionality
    in unit tests and integration tests.
    """
    from fastapi.testclient import TestClient

    app = create_websocket_app()
    client = TestClient(app)

    # Test REST endpoints
    response = client.get("/health")
    assert response.status_code == 200
    print(f"Health check: {response.json()}")

    response = client.get("/api/ws/rooms")
    assert response.status_code == 200
    print(f"Rooms list: {response.json()}")

    # Create a room
    response = client.post(
        "/api/ws/rooms",
        params={
            "room_id": "test-room",
            "name": "Test Room",
            "max_members": 10,
        }
    )
    assert response.status_code == 200
    print(f"Created room: {response.json()}")

    # Get room info
    response = client.get("/api/ws/rooms/test-room")
    assert response.status_code == 200
    print(f"Room info: {response.json()}")

    # Get metrics
    response = client.get("/api/ws/metrics")
    assert response.status_code == 200
    print(f"Metrics: {response.json()}")

    print("\nAll tests passed!")


# Main execution

if __name__ == "__main__":
    """
    Run examples.

    Usage:
        python -m sparql_agent.web.websocket_examples
    """
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    print("SPARQL Agent WebSocket Examples")
    print("=" * 50)
    print("\nAvailable examples:")
    print("  1. Create WebSocket app")
    print("  2. WebSocket client")
    print("  3. Collaborative room")
    print("  4. Advanced features")
    print("  5. Production deployment")
    print("  6. Complete integration")
    print("  7. Test endpoints")
    print("\nTo run examples:")
    print("  python -m sparql_agent.web.websocket_examples <example_number>")
    print("\nOr import and use in your code:")
    print("  from sparql_agent.web.websocket_examples import create_websocket_app")
    print("  app = create_websocket_app()")
    print("  # Run with: uvicorn app:app --reload")

    if len(sys.argv) > 1:
        example_num = int(sys.argv[1])

        if example_num == 1:
            app = create_websocket_app()
            print("\nFastAPI app created!")
            print("Run with: uvicorn sparql_agent.web.websocket_examples:app --reload")

        elif example_num == 2:
            asyncio.run(example_websocket_client())

        elif example_num == 3:
            asyncio.run(example_collaborative_room())

        elif example_num == 4:
            asyncio.run(example_advanced_features())

        elif example_num == 5:
            deployment = ProductionWebSocketDeployment(
                redis_url="redis://localhost:6379",
                enable_redis=False,
            )
            asyncio.run(deployment.start())
            print("Production deployment started (press Ctrl+C to stop)")
            try:
                asyncio.get_event_loop().run_forever()
            except KeyboardInterrupt:
                asyncio.run(deployment.shutdown())

        elif example_num == 6:
            asyncio.run(complete_integration_example())

        elif example_num == 7:
            asyncio.run(test_websocket_endpoints())

        else:
            print(f"Unknown example number: {example_num}")
