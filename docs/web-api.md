# Web API Reference

SPARQL Agent provides a RESTful API built with FastAPI for web integration.

## Starting the Server

=== "UV"

    ```bash
    uv run sparql-agent-server --host 0.0.0.0 --port 8000
    ```

=== "Uvicorn"

    ```bash
    uvicorn sparql_agent.web.server:app --reload
    ```

=== "Docker"

    ```bash
    docker run -p 8000:8000 david4096/sparql-agent:latest
    ```

## Base URL

```
http://localhost:8000
```

## Interactive Documentation

Once the server is running, access:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI Schema**: `http://localhost:8000/openapi.json`

## Authentication

Configure API key authentication in `config.yaml`:

```yaml
web:
  auth:
    enabled: true
    type: api_key
    header: X-API-Key
```

Include API key in requests:

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/query
```

## Endpoints

### Query Endpoints

#### POST /api/query

Execute a natural language or SPARQL query.

**Request:**

```json
{
  "query": "Find all human proteins",
  "endpoint": "https://sparql.uniprot.org/sparql",
  "format": "json",
  "limit": 100,
  "ontology": "go",
  "strategy": "auto"
}
```

**Response:**

```json
{
  "status": "success",
  "results": [
    {
      "protein": "http://purl.uniprot.org/uniprot/P00533",
      "name": "Epidermal growth factor receptor",
      "organism": "Homo sapiens"
    }
  ],
  "sparql": "SELECT ?protein ?name ...",
  "execution_time": 1.234,
  "result_count": 42
}
```

**cURL Example:**

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Find all human proteins",
    "endpoint": "https://sparql.uniprot.org/sparql"
  }'
```

**Python Example:**

```python
import requests

response = requests.post(
    "http://localhost:8000/api/query",
    json={
        "query": "Find all human proteins",
        "endpoint": "https://sparql.uniprot.org/sparql"
    }
)

data = response.json()
print(f"Found {data['result_count']} results")
for result in data['results']:
    print(result)
```

#### POST /api/sparql

Execute a raw SPARQL query.

**Request:**

```json
{
  "sparql": "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10",
  "endpoint": "https://sparql.uniprot.org/sparql",
  "format": "json"
}
```

**Response:**

```json
{
  "status": "success",
  "results": [...],
  "execution_time": 0.5
}
```

#### POST /api/query/validate

Validate a SPARQL query.

**Request:**

```json
{
  "sparql": "SELECT ?s WHERE { ?s ?p ?o }"
}
```

**Response:**

```json
{
  "valid": true,
  "errors": [],
  "warnings": ["Query may return many results"]
}
```

### Discovery Endpoints

#### GET /api/discover/{endpoint_url}

Discover endpoint capabilities.

**Example:**

```bash
curl http://localhost:8000/api/discover/https%3A%2F%2Fsparql.uniprot.org%2Fsparql
```

**Response:**

```json
{
  "endpoint": "https://sparql.uniprot.org/sparql",
  "status": "available",
  "statistics": {
    "triple_count": 15000000000,
    "class_count": 342,
    "property_count": 456
  },
  "classes": [...],
  "properties": [...],
  "namespaces": {...}
}
```

#### GET /api/discover/statistics/{endpoint_url}

Get endpoint statistics.

**Response:**

```json
{
  "triple_count": 15000000000,
  "class_count": 342,
  "property_count": 456,
  "predicate_count": 523,
  "namespace_count": 45
}
```

### Ontology Endpoints

#### GET /api/ontology/search

Search OLS4 ontologies.

**Parameters:**
- `query`: Search term
- `ontology`: Ontology ID (optional)
- `limit`: Maximum results (default: 10)

**Example:**

```bash
curl "http://localhost:8000/api/ontology/search?query=diabetes&ontology=efo&limit=5"
```

**Response:**

```json
{
  "results": [
    {
      "iri": "http://www.ebi.ac.uk/efo/EFO_0000400",
      "label": "diabetes mellitus",
      "definition": "A metabolic disease...",
      "ontology": "efo"
    }
  ],
  "count": 5
}
```

#### GET /api/ontology/{ontology_id}/term/{term_id}

Get detailed term information.

**Example:**

```bash
curl http://localhost:8000/api/ontology/efo/term/EFO_0000400
```

**Response:**

```json
{
  "iri": "http://www.ebi.ac.uk/efo/EFO_0000400",
  "label": "diabetes mellitus",
  "definition": "A metabolic disease...",
  "synonyms": ["diabetes", "DM"],
  "parents": [...],
  "children": [...],
  "annotations": {...}
}
```

### Schema Endpoints

#### POST /api/schema/infer

Infer schema from endpoint.

**Request:**

```json
{
  "endpoint": "https://sparql.uniprot.org/sparql",
  "methods": ["void", "introspection"],
  "sampling": true
}
```

**Response:**

```json
{
  "classes": {
    "up:Protein": {
      "instance_count": 500000,
      "properties": ["rdfs:label", "up:organism"]
    }
  },
  "properties": [...],
  "namespaces": {...}
}
```

### Batch Processing

#### POST /api/batch

Process multiple queries.

**Request:**

```json
{
  "queries": [
    "Find all proteins",
    "List all diseases",
    "Show pathways"
  ],
  "endpoint": "https://sparql.uniprot.org/sparql",
  "parallel": true
}
```

**Response:**

```json
{
  "status": "completed",
  "results": [
    {"query": "Find all proteins", "results": [...], "status": "success"},
    {"query": "List all diseases", "results": [...], "status": "success"},
    {"query": "Show pathways", "results": [...], "status": "success"}
  ],
  "total_time": 3.5
}
```

### Health & Status

#### GET /health

Health check endpoint.

**Response:**

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2024-10-02T22:00:00Z"
}
```

#### GET /api/version

Get version information.

**Response:**

```json
{
  "version": "0.1.0",
  "python_version": "3.11.0",
  "dependencies": {
    "rdflib": "7.0.0",
    "SPARQLWrapper": "2.0.0"
  }
}
```

## Rate Limiting

Configure rate limiting in `config.yaml`:

```yaml
web:
  rate_limit:
    enabled: true
    requests_per_minute: 60
```

When rate limited, API returns HTTP 429:

```json
{
  "error": "Rate limit exceeded",
  "retry_after": 30
}
```

## CORS Configuration

```yaml
web:
  cors:
    enabled: true
    allow_origins:
      - "http://localhost:3000"
      - "https://myapp.com"
    allow_methods:
      - GET
      - POST
      - OPTIONS
    allow_headers:
      - "*"
```

## Error Handling

All errors follow this format:

```json
{
  "error": "Error type",
  "message": "Detailed error message",
  "details": {
    "field": "Additional context"
  },
  "timestamp": "2024-10-02T22:00:00Z"
}
```

### HTTP Status Codes

- `200 OK`: Success
- `201 Created`: Resource created
- `400 Bad Request`: Invalid input
- `401 Unauthorized`: Missing/invalid auth
- `404 Not Found`: Resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Service down

## WebSocket Support

Real-time query execution with progress updates:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/query');

ws.onopen = () => {
  ws.send(JSON.stringify({
    query: "Find all proteins",
    endpoint: "https://sparql.uniprot.org/sparql"
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === 'progress') {
    console.log(`Progress: ${data.percentage}%`);
  } else if (data.type === 'result') {
    console.log('Results:', data.results);
  } else if (data.type === 'error') {
    console.error('Error:', data.message);
  }
};
```

## Client Libraries

### JavaScript/TypeScript

```typescript
import { SPARQLAgentClient } from 'sparql-agent-client';

const client = new SPARQLAgentClient({
  baseURL: 'http://localhost:8000',
  apiKey: 'your-api-key'
});

const results = await client.query({
  query: 'Find all proteins',
  endpoint: 'https://sparql.uniprot.org/sparql'
});

console.log(results);
```

### Python

```python
from sparql_agent_client import WebClient

client = WebClient(
    base_url="http://localhost:8000",
    api_key="your-api-key"
)

results = client.query(
    query="Find all proteins",
    endpoint="https://sparql.uniprot.org/sparql"
)

print(results)
```

## Deployment

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install -e .

CMD ["sparql-agent-server", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  sparql-agent:
    image: david4096/sparql-agent:latest
    ports:
      - "8000:8000"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    volumes:
      - ./config:/app/config
    restart: unless-stopped

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sparql-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: sparql-agent
  template:
    metadata:
      labels:
        app: sparql-agent
    spec:
      containers:
      - name: sparql-agent
        image: david4096/sparql-agent:latest
        ports:
        - containerPort: 8000
        env:
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: sparql-agent-secrets
              key: anthropic-api-key
```

## Monitoring

### Prometheus Metrics

Access metrics at `/metrics`:

```
# Query execution time
sparql_agent_query_duration_seconds{endpoint="uniprot"}

# Query count
sparql_agent_query_total{status="success"}

# Error rate
sparql_agent_errors_total{type="timeout"}
```

### Logging

Configure structured logging:

```yaml
logging:
  level: INFO
  format: json
  output: /var/log/sparql-agent/access.log
```

## Next Steps

- [MCP Integration](mcp.md) - Model Context Protocol
- [Configuration](configuration.md) - Server configuration
- [Deployment Guide](deployment.md) - Production deployment
- [Best Practices](best-practices/security.md) - Security best practices
