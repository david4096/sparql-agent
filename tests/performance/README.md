# Performance and Load Testing Framework

Comprehensive performance testing suite for sparql-agent, including benchmarks, load tests, memory profiling, and performance regression detection.

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Performance Benchmarks](#performance-benchmarks)
- [Load Testing](#load-testing)
- [Memory Profiling](#memory-profiling)
- [Concurrency Testing](#concurrency-testing)
- [Profiling Tools](#profiling-tools)
- [Reporting](#reporting)
- [CI/CD Integration](#cicd-integration)
- [Configuration](#configuration)

## Overview

This framework provides:

- **Benchmark Tests**: Query execution, LLM generation, parsing performance
- **Load Tests**: SPARQL endpoints, LLM providers, MCP server, Web API
- **Memory Profiling**: Memory usage tracking and leak detection
- **Concurrency Tests**: Thread safety and parallel execution
- **Performance Regression Detection**: Automated baseline comparison
- **Profiling Tools**: CPU, memory, and line-by-line profiling
- **Visualization**: Charts, graphs, and performance dashboards

## Installation

Install performance testing dependencies:

```bash
# Using uv (recommended)
uv pip install -e ".[performance]"

# Or using pip
pip install -e ".[performance]"
```

Dependencies include:
- `pytest-benchmark` - Benchmarking framework
- `locust` - Load testing framework
- `memory-profiler` - Memory profiling
- `psutil` - System resource monitoring
- `py-spy` - Sampling profiler
- `matplotlib` - Visualization
- `pandas` - Data analysis

## Quick Start

### Run All Performance Tests

```bash
# Run all benchmark tests
uv run pytest tests/performance/ --benchmark-only

# Run with coverage
uv run pytest tests/performance/ --cov=sparql_agent

# Run specific test file
uv run pytest tests/performance/test_query_performance.py --benchmark-only
```

### Run Load Tests

```bash
# SPARQL endpoint load test
uv run locust -f tests/performance/load_tests/locust_sparql.py \
    --host=http://localhost:8000 \
    --users=10 \
    --spawn-rate=1 \
    --run-time=1m

# LLM endpoint load test
uv run locust -f tests/performance/load_tests/locust_llm.py \
    --host=http://localhost:8000 \
    --users=5 \
    --spawn-rate=1 \
    --run-time=2m

# With web UI (interactive)
uv run locust -f tests/performance/load_tests/locust_web.py \
    --host=http://localhost:8000
# Then open http://localhost:8089
```

### Memory Profiling

```bash
# Run memory tests
uv run pytest tests/performance/test_memory_usage.py -v

# Run with memory profiler
uv run python -m memory_profiler tests/performance/test_memory_usage.py
```

## Performance Benchmarks

### Query Performance Tests

Test query execution time across different complexity levels:

```bash
uv run pytest tests/performance/test_query_performance.py::TestQueryPerformanceBenchmarks --benchmark-only
```

Tests include:
- Simple query execution (< 100ms target)
- Complex queries with joins (< 500ms target)
- Nested queries with subqueries
- Query scaling by result size (10, 100, 1k, 10k results)
- Query complexity scaling (1, 3, 5, 10 joins)

**Example output:**
```
test_simple_query_execution     Mean: 45.23ms, Min: 42.11ms, Max: 52.34ms
test_complex_query_execution    Mean: 234.56ms, Min: 198.23ms, Max: 287.91ms
```

### LLM Generation Performance

Test SPARQL query generation from natural language:

```bash
uv run pytest tests/performance/test_generation_performance.py --benchmark-only
```

Tests include:
- Simple query generation (< 2s target)
- Complex query generation with constraints
- Provider comparison (Anthropic vs OpenAI)
- Prompt engineering optimization
- Batch generation (sequential vs parallel)
- Token usage optimization

### Parsing Performance

Test schema and ontology parsing speed:

```bash
uv run pytest tests/performance/test_parsing_performance.py --benchmark-only
```

Tests include:
- OWL ontology parsing (small, medium, large)
- ShEx schema parsing
- VoID metadata parsing
- Schema inference from data
- RDF graph parsing
- Namespace resolution

## Load Testing

### SPARQL Endpoint Load Testing

Simulate multiple users executing SPARQL queries:

```bash
# Command line (headless)
uv run locust -f tests/performance/load_tests/locust_sparql.py \
    --host=http://localhost:8000 \
    --users=20 \
    --spawn-rate=2 \
    --run-time=5m \
    --headless

# With web UI
uv run locust -f tests/performance/load_tests/locust_sparql.py \
    --host=http://localhost:8000
```

**User Types:**
- `SPARQLQueryUser` - Executes various query types
- `SPARQLUpdateUser` - Performs INSERT/DELETE operations
- `SPARQLBatchUser` - Executes batch queries
- `SPARQLStressUser` - Rapid-fire stress testing

**Query Distribution:**
- Simple queries: 50% (weight 10)
- Filtered queries: 25% (weight 5)
- Join queries: 15% (weight 3)
- Aggregation: 8% (weight 2)
- Complex queries: 2% (weight 1)

### LLM Provider Load Testing

Test LLM query generation under load:

```bash
uv run locust -f tests/performance/load_tests/locust_llm.py \
    --host=http://localhost:8000 \
    --users=5 \
    --spawn-rate=1 \
    --run-time=3m
```

**User Types:**
- `LLMQueryGenerationUser` - Generate queries from NL
- `LLMBatchGenerationUser` - Batch query generation
- `LLMRefinementUser` - Iterative query refinement
- `LLMCachingUser` - Test cache effectiveness
- `LLMStressUser` - Stress test with rapid requests

### MCP Server Load Testing

Test Model Context Protocol server:

```bash
uv run locust -f tests/performance/load_tests/locust_mcp.py \
    --host=http://localhost:8080 \
    --users=10 \
    --spawn-rate=2 \
    --run-time=2m
```

**User Types:**
- `MCPToolUser` - Execute MCP tools
- `MCPResourceUser` - Access resources
- `MCPPromptUser` - Work with prompts
- `MCPBatchUser` - Batch operations
- `MCPWebSocketUser` - WebSocket connections

### Web API Load Testing

Test REST API endpoints:

```bash
uv run locust -f tests/performance/load_tests/locust_web.py \
    --host=http://localhost:8000 \
    --users=20 \
    --spawn-rate=2 \
    --run-time=5m
```

**User Types:**
- `WebAPIUser` - General API operations
- `WebUIUser` - UI workflow simulation
- `RestAPIUser` - REST endpoint testing
- `WebhookUser` - Webhook functionality
- `FileUploadUser` - File upload testing

## Memory Profiling

### Memory Usage Tests

Track memory consumption and detect leaks:

```bash
# Run memory tests
uv run pytest tests/performance/test_memory_usage.py -v

# Run with memory profiler
uv run python -m memory_profiler tests/performance/test_memory_usage.py
```

**Test Categories:**
- **Baseline Tests**: Component memory footprint
- **Scaling Tests**: Memory growth with data size
- **Leak Detection**: Repeated operations memory growth
- **Large Data**: Streaming and chunked processing
- **Cleanup Tests**: Resource release verification

**Memory Thresholds:**
- Query Executor: < 50 MB baseline
- OWL Parser: < 30 MB baseline
- LLM Provider: < 20 MB baseline
- Result Processing (1k): < 5 MB
- Memory Growth (1000 iterations): < 10 MB

### Memory Profiling Output

```bash
# Generate detailed memory profile
uv run python -m memory_profiler tests/performance/test_memory_usage.py

# Profile specific function
@profile
def test_function():
    # Function will be profiled line-by-line
    pass
```

## Concurrency Testing

Test concurrent request handling and thread safety:

```bash
uv run pytest tests/performance/test_concurrency.py -v
```

**Test Categories:**
- **Async Query Execution**: asyncio performance
- **Thread Pool Execution**: Thread pool scaling
- **Process Pool**: CPU-intensive parallel tasks
- **Cache Concurrency**: Thread-safe cache access
- **Rate Limiting**: Concurrent rate limit testing
- **Connection Pooling**: Pool efficiency
- **Deadlock Prevention**: Lock ordering tests

**Concurrency Levels Tested:** 1, 5, 10, 20, 50, 100 concurrent users

## Profiling Tools

### CPU Profiling

```python
from tests.performance.profiling_utils import CPUProfiler

profiler = CPUProfiler()

# Profile code block
with profiler.profile("my_operation"):
    # Code to profile
    execute_queries()

# Print statistics
profiler.print_stats(sort_by='cumulative', limit=20)
```

### Memory Profiling

```python
from tests.performance.profiling_utils import MemoryProfiler

profiler = MemoryProfiler()

# Profile memory usage
with profiler.profile("my_operation"):
    # Code to profile
    load_large_dataset()
```

### Performance Monitor

Combines CPU and memory profiling:

```python
from tests.performance.profiling_utils import PerformanceMonitor

monitor = PerformanceMonitor("comprehensive_test")

with monitor.monitor():
    # Code to monitor
    process_data()
```

### Function Profiler

Profile individual functions:

```python
from tests.performance.profiling_utils import FunctionProfiler

profiler = FunctionProfiler()

@profiler.profile
def my_function():
    # Function will be profiled
    pass

# Get results
result = profiler.get_result("my_function")
print(f"Execution time: {result.execution_time}s")
print(f"Memory used: {result.memory_used_mb}MB")
```

## Reporting

### Generate Performance Reports

```python
from pathlib import Path
from tests.performance.reporting import PerformanceDashboard

# Create dashboard
dashboard = PerformanceDashboard(Path("tests/performance/reports"))

# Generate comprehensive dashboard
dashboard.generate_dashboard(
    metrics={
        "query_execution_ms": 45.2,
        "generation_time_ms": 1823.4,
        "memory_usage_mb": 48.7
    },
    baseline={
        "query_execution_ms": 50.0,
        "generation_time_ms": 2000.0,
        "memory_usage_mb": 50.0
    }
)
```

### Visualization

```python
from tests.performance.reporting import PerformanceVisualizer

viz = PerformanceVisualizer(Path("tests/performance/reports"))

# Plot benchmark comparison
viz.plot_benchmark_comparison({
    "test1": [45, 48, 42, 50],
    "test2": [120, 115, 125, 118]
})

# Plot time series
viz.plot_time_series(df, "query_execution_ms")

# Plot memory usage
viz.plot_memory_usage(measurements)

# Plot performance distribution
viz.plot_performance_distribution([45, 48, 42, 50, 47])
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Performance Tests

on: [push, pull_request]

jobs:
  performance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install dependencies
        run: |
          pip install uv
          uv pip install -e ".[performance]"

      - name: Run performance benchmarks
        run: |
          uv run pytest tests/performance/ --benchmark-only \
            --benchmark-json=benchmark-results.json

      - name: Compare with baseline
        run: |
          python scripts/compare_benchmarks.py \
            benchmark-results.json \
            tests/performance/benchmarks/baseline.json

      - name: Fail on regression
        if: steps.compare.outputs.regression == 'true'
        run: exit 1
```

### Performance Gates

Configure in `performance_config.yaml`:

```yaml
ci_cd:
  fail_on_regression: true
  regression_threshold: 0.25  # 25% regression fails build
  performance_gates:
    - metric: "max_query_time_ms"
      threshold: 500
    - metric: "max_memory_mb"
      threshold: 200
```

## Configuration

### Performance Configuration File

Edit `tests/performance/performance_config.yaml`:

```yaml
# Baseline metrics
baseline_metrics:
  query_execution_ms: 100
  llm_generation_ms: 2000
  parsing_ms: 50

# Thresholds
thresholds:
  max_query_time_ms: 500
  max_generation_time_ms: 5000
  regression_tolerance: 0.20

# Load test configuration
load_test:
  sparql:
    users: 10
    spawn_rate: 1
    duration: "1m"
```

### Baseline Metrics

Update baseline metrics in `tests/performance/benchmarks/baseline.json`:

```json
{
  "query_execution_ms": 100,
  "llm_generation_ms": 2000,
  "parsing_ms": 50,
  "memory_baseline_mb": 50
}
```

### Environment Variables

```bash
# Load test configuration
export LOAD_TEST_HOST="http://localhost:8000"
export LOAD_TEST_USERS="20"
export LOAD_TEST_DURATION="5m"

# Performance thresholds
export MAX_QUERY_TIME_MS="500"
export MAX_MEMORY_MB="200"

# Enable/disable features
export ENABLE_PROFILING="true"
export ENABLE_CHARTS="true"
```

## Best Practices

### Writing Performance Tests

1. **Use pytest-benchmark for microbenchmarks**
   ```python
   def test_operation(benchmark):
       result = benchmark(function_to_test, arg1, arg2)
       assert result is not None
   ```

2. **Profile memory for memory-intensive operations**
   ```python
   def test_memory_usage(memory_tracker):
       memory_tracker.start()
       # Operation
       stats = memory_tracker.stop()
       assert stats['growth_mb'] < 10
   ```

3. **Test concurrency for multi-user scenarios**
   ```python
   @pytest.mark.parametrize("concurrency", [1, 10, 50])
   def test_concurrent_requests(concurrency):
       # Test with different concurrency levels
       pass
   ```

4. **Compare against baselines**
   ```python
   def test_regression(baseline_metrics, performance_threshold_checker):
       current_value = measure_performance()
       performance_threshold_checker.assert_threshold(
           "metric_name", current_value, tolerance=0.2
       )
   ```

### Load Testing Tips

1. **Start with low load** and gradually increase
2. **Monitor server resources** during tests
3. **Use realistic data** for queries
4. **Test different user types** with appropriate weights
5. **Run tests in environment similar to production**

### Performance Optimization

1. **Identify bottlenecks** using profiling tools
2. **Focus on high-impact areas** (most frequent operations)
3. **Measure before and after** optimization
4. **Use caching** for repeated operations
5. **Implement connection pooling** for external services
6. **Use async/await** for I/O-bound operations

## Troubleshooting

### Common Issues

**Issue**: Benchmark tests fail with timeout
```bash
# Increase timeout
uv run pytest tests/performance/ --benchmark-only --benchmark-max-time=20.0
```

**Issue**: Memory tests show excessive growth
```bash
# Check for memory leaks
uv run python -m memory_profiler tests/performance/test_memory_usage.py
```

**Issue**: Load tests cannot connect to server
```bash
# Ensure server is running
python -m sparql_agent.web.server &
# Then run load tests
```

**Issue**: Locust web UI not accessible
```bash
# Check if port 8089 is available
# Specify different port:
uv run locust -f load_tests/locust_web.py --web-port=8090
```

## Contributing

When adding new performance tests:

1. Follow existing test patterns
2. Add baselines to `baseline.json`
3. Update this README with new test descriptions
4. Ensure tests pass in CI/CD
5. Document any special requirements

## License

MIT License - See LICENSE file for details
