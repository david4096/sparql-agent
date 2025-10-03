"""
Performance profiling utilities.

Tools for CPU profiling, memory profiling, and performance analysis.
"""

import cProfile
import pstats
import io
import time
import psutil
import functools
from typing import Callable, Any, Dict, List, Optional
from pathlib import Path
from dataclasses import dataclass, field
from contextlib import contextmanager

import pandas as pd


@dataclass
class ProfileResult:
    """Container for profiling results."""
    function_name: str
    execution_time: float
    memory_used_mb: float
    cpu_percent: float
    call_count: int = 0
    stats: Dict[str, Any] = field(default_factory=dict)


class CPUProfiler:
    """CPU profiler using cProfile."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path("tests/performance/profiles")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.profiler = None

    @contextmanager
    def profile(self, name: str = "profile"):
        """Context manager for profiling code block."""
        self.profiler = cProfile.Profile()
        self.profiler.enable()

        try:
            yield self.profiler
        finally:
            self.profiler.disable()
            self._save_stats(name)

    def _save_stats(self, name: str):
        """Save profiling statistics."""
        # Save binary stats
        stats_file = self.output_dir / f"{name}.prof"
        self.profiler.dump_stats(str(stats_file))

        # Save human-readable stats
        s = io.StringIO()
        ps = pstats.Stats(self.profiler, stream=s)
        ps.strip_dirs()
        ps.sort_stats('cumulative')
        ps.print_stats(50)  # Top 50 functions

        text_file = self.output_dir / f"{name}.txt"
        with open(text_file, 'w') as f:
            f.write(s.getvalue())

        print(f"CPU profile saved to {stats_file}")

    def profile_function(self, func: Callable) -> Callable:
        """Decorator to profile a function."""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with self.profile(func.__name__):
                return func(*args, **kwargs)
        return wrapper

    def get_stats(self) -> pstats.Stats:
        """Get profiling statistics."""
        if self.profiler:
            return pstats.Stats(self.profiler)
        return None

    def print_stats(self, sort_by: str = 'cumulative', limit: int = 20):
        """Print profiling statistics."""
        if self.profiler:
            s = io.StringIO()
            ps = pstats.Stats(self.profiler, stream=s)
            ps.strip_dirs()
            ps.sort_stats(sort_by)
            ps.print_stats(limit)
            print(s.getvalue())


class MemoryProfiler:
    """Memory profiler for tracking memory usage."""

    def __init__(self, interval: float = 0.1):
        self.interval = interval
        self.measurements: List[Dict[str, Any]] = []
        self.process = psutil.Process()

    def start(self):
        """Start memory profiling."""
        self.measurements = []
        self._take_measurement("start")

    def measure(self, label: str = ""):
        """Take a memory measurement."""
        self._take_measurement(label)

    def stop(self) -> Dict[str, float]:
        """Stop profiling and return statistics."""
        self._take_measurement("stop")
        return self._calculate_stats()

    def _take_measurement(self, label: str):
        """Take a single memory measurement."""
        mem_info = self.process.memory_info()
        self.measurements.append({
            "timestamp": time.time(),
            "label": label,
            "rss_mb": mem_info.rss / 1024 / 1024,
            "vms_mb": mem_info.vms / 1024 / 1024,
        })

    def _calculate_stats(self) -> Dict[str, float]:
        """Calculate memory usage statistics."""
        if not self.measurements:
            return {}

        rss_values = [m["rss_mb"] for m in self.measurements]
        return {
            "start_mb": rss_values[0],
            "end_mb": rss_values[-1],
            "peak_mb": max(rss_values),
            "min_mb": min(rss_values),
            "avg_mb": sum(rss_values) / len(rss_values),
            "growth_mb": rss_values[-1] - rss_values[0],
        }

    def get_dataframe(self) -> pd.DataFrame:
        """Get measurements as pandas DataFrame."""
        return pd.DataFrame(self.measurements)

    @contextmanager
    def profile(self, label: str = "profile"):
        """Context manager for memory profiling."""
        self.start()
        try:
            yield self
        finally:
            stats = self.stop()
            print(f"\nMemory Profile [{label}]:")
            print(f"  Start: {stats['start_mb']:.2f} MB")
            print(f"  Peak:  {stats['peak_mb']:.2f} MB")
            print(f"  End:   {stats['end_mb']:.2f} MB")
            print(f"  Growth: {stats['growth_mb']:.2f} MB")


class PerformanceMonitor:
    """Comprehensive performance monitor combining CPU and memory profiling."""

    def __init__(self, name: str = "monitor"):
        self.name = name
        self.cpu_profiler = CPUProfiler()
        self.mem_profiler = MemoryProfiler()
        self.start_time = None
        self.end_time = None

    @contextmanager
    def monitor(self):
        """Monitor performance of code block."""
        self.start_time = time.perf_counter()
        self.mem_profiler.start()

        with self.cpu_profiler.profile(self.name):
            try:
                yield self
            finally:
                self.end_time = time.perf_counter()
                mem_stats = self.mem_profiler.stop()
                self._print_summary(mem_stats)

    def _print_summary(self, mem_stats: Dict[str, float]):
        """Print performance summary."""
        elapsed = self.end_time - self.start_time
        print(f"\nPerformance Monitor [{self.name}]:")
        print(f"  Execution Time: {elapsed:.3f}s")
        print(f"  Memory Start:   {mem_stats['start_mb']:.2f} MB")
        print(f"  Memory Peak:    {mem_stats['peak_mb']:.2f} MB")
        print(f"  Memory Growth:  {mem_stats['growth_mb']:.2f} MB")


class FunctionProfiler:
    """Profile individual functions with detailed metrics."""

    def __init__(self):
        self.results: Dict[str, ProfileResult] = {}

    def profile(self, func: Callable) -> Callable:
        """Decorator to profile a function."""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = self._profile_execution(func, *args, **kwargs)
            self.results[func.__name__] = result
            return result.stats.get("return_value")
        return wrapper

    def _profile_execution(self, func: Callable, *args, **kwargs) -> ProfileResult:
        """Profile function execution."""
        process = psutil.Process()

        # Measure before
        mem_before = process.memory_info().rss / 1024 / 1024
        cpu_before = process.cpu_percent()
        start_time = time.perf_counter()

        # Execute function
        return_value = func(*args, **kwargs)

        # Measure after
        elapsed = time.perf_counter() - start_time
        mem_after = process.memory_info().rss / 1024 / 1024
        cpu_after = process.cpu_percent()

        return ProfileResult(
            function_name=func.__name__,
            execution_time=elapsed,
            memory_used_mb=mem_after - mem_before,
            cpu_percent=(cpu_after + cpu_before) / 2,
            call_count=1,
            stats={"return_value": return_value}
        )

    def get_result(self, func_name: str) -> Optional[ProfileResult]:
        """Get profiling result for a function."""
        return self.results.get(func_name)

    def get_all_results(self) -> Dict[str, ProfileResult]:
        """Get all profiling results."""
        return self.results

    def print_results(self):
        """Print all profiling results."""
        print("\nFunction Profiling Results:")
        print("=" * 80)
        for name, result in self.results.items():
            print(f"\nFunction: {name}")
            print(f"  Execution Time: {result.execution_time:.4f}s")
            print(f"  Memory Used:    {result.memory_used_mb:.2f} MB")
            print(f"  CPU Usage:      {result.cpu_percent:.1f}%")
            print(f"  Call Count:     {result.call_count}")


class LineProfiler:
    """Line-by-line profiler for detailed analysis."""

    def __init__(self):
        self.line_stats: Dict[str, List[tuple]] = {}

    def profile_lines(self, func: Callable) -> Callable:
        """Profile function line by line."""
        # Note: Full line profiling requires line_profiler package
        # This is a simplified version
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            elapsed = time.perf_counter() - start

            # Store timing for the function
            if func.__name__ not in self.line_stats:
                self.line_stats[func.__name__] = []
            self.line_stats[func.__name__].append((elapsed, args, kwargs))

            return result
        return wrapper


class PerformanceComparator:
    """Compare performance of different implementations."""

    def __init__(self):
        self.implementations: Dict[str, Callable] = {}
        self.results: Dict[str, List[float]] = {}

    def add_implementation(self, name: str, func: Callable):
        """Add an implementation to compare."""
        self.implementations[name] = func

    def compare(self, iterations: int = 100, *args, **kwargs) -> pd.DataFrame:
        """Compare all implementations."""
        for name, func in self.implementations.items():
            times = []
            for _ in range(iterations):
                start = time.perf_counter()
                func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                times.append(elapsed * 1000)  # Convert to ms

            self.results[name] = times

        # Create comparison DataFrame
        df = pd.DataFrame(self.results)
        return df.describe()

    def print_comparison(self, iterations: int = 100, *args, **kwargs):
        """Print comparison results."""
        df = self.compare(iterations, *args, **kwargs)
        print("\nPerformance Comparison:")
        print("=" * 80)
        print(df)
        print("\nWinner (by median):")
        medians = df.loc["50%"]
        winner = medians.idxmin()
        print(f"  {winner}: {medians[winner]:.3f}ms")


def profile_async_function(func: Callable) -> Callable:
    """Profile async function execution."""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = await func(*args, **kwargs)
        elapsed = time.perf_counter() - start_time

        print(f"\nAsync Function: {func.__name__}")
        print(f"  Execution Time: {elapsed:.4f}s")

        return result
    return wrapper


def generate_flame_graph(prof_file: Path, output_file: Path):
    """Generate flame graph from profiling data."""
    # Note: Requires flamegraph package
    # This is a placeholder for flame graph generation
    print(f"Flame graph generation: {prof_file} -> {output_file}")
    print("To generate flame graphs, use: py-spy record --format flamegraph -o output.svg -- python script.py")


class PerformanceTracker:
    """Track performance metrics over time."""

    def __init__(self, metrics_file: Path):
        self.metrics_file = metrics_file
        self.metrics: List[Dict[str, Any]] = []
        self._load_metrics()

    def _load_metrics(self):
        """Load existing metrics."""
        if self.metrics_file.exists():
            import json
            with open(self.metrics_file, 'r') as f:
                self.metrics = json.load(f)

    def record_metric(self, test_name: str, metric_name: str,
                     value: float, unit: str = "ms"):
        """Record a performance metric."""
        self.metrics.append({
            "timestamp": time.time(),
            "test": test_name,
            "metric": metric_name,
            "value": value,
            "unit": unit
        })

    def save(self):
        """Save metrics to file."""
        import json
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.metrics_file, 'w') as f:
            json.dump(self.metrics, f, indent=2)

    def get_history(self, test_name: str, metric_name: str) -> pd.DataFrame:
        """Get historical data for a metric."""
        filtered = [
            m for m in self.metrics
            if m["test"] == test_name and m["metric"] == metric_name
        ]
        return pd.DataFrame(filtered)

    def detect_trend(self, test_name: str, metric_name: str,
                    window: int = 10) -> str:
        """Detect performance trend."""
        df = self.get_history(test_name, metric_name)
        if len(df) < window:
            return "insufficient_data"

        recent = df.tail(window)["value"].mean()
        previous = df.head(len(df) - window)["value"].mean() if len(df) > window else recent

        if recent > previous * 1.1:
            return "degrading"
        elif recent < previous * 0.9:
            return "improving"
        else:
            return "stable"
