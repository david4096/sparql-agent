"""
Example usage of MCP handlers and routing.

This example demonstrates:
- Creating a request router
- Handling different types of requests
- Rate limiting
- Error handling
- Response formatting
"""

import asyncio
from sparql_agent.mcp.handlers import (
    RequestRouter,
    RequestType,
    MCPRequest,
    RateLimitConfig,
    create_router,
    handle_request,
)
from sparql_agent.query.generator import SPARQLGenerator
from sparql_agent.llm.client import LLMClient


async def example_query_execution():
    """Example: Execute a SPARQL query."""
    print("\n=== Example 1: Query Execution ===\n")

    router = create_router(enable_rate_limiting=False)

    request_data = {
        "type": "query",
        "params": {
            "query": """
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                SELECT ?s ?label
                WHERE {
                    ?s rdf:type ?type .
                    ?s rdfs:label ?label .
                }
                LIMIT 10
            """,
            "endpoint": "https://sparql.uniprot.org/sparql",
            "timeout": 30
        }
    }

    response = await handle_request(router, request_data)
    print(f"Status: {response['status']}")
    if response['status'] == 'success':
        print(f"Rows returned: {response['data']['row_count']}")
        print(f"Execution time: {response['data']['execution_time']:.2f}s")
    else:
        print(f"Error: {response['error']}")


async def example_endpoint_discovery():
    """Example: Discover endpoint capabilities."""
    print("\n=== Example 2: Endpoint Discovery ===\n")

    router = create_router(enable_rate_limiting=False)

    request_data = {
        "type": "discover",
        "params": {
            "endpoint": "https://sparql.uniprot.org/sparql",
            "discover_schema": True,
            "discover_capabilities": True,
            "timeout": 60
        }
    }

    response = await handle_request(router, request_data)
    print(f"Status: {response['status']}")
    if response['status'] == 'success':
        data = response['data']
        print(f"Endpoint: {data['endpoint']}")
        if 'capabilities' in data:
            caps = data['capabilities']
            print(f"SPARQL Version: {caps.get('sparql_version')}")
            print(f"Named Graphs: {len(caps.get('named_graphs', []))}")
        if 'schema' in data:
            schema = data['schema']
            print(f"Classes found: {len(schema.get('classes', []))}")
            print(f"Properties found: {len(schema.get('properties', []))}")
    else:
        print(f"Error: {response['error']}")


async def example_query_validation():
    """Example: Validate SPARQL query."""
    print("\n=== Example 3: Query Validation ===\n")

    router = create_router(enable_rate_limiting=False)

    # Valid query
    valid_query = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT ?s WHERE { ?s rdf:type ?type }
        LIMIT 10
    """

    request_data = {
        "type": "validate",
        "params": {
            "query": valid_query,
            "strict": False
        }
    }

    response = await handle_request(router, request_data)
    print(f"Valid Query - Status: {response['status']}")
    if response['status'] == 'success':
        data = response['data']
        print(f"  Is Valid: {data['is_valid']}")
        print(f"  Errors: {len(data['errors'])}")
        print(f"  Warnings: {len(data['warnings'])}")

    # Invalid query
    invalid_query = "SELECT * WHERE { ?s ?p ?o"  # Missing closing brace

    request_data["params"]["query"] = invalid_query

    response = await handle_request(router, request_data)
    print(f"\nInvalid Query - Status: {response['status']}")
    if response['status'] == 'success':
        data = response['data']
        print(f"  Is Valid: {data['is_valid']}")
        print(f"  Errors: {data['errors']}")


async def example_query_generation():
    """Example: Generate SPARQL from natural language."""
    print("\n=== Example 4: Query Generation ===\n")

    # Note: This requires an LLM client to be configured
    # For this example, we'll show the structure even if it fails

    router = create_router(enable_rate_limiting=False)

    # Try to register a generator (will work if LLM is configured)
    try:
        from sparql_agent.llm.anthropic_provider import AnthropicProvider
        provider = AnthropicProvider()  # Will fail without API key
        llm_client = LLMClient(provider=provider)
        generator = SPARQLGenerator(llm_client=llm_client)
        router.register_generator(generator)
        print("Generator registered successfully")
    except Exception as e:
        print(f"Generator not available: {e}")
        print("(This is expected without LLM configuration)")
        return

    request_data = {
        "type": "generate",
        "params": {
            "natural_language": "Find all proteins from human",
            "return_alternatives": False
        }
    }

    response = await handle_request(router, request_data)
    print(f"Status: {response['status']}")
    if response['status'] == 'success':
        data = response['data']
        print(f"Generated Query:\n{data['query']}")
        print(f"Confidence: {data['confidence']:.2f}")
        if data.get('explanation'):
            print(f"Explanation: {data['explanation']}")
    else:
        print(f"Error: {response['error']}")


async def example_ontology_operations():
    """Example: Ontology lookup operations."""
    print("\n=== Example 5: Ontology Operations ===\n")

    router = create_router(enable_rate_limiting=False)

    # Search ontologies
    request_data = {
        "type": "ontology",
        "params": {
            "operation": "search",
            "query": "protein",
            "ontology": "go",
            "limit": 5
        }
    }

    response = await handle_request(router, request_data)
    print(f"Search - Status: {response['status']}")
    if response['status'] == 'success':
        data = response['data']
        print(f"Found {data['count']} results")
        for result in data['results'][:3]:
            print(f"  - {result.get('label', 'N/A')}")

    # List ontologies
    request_data = {
        "type": "ontology",
        "params": {
            "operation": "list_ontologies",
            "limit": 10
        }
    }

    response = await handle_request(router, request_data)
    print(f"\nList Ontologies - Status: {response['status']}")
    if response['status'] == 'success':
        data = response['data']
        print(f"Found {data['count']} ontologies")
        for ont in data['ontologies'][:5]:
            print(f"  - {ont.get('id')}: {ont.get('title', 'N/A')}")


async def example_rate_limiting():
    """Example: Rate limiting demonstration."""
    print("\n=== Example 6: Rate Limiting ===\n")

    # Create router with strict rate limits
    rate_config = RateLimitConfig(
        requests_per_minute=5,
        requests_per_hour=20,
        burst_size=3
    )

    router = RequestRouter(rate_limit_config=rate_config)

    # Make multiple requests
    client_id = "test_client"

    request_data = {
        "type": "validate",
        "client_id": client_id,
        "params": {
            "query": "SELECT * WHERE { ?s ?p ?o }",
            "strict": False
        }
    }

    print(f"Making 10 rapid requests with limit of 5/minute...")
    for i in range(10):
        request = MCPRequest.from_dict(request_data)
        request.client_id = client_id
        response = await router.route(request)

        if response.status.value == 'error' and response.error:
            if 'rate limit' in response.error['message'].lower():
                print(f"Request {i+1}: RATE LIMITED")
                break
        else:
            print(f"Request {i+1}: OK")

    # Get rate limit stats
    stats = router.rate_limiter.get_client_stats(client_id)
    print(f"\nRate limit stats for {client_id}:")
    print(f"  Requests last minute: {stats['requests_last_minute']}/{stats['limit_per_minute']}")
    print(f"  Requests last hour: {stats['requests_last_hour']}/{stats['limit_per_hour']}")


async def example_router_statistics():
    """Example: Router statistics and monitoring."""
    print("\n=== Example 7: Router Statistics ===\n")

    router = create_router(enable_rate_limiting=False)

    # Make several requests
    requests = [
        {"type": "validate", "params": {"query": "SELECT * WHERE { ?s ?p ?o }"}},
        {"type": "ontology", "params": {"operation": "list_ontologies"}},
        {"type": "validate", "params": {"query": "INVALID QUERY"}},
    ]

    for req_data in requests:
        await handle_request(router, req_data)

    # Get statistics
    stats = router.get_stats()
    print("Router Statistics:")
    print(f"  Total requests: {stats['total_requests']}")
    print(f"  Successful: {stats['successful_requests']}")
    print(f"  Failed: {stats['failed_requests']}")
    print(f"  Active: {stats['active_requests']}")

    print("\nHandler Statistics:")
    for handler_name, handler_stats in stats['handler_stats'].items():
        print(f"  {handler_name}:")
        print(f"    Total: {handler_stats['total_requests']}")
        print(f"    Success: {handler_stats['successful_requests']}")
        print(f"    Failed: {handler_stats['failed_requests']}")
        print(f"    Avg duration: {handler_stats['average_duration']:.3f}s")

    # Get request history
    history = router.get_request_history(limit=10)
    print(f"\nRecent request history ({len(history)} entries):")
    for entry in history:
        print(f"  {entry['timestamp']}: {entry['type']} - {entry['status']}")


async def example_error_handling():
    """Example: Error handling patterns."""
    print("\n=== Example 8: Error Handling ===\n")

    router = create_router(enable_rate_limiting=False)

    # Missing required parameter
    print("1. Missing required parameter:")
    request_data = {
        "type": "query",
        "params": {
            # Missing 'query' and 'endpoint'
        }
    }
    response = await handle_request(router, request_data)
    print(f"   Status: {response['status']}")
    if response.get('error'):
        print(f"   Error: {response['error']['message']}")

    # Invalid endpoint
    print("\n2. Invalid endpoint:")
    request_data = {
        "type": "query",
        "params": {
            "query": "SELECT * WHERE { ?s ?p ?o }",
            "endpoint": "http://invalid-endpoint-xyz.com/sparql"
        }
    }
    response = await handle_request(router, request_data)
    print(f"   Status: {response['status']}")
    if response.get('error'):
        print(f"   Error type: {response['error']['type']}")
        print(f"   Error message: {response['error']['message']}")

    # Unknown request type
    print("\n3. Unknown request type:")
    request_data = {
        "type": "unknown_operation",
        "params": {}
    }
    try:
        request = MCPRequest.from_dict(request_data)
        response = await router.route(request)
    except ValueError as e:
        print(f"   Error: {e}")


async def main():
    """Run all examples."""
    print("=" * 70)
    print("MCP Handlers and Routing Examples")
    print("=" * 70)

    # Run examples that don't require external services
    await example_query_validation()
    await example_rate_limiting()
    await example_router_statistics()
    await example_error_handling()

    # Examples that require external services (may fail)
    print("\n" + "=" * 70)
    print("Examples requiring external services (may fail without network):")
    print("=" * 70)

    try:
        await example_ontology_operations()
    except Exception as e:
        print(f"Ontology example failed: {e}")

    try:
        await example_endpoint_discovery()
    except Exception as e:
        print(f"Discovery example failed: {e}")

    try:
        await example_query_execution()
    except Exception as e:
        print(f"Query execution example failed: {e}")

    # This will show the structure even if LLM is not configured
    try:
        await example_query_generation()
    except Exception as e:
        print(f"Generation example failed: {e}")

    print("\n" + "=" * 70)
    print("Examples complete!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
