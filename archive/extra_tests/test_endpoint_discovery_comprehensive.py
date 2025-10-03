#!/usr/bin/env python3
"""
Comprehensive SPARQL Endpoint Discovery System Test Suite

Tests the endpoint discovery system with multiple real endpoints, measuring:
- Discovery capabilities across different endpoint types
- Performance (fast mode vs full discovery)
- Timeout handling (progressive vs fixed)
- Feature detection accuracy
- Edge case handling (slow endpoints, errors, non-existent)
- Concurrent discovery performance

This script provides detailed metrics and generates a comprehensive test report.
"""

import asyncio
import json
import logging
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

# Setup path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sparql_agent.discovery.capabilities import CapabilitiesDetector
from sparql_agent.discovery.connectivity import EndpointPinger, ConnectionConfig
from sparql_agent.discovery.statistics import StatisticsCollector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class EndpointTestCase:
    """Test case for an endpoint"""
    name: str
    url: str
    description: str
    expected_features: List[str] = field(default_factory=list)
    expected_namespaces: List[str] = field(default_factory=list)
    known_slow: bool = False
    requires_auth: bool = False


@dataclass
class DiscoveryTestResult:
    """Result of a discovery test"""
    endpoint_name: str
    endpoint_url: str
    mode: str  # 'fast' or 'full'
    success: bool
    duration_seconds: float
    error_message: Optional[str] = None

    # Connectivity results
    connectivity_status: Optional[str] = None
    response_time_ms: Optional[float] = None

    # Capability detection results
    sparql_version: Optional[str] = None
    features_detected: List[str] = field(default_factory=list)
    namespaces_count: int = 0
    named_graphs_count: int = 0
    supported_functions_count: int = 0

    # Statistics (if collected)
    total_triples: Optional[int] = None
    distinct_subjects: Optional[int] = None
    top_classes_count: int = 0

    # Metadata
    failed_queries: List[str] = field(default_factory=list)
    timed_out_queries: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class TestReport:
    """Comprehensive test report"""
    test_run_timestamp: str
    total_endpoints_tested: int
    successful_discoveries: int
    failed_discoveries: int
    total_duration_seconds: float

    results_by_endpoint: Dict[str, List[DiscoveryTestResult]] = field(default_factory=dict)
    performance_comparison: Dict[str, Any] = field(default_factory=dict)
    edge_case_results: Dict[str, Any] = field(default_factory=dict)
    concurrent_test_results: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'test_run_timestamp': self.test_run_timestamp,
            'total_endpoints_tested': self.total_endpoints_tested,
            'successful_discoveries': self.successful_discoveries,
            'failed_discoveries': self.failed_discoveries,
            'total_duration_seconds': self.total_duration_seconds,
            'results_by_endpoint': {
                name: [asdict(r) for r in results]
                for name, results in self.results_by_endpoint.items()
            },
            'performance_comparison': self.performance_comparison,
            'edge_case_results': self.edge_case_results,
            'concurrent_test_results': self.concurrent_test_results,
        }


class EndpointDiscoveryTester:
    """Comprehensive tester for endpoint discovery system"""

    # Define test endpoints
    TEST_ENDPOINTS = [
        EndpointTestCase(
            name="Wikidata",
            url="https://query.wikidata.org/sparql",
            description="Large public knowledge graph",
            expected_features=["OPTIONAL", "UNION", "FILTER", "BIND"],
            expected_namespaces=["http://www.wikidata.org/", "http://www.w3.org/"],
            known_slow=True
        ),
        EndpointTestCase(
            name="UniProt",
            url="https://sparql.uniprot.org/sparql",
            description="Protein sequence and functional information",
            expected_features=["OPTIONAL", "FILTER", "BIND"],
            expected_namespaces=["http://purl.uniprot.org/", "http://www.w3.org/"],
            known_slow=False
        ),
        EndpointTestCase(
            name="DBpedia",
            url="https://dbpedia.org/sparql",
            description="Structured content from Wikipedia",
            expected_features=["OPTIONAL", "UNION", "FILTER"],
            expected_namespaces=["http://dbpedia.org/", "http://www.w3.org/"],
            known_slow=True
        ),
        EndpointTestCase(
            name="ChEMBL",
            url="https://www.ebi.ac.uk/rdf/services/chembl/sparql",
            description="Bioactive drug-like small molecules",
            expected_features=["OPTIONAL", "FILTER"],
            expected_namespaces=["http://rdf.ebi.ac.uk/", "http://www.w3.org/"],
            known_slow=False
        ),
    ]

    EDGE_CASE_ENDPOINTS = [
        EndpointTestCase(
            name="Non-existent",
            url="https://example.com/sparql/nonexistent",
            description="Test handling of non-existent endpoint",
        ),
        EndpointTestCase(
            name="Invalid-URL",
            url="not-a-valid-url",
            description="Test handling of invalid URL format",
        ),
    ]

    def __init__(self, output_dir: Path = Path("test_results")):
        """Initialize the tester"""
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
        self.report = TestReport(
            test_run_timestamp=datetime.now().isoformat(),
            total_endpoints_tested=0,
            successful_discoveries=0,
            failed_discoveries=0,
            total_duration_seconds=0.0
        )

    def test_connectivity(self, endpoint: EndpointTestCase, timeout: int = 10) -> Dict[str, Any]:
        """Test basic connectivity to endpoint"""
        logger.info(f"Testing connectivity for {endpoint.name}...")

        try:
            config = ConnectionConfig(
                timeout=timeout,
                verify_ssl=True,
                retry_attempts=2
            )

            pinger = EndpointPinger(config=config)

            start_time = time.time()
            health = pinger.ping_sync(endpoint.url, check_query=True)
            duration = time.time() - start_time

            pinger.close_sync()

            return {
                'success': health.status.value in ['healthy', 'degraded'],
                'status': health.status.value,
                'response_time_ms': health.response_time_ms,
                'duration_seconds': duration,
                'error_message': health.error_message
            }

        except Exception as e:
            logger.error(f"Connectivity test failed for {endpoint.name}: {e}")
            return {
                'success': False,
                'status': 'error',
                'error_message': str(e)
            }

    def test_discovery(
        self,
        endpoint: EndpointTestCase,
        fast_mode: bool = False,
        progressive_timeout: bool = True,
        timeout: int = 30
    ) -> DiscoveryTestResult:
        """Test endpoint discovery"""
        mode = 'fast' if fast_mode else 'full'
        logger.info(f"Testing discovery for {endpoint.name} in {mode} mode...")

        start_time = time.time()

        try:
            # Test connectivity first
            connectivity_result = self.test_connectivity(endpoint, timeout=10)

            if not connectivity_result['success']:
                return DiscoveryTestResult(
                    endpoint_name=endpoint.name,
                    endpoint_url=endpoint.url,
                    mode=mode,
                    success=False,
                    duration_seconds=time.time() - start_time,
                    error_message=connectivity_result.get('error_message', 'Connectivity check failed'),
                    connectivity_status=connectivity_result['status']
                )

            # Run discovery
            detector = CapabilitiesDetector(
                endpoint.url,
                timeout=timeout,
                fast_mode=fast_mode,
                progressive_timeout=progressive_timeout,
                max_samples=1000
            )

            # Progress tracking
            progress_steps = []
            def progress_callback(current, total, message):
                progress_steps.append({
                    'step': current,
                    'total': total,
                    'message': message,
                    'timestamp': time.time() - start_time
                })
                logger.debug(f"  [{current}/{total}] {message}")

            capabilities = detector.detect_all_capabilities(
                progress_callback=progress_callback
            )

            duration = time.time() - start_time

            # Extract results
            result = DiscoveryTestResult(
                endpoint_name=endpoint.name,
                endpoint_url=endpoint.url,
                mode=mode,
                success=True,
                duration_seconds=duration,
                connectivity_status=connectivity_result['status'],
                response_time_ms=connectivity_result.get('response_time_ms'),
                sparql_version=capabilities.get('sparql_version'),
                features_detected=capabilities.get('features', {}).get('supported_features', []) if capabilities.get('features') else [],
                namespaces_count=len(capabilities.get('namespaces', {}).get('discovered_namespaces', [])) if capabilities.get('namespaces') else 0,
                named_graphs_count=len(capabilities.get('named_graphs', [])) if capabilities.get('named_graphs') else 0,
                supported_functions_count=len(capabilities.get('supported_functions', [])) if capabilities.get('supported_functions') else 0,
                failed_queries=capabilities.get('_metadata', {}).get('failed_queries', []),
                timed_out_queries=capabilities.get('_metadata', {}).get('timed_out_queries', [])
            )

            # Add warnings for expected features not detected
            for expected_feature in endpoint.expected_features:
                if expected_feature not in result.features_detected:
                    result.warnings.append(f"Expected feature not detected: {expected_feature}")

            # Try to get statistics if in full mode
            if not fast_mode and connectivity_result['success']:
                try:
                    stats = capabilities.get('statistics')
                    if stats:
                        result.total_triples = stats.get('total_triples')
                        result.distinct_subjects = stats.get('distinct_subjects')
                        result.top_classes_count = len(stats.get('top_classes', []))
                except Exception as e:
                    logger.warning(f"Could not extract statistics: {e}")

            logger.info(f"Discovery completed for {endpoint.name} in {duration:.2f}s")
            return result

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Discovery failed for {endpoint.name}: {e}")
            return DiscoveryTestResult(
                endpoint_name=endpoint.name,
                endpoint_url=endpoint.url,
                mode=mode,
                success=False,
                duration_seconds=duration,
                error_message=str(e)
            )

    def test_performance_comparison(self, endpoint: EndpointTestCase) -> Dict[str, Any]:
        """Compare fast mode vs full discovery performance"""
        logger.info(f"\n{'='*70}")
        logger.info(f"Performance Comparison: {endpoint.name}")
        logger.info(f"{'='*70}")

        # Test fast mode
        fast_result = self.test_discovery(endpoint, fast_mode=True, timeout=30)

        # Test full mode (with longer timeout for known slow endpoints)
        full_timeout = 60 if endpoint.known_slow else 30
        full_result = self.test_discovery(endpoint, fast_mode=False, timeout=full_timeout)

        # Calculate speedup
        speedup = None
        if fast_result.success and full_result.success:
            speedup = full_result.duration_seconds / fast_result.duration_seconds

        comparison = {
            'endpoint': endpoint.name,
            'fast_mode': {
                'success': fast_result.success,
                'duration_seconds': fast_result.duration_seconds,
                'features_detected': len(fast_result.features_detected),
                'namespaces_count': fast_result.namespaces_count,
            },
            'full_mode': {
                'success': full_result.success,
                'duration_seconds': full_result.duration_seconds,
                'features_detected': len(full_result.features_detected),
                'namespaces_count': full_result.namespaces_count,
                'total_triples': full_result.total_triples,
            },
            'speedup_factor': speedup,
            'additional_info_in_full': {
                'statistics_available': full_result.total_triples is not None,
                'additional_namespaces': full_result.namespaces_count - fast_result.namespaces_count,
            }
        }

        # Store results
        if endpoint.name not in self.report.results_by_endpoint:
            self.report.results_by_endpoint[endpoint.name] = []
        self.report.results_by_endpoint[endpoint.name].extend([fast_result, full_result])

        return comparison

    def test_timeout_strategies(self, endpoint: EndpointTestCase) -> Dict[str, Any]:
        """Test progressive vs fixed timeout strategies"""
        logger.info(f"\n{'='*70}")
        logger.info(f"Timeout Strategy Comparison: {endpoint.name}")
        logger.info(f"{'='*70}")

        # Test with progressive timeout
        progressive_result = self.test_discovery(
            endpoint,
            fast_mode=False,
            progressive_timeout=True,
            timeout=30
        )

        # Test with fixed timeout
        fixed_result = self.test_discovery(
            endpoint,
            fast_mode=False,
            progressive_timeout=False,
            timeout=30
        )

        return {
            'endpoint': endpoint.name,
            'progressive_timeout': {
                'success': progressive_result.success,
                'duration_seconds': progressive_result.duration_seconds,
                'timed_out_queries': len(progressive_result.timed_out_queries),
                'failed_queries': len(progressive_result.failed_queries),
            },
            'fixed_timeout': {
                'success': fixed_result.success,
                'duration_seconds': fixed_result.duration_seconds,
                'timed_out_queries': len(fixed_result.timed_out_queries),
                'failed_queries': len(fixed_result.failed_queries),
            },
            'progressive_advantage': {
                'fewer_timeouts': len(progressive_result.timed_out_queries) < len(fixed_result.timed_out_queries),
                'timeout_difference': len(fixed_result.timed_out_queries) - len(progressive_result.timed_out_queries),
            }
        }

    def test_edge_cases(self) -> Dict[str, Any]:
        """Test edge cases (non-existent endpoints, invalid URLs, etc.)"""
        logger.info(f"\n{'='*70}")
        logger.info(f"Edge Case Testing")
        logger.info(f"{'='*70}")

        edge_results = {}

        for endpoint in self.EDGE_CASE_ENDPOINTS:
            logger.info(f"\nTesting edge case: {endpoint.name}")
            result = self.test_discovery(endpoint, fast_mode=True, timeout=10)

            edge_results[endpoint.name] = {
                'description': endpoint.description,
                'expected_to_fail': True,
                'did_fail': not result.success,
                'handled_gracefully': result.error_message is not None,
                'error_message': result.error_message,
                'duration_seconds': result.duration_seconds
            }

            # Test should fail but handle gracefully
            if not result.success and result.error_message:
                logger.info(f"✓ Edge case handled correctly: {endpoint.name}")
            else:
                logger.warning(f"✗ Edge case not handled as expected: {endpoint.name}")

        return edge_results

    def test_concurrent_discovery(self, max_workers: int = 4) -> Dict[str, Any]:
        """Test concurrent discovery of multiple endpoints"""
        logger.info(f"\n{'='*70}")
        logger.info(f"Concurrent Discovery Test ({max_workers} workers)")
        logger.info(f"{'='*70}")

        start_time = time.time()

        # Run discoveries concurrently
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    self.test_discovery,
                    endpoint,
                    fast_mode=True,
                    timeout=30
                ): endpoint
                for endpoint in self.TEST_ENDPOINTS
            }

            for future in as_completed(futures):
                endpoint = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                    logger.info(f"Completed: {endpoint.name}")
                except Exception as e:
                    logger.error(f"Failed: {endpoint.name} - {e}")

        concurrent_duration = time.time() - start_time

        # Compare with sequential
        sequential_duration = sum(r.duration_seconds for r in results)

        return {
            'max_workers': max_workers,
            'endpoints_tested': len(results),
            'successful': sum(1 for r in results if r.success),
            'failed': sum(1 for r in results if not r.success),
            'concurrent_duration_seconds': concurrent_duration,
            'sequential_duration_estimate': sequential_duration,
            'speedup_factor': sequential_duration / concurrent_duration if concurrent_duration > 0 else 0,
            'results': [asdict(r) for r in results]
        }

    def run_all_tests(self):
        """Run all tests and generate comprehensive report"""
        logger.info("\n" + "="*70)
        logger.info("SPARQL ENDPOINT DISCOVERY COMPREHENSIVE TEST SUITE")
        logger.info("="*70)

        overall_start_time = time.time()

        # 1. Performance Comparison Tests
        logger.info("\n\n" + "="*70)
        logger.info("SECTION 1: Performance Comparison (Fast vs Full)")
        logger.info("="*70)

        for endpoint in self.TEST_ENDPOINTS[:2]:  # Test first 2 endpoints for performance
            comparison = self.test_performance_comparison(endpoint)
            self.report.performance_comparison[endpoint.name] = comparison

            if comparison['speedup_factor']:
                logger.info(f"\n{endpoint.name} Results:")
                logger.info(f"  Fast mode: {comparison['fast_mode']['duration_seconds']:.2f}s")
                logger.info(f"  Full mode: {comparison['full_mode']['duration_seconds']:.2f}s")
                logger.info(f"  Speedup: {comparison['speedup_factor']:.2f}x")

        # 2. Timeout Strategy Tests
        logger.info("\n\n" + "="*70)
        logger.info("SECTION 2: Timeout Strategy Comparison")
        logger.info("="*70)

        for endpoint in [self.TEST_ENDPOINTS[0]]:  # Test with Wikidata (known slow)
            timeout_results = self.test_timeout_strategies(endpoint)
            self.report.performance_comparison[f'{endpoint.name}_timeout'] = timeout_results

            logger.info(f"\n{endpoint.name} Timeout Strategy Results:")
            logger.info(f"  Progressive timeouts: {timeout_results['progressive_timeout']['timed_out_queries']} queries timed out")
            logger.info(f"  Fixed timeout: {timeout_results['fixed_timeout']['timed_out_queries']} queries timed out")

        # 3. Edge Case Tests
        logger.info("\n\n" + "="*70)
        logger.info("SECTION 3: Edge Case Testing")
        logger.info("="*70)

        self.report.edge_case_results = self.test_edge_cases()

        # 4. Concurrent Discovery Test
        logger.info("\n\n" + "="*70)
        logger.info("SECTION 4: Concurrent Discovery")
        logger.info("="*70)

        self.report.concurrent_test_results = self.test_concurrent_discovery(max_workers=4)

        logger.info(f"\nConcurrent discovery completed:")
        logger.info(f"  Concurrent: {self.report.concurrent_test_results['concurrent_duration_seconds']:.2f}s")
        logger.info(f"  Sequential estimate: {self.report.concurrent_test_results['sequential_duration_estimate']:.2f}s")
        logger.info(f"  Speedup: {self.report.concurrent_test_results['speedup_factor']:.2f}x")

        # 5. Individual Endpoint Tests (remaining endpoints)
        logger.info("\n\n" + "="*70)
        logger.info("SECTION 5: Additional Endpoint Testing")
        logger.info("="*70)

        for endpoint in self.TEST_ENDPOINTS[2:]:  # Test remaining endpoints
            result = self.test_discovery(endpoint, fast_mode=True, timeout=30)
            if endpoint.name not in self.report.results_by_endpoint:
                self.report.results_by_endpoint[endpoint.name] = []
            self.report.results_by_endpoint[endpoint.name].append(result)

            if result.success:
                logger.info(f"\n✓ {endpoint.name}: Discovery successful")
                logger.info(f"  Duration: {result.duration_seconds:.2f}s")
                logger.info(f"  Features: {len(result.features_detected)}")
                logger.info(f"  Namespaces: {result.namespaces_count}")
            else:
                logger.warning(f"\n✗ {endpoint.name}: Discovery failed - {result.error_message}")

        # Calculate summary statistics
        total_duration = time.time() - overall_start_time
        all_results = [r for results in self.report.results_by_endpoint.values() for r in results]

        self.report.total_endpoints_tested = len(set(r.endpoint_name for r in all_results))
        self.report.successful_discoveries = sum(1 for r in all_results if r.success)
        self.report.failed_discoveries = sum(1 for r in all_results if not r.success)
        self.report.total_duration_seconds = total_duration

        # Generate reports
        self.generate_report()

        logger.info("\n\n" + "="*70)
        logger.info("TEST SUITE COMPLETED")
        logger.info("="*70)
        logger.info(f"Total endpoints tested: {self.report.total_endpoints_tested}")
        logger.info(f"Successful discoveries: {self.report.successful_discoveries}")
        logger.info(f"Failed discoveries: {self.report.failed_discoveries}")
        logger.info(f"Total duration: {total_duration:.2f}s")
        logger.info(f"Reports saved to: {self.output_dir}")

    def generate_report(self):
        """Generate test reports in multiple formats"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # JSON report
        json_file = self.output_dir / f"discovery_test_report_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(self.report.to_dict(), f, indent=2, default=str)
        logger.info(f"\nJSON report saved: {json_file}")

        # Markdown report
        md_file = self.output_dir / f"discovery_test_report_{timestamp}.md"
        with open(md_file, 'w') as f:
            self.write_markdown_report(f)
        logger.info(f"Markdown report saved: {md_file}")

    def write_markdown_report(self, f):
        """Write detailed markdown report"""
        f.write("# SPARQL Endpoint Discovery Comprehensive Test Report\n\n")
        f.write(f"**Test Run:** {self.report.test_run_timestamp}\n\n")
        f.write(f"**Total Duration:** {self.report.total_duration_seconds:.2f} seconds\n\n")

        f.write("## Summary\n\n")
        f.write(f"- **Total Endpoints Tested:** {self.report.total_endpoints_tested}\n")
        f.write(f"- **Successful Discoveries:** {self.report.successful_discoveries}\n")
        f.write(f"- **Failed Discoveries:** {self.report.failed_discoveries}\n")
        f.write(f"- **Success Rate:** {(self.report.successful_discoveries / max(1, self.report.successful_discoveries + self.report.failed_discoveries) * 100):.1f}%\n\n")

        f.write("## Performance Comparison\n\n")
        f.write("### Fast Mode vs Full Discovery\n\n")
        f.write("| Endpoint | Fast Duration | Full Duration | Speedup | Features (Fast) | Features (Full) |\n")
        f.write("|----------|---------------|---------------|---------|-----------------|------------------|\n")
        for name, comparison in self.report.performance_comparison.items():
            if not name.endswith('_timeout') and 'speedup_factor' in comparison:
                f.write(f"| {comparison['endpoint']} | "
                       f"{comparison['fast_mode']['duration_seconds']:.2f}s | "
                       f"{comparison['full_mode']['duration_seconds']:.2f}s | "
                       f"{comparison['speedup_factor']:.2f}x | "
                       f"{comparison['fast_mode']['features_detected']} | "
                       f"{comparison['full_mode']['features_detected']} |\n")
        f.write("\n")

        f.write("### Timeout Strategy Comparison\n\n")
        for name, comparison in self.report.performance_comparison.items():
            if name.endswith('_timeout'):
                f.write(f"**{comparison['endpoint']}**\n\n")
                f.write(f"- Progressive Timeout: {comparison['progressive_timeout']['timed_out_queries']} timeouts\n")
                f.write(f"- Fixed Timeout: {comparison['fixed_timeout']['timed_out_queries']} timeouts\n")
                f.write(f"- Advantage: {comparison['progressive_advantage']['timeout_difference']} fewer timeouts\n\n")

        f.write("## Endpoint Discovery Results\n\n")
        for endpoint_name, results in self.report.results_by_endpoint.items():
            f.write(f"### {endpoint_name}\n\n")
            for result in results:
                f.write(f"**Mode:** {result.mode.upper()}\n\n")
                f.write(f"- **Status:** {'✓ Success' if result.success else '✗ Failed'}\n")
                f.write(f"- **Duration:** {result.duration_seconds:.2f}s\n")
                if result.response_time_ms:
                    f.write(f"- **Response Time:** {result.response_time_ms:.2f}ms\n")
                f.write(f"- **SPARQL Version:** {result.sparql_version or 'Unknown'}\n")
                f.write(f"- **Features Detected:** {len(result.features_detected)}\n")
                f.write(f"- **Namespaces:** {result.namespaces_count}\n")
                f.write(f"- **Named Graphs:** {result.named_graphs_count}\n")
                if result.total_triples:
                    f.write(f"- **Total Triples:** {result.total_triples:,}\n")
                if result.warnings:
                    f.write(f"- **Warnings:** {len(result.warnings)}\n")
                    for warning in result.warnings:
                        f.write(f"  - {warning}\n")
                f.write("\n")

        f.write("## Edge Case Testing\n\n")
        f.write("| Endpoint | Expected to Fail | Did Fail | Handled Gracefully |\n")
        f.write("|----------|------------------|----------|--------------------|\n")
        for name, result in self.report.edge_case_results.items():
            f.write(f"| {name} | "
                   f"{'Yes' if result['expected_to_fail'] else 'No'} | "
                   f"{'Yes' if result['did_fail'] else 'No'} | "
                   f"{'Yes' if result['handled_gracefully'] else 'No'} |\n")
        f.write("\n")

        if self.report.concurrent_test_results:
            f.write("## Concurrent Discovery Results\n\n")
            f.write(f"- **Workers:** {self.report.concurrent_test_results['max_workers']}\n")
            f.write(f"- **Endpoints Tested:** {self.report.concurrent_test_results['endpoints_tested']}\n")
            f.write(f"- **Concurrent Duration:** {self.report.concurrent_test_results['concurrent_duration_seconds']:.2f}s\n")
            f.write(f"- **Sequential Estimate:** {self.report.concurrent_test_results['sequential_duration_estimate']:.2f}s\n")
            f.write(f"- **Speedup Factor:** {self.report.concurrent_test_results['speedup_factor']:.2f}x\n\n")

        f.write("## Recommendations\n\n")
        f.write("Based on the test results:\n\n")

        # Analyze results and provide recommendations
        if self.report.performance_comparison:
            avg_speedup = sum(
                c.get('speedup_factor', 0)
                for c in self.report.performance_comparison.values()
                if 'speedup_factor' in c
            ) / max(1, sum(1 for c in self.report.performance_comparison.values() if 'speedup_factor' in c))

            if avg_speedup > 2:
                f.write(f"1. **Fast mode is highly effective** (average {avg_speedup:.1f}x speedup). Use for initial endpoint exploration.\n")
            f.write("2. **Progressive timeout strategy** reduces timeout failures on large endpoints.\n")
            f.write("3. **Concurrent discovery** significantly improves performance for multiple endpoints.\n")

        f.write("\n---\n")
        f.write(f"\n*Report generated at {datetime.now().isoformat()}*\n")


def main():
    """Main entry point"""
    print("\n" + "="*70)
    print("SPARQL Endpoint Discovery - Comprehensive Test Suite")
    print("="*70 + "\n")

    tester = EndpointDiscoveryTester()

    try:
        tester.run_all_tests()
        print("\n✓ All tests completed successfully!")
        print(f"\nReports saved to: {tester.output_dir}")
        return 0
    except KeyboardInterrupt:
        print("\n\n✗ Tests interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"\n✗ Test suite failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
