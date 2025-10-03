# SPARQL Agent Web API

Production-ready FastAPI REST API for natural language to SPARQL conversion and query execution.

## Quick Start

Start the server using uvicorn:

```bash
uv run uvicorn sparql_agent.web.server:app --reload --host 0.0.0.0 --port 8000
```

Or use the shortcut:

```bash
cd /Users/david/git/sparql-agent/src/sparql_agent/web
uv run uvicorn server:app --reload
```

The API will be available at:
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Features

### Core Capabilities

- **Natural Language to SPARQL**: Convert questions to SPARQL queries
- **Query Execution**: Execute SPARQL queries against endpoints
- **Validation**: Validate SPARQL syntax and best practices
- **Ontology Integration**: Search and retrieve ontology information from OLS4
- **Federation**: Execute queries across multiple endpoints
- **Batch Processing**: Upload and process multiple queries
- **WebSocket Streaming**: Real-time query processing

### Production Features

- **Rate Limiting**: Configurable request limits per endpoint
- **CORS Support**: Cross-origin resource sharing enabled
- **GZip Compression**: Automatic response compression
- **Health Checks**: Detailed system health and metrics
- **Error Handling**: Comprehensive error responses
- **OpenAPI Documentation**: Auto-generated API documentation
- **Background Tasks**: Async processing for long-running operations

## API Endpoints

### Query Generation and Execution

#### POST `/query`
Convert natural language to SPARQL and execute

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "natural_language": "Find all proteins from human",
    "endpoint_url": "https://sparql.uniprot.org/sparql",
    "execute": true,
    "limit": 10
  }'
```

Response:
```json
{
  "success": true,
  "query": "PREFIX up: <http://purl.uniprot.org/core/>\nSELECT ?protein WHERE { ?protein a up:Protein . ?protein up:organism <http://purl.uniprot.org/taxonomy/9606> } LIMIT 10",
  "natural_language": "Find all proteins from human",
  "results": {
    "bindings": [...],
    "row_count": 10
  },
  "confidence": 0.85,
  "execution_time": 1.23
}
```

#### POST `/execute`
Execute a SPARQL query directly

```bash
curl -X POST "http://localhost:8000/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT * WHERE { ?s ?p ?o } LIMIT 10",
    "endpoint_url": "https://sparql.uniprot.org/sparql",
    "format": "json"
  }'
```

### Validation

#### POST `/validate`
Validate SPARQL query syntax

```bash
curl -X POST "http://localhost:8000/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10",
    "strict": false
  }'
```

Response:
```json
{
  "is_valid": true,
  "query": "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10",
  "errors": [],
  "warnings": [],
  "suggestions": ["Consider adding DISTINCT to eliminate duplicates"],
  "complexity_score": 2.5
}
```

### Endpoints

#### GET `/endpoints`
List all configured SPARQL endpoints

```bash
curl "http://localhost:8000/endpoints"
```

#### GET `/endpoints/{endpoint_id}/schema`
Get schema information for an endpoint

```bash
curl "http://localhost:8000/endpoints/uniprot/schema"
```

### Ontology Lookup

#### GET `/ontologies`
Search for ontology terms

```bash
curl "http://localhost:8000/ontologies?q=protein&limit=10"
```

#### GET `/ontologies/{ontology_id}`
Get detailed information about an ontology

```bash
curl "http://localhost:8000/ontologies/go"
```

### Advanced Features

#### POST `/generate`
Generate multiple alternative queries

```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "natural_language": "Find all proteins from human",
    "count": 3
  }'
```

#### POST `/federated`
Execute query across multiple endpoints

```bash
curl -X POST "http://localhost:8000/federated" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT * WHERE { ?s ?p ?o } LIMIT 5",
    "endpoint_urls": [
      "https://sparql.uniprot.org/sparql",
      "https://www.ebi.ac.uk/rdf/services/sparql"
    ],
    "merge_strategy": "union",
    "parallel": true
  }'
```

#### POST `/batch/upload`
Upload file with multiple queries

```bash
curl -X POST "http://localhost:8000/batch/upload" \
  -F "file=@queries.json" \
  -F "endpoint_url=https://sparql.uniprot.org/sparql"
```

### Health and Monitoring

#### GET `/health`
System health check

```bash
curl "http://localhost:8000/health"
```

Response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime": 123.45,
  "components": {
    "generator": "healthy",
    "executor": "healthy",
    "validator": "healthy",
    "ols_client": "healthy",
    "llm_client": "healthy"
  },
  "metrics": {
    "total_requests": 150,
    "successful_requests": 145,
    "total_queries_executed": 80
  }
}
```

#### GET `/metrics`
Detailed system metrics

```bash
curl "http://localhost:8000/metrics"
```

### WebSocket

#### WS `/ws/query`
Real-time query processing

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/query');

ws.onopen = () => {
  ws.send(JSON.stringify({
    action: 'query',
    natural_language: 'Find all proteins from human',
    endpoint_url: 'https://sparql.uniprot.org/sparql'
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
};
```

## Configuration

### Environment Variables

Set these environment variables to configure the API:

```bash
# LLM Configuration
export SPARQL_AGENT_LLM__API_KEY="your-api-key"
export SPARQL_AGENT_LLM__MODEL_NAME="gpt-4"
export SPARQL_AGENT_LLM__TEMPERATURE="0.1"

# Endpoint Configuration
export SPARQL_AGENT_ENDPOINT__DEFAULT_TIMEOUT="60"
export SPARQL_AGENT_ENDPOINT__MAX_RETRIES="3"

# Ontology Configuration
export SPARQL_AGENT_ONTOLOGY__OLS_API_BASE_URL="https://www.ebi.ac.uk/ols4/api"

# Logging
export SPARQL_AGENT_LOG__LEVEL="INFO"
```

### Rate Limiting

Default rate limits:
- `/query`: 20 requests/minute
- `/execute`: 30 requests/minute
- `/validate`: 60 requests/minute
- `/generate`: 15 requests/minute
- `/federated`: 10 requests/minute

### Authentication (Optional)

To enable API key authentication, include the `X-API-Key` header:

```bash
curl -X POST "http://localhost:8000/query" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{ ... }'
```

## Error Handling

All endpoints return consistent error responses:

```json
{
  "success": false,
  "error": "Query execution failed: Connection timeout",
  "metadata": {
    "error_type": "QueryTimeoutError"
  }
}
```

Common HTTP status codes:
- `200`: Success
- `400`: Bad request / validation error
- `404`: Resource not found
- `429`: Rate limit exceeded
- `500`: Internal server error
- `504`: Gateway timeout

## Development

### Running with Auto-Reload

```bash
uv run uvicorn sparql_agent.web.server:app --reload --log-level debug
```

### Testing the API

Using Python:

```python
import requests

# Generate and execute query
response = requests.post(
    "http://localhost:8000/query",
    json={
        "natural_language": "Find all proteins from human",
        "endpoint_url": "https://sparql.uniprot.org/sparql",
        "execute": True,
        "limit": 10
    }
)

result = response.json()
print(f"Generated query: {result['query']}")
print(f"Results: {result['results']['row_count']} rows")
```

### Docker Deployment

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy project files
COPY . .

# Install dependencies
RUN uv sync

# Expose port
EXPOSE 8000

# Run server
CMD ["uv", "run", "uvicorn", "sparql_agent.web.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:

```bash
docker build -t sparql-agent-api .
docker run -p 8000:8000 -e SPARQL_AGENT_LLM__API_KEY="your-key" sparql-agent-api
```

## Performance

### Benchmarks

Typical response times (on standard hardware):
- Query generation (template): ~50ms
- Query generation (LLM): ~500-2000ms
- Query execution: ~100-1000ms (depends on endpoint)
- Validation: ~10-50ms
- Ontology search: ~100-500ms

### Optimization Tips

1. **Use Template Strategy**: For simple queries, use `strategy: "template"` for faster generation
2. **Enable Caching**: Results are cached automatically for repeated queries
3. **Limit Result Sets**: Use `limit` parameter to reduce transfer time
4. **Parallel Execution**: Use `/federated` with `parallel: true` for multi-endpoint queries
5. **WebSocket for Streaming**: Use WebSocket for real-time updates on long-running queries

## Monitoring

### Prometheus Metrics

The `/metrics` endpoint provides data suitable for Prometheus scraping:

```yaml
scrape_configs:
  - job_name: 'sparql-agent'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

### Health Checks

Use `/health` for liveness and readiness probes:

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

## Troubleshooting

### Common Issues

1. **LLM Client Not Available**
   - Ensure `SPARQL_AGENT_LLM__API_KEY` is set
   - Check API key validity
   - Verify model name is correct

2. **Query Execution Timeouts**
   - Increase timeout: `SPARQL_AGENT_ENDPOINT__DEFAULT_TIMEOUT`
   - Check endpoint availability
   - Simplify query or add LIMIT clause

3. **Rate Limit Exceeded**
   - Reduce request frequency
   - Implement client-side rate limiting
   - Contact administrator to adjust limits

4. **Validation Failures**
   - Check SPARQL syntax
   - Verify PREFIX declarations
   - Use `/validate` endpoint for detailed errors

## API Client Libraries

### Python Client Example

```python
from typing import Dict, Any
import requests

class SPARQLAgentClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()

    def query(
        self,
        natural_language: str,
        endpoint_url: str,
        execute: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate and execute SPARQL query from natural language."""
        response = self.session.post(
            f"{self.base_url}/query",
            json={
                "natural_language": natural_language,
                "endpoint_url": endpoint_url,
                "execute": execute,
                **kwargs
            }
        )
        response.raise_for_status()
        return response.json()

    def execute(
        self,
        query: str,
        endpoint_url: str,
        format: str = "json"
    ) -> Dict[str, Any]:
        """Execute SPARQL query directly."""
        response = self.session.post(
            f"{self.base_url}/execute",
            json={
                "query": query,
                "endpoint_url": endpoint_url,
                "format": format
            }
        )
        response.raise_for_status()
        return response.json()

    def validate(self, query: str) -> Dict[str, Any]:
        """Validate SPARQL query."""
        response = self.session.post(
            f"{self.base_url}/validate",
            json={"query": query}
        )
        response.raise_for_status()
        return response.json()

# Usage
client = SPARQLAgentClient()
result = client.query(
    "Find all proteins from human",
    "https://sparql.uniprot.org/sparql"
)
print(result)
```

## License

MIT License - See LICENSE file for details
