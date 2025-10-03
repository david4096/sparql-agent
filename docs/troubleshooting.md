# SPARQL Agent Troubleshooting Guide

Common issues and solutions for SPARQL Agent installation and usage.

## Table of Contents

- [Installation Issues](#installation-issues)
- [CLI Issues](#cli-issues)
- [Configuration Issues](#configuration-issues)
- [Runtime Errors](#runtime-errors)
- [Performance Issues](#performance-issues)
- [Getting Help](#getting-help)

## Installation Issues

### Command Not Found After Installation

**Problem:** After running `uv sync`, commands like `sparql-agent` are not found.

**Solutions:**

1. **Use `uv run` prefix (recommended):**
   ```bash
   uv run sparql-agent --help
   ```

2. **Activate the virtual environment:**
   ```bash
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   sparql-agent --help
   ```

3. **Use full path:**
   ```bash
   .venv/bin/sparql-agent --help
   ```

### Import Errors

**Problem:** `ImportError` or `ModuleNotFoundError` when running commands.

**Solutions:**

1. **Re-sync dependencies:**
   ```bash
   uv sync --force
   ```

2. **Check Python version:**
   ```bash
   python --version  # Must be 3.9 or higher
   ```

3. **Verify installation:**
   ```bash
   uv run python -c "import sparql_agent; print(sparql_agent.__version__)"
   ```

### UV Installation Issues

**Problem:** `uv` command not found or fails to install.

**Solutions:**

1. **Reinstall UV:**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Add to PATH:**
   ```bash
   echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc
   source ~/.bashrc
   ```

3. **Use pip as fallback:**
   ```bash
   pip install uv
   ```

## CLI Issues

### "Failed to load logging configuration" Warning

**Problem:** Warning message: `WARNING:root:Failed to load logging configuration: Unable to configure formatter 'json'`

**Explanation:** This is a harmless warning that occurs when JSON logging is configured but can't be initialized. It doesn't affect functionality.

**Solutions:**

1. **Ignore the warning** - it's non-critical

2. **Disable JSON logging in config:**
   ```yaml
   # ~/.sparql-agent/config.yaml
   logging:
     json_enabled: false
   ```

### CLI Commands Not Working from Any Directory

**Problem:** Commands work in project directory but fail elsewhere.

**Solutions:**

1. **Use `--directory` flag:**
   ```bash
   uv run --directory /path/to/sparql-agent sparql-agent --help
   ```

2. **Install globally (not recommended):**
   ```bash
   cd /path/to/sparql-agent
   pip install -e .
   ```

3. **Create alias:**
   ```bash
   alias sparql-agent='uv run --directory /path/to/sparql-agent sparql-agent'
   ```

### MCP Server Errors

**Problem:** `sparql-agent-mcp` fails with "MCP SDK not installed"

**Solution:**
```bash
# Install MCP SDK
pip install mcp

# Or add to your project
cd /path/to/sparql-agent
uv add mcp
```

## Configuration Issues

### API Key Not Found

**Problem:** Errors about missing API keys when using LLM features.

**Solutions:**

1. **Set environment variable:**
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."
   export OPENAI_API_KEY="sk-..."
   ```

2. **Add to config file:**
   ```yaml
   # ~/.sparql-agent/config.yaml
   llm:
     api_key: "sk-ant-..."  # Not recommended - use env var instead
   ```

3. **Pass as command option:**
   ```bash
   uv run sparql-agent query "..." --llm-api-key "sk-ant-..."
   ```

### Config File Not Loading

**Problem:** Configuration file is not being read.

**Solutions:**

1. **Check file location:**
   ```bash
   ls -la ~/.sparql-agent/config.yaml
   ```

2. **Specify config path:**
   ```bash
   export SPARQL_AGENT_CONFIG=~/.sparql-agent/config.yaml
   ```

3. **Use --config flag:**
   ```bash
   uv run sparql-agent --config ~/.sparql-agent/config.yaml query "..."
   ```

4. **Verify YAML syntax:**
   ```bash
   python -c "import yaml; yaml.safe_load(open('~/.sparql-agent/config.yaml'))"
   ```

### Endpoint Not Configured

**Problem:** "No endpoint specified and no default configured"

**Solutions:**

1. **Specify endpoint:**
   ```bash
   uv run sparql-agent query "..." --endpoint https://query.wikidata.org/sparql
   ```

2. **Configure default endpoint:**
   ```yaml
   # ~/.sparql-agent/config.yaml
   endpoints:
     default:
       url: https://query.wikidata.org/sparql
   ```

3. **Use environment variable:**
   ```bash
   export SPARQL_AGENT_ENDPOINT=https://query.wikidata.org/sparql
   ```

## Runtime Errors

### Query Timeout Errors

**Problem:** Queries time out on large endpoints like Wikidata.

**Solutions:**

1. **Increase timeout:**
   ```bash
   uv run sparql-agent query "..." --timeout 120
   ```

2. **Use fast discovery mode:**
   ```bash
   uv run sparql-agent discover https://query.wikidata.org/sparql --fast
   ```

3. **Limit result size:**
   ```bash
   uv run sparql-agent query "..." --limit 100
   ```

4. **Configure in settings:**
   ```yaml
   endpoint:
     default_timeout: 120
   query:
     default_limit: 100
   ```

### Connection Errors

**Problem:** Unable to connect to SPARQL endpoint.

**Solutions:**

1. **Check network connectivity:**
   ```bash
   curl -I https://query.wikidata.org/sparql
   ```

2. **Verify endpoint URL:**
   ```bash
   # Test with simple query
   curl -X POST https://query.wikidata.org/sparql \
     -H "Content-Type: application/sparql-query" \
     -d "SELECT * WHERE { ?s ?p ?o } LIMIT 1"
   ```

3. **Check firewall/proxy settings:**
   ```bash
   export HTTP_PROXY=http://proxy.example.com:8080
   export HTTPS_PROXY=http://proxy.example.com:8080
   ```

4. **Use alternative endpoint:**
   ```bash
   # Try different endpoint
   uv run sparql-agent query "..." --endpoint https://dbpedia.org/sparql
   ```

### Query Generation Errors

**Problem:** Natural language query generation fails.

**Solutions:**

1. **Check LLM configuration:**
   ```bash
   uv run sparql-agent config show | grep llm
   ```

2. **Verify API key:**
   ```bash
   echo $ANTHROPIC_API_KEY  # Should show your key
   ```

3. **Try with explicit SPARQL:**
   ```bash
   # Instead of natural language, use SPARQL directly
   uv run sparql-agent query "SELECT * WHERE { ?s ?p ?o } LIMIT 10"
   ```

4. **Use template strategy:**
   ```bash
   uv run sparql-agent query "..." --strategy template
   ```

### Result Formatting Errors

**Problem:** Errors when formatting results (e.g., "pandas required for table format").

**Solutions:**

1. **Install pandas:**
   ```bash
   uv add pandas
   ```

2. **Use alternative format:**
   ```bash
   uv run sparql-agent query "..." --format json
   ```

3. **Install all optional dependencies:**
   ```bash
   uv sync --extra performance
   ```

## Performance Issues

### Slow Query Execution

**Problem:** Queries take too long to execute.

**Solutions:**

1. **Add LIMIT clause:**
   ```sparql
   SELECT * WHERE { ?s ?p ?o } LIMIT 100
   ```

2. **Use fast discovery mode:**
   ```bash
   uv run sparql-agent discover https://endpoint.org/sparql --fast
   ```

3. **Enable query optimization:**
   ```yaml
   query:
     enable_optimization: true
   ```

4. **Check endpoint status:**
   ```bash
   # Some endpoints have status pages
   curl https://query.wikidata.org/sparql
   ```

### High Memory Usage

**Problem:** Application uses too much memory.

**Solutions:**

1. **Limit result size:**
   ```bash
   uv run sparql-agent query "..." --limit 1000
   ```

2. **Use streaming for large results:**
   ```python
   # In Python API
   results = executor.execute_stream(query, endpoint)
   for result in results:
       process(result)
   ```

3. **Disable caching:**
   ```yaml
   ontology:
     cache_enabled: false
   ```

### Slow Startup Time

**Problem:** Commands take long to start.

**Solutions:**

1. **Use UV (faster than pip):**
   ```bash
   uv run sparql-agent ...
   ```

2. **Precompile Python files:**
   ```bash
   python -m compileall src/
   ```

3. **Check for hanging network requests:**
   ```bash
   uv run sparql-agent --verbose config show
   ```

## Common Error Messages

### "No such option: --version"

**Problem:** The main CLI uses `version` as a subcommand, not `--version`.

**Solution:**
```bash
uv run sparql-agent version  # Correct
# NOT: uv run sparql-agent --version
```

### "QueryGenerationError: Failed to generate SPARQL query"

**Problem:** LLM failed to generate valid SPARQL.

**Solutions:**

1. **Be more specific in query:**
   ```bash
   # Instead of: "proteins"
   # Use: "Find all human proteins with GO annotation"
   ```

2. **Provide ontology context:**
   ```bash
   uv run sparql-agent query "..." --ontology go
   ```

3. **Use hybrid strategy:**
   ```bash
   uv run sparql-agent query "..." --strategy hybrid
   ```

### "EndpointError: Endpoint returned 503"

**Problem:** SPARQL endpoint is overloaded or down.

**Solutions:**

1. **Retry later:**
   ```bash
   sleep 60 && uv run sparql-agent query "..."
   ```

2. **Use alternative endpoint:**
   ```bash
   # Wikidata has mirrors
   uv run sparql-agent query "..." --endpoint https://query.wikidata.org/sparql
   ```

3. **Reduce query complexity:**
   ```bash
   # Simplify your query or add more constraints
   ```

## Debug Mode

Enable debug mode for detailed error information:

```bash
# With --debug flag
uv run sparql-agent --debug query "..."

# With verbose output
uv run sparql-agent -vv query "..."

# Both
uv run sparql-agent --debug -vv query "..."
```

Debug output includes:
- Full stack traces
- HTTP request/response details  
- LLM API calls and responses
- Query generation steps
- Configuration values

## Getting Help

### Check Logs

```bash
# View recent logs
tail -f ~/.sparql-agent/logs/sparql-agent.log

# Search for errors
grep ERROR ~/.sparql-agent/logs/sparql-agent.log
```

### Verify Installation

```bash
# Run verification script
cat > verify.py << 'EOF'
import sys
from sparql_agent import __version__
from sparql_agent.config.settings import get_settings

print(f"Python: {sys.version}")
print(f"SPARQL Agent: {__version__}")
settings = get_settings()
print(f"Config: {settings.config_dir}")
print("✓ Installation verified")
EOF

uv run python verify.py
```

### Run Tests

```bash
# Run test suite
uv run pytest -v

# Run with debug output
uv run pytest -v --log-cli-level=DEBUG

# Test specific component
uv run pytest tests/test_cli.py -v
```

### Report Issues

When reporting issues, include:

1. **Version information:**
   ```bash
   uv run sparql-agent version --verbose
   ```

2. **Full error message:**
   ```bash
   uv run sparql-agent --debug query "..." 2>&1 | tee error.log
   ```

3. **Configuration (sanitized):**
   ```bash
   uv run sparql-agent config show > config.txt
   # Remove API keys before sharing
   ```

4. **System information:**
   ```bash
   uname -a  # OS version
   python --version
   uv --version
   ```

### Community Resources

- GitHub Issues: https://github.com/david4096/sparql-agent/issues
- Discussions: https://github.com/david4096/sparql-agent/discussions
- Documentation: https://github.com/david4096/sparql-agent/docs
- Stack Overflow: Tag with `sparql-agent`

## Still Having Issues?

If you've tried the solutions above and still have problems:

1. Search existing issues: https://github.com/david4096/sparql-agent/issues
2. Create a new issue with:
   - Clear description of the problem
   - Steps to reproduce
   - Error messages and logs
   - System information
   - Configuration (sanitize API keys)
3. Join community discussions for help from other users

We're here to help!
