#!/usr/bin/env python3
"""
Test script for discovery timeout improvements.

Tests the new progressive timeout functionality with various endpoints.
"""

import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sparql_agent.discovery.capabilities import CapabilitiesDetector

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_endpoint(endpoint_url, name, fast_mode=False, timeout=30):
    """Test discovery on an endpoint."""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"URL: {endpoint_url}")
    print(f"Fast mode: {fast_mode}, Timeout: {timeout}s")
    print(f"{'='*60}\n")

    try:
        detector = CapabilitiesDetector(
            endpoint_url,
            timeout=timeout,
            fast_mode=fast_mode,
            progressive_timeout=True,
            max_samples=500
        )

        def progress(current, total, message):
            print(f"  [{current}/{total}] {message}")

        capabilities = detector.detect_all_capabilities(progress_callback=progress)

        print(f"\n✓ Discovery completed successfully!")
        print(f"\nResults summary:")
        print(f"  - SPARQL Version: {capabilities.get('sparql_version', 'Unknown')}")
        print(f"  - Named Graphs: {len(capabilities.get('named_graphs', []))}")
        print(f"  - Namespaces: {len(capabilities.get('namespaces', []))}")

        if capabilities.get('features'):
            supported = sum(1 for v in capabilities['features'].values() if v)
            print(f"  - Supported Features: {supported}/{len(capabilities['features'])}")

        if capabilities.get('statistics'):
            stats = capabilities['statistics']
            if stats.get('distinct_predicates'):
                print(f"  - Distinct Predicates: {stats['distinct_predicates']}")
            if stats.get('distinct_classes'):
                print(f"  - Distinct Classes: {stats['distinct_classes']}")

        # Check for issues
        if capabilities.get('_metadata'):
            metadata = capabilities['_metadata']
            if metadata.get('timed_out_queries'):
                print(f"\n⚠ Some queries timed out: {metadata['timed_out_queries']}")
            if metadata.get('failed_queries'):
                print(f"\n⚠ Some queries failed: {metadata['failed_queries']}")

        return True

    except Exception as e:
        print(f"\n✗ Discovery failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run discovery tests on various endpoints."""
    print("SPARQL Discovery Timeout Improvements Test Suite")
    print("="*60)

    # Test endpoints (ordered from small to large)
    endpoints = [
        # Small, fast endpoint (for baseline)
        {
            'url': 'https://dbpedia.org/sparql',
            'name': 'DBpedia (small sample)',
            'fast_mode': True,
            'timeout': 20,
        },
        # Medium endpoint
        {
            'url': 'https://sparql.uniprot.org/sparql',
            'name': 'UniProt',
            'fast_mode': True,
            'timeout': 30,
        },
        # Large endpoint that commonly times out
        {
            'url': 'https://query.wikidata.org/sparql',
            'name': 'Wikidata (large, often times out)',
            'fast_mode': True,  # Use fast mode for Wikidata
            'timeout': 30,
        },
    ]

    results = []
    for endpoint_config in endpoints:
        success = test_endpoint(**endpoint_config)
        results.append((endpoint_config['name'], success))

    # Summary
    print(f"\n\n{'='*60}")
    print("Test Summary")
    print(f"{'='*60}")
    for name, success in results:
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"{status}: {name}")

    passed = sum(1 for _, s in results if s)
    total = len(results)
    print(f"\nTotal: {passed}/{total} passed")

    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
