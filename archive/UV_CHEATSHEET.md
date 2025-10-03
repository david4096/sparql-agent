# UV Cheat Sheet for SPARQL Agent

Quick reference for common UV commands used in this project.

## Project Setup

```bash
# Initialize project (first time)
uv sync

# Add new dependency
uv add requests
uv add --dev pytest

# Remove dependency
uv remove requests

# Update all dependencies
uv sync --upgrade
```

## Running Code

```bash
# Run any Python script/command
uv run python script.py
uv run python -c "import sparql_agent; print('works!')"

# Run CLI commands
uv run sparql-agent --help
uv run sparql-agent query "find proteins" --endpoint https://sparql.uniprot.org/sparql

# Start services
uv run sparql-agent-server       # Web server
uv run sparql-agent-mcp          # MCP server
```

## Development

```bash
# Run tests
uv run pytest                    # All tests
uv run pytest tests/test_core.py # Specific file
uv run pytest -v                 # Verbose
uv run pytest --cov=sparql_agent # With coverage

# Code quality
uv run black .                   # Format code
uv run ruff check .              # Lint code
uv run ruff check --fix .        # Fix linting issues
uv run mypy src/                 # Type checking
uv run isort .                   # Sort imports
```

## Common Tasks

```bash
# Test major components
uv run python -c "from sparql_agent.core import *; print('✅ Core')"
uv run python -c "from sparql_agent.ontology import *; print('✅ Ontology')"
uv run python -c "from sparql_agent.llm import *; print('✅ LLM')"
uv run python -c "from sparql_agent.query import *; print('✅ Query')"

# Run examples
uv run python src/sparql_agent/ontology/example_usage.py
uv run python src/sparql_agent/query/examples.py

# Interactive shell
uv run python -m sparql_agent.cli.interactive
uv run python # Just get a Python shell with everything available

# Quick connectivity test
uv run python -c "
from sparql_agent.discovery import EndpointPinger
pinger = EndpointPinger()
result = pinger.ping('https://sparql.uniprot.org/sparql', timeout=10)
print('✅ UniProt online' if result.is_healthy else '❌ UniProt offline')
"
```

## No More PYTHONPATH Issues!

❌ **Old way (error-prone):**
```bash
export PYTHONPATH=src:$PYTHONPATH
python script.py  # May fail with import errors
```

✅ **New way (always works):**
```bash
uv run python script.py  # Automatically handles paths
```

## Environment Management

```bash
# UV automatically creates .venv/
# No need to manually activate/deactivate

# Check environment
uv run python --version
uv run pip list

# Clean reinstall
rm -rf .venv
uv sync
```

## Key Benefits

- 🚀 **10-100x faster** than pip
- 🔒 **Lock file** for reproducible builds
- 🛡️ **No PYTHONPATH** headaches
- 🎯 **Zero configuration** virtual environments
- 📦 **Works everywhere** - CI, Docker, local dev

## Migration Guide

| Old Command | New Command |
|-------------|-------------|
| `pip install -r requirements.txt` | `uv sync` |
| `source venv/bin/activate && python script.py` | `uv run python script.py` |
| `pip install package` | `uv add package` |
| `pip install -e .` | `uv sync` (after first `uv init`) |
| `python -m pytest` | `uv run pytest` |

Just prefix everything with `uv run` and forget about virtual environments! 🎉