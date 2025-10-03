"""
Performance reporting and visualization.

Generate reports, charts, and dashboards for performance test results.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend


@dataclass
class PerformanceReport:
    """Performance test report."""
    test_name: str
    timestamp: str
    duration_seconds: float
    metrics: Dict[str, float]
    regressions: List[Dict[str, Any]]
    summary: str
    passed: bool


class PerformanceReporter:
    """Generate performance reports."""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.reports: List[PerformanceReport] = []

    def create_report(self, test_name: str, metrics: Dict[str, float],
                     regressions: List[Dict[str, Any]] = None,
                     baseline: Dict[str, float] = None) -> PerformanceReport:
        """Create performance report."""
        regressions = regressions or []
        passed = len(regressions) == 0

        summary = self._generate_summary(test_name, metrics, regressions, baseline)

        report = PerformanceReport(
            test_name=test_name,
            timestamp=datetime.now().isoformat(),
            duration_seconds=sum(metrics.values()) / 1000,  # Approximate
            metrics=metrics,
            regressions=regressions,
            summary=summary,
            passed=passed
        )

        self.reports.append(report)
        return report

    def _generate_summary(self, test_name: str, metrics: Dict[str, float],
                         regressions: List[Dict[str, Any]],
                         baseline: Dict[str, float] = None) -> str:
        """Generate summary text."""
        lines = [f"Performance Test: {test_name}"]
        lines.append(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        if baseline:
            lines.append("Metrics vs Baseline:")
            for metric, value in metrics.items():
                baseline_val = baseline.get(metric)
                if baseline_val:
                    pct_diff = ((value - baseline_val) / baseline_val) * 100
                    symbol = "📈" if pct_diff > 0 else "📉"
                    lines.append(f"  {metric}: {value:.2f} ({symbol} {pct_diff:+.1f}%)")
                else:
                    lines.append(f"  {metric}: {value:.2f}")
        else:
            lines.append("Metrics:")
            for metric, value in metrics.items():
                lines.append(f"  {metric}: {value:.2f}")

        if regressions:
            lines.append("")
            lines.append(f"REGRESSIONS DETECTED ({len(regressions)}):")
            for reg in regressions:
                lines.append(f"  - {reg['metric']}: {reg['current']:.2f} "
                           f"(baseline: {reg['baseline']:.2f}, "
                           f"+{reg['increase_pct']:.1f}%)")
        else:
            lines.append("")
            lines.append("✅ No regressions detected")

        return "\n".join(lines)

    def save_report(self, report: PerformanceReport, format: str = "json"):
        """Save report to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"{report.test_name}_{timestamp}"

        if format == "json":
            output_file = self.output_dir / f"{base_name}.json"
            with open(output_file, 'w') as f:
                json.dump(asdict(report), f, indent=2)

        elif format == "html":
            output_file = self.output_dir / f"{base_name}.html"
            html = self._generate_html(report)
            with open(output_file, 'w') as f:
                f.write(html)

        elif format == "txt":
            output_file = self.output_dir / f"{base_name}.txt"
            with open(output_file, 'w') as f:
                f.write(report.summary)

        print(f"Report saved to: {output_file}")
        return output_file

    def _generate_html(self, report: PerformanceReport) -> str:
        """Generate HTML report."""
        status_color = "green" if report.passed else "red"
        status_text = "PASSED" if report.passed else "FAILED"

        metrics_html = "\n".join([
            f"<tr><td>{metric}</td><td>{value:.2f}</td></tr>"
            for metric, value in report.metrics.items()
        ])

        regressions_html = ""
        if report.regressions:
            regressions_html = "<h3>Regressions</h3><ul>"
            for reg in report.regressions:
                regressions_html += f"<li>{reg['metric']}: {reg['current']:.2f} "
                regressions_html += f"(+{reg['increase_pct']:.1f}% from baseline)</li>"
            regressions_html += "</ul>"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Performance Report: {report.test_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .status {{ font-weight: bold; color: {status_color}; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #4CAF50; color: white; }}
                .regression {{ color: red; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Performance Test Report</h1>
                <p><strong>Test:</strong> {report.test_name}</p>
                <p><strong>Timestamp:</strong> {report.timestamp}</p>
                <p><strong>Status:</strong> <span class="status">{status_text}</span></p>
            </div>

            <h2>Metrics</h2>
            <table>
                <tr><th>Metric</th><th>Value</th></tr>
                {metrics_html}
            </table>

            {regressions_html}

            <h2>Summary</h2>
            <pre>{report.summary}</pre>
        </body>
        </html>
        """
        return html

    def generate_comparison_report(self, reports: List[PerformanceReport]):
        """Generate comparison report across multiple test runs."""
        df = pd.DataFrame([
            {"test": r.test_name, "timestamp": r.timestamp, **r.metrics}
            for r in reports
        ])

        output_file = self.output_dir / "comparison_report.csv"
        df.to_csv(output_file, index=False)
        print(f"Comparison report saved to: {output_file}")
        return df


class PerformanceVisualizer:
    """Create performance visualizations."""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def plot_benchmark_comparison(self, data: Dict[str, List[float]],
                                  title: str = "Benchmark Comparison",
                                  ylabel: str = "Time (ms)"):
        """Plot benchmark comparison bar chart."""
        df = pd.DataFrame(data)
        means = df.mean()

        plt.figure(figsize=(10, 6))
        means.plot(kind='bar')
        plt.title(title)
        plt.xlabel("Test")
        plt.ylabel(ylabel)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()

        output_file = self.output_dir / f"{title.replace(' ', '_').lower()}.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"Chart saved to: {output_file}")
        return output_file

    def plot_time_series(self, df: pd.DataFrame, metric_name: str,
                        title: Optional[str] = None):
        """Plot metric over time."""
        if 'timestamp' not in df.columns:
            print("Warning: No timestamp column found")
            return

        title = title or f"{metric_name} Over Time"

        plt.figure(figsize=(12, 6))
        plt.plot(pd.to_datetime(df['timestamp']), df[metric_name], marker='o')
        plt.title(title)
        plt.xlabel("Time")
        plt.ylabel(metric_name)
        plt.xticks(rotation=45, ha='right')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        output_file = self.output_dir / f"{metric_name}_timeseries.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"Time series chart saved to: {output_file}")
        return output_file

    def plot_memory_usage(self, measurements: List[Dict[str, Any]],
                         title: str = "Memory Usage"):
        """Plot memory usage over time."""
        df = pd.DataFrame(measurements)

        plt.figure(figsize=(12, 6))
        plt.plot(df['timestamp'] - df['timestamp'].iloc[0],
                df['rss_mb'], label='RSS', linewidth=2)
        plt.title(title)
        plt.xlabel("Time (s)")
        plt.ylabel("Memory (MB)")
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        output_file = self.output_dir / "memory_usage.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"Memory chart saved to: {output_file}")
        return output_file

    def plot_performance_distribution(self, data: List[float],
                                     title: str = "Performance Distribution",
                                     xlabel: str = "Time (ms)"):
        """Plot performance distribution histogram."""
        plt.figure(figsize=(10, 6))
        plt.hist(data, bins=30, edgecolor='black', alpha=0.7)
        plt.axvline(pd.Series(data).median(), color='red',
                   linestyle='--', label=f'Median: {pd.Series(data).median():.2f}ms')
        plt.title(title)
        plt.xlabel(xlabel)
        plt.ylabel("Frequency")
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        output_file = self.output_dir / f"{title.replace(' ', '_').lower()}.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"Distribution chart saved to: {output_file}")
        return output_file

    def plot_regression_analysis(self, baseline: Dict[str, float],
                                current: Dict[str, float]):
        """Plot regression analysis comparison."""
        metrics = list(baseline.keys())
        baseline_vals = [baseline[m] for m in metrics]
        current_vals = [current.get(m, 0) for m in metrics]

        x = range(len(metrics))
        width = 0.35

        plt.figure(figsize=(12, 6))
        plt.bar([i - width/2 for i in x], baseline_vals, width, label='Baseline', alpha=0.8)
        plt.bar([i + width/2 for i in x], current_vals, width, label='Current', alpha=0.8)

        plt.xlabel("Metrics")
        plt.ylabel("Value (ms)")
        plt.title("Performance: Current vs Baseline")
        plt.xticks(x, metrics, rotation=45, ha='right')
        plt.legend()
        plt.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()

        output_file = self.output_dir / "regression_analysis.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"Regression analysis chart saved to: {output_file}")
        return output_file

    def plot_concurrency_scaling(self, concurrency_levels: List[int],
                                response_times: List[float]):
        """Plot concurrency scaling chart."""
        plt.figure(figsize=(10, 6))
        plt.plot(concurrency_levels, response_times, marker='o', linewidth=2)
        plt.title("Response Time vs Concurrency Level")
        plt.xlabel("Concurrent Users")
        plt.ylabel("Average Response Time (ms)")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        output_file = self.output_dir / "concurrency_scaling.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"Concurrency scaling chart saved to: {output_file}")
        return output_file


class PerformanceDashboard:
    """Generate comprehensive performance dashboard."""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.reporter = PerformanceReporter(output_dir)
        self.visualizer = PerformanceVisualizer(output_dir)

    def generate_dashboard(self, metrics: Dict[str, Any],
                          baseline: Dict[str, float] = None,
                          history: pd.DataFrame = None):
        """Generate complete performance dashboard."""
        print("Generating performance dashboard...")

        # Create report
        regressions = self._detect_regressions(metrics, baseline) if baseline else []
        report = self.reporter.create_report(
            "Performance Dashboard",
            metrics,
            regressions,
            baseline
        )

        # Save reports in multiple formats
        self.reporter.save_report(report, format="json")
        self.reporter.save_report(report, format="html")

        # Generate visualizations
        if baseline:
            self.visualizer.plot_regression_analysis(baseline, metrics)

        if history is not None and not history.empty:
            for metric in metrics.keys():
                if metric in history.columns:
                    self.visualizer.plot_time_series(history, metric)

        print(f"Dashboard generated in: {self.output_dir}")

    def _detect_regressions(self, current: Dict[str, float],
                          baseline: Dict[str, float],
                          threshold: float = 1.2) -> List[Dict[str, Any]]:
        """Detect performance regressions."""
        regressions = []
        for metric, value in current.items():
            baseline_val = baseline.get(metric)
            if baseline_val and value > baseline_val * threshold:
                regressions.append({
                    "metric": metric,
                    "baseline": baseline_val,
                    "current": value,
                    "increase_pct": ((value - baseline_val) / baseline_val) * 100
                })
        return regressions


def generate_load_test_report(stats: Dict[str, Any], output_file: Path):
    """Generate report from Locust load test statistics."""
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_requests": stats.get("total_requests", 0),
        "total_failures": stats.get("total_failures", 0),
        "failure_rate": stats.get("failure_rate", 0),
        "average_response_time": stats.get("avg_response_time", 0),
        "rps": stats.get("total_rps", 0),
        "percentiles": {
            "50th": stats.get("response_time_percentile_50", 0),
            "95th": stats.get("response_time_percentile_95", 0),
            "99th": stats.get("response_time_percentile_99", 0),
        }
    }

    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"Load test report saved to: {output_file}")
    return report
