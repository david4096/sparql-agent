# WebSocket Quick Start Guide

Get up and running with WebSocket real-time communication in 5 minutes.

## Installation

WebSocket dependencies are already included in the SPARQL Agent package:

```bash
# If not already installed
pip install fastapi>=0.110.0 websockets>=12.0
```

## Server Setup (Python)

### Option 1: Use the Example App (Fastest)

```python
# Create a file: app.py
from sparql_agent.web.websocket_examples import create_websocket_app

app = create_websocket_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

Run it:
```bash
python app.py
```

### Option 2: Integrate with Existing FastAPI App

```python
from fastapi import FastAPI
from sparql_agent.web.websocket import WebSocketManager
from sparql_agent.web.websocket_routes import create_websocket_routes

app = FastAPI()

# Initialize WebSocket manager
ws_manager = WebSocketManager()

# Add WebSocket routes
# Note: You'll need your actual SPARQL components here
ws_router = create_websocket_routes(
    manager=ws_manager,
    generator=your_sparql_generator,
    executor=your_query_executor,
    ols_client=your_ols_client,
)
app.include_router(ws_router, prefix="/api")

@app.on_event("startup")
async def startup():
    await ws_manager.start()

@app.on_event("shutdown")
async def shutdown():
    await ws_manager.shutdown()
```

## Client Setup

### JavaScript/Browser

Copy the client library from `websocket.py` (CLIENT_JAVASCRIPT constant) or use this minimal version:

```html
<!DOCTYPE html>
<html>
<head>
    <title>SPARQL WebSocket Client</title>
</head>
<body>
    <h1>SPARQL Query Interface</h1>

    <input type="text" id="query" placeholder="Enter your query..." style="width: 500px;">
    <button onclick="sendQuery()">Execute</button>

    <div id="progress"></div>
    <div id="results"></div>

    <script>
        const ws = new WebSocket('ws://localhost:8000/api/ws/query');

        ws.onopen = () => {
            console.log('Connected!');
            document.getElementById('progress').innerText = 'Connected to server';
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log('Received:', data);

            if (data.type === 'query_progress') {
                const progress = data.payload;
                document.getElementById('progress').innerText =
                    `${progress.stage}: ${progress.message} (${Math.round(progress.progress * 100)}%)`;
            }

            if (data.type === 'query_result') {
                const result = data.payload;
                document.getElementById('results').innerHTML = `
                    <h3>Results</h3>
                    <p>Query: <code>${result.query}</code></p>
                    <p>Rows: ${result.row_count}</p>
                    <p>Time: ${result.execution_time.toFixed(2)}s</p>
                    <pre>${JSON.stringify(result.results, null, 2)}</pre>
                `;
            }

            if (data.type === 'error_message') {
                document.getElementById('results').innerHTML =
                    `<p style="color: red;">Error: ${data.payload.error}</p>`;
            }

            // Respond to heartbeat
            if (data.type === 'heartbeat') {
                ws.send(JSON.stringify({ type: 'pong' }));
            }
        };

        function sendQuery() {
            const query = document.getElementById('query').value;

            ws.send(JSON.stringify({
                type: 'query_request',
                message_id: Math.random().toString(36).substr(2, 9),
                payload: {
                    natural_language: query,
                    endpoint_id: 'uniprot',
                    execute: true,
                    limit: 10
                }
            }));
        }
    </script>
</body>
</html>
```

Save as `client.html` and open in your browser.

### Python Client

```python
import asyncio
import websockets
import json

async def test_client():
    uri = "ws://localhost:8000/api/ws/query?user_id=test_user"

    async with websockets.connect(uri) as websocket:
        print("Connected to WebSocket")

        # Receive connection ack
        ack = await websocket.recv()
        print(f"Received: {ack}")

        # Send a query
        await websocket.send(json.dumps({
            "type": "query_request",
            "message_id": "test-query-1",
            "payload": {
                "natural_language": "Find all proteins from human",
                "endpoint_id": "uniprot",
                "execute": True,
                "limit": 10
            }
        }))
        print("Query sent!")

        # Receive messages
        while True:
            try:
                message = await websocket.recv()
                data = json.loads(message)

                msg_type = data.get("type")

                if msg_type == "query_progress":
                    progress = data["payload"]
                    print(f"Progress: {progress['stage']} - {progress['message']}")

                elif msg_type == "query_result":
                    result = data["payload"]
                    print(f"\nQuery completed!")
                    print(f"  SPARQL: {result['query'][:100]}...")
                    print(f"  Rows: {result['row_count']}")
                    print(f"  Time: {result['execution_time']:.2f}s")
                    break

                elif msg_type == "error_message":
                    print(f"Error: {data['payload']['error']}")
                    break

                elif msg_type == "heartbeat":
                    # Respond to heartbeat
                    await websocket.send(json.dumps({"type": "pong"}))

            except websockets.exceptions.ConnectionClosed:
                print("Connection closed")
                break

# Run the client
asyncio.run(test_client())
```

### React Client

```jsx
import { useState } from 'react';

function useWebSocket(url) {
    const [ws, setWs] = useState(null);
    const [isConnected, setIsConnected] = useState(false);

    useState(() => {
        const websocket = new WebSocket(url);

        websocket.onopen = () => {
            setIsConnected(true);
        };

        websocket.onclose = () => {
            setIsConnected(false);
        };

        setWs(websocket);

        return () => websocket.close();
    }, [url]);

    return { ws, isConnected };
}

function QueryInterface() {
    const [query, setQuery] = useState('');
    const [progress, setProgress] = useState(null);
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);

    const { ws, isConnected } = useWebSocket('ws://localhost:8000/api/ws/query');

    if (ws) {
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);

            if (data.type === 'query_progress') {
                setProgress(data.payload);
            }

            if (data.type === 'query_result') {
                setResult(data.payload);
                setProgress(null);
            }

            if (data.type === 'error_message') {
                setError(data.payload.error);
                setProgress(null);
            }

            if (data.type === 'heartbeat') {
                ws.send(JSON.stringify({ type: 'pong' }));
            }
        };
    }

    const executeQuery = () => {
        if (!ws || !isConnected) return;

        setResult(null);
        setError(null);
        setProgress(null);

        ws.send(JSON.stringify({
            type: 'query_request',
            message_id: Math.random().toString(36).substr(2, 9),
            payload: {
                natural_language: query,
                endpoint_id: 'uniprot',
                execute: true,
                limit: 10
            }
        }));
    };

    return (
        <div>
            <h1>SPARQL Query Interface</h1>

            <div>
                Status: {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
            </div>

            <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Enter your query..."
                style={{ width: '500px' }}
            />
            <button onClick={executeQuery} disabled={!isConnected}>
                Execute Query
            </button>

            {progress && (
                <div>
                    <p>{progress.stage}: {progress.message}</p>
                    <progress value={progress.progress} max={1} />
                </div>
            )}

            {result && (
                <div>
                    <h3>Results</h3>
                    <p>Rows: {result.row_count}</p>
                    <p>Time: {result.execution_time.toFixed(2)}s</p>
                    <pre>{JSON.stringify(result.results, null, 2)}</pre>
                </div>
            )}

            {error && (
                <div style={{ color: 'red' }}>
                    Error: {error}
                </div>
            )}
        </div>
    );
}

export default QueryInterface;
```

## Test the Connection

### 1. Start the server:

```bash
python app.py
```

### 2. Open another terminal and test with curl:

```bash
# Check health
curl http://localhost:8000/health

# List rooms
curl http://localhost:8000/api/ws/rooms

# Get metrics
curl http://localhost:8000/api/ws/metrics
```

### 3. Connect with a WebSocket client:

Open `client.html` in your browser or run the Python client script.

## Common Use Cases

### Real-Time Query Execution

```javascript
ws.send(JSON.stringify({
    type: 'query_request',
    payload: {
        natural_language: 'Find all proteins from human',
        endpoint_id: 'uniprot',
        execute: true
    }
}));
```

Listen for progress:
```javascript
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.type === 'query_progress') {
        console.log(`${data.payload.stage}: ${data.payload.progress * 100}%`);
    }
};
```

### Ontology Search

```javascript
ws.send(JSON.stringify({
    type: 'ontology_search',
    payload: {
        query: 'protein',
        ontology: 'PR',
        limit: 10
    }
}));
```

### Collaborative Rooms

Connect to a room:
```javascript
const ws = new WebSocket('ws://localhost:8000/api/ws/room/my-room?user_id=alice');
```

Send typing indicator:
```javascript
ws.send(JSON.stringify({
    type: 'typing_indicator',
    payload: {
        is_typing: true,
        room_id: 'my-room'
    }
}));
```

Send room message:
```javascript
ws.send(JSON.stringify({
    type: 'room_message',
    payload: {
        room_id: 'my-room',
        message: 'Check out this query!'
    }
}));
```

## Troubleshooting

### Can't connect?

1. Check server is running: `curl http://localhost:8000/health`
2. Check URL scheme: Use `ws://` (not `http://`)
3. Check CORS settings in server configuration
4. Check firewall rules

### Connection drops?

1. Implement heartbeat response:
   ```javascript
   ws.onmessage = (event) => {
       const data = JSON.parse(event.data);
       if (data.type === 'heartbeat') {
           ws.send(JSON.stringify({ type: 'pong' }));
       }
   };
   ```

2. Implement reconnection:
   ```javascript
   function connect() {
       const ws = new WebSocket(url);

       ws.onclose = () => {
           console.log('Disconnected, reconnecting in 3s...');
           setTimeout(connect, 3000);
       };

       return ws;
   }
   ```

### Rate limited?

Server returns error when rate limit exceeded. Implement client-side throttling:

```javascript
let lastMessageTime = 0;
const MIN_MESSAGE_INTERVAL = 1000; // 1 second

function sendMessage(message) {
    const now = Date.now();
    if (now - lastMessageTime < MIN_MESSAGE_INTERVAL) {
        console.log('Rate limited, waiting...');
        setTimeout(() => sendMessage(message), MIN_MESSAGE_INTERVAL);
        return;
    }

    ws.send(JSON.stringify(message));
    lastMessageTime = now;
}
```

## Next Steps

1. **Read the full documentation**: See `WEBSOCKET_README.md` for complete API reference
2. **Explore examples**: Check `websocket_examples.py` for advanced patterns
3. **Run tests**: `pytest test_websocket.py -v`
4. **Deploy to production**: See production deployment section in docs
5. **Add authentication**: Implement proper auth before deploying

## Resources

- **Full Documentation**: `WEBSOCKET_README.md`
- **API Reference**: Docstrings in `websocket.py`
- **Examples**: `websocket_examples.py`
- **Tests**: `test_websocket.py`

## Support

For issues or questions:
1. Check the troubleshooting guide above
2. Review the full documentation in `WEBSOCKET_README.md`
3. Check test examples in `test_websocket.py`
4. Review the implementation summary in `IMPLEMENTATION_SUMMARY.md`

Happy coding! 🚀
