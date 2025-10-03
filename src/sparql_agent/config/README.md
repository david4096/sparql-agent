# SPARQL Agent Configuration System

Comprehensive configuration management system for the SPARQL Agent with Pydantic settings, environment variable support, and YAML configuration files.

## Overview

The configuration system provides:

- **Pydantic-based settings** with type validation and environment variable support
- **YAML configuration files** for endpoints, ontologies, prompts, and logging
- **Runtime configuration updates** for dynamic behavior
- **Environment variable overrides** with `SPARQL_AGENT_` prefix
- **OWL ontology cache settings** for offline and performance optimization
- **EBI OLS4 API integration** for ontology services
- **Multi-endpoint support** for federated SPARQL queries

## Directory Structure

```
config/
├── __init__.py           # Module exports and utilities
├── settings.py           # Pydantic settings classes
├── endpoints.yaml        # SPARQL endpoint configurations
├── ontologies.yaml       # EBI OLS4 ontology configurations
├── prompts.yaml          # LLM prompt templates
└── logging.yaml          # Logging configuration
```

## Quick Start

### Basic Usage

```python
from sparql_agent.config import get_settings

# Get global settings instance
settings = get_settings()

# Access endpoint configuration
uniprot_config = settings.get_endpoint_config('uniprot')
print(f"UniProt URL: {uniprot_config['url']}")

# Access ontology configuration
efo_config = settings.get_ontology_config('efo')
print(f"EFO Description: {efo_config['description']}")

# Get prompt template
nl_to_sparql = settings.get_prompt_template('nl_to_sparql')

# List available resources
print(f"Available endpoints: {settings.list_endpoints()}")
print(f"Available ontologies: {settings.list_ontologies()}")
print(f"Available prompts: {settings.list_prompts()}")
```

### Environment Variables

All settings can be overridden using environment variables:

```bash
# General settings
export SPARQL_AGENT_DEBUG=true

# Ontology settings
export SPARQL_AGENT_ONTOLOGY__OLS_API_BASE_URL=https://custom-ols.org/api
export SPARQL_AGENT_ONTOLOGY__CACHE_ENABLED=false
export SPARQL_AGENT_ONTOLOGY__CACHE_DIR=/custom/cache/path
export SPARQL_AGENT_ONTOLOGY__CACHE_TTL=3600

# Endpoint settings
export SPARQL_AGENT_ENDPOINT__DEFAULT_TIMEOUT=120
export SPARQL_AGENT_ENDPOINT__MAX_RETRIES=5

# LLM settings
export SPARQL_AGENT_LLM__MODEL_NAME=gpt-4-turbo
export SPARQL_AGENT_LLM__TEMPERATURE=0.2
export SPARQL_AGENT_LLM__API_KEY=your-api-key-here

# Logging settings
export SPARQL_AGENT_LOG__LEVEL=DEBUG
export SPARQL_AGENT_LOG__FILE_ENABLED=true
```

### Runtime Configuration Updates

```python
from sparql_agent.config import get_settings

settings = get_settings()

# Update configuration at runtime
settings.update_config(debug=True)
settings.ontology.cache_enabled = False
settings.llm.temperature = 0.5

# Reload YAML configurations
settings.reload_yaml_configs()
```

## Configuration Components

### 1. Settings (settings.py)

#### SPARQLAgentSettings

Main configuration class with nested settings for different components.

```python
class SPARQLAgentSettings(BaseSettings):
    ontology: OntologySettings      # Ontology service configuration
    endpoint: EndpointSettings      # SPARQL endpoint configuration
    llm: LLMSettings                # LLM integration configuration
    logging: LoggingSettings        # Logging configuration
    config_dir: Path                # Configuration directory
    debug: bool                     # Debug mode flag
```

#### OntologySettings

Configuration for EBI OLS4 API and ontology caching:

```python
class OntologySettings(BaseSettings):
    # EBI OLS4 API
    ols_api_base_url: str = "https://www.ebi.ac.uk/ols4/api"
    ols_timeout: int = 30
    ols_max_retries: int = 3

    # Cache settings
    cache_enabled: bool = True
    cache_dir: Path = Path.home() / ".cache" / "sparql_agent" / "ontologies"
    cache_ttl: int = 86400  # 24 hours
    cache_max_size_mb: int = 500

    # Default ontologies
    default_ontologies: List[str] = ["efo", "mondo", "hp", "uberon", "go"]
```

#### EndpointSettings

Configuration for SPARQL endpoint connections:

```python
class EndpointSettings(BaseSettings):
    default_timeout: int = 60
    max_retries: int = 3
    retry_delay: float = 1.0
    user_agent: str = "SPARQL-Agent/1.0"

    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_calls: int = 10
    rate_limit_period: int = 60
```

#### LLMSettings

Configuration for LLM integration:

```python
class LLMSettings(BaseSettings):
    model_name: str = "gpt-4"
    temperature: float = 0.1
    max_tokens: int = 2000
    api_key: Optional[str] = None
    api_base_url: Optional[str] = None

    # Prompt configuration
    use_few_shot: bool = True
    max_examples: int = 5
```

#### LoggingSettings

Configuration for logging behavior:

```python
class LoggingSettings(BaseSettings):
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # File logging
    file_enabled: bool = False
    file_path: Optional[Path] = None
    file_max_bytes: int = 10485760  # 10MB
    file_backup_count: int = 5

    # Structured logging
    json_enabled: bool = False
```

### 2. Endpoints (endpoints.yaml)

Defines SPARQL endpoint configurations with metadata, prefixes, and examples.

#### Configured Endpoints

- **UniProt**: Protein data and annotations
- **ClinVar**: Genetic variants and clinical significance
- **RDFPortal**: Multi-domain RDF data portal
- **Wikidata**: General knowledge base
- **EBI RDF Platform**: Biomedical data from EBI
- **DBpedia**: Wikipedia-derived structured data

#### Endpoint Structure

```yaml
endpoints:
  uniprot:
    name: "UniProt"
    url: "https://sparql.uniprot.org/sparql/"
    description: "Universal Protein Resource SPARQL endpoint"
    timeout: 60
    rate_limit:
      enabled: true
      calls: 10
      period: 60
    prefixes:
      up: "http://purl.uniprot.org/core/"
      uniprotkb: "http://purl.uniprot.org/uniprot/"
    examples:
      - name: "Get protein information"
        query: |
          PREFIX up: <http://purl.uniprot.org/core/>
          SELECT ?protein ?name
          WHERE { ... }
    features:
      - "Protein annotations"
      - "Taxonomy information"
```

### 3. Ontologies (ontologies.yaml)

Defines ontology metadata and EBI OLS4 integration settings.

#### Configured Ontologies

- **EFO** (Experimental Factor Ontology): Disease and experimental variables
- **MONDO** (Mondo Disease Ontology): Harmonized disease ontology
- **HP** (Human Phenotype Ontology): Phenotypic abnormalities
- **UBERON** (Multi-species Anatomy): Cross-species anatomy
- **GO** (Gene Ontology): Gene function and process
- **ChEBI**: Chemical entities
- **PR** (Protein Ontology): Protein-related entities
- **SO** (Sequence Ontology): Sequence features
- **CL** (Cell Ontology): Cell types
- **NCBITaxon**: Organismal classification

#### Ontology Structure

```yaml
ontologies:
  efo:
    id: "efo"
    name: "Experimental Factor Ontology"
    namespace: "http://www.ebi.ac.uk/efo/"
    prefix: "EFO"
    description: "An application ontology..."
    homepage: "https://www.ebi.ac.uk/efo/"
    download_url: "http://www.ebi.ac.uk/efo/efo.owl"
    categories:
      - "disease"
      - "phenotype"
    cache_enabled: true
    preload: true
    use_cases:
      - "Disease annotation"
      - "Experimental design"
```

#### OLS4 Configuration

```yaml
ols_config:
  api_base_url: "https://www.ebi.ac.uk/ols4/api"
  sparql_endpoint: "https://www.ebi.ac.uk/ols4/sparql"
  timeout: 30
  max_retries: 3
  page_size: 20
```

### 4. Prompts (prompts.yaml)

LLM prompt templates for various agent tasks.

#### Available Prompts

- **nl_to_sparql**: Natural language to SPARQL query generation
- **query_refinement**: Refine queries based on results or errors
- **result_interpretation**: Interpret query results in natural language
- **ontology_suggestion**: Suggest relevant ontology terms
- **query_optimization**: Optimize queries for performance
- **error_analysis**: Analyze and fix query errors
- **federated_query**: Plan federated queries across endpoints
- **entity_linking**: Link text entities to RDF resources
- **query_explanation**: Explain SPARQL queries in natural language
- **schema_discovery**: Discover dataset schema and patterns
- **data_quality**: Assess RDF data quality
- **answer_synthesis**: Synthesize answers from multiple results
- **clarification**: Ask clarifying questions for ambiguous requests
- **batch_query**: Generate multiple related queries

#### Prompt Structure

```yaml
prompts:
  nl_to_sparql:
    name: "Natural Language to SPARQL"
    description: "Convert natural language questions to SPARQL queries"
    template: |
      You are an expert SPARQL query generator...

      Question: {question}

      Guidelines:
      1. Use appropriate prefixes
      2. Generate efficient queries
      ...

      SPARQL Query:
    parameters:
      - "question"
      - "endpoints"
      - "ontologies"
    examples:
      - question: "Find all proteins associated with diabetes"
        output: |
          PREFIX up: <http://purl.uniprot.org/core/>
          SELECT ?protein ?name
          WHERE { ... }
```

### 5. Logging (logging.yaml)

Python logging configuration in dictConfig format.

#### Formatters

- **standard**: Basic timestamp and level
- **detailed**: Includes function name and line number
- **json**: Structured JSON logging
- **colored**: Colored console output

#### Handlers

- **console**: Standard output with colored formatting
- **file**: Rotating file handler for general logs
- **error_file**: Separate file for errors
- **json_file**: JSON-formatted logs
- **query_file**: Dedicated query logging
- **performance_file**: Performance metrics

#### Loggers

- `sparql_agent`: Main application logger
- `sparql_agent.query`: Query execution logger
- `sparql_agent.ontology`: Ontology service logger
- `sparql_agent.llm`: LLM integration logger
- `sparql_agent.performance`: Performance monitoring
- `sparql_agent.errors`: Error tracking

## Advanced Usage

### Custom Configuration Directory

```python
from sparql_agent.config import SPARQLAgentSettings

settings = SPARQLAgentSettings(config_dir="/custom/config/path")
```

### Configuration Validation

```python
from sparql_agent.config import validate_configuration

is_valid, errors = validate_configuration()
if not is_valid:
    for error in errors:
        print(f"Configuration error: {error}")
```

### Print Configuration

```python
from sparql_agent.config import print_configuration

# Basic summary
print_configuration()

# Verbose output with all details
print_configuration(verbose=True)
```

### Export Configuration

```python
from sparql_agent.config import export_configuration

# Export as JSON
json_config = export_configuration(format="json")

# Export as YAML
yaml_config = export_configuration(format="yaml")
```

### Accessing Sub-configurations

```python
from sparql_agent.config import get_settings

settings = get_settings()

# Ontology settings
print(f"Cache directory: {settings.ontology.cache_dir}")
print(f"OLS API: {settings.ontology.ols_api_base_url}")

# Endpoint settings
print(f"Timeout: {settings.endpoint.default_timeout}")
print(f"Rate limiting: {settings.endpoint.rate_limit_enabled}")

# LLM settings
print(f"Model: {settings.llm.model_name}")
print(f"Temperature: {settings.llm.temperature}")

# Convert to dictionary
config_dict = settings.to_dict()
```

## Configuration Profiles

Use environment-specific configuration by setting different values:

### Development

```bash
export SPARQL_AGENT_DEBUG=true
export SPARQL_AGENT_LOG__LEVEL=DEBUG
export SPARQL_AGENT_ONTOLOGY__CACHE_ENABLED=true
```

### Testing

```bash
export SPARQL_AGENT_DEBUG=false
export SPARQL_AGENT_LOG__LEVEL=WARNING
export SPARQL_AGENT_ONTOLOGY__CACHE_ENABLED=false
export SPARQL_AGENT_ENDPOINT__DEFAULT_TIMEOUT=30
```

### Production

```bash
export SPARQL_AGENT_DEBUG=false
export SPARQL_AGENT_LOG__LEVEL=INFO
export SPARQL_AGENT_LOG__FILE_ENABLED=true
export SPARQL_AGENT_LOG__JSON_ENABLED=true
export SPARQL_AGENT_ONTOLOGY__CACHE_ENABLED=true
export SPARQL_AGENT_ENDPOINT__RATE_LIMIT_ENABLED=true
```

## Best Practices

1. **Use environment variables for secrets**: Never commit API keys or credentials in YAML files
2. **Enable caching in production**: Reduce API calls and improve performance
3. **Configure appropriate timeouts**: Balance between responsiveness and reliability
4. **Use structured logging**: Enable JSON logging for easier log analysis
5. **Monitor rate limits**: Configure rate limiting to avoid overwhelming endpoints
6. **Validate configuration on startup**: Use `validate_configuration()` to catch issues early
7. **Separate concerns**: Use different log files for queries, errors, and performance
8. **Regular cache maintenance**: Set appropriate TTL and size limits for ontology cache

## Troubleshooting

### Configuration not loading

Check that all YAML files are present and valid:

```bash
ls -l /path/to/config/
python -c "import yaml; yaml.safe_load(open('config/endpoints.yaml'))"
```

### Environment variables not applied

Ensure correct prefix and delimiter:

```bash
# Correct
export SPARQL_AGENT_DEBUG=true
export SPARQL_AGENT_ONTOLOGY__CACHE_ENABLED=false

# Incorrect
export SPARQLAGENT_DEBUG=true  # Missing underscore
export SPARQL_AGENT_ONTOLOGY_CACHE_ENABLED=false  # Single underscore
```

### Cache directory issues

Ensure directory exists and has proper permissions:

```python
from sparql_agent.config import get_settings

settings = get_settings()
cache_dir = settings.ontology.cache_dir
cache_dir.mkdir(parents=True, exist_ok=True)
```

## API Reference

### Functions

#### `get_settings(reload: bool = False) -> SPARQLAgentSettings`

Get or create the global settings instance.

#### `reset_settings() -> None`

Reset the global settings instance (useful for testing).

#### `load_configuration(config_dir=None, reload=False) -> SPARQLAgentSettings`

Load or reload configuration from a specific directory.

#### `validate_configuration(settings=None) -> tuple[bool, list]`

Validate configuration and return (is_valid, errors).

#### `print_configuration(settings=None, verbose=False) -> None`

Print current configuration to stdout.

#### `export_configuration(settings=None, format="json") -> str`

Export configuration as JSON or YAML string.

## Contributing

When adding new configuration options:

1. Add the setting to the appropriate class in `settings.py`
2. Update the corresponding YAML file if needed
3. Add environment variable documentation
4. Update this README with examples
5. Add validation in `validate_configuration()`

## License

MIT License - See LICENSE file for details
