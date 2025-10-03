"""
Usage examples for SPARQL endpoint connectivity module

Demonstrates both synchronous and asynchronous usage patterns.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

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


def example_1_basic_sync():
    """Example 1: Basic synchronous ping"""
    print("\n=== Example 1: Basic Synchronous Ping ===\n")

    pinger = EndpointPinger()

    for endpoint in TEST_ENDPOINTS:
        print(f"Pinging {endpoint}...")
        health = pinger.ping_sync(endpoint, check_query=True)

        print(f"  Status: {health.status.value}")
        print(f"  Response Time: {health.response_time_ms:.2f}ms" if health.response_time_ms else "  Response Time: N/A")
        print(f"  Status Code: {health.status_code}")
        print(f"  SSL Valid: {health.ssl_valid}")

        if health.ssl_expiry:
            print(f"  SSL Expiry: {health.ssl_expiry}")

        if health.error_message:
            print(f"  Error: {health.error_message}")

        print()

    pinger.close_sync()


async def example_2_basic_async():
    """Example 2: Basic asynchronous ping"""
    print("\n=== Example 2: Basic Asynchronous Ping ===\n")

    async with EndpointPinger() as pinger:
        for endpoint in TEST_ENDPOINTS:
            print(f"Pinging {endpoint}...")
            health = await pinger.ping_async(endpoint, check_query=True)

            print(f"  Status: {health.status.value}")
            print(f"  Response Time: {health.response_time_ms:.2f}ms" if health.response_time_ms else "  Response Time: N/A")
            print(f"  Status Code: {health.status_code}")
            print()


async def example_3_concurrent_pings():
    """Example 3: Concurrent pings to multiple endpoints"""
    print("\n=== Example 3: Concurrent Pings ===\n")

    async with EndpointPinger() as pinger:
        print(f"Pinging {len(TEST_ENDPOINTS)} endpoints concurrently...")

        results = await pinger.ping_multiple_async(TEST_ENDPOINTS)

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


def example_4_custom_config():
    """Example 4: Custom connection configuration"""
    print("\n=== Example 4: Custom Configuration ===\n")

    # Custom configuration with shorter timeout and retries
    config = ConnectionConfig(
        timeout=5.0,
        retry_attempts=2,
        retry_delay=0.5,
        retry_backoff=2.0,
        user_agent="MyApp/1.0 SPARQL-Agent"
    )

    with EndpointPinger(config=config) as pinger:
        endpoint = TEST_ENDPOINTS[0]
        print(f"Pinging {endpoint} with custom config...")

        health = pinger.ping_sync(endpoint)

        print(f"  Status: {health.status.value}")
        print(f"  Response Time: {health.response_time_ms:.2f}ms" if health.response_time_ms else "  Response Time: N/A")
        print()


async def example_5_rate_limiting():
    """Example 5: Rate-limited pings"""
    print("\n=== Example 5: Rate Limiting ===\n")

    # Rate limit: 2 requests per second, burst of 3
    async with EndpointPinger(rate_limit=(2.0, 3)) as pinger:
        print("Pinging with rate limit (2 req/sec)...")

        import time
        start = time.monotonic()

        # This will rate-limit the requests
        results = await pinger.ping_multiple_async(TEST_ENDPOINTS)

        elapsed = time.monotonic() - start

        print(f"\nCompleted {len(results)} pings in {elapsed:.2f} seconds")
        print(f"Average rate: {len(results) / elapsed:.2f} req/sec")


def example_6_health_history():
    """Example 6: Health history tracking"""
    print("\n=== Example 6: Health History Tracking ===\n")

    with EndpointPinger() as pinger:
        endpoint = TEST_ENDPOINTS[0]

        print(f"Performing 5 health checks on {endpoint}...")

        # Perform multiple checks
        for i in range(5):
            health = pinger.ping_sync(endpoint, check_query=False)  # HEAD only
            pinger.record_health(health)
            print(f"  Check {i + 1}: {health.status.value} ({health.response_time_ms:.2f}ms)" if health.response_time_ms else f"  Check {i + 1}: {health.status.value}")

        # Get statistics
        uptime = pinger.get_uptime_percentage(endpoint)
        avg_response = pinger.get_average_response_time(endpoint)

        print(f"\nStatistics:")
        print(f"  Uptime: {uptime:.1f}%")
        print(f"  Avg Response Time: {avg_response:.2f}ms" if avg_response else "  Avg Response Time: N/A")


async def example_7_detailed_info():
    """Example 7: Detailed endpoint information"""
    print("\n=== Example 7: Detailed Endpoint Information ===\n")

    async with EndpointPinger() as pinger:
        endpoint = TEST_ENDPOINTS[0]

        print(f"Getting detailed info for {endpoint}...")

        health = await pinger.ping_async(endpoint, check_query=True)

        print(f"\nStatus: {health.status.value}")
        print(f"Response Time: {health.response_time_ms:.2f}ms" if health.response_time_ms else "Response Time: N/A")
        print(f"Status Code: {health.status_code}")
        print(f"SSL Valid: {health.ssl_valid}")

        if health.ssl_expiry:
            print(f"SSL Expiry: {health.ssl_expiry}")

        if health.server_info:
            print("\nServer Info:")
            for key, value in health.server_info.items():
                print(f"  {key}: {value}")

        if health.capabilities:
            print("\nCapabilities:")
            for cap in health.capabilities:
                print(f"  - {cap}")

        # Convert to dict
        print("\nAs Dictionary:")
        import json
        print(json.dumps(health.to_dict(), indent=2, default=str))


def example_8_authentication():
    """Example 8: Authenticated endpoints"""
    print("\n=== Example 8: Authentication Support ===\n")

    # Configuration with basic auth
    config = ConnectionConfig(
        auth=("username", "password")
    )

    with EndpointPinger(config=config) as pinger:
        # This would work with endpoints requiring auth
        print("Configuration supports authentication:")
        print(f"  Auth configured: {config.auth is not None}")
        print("\nNote: Test endpoints don't require authentication")


def example_9_error_handling():
    """Example 9: Error handling"""
    print("\n=== Example 9: Error Handling ===\n")

    with EndpointPinger() as pinger:
        # Invalid endpoint
        invalid_endpoint = "https://invalid-endpoint-does-not-exist.example.com/sparql"

        print(f"Pinging invalid endpoint: {invalid_endpoint}...")

        health = pinger.ping_sync(invalid_endpoint)

        print(f"  Status: {health.status.value}")
        print(f"  Error: {health.error_message}")
        print()


async def example_10_connection_pooling():
    """Example 10: Connection pooling"""
    print("\n=== Example 10: Connection Pooling ===\n")

    # Create pinger with larger pool
    async with EndpointPinger(pool_size=20) as pinger:
        print("Connection pooling enabled (pool size: 20)")

        # Perform many concurrent requests
        endpoints = TEST_ENDPOINTS * 3  # 9 total requests

        print(f"Performing {len(endpoints)} concurrent requests...")

        import time
        start = time.monotonic()

        results = await pinger.ping_multiple_async(endpoints, check_query=False)

        elapsed = time.monotonic() - start

        successful = sum(1 for r in results if r.status == EndpointStatus.HEALTHY)

        print(f"\nCompleted in {elapsed:.2f} seconds")
        print(f"Successful: {successful}/{len(results)}")
        print(f"Throughput: {len(results) / elapsed:.2f} req/sec")


def main():
    """Run all examples"""
    print("=" * 60)
    print("SPARQL Endpoint Connectivity Examples")
    print("=" * 60)

    # Synchronous examples
    example_1_basic_sync()
    example_4_custom_config()
    example_6_health_history()
    example_8_authentication()
    example_9_error_handling()

    # Asynchronous examples
    asyncio.run(example_2_basic_async())
    asyncio.run(example_3_concurrent_pings())
    asyncio.run(example_5_rate_limiting())
    asyncio.run(example_7_detailed_info())
    asyncio.run(example_10_connection_pooling())

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
