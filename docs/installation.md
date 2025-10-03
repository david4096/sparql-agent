# SPARQL Agent Installation Guide

Complete installation instructions for SPARQL Agent with UV package manager.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation Methods](#installation-methods)
- [Post-Installation](#post-installation)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software

1. **Python 3.9 or higher**
   ```bash
   python --version  # Should show 3.9 or higher
   ```

2. **UV Package Manager** (Recommended)

   UV is a fast, modern Python package manager that handles dependencies efficiently.

   ```bash
   # macOS and Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Windows (PowerShell)
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

   # Via pip (if you prefer)
   pip install uv

   # Verify installation
   uv --version
   ```

### Optional Dependencies

- **MCP SDK**: For Model Context Protocol server functionality
  ```bash
  pip install mcp
  ```

- **Pandas**: For advanced data formatting
  ```bash
  uv add pandas
  ```

## Installation Methods

### Method 1: Using UV (Recommended)

UV provides the cleanest installation with automatic dependency management and no PYTHONPATH issues.

#### Development Installation (from source)

```bash
# Clone the repository
git clone https://github.com/david4096/sparql-agent.git
cd sparql-agent

# Install all dependencies and create virtual environment
uv sync

# This command will:
# - Create a .venv directory with Python environment
# - Install all dependencies from pyproject.toml
# - Install the package in editable mode
# - Set up all CLI entry points
```

#### Using the Installation

After `uv sync`, you can run commands in two ways:

1. **Using `uv run` (No activation needed):**
   ```bash
   # From any directory
   uv run --directory /path/to/sparql-agent sparql-agent --help
   uv run --directory /path/to/sparql-agent sparql-agent-server --help
   uv run --directory /path/to/sparql-agent sparql-agent-mcp --help

   # From within the project directory
   uv run sparql-agent query "Find all proteins"
   uv run sparql-agent-server --port 8000
   ```

2. **Activate the virtual environment:**
   ```bash
   # Activate .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

   # Now use commands directly
   sparql-agent --help
   sparql-agent-server --port 8000
   sparql-agent-mcp
   ```

### Method 2: Traditional pip Installation

If you prefer traditional pip:

```bash
# Clone repository
git clone https://github.com/david4096/sparql-agent.git
cd sparql-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Install in editable mode
pip install -e .

# Or with development dependencies
pip install -e ".[dev]"
```

### Method 3: From PyPI (When Published)

Once published, you can install directly:

```bash
# Using UV
uv add sparql-agent

# Using pip
pip install sparql-agent
```

## Post-Installation

### Configuration

1. **Create configuration directory:**
   ```bash
   mkdir -p ~/.sparql-agent
   ```

2. **Create configuration file:**

   Create `~/.sparql-agent/config.yaml`:

   ```yaml
   # LLM Configuration
   llm:
     provider: anthropic  # or openai
     model_name: claude-3-5-sonnet-20241022
     api_key: ${ANTHROPIC_API_KEY}  # Use environment variable
     temperature: 0.0
     max_tokens: 4096

   # SPARQL Endpoints
   endpoints:
     default:
       url: https://sparql.uniprot.org/sparql
       timeout: 30
       description: UniProt SPARQL Endpoint

     wikidata:
       url: https://query.wikidata.org/sparql
       timeout: 30
       description: Wikidata Query Service

   # Ontology Settings
   ontology:
     ols_api_base_url: https://www.ebi.ac.uk/ols4/api
     cache_enabled: true
     cache_dir: ~/.sparql-agent/ontology-cache
     default_ontologies:
       - efo
       - mondo
       - hp
       - go

   # Query Settings
   query:
     default_limit: 100
     max_limit: 10000
     timeout: 60
     enable_validation: true
     enable_optimization: true

   # Logging
   logging:
     level: INFO
     log_dir: ~/.sparql-agent/logs
     json_enabled: false
   ```

3. **Set environment variables:**

   Add to your `~/.bashrc` or `~/.zshrc`:

   ```bash
   # LLM API Keys
   export ANTHROPIC_API_KEY="sk-ant-your-key-here"
   export OPENAI_API_KEY="sk-..."

   # Optional: Override default config location
   export SPARQL_AGENT_CONFIG=~/.sparql-agent/config.yaml
   ```

## Verification

### Test CLI Commands

Verify all three CLI entry points work:

```bash
# Main CLI
uv run sparql-agent --help
uv run sparql-agent version

# Web server
uv run sparql-agent-server --help

# MCP server (requires MCP SDK)
uv run sparql-agent-mcp --help
```

### Test Basic Functionality

```bash
# Test endpoint discovery
uv run sparql-agent discover https://query.wikidata.org/sparql

# Test query (requires LLM API key configured)
uv run sparql-agent query "Find all classes" \
  --endpoint https://query.wikidata.org/sparql \
  --no-execute \
  --show-sparql

# Test configuration
uv run sparql-agent config show
```

## Troubleshooting

See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for detailed troubleshooting guidance.

### Quick Fixes

**Command not found:**
```bash
# Make sure you're using uv run
uv run sparql-agent --help

# Or activate the virtual environment
source .venv/bin/activate
sparql-agent --help
```

**Import errors:**
```bash
# Re-sync dependencies
uv sync --force
```

**MCP server not working:**
```bash
# Install MCP SDK
pip install mcp
```

## Next Steps

- Read the [User Guide](./USER_GUIDE.md) for detailed usage instructions
- Check out [Examples](../examples/) for sample queries and scripts
- Review [API Documentation](./API.md) for Python API reference
