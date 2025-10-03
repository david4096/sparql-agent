# Configuration Guide

SPARQL Agent can be configured through environment variables, configuration files, or programmatically.

## Configuration Methods

### 1. Environment Variables

Set environment variables for quick configuration:

```bash
# LLM Configuration
export ANTHROPIC_API_KEY="sk-ant-your-key-here"
export OPENAI_API_KEY="sk-your-key-here"

# Default Endpoint
export SPARQL_AGENT_ENDPOINT="https://sparql.uniprot.org/sparql"

# Logging
export SPARQL_AGENT_LOG_LEVEL="INFO"
export SPARQL_AGENT_LOG_FILE="~/.sparql-agent/logs/sparql-agent.log"

# Query Settings
export SPARQL_AGENT_TIMEOUT="30"
export SPARQL_AGENT_MAX_RESULTS="1000"
```

### 2. Configuration File

Create a YAML configuration file at `~/.sparql-agent/config.yaml`:

```yaml
# LLM Configuration
llm:
  # Provider: anthropic, openai, or local
  provider: anthropic

  # Model name
  model: claude-3-5-sonnet-20241022

  # API key (can use ${ENV_VAR} for environment variables)
  api_key: ${ANTHROPIC_API_KEY}

  # Temperature for generation (0.0-1.0)
  temperature: 0.0

  # Maximum tokens
  max_tokens: 4096

  # Alternative providers
  providers:
    anthropic:
      api_key: ${ANTHROPIC_API_KEY}
      model: claude-3-5-sonnet-20241022
      max_tokens: 4096
    openai:
      api_key: ${OPENAI_API_KEY}
      model: gpt-4
      max_tokens: 4096
    local:
      base_url: http://localhost:1234/v1
      model: local-model

# SPARQL Endpoints
endpoints:
  # Default endpoint
  default: https://sparql.uniprot.org/sparql

  # Named endpoints
  uniprot: https://sparql.uniprot.org/sparql
  wikidata: https://query.wikidata.org/sparql
  dbpedia: https://dbpedia.org/sparql
  chembl: https://chembl.lbl.gov/sparql
  reactome: https://reactome.org/ContentService/sparql

  # Endpoint-specific settings
  settings:
    uniprot:
      timeout: 60
      max_results: 10000
      headers:
        User-Agent: "SPARQL-Agent/0.1.0"

# Ontology Configuration
ontologies:
  # OLS4 base URL
  ols_base_url: https://www.ebi.ac.uk/ols4/api

  # Local ontology cache
  local_cache: ~/.sparql-agent/ontologies

  # Auto-download ontologies
  auto_download: true

  # Preferred ontologies for different domains
  biomedical:
    - efo  # Experimental Factor Ontology
    - mondo  # Monarch Disease Ontology
    - hp  # Human Phenotype Ontology
    - go  # Gene Ontology

  # Local OWL files
  local:
    go: ~/.sparql-agent/ontologies/go.owl
    mondo: ~/.sparql-agent/ontologies/mondo.owl

# Query Configuration
query:
  # Query timeout in seconds
  timeout: 30

  # Maximum number of results
  max_results: 1000

  # Enable OWL reasoning
  enable_reasoning: true

  # Retry settings
  retry_count: 3
  retry_delay: 5
  retry_backoff: 2.0

  # Query optimization
  optimize: true

  # Default output format
  default_format: json

  # Validation
  validate_before_execution: true

  # Query generation strategy
  strategy: auto  # auto, template, llm, hybrid

# Schema Discovery
discovery:
  # Enable automatic schema discovery
  enabled: true

  # Cache discovery results
  cache_ttl: 3600  # 1 hour

  # Discovery methods
  methods:
    - void  # VoID parsing
    - introspection  # SPARQL introspection
    - statistical  # Statistical analysis

  # Sampling for large endpoints
  sampling:
    enabled: true
    size: 10000

# Result Formatting
formatting:
  # Default format
  default: table

  # Table settings
  table:
    max_column_width: 50
    truncate: true
    show_index: true

  # JSON settings
  json:
    indent: 2
    ensure_ascii: false

  # CSV settings
  csv:
    delimiter: ","
    quoting: minimal

# Caching
cache:
  # Enable caching
  enabled: true

  # Cache backend: memory, redis, file
  backend: file

  # Cache directory
  directory: ~/.sparql-agent/cache

  # Default TTL in seconds
  ttl: 3600

  # Maximum cache size (MB)
  max_size: 1000

  # Redis settings (if backend=redis)
  redis:
    host: localhost
    port: 6379
    db: 0

# Logging
logging:
  # Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
  level: INFO

  # Log format: text or json
  format: text

  # Log output
  output: ~/.sparql-agent/logs/sparql-agent.log

  # Rotation
  rotation:
    max_bytes: 10485760  # 10MB
    backup_count: 5

  # Log different components
  components:
    sparql_agent.llm: INFO
    sparql_agent.query: DEBUG
    sparql_agent.execution: INFO

# Web Server
web:
  # Host and port
  host: 0.0.0.0
  port: 8000

  # Workers
  workers: 4

  # CORS
  cors:
    enabled: true
    allow_origins:
      - "*"
    allow_methods:
      - GET
      - POST
      - OPTIONS
    allow_headers:
      - "*"

  # Rate limiting
  rate_limit:
    enabled: true
    requests_per_minute: 60

  # Authentication
  auth:
    enabled: false
    type: api_key
    header: X-API-Key

# MCP Server
mcp:
  # Host and port
  host: localhost
  port: 3000

  # Timeout
  timeout: 300

  # Enable features
  features:
    query_generation: true
    schema_discovery: true
    ontology_lookup: true
    validation: true

# Performance
performance:
  # Connection pooling
  pool_size: 10
  pool_max_overflow: 20

  # Thread settings
  max_workers: 4

  # Memory limits
  max_memory_mb: 1024

# Security
security:
  # Validate queries for malicious content
  validate_queries: true

  # Maximum query complexity
  max_query_complexity: 100

  # Allowed query types
  allowed_query_types:
    - SELECT
    - ASK
    - DESCRIBE
    - CONSTRUCT

  # Blocked patterns
  blocked_patterns:
    - "DELETE"
    - "INSERT"
    - "DROP"
    - "CLEAR"
```

### 3. Programmatic Configuration

Configure SPARQL Agent in your Python code:

```python
from sparql_agent import SPARQLAgent
from sparql_agent.config import Config

# Method 1: Direct initialization
agent = SPARQLAgent(
    endpoint="https://sparql.uniprot.org/sparql",
    llm_provider="anthropic",
    api_key="your-api-key",
    timeout=60,
    max_results=1000
)

# Method 2: Using Config object
config = Config(
    llm_provider="anthropic",
    llm_model="claude-3-5-sonnet-20241022",
    default_endpoint="https://sparql.uniprot.org/sparql",
    timeout=60
)

agent = SPARQLAgent(config=config)

# Method 3: Load from file
config = Config.from_file("~/.sparql-agent/config.yaml")
agent = SPARQLAgent(config=config)

# Method 4: Load from environment
config = Config.from_env()
agent = SPARQLAgent(config=config)
```

## Configuration Profiles

Use different profiles for different environments:

```yaml
# config.yaml
profiles:
  development:
    llm:
      provider: anthropic
      model: claude-3-5-sonnet-20241022
    logging:
      level: DEBUG
    endpoints:
      default: http://localhost:3030/sparql

  production:
    llm:
      provider: anthropic
      model: claude-3-5-sonnet-20241022
    logging:
      level: WARNING
    endpoints:
      default: https://sparql.uniprot.org/sparql
    cache:
      enabled: true
      backend: redis

  testing:
    llm:
      provider: local
      model: test-model
    logging:
      level: DEBUG
    cache:
      enabled: false
```

Use profiles:

```bash
# CLI
uv run sparql-agent --profile production query "test"

# Environment variable
export SPARQL_AGENT_PROFILE=production
uv run sparql-agent query "test"
```

```python
# Python API
config = Config.from_file("config.yaml", profile="production")
agent = SPARQLAgent(config=config)
```

## Configuration Precedence

Configuration is loaded in the following order (later overrides earlier):

1. Default values
2. Configuration file (`~/.sparql-agent/config.yaml`)
3. Environment variables
4. Profile-specific settings
5. Command-line arguments
6. Programmatic configuration

## Environment Variables Reference

### LLM Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key | - |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `SPARQL_AGENT_LLM_PROVIDER` | LLM provider | anthropic |
| `SPARQL_AGENT_LLM_MODEL` | Model name | claude-3-5-sonnet-20241022 |
| `SPARQL_AGENT_LLM_TEMPERATURE` | Temperature | 0.0 |

### Endpoint Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `SPARQL_AGENT_ENDPOINT` | Default SPARQL endpoint | - |
| `SPARQL_AGENT_TIMEOUT` | Query timeout (seconds) | 30 |
| `SPARQL_AGENT_MAX_RESULTS` | Maximum results | 1000 |

### Logging Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `SPARQL_AGENT_LOG_LEVEL` | Log level | INFO |
| `SPARQL_AGENT_LOG_FILE` | Log file path | - |
| `SPARQL_AGENT_LOG_FORMAT` | Log format (text/json) | text |

### Cache Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `SPARQL_AGENT_CACHE_ENABLED` | Enable caching | true |
| `SPARQL_AGENT_CACHE_BACKEND` | Cache backend | file |
| `SPARQL_AGENT_CACHE_TTL` | Cache TTL (seconds) | 3600 |
| `SPARQL_AGENT_CACHE_DIR` | Cache directory | ~/.sparql-agent/cache |

## Advanced Configuration

### Custom Endpoints with Authentication

```yaml
endpoints:
  secure_endpoint:
    url: https://secure.example.com/sparql
    auth:
      type: basic
      username: ${ENDPOINT_USER}
      password: ${ENDPOINT_PASS}
    headers:
      User-Agent: "SPARQL-Agent/0.1.0"
      Accept: "application/sparql-results+json"
    timeout: 60
    verify_ssl: true
```

### Multiple LLM Providers

```yaml
llm:
  fallback_enabled: true
  providers:
    - name: primary
      provider: anthropic
      api_key: ${ANTHROPIC_API_KEY}
      priority: 1
    - name: secondary
      provider: openai
      api_key: ${OPENAI_API_KEY}
      priority: 2
    - name: local
      provider: local
      base_url: http://localhost:1234/v1
      priority: 3
```

### Query Templates

```yaml
query:
  templates:
    protein_search: |
      SELECT ?protein ?name ?organism
      WHERE {
        ?protein a up:Protein ;
                 rdfs:label ?name ;
                 up:organism ?organism .
        FILTER(CONTAINS(LCASE(?name), LCASE("{{term}}")))
      }
      LIMIT {{limit}}

    disease_genes: |
      SELECT ?gene ?disease ?association
      WHERE {
        ?gene a :Gene ;
              :associatedWith ?disease .
        ?disease a :Disease ;
                 rdfs:label ?diseaseName .
        FILTER(CONTAINS(LCASE(?diseaseName), LCASE("{{disease}}")))
      }
```

## Validation

Validate your configuration:

```bash
# CLI validation
uv run sparql-agent config validate

# Check specific profile
uv run sparql-agent config validate --profile production

# Show current configuration
uv run sparql-agent config show
```

```python
# Python validation
from sparql_agent.config import Config

config = Config.from_file("config.yaml")

# Validate
is_valid, errors = config.validate()
if not is_valid:
    for error in errors:
        print(f"Error: {error}")

# Show configuration
print(config.to_yaml())
```

## Migration

### From 0.0.x to 0.1.0

Configuration format changes:

```yaml
# Old format (0.0.x)
anthropic_api_key: sk-ant-...
endpoint: https://sparql.uniprot.org/sparql

# New format (0.1.0)
llm:
  provider: anthropic
  api_key: ${ANTHROPIC_API_KEY}

endpoints:
  default: https://sparql.uniprot.org/sparql
```

Use the migration tool:

```bash
uv run sparql-agent config migrate config-old.yaml config-new.yaml
```

## Troubleshooting

### Configuration Not Found

```bash
# Check configuration search paths
uv run sparql-agent config paths

# Specify custom location
uv run sparql-agent --config /path/to/config.yaml query "test"
```

### Environment Variables Not Working

```bash
# Verify environment variables are set
env | grep SPARQL_AGENT

# Use verbose mode to see configuration loading
uv run sparql-agent -vv config show
```

### API Key Issues

```bash
# Test API key
uv run sparql-agent config test-llm

# Use different provider
export SPARQL_AGENT_LLM_PROVIDER=openai
```

## Best Practices

1. **Use environment variables for secrets**
   ```yaml
   llm:
     api_key: ${ANTHROPIC_API_KEY}  # Not hardcoded
   ```

2. **Use profiles for different environments**
   ```yaml
   profiles:
     development: {...}
     production: {...}
   ```

3. **Enable caching for better performance**
   ```yaml
   cache:
     enabled: true
     backend: redis  # For production
   ```

4. **Set appropriate timeouts**
   ```yaml
   query:
     timeout: 60  # Longer for complex queries
   ```

5. **Use validation before execution**
   ```yaml
   query:
     validate_before_execution: true
   ```

## Next Steps

- [CLI Reference](cli.md) - Command-line usage
- [Python API](api.md) - Programmatic usage
- [Best Practices](best-practices/production.md) - Production deployment
