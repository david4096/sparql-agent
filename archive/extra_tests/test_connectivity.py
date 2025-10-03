#!/usr/bin/env python3
"""
Quick test script for SPARQL endpoint connectivity module
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from sparql_agent.discovery.connectivity import (
    EndpointPinger,
    ConnectionConfig,
    EndpointStatus
)


# Test endpoints
TEST_ENDPOINTS = [
    'https://rdfportal.org/pdb/sparql',
    'https://sparql.uniprot.org/sparql',
    'https://www.ebi.ac.uk/rdf/services/sparql'
]


def test_sync():
    """Test synchronous functionality"""
    print("Testing Synchronous Ping...\n")

    config = ConnectionConfig(timeout=15.0, retry_attempts=2)
    pinger = EndpointPinger(config=config)

    for endpoint in TEST_ENDPOINTS:
        print(f"Pinging {endpoint}...")
        health = pinger.ping_sync(endpoint, check_query=False)  # HEAD only for speed

        print(f"  Status: {health.status.value}")
        if health.response_time_ms:
            print(f"  Response Time: {health.response_time_ms:.2f}ms")
        if health.status_code:
            print(f"  Status Code: {health.status_code}")
        if health.error_message:
            print(f"  Error: {health.error_message}")
        print()

    pinger.close_sync()
    return True


async def test_async():
    """Test asynchronous functionality"""
    print("\nTesting Asynchronous Ping...\n")

    config = ConnectionConfig(timeout=15.0, retry_attempts=2)

    async with EndpointPinger(config=config) as pinger:
        # Test concurrent pings
        print(f"Pinging {len(TEST_ENDPOINTS)} endpoints concurrently...")

        results = await pinger.ping_multiple_async(
            TEST_ENDPOINTS,
            check_query=False  # HEAD only for speed
        )

        print("\nResults:")
        for health in results:
            status_icon = "✓" if health.status == EndpointStatus.HEALTHY else "✗"
            print(f"{status_icon} {health.endpoint_url}")
            print(f"  Status: {health.status.value}")
            if health.response_time_ms:
                print(f"  Response Time: {health.response_time_ms:.2f}ms")
            if health.error_message:
                print(f"  Error: {health.error_message}")
            print()

    return True


async def test_with_query():
    """Test with actual SPARQL query"""
    print("\nTesting with SPARQL Query...\n")

    config = ConnectionConfig(timeout=20.0, retry_attempts=2)

    async with EndpointPinger(config=config) as pinger:
        endpoint = TEST_ENDPOINTS[0]
        print(f"Testing {endpoint} with SPARQL query...")

        health = await pinger.ping_async(endpoint, check_query=True)

        print(f"  Status: {health.status.value}")
        if health.response_time_ms:
            print(f"  Response Time: {health.response_time_ms:.2f}ms")
        if health.status_code:
            print(f"  Status Code: {health.status_code}")
        if health.ssl_valid:
            print(f"  SSL: Valid")
            if health.ssl_expiry:
                print(f"  SSL Expiry: {health.ssl_expiry}")

        if health.server_info:
            print(f"  Server Info: {health.server_info}")

        if health.capabilities:
            print(f"  Capabilities: {health.capabilities}")

        print()

    return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("SPARQL Connectivity Module Test")
    print("=" * 60)
    print()

    try:
        # Test sync
        if not test_sync():
            return 1

        # Test async
        if not asyncio.run(test_async()):
            return 1

        # Test with query
        if not asyncio.run(test_with_query()):
            return 1

        print("=" * 60)
        print("All tests completed successfully!")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
