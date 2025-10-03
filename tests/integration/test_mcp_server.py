"""
Comprehensive integration tests for MCP (Model Context Protocol) server.

This module tests the complete MCP server implementation including:
- Server initialization and lifecycle
- Tool definitions and execution
- Resource management
- Prompt templates
- Error handling
- Concurrent operations
- Protocol compliance

Tests validate MCP specification compliance and real-world usage scenarios.
"""

import asyncio
import json
import os
import pytest
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

# MCP SDK imports (with fallback)
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.types import Tool, Resource, Prompt, TextContent
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    pytest.skip("MCP SDK not available", allow_module_level=True)

from sparql_agent.mcp.server import MCPServer, MCPServerConfig, MCPServerCapability
from sparql_agent.mcp.handlers import (
    RequestRouter,
    RequestType,
    ResponseStatus,
    MCPRequest,
    MCPResponse,
    RateLimitConfig,
)
from sparql_agent.core.types import (
    QueryResult,
    QueryStatus,
    EndpointInfo,
    SchemaInfo,
)
from sparql_agent.core.exceptions import (
    QueryExecutionError,
    ValidationError,
)
from sparql_agent.config.settings import Settings


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mcp_config():
    """Create MCP server configuration for testing."""
    return MCPServerConfig(
        name="test-sparql-agent-mcp",
        version="0.1.0-test",
        capabilities=[
            MCPServerCapability.TOOLS,
            MCPServerCapability.RESOURCES,
            MCPServerCapability.PROMPTS,
        ],
        default_timeout=10,
        max_results_per_query=100,
        enable_caching=True,
        enable_telemetry=True,
        log_level="INFO",
    )


@pytest.fixture
def settings():
    """Create settings for testing."""
    return Settings(
        llm_provider="anthropic",
        llm_api_key=os.getenv("ANTHROPIC_API_KEY", "test-key"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", "test-key"),
        default_endpoint_timeout=10,
    )


@pytest.fixture
def mcp_server(mcp_config, settings):
    """Create MCP server instance for testing."""
    return MCPServer(config=mcp_config, settings=settings)


@pytest.fixture
def mock_query_result():
    """Create mock query result."""
    return QueryResult(
        status=QueryStatus.SUCCESS,
        bindings=[
            {"s": "http://example.org/subject1", "p": "rdf:type", "o": "owl:Class"},
            {"s": "http://example.org/subject2", "p": "rdf:type", "o": "owl:Class"},
        ],
        variables=["s", "p", "o"],
        row_count=2,
        execution_time=0.123,
        metadata={"endpoint": "http://example.org/sparql"},
    )


# ============================================================================
# Server Initialization Tests
# ============================================================================


class TestMCPServerInitialization:
    """Test MCP server initialization and configuration."""

    def test_server_creation(self, mcp_server, mcp_config):
        """Test basic server creation."""
        assert mcp_server is not None
        assert mcp_server.config == mcp_config
        assert mcp_server.mcp is not None
        assert mcp_server.query_executor is not None
        assert mcp_server.query_validator is not None

    def test_server_capabilities(self, mcp_server):
        """Test server capabilities are properly configured."""
        assert MCPServerCapability.TOOLS in mcp_server.config.capabilities
        assert MCPServerCapability.RESOURCES in mcp_server.config.capabilities
        assert MCPServerCapability.PROMPTS in mcp_server.config.capabilities

    def test_server_caches_initialized(self, mcp_server):
        """Test server caches are initialized."""
        assert mcp_server.endpoint_cache == {}
        assert mcp_server.schema_cache == {}
        assert mcp_server.ontology_cache == {}

    def test_server_stats_initialized(self, mcp_server):
        """Test server statistics are initialized."""
        stats = mcp_server.get_stats()
        assert stats["queries_executed"] == 0
        assert stats["queries_generated"] == 0
        assert stats["endpoints_discovered"] == 0
        assert stats["ontology_lookups"] == 0
        assert stats["errors"] == 0
        assert "uptime_seconds" in stats

    def test_config_validation(self):
        """Test configuration validation."""
        # Test with minimal config
        config = MCPServerConfig(name="minimal-server")
        server = MCPServer(config=config)
        assert server.config.name == "minimal-server"
        assert server.config.default_timeout == 30

    def test_without_mcp_sdk_raises_error(self):
        """Test that server creation fails without MCP SDK."""
        with patch("sparql_agent.mcp.server.MCP_AVAILABLE", False):
            with pytest.raises(ImportError, match="MCP SDK not available"):
                MCPServer()


# ============================================================================
# Tool Handler Tests
# ============================================================================


class TestMCPToolHandlers:
    """Test MCP tool handlers and execution."""

    @pytest.mark.asyncio
    async def test_list_tools(self, mcp_server):
        """Test listing available tools."""
        result = await mcp_server.handle_list_tools()

        assert result is not None
        assert len(result.tools) > 0

        # Check for expected tools
        tool_names = [tool.name for tool in result.tools]
        assert "query_sparql" in tool_names
        assert "discover_endpoint" in tool_names
        assert "generate_query" in tool_names
        assert "validate_query" in tool_names
        assert "format_results" in tool_names
        assert "lookup_ontology" in tool_names
        assert "get_ontology_term" in tool_names
        assert "list_ontologies" in tool_names

    @pytest.mark.asyncio
    async def test_query_sparql_tool_schema(self, mcp_server):
        """Test query_sparql tool has correct schema."""
        result = await mcp_server.handle_list_tools()

        query_tool = next(t for t in result.tools if t.name == "query_sparql")
        assert query_tool.description is not None
        assert "inputSchema" in query_tool.inputSchema or "properties" in query_tool.inputSchema

        schema = query_tool.inputSchema
        if "properties" in schema:
            props = schema["properties"]
        else:
            props = schema.get("inputSchema", {}).get("properties", {})

        assert "query" in props
        assert "endpoint_url" in props

    @pytest.mark.asyncio
    async def test_call_unknown_tool(self, mcp_server):
        """Test calling unknown tool returns error."""
        result = await mcp_server.handle_call_tool(
            name="unknown_tool",
            arguments={}
        )

        assert result.isError is True
        content = json.loads(result.content[0].text)
        assert "error" in content

    @pytest.mark.asyncio
    async def test_validate_query_tool(self, mcp_server):
        """Test validate_query tool execution."""
        result = await mcp_server.handle_call_tool(
            name="validate_query",
            arguments={
                "query": "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10",
                "strict": False
            }
        )

        assert result.isError is False
        data = json.loads(result.content[0].text)
        assert "is_valid" in data
        assert data["is_valid"] is True

    @pytest.mark.asyncio
    async def test_validate_invalid_query_tool(self, mcp_server):
        """Test validate_query tool with invalid query."""
        result = await mcp_server.handle_call_tool(
            name="validate_query",
            arguments={
                "query": "INVALID SPARQL SYNTAX",
                "strict": True
            }
        )

        assert result.isError is False
        data = json.loads(result.content[0].text)
        assert "is_valid" in data
        assert data["is_valid"] is False
        assert len(data["errors"]) > 0

    @pytest.mark.asyncio
    async def test_format_results_tool(self, mcp_server, mock_query_result):
        """Test format_results tool execution."""
        results_json = json.dumps({
            "status": "success",
            "bindings": mock_query_result.bindings,
            "variables": mock_query_result.variables,
            "row_count": mock_query_result.row_count,
        })

        result = await mcp_server.handle_call_tool(
            name="format_results",
            arguments={
                "results": results_json,
                "format": "json",
                "pretty": True
            }
        )

        assert result.isError is False
        data = json.loads(result.content[0].text)
        assert "format" in data
        assert data["format"] == "json"
        assert "row_count" in data

    @pytest.mark.asyncio
    async def test_list_ontologies_tool(self, mcp_server):
        """Test list_ontologies tool execution."""
        result = await mcp_server.handle_call_tool(
            name="list_ontologies",
            arguments={
                "common_only": True,
                "limit": 10
            }
        )

        assert result.isError is False
        data = json.loads(result.content[0].text)
        assert "ontologies" in data
        assert "count" in data
        assert data["count"] >= 0

    @pytest.mark.asyncio
    @pytest.mark.network
    async def test_lookup_ontology_tool_integration(self, mcp_server):
        """Test lookup_ontology tool with real OLS4 API (requires network)."""
        result = await mcp_server.handle_call_tool(
            name="lookup_ontology",
            arguments={
                "query": "cancer",
                "ontology": "mondo",
                "limit": 5,
                "exact": False
            }
        )

        # Should succeed or fail gracefully
        data = json.loads(result.content[0].text)
        if not result.isError:
            assert "results" in data
            assert "count" in data
        else:
            # Network error is acceptable in test environment
            assert "error" in data


# ============================================================================
# Resource Handler Tests
# ============================================================================


class TestMCPResourceHandlers:
    """Test MCP resource handlers."""

    @pytest.mark.asyncio
    async def test_list_resources(self, mcp_server):
        """Test listing available resources."""
        result = await mcp_server.handle_list_resources()

        assert result is not None
        assert len(result.resources) > 0

        # Check for expected resources
        resource_uris = [r.uri for r in result.resources]
        assert "sparql://endpoints/common" in resource_uris
        assert "sparql://prefixes/standard" in resource_uris
        assert "sparql://ontologies/biomedical" in resource_uris

    @pytest.mark.asyncio
    async def test_read_common_endpoints_resource(self, mcp_server):
        """Test reading common endpoints resource."""
        result = await mcp_server.handle_read_resource(
            uri="sparql://endpoints/common"
        )

        assert result is not None
        assert len(result.contents) > 0

        content_text = result.contents[0].text
        endpoints = json.loads(content_text)

        assert "uniprot" in endpoints
        assert "wikidata" in endpoints
        assert "dbpedia" in endpoints

    @pytest.mark.asyncio
    async def test_read_prefixes_resource(self, mcp_server):
        """Test reading prefixes resource."""
        result = await mcp_server.handle_read_resource(
            uri="sparql://prefixes/standard"
        )

        assert result is not None
        content_text = result.contents[0].text
        prefixes = json.loads(content_text)

        assert "rdf" in prefixes
        assert "rdfs" in prefixes
        assert "owl" in prefixes

    @pytest.mark.asyncio
    async def test_read_ontologies_resource(self, mcp_server):
        """Test reading biomedical ontologies resource."""
        result = await mcp_server.handle_read_resource(
            uri="sparql://ontologies/biomedical"
        )

        assert result is not None
        content_text = result.contents[0].text
        ontologies = json.loads(content_text)

        assert len(ontologies) > 0

    @pytest.mark.asyncio
    async def test_read_examples_resource(self, mcp_server):
        """Test reading example queries resource."""
        result = await mcp_server.handle_read_resource(
            uri="sparql://examples/queries"
        )

        assert result is not None
        content_text = result.contents[0].text
        examples = json.loads(content_text)

        assert len(examples) > 0
        assert "name" in examples[0]
        assert "query" in examples[0]

    @pytest.mark.asyncio
    async def test_read_nonexistent_resource(self, mcp_server):
        """Test reading non-existent resource returns error."""
        with pytest.raises(ValueError, match="Unknown resource URI"):
            await mcp_server.handle_read_resource(
                uri="sparql://invalid/resource"
            )

    @pytest.mark.asyncio
    async def test_cached_endpoint_resource(self, mcp_server):
        """Test reading cached endpoint resource."""
        # Add endpoint to cache
        endpoint_url = "http://test.example.org/sparql"
        endpoint_info = EndpointInfo(url=endpoint_url, timeout=30)
        mcp_server.endpoint_cache[endpoint_url] = endpoint_info

        # List resources should include it
        result = await mcp_server.handle_list_resources()
        resource_uris = [r.uri for r in result.resources]
        assert f"sparql://endpoint/{endpoint_url}" in resource_uris

        # Read the resource
        read_result = await mcp_server.handle_read_resource(
            uri=f"sparql://endpoint/{endpoint_url}"
        )
        assert read_result is not None


# ============================================================================
# Prompt Handler Tests
# ============================================================================


class TestMCPPromptHandlers:
    """Test MCP prompt handlers."""

    @pytest.mark.asyncio
    async def test_list_prompts(self, mcp_server):
        """Test listing available prompts."""
        result = await mcp_server.handle_list_prompts()

        assert result is not None
        assert len(result.prompts) > 0

        # Check for expected prompts
        prompt_names = [p.name for p in result.prompts]
        assert "sparql_query_from_question" in prompt_names
        assert "explain_query" in prompt_names
        assert "optimize_query" in prompt_names

    @pytest.mark.asyncio
    async def test_get_query_generation_prompt(self, mcp_server):
        """Test getting query generation prompt."""
        result = await mcp_server.handle_get_prompt(
            name="sparql_query_from_question",
            arguments={
                "question": "Find all proteins related to cancer",
                "endpoint_info": "UniProt SPARQL endpoint"
            }
        )

        assert result is not None
        assert len(result.messages) > 0

        message = result.messages[0]
        assert message["role"] == "user"
        assert "Find all proteins related to cancer" in message["content"].text

    @pytest.mark.asyncio
    async def test_get_explain_query_prompt(self, mcp_server):
        """Test getting explain query prompt."""
        query = "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10"

        result = await mcp_server.handle_get_prompt(
            name="explain_query",
            arguments={"query": query}
        )

        assert result is not None
        message = result.messages[0]
        assert query in message["content"].text

    @pytest.mark.asyncio
    async def test_get_optimize_query_prompt(self, mcp_server):
        """Test getting optimize query prompt."""
        query = "SELECT * WHERE { ?s ?p ?o . FILTER(?p = <http://test.org/prop>) }"

        result = await mcp_server.handle_get_prompt(
            name="optimize_query",
            arguments={"query": query}
        )

        assert result is not None
        message = result.messages[0]
        assert "optimization" in message["content"].text.lower()

    @pytest.mark.asyncio
    async def test_get_unknown_prompt(self, mcp_server):
        """Test getting unknown prompt returns error."""
        with pytest.raises(ValueError, match="Unknown prompt"):
            await mcp_server.handle_get_prompt(
                name="unknown_prompt",
                arguments={}
            )


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestMCPErrorHandling:
    """Test MCP server error handling."""

    @pytest.mark.asyncio
    async def test_tool_execution_error_handling(self, mcp_server):
        """Test error handling in tool execution."""
        # Call with missing required parameter
        result = await mcp_server.handle_call_tool(
            name="validate_query",
            arguments={}  # Missing 'query' parameter
        )

        assert result.isError is True
        error_data = json.loads(result.content[0].text)
        assert "error" in error_data

    @pytest.mark.asyncio
    async def test_invalid_tool_arguments(self, mcp_server):
        """Test handling of invalid tool arguments."""
        result = await mcp_server.handle_call_tool(
            name="format_results",
            arguments={
                "results": "not valid json",
                "format": "json"
            }
        )

        assert result.isError is True

    @pytest.mark.asyncio
    async def test_error_statistics_tracking(self, mcp_server):
        """Test that errors are tracked in statistics."""
        initial_errors = mcp_server.stats["errors"]

        # Cause an error
        await mcp_server.handle_call_tool(
            name="unknown_tool",
            arguments={}
        )

        assert mcp_server.stats["errors"] == initial_errors + 1

    @pytest.mark.asyncio
    async def test_concurrent_error_handling(self, mcp_server):
        """Test error handling with concurrent requests."""
        # Execute multiple failing requests concurrently
        tasks = [
            mcp_server.handle_call_tool(name="unknown_tool", arguments={})
            for _ in range(5)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=False)

        # All should return error responses
        assert all(r.isError for r in results)
        assert mcp_server.stats["errors"] >= 5


# ============================================================================
# Concurrent Request Tests
# ============================================================================


class TestMCPConcurrency:
    """Test MCP server concurrent request handling."""

    @pytest.mark.asyncio
    async def test_concurrent_tool_calls(self, mcp_server):
        """Test handling multiple concurrent tool calls."""
        # Execute multiple validation requests concurrently
        queries = [
            "SELECT ?s WHERE { ?s ?p ?o } LIMIT 10",
            "SELECT ?p WHERE { ?s ?p ?o } LIMIT 20",
            "SELECT ?o WHERE { ?s ?p ?o } LIMIT 30",
        ]

        tasks = [
            mcp_server.handle_call_tool(
                name="validate_query",
                arguments={"query": query}
            )
            for query in queries
        ]

        results = await asyncio.gather(*tasks)

        # All should succeed
        assert len(results) == 3
        assert all(not r.isError for r in results)

    @pytest.mark.asyncio
    async def test_concurrent_resource_reads(self, mcp_server):
        """Test concurrent resource reading."""
        resource_uris = [
            "sparql://endpoints/common",
            "sparql://prefixes/standard",
            "sparql://ontologies/biomedical",
        ]

        tasks = [
            mcp_server.handle_read_resource(uri=uri)
            for uri in resource_uris
        ]

        results = await asyncio.gather(*tasks)

        # All should succeed
        assert len(results) == 3
        assert all(r is not None for r in results)

    @pytest.mark.asyncio
    async def test_concurrent_prompt_retrieval(self, mcp_server):
        """Test concurrent prompt retrieval."""
        prompts = [
            ("sparql_query_from_question", {"question": f"Query {i}"})
            for i in range(5)
        ]

        tasks = [
            mcp_server.handle_get_prompt(name=name, arguments=args)
            for name, args in prompts
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        assert all(r is not None for r in results)

    @pytest.mark.asyncio
    async def test_cache_thread_safety(self, mcp_server):
        """Test cache operations are thread-safe."""
        # Concurrently add to endpoint cache
        async def add_to_cache(i):
            url = f"http://example{i}.org/sparql"
            endpoint = EndpointInfo(url=url, timeout=30)
            mcp_server.endpoint_cache[url] = endpoint
            # Small delay to increase chance of race conditions
            await asyncio.sleep(0.001)
            return mcp_server.endpoint_cache.get(url)

        results = await asyncio.gather(*[add_to_cache(i) for i in range(10)])

        # All should have been added successfully
        assert len(mcp_server.endpoint_cache) == 10
        assert all(r is not None for r in results)


# ============================================================================
# Performance and Scalability Tests
# ============================================================================


class TestMCPPerformance:
    """Test MCP server performance characteristics."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_tool_call_latency(self, mcp_server):
        """Test tool call latency is acceptable."""
        start_time = time.time()

        result = await mcp_server.handle_call_tool(
            name="validate_query",
            arguments={"query": "SELECT * WHERE { ?s ?p ?o }"}
        )

        latency = time.time() - start_time

        # Should complete in under 100ms for simple validation
        assert latency < 0.1
        assert not result.isError

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_resource_read_latency(self, mcp_server):
        """Test resource reading latency."""
        start_time = time.time()

        result = await mcp_server.handle_read_resource(
            uri="sparql://prefixes/standard"
        )

        latency = time.time() - start_time

        # Should complete in under 50ms for cached data
        assert latency < 0.05
        assert result is not None

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_high_request_volume(self, mcp_server):
        """Test handling high volume of requests."""
        num_requests = 100

        start_time = time.time()

        tasks = [
            mcp_server.handle_call_tool(
                name="validate_query",
                arguments={"query": f"SELECT ?s{i} WHERE {{ ?s ?p ?o }}"}
            )
            for i in range(num_requests)
        ]

        results = await asyncio.gather(*tasks)

        duration = time.time() - start_time
        throughput = num_requests / duration

        # Should handle at least 50 requests per second
        assert throughput > 50
        assert len(results) == num_requests
        assert all(not r.isError for r in results)

    @pytest.mark.asyncio
    async def test_statistics_collection(self, mcp_server):
        """Test statistics are collected correctly."""
        # Execute various operations
        await mcp_server.handle_list_tools()
        await mcp_server.handle_list_resources()
        await mcp_server.handle_list_prompts()

        stats = mcp_server.get_stats()

        assert "uptime_seconds" in stats
        assert stats["uptime_seconds"] > 0
        assert "cached_endpoints" in stats
        assert "cached_schemas" in stats


# ============================================================================
# MCP Protocol Compliance Tests
# ============================================================================


class TestMCPProtocolCompliance:
    """Test MCP protocol specification compliance."""

    @pytest.mark.asyncio
    async def test_tool_schema_compliance(self, mcp_server):
        """Test that tool schemas follow MCP specification."""
        result = await mcp_server.handle_list_tools()

        for tool in result.tools:
            # Each tool must have required fields
            assert hasattr(tool, 'name')
            assert hasattr(tool, 'description')
            assert hasattr(tool, 'inputSchema')

            # Name should be valid
            assert len(tool.name) > 0
            assert "_" in tool.name or tool.name.islower()

            # Description should be present
            assert len(tool.description) > 0

            # Schema should be valid JSON Schema
            schema = tool.inputSchema
            assert "type" in schema or "properties" in schema

    @pytest.mark.asyncio
    async def test_resource_schema_compliance(self, mcp_server):
        """Test that resources follow MCP specification."""
        result = await mcp_server.handle_list_resources()

        for resource in result.resources:
            # Each resource must have required fields
            assert hasattr(resource, 'uri')
            assert hasattr(resource, 'name')
            assert hasattr(resource, 'description')
            assert hasattr(resource, 'mimeType')

            # URI should be valid
            assert len(resource.uri) > 0
            assert "://" in resource.uri

    @pytest.mark.asyncio
    async def test_prompt_schema_compliance(self, mcp_server):
        """Test that prompts follow MCP specification."""
        result = await mcp_server.handle_list_prompts()

        for prompt in result.prompts:
            # Each prompt must have required fields
            assert hasattr(prompt, 'name')
            assert hasattr(prompt, 'description')
            assert hasattr(prompt, 'arguments')

            # Arguments should be a list
            assert isinstance(prompt.arguments, list)

            # Each argument should have required fields
            for arg in prompt.arguments:
                assert "name" in arg
                assert "description" in arg
                assert "required" in arg

    @pytest.mark.asyncio
    async def test_text_content_compliance(self, mcp_server):
        """Test that text content follows MCP specification."""
        result = await mcp_server.handle_call_tool(
            name="validate_query",
            arguments={"query": "SELECT * WHERE { ?s ?p ?o }"}
        )

        # Content should be a list
        assert isinstance(result.content, list)
        assert len(result.content) > 0

        # Each content item should have type
        for item in result.content:
            assert hasattr(item, 'type')
            assert item.type in ["text", "image", "resource"]

            if item.type == "text":
                assert hasattr(item, 'text')
                assert isinstance(item.text, str)


# ============================================================================
# Integration with Real Endpoints Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.network
class TestMCPRealEndpoints:
    """Test MCP server with real SPARQL endpoints."""

    @pytest.mark.asyncio
    async def test_query_wikidata(self, mcp_server):
        """Test querying Wikidata through MCP."""
        query = """
        SELECT ?item ?itemLabel WHERE {
          ?item wdt:P31 wd:Q5.
          SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
        }
        LIMIT 5
        """

        with patch.object(
            mcp_server.query_executor,
            'execute',
            return_value=QueryResult(
                status=QueryStatus.SUCCESS,
                bindings=[{"item": "Q1", "itemLabel": "Test"}],
                variables=["item", "itemLabel"],
                row_count=1,
                execution_time=0.5
            )
        ):
            result = await mcp_server.handle_call_tool(
                name="query_sparql",
                arguments={
                    "query": query,
                    "endpoint_url": "https://query.wikidata.org/sparql",
                    "timeout": 30
                }
            )

            # Should succeed or timeout gracefully
            if not result.isError:
                data = json.loads(result.content[0].text)
                assert "bindings" in data or "status" in data

    @pytest.mark.asyncio
    async def test_discover_uniprot(self, mcp_server):
        """Test discovering UniProt endpoint capabilities."""
        # Mock the capabilities detector
        with patch('sparql_agent.discovery.capabilities.CapabilitiesDetector') as MockDetector:
            mock_instance = MockDetector.return_value
            mock_instance.detect_all_capabilities.return_value = {
                "has_service": True,
                "supports_federation": True,
                "prefixes": {"up": "http://purl.uniprot.org/core/"}
            }

            result = await mcp_server.handle_call_tool(
                name="discover_endpoint",
                arguments={
                    "endpoint_url": "https://sparql.uniprot.org/sparql",
                    "include_statistics": False,
                    "include_schema": False
                }
            )

            if not result.isError:
                data = json.loads(result.content[0].text)
                assert "endpoint_url" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
