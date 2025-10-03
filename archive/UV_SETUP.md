# UV Setup Guide for SPARQL Agent

This project now uses [UV](https://docs.astral.sh/uv/) for modern Python package management and virtual environment handling. UV eliminates the need to manually manage PYTHONPATH and provides much faster dependency resolution.

## Quick Start

### 1. Install UV
```bash
# macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Via pip
pip install uv
```

### 2. Initialize Project
```bash
cd sparql-agent
uv sync  # Creates .venv and installs all dependencies
```

### 3. Run Commands
```bash
# Run any Python command with dependencies
uv run python -c "from sparql_agent.core import *; print('Working!')"

# Run the CLI
uv run sparql-agent --help

# Run tests
uv run pytest

# Run linting
uv run black src/
uv run ruff check src/
uv run mypy src/

# Start interactive shell
uv run python -m sparql_agent.cli.interactive

# Start web server
uv run sparql-agent-server

# Start MCP server
uv run sparql-agent-mcp
```

## Key Benefits of UV

1. **No PYTHONPATH issues** - UV automatically handles package paths
2. **Fast dependency resolution** - 10-100x faster than pip
3. **Automatic virtual environment** - Creates and manages .venv automatically
4. **Lock file support** - Reproducible builds with uv.lock
5. **Drop-in pip replacement** - Same commands, better performance

## Development Workflow

### Running Tests
```bash
# All tests
uv run pytest

# Specific test file
uv run pytest tests/test_core.py

# With coverage
uv run pytest --cov=sparql_agent --cov-report=html
```

### Code Quality
```bash
# Format code
uv run black .
uv run isort .

# Lint code
uv run ruff check .
uv run mypy src/

# Fix linting issues
uv run ruff check --fix .
```

### Adding Dependencies

```bash
# Add runtime dependency
uv add requests

# Add dev dependency
uv add --dev pytest

# Add specific version
uv add "fastapi>=0.100.0"
```

### Examples and Testing

```bash
# Run OLS client examples
uv run python src/sparql_agent/ontology/example_usage.py

# Run query examples
uv run python src/sparql_agent/query/prompt_engine_examples.py

# Test connectivity
uv run python -c "
from sparql_agent.discovery import EndpointPinger
pinger = EndpointPinger()
result = pinger.ping('https://sparql.uniprot.org/sparql', timeout=10)
print(f'✅ UniProt: {result.response_time_ms}ms' if result.is_healthy else '❌ UniProt offline')
"
```

### Component Testing

```bash
# Test each major component
uv run python -c "from sparql_agent.core import *; print('✅ Core')"
uv run python -c "from sparql_agent.ontology import *; print('✅ Ontology')"
uv run python -c "from sparql_agent.llm import *; print('✅ LLM')"
uv run python -c "from sparql_agent.query import *; print('✅ Query')"
uv run python -c "from sparql_agent.formatting import *; print('✅ Formatting')"
uv run python -c "from sparql_agent.execution import *; print('✅ Execution')"
uv run python -c "from sparql_agent.discovery import *; print('✅ Discovery')"
uv run python -c "from sparql_agent.schema import *; print('✅ Schema')"
```

## Migration from pip/pipenv/poetry

If you were previously using:

### From pip + virtualenv:
```bash
# Old way
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
export PYTHONPATH=src:$PYTHONPATH
python script.py

# New way
uv run python script.py
```

### From poetry:
```bash
# Old way
poetry install
poetry run python script.py

# New way
uv sync
uv run python script.py
```

## Troubleshooting

### UV not found
```bash
# Add UV to PATH (add to ~/.bashrc or ~/.zshrc)
export PATH="$HOME/.cargo/bin:$PATH"
```

### Permission issues
```bash
# On some systems, you may need:
chmod +x ~/.cargo/bin/uv
```

### Import errors
```bash
# If imports fail, ensure you're using `uv run`
uv run python -c "import sparql_agent"  # ✅ Good
python -c "import sparql_agent"         # ❌ May fail
```

### Dependencies out of sync
```bash
# Resync dependencies
uv sync --locked

# Force reinstall
rm -rf .venv
uv sync
```

## Performance Comparison

| Task | pip | UV |
|------|-----|-----|
| Fresh install | ~60s | ~8s |
| Dependency resolution | ~15s | ~0.5s |
| Virtual environment creation | ~3s | ~0.1s |
| Package imports | Sometimes fails | Always works |

## IDE Integration

### VS Code
UV automatically creates `.venv/` which VS Code detects. No additional setup needed.

### PyCharm
Point PyCharm interpreter to `.venv/bin/python` (or `.venv\Scripts\python.exe` on Windows).

### Cursor/Other IDEs
Most modern IDEs auto-detect `.venv/` directories created by UV.

## CI/CD Integration

```yaml
# GitHub Actions
- name: Set up UV
  uses: astral-sh/setup-uv@v1

- name: Install dependencies
  run: uv sync

- name: Run tests
  run: uv run pytest
```

This setup eliminates all PYTHONPATH issues and provides a much smoother development experience!