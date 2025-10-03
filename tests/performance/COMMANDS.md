# Performance Testing Quick Command Reference

## Setup

```bash
# Install dependencies
uv pip install -e ".[performance]"
```

## Benchmark Tests

```bash
# Run all benchmarks
uv run pytest tests/performance/ --benchmark-only

# Run specific test file
uv run pytest tests/performance/test_query_performance.py --benchmark-only

# Run with custom iterations
uv run pytest tests/performance/ --benchmark-only --benchmark-min-rounds=100

# Save benchmark results
uv run pytest tests/performance/ --benchmark-only --benchmark-json=results.json

# Compare with baseline
uv run pytest tests/performance/ --benchmark-only --benchmark-compare=baseline.json

# Benchmark specific tests
uv run pytest tests/performance/test_query_performance.py::TestQueryPerformanceBenchmarks::test_simple_query_execution --benchmark-only
uv run pytest tests/performance/test_generation_performance.py --benchmark-only
uv run pytest tests/performance/test_parsing_performance.py --benchmark-only
```

## Memory Profiling

```bash
# Run memory tests
uv run pytest tests/performance/test_memory_usage.py -v

# Run with memory profiler
uv run python -m memory_profiler tests/performance/test_memory_usage.py

# Track memory over time
uv run pytest tests/performance/test_memory_usage.py::TestMemoryUsageBaseline -v
uv run pytest tests/performance/test_memory_usage.py::TestMemoryLeaks -v
```

## Concurrency Tests

```bash
# Run all concurrency tests
uv run pytest tests/performance/test_concurrency.py -v

# Run specific concurrency level
uv run pytest tests/performance/test_concurrency.py::TestAsyncQueryExecution -v
uv run pytest tests/performance/test_concurrency.py::TestThreadPoolExecution -v
```

## Load Tests

### SPARQL Endpoint Load Test

```bash
# Headless mode (5 minutes, 10 users)
uv run locust -f tests/performance/load_tests/locust_sparql.py \
    --host=http://localhost:8000 \
    --users=10 \
    --spawn-rate=1 \
    --run-time=5m \
    --headless

# With web UI (then open http://localhost:8089)
uv run locust -f tests/performance/load_tests/locust_sparql.py \
    --host=http://localhost:8000

# Stress test (100 users)
uv run locust -f tests/performance/load_tests/locust_sparql.py \
    --host=http://localhost:8000 \
    --users=100 \
    --spawn-rate=10 \
    --run-time=2m \
    --headless

# Save results
uv run locust -f tests/performance/load_tests/locust_sparql.py \
    --host=http://localhost:8000 \
    --users=20 \
    --spawn-rate=2 \
    --run-time=5m \
    --headless \
    --csv=results/sparql_load_test \
    --html=results/sparql_load_test.html
```

### LLM Provider Load Test

```bash
# Basic load test
uv run locust -f tests/performance/load_tests/locust_llm.py \
    --host=http://localhost:8000 \
    --users=5 \
    --spawn-rate=1 \
    --run-time=3m \
    --headless

# With rate limiting test
uv run locust -f tests/performance/load_tests/locust_llm.py \
    --host=http://localhost:8000 \
    --users=10 \
    --spawn-rate=2 \
    --run-time=5m \
    --headless
```

### MCP Server Load Test

```bash
# MCP server load test
uv run locust -f tests/performance/load_tests/locust_mcp.py \
    --host=http://localhost:8080 \
    --users=10 \
    --spawn-rate=2 \
    --run-time=2m \
    --headless

# Stress test
uv run locust -f tests/performance/load_tests/locust_mcp.py \
    --host=http://localhost:8080 \
    --users=50 \
    --spawn-rate=5 \
    --run-time=5m \
    --headless
```

### Web API Load Test

```bash
# Web API load test
uv run locust -f tests/performance/load_tests/locust_web.py \
    --host=http://localhost:8000 \
    --users=20 \
    --spawn-rate=2 \
    --run-time=5m \
    --headless

# Different user classes
uv run locust -f tests/performance/load_tests/locust_web.py \
    --host=http://localhost:8000 \
    WebAPIUser RestAPIUser \
    --users=30 \
    --spawn-rate=3 \
    --run-time=10m
```

## Profiling

### CPU Profiling

```bash
# Profile with cProfile
python -m cProfile -o output.prof script.py

# View profile stats
python -c "import pstats; p = pstats.Stats('output.prof'); p.sort_stats('cumulative'); p.print_stats(20)"

# Using py-spy (requires root)
sudo py-spy record --format flamegraph -o flamegraph.svg -- python script.py
```

### Memory Profiling

```bash
# Line-by-line memory profiling
python -m memory_profiler tests/performance/test_memory_usage.py

# Memory usage over time
mprof run tests/performance/test_memory_usage.py
mprof plot
```

## Reporting

### Generate Performance Reports

```bash
# Run tests and generate JSON report
uv run pytest tests/performance/ --benchmark-only --benchmark-json=report.json

# Generate HTML report
uv run pytest tests/performance/ --html=report.html --self-contained-html

# Generate coverage report
uv run pytest tests/performance/ --cov=sparql_agent --cov-report=html
```

### Visualizations

```python
# Python script to generate charts
from pathlib import Path
from tests.performance.reporting import PerformanceVisualizer

viz = PerformanceVisualizer(Path("tests/performance/reports"))
viz.plot_benchmark_comparison(data, title="Benchmark Results")
viz.plot_time_series(df, "query_execution_ms")
viz.plot_memory_usage(measurements)
```

## Regression Detection

```bash
# Compare current results with baseline
uv run pytest tests/performance/ --benchmark-only \
    --benchmark-json=current.json \
    --benchmark-compare=tests/performance/benchmarks/baseline.json \
    --benchmark-compare-fail=mean:10%  # Fail if 10% slower

# Update baseline
cp current.json tests/performance/benchmarks/baseline.json
```

## CI/CD Integration

### GitHub Actions

```bash
# Run in CI
uv run pytest tests/performance/ --benchmark-only \
    --benchmark-json=benchmark-results.json \
    --benchmark-min-rounds=50

# Compare and fail on regression
python scripts/compare_benchmarks.py \
    benchmark-results.json \
    tests/performance/benchmarks/baseline.json \
    --threshold=0.25  # 25% threshold
```

### Local Pre-commit Check

```bash
# Quick performance check before commit
uv run pytest tests/performance/ --benchmark-only \
    --benchmark-max-time=10.0 \
    --benchmark-min-rounds=5

# Full performance check
uv run pytest tests/performance/ --benchmark-only \
    && uv run pytest tests/performance/test_memory_usage.py -v
```

## Environment Variables

```bash
# Set load test parameters
export LOAD_TEST_HOST="http://localhost:8000"
export LOAD_TEST_USERS="20"
export LOAD_TEST_DURATION="5m"
export LOAD_TEST_SPAWN_RATE="2"

# Set performance thresholds
export MAX_QUERY_TIME_MS="500"
export MAX_MEMORY_MB="200"
export REGRESSION_THRESHOLD="0.20"

# Enable/disable features
export ENABLE_PROFILING="true"
export ENABLE_CHARTS="true"
export ENABLE_REGRESSION_CHECK="true"
```

## Debugging

```bash
# Run single test with verbose output
uv run pytest tests/performance/test_query_performance.py::test_simple_query_execution -vv

# Run with Python debugger
uv run pytest tests/performance/test_query_performance.py --pdb

# Show test execution time
uv run pytest tests/performance/ --durations=10

# Profile test execution
uv run pytest tests/performance/ --profile

# Capture output
uv run pytest tests/performance/ -s  # Show print statements
```

## Monitoring

### Real-time Monitoring

```bash
# Monitor system resources during tests
watch -n 1 'ps aux | grep python | head -10'

# Monitor memory
watch -n 1 free -h

# Monitor CPU
top -p $(pgrep -f "python.*pytest")

# Monitor network
nethogs
```

### Locust Real-time Dashboard

```bash
# Start Locust with web UI
uv run locust -f tests/performance/load_tests/locust_sparql.py \
    --host=http://localhost:8000

# Open browser to http://localhost:8089
# Configure users and spawn rate in the UI
# Watch real-time charts and statistics
```

## Clean Up

```bash
# Remove generated files
rm -rf tests/performance/profiles/*.prof
rm -rf tests/performance/reports/*.html
rm -rf tests/performance/.pytest_cache

# Clean benchmark results
rm -f benchmark-*.json
rm -f .benchmarks/

# Clean Locust results
rm -f locust_*.csv
rm -f locust_*.html
```

## Tips

1. **Always warm up** - Run tests twice, discard first run
2. **Isolate environment** - Close other applications during tests
3. **Multiple runs** - Average results from multiple runs
4. **Monitor resources** - Watch CPU, memory, network during tests
5. **Start small** - Begin with low load, increase gradually
6. **Document baselines** - Keep track of baseline metrics
7. **Version control** - Commit baseline.json to track performance over time
