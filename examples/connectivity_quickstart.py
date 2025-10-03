#!/usr/bin/env python3
"""
Quick Start Guide for SPARQL Endpoint Connectivity Module

This file shows the most common usage patterns in a simple, copy-paste format.
"""

# ============================================================================
# QUICK START EXAMPLES
# ============================================================================

# ----------------------------------------------------------------------------
# Example 1: Simple Synchronous Ping
# ----------------------------------------------------------------------------

from sparql_agent.discovery.connectivity import EndpointPinger

pinger = EndpointPinger()
health = pinger.ping_sync('https://sparql.uniprot.org/sparql')

print(f"Status: {health.status.value}")
print(f"Response Time: {health.response_time_ms:.2f}ms")
pinger.close_sync()


# ----------------------------------------------------------------------------
# Example 2: Simple Asynchronous Ping
# ----------------------------------------------------------------------------

import asyncio
from sparql_agent.discovery.connectivity import EndpointPinger

async def check():
    async with EndpointPinger() as pinger:
        health = await pinger.ping_async('https://sparql.uniprot.org/sparql')
        print(f"Status: {health.status.value}")

asyncio.run(check())


# ----------------------------------------------------------------------------
# Example 3: Check Multiple Endpoints Concurrently
# ----------------------------------------------------------------------------

import asyncio
from sparql_agent.discovery.connectivity import EndpointPinger

async def check_multiple():
    endpoints = [
        'https://rdfportal.org/pdb/sparql',
        'https://sparql.uniprot.org/sparql',
        'https://www.ebi.ac.uk/rdf/services/sparql'
    ]

    async with EndpointPinger() as pinger:
        results = await pinger.ping_multiple_async(endpoints)

        for health in results:
            print(f"{health.endpoint_url}: {health.status.value} "
                  f"({health.response_time_ms:.0f}ms)")

asyncio.run(check_multiple())


# ----------------------------------------------------------------------------
# Example 4: Custom Configuration
# ----------------------------------------------------------------------------

from sparql_agent.discovery.connectivity import (
    EndpointPinger,
    ConnectionConfig
)

config = ConnectionConfig(
    timeout=15.0,           # 15 second timeout
    retry_attempts=3,       # Try 3 times
    retry_delay=1.0,       # Wait 1s between retries
    verify_ssl=True,       # Verify SSL certificates
    user_agent="MyApp/1.0"  # Custom user agent
)

with EndpointPinger(config=config) as pinger:
    health = pinger.ping_sync('https://sparql.uniprot.org/sparql')
    print(f"Status: {health.status.value}")


# ----------------------------------------------------------------------------
# Example 5: With Authentication
# ----------------------------------------------------------------------------

from sparql_agent.discovery.connectivity import (
    EndpointPinger,
    ConnectionConfig
)

config = ConnectionConfig(
    auth=("username", "password")
)

with EndpointPinger(config=config) as pinger:
    health = pinger.ping_sync('https://secure-endpoint.com/sparql')
    print(f"Status: {health.status.value}")


# ----------------------------------------------------------------------------
# Example 6: Rate Limited Requests
# ----------------------------------------------------------------------------

import asyncio
from sparql_agent.discovery.connectivity import EndpointPinger

async def rate_limited():
    # Limit to 2 requests/second, burst of 5
    async with EndpointPinger(rate_limit=(2.0, 5)) as pinger:
        endpoints = [
            'https://rdfportal.org/pdb/sparql',
            'https://sparql.uniprot.org/sparql',
            'https://www.ebi.ac.uk/rdf/services/sparql'
        ]

        # Automatically rate-limited
        results = await pinger.ping_multiple_async(endpoints)

asyncio.run(rate_limited())


# ----------------------------------------------------------------------------
# Example 7: Track Health Over Time
# ----------------------------------------------------------------------------

from sparql_agent.discovery.connectivity import EndpointPinger

with EndpointPinger() as pinger:
    endpoint = 'https://sparql.uniprot.org/sparql'

    # Perform 5 health checks
    for i in range(5):
        health = pinger.ping_sync(endpoint, check_query=False)
        pinger.record_health(health)

    # Get statistics
    uptime = pinger.get_uptime_percentage(endpoint)
    avg_time = pinger.get_average_response_time(endpoint)

    print(f"Uptime: {uptime:.1f}%")
    print(f"Avg Response Time: {avg_time:.2f}ms")


# ----------------------------------------------------------------------------
# Example 8: Detailed Health Information
# ----------------------------------------------------------------------------

import asyncio
from sparql_agent.discovery.connectivity import EndpointPinger

async def detailed():
    async with EndpointPinger() as pinger:
        health = await pinger.ping_async(
            'https://www.ebi.ac.uk/rdf/services/sparql',
            check_query=True  # Execute test SPARQL query
        )

        print(f"Status: {health.status.value}")
        print(f"Response: {health.response_time_ms:.2f}ms")
        print(f"Status Code: {health.status_code}")
        print(f"SSL Valid: {health.ssl_valid}")

        if health.server_info:
            print("Server:", health.server_info)

        if health.capabilities:
            print("Capabilities:", health.capabilities)

asyncio.run(detailed())


# ----------------------------------------------------------------------------
# Example 9: Error Handling
# ----------------------------------------------------------------------------

from sparql_agent.discovery.connectivity import (
    EndpointPinger,
    EndpointStatus
)

with EndpointPinger() as pinger:
    health = pinger.ping_sync('https://invalid-endpoint.example.com/sparql')

    if health.status == EndpointStatus.UNREACHABLE:
        print(f"Cannot reach: {health.error_message}")
    elif health.status == EndpointStatus.TIMEOUT:
        print(f"Timeout: {health.error_message}")
    elif health.status == EndpointStatus.SSL_ERROR:
        print(f"SSL error: {health.error_message}")
    elif health.status in [EndpointStatus.HEALTHY, EndpointStatus.DEGRADED]:
        print(f"Endpoint is up!")


# ----------------------------------------------------------------------------
# Example 10: Export Results as JSON
# ----------------------------------------------------------------------------

import asyncio
import json
from sparql_agent.discovery.connectivity import EndpointPinger

async def export_json():
    async with EndpointPinger() as pinger:
        health = await pinger.ping_async('https://sparql.uniprot.org/sparql')

        # Convert to dictionary
        data = health.to_dict()

        # Export as JSON
        print(json.dumps(data, indent=2, default=str))

asyncio.run(export_json())


# ============================================================================
# COMMON PATTERNS
# ============================================================================

"""
Pattern 1: Monitor Multiple Endpoints
--------------------------------------
"""

import asyncio
from sparql_agent.discovery.connectivity import EndpointPinger, EndpointStatus

async def monitor_endpoints(endpoints, interval=60):
    '''Monitor endpoints every 60 seconds'''
    async with EndpointPinger() as pinger:
        while True:
            results = await pinger.ping_multiple_async(endpoints)

            for health in results:
                pinger.record_health(health)

                if health.status != EndpointStatus.HEALTHY:
                    print(f"ALERT: {health.endpoint_url} is {health.status.value}")

            await asyncio.sleep(interval)


"""
Pattern 2: Test Endpoint Before Query
--------------------------------------
"""

from sparql_agent.discovery.connectivity import EndpointPinger, EndpointStatus

def is_endpoint_available(endpoint_url, timeout=5.0):
    '''Quick check if endpoint is available'''
    from sparql_agent.discovery.connectivity import ConnectionConfig

    config = ConnectionConfig(timeout=timeout)
    with EndpointPinger(config=config) as pinger:
        health = pinger.ping_sync(endpoint_url, check_query=False)
        return health.status in [EndpointStatus.HEALTHY, EndpointStatus.DEGRADED]


"""
Pattern 3: Retry Until Healthy
-------------------------------
"""

import asyncio
from sparql_agent.discovery.connectivity import EndpointPinger, EndpointStatus

async def wait_for_endpoint(endpoint_url, max_wait=300):
    '''Wait for endpoint to become healthy (up to 5 minutes)'''
    async with EndpointPinger() as pinger:
        start = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start) < max_wait:
            health = await pinger.ping_async(endpoint_url, check_query=False)

            if health.status == EndpointStatus.HEALTHY:
                return True

            await asyncio.sleep(5)

        return False


"""
Pattern 4: Choose Fastest Endpoint
-----------------------------------
"""

import asyncio
from sparql_agent.discovery.connectivity import EndpointPinger, EndpointStatus

async def choose_fastest_endpoint(endpoints):
    '''Select the fastest responding endpoint'''
    async with EndpointPinger() as pinger:
        results = await pinger.ping_multiple_async(endpoints)

        # Filter healthy endpoints
        healthy = [
            r for r in results
            if r.status == EndpointStatus.HEALTHY and r.response_time_ms
        ]

        if not healthy:
            return None

        # Return fastest
        return min(healthy, key=lambda x: x.response_time_ms)


# ============================================================================
# INTEGRATION EXAMPLES
# ============================================================================

"""
Integration 1: With SPARQLWrapper
----------------------------------
"""

from sparql_agent.discovery.connectivity import EndpointPinger, EndpointStatus

def safe_sparql_query(endpoint_url, query):
    '''Execute SPARQL query only if endpoint is healthy'''
    # Check health first
    with EndpointPinger() as pinger:
        health = pinger.ping_sync(endpoint_url, check_query=False)

        if health.status not in [EndpointStatus.HEALTHY, EndpointStatus.DEGRADED]:
            raise Exception(f"Endpoint unhealthy: {health.status.value}")

    # Execute query
    from SPARQLWrapper import SPARQLWrapper, JSON
    sparql = SPARQLWrapper(endpoint_url)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    return sparql.query().convert()


"""
Integration 2: Load Balancing
------------------------------
"""

import asyncio
from sparql_agent.discovery.connectivity import EndpointPinger

class EndpointLoadBalancer:
    '''Simple load balancer for SPARQL endpoints'''

    def __init__(self, endpoints):
        self.endpoints = endpoints
        self.pinger = EndpointPinger()
        self.current = 0

    async def get_next_healthy_endpoint(self):
        '''Round-robin selection of healthy endpoints'''
        attempts = 0

        while attempts < len(self.endpoints):
            endpoint = self.endpoints[self.current]
            self.current = (self.current + 1) % len(self.endpoints)

            health = await self.pinger.ping_async(endpoint, check_query=False)

            if health.status.value in ['healthy', 'degraded']:
                return endpoint

            attempts += 1

        return None


"""
Integration 3: Endpoint Discovery
----------------------------------
"""

import asyncio
from sparql_agent.discovery.connectivity import EndpointPinger, EndpointStatus

async def discover_endpoints(candidate_urls):
    '''Test multiple URLs to find working SPARQL endpoints'''
    async with EndpointPinger() as pinger:
        results = await pinger.ping_multiple_async(candidate_urls, check_query=True)

        return [
            r.endpoint_url for r in results
            if r.status == EndpointStatus.HEALTHY
        ]


# ============================================================================
# SUMMARY
# ============================================================================

"""
Key Takeaways:
--------------

1. Use EndpointPinger for health checks
2. Both sync and async interfaces available
3. Connection pooling for performance
4. Rate limiting to respect endpoints
5. Comprehensive health information
6. Built-in retry logic
7. SSL/TLS validation
8. Authentication support
9. Health history tracking
10. Easy integration with existing code

Tested Endpoints:
-----------------
- https://rdfportal.org/pdb/sparql
- https://sparql.uniprot.org/sparql
- https://www.ebi.ac.uk/rdf/services/sparql

For more examples, see: examples/connectivity_examples.py
For documentation, see: CONNECTIVITY_README.md
"""
