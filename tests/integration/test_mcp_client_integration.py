"""
MCP Client Integration Tests.

Tests the MCP server with actual MCP client connections via stdio transport.
This validates end-to-end functionality and protocol compliance.
"""

import asyncio
import json
import os
import pytest
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# MCP SDK imports
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    pytest.skip("MCP SDK not available", allow_module_level=True)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
async def mcp_client_session():
    """
    Create MCP client session connected to the server via stdio.

    Yields:
        ClientSession connected to MCP server
    """
    # Get path to MCP server
    project_root = Path(__file__).parent.parent.parent
    server_script = project_root / "src" / "sparql_agent" / "mcp" / "server.py"

    if not server_script.exists():
        pytest.skip(f"Server script not found at {server_script}")

    # Create server parameters
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(server_script)],
        env={**os.environ, "PYTHONUNBUFFERED": "1"}
    )

    # Connect to server
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            # Initialize the session
            await session.initialize()

            yield session


@pytest.fixture
async def short_mcp_session():
    """Create short-lived MCP session for quick tests."""
    project_root = Path(__file__).parent.parent.parent
    server_script = project_root / "src" / "sparql_agent" / "mcp" / "server.py"

    if not server_script.exists():
        pytest.skip(f"Server script not found at {server_script}")

    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(server_script)],
        env={**os.environ, "PYTHONUNBUFFERED": "1"}
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            yield session


# ============================================================================
# Connection and Initialization Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
class TestMCPClientConnection:
    """Test MCP client connection and initialization."""

    async def test_client_connection(self, mcp_client_session):
        """Test that client can connect to server."""
        assert mcp_client_session is not None
        # If we got here, connection was successful

    async def test_server_info(self, mcp_client_session):
        """Test retrieving server information."""
        # Server should be initialized and have capabilities
        # The session object contains server capabilities after init
        assert mcp_client_session is not None

    async def test_multiple_connections(self):
        """Test multiple concurrent client connections."""
        project_root = Path(__file__).parent.parent.parent
        server_script = project_root / "src" / "sparql_agent" / "mcp" / "server.py"

        if not server_script.exists():
            pytest.skip(f"Server script not found")

        async def create_session():
            server_params = StdioServerParameters(
                command=sys.executable,
                args=[str(server_script)],
                env={**os.environ, "PYTHONUNBUFFERED": "1"}
            )

            async with stdio_client(server_params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    return True

        # Create multiple sessions concurrently
        results = await asyncio.gather(*[create_session() for _ in range(3)])

        assert all(results)

    @pytest.mark.slow
    async def test_connection_stability(self, mcp_client_session):
        """Test connection remains stable over time."""
        # Keep connection alive for a bit
        await asyncio.sleep(1)

        # Session should still be active
        assert mcp_client_session is not None


# ============================================================================
# Tool Execution Tests via Client
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
class TestMCPClientToolExecution:
    """Test tool execution through MCP client."""

    async def test_list_tools(self, mcp_client_session):
        """Test listing tools via client."""
        tools = await mcp_client_session.list_tools()

        assert tools is not None
        assert len(tools.tools) > 0

        # Check for expected tools
        tool_names = [t.name for t in tools.tools]
        assert "query_sparql" in tool_names
        assert "validate_query" in tool_names
        assert "discover_endpoint" in tool_names

    async def test_call_validate_query_tool(self, mcp_client_session):
        """Test calling validate_query tool via client."""
        result = await mcp_client_session.call_tool(
            "validate_query",
            arguments={
                "query": "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10",
                "strict": False
            }
        )

        assert result is not None
        assert len(result.content) > 0

        # Parse the result
        content = result.content[0]
        data = json.loads(content.text)

        assert "is_valid" in data
        assert data["is_valid"] is True

    async def test_call_format_results_tool(self, mcp_client_session):
        """Test calling format_results tool via client."""
        mock_results = json.dumps({
            "status": "success",
            "bindings": [
                {"s": "http://ex.org/1", "p": "rdf:type", "o": "owl:Class"}
            ],
            "variables": ["s", "p", "o"],
            "row_count": 1
        })

        result = await mcp_client_session.call_tool(
            "format_results",
            arguments={
                "results": mock_results,
                "format": "json",
                "pretty": True
            }
        )

        assert result is not None
        content = json.loads(result.content[0].text)
        assert "format" in content
        assert content["format"] == "json"

    async def test_call_list_ontologies_tool(self, mcp_client_session):
        """Test calling list_ontologies tool via client."""
        result = await mcp_client_session.call_tool(
            "list_ontologies",
            arguments={
                "common_only": True,
                "limit": 10
            }
        )

        assert result is not None
        content = json.loads(result.content[0].text)
        assert "ontologies" in content

    async def test_invalid_tool_call(self, mcp_client_session):
        """Test calling non-existent tool returns error."""
        try:
            result = await mcp_client_session.call_tool(
                "nonexistent_tool",
                arguments={}
            )
            # If it returns a result, it should be an error
            assert result.isError or "error" in json.loads(result.content[0].text)
        except Exception as e:
            # Exception is also acceptable
            assert "unknown" in str(e).lower() or "not found" in str(e).lower()

    async def test_tool_call_with_invalid_arguments(self, mcp_client_session):
        """Test tool call with invalid arguments."""
        result = await mcp_client_session.call_tool(
            "validate_query",
            arguments={}  # Missing required 'query' parameter
        )

        # Should return error
        assert result.isError or "error" in json.loads(result.content[0].text)

    async def test_concurrent_tool_calls(self, mcp_client_session):
        """Test multiple concurrent tool calls."""
        queries = [
            "SELECT ?s WHERE { ?s ?p ?o } LIMIT 10",
            "SELECT ?p WHERE { ?s ?p ?o } LIMIT 20",
            "SELECT ?o WHERE { ?s ?p ?o } LIMIT 30",
        ]

        tasks = [
            mcp_client_session.call_tool(
                "validate_query",
                arguments={"query": q}
            )
            for q in queries
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 3
        for result in results:
            data = json.loads(result.content[0].text)
            assert "is_valid" in data


# ============================================================================
# Resource Access Tests via Client
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
class TestMCPClientResources:
    """Test resource access through MCP client."""

    async def test_list_resources(self, mcp_client_session):
        """Test listing resources via client."""
        resources = await mcp_client_session.list_resources()

        assert resources is not None
        assert len(resources.resources) > 0

        # Check for expected resources
        resource_uris = [r.uri for r in resources.resources]
        assert "sparql://endpoints/common" in resource_uris

    async def test_read_resource(self, mcp_client_session):
        """Test reading a resource via client."""
        result = await mcp_client_session.read_resource(
            "sparql://endpoints/common"
        )

        assert result is not None
        assert len(result.contents) > 0

        # Parse content
        content = result.contents[0]
        endpoints = json.loads(content.text)

        assert "uniprot" in endpoints
        assert "wikidata" in endpoints

    async def test_read_prefixes_resource(self, mcp_client_session):
        """Test reading prefixes resource via client."""
        result = await mcp_client_session.read_resource(
            "sparql://prefixes/standard"
        )

        assert result is not None
        prefixes = json.loads(result.contents[0].text)

        assert "rdf" in prefixes
        assert "rdfs" in prefixes
        assert "owl" in prefixes

    async def test_read_nonexistent_resource(self, mcp_client_session):
        """Test reading non-existent resource."""
        try:
            result = await mcp_client_session.read_resource(
                "sparql://invalid/resource"
            )
            pytest.fail("Should have raised an exception")
        except Exception as e:
            # Should raise an error
            assert "unknown" in str(e).lower() or "not found" in str(e).lower()

    async def test_concurrent_resource_reads(self, mcp_client_session):
        """Test concurrent resource reading."""
        uris = [
            "sparql://endpoints/common",
            "sparql://prefixes/standard",
            "sparql://ontologies/biomedical",
        ]

        tasks = [
            mcp_client_session.read_resource(uri)
            for uri in uris
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 3
        assert all(r is not None for r in results)


# ============================================================================
# Prompt Tests via Client
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
class TestMCPClientPrompts:
    """Test prompt functionality through MCP client."""

    async def test_list_prompts(self, mcp_client_session):
        """Test listing prompts via client."""
        prompts = await mcp_client_session.list_prompts()

        assert prompts is not None
        assert len(prompts.prompts) > 0

        # Check for expected prompts
        prompt_names = [p.name for p in prompts.prompts]
        assert "sparql_query_from_question" in prompt_names

    async def test_get_prompt(self, mcp_client_session):
        """Test getting a prompt via client."""
        result = await mcp_client_session.get_prompt(
            "sparql_query_from_question",
            arguments={
                "question": "Find all entities of type Person",
                "endpoint_info": "Test endpoint"
            }
        )

        assert result is not None
        assert len(result.messages) > 0

        message = result.messages[0]
        assert "question" in str(message)

    async def test_get_explain_prompt(self, mcp_client_session):
        """Test getting explain query prompt."""
        result = await mcp_client_session.get_prompt(
            "explain_query",
            arguments={
                "query": "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10"
            }
        )

        assert result is not None
        assert len(result.messages) > 0

    async def test_get_prompt_invalid_name(self, mcp_client_session):
        """Test getting prompt with invalid name."""
        try:
            result = await mcp_client_session.get_prompt(
                "invalid_prompt",
                arguments={}
            )
            pytest.fail("Should have raised an exception")
        except Exception as e:
            assert "unknown" in str(e).lower() or "not found" in str(e).lower()


# ============================================================================
# End-to-End Workflow Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
class TestMCPClientWorkflows:
    """Test end-to-end workflows through MCP client."""

    async def test_query_validation_workflow(self, mcp_client_session):
        """Test complete query validation workflow."""
        # Step 1: Validate a query
        validate_result = await mcp_client_session.call_tool(
            "validate_query",
            arguments={
                "query": "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10"
            }
        )

        validate_data = json.loads(validate_result.content[0].text)
        assert validate_data["is_valid"] is True

        # Step 2: Format mock results
        mock_results = json.dumps({
            "status": "success",
            "bindings": [{"s": "test", "p": "test", "o": "test"}],
            "variables": ["s", "p", "o"],
            "row_count": 1
        })

        format_result = await mcp_client_session.call_tool(
            "format_results",
            arguments={
                "results": mock_results,
                "format": "json"
            }
        )

        format_data = json.loads(format_result.content[0].text)
        assert "format" in format_data

    async def test_resource_discovery_workflow(self, mcp_client_session):
        """Test resource discovery workflow."""
        # List available resources
        resources = await mcp_client_session.list_resources()
        assert len(resources.resources) > 0

        # Read first resource
        first_resource = resources.resources[0]
        content = await mcp_client_session.read_resource(first_resource.uri)

        assert content is not None
        assert len(content.contents) > 0

    async def test_prompt_based_workflow(self, mcp_client_session):
        """Test prompt-based workflow."""
        # List available prompts
        prompts = await mcp_client_session.list_prompts()
        assert len(prompts.prompts) > 0

        # Get a specific prompt
        result = await mcp_client_session.get_prompt(
            "sparql_query_from_question",
            arguments={"question": "Test query"}
        )

        assert result is not None
        assert len(result.messages) > 0

    async def test_mixed_operations_workflow(self, mcp_client_session):
        """Test workflow mixing tools, resources, and prompts."""
        # 1. List tools
        tools = await mcp_client_session.list_tools()
        assert len(tools.tools) > 0

        # 2. Read a resource
        endpoints = await mcp_client_session.read_resource(
            "sparql://endpoints/common"
        )
        assert endpoints is not None

        # 3. Get a prompt
        prompt = await mcp_client_session.get_prompt(
            "explain_query",
            arguments={"query": "SELECT * WHERE { ?s ?p ?o }"}
        )
        assert prompt is not None

        # 4. Call a tool
        result = await mcp_client_session.call_tool(
            "validate_query",
            arguments={"query": "SELECT * WHERE { ?s ?p ?o }"}
        )
        assert result is not None


# ============================================================================
# Performance Tests via Client
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
class TestMCPClientPerformance:
    """Test MCP client performance characteristics."""

    async def test_tool_call_latency(self, short_mcp_session):
        """Test tool call latency through client."""
        start_time = time.time()

        result = await short_mcp_session.call_tool(
            "validate_query",
            arguments={"query": "SELECT * WHERE { ?s ?p ?o }"}
        )

        latency = time.time() - start_time

        # Should complete in under 500ms including network overhead
        assert latency < 0.5
        assert result is not None

    async def test_resource_read_latency(self, short_mcp_session):
        """Test resource read latency through client."""
        start_time = time.time()

        result = await short_mcp_session.read_resource(
            "sparql://prefixes/standard"
        )

        latency = time.time() - start_time

        # Should complete in under 200ms
        assert latency < 0.2
        assert result is not None

    async def test_sequential_operations_performance(self, mcp_client_session):
        """Test performance of sequential operations."""
        start_time = time.time()

        # Perform multiple sequential operations
        for i in range(10):
            await mcp_client_session.call_tool(
                "validate_query",
                arguments={"query": f"SELECT ?s{i} WHERE {{ ?s ?p ?o }}"}
            )

        total_time = time.time() - start_time
        avg_time = total_time / 10

        # Average time per operation should be reasonable
        assert avg_time < 0.2  # 200ms per operation

    async def test_concurrent_operations_performance(self, mcp_client_session):
        """Test performance of concurrent operations."""
        start_time = time.time()

        # Perform multiple concurrent operations
        tasks = [
            mcp_client_session.call_tool(
                "validate_query",
                arguments={"query": f"SELECT ?s{i} WHERE {{ ?s ?p ?o }}"}
            )
            for i in range(10)
        ]

        results = await asyncio.gather(*tasks)

        total_time = time.time() - start_time

        # Concurrent operations should be faster than sequential
        assert total_time < 2.0  # Should complete in under 2 seconds
        assert len(results) == 10


# ============================================================================
# Error Handling and Recovery Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
class TestMCPClientErrorHandling:
    """Test error handling and recovery through MCP client."""

    async def test_invalid_tool_error(self, mcp_client_session):
        """Test handling of invalid tool calls."""
        try:
            await mcp_client_session.call_tool(
                "nonexistent_tool",
                arguments={}
            )
        except Exception as e:
            # Should raise an error
            assert e is not None

    async def test_invalid_arguments_error(self, mcp_client_session):
        """Test handling of invalid arguments."""
        result = await mcp_client_session.call_tool(
            "validate_query",
            arguments={}  # Missing required parameter
        )

        # Should return error in response
        assert result.isError or "error" in json.loads(result.content[0].text)

    async def test_recovery_after_error(self, mcp_client_session):
        """Test that client can recover after error."""
        # Cause an error
        try:
            await mcp_client_session.call_tool("invalid_tool", arguments={})
        except:
            pass

        # Should still be able to make valid calls
        result = await mcp_client_session.call_tool(
            "validate_query",
            arguments={"query": "SELECT * WHERE { ?s ?p ?o }"}
        )

        assert result is not None
        data = json.loads(result.content[0].text)
        assert "is_valid" in data

    async def test_multiple_errors_handling(self, mcp_client_session):
        """Test handling multiple consecutive errors."""
        # Make multiple invalid calls
        for i in range(5):
            try:
                await mcp_client_session.call_tool(
                    f"invalid_tool_{i}",
                    arguments={}
                )
            except:
                pass  # Expected to fail

        # Should still work after errors
        result = await mcp_client_session.list_tools()
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
