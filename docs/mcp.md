# MCP Integration Guide

Model Context Protocol (MCP) integration enables AI agents to use SPARQL Agent as a tool for querying knowledge graphs.

## What is MCP?

MCP (Model Context Protocol) is a standardized protocol for AI agents to interact with external tools and data sources. SPARQL Agent implements MCP to enable seamless integration with AI agent frameworks.

## Starting the MCP Server

=== "UV"

    ```bash
    uv run sparql-agent-mcp --port 3000
    ```

=== "Python"

    ```bash
    python -m sparql_agent.mcp.server
    ```

=== "Docker"

    ```bash
    docker run -p 3000:3000 david4096/sparql-agent:latest sparql-agent-mcp
    ```

## Configuration

Configure the MCP server in `config.yaml`:

```yaml
mcp:
  host: localhost
  port: 3000
  timeout: 300

  # Enable specific features
  features:
    query_generation: true
    schema_discovery: true
    ontology_lookup: true
    validation: true

  # Default endpoint
  default_endpoint: https://sparql.uniprot.org/sparql

  # LLM configuration
  llm:
    provider: anthropic
    api_key: ${ANTHROPIC_API_KEY}
```

## MCP Tools

The MCP server exposes these tools to AI agents:

### 1. query_knowledge_graph

Execute natural language queries against SPARQL endpoints.

**Parameters:**
- `query` (string): Natural language query
- `endpoint` (string, optional): SPARQL endpoint URL
- `ontology` (string, optional): Ontology ID for term mapping

**Example Request:**

```json
{
  "tool": "query_knowledge_graph",
  "parameters": {
    "query": "Find all human proteins involved in DNA repair",
    "endpoint": "https://sparql.uniprot.org/sparql",
    "ontology": "go"
  }
}
```

**Response:**

```json
{
  "success": true,
  "results": [
    {
      "protein": "P00533",
      "name": "BRCA1",
      "function": "DNA repair"
    }
  ],
  "sparql": "SELECT ?protein ?name ...",
  "count": 42
}
```

### 2. discover_endpoint

Discover capabilities and schema of a SPARQL endpoint.

**Parameters:**
- `endpoint` (string): SPARQL endpoint URL
- `methods` (array, optional): Discovery methods ["void", "introspection"]

**Example Request:**

```json
{
  "tool": "discover_endpoint",
  "parameters": {
    "endpoint": "https://sparql.uniprot.org/sparql",
    "methods": ["void", "introspection"]
  }
}
```

**Response:**

```json
{
  "success": true,
  "statistics": {
    "triple_count": 15000000000,
    "class_count": 342,
    "property_count": 456
  },
  "classes": ["up:Protein", "up:Enzyme", ...],
  "properties": ["rdfs:label", "up:organism", ...],
  "namespaces": {...}
}
```

### 3. search_ontology

Search for ontology terms in OLS4.

**Parameters:**
- `query` (string): Search term
- `ontology` (string, optional): Specific ontology ID
- `limit` (number, optional): Maximum results

**Example Request:**

```json
{
  "tool": "search_ontology",
  "parameters": {
    "query": "diabetes",
    "ontology": "efo",
    "limit": 10
  }
}
```

**Response:**

```json
{
  "success": true,
  "results": [
    {
      "iri": "http://www.ebi.ac.uk/efo/EFO_0000400",
      "label": "diabetes mellitus",
      "definition": "A metabolic disease...",
      "ontology": "efo"
    }
  ]
}
```

### 4. validate_sparql

Validate a SPARQL query.

**Parameters:**
- `sparql` (string): SPARQL query to validate

**Example Request:**

```json
{
  "tool": "validate_sparql",
  "parameters": {
    "sparql": "SELECT ?s WHERE { ?s ?p ?o }"
  }
}
```

**Response:**

```json
{
  "success": true,
  "valid": true,
  "errors": [],
  "warnings": ["Query may return many results"]
}
```

### 5. generate_sparql

Generate SPARQL from natural language.

**Parameters:**
- `query` (string): Natural language query
- `schema` (object, optional): Schema information
- `ontology` (string, optional): Ontology context

**Example Request:**

```json
{
  "tool": "generate_sparql",
  "parameters": {
    "query": "Find all proteins from human",
    "ontology": "up"
  }
}
```

**Response:**

```json
{
  "success": true,
  "sparql": "SELECT ?protein WHERE { ... }",
  "explanation": "This query finds all proteins..."
}
```

## Using with AI Agent Frameworks

### LangChain Integration

```python
from langchain.agents import Tool, AgentExecutor
from sparql_agent.mcp import MCPClient

# Connect to MCP server
mcp_client = MCPClient(base_url="http://localhost:3000")

# Create LangChain tools
tools = [
    Tool(
        name="QueryKnowledgeGraph",
        func=mcp_client.query_knowledge_graph,
        description="Query SPARQL endpoints with natural language"
    ),
    Tool(
        name="DiscoverEndpoint",
        func=mcp_client.discover_endpoint,
        description="Discover capabilities of SPARQL endpoints"
    ),
    Tool(
        name="SearchOntology",
        func=mcp_client.search_ontology,
        description="Search for ontology terms"
    )
]

# Create agent
from langchain.llms import OpenAI
from langchain.agents import initialize_agent

llm = OpenAI(temperature=0)
agent = initialize_agent(
    tools,
    llm,
    agent="zero-shot-react-description",
    verbose=True
)

# Use agent
result = agent.run(
    "Find all human proteins involved in cancer pathways"
)
```

### AutoGen Integration

```python
from autogen import AssistantAgent, UserProxyAgent
from sparql_agent.mcp import MCPClient

# Connect to MCP
mcp = MCPClient(base_url="http://localhost:3000")

# Create assistant with MCP tools
assistant = AssistantAgent(
    "assistant",
    llm_config={
        "model": "gpt-4",
        "functions": [
            {
                "name": "query_knowledge_graph",
                "description": "Query SPARQL endpoints",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "endpoint": {"type": "string"}
                    }
                }
            }
        ]
    },
    function_map={
        "query_knowledge_graph": mcp.query_knowledge_graph
    }
)

# Create user proxy
user_proxy = UserProxyAgent("user_proxy")

# Start conversation
user_proxy.initiate_chat(
    assistant,
    message="Find all proteins related to diabetes"
)
```

### Claude Desktop Integration

Add to Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "sparql-agent": {
      "command": "sparql-agent-mcp",
      "args": ["--port", "3000"],
      "env": {
        "ANTHROPIC_API_KEY": "your-api-key"
      }
    }
  }
}
```

Then use in Claude Desktop:

```
User: Can you find all human proteins involved in DNA repair?

Claude: I'll use the SPARQL Agent to query UniProt for that information.
[Uses query_knowledge_graph tool]

I found 42 human proteins involved in DNA repair, including:
- BRCA1 (P38398): Involved in DNA double-strand break repair
- RAD51 (Q06609): Essential for homologous recombination
...
```

## Custom MCP Handlers

Extend MCP with custom handlers:

```python
from sparql_agent.mcp import MCPServer, MCPHandler

class CustomHandler(MCPHandler):
    async def handle_custom_query(self, request):
        """Custom query handler"""
        query = request.get("query")

        # Custom processing
        results = await self.process_custom_logic(query)

        return {
            "success": True,
            "results": results
        }

# Register handler
server = MCPServer()
server.register_handler("custom_query", CustomHandler())

# Start server
server.run(port=3000)
```

## MCP Middleware

Add middleware for authentication, logging, etc:

```python
from sparql_agent.mcp import MCPServer, Middleware

class AuthMiddleware(Middleware):
    async def process_request(self, request):
        api_key = request.headers.get("X-API-Key")
        if not self.validate_key(api_key):
            raise AuthenticationError("Invalid API key")
        return request

    async def process_response(self, response):
        # Add headers, log, etc
        return response

server = MCPServer()
server.add_middleware(AuthMiddleware())
server.run()
```

## Monitoring MCP Server

### Health Check

```bash
curl http://localhost:3000/health
```

Response:

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "uptime": 3600,
  "active_connections": 5
}
```

### Metrics

```bash
curl http://localhost:3000/metrics
```

Response:

```json
{
  "requests_total": 1000,
  "requests_per_minute": 10,
  "average_response_time": 0.5,
  "error_rate": 0.01,
  "tools": {
    "query_knowledge_graph": {
      "calls": 500,
      "avg_time": 1.2
    },
    "discover_endpoint": {
      "calls": 200,
      "avg_time": 2.5
    }
  }
}
```

## Security

### Authentication

```yaml
mcp:
  auth:
    enabled: true
    method: api_key
    keys:
      - key: secret-key-1
        name: agent-1
        permissions: ["query", "discover"]
      - key: secret-key-2
        name: agent-2
        permissions: ["query"]
```

Include API key in requests:

```json
{
  "tool": "query_knowledge_graph",
  "api_key": "secret-key-1",
  "parameters": {...}
}
```

### Rate Limiting

```yaml
mcp:
  rate_limit:
    enabled: true
    requests_per_minute: 100
    burst: 10
```

### Request Validation

```yaml
mcp:
  validation:
    max_query_length: 1000
    max_results: 10000
    timeout: 300
    allowed_endpoints:
      - "https://sparql.uniprot.org/sparql"
      - "https://query.wikidata.org/sparql"
```

## Troubleshooting

### Connection Issues

```bash
# Test MCP server
curl http://localhost:3000/health

# Check logs
tail -f ~/.sparql-agent/logs/mcp.log
```

### Timeout Errors

Increase timeout:

```yaml
mcp:
  timeout: 600  # 10 minutes
```

### Memory Issues

Limit concurrent requests:

```yaml
mcp:
  max_concurrent_requests: 10
  max_memory_mb: 2048
```

## Best Practices

1. **Use Caching**: Enable caching for frequently accessed data
2. **Set Timeouts**: Configure appropriate timeouts for long-running queries
3. **Monitor Usage**: Track API usage and performance
4. **Secure Access**: Use API keys and rate limiting
5. **Handle Errors**: Implement proper error handling in agents

## Examples

### Complete Agent Example

```python
from langchain.agents import Tool, AgentExecutor, initialize_agent
from langchain.llms import Anthropic
from sparql_agent.mcp import MCPClient

# Connect to MCP
mcp = MCPClient(base_url="http://localhost:3000")

# Define tools
tools = [
    Tool(
        name="QueryKG",
        func=lambda q: mcp.query_knowledge_graph(query=q),
        description="Query knowledge graphs with natural language"
    ),
    Tool(
        name="SearchOntology",
        func=lambda q: mcp.search_ontology(query=q),
        description="Search for ontology terms"
    )
]

# Create agent
llm = Anthropic()
agent = initialize_agent(
    tools, llm, agent="zero-shot-react-description"
)

# Execute task
result = agent.run("""
    Find all human proteins involved in the p53 pathway
    and their associated diseases.
""")

print(result)
```

## Next Steps

- [Web API Reference](web-api.md) - REST API documentation
- [Configuration Guide](configuration.md) - MCP server configuration
- [Examples](examples/integrations.md) - Integration examples
