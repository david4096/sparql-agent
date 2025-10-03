#!/usr/bin/env python3
"""
Standalone test for connectivity module (doesn't require full package import)
"""

import sys
import importlib.util

# Load the connectivity module directly
spec = importlib.util.spec_from_file_location(
    "connectivity",
    "/Users/david/git/sparql-agent/src/sparql_agent/discovery/connectivity.py"
)
connectivity = importlib.util.module_from_spec(spec)

# Check dependencies
try:
    import httpx
    print("✓ httpx is available")
    HTTPX_OK = True
except ImportError:
    print("✗ httpx is NOT available")
    HTTPX_OK = False

try:
    import requests
    print("✓ requests is available")
    REQUESTS_OK = True
except ImportError:
    print("✗ requests is NOT available")
    REQUESTS_OK = False

if not (HTTPX_OK or REQUESTS_OK):
    print("\nError: At least one of httpx or requests must be installed")
    print("Install with: pip install httpx requests")
    sys.exit(1)

# Load the module
try:
    spec.loader.exec_module(connectivity)
    print("✓ Connectivity module loaded successfully\n")
except Exception as e:
    print(f"✗ Failed to load connectivity module: {e}")
    sys.exit(1)

# Test classes are available
print("Testing module exports...")
assert hasattr(connectivity, 'EndpointPinger'), "EndpointPinger not found"
assert hasattr(connectivity, 'EndpointHealth'), "EndpointHealth not found"
assert hasattr(connectivity, 'EndpointStatus'), "EndpointStatus not found"
assert hasattr(connectivity, 'ConnectionConfig'), "ConnectionConfig not found"
assert hasattr(connectivity, 'ConnectionPool'), "ConnectionPool not found"
assert hasattr(connectivity, 'RateLimiter'), "RateLimiter not found"
print("✓ All classes exported correctly\n")

# Test instantiation
print("Testing class instantiation...")
config = connectivity.ConnectionConfig(timeout=10.0)
print(f"✓ ConnectionConfig created: timeout={config.timeout}s")

pinger = connectivity.EndpointPinger(config=config)
print("✓ EndpointPinger created")

# Test with requests (sync)
if REQUESTS_OK:
    print("\nTesting synchronous ping with requests...")
    endpoint = 'https://rdfportal.org/pdb/sparql'
    print(f"Pinging {endpoint}...")

    try:
        health = pinger.ping_sync(endpoint, check_query=False)
        print(f"✓ Sync ping completed")
        print(f"  Status: {health.status.value}")
        if health.response_time_ms:
            print(f"  Response Time: {health.response_time_ms:.2f}ms")
        if health.status_code:
            print(f"  Status Code: {health.status_code}")
    except Exception as e:
        print(f"✗ Sync ping failed: {e}")

    pinger.close_sync()

# Test with httpx (async)
if HTTPX_OK:
    print("\nTesting asynchronous ping with httpx...")

    import asyncio

    async def test_async_ping():
        async with connectivity.EndpointPinger(config=config) as pinger:
            endpoint = 'https://sparql.uniprot.org/sparql'
            print(f"Pinging {endpoint}...")

            try:
                health = await pinger.ping_async(endpoint, check_query=False)
                print(f"✓ Async ping completed")
                print(f"  Status: {health.status.value}")
                if health.response_time_ms:
                    print(f"  Response Time: {health.response_time_ms:.2f}ms")
                if health.status_code:
                    print(f"  Status Code: {health.status_code}")
            except Exception as e:
                print(f"✗ Async ping failed: {e}")

    asyncio.run(test_async_ping())

print("\n" + "=" * 60)
print("Connectivity module test completed!")
print("=" * 60)
