# SPARQL Agent

An intelligent SPARQL query agent with OWL ontology support and LLM integration for semantic web querying and knowledge graph exploration.

## Overview

SPARQL Agent is a comprehensive Python framework that combines the power of SPARQL querying with Large Language Models (LLMs) and OWL ontology reasoning. It provides an intelligent interface for interacting with RDF knowledge graphs, automatic query generation, and schema discovery.

## Features

- **OWL Ontology Support**: Full support for OWL ontologies with reasoning capabilities via owlready2
- **EBI OLS4 Integration**: Direct integration with the EMBL-EBI Ontology Lookup Service (OLS4) for accessing biomedical ontologies
- **LLM Integration**: Support for multiple LLM providers (Anthropic Claude, OpenAI GPT) for natural language to SPARQL translation
- **Schema Discovery**: Automatic discovery and analysis of RDF/OWL schema structures
- **Query Generation**: Intelligent SPARQL query generation from natural language
- **Query Execution**: Robust SPARQL query execution with multiple endpoint support
- **Result Formatting**: Flexible formatting of query results (JSON, CSV, RDF, etc.)
- **MCP Support**: Model Context Protocol integration for AI agent workflows
- **Web Interface**: FastAPI-based REST API and web UI
- **CLI Tool**: Command-line interface for all operations

## Architecture

```
sparql-agent/
├── core/           # Core agent logic and base classes
├── ontology/       # OWL ontology parsing and OLS4 client
├── discovery/      # Schema discovery and analysis
├── schema/         # Schema representation and management
├── llm/            # LLM integration (Anthropic, OpenAI)
├── query/          # SPARQL query generation and validation
├── execution/      # Query execution and endpoint management
├── formatting/     # Result formatting and serialization
├── mcp/            # Model Context Protocol server
├── cli/            # Command-line interface
├── endpoints/      # SPARQL endpoint configurations
└── web/            # Web API and UI
```

## Installation

### Quick Install

```bash
# 1. Install UV (fast Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone and install
git clone https://github.com/david4096/sparql-agent.git
cd sparql-agent
uv sync

# 3. Run commands
uv run sparql-agent --help
```

That's it! UV handles everything automatically - no PYTHONPATH, no activation needed.

### Detailed Installation

#### Prerequisites

- **Python 3.9+** - Check with `python --version`
- **UV** - Modern package manager (recommended)

```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh  # macOS/Linux
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"  # Windows
```

#### Method 1: Using UV (Recommended)

```bash
git clone https://github.com/david4096/sparql-agent.git
cd sparql-agent
uv sync  # Creates .venv and installs everything

# Run commands from anywhere
uv run sparql-agent --help
uv run sparql-agent-server --help
uv run sparql-agent-mcp --help
```

#### Method 2: Traditional Installation

```bash
git clone https://github.com/david4096/sparql-agent.git
cd sparql-agent
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e .
```

#### From PyPI (when published)

```bash
uv add sparql-agent  # or: pip install sparql-agent
```

### Post-Installation Setup

1. **Configure API keys:**
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."
   export OPENAI_API_KEY="sk-..."
   ```

2. **Test installation:**
   ```bash
   uv run sparql-agent version
   uv run sparql-agent discover https://query.wikidata.org/sparql --fast
   ```

3. **Optional: Create config file**
   ```bash
   mkdir -p ~/.sparql-agent
   # See docs/INSTALLATION.md for config examples
   ```

For detailed installation instructions, troubleshooting, and configuration, see:
- **[Complete Installation Guide](docs/INSTALLATION.md)**
- **[Troubleshooting Guide](docs/TROUBLESHOOTING.md)**

## Quick Start

### CLI Usage

The SPARQL Agent provides comprehensive CLI tools and user interfaces:

#### 1. Main CLI - `sparql-agent`

```bash
# Query with natural language (works reliably, returns manageable results)
uv run sparql-agent query "Find 10 people born in Paris" \
  --endpoint https://query.wikidata.org/sparql \
  --limit 10

# More complex queries that work well
uv run sparql-agent query "Show me 5 Nobel Prize winners in Physics with their birth years" \
  --endpoint https://query.wikidata.org/sparql

uv run sparql-agent query "Find proteins involved in diabetes, limit 20" \
  --endpoint https://sparql.uniprot.org/sparql

# Ontology-guided queries with context
uv run sparql-agent query "Find cancer-related genes" \
  --endpoint https://rdfportal.org/biomedical/sparql \
  --ontology-context cancer_ontology.ttl \
  --examples cancer_queries.yaml

# Discover endpoint capabilities and save configuration
uv run sparql-agent discover https://query.wikidata.org/sparql \
  --generate-void \
  --generate-shex \
  --save-config wikidata.yaml

# Search ontologies
uv run sparql-agent ontology search "diabetes" \
  --ontology efo \
  --format json-ld

# Validate and optimize queries
uv run sparql-agent validate query.sparql --optimize --explain

# Interactive mode with history
uv run sparql-agent interactive --save-session --endpoint-config endpoints.yaml
```

#### 2. Web UI - `sparql-agent-web-ui`

```bash
# Start interactive web chat interface
uv run sparql-agent-web-ui --port 5001

# Features:
# - Natural language ↔ SPARQL translation
# - Multiple endpoint support with testing
# - Result visualization and export
# - Session history and explanations
# - Performance metrics tracking

# Visit: http://localhost:5001
```

#### 3. Terminal UI - `sparql-agent-tui`

```bash
# Start rich terminal interface
uv run sparql-agent-tui

# Features:
# - Interactive natural language queries
# - Real-time SPARQL generation and execution
# - Performance metrics and token usage
# - Session history and endpoint management
# - Rich terminal formatting and help
```

#### 4. REST API Server - `sparql-agent-server`

```bash
# Start REST API server
uv run sparql-agent-server --host 0.0.0.0 --port 8000

# With metrics and monitoring
uv run sparql-agent-server --enable-metrics --log-level debug

# Visit: http://localhost:8000/docs for API documentation
```

#### 5. MCP Server - `sparql-agent-mcp`

```bash
# Start Model Context Protocol server
uv run sparql-agent-mcp --port 3000

# With ontology context management
uv run sparql-agent-mcp --config mcp-config.json --ontology-cache ~/.sparql-agent/ontologies
```

### Python API (Streamlined & Easy to Import)

```python
from sparql_agent import SPARQLAgent, quick_query
from sparql_agent.llm import create_anthropic_provider
from sparql_agent.query import quick_generate
from sparql_agent.execution import execute_query
from sparql_agent.discovery import discover_endpoint, generate_void, generate_shex
from sparql_agent.ontology import OLSClient, OWLParser

# Quick one-liner queries
results = quick_query(
    "Find 10 people born in Paris",
    endpoint="https://query.wikidata.org/sparql",
    api_key="your-api-key"
)

# Full-featured agent with context management
agent = SPARQLAgent(
    endpoint="https://sparql.uniprot.org/sparql",
    llm_provider="anthropic",
    api_key="your-api-key",
    ontology_context=["go.owl", "uniprot.ttl"],
    example_queries="protein_queries.yaml",
    cache_dir="~/.sparql-agent/cache"
)

# Natural language query with performance metrics
result = agent.query(
    "Find human proteins involved in cell division",
    include_explanation=True,
    return_metrics=True
)

print(f"Found {len(result.data)} results in {result.metrics.total_time}s")
print(f"LLM tokens used: {result.metrics.llm_tokens}")
print(f"Explanation: {result.explanation}")

# Load and query OWL ontology with reasoning
owl_parser = OWLParser("gene_ontology.owl")
classes = owl_parser.get_classes()
properties = owl_parser.get_properties()

# Query OLS4 with JSON-LD output
ols = OLSClient()
terms = ols.search("diabetes", ontology="efo", format="json-ld")

# Endpoint discovery with VoID and SHEX generation
endpoint_info = discover_endpoint(
    "https://rdfportal.org/sparql",
    generate_void=True,
    generate_shex=True,
    save_config=True
)

# Reuse discovered information for better queries
agent_with_context = SPARQLAgent(
    endpoint="https://rdfportal.org/sparql",
    endpoint_config=endpoint_info,
    void_description=endpoint_info.void,
    shex_schema=endpoint_info.shex
)
```

## Real-World Examples

### Working Queries That Return Useful Results

```bash
# Wikidata examples (tested and reliable)
uv run sparql-agent query "Find 10 Nobel Prize winners in Medicine with their birth year and country" \
  --endpoint https://query.wikidata.org/sparql

uv run sparql-agent query "Show me 5 programming languages created after 2000 with their creators" \
  --endpoint https://query.wikidata.org/sparql

uv run sparql-agent query "List 8 European capitals with their population" \
  --endpoint https://query.wikidata.org/sparql

# UniProt examples (protein research)
uv run sparql-agent query "Find 15 human proteins involved in DNA repair, show their names and functions" \
  --endpoint https://sparql.uniprot.org/sparql

uv run sparql-agent query "Show me proteins from E. coli that are enzymes, limit to 20" \
  --endpoint https://sparql.uniprot.org/sparql

# RDF Portal examples (FAIR data)
uv run sparql-agent query "Find datasets related to cancer research, show title and creator" \
  --endpoint https://rdfportal.org/sparql

uv run sparql-agent query "List 10 biomedical ontologies with their descriptions" \
  --endpoint https://rdfportal.org/biomedical/sparql

# EBI OLS4 examples (ontology data)
uv run sparql-agent query "Find 12 terms related to heart disease in medical ontologies" \
  --endpoint https://www.ebi.ac.uk/ols4/api/sparql
```

### Complex Multi-Clause Queries

```bash
# Complex Wikidata query with multiple conditions
uv run sparql-agent query "Find Nobel Prize winners in Physics who were also university professors, born after 1950, show their name, birth year, and university" \
  --endpoint https://query.wikidata.org/sparql

# Complex UniProt query with protein properties
uv run sparql-agent query "Find human membrane proteins involved in neurotransmitter transport, with molecular weight between 40-60 kDa, show protein name, gene name, and cellular location" \
  --endpoint https://sparql.uniprot.org/sparql

# Complex biomedical data query
uv run sparql-agent query "Find cancer-related genes that are also drug targets, include the gene symbol, cancer type, and drug name" \
  --endpoint https://rdfportal.org/biomedical/sparql
```

### Ontology and VoID Integration Examples

```bash
# Query with ontology context
uv run sparql-agent query "Find genes involved in Alzheimer's disease pathways" \
  --endpoint https://rdfportal.org/biomedical/sparql \
  --ontology-context gene_ontology.owl,disease_ontology.owl \
  --include-reasoning

# Generate VoID description for endpoint
uv run sparql-agent discover https://query.wikidata.org/sparql \
  --generate-void \
  --output wikidata_void.ttl

# Generate SHEX schema from endpoint
uv run sparql-agent discover https://sparql.uniprot.org/sparql \
  --generate-shex \
  --sample-size 1000 \
  --output uniprot_schema.shex

# Use discovered metadata for better queries
uv run sparql-agent query "Find biological processes" \
  --endpoint https://rdfportal.org/sparql \
  --void-file endpoint_void.ttl \
  --shex-file endpoint_schema.shex
```

### Performance Monitoring Examples

```bash
# Query with detailed metrics
uv run sparql-agent query "Find 5 recent scientific publications about machine learning" \
  --endpoint https://query.wikidata.org/sparql \
  --show-metrics \
  --log-performance metrics.json

# Batch testing with performance analysis
uv run sparql-agent batch-test queries.yaml \
  --endpoints endpoints.yaml \
  --metrics-output performance_report.json \
  --include-token-usage \
  --regression-detection

# Endpoint performance comparison
uv run sparql-agent benchmark \
  --query "Find 10 people born in 1970" \
  --endpoints wikidata,dbpedia \
  --iterations 5 \
  --report benchmark_report.html
```

## Configuration

Create a configuration file `~/.sparql-agent/config.yaml`:

```yaml
llm:
  provider: anthropic  # or openai
  model: claude-3-5-sonnet-20241022
  api_key: ${ANTHROPIC_API_KEY}
  track_tokens: true
  metrics_db: ~/.sparql-agent/metrics.db

endpoints:
  default: https://sparql.uniprot.org/sparql
  wikidata: https://query.wikidata.org/sparql
  dbpedia: https://dbpedia.org/sparql
  rdf_portal_fair: https://rdfportal.org/sparql
  rdf_portal_bio: https://rdfportal.org/biomedical/sparql
  ebi_ols4: https://www.ebi.ac.uk/ols4/api/sparql

ontologies:
  ols_base_url: https://www.ebi.ac.uk/ols4/api
  local_cache: ~/.sparql-agent/ontologies
  context_files:
    - gene_ontology.owl
    - uniprot_core.ttl
    - schema_org.jsonld

discovery:
  void_cache: ~/.sparql-agent/void
  shex_cache: ~/.sparql-agent/shex
  auto_generate: true
  sample_size: 1000

query:
  timeout: 30
  max_results: 1000
  enable_reasoning: true
  cache_results: true
  save_session: true

performance:
  metrics_enabled: true
  log_slow_queries: true
  slow_query_threshold: 10  # seconds
  regression_detection: true
  benchmark_history: 30  # days

mcp:
  port: 3000
  database: ~/.sparql-agent/mcp.db
  log_queries: true
  store_discovery: true
  session_timeout: 3600  # seconds
```

### Session Management and Reusable Discovery

```bash
# Discover endpoint and save comprehensive metadata
uv run sparql-agent discover https://rdfportal.org/sparql \
  --generate-void \
  --generate-shex \
  --sample-queries \
  --save-examples \
  --output-dir ~/.sparql-agent/endpoints/rdf-portal

# Use saved discovery for improved queries
uv run sparql-agent query "Find FAIR datasets" \
  --use-discovery ~/.sparql-agent/endpoints/rdf-portal \
  --context-aware

# Share discovery information
uv run sparql-agent export-config \
  --endpoint https://rdfportal.org/sparql \
  --output rdfportal-config.yaml \
  --include-examples
```

### MCP Server with Rich Database

The MCP server includes comprehensive logging and database facilities:

```bash
# Start MCP server with full logging
uv run sparql-agent-mcp \
  --database-url sqlite:///~/.sparql-agent/mcp.db \
  --log-level debug \
  --enable-metrics \
  --store-discoveries \
  --track-performance

# Server stores:
# - Endpoint discovery information (VoID, SHEX, examples)
# - Query success/failure pairs for learning
# - Performance metrics and regression detection
# - LLM token usage and response times
# - Session history and context
```

Database schema includes:
- **endpoints**: Discovered endpoint metadata
- **queries**: Successful/failed query pairs
- **performance**: Response times, token usage
- **discoveries**: VoID descriptions, SHEX schemas
- **sessions**: User sessions and context
- **examples**: Working query examples

## OWL Ontology Support

SPARQL Agent provides comprehensive OWL ontology support:

### Ontology Loading

```python
from sparql_agent.ontology import OWLParser

# Load from file
parser = OWLParser("ontology.owl")

# Load from URL
parser = OWLParser("http://purl.obolibrary.org/obo/go.owl")

# Access ontology metadata
print(parser.get_metadata())
print(parser.get_classes())
print(parser.get_properties())
```

### OLS4 Integration

```python
from sparql_agent.ontology import OLSClient

ols = OLSClient()

# Search across all ontologies
results = ols.search("diabetes")

# Search in specific ontology
results = ols.search("diabetes", ontology="efo")

# Get term details
term = ols.get_term("efo", "EFO_0000400")

# Get ontology information
ontology = ols.get_ontology("efo")
```

## LLM Integration

The agent supports multiple LLM providers for natural language query translation:

- **Anthropic Claude**: Claude 3.5 Sonnet, Claude 3 Opus, etc.
- **OpenAI**: GPT-4, GPT-3.5-turbo, etc.

```python
from sparql_agent.llm import AnthropicClient, OpenAIClient

# Anthropic
llm = AnthropicClient(api_key="sk-ant-...")
response = llm.generate_query("Find all proteins")

# OpenAI
llm = OpenAIClient(api_key="sk-...")
response = llm.generate_query("Find all proteins")
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=sparql_agent --cov-report=html

# Run specific test file
pytest tests/test_ontology.py
```

## Development

### Code Quality

```bash
# Format code
black src/ tests/
isort src/ tests/

# Lint
ruff check src/ tests/

# Type checking
mypy src/
```

### Project Structure

The project follows a modular architecture:

- **core**: Base classes and agent logic
- **ontology**: OWL parsing and OLS4 integration
- **discovery**: Automated schema discovery
- **llm**: LLM provider integrations
- **query**: SPARQL query generation and validation
- **execution**: Query execution engine
- **formatting**: Result serialization
- **mcp**: Model Context Protocol server
- **cli**: Command-line interface
- **web**: REST API and web interface

## Dependencies

### Core Dependencies

- **rdflib**: RDF processing and SPARQL
- **SPARQLWrapper**: SPARQL endpoint communication
- **owlready2**: OWL ontology processing and reasoning
- **pronto**: Ontology format parsing
- **anthropic**: Anthropic Claude API
- **openai**: OpenAI API
- **click**: CLI framework
- **fastapi**: Web framework
- **pydantic**: Data validation

### Development Dependencies

- **pytest**: Testing framework
- **black**: Code formatting
- **mypy**: Static type checking
- **ruff**: Fast Python linter

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run code quality checks
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Citation

If you use SPARQL Agent in your research, please cite:

```bibtex
@software{sparql_agent,
  title = {SPARQL Agent: Intelligent SPARQL Query Agent with OWL Support},
  author = {Your Name},
  year = {2024},
  url = {https://github.com/david4096/sparql-agent}
}
```

## Acknowledgments

- EMBL-EBI for the Ontology Lookup Service (OLS4)
- The RDFlib and owlready2 communities
- Anthropic and OpenAI for LLM APIs

## Support

- GitHub Issues: https://github.com/david4096/sparql-agent/issues
- Documentation: https://github.com/david4096/sparql-agent
- Email: david@example.com
