"""
Concurrency and parallel execution performance tests.

Tests concurrent request handling, thread safety, and async performance.
"""

import pytest
import asyncio
import threading
import time
from typing import List, Dict, Any, Callable
from unittest.mock import Mock, AsyncMock
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import aiohttp


class TestAsyncQueryExecution:
    """Test asynchronous query execution performance."""

    @pytest.fixture
    def mock_async_executor(self):
        """Create mock async executor."""
        mock = Mock()
        mock.execute_async = AsyncMock(return_value={
            "success": True,
            "results": [{"s": "subject", "p": "predicate", "o": "object"}]
        })
        return mock

    @pytest.mark.asyncio
    async def test_single_async_query(self, benchmark, mock_async_executor):
        """Benchmark single async query execution."""
        async def execute():
            return await mock_async_executor.execute_async(
                "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10"
            )

        result = await execute()
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_concurrent_async_queries(self, mock_async_executor):
        """Test concurrent async query execution."""
        queries = [
            f"SELECT ?s ?p ?o WHERE {{ ?s ?p ?o }} LIMIT {i*10}"
            for i in range(1, 11)
        ]

        start_time = time.time()

        # Execute all queries concurrently
        tasks = [mock_async_executor.execute_async(q) for q in queries]
        results = await asyncio.gather(*tasks)

        elapsed = time.time() - start_time

        assert len(results) == len(queries)
        # Should be much faster than sequential
        assert elapsed < 1.0, f"Concurrent execution too slow: {elapsed}s"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("concurrency_level", [10, 50, 100])
    async def test_async_query_scaling(self, mock_async_executor, concurrency_level):
        """Test async query performance scaling with concurrency level."""
        queries = [f"SELECT * WHERE {{ ?s ?p ?o }} LIMIT {i}" for i in range(concurrency_level)]

        start_time = time.time()

        tasks = [mock_async_executor.execute_async(q) for q in queries]
        results = await asyncio.gather(*tasks)

        elapsed = time.time() - start_time

        assert len(results) == concurrency_level
        # Average time per query should remain reasonable
        avg_time = elapsed / concurrency_level
        assert avg_time < 0.1, f"Average query time too high: {avg_time}s"


class TestThreadPoolExecution:
    """Test thread pool executor performance."""

    @pytest.fixture
    def mock_executor(self):
        """Create mock executor."""
        mock = Mock()
        mock.execute = Mock(return_value={
            "success": True,
            "results": [{"s": "s", "p": "p", "o": "o"}]
        })
        return mock

    def test_thread_pool_query_execution(self, mock_executor):
        """Test query execution with thread pool."""
        queries = [f"SELECT ?s WHERE {{ ?s ?p ?o }} LIMIT {i*10}" for i in range(1, 21)]

        start_time = time.time()

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(mock_executor.execute, query)
                for query in queries
            ]
            results = [f.result() for f in as_completed(futures)]

        elapsed = time.time() - start_time

        assert len(results) == len(queries)
        assert elapsed < 2.0, f"Thread pool execution too slow: {elapsed}s"

    @pytest.mark.parametrize("num_workers", [5, 10, 20])
    def test_thread_pool_scaling(self, mock_executor, num_workers):
        """Test thread pool performance with different worker counts."""
        queries = [f"SELECT * WHERE {{ ?s ?p ?o }} LIMIT {i}" for i in range(100)]

        start_time = time.time()

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(mock_executor.execute, q) for q in queries]
            results = [f.result() for f in as_completed(futures)]

        elapsed = time.time() - start_time

        assert len(results) == len(queries)
        # More workers should generally be faster (up to a point)
        print(f"Workers: {num_workers}, Time: {elapsed:.2f}s")


class TestProcessPoolExecution:
    """Test process pool executor performance for CPU-intensive tasks."""

    def test_process_pool_parsing(self):
        """Test parallel parsing with process pool."""
        def parse_ontology(data: str) -> Dict[str, Any]:
            """Simulate CPU-intensive parsing."""
            # Simulate work
            result = {"classes": [], "properties": []}
            for i in range(100):
                result["classes"].append(f"Class{i}")
            return result

        datasets = [f"ontology_data_{i}" for i in range(20)]

        start_time = time.time()

        with ProcessPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(parse_ontology, data) for data in datasets]
            results = [f.result() for f in as_completed(futures)]

        elapsed = time.time() - start_time

        assert len(results) == len(datasets)
        assert elapsed < 3.0, f"Process pool parsing too slow: {elapsed}s"


class TestConcurrentCacheAccess:
    """Test cache performance under concurrent access."""

    @pytest.fixture
    def thread_safe_cache(self) -> Dict[str, Any]:
        """Create thread-safe cache with lock."""
        cache: Dict[str, Any] = {}
        lock = threading.Lock()
        cache_lock = lock
        return {"cache": cache, "lock": cache_lock}

    def test_concurrent_cache_writes(self, thread_safe_cache):
        """Test concurrent cache write performance."""
        cache = thread_safe_cache["cache"]
        lock = thread_safe_cache["lock"]

        def write_to_cache(key: str, value: Any) -> None:
            with lock:
                cache[key] = value

        start_time = time.time()

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(write_to_cache, f"key_{i}", f"value_{i}")
                for i in range(1000)
            ]
            for f in as_completed(futures):
                f.result()

        elapsed = time.time() - start_time

        assert len(cache) == 1000
        assert elapsed < 1.0, f"Concurrent cache writes too slow: {elapsed}s"

    def test_concurrent_cache_reads(self, thread_safe_cache):
        """Test concurrent cache read performance."""
        cache = thread_safe_cache["cache"]
        lock = thread_safe_cache["lock"]

        # Pre-populate cache
        with lock:
            for i in range(1000):
                cache[f"key_{i}"] = f"value_{i}"

        def read_from_cache(key: str) -> Any:
            with lock:
                return cache.get(key)

        start_time = time.time()

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [
                executor.submit(read_from_cache, f"key_{i % 1000}")
                for i in range(5000)
            ]
            results = [f.result() for f in as_completed(futures)]

        elapsed = time.time() - start_time

        assert len([r for r in results if r is not None]) == 5000
        assert elapsed < 1.0, f"Concurrent cache reads too slow: {elapsed}s"


class TestRateLimiting:
    """Test rate limiting under concurrent load."""

    @pytest.fixture
    def rate_limiter(self):
        """Create simple rate limiter."""
        class RateLimiter:
            def __init__(self, max_requests: int, time_window: float):
                self.max_requests = max_requests
                self.time_window = time_window
                self.requests: List[float] = []
                self.lock = threading.Lock()

            def acquire(self) -> bool:
                """Try to acquire a rate limit slot."""
                with self.lock:
                    now = time.time()
                    # Remove old requests outside time window
                    self.requests = [t for t in self.requests if now - t < self.time_window]

                    if len(self.requests) < self.max_requests:
                        self.requests.append(now)
                        return True
                    return False

        return RateLimiter(max_requests=100, time_window=1.0)

    def test_rate_limiter_concurrent_access(self, rate_limiter):
        """Test rate limiter under concurrent access."""
        successful_requests = []
        lock = threading.Lock()

        def make_request(request_id: int) -> bool:
            """Try to make a rate-limited request."""
            if rate_limiter.acquire():
                with lock:
                    successful_requests.append(request_id)
                return True
            return False

        # Try to make 200 requests concurrently (should only allow 100)
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_request, i) for i in range(200)]
            for f in as_completed(futures):
                f.result()

        # Should have rate limited to ~100 requests
        assert len(successful_requests) <= 110, \
            f"Rate limiter failed: {len(successful_requests)} requests succeeded"
        assert len(successful_requests) >= 90, \
            f"Rate limiter too strict: only {len(successful_requests)} requests succeeded"


class TestAsyncHTTPRequests:
    """Test async HTTP request performance."""

    @pytest.mark.asyncio
    async def test_concurrent_sparql_queries(self):
        """Test concurrent SPARQL queries via HTTP."""
        # Mock HTTP responses
        async def mock_sparql_query(query: str) -> Dict[str, Any]:
            """Mock async SPARQL query."""
            await asyncio.sleep(0.1)  # Simulate network delay
            return {
                "results": {
                    "bindings": [{"s": {"value": "subject"}}]
                }
            }

        queries = [f"SELECT ?s WHERE {{ ?s ?p ?o }} LIMIT {i}" for i in range(10)]

        start_time = time.time()

        tasks = [mock_sparql_query(q) for q in queries]
        results = await asyncio.gather(*tasks)

        elapsed = time.time() - start_time

        assert len(results) == len(queries)
        # Concurrent requests should complete in ~0.1s, not 1.0s
        assert elapsed < 0.5, f"Concurrent HTTP requests too slow: {elapsed}s"

    @pytest.mark.asyncio
    async def test_async_http_session_reuse(self):
        """Test performance with HTTP session reuse."""
        async def query_with_new_session(url: str) -> Dict[str, Any]:
            """Query with new session each time (slower)."""
            # Simulate session creation overhead
            await asyncio.sleep(0.05)
            return {"data": "result"}

        async def query_with_shared_session(url: str, session: Any) -> Dict[str, Any]:
            """Query with shared session (faster)."""
            await asyncio.sleep(0.01)
            return {"data": "result"}

        urls = [f"http://example.org/query{i}" for i in range(20)]

        # Test without session reuse
        start_time = time.time()
        tasks = [query_with_new_session(url) for url in urls]
        await asyncio.gather(*tasks)
        time_without_reuse = time.time() - start_time

        # Test with session reuse
        start_time = time.time()
        mock_session = object()
        tasks = [query_with_shared_session(url, mock_session) for url in urls]
        await asyncio.gather(*tasks)
        time_with_reuse = time.time() - start_time

        # Session reuse should be significantly faster
        assert time_with_reuse < time_without_reuse, \
            f"Session reuse not faster: {time_with_reuse}s vs {time_without_reuse}s"


class TestConnectionPooling:
    """Test connection pooling performance."""

    def test_connection_pool_reuse(self):
        """Test connection pool reuse reduces overhead."""
        class MockConnectionPool:
            def __init__(self, max_connections: int):
                self.max_connections = max_connections
                self.available_connections = []
                self.in_use = 0
                self.lock = threading.Lock()

            def acquire(self) -> int:
                """Acquire a connection from pool."""
                with self.lock:
                    if self.available_connections:
                        return self.available_connections.pop()
                    elif self.in_use < self.max_connections:
                        conn_id = self.in_use
                        self.in_use += 1
                        return conn_id
                    else:
                        # Wait for available connection
                        time.sleep(0.01)
                        return self.acquire()

            def release(self, conn_id: int) -> None:
                """Release connection back to pool."""
                with self.lock:
                    self.available_connections.append(conn_id)

        pool = MockConnectionPool(max_connections=10)
        executed = []
        lock = threading.Lock()

        def execute_query(query_id: int) -> None:
            """Execute query using pooled connection."""
            conn = pool.acquire()
            # Simulate query execution
            time.sleep(0.01)
            with lock:
                executed.append(query_id)
            pool.release(conn)

        start_time = time.time()

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(execute_query, i) for i in range(100)]
            for f in as_completed(futures):
                f.result()

        elapsed = time.time() - start_time

        assert len(executed) == 100
        # Connection pooling should handle 100 queries efficiently
        assert elapsed < 2.0, f"Connection pooling too slow: {elapsed}s"


class TestDeadlockPrevention:
    """Test for deadlock prevention in concurrent operations."""

    def test_no_deadlock_with_ordered_locks(self):
        """Test that ordered lock acquisition prevents deadlocks."""
        lock_a = threading.Lock()
        lock_b = threading.Lock()
        results = []

        def task1():
            """Task that acquires locks in order A, B."""
            with lock_a:
                time.sleep(0.01)
                with lock_b:
                    results.append("task1")

        def task2():
            """Task that also acquires locks in order A, B."""
            with lock_a:
                time.sleep(0.01)
                with lock_b:
                    results.append("task2")

        # Run concurrently - should not deadlock
        t1 = threading.Thread(target=task1)
        t2 = threading.Thread(target=task2)

        start_time = time.time()
        t1.start()
        t2.start()
        t1.join(timeout=2.0)
        t2.join(timeout=2.0)
        elapsed = time.time() - start_time

        assert len(results) == 2
        assert elapsed < 1.0, f"Possible deadlock detected: {elapsed}s"


class TestConcurrencyLimits:
    """Test system behavior at concurrency limits."""

    def test_max_concurrent_connections(self):
        """Test behavior at maximum concurrent connections."""
        max_connections = 50
        connection_semaphore = threading.Semaphore(max_connections)
        active_connections = []
        lock = threading.Lock()

        def simulate_connection(conn_id: int) -> None:
            """Simulate a connection."""
            with connection_semaphore:
                with lock:
                    active_connections.append(conn_id)
                time.sleep(0.05)  # Simulate work
                with lock:
                    active_connections.remove(conn_id)

        # Try to create more connections than allowed
        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = [
                executor.submit(simulate_connection, i)
                for i in range(100)
            ]
            for f in as_completed(futures):
                f.result()

        # All connections should have completed
        assert len(active_connections) == 0

    @pytest.mark.asyncio
    async def test_async_concurrency_limit(self):
        """Test async concurrency limiting."""
        max_concurrent = 10
        semaphore = asyncio.Semaphore(max_concurrent)
        active_count = 0
        max_active = 0
        lock = asyncio.Lock()

        async def limited_task(task_id: int) -> None:
            """Task with concurrency limit."""
            nonlocal active_count, max_active

            async with semaphore:
                async with lock:
                    active_count += 1
                    max_active = max(max_active, active_count)

                await asyncio.sleep(0.01)  # Simulate work

                async with lock:
                    active_count -= 1

        # Launch 50 tasks but only 10 should run concurrently
        tasks = [limited_task(i) for i in range(50)]
        await asyncio.gather(*tasks)

        assert max_active <= max_concurrent, \
            f"Concurrency limit exceeded: {max_active} > {max_concurrent}"
