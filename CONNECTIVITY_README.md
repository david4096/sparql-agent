# SPARQL Endpoint Connectivity Module

Complete implementation of the SPARQL endpoint ping and connectivity module with health checks, SSL/TLS validation, response time measurement, authentication support, connection pooling, rate limiting, and dual async/sync interfaces.

## Location

```
/Users/david/git/sparql-agent/src/sparql_agent/discovery/connectivity.py
```

## Features

### 1. EndpointPinger Class

The main class for performing health checks on SPARQL endpoints.

**Features:**
- HTTP/HTTPS connectivity testing
- SSL/TLS certificate validation and expiry checking
- Response time measurement
- HTTP status code analysis
- Authentication support (Basic Auth)
- Automatic retry logic with exponential backoff
- Connection pooling
- Rate limiting
- Health status determination
- Server information extraction
- Capability detection (CORS, UPDATE support)
- Health history tracking
- Uptime percentage calculation
- Average response time metrics

**Supported Libraries:**
- `httpx` for async operations
- `requests` for sync operations
- Both libraries are optional - use what you have installed

### 2. Connection Pooling

**ConnectionPool class** manages HTTP connection pools:
- Configurable pool size
- Keepalive connection management
- Separate pools for async and sync operations
- Automatic resource cleanup

### 3. Rate Limiting

**RateLimiter class** implements token bucket algorithm:
- Configurable rate (requests per second)
- Burst capacity
- Both async and sync interfaces
- Thread-safe token management

### 4. Configuration

**ConnectionConfig dataclass** provides comprehensive configuration:
- Timeout settings
- SSL verification options
- Redirect behavior
- Custom user agent
- Authentication credentials
- Custom headers
- Retry configuration (attempts, delay, backoff)

### 5. Health Status

**EndpointStatus enum** represents endpoint states:
- `HEALTHY`: Endpoint responding normally (< 1s response)
- `DEGRADED`: Endpoint slow but functional (1-5s response)
- `UNHEALTHY`: Endpoint having issues (> 5s or HTTP errors)
- `UNREACHABLE`: Connection failed
- `TIMEOUT`: Request timed out
- `SSL_ERROR`: SSL/TLS certificate issues
- `AUTH_REQUIRED`: Authentication needed (401)
- `AUTH_FAILED`: Authentication failed (403)

### 6. Health Check Results

**EndpointHealth dataclass** contains detailed results:
- Endpoint URL
- Status
- Response time (milliseconds)
- HTTP status code
- SSL validity
- SSL expiry date
- Error messages
- Timestamp
- Server information (from headers)
- Detected capabilities
- JSON export via `to_dict()`

## Installation

```bash
# Install dependencies
pip install httpx requests

# Or install the full project
pip install -e .
```

## Usage Examples

### Basic Synchronous Usage

```python
from sparql_agent.discovery.connectivity import EndpointPinger

# Create pinger
pinger = EndpointPinger()

# Ping an endpoint
health = pinger.ping_sync('https://rdfportal.org/pdb/sparql')

print(f"Status: {health.status.value}")
print(f"Response Time: {health.response_time_ms:.2f}ms")
print(f"Status Code: {health.status_code}")

pinger.close_sync()
```

### Basic Asynchronous Usage

```python
import asyncio
from sparql_agent.discovery.connectivity import EndpointPinger

async def check_endpoint():
    async with EndpointPinger() as pinger:
        health = await pinger.ping_async('https://sparql.uniprot.org/sparql')
        print(f"Status: {health.status.value}")
        print(f"Response Time: {health.response_time_ms:.2f}ms")

asyncio.run(check_endpoint())
```

### Concurrent Multiple Endpoints

```python
import asyncio
from sparql_agent.discovery.connectivity import EndpointPinger

async def check_multiple():
    endpoints = [
        'https://rdfportal.org/pdb/sparql',
        'https://sparql.uniprot.org/sparql',
        'https://www.ebi.ac.uk/rdf/services/sparql'
    ]

    async with EndpointPinger() as pinger:
        results = await pinger.ping_multiple_async(endpoints)

        for health in results:
            print(f"{health.endpoint_url}: {health.status.value}")

asyncio.run(check_multiple())
```

### Custom Configuration

```python
from sparql_agent.discovery.connectivity import (
    EndpointPinger,
    ConnectionConfig
)

# Custom configuration
config = ConnectionConfig(
    timeout=15.0,
    verify_ssl=True,
    retry_attempts=3,
    retry_delay=1.0,
    retry_backoff=2.0,
    user_agent="MyApp/1.0"
)

with EndpointPinger(config=config) as pinger:
    health = pinger.ping_sync('https://example.com/sparql')
    print(f"Status: {health.status.value}")
```

### Authentication

```python
from sparql_agent.discovery.connectivity import (
    EndpointPinger,
    ConnectionConfig
)

# Configure authentication
config = ConnectionConfig(
    auth=("username", "password")
)

with EndpointPinger(config=config) as pinger:
    health = pinger.ping_sync('https://secure-endpoint.com/sparql')
    print(f"Status: {health.status.value}")
```

### Rate Limiting

```python
import asyncio
from sparql_agent.discovery.connectivity import EndpointPinger

async def rate_limited_checks():
    # Limit to 2 requests per second, burst of 5
    async with EndpointPinger(rate_limit=(2.0, 5)) as pinger:
        endpoints = ['...'] * 10  # 10 endpoints

        # These will be automatically rate-limited
        results = await pinger.ping_multiple_async(endpoints)

asyncio.run(rate_limited_checks())
```

### Health History Tracking

```python
from sparql_agent.discovery.connectivity import EndpointPinger
from datetime import timedelta

with EndpointPinger() as pinger:
    endpoint = 'https://sparql.uniprot.org/sparql'

    # Perform multiple checks
    for _ in range(10):
        health = pinger.ping_sync(endpoint, check_query=False)
        pinger.record_health(health)

    # Get statistics
    uptime = pinger.get_uptime_percentage(endpoint)
    avg_time = pinger.get_average_response_time(endpoint)

    print(f"Uptime: {uptime:.1f}%")
    print(f"Avg Response: {avg_time:.2f}ms")

    # Get uptime for last hour only
    uptime_1h = pinger.get_uptime_percentage(
        endpoint,
        time_window=timedelta(hours=1)
    )
```

### Detailed Health Information

```python
import asyncio
from sparql_agent.discovery.connectivity import EndpointPinger

async def detailed_check():
    async with EndpointPinger() as pinger:
        health = await pinger.ping_async(
            'https://www.ebi.ac.uk/rdf/services/sparql',
            check_query=True  # Execute SPARQL test query
        )

        print(f"Status: {health.status.value}")
        print(f"Response Time: {health.response_time_ms:.2f}ms")
        print(f"SSL Valid: {health.ssl_valid}")
        print(f"SSL Expiry: {health.ssl_expiry}")

        # Server information from headers
        for key, value in health.server_info.items():
            print(f"{key}: {value}")

        # Detected capabilities
        for cap in health.capabilities:
            print(f"Capability: {cap}")

        # Export as dictionary
        import json
        print(json.dumps(health.to_dict(), indent=2, default=str))

asyncio.run(detailed_check())
```

### Connection Pooling

```python
from sparql_agent.discovery.connectivity import EndpointPinger

# Create pinger with larger connection pool
pinger = EndpointPinger(pool_size=50)

# Make many concurrent requests efficiently
# The connection pool will reuse connections
```

### Error Handling

```python
from sparql_agent.discovery.connectivity import (
    EndpointPinger,
    EndpointStatus
)

with EndpointPinger() as pinger:
    health = pinger.ping_sync('https://invalid-endpoint.example.com/sparql')

    if health.status == EndpointStatus.UNREACHABLE:
        print(f"Cannot reach endpoint: {health.error_message}")
    elif health.status == EndpointStatus.TIMEOUT:
        print(f"Request timed out: {health.error_message}")
    elif health.status == EndpointStatus.SSL_ERROR:
        print(f"SSL error: {health.error_message}")
    elif health.status == EndpointStatus.AUTH_REQUIRED:
        print("Authentication required")
    elif health.status == EndpointStatus.AUTH_FAILED:
        print("Authentication failed")
```

## Test Endpoints

The module has been designed to work with these endpoints:

1. **PDB SPARQL** - https://rdfportal.org/pdb/sparql
   - Protein Data Bank RDF data

2. **UniProt SPARQL** - https://sparql.uniprot.org/sparql
   - Protein sequence and functional information

3. **EBI SPARQL** - https://www.ebi.ac.uk/rdf/services/sparql
   - European Bioinformatics Institute data

## Architecture

### Async vs Sync

The module provides both async and sync interfaces:

- **Async** (using `httpx`): Best for concurrent operations, web servers, and high-throughput scenarios
- **Sync** (using `requests`): Best for scripts, simple tools, and sequential operations

Both interfaces share the same core logic and configuration.

### Connection Management

```
EndpointPinger
    ├── ConnectionPool
    │   ├── AsyncClient (httpx)
    │   └── SyncSession (requests)
    ├── RateLimiter
    │   └── Token Bucket
    └── Health History
        └── Deque per endpoint
```

### Health Check Flow

1. Apply rate limiting (if configured)
2. Attempt request with retry logic
3. Measure response time
4. Check SSL certificate (if HTTPS)
5. Analyze HTTP status code
6. Extract server information
7. Detect capabilities
8. Return EndpointHealth result

### Retry Logic

Exponential backoff with configurable parameters:
- Initial delay: `retry_delay`
- Backoff multiplier: `retry_backoff`
- Max attempts: `retry_attempts`

Example: With delay=1s and backoff=2.0:
- Attempt 1: Immediate
- Attempt 2: Wait 1s
- Attempt 3: Wait 2s
- Attempt 4: Wait 4s

## Performance Considerations

### Connection Pooling

- Default pool size: 10 connections
- Keepalive connections: 5
- Connections are reused across requests
- Significant performance improvement for multiple requests

### Rate Limiting

- Token bucket algorithm
- Non-blocking for async operations
- Ensures compliance with endpoint policies
- Configurable per-endpoint if needed

### Timeouts

- Default: 10 seconds
- Should be adjusted based on endpoint characteristics
- Consider network latency
- Balance between patience and responsiveness

## Testing

Run the comprehensive examples:

```bash
python examples/connectivity_examples.py
```

Run the standalone test:

```bash
python test_connectivity_standalone.py
```

## Integration

The module integrates with the rest of the SPARQL agent:

```python
from sparql_agent.discovery import EndpointPinger, ConnectionConfig

# Available from discovery module
pinger = EndpointPinger()
```

## API Reference

### Classes

- `EndpointPinger`: Main health check class
- `EndpointHealth`: Health check result
- `EndpointStatus`: Status enumeration
- `ConnectionConfig`: Configuration dataclass
- `ConnectionPool`: Connection pool manager
- `RateLimiter`: Rate limiting implementation

### Methods

**EndpointPinger:**
- `ping_sync(endpoint_url, check_query, config)`: Synchronous ping
- `ping_async(endpoint_url, check_query, config)`: Asynchronous ping
- `ping_multiple_sync(endpoint_urls, check_query, config)`: Ping multiple (sync)
- `ping_multiple_async(endpoint_urls, check_query, config)`: Ping multiple (async)
- `record_health(health)`: Record health in history
- `get_health_history(endpoint_url)`: Get health history
- `get_uptime_percentage(endpoint_url, time_window)`: Calculate uptime
- `get_average_response_time(endpoint_url, time_window)`: Calculate avg response time
- `close_sync()`: Close sync resources
- `close_async()`: Close async resources

## Files Created

1. `/Users/david/git/sparql-agent/src/sparql_agent/discovery/connectivity.py` (1,086 lines)
   - Complete implementation with all features

2. `/Users/david/git/sparql-agent/examples/connectivity_examples.py` (468 lines)
   - 10 comprehensive usage examples
   - Demonstrates all major features

3. `/Users/david/git/sparql-agent/test_connectivity.py` (150 lines)
   - Quick test script

4. `/Users/david/git/sparql-agent/test_connectivity_standalone.py` (120 lines)
   - Standalone test without full package import

## Dependencies

Required (one of):
- `httpx >= 0.27.0` (for async)
- `requests >= 2.31.0` (for sync)

Already included in project's `requirements.txt` and `pyproject.toml`.

## Summary

Complete SPARQL endpoint connectivity module with:
- ✅ EndpointPinger class with health checks
- ✅ SSL/TLS validation with expiry dates
- ✅ Response time measurement
- ✅ Authentication support (Basic Auth)
- ✅ Connection pooling
- ✅ Rate limiting with token bucket
- ✅ Retry logic with exponential backoff
- ✅ Async/sync dual interface
- ✅ Health history tracking
- ✅ Uptime percentage calculation
- ✅ Server information extraction
- ✅ Capability detection
- ✅ Comprehensive examples
- ✅ Tested against required endpoints

The module is production-ready and fully integrated into the project structure.
