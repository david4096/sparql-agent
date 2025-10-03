# WebSocket Real-Time Communication System

Complete WebSocket infrastructure for real-time SPARQL query processing and collaboration.

## Overview

The WebSocket system provides real-time bidirectional communication between clients and the SPARQL agent server, enabling:

- **Real-time query execution** with live progress updates
- **Collaborative query building** with multiple users
- **Live ontology suggestions** as users type
- **Endpoint health monitoring** with automatic status updates
- **Message persistence** for offline clients
- **Automatic reconnection** with exponential backoff
- **Rate limiting** to prevent abuse
- **Room-based messaging** for team collaboration

## Architecture

### Components

1. **WebSocketManager** (`websocket.py`)
   - Core WebSocket connection management
   - Message routing and broadcasting
   - Room management
   - Rate limiting and authentication
   - Heartbeat mechanism
   - Message queuing

2. **WebSocket Routes** (`websocket_routes.py`)
   - FastAPI WebSocket endpoints
   - Integration with SPARQL components
   - Message handlers
   - REST API for WebSocket management

3. **Client Libraries** (JavaScript/React)
   - Automatic reconnection
   - Message queuing
   - Event-driven architecture
   - React hooks for easy integration

## Quick Start

### Server Setup

```python
from fastapi import FastAPI
from sparql_agent.web.websocket import WebSocketManager
from sparql_agent.web.websocket_routes import create_websocket_routes

# Initialize FastAPI app
app = FastAPI()

# Initialize WebSocket manager
ws_manager = WebSocketManager(
    heartbeat_interval=30,
    heartbeat_timeout=60,
    rate_limit_per_minute=60,
)

# Create routes
ws_router = create_websocket_routes(
    manager=ws_manager,
    generator=sparql_generator,  # Your SPARQLGenerator instance
    executor=query_executor,     # Your QueryExecutor instance
    ols_client=ols_client,       # Your OLSClient instance
)

app.include_router(ws_router, prefix="/api")

# Start/stop manager with app lifecycle
@app.on_event("startup")
async def startup():
    await ws_manager.start()

@app.on_event("shutdown")
async def shutdown():
    await ws_manager.shutdown()
```

### Client Setup (JavaScript)

```javascript
// Initialize WebSocket client
const client = new SPARQLWebSocketClient('ws://localhost:8000/api/ws/query');

// Listen for connection
client.on('connected', () => {
    console.log('Connected!');
});

// Listen for query results
client.on('query_result', (data) => {
    console.log('Results:', data);
});

// Send a query
await client.sendQuery('Find all proteins from human', {
    endpoint_id: 'uniprot',
    execute: true,
    onProgress: (progress) => {
        console.log(`${progress.stage}: ${progress.progress * 100}%`);
    }
});
```

### Client Setup (React)

```jsx
import { useSPARQLQuery } from './hooks';

function QueryInterface() {
    const { executeQuery, isLoading, progress, result, error } = useSPARQLQuery();

    return (
        <div>
            <button onClick={() => executeQuery('Find all proteins from human')}>
                Execute Query
            </button>

            {progress && <Progress value={progress.progress} />}
            {result && <Results data={result} />}
            {error && <Error message={error.message} />}
        </div>
    );
}
```

## WebSocket Endpoints

### Main Query Endpoint

**URL:** `ws://localhost:8000/api/ws/query`

**Query Parameters:**
- `user_id` (optional): User identifier
- `user_name` (optional): User display name

**Supported Message Types:**

#### Client → Server

##### `query_request`
Execute a natural language query.

```json
{
    "type": "query_request",
    "message_id": "unique-id",
    "payload": {
        "natural_language": "Find all proteins from human",
        "endpoint_id": "uniprot",
        "execute": true,
        "limit": 100,
        "timeout": 60
    }
}
```

##### `ontology_search`
Search for ontology terms.

```json
{
    "type": "ontology_search",
    "message_id": "unique-id",
    "payload": {
        "query": "protein",
        "ontology": "PR",
        "limit": 10
    }
}
```

##### `ping`
Heartbeat ping.

```json
{
    "type": "ping"
}
```

#### Server → Client

##### `connection_ack`
Connection acknowledgment with connection details.

```json
{
    "type": "connection_ack",
    "payload": {
        "connection_id": "abc123",
        "user_id": "user123",
        "server_time": "2025-10-02T12:00:00",
        "heartbeat_interval": 30
    }
}
```

##### `query_progress`
Real-time query execution progress.

```json
{
    "type": "query_progress",
    "correlation_id": "unique-id",
    "payload": {
        "query_id": "query123",
        "stage": "generating",
        "progress": 0.5,
        "message": "Generating SPARQL query..."
    }
}
```

Progress stages:
- `parsing` - Parsing natural language
- `validating` - Validating query
- `generating` - Generating SPARQL
- `optimizing` - Optimizing query
- `executing` - Executing query
- `formatting` - Formatting results
- `completed` - Successfully completed
- `failed` - Query failed

##### `query_result`
Final query result.

```json
{
    "type": "query_result",
    "correlation_id": "unique-id",
    "payload": {
        "query_id": "query123",
        "query": "SELECT ?protein WHERE { ... }",
        "results": {
            "bindings": [...],
            "variables": ["protein"],
            "row_count": 42
        },
        "execution_time": 1.23,
        "confidence": 0.95,
        "explanation": "This query finds all proteins..."
    }
}
```

##### `ontology_suggestion`
Ontology term suggestions.

```json
{
    "type": "ontology_suggestion",
    "correlation_id": "unique-id",
    "payload": {
        "query_text": "protein",
        "suggestions": [
            {
                "iri": "http://purl.obolibrary.org/obo/PR_000000001",
                "label": "protein",
                "description": "A biological macromolecule..."
            }
        ]
    }
}
```

##### `error_message`
Error notification.

```json
{
    "type": "error_message",
    "correlation_id": "unique-id",
    "payload": {
        "error": "Query execution failed",
        "error_type": "QueryExecutionError"
    }
}
```

##### `heartbeat`
Server heartbeat.

```json
{
    "type": "heartbeat",
    "payload": {
        "timestamp": "2025-10-02T12:00:00"
    }
}
```

### Collaboration Room Endpoint

**URL:** `ws://localhost:8000/api/ws/room/{room_id}`

**Path Parameters:**
- `room_id`: Room identifier

**Query Parameters:**
- `user_id` (optional): User identifier
- `user_name` (optional): User display name

**Additional Message Types:**

##### `user_joined`
User joined the room.

```json
{
    "type": "user_joined",
    "payload": {
        "room_id": "room1",
        "user_id": "user123",
        "user_name": "Alice",
        "member_count": 3
    }
}
```

##### `user_left`
User left the room.

```json
{
    "type": "user_left",
    "payload": {
        "room_id": "room1",
        "user_id": "user123",
        "member_count": 2
    }
}
```

##### `typing_indicator`
User typing status.

```json
{
    "type": "typing_indicator",
    "payload": {
        "user_id": "user123",
        "user_name": "Alice",
        "is_typing": true,
        "room_id": "room1"
    }
}
```

##### `room_message`
Broadcast message to room.

```json
{
    "type": "room_message",
    "payload": {
        "room_id": "room1",
        "user_id": "user123",
        "user_name": "Alice",
        "message": "Check out this query!",
        "timestamp": 1696248000
    }
}
```

### Admin Endpoint

**URL:** `ws://localhost:8000/api/ws/admin`

**Query Parameters:**
- `api_key` (required): Admin API key

**Admin Actions:**

```json
{
    "action": "get_metrics"
}

{
    "action": "list_connections"
}

{
    "action": "list_rooms"
}

{
    "action": "broadcast",
    "message": {
        "type": "system_message",
        "payload": {
            "message": "System maintenance in 5 minutes"
        }
    }
}
```

## REST API Endpoints

### List Rooms

```http
GET /api/ws/rooms
```

Response:
```json
{
    "rooms": [
        {
            "room_id": "room1",
            "name": "Query Lab",
            "member_count": 3,
            "max_members": 10,
            "is_public": true
        }
    ]
}
```

### Create Room

```http
POST /api/ws/rooms?room_id=room1&name=Query%20Lab&max_members=10
```

Response:
```json
{
    "room_id": "room1",
    "name": "Query Lab",
    "owner_id": null,
    "created_at": "2025-10-02T12:00:00",
    "member_count": 0,
    "max_members": 10,
    "is_public": true
}
```

### Get Room Info

```http
GET /api/ws/rooms/room1
```

### Delete Room

```http
DELETE /api/ws/rooms/room1
```

### Get Metrics

```http
GET /api/ws/metrics
```

Response:
```json
{
    "total_connections": 1234,
    "active_connections": 42,
    "active_rooms": 5,
    "total_messages_sent": 5678,
    "total_messages_received": 5432,
    "queued_messages": 10,
    "rate_limit_violations": 3
}
```

### List Connections (Admin)

```http
GET /api/ws/connections
```

## Features

### 1. Connection Management

```python
# Server-side
manager = WebSocketManager()

# Connect a client
connection_id = await manager.connect(websocket, user_id="user123")

# Disconnect
await manager.disconnect(connection_id)

# Get connection info
info = manager.get_connection_info(connection_id)
```

### 2. Message Broadcasting

```python
# Send to specific connection
await manager.send_to_connection(connection_id, message)

# Send to specific user (all their connections)
await manager.send_to_user(user_id, message)

# Send to room
await manager.send_to_room(room_id, message)

# Broadcast to all
await manager.broadcast(message)
```

### 3. Room Management

```python
# Create room
room = await manager.create_room(
    room_id="query-lab",
    name="Query Lab",
    max_members=10,
)

# Join room
await manager.join_room(connection_id, room_id)

# Leave room
await manager.leave_room(connection_id, room_id)

# Delete room
await manager.delete_room(room_id)
```

### 4. Rate Limiting

Automatic token bucket rate limiting per connection:
- Configurable messages per minute
- Automatic token refill
- Error messages on limit exceeded

### 5. Message Persistence

Messages are queued for offline users:
- Configurable queue size (default: 100 messages)
- Automatic delivery on reconnection
- TTL-based cleanup

### 6. Heartbeat Mechanism

Automatic connection health monitoring:
- Periodic heartbeat checks (default: 30s)
- Timeout detection (default: 60s)
- Automatic disconnection of dead connections

### 7. Automatic Reconnection (Client)

Client-side reconnection with exponential backoff:
- Configurable max attempts
- Exponential backoff with decay
- Message queue during disconnection

## Client Libraries

### JavaScript WebSocket Client

Complete client implementation with:
- Automatic reconnection
- Message queuing
- Event handlers
- Heartbeat management

See `CLIENT_JAVASCRIPT` constant in `websocket.py` for full implementation.

### React Hooks

Pre-built React hooks for common use cases:
- `useWebSocket` - Basic WebSocket connection
- `useSPARQLQuery` - Query execution with progress
- `useCollaborationRoom` - Room-based collaboration

See `REACT_HOOKS` constant in `websocket.py` for full implementation.

## Production Deployment

### Redis Integration

For multi-instance deployments, use Redis pub/sub:

```python
from sparql_agent.web.websocket_examples import ProductionWebSocketDeployment

deployment = ProductionWebSocketDeployment(
    redis_url="redis://localhost:6379",
    enable_redis=True,
)

await deployment.start()

# Broadcast across all instances
await deployment.broadcast_via_redis({
    "type": "system_message",
    "payload": {"message": "Update deployed"}
})
```

### Load Balancing

Configure sticky sessions for WebSocket connections:

**Nginx:**
```nginx
upstream websocket {
    ip_hash;  # Sticky sessions
    server backend1:8000;
    server backend2:8000;
    server backend3:8000;
}

server {
    location /api/ws/ {
        proxy_pass http://websocket;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 3600s;
    }
}
```

### Monitoring

Monitor WebSocket health:

```python
# Get metrics
metrics = manager.get_metrics()

# Health check
from sparql_agent.web.websocket_routes import websocket_health_check
health = await websocket_health_check(manager)
```

Key metrics to monitor:
- Active connections
- Message throughput (sent/received per second)
- Rate limit violations
- Connection errors
- Average connection duration
- Room utilization

### Security Considerations

1. **Authentication**: Implement proper authentication before accepting connections
2. **Rate Limiting**: Tune rate limits based on your use case
3. **Message Validation**: Validate all incoming messages
4. **Connection Limits**: Set max connections per user/IP
5. **CORS**: Configure CORS appropriately for production
6. **TLS**: Use WSS (WebSocket Secure) in production

## Examples

Complete examples are provided in `websocket_examples.py`:

1. **Basic WebSocket Client**: Simple connection and query execution
2. **Collaborative Room**: Multi-user collaboration example
3. **Advanced Features**: Reconnection, queuing, rate limiting
4. **Production Deployment**: Redis integration, load balancing
5. **Complete Integration**: Full-featured example
6. **Testing**: Test cases for WebSocket functionality

Run examples:
```bash
python -m sparql_agent.web.websocket_examples 1  # Create app
python -m sparql_agent.web.websocket_examples 2  # WebSocket client
python -m sparql_agent.web.websocket_examples 3  # Collaborative room
```

## Troubleshooting

### Connection Issues

**Problem**: Client can't connect
- Check CORS configuration
- Verify WebSocket URL scheme (ws:// or wss://)
- Check firewall rules
- Verify WebSocket upgrade headers

**Problem**: Frequent disconnections
- Increase heartbeat timeout
- Check network stability
- Verify rate limit settings

### Performance Issues

**Problem**: High latency
- Enable message compression
- Optimize message size
- Check network bandwidth
- Consider Redis for scaling

**Problem**: Memory usage
- Tune message queue sizes
- Implement message TTL
- Regular cleanup of old rooms
- Monitor connection count

### Rate Limiting

**Problem**: Too many rate limit violations
- Increase rate limit threshold
- Implement client-side throttling
- Use message batching

## API Reference

See docstrings in source files for detailed API reference:
- `websocket.py`: WebSocketManager and core functionality
- `websocket_routes.py`: FastAPI route definitions
- `websocket_examples.py`: Usage examples

## Contributing

When adding new features:
1. Add message type to `MessageType` enum
2. Implement handler in `_register_*_handlers`
3. Update client libraries
4. Add examples
5. Update documentation

## License

Same as parent project.
