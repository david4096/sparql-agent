# Logging Configuration

The SPARQL Agent system has a comprehensive, production-ready logging configuration that is flexible, secure, and clean.

## Features

- **Multiple formatters**: Standard, detailed, simple, JSON (optional), and colored (optional)
- **Custom filters**: Rate limiting and sensitive data masking
- **Flexible handlers**: Console, file, rotating files, syslog support
- **Module-specific loggers**: Fine-grained control over different components
- **Environment-based configuration**: Different settings for development, testing, and production
- **Graceful degradation**: Works even when optional dependencies are missing

## Basic Usage

### CLI Commands

```bash
# Normal output
uv run sparql-agent config show

# Verbose output (INFO level)
uv run sparql-agent -v config show

# Very verbose output (DEBUG level)
uv run sparql-agent -vv config show

# Debug mode with stack traces
uv run sparql-agent --debug config show
```

### Programmatic Usage

```python
from sparql_agent.utils.logging import setup_logging, get_logger

# Basic setup with INFO level
setup_logging(log_level="INFO")

# Setup with file logging enabled
setup_logging(
    log_level="DEBUG",
    enable_file_logging=True,
    enable_json_logging=False
)

# Get a logger for your module
logger = get_logger(__name__)
logger.info("Application started")
```

## Configuration File

The logging configuration is stored in `src/sparql_agent/config/logging.yaml`. This file defines:

### Formatters

- **standard**: Simple timestamped format
- **detailed**: Includes function name and line number
- **simple**: Just level and message
- **json**: Structured JSON format (requires `python-json-logger`)
- **colored**: Colored console output (requires `colorlog`)

### Handlers

- **console**: Standard console output
- **console_simple**: Minimal console output
- **console_colored**: Colored console output (when colorlog is available)
- **file**: Rotating file handler for general logs
- **error_file**: Separate file for error logs
- **json_file**: JSON-formatted logs for parsing
- **query_file**: Dedicated log for SPARQL queries
- **performance_file**: Performance metrics in JSON
- **syslog**: System log integration

### Filters

- **rate_limit**: Prevents log flooding by limiting message frequency
- **sensitive_data**: Masks passwords, API keys, tokens, and secrets

### Module Loggers

Pre-configured loggers for different components:

- `sparql_agent`: Main application logger
- `sparql_agent.query`: Query execution
- `sparql_agent.ontology`: Ontology services
- `sparql_agent.llm`: LLM integration
- `sparql_agent.config`: Configuration
- `sparql_agent.performance`: Performance monitoring
- `sparql_agent.errors`: Error tracking
- `sparql_agent.http`: HTTP requests
- `sparql_agent.cache`: Caching layer

## Optional Dependencies

The logging system works without any optional dependencies, but you can enhance it by installing:

### JSON Logging

For structured JSON logs in production:

```bash
pip install python-json-logger
```

Then enable in code:

```python
setup_logging(enable_json_logging=True)
```

### Colored Console Output

For better readability during development:

```bash
pip install colorlog
```

The system will automatically use colored output when available.

## Custom Filters

### Rate Limiting

Prevents log flooding by limiting the number of messages:

```python
from sparql_agent.utils.logging import RateLimitFilter

# Limit to 10 messages per 60 seconds
rate_filter = RateLimitFilter(rate=10, per=60)
```

### Sensitive Data Masking

Automatically masks sensitive information in logs:

```python
from sparql_agent.utils.logging import SensitiveDataFilter

# Will mask: password, api_key, secret, token
sensitive_filter = SensitiveDataFilter()

# Custom patterns
custom_filter = SensitiveDataFilter(
    patterns=['password', 'api_key', 'my_secret_field'],
    mask='[HIDDEN]'
)
```

## Environment Configuration

The logging system supports different environments:

### Development

```yaml
development:
  root_level: DEBUG
  console_handler: console
  file_logging: true
  json_logging: false
```

### Testing

```yaml
testing:
  root_level: WARNING
  console_handler: console_simple
  file_logging: false
  json_logging: false
```

### Production

```yaml
production:
  root_level: INFO
  console_handler: console
  file_logging: true
  json_logging: true
  syslog_enabled: true
```

## Disabling Logging

To disable automatic logging configuration on import:

```bash
export SPARQL_AGENT_DISABLE_AUTO_LOGGING=true
```

## Best Practices

### Log Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: Confirmation of normal operation
- **WARNING**: Something unexpected but not critical
- **ERROR**: Serious problem preventing a function
- **CRITICAL**: System failure imminent

### Module-Specific Logging

```python
import logging

# Get a module-specific logger
logger = logging.getLogger(__name__)

# Use appropriate levels
logger.debug("Detailed execution information")
logger.info("Request completed successfully")
logger.warning("API rate limit approaching")
logger.error("Failed to connect to endpoint")
logger.critical("Database connection lost")
```

### Structured Logging

When using JSON logging, include context:

```python
logger.info(
    "Query executed",
    extra={
        'query_id': query_id,
        'endpoint': endpoint_url,
        'duration_ms': duration,
        'result_count': count
    }
)
```

### Security

The sensitive data filter is automatically applied to relevant loggers:

- HTTP request logger
- Query file logger

Avoid logging:
- Passwords
- API keys and tokens
- Personal identifiable information (PII)
- Full query responses containing sensitive data

## Log Files

When file logging is enabled, logs are written to:

```
logs/
├── sparql_agent.log          # Main application log
├── sparql_agent_errors.log   # Error-only log
├── sparql_agent.json         # JSON-formatted log
├── sparql_queries.log        # SPARQL query log
└── sparql_performance.json   # Performance metrics
```

Each file:
- Rotates at 10 MB
- Keeps 5 backup files (50 MB total per log)
- Uses UTF-8 encoding

## Troubleshooting

### No log output

Check that logging is enabled:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Too much output from third-party libraries

```python
from sparql_agent.utils.logging import disable_third_party_logging

# Reduce noise from common libraries
disable_third_party_logging()
```

### Custom configuration not loading

Verify the config path:

```python
from sparql_agent.config import get_settings

settings = get_settings()
print(settings.config_dir)
```

### Missing dependencies warning

This is informational only. The system works fine without optional dependencies. To remove the warning, install:

```bash
pip install python-json-logger colorlog
```

## Examples

### Simple Script

```python
from sparql_agent.utils.logging import setup_logging, get_logger

# Setup
setup_logging(log_level="INFO")
logger = get_logger(__name__)

# Use
logger.info("Starting data processing")
logger.warning("Large dataset detected")
logger.info("Processing complete")
```

### Production Configuration

```python
from pathlib import Path
from sparql_agent.utils.logging import setup_logging

setup_logging(
    config_path=Path("config/logging.yaml"),
    log_level="INFO",
    enable_file_logging=True,
    enable_json_logging=True,
    log_dir=Path("/var/log/sparql-agent")
)
```

### CLI with Debug

```bash
# Enable debug mode for troubleshooting
uv run sparql-agent --debug query "Find all proteins" --endpoint https://sparql.uniprot.org/sparql
```

## API Reference

See `src/sparql_agent/utils/logging.py` for full API documentation.

### Key Functions

- `setup_logging(...)`: Configure logging system
- `get_logger(name)`: Get a logger instance
- `configure_module_logging(...)`: Configure specific module
- `disable_third_party_logging(...)`: Quiet noisy libraries

### Key Classes

- `RateLimitFilter`: Rate limit log messages
- `SensitiveDataFilter`: Mask sensitive data
