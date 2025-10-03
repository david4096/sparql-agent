"""
Locust load testing for MCP (Model Context Protocol) server.

Run with: locust -f locust_mcp.py --host=http://localhost:8080
"""

from locust import HttpUser, task, between, events
import random
import json
import time
from typing import Dict, Any, List


class MCPToolUser(HttpUser):
    """
    Simulated user interacting with MCP tools.
    """
    wait_time = between(1, 3)

    def on_start(self):
        """Initialize MCP session."""
        self.session_id = None
        self.initialize_session()

    def initialize_session(self):
        """Initialize MCP session."""
        with self.client.post(
            "/mcp/initialize",
            json={"client_info": {"name": "load-test", "version": "1.0"}},
            catch_response=True,
            name="MCP: Initialize Session"
        ) as response:
            if response.status_code == 200:
                result = response.json()
                self.session_id = result.get("session_id")
                response.success()
            else:
                response.failure("Session initialization failed")

    @task(10)
    def execute_sparql_tool(self):
        """Execute SPARQL query via MCP tool."""
        payload = {
            "tool": "sparql_query",
            "parameters": {
                "query": "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10",
                "endpoint": "http://example.org/sparql"
            },
            "session_id": self.session_id
        }

        with self.client.post(
            "/mcp/tools/execute",
            json=payload,
            catch_response=True,
            name="MCP Tool: SPARQL Query"
        ) as response:
            if response.status_code == 200:
                result = response.json()
                if "result" in result:
                    response.success()
                else:
                    response.failure("No result in response")
            else:
                response.failure(f"Tool execution failed: {response.status_code}")

    @task(5)
    def execute_schema_discovery_tool(self):
        """Execute schema discovery via MCP tool."""
        payload = {
            "tool": "discover_schema",
            "parameters": {
                "endpoint": "http://example.org/sparql",
                "sample_size": 100
            },
            "session_id": self.session_id
        }

        with self.client.post(
            "/mcp/tools/execute",
            json=payload,
            catch_response=True,
            name="MCP Tool: Schema Discovery"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Schema discovery failed: {response.status_code}")

    @task(8)
    def execute_query_generation_tool(self):
        """Execute query generation via MCP tool."""
        questions = [
            "Find all people",
            "List organizations",
            "Show publications from 2023",
            "What genes are related to cancer?"
        ]

        payload = {
            "tool": "generate_query",
            "parameters": {
                "question": random.choice(questions),
                "provider": "anthropic"
            },
            "session_id": self.session_id
        }

        with self.client.post(
            "/mcp/tools/execute",
            json=payload,
            catch_response=True,
            name="MCP Tool: Query Generation"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Query generation failed: {response.status_code}")

    @task(3)
    def execute_ontology_parsing_tool(self):
        """Execute ontology parsing via MCP tool."""
        payload = {
            "tool": "parse_ontology",
            "parameters": {
                "ontology_url": "http://example.org/ontology.owl",
                "format": "owl"
            },
            "session_id": self.session_id
        }

        with self.client.post(
            "/mcp/tools/execute",
            json=payload,
            catch_response=True,
            name="MCP Tool: Ontology Parsing"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Ontology parsing failed: {response.status_code}")

    @task(2)
    def list_available_tools(self):
        """List available MCP tools."""
        with self.client.get(
            "/mcp/tools/list",
            params={"session_id": self.session_id},
            catch_response=True,
            name="MCP: List Tools"
        ) as response:
            if response.status_code == 200:
                result = response.json()
                if "tools" in result:
                    response.success()
                else:
                    response.failure("No tools in response")
            else:
                response.failure("List tools failed")

    def on_stop(self):
        """Cleanup MCP session."""
        if self.session_id:
            with self.client.post(
                "/mcp/terminate",
                json={"session_id": self.session_id},
                catch_response=True,
                name="MCP: Terminate Session"
            ) as response:
                if response.status_code in [200, 204]:
                    response.success()


class MCPResourceUser(HttpUser):
    """
    User accessing MCP resources.
    """
    wait_time = between(2, 4)

    @task(10)
    def read_resource(self):
        """Read MCP resource."""
        resources = [
            "sparql://endpoint/schema",
            "ontology://example/classes",
            "dataset://example/metadata"
        ]

        resource_uri = random.choice(resources)

        with self.client.get(
            "/mcp/resources/read",
            params={"uri": resource_uri},
            catch_response=True,
            name="MCP: Read Resource"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                response.failure("Resource not found")
            else:
                response.failure(f"Read failed: {response.status_code}")

    @task(5)
    def list_resources(self):
        """List available MCP resources."""
        with self.client.get(
            "/mcp/resources/list",
            catch_response=True,
            name="MCP: List Resources"
        ) as response:
            if response.status_code == 200:
                result = response.json()
                if "resources" in result:
                    response.success()
                else:
                    response.failure("No resources in response")
            else:
                response.failure("List resources failed")

    @task(3)
    def subscribe_to_resource(self):
        """Subscribe to resource updates."""
        payload = {
            "uri": "sparql://endpoint/changes",
            "webhook_url": "http://example.org/webhook"
        }

        with self.client.post(
            "/mcp/resources/subscribe",
            json=payload,
            catch_response=True,
            name="MCP: Subscribe to Resource"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure("Subscribe failed")


class MCPPromptUser(HttpUser):
    """
    User working with MCP prompts.
    """
    wait_time = between(1, 3)

    @task(10)
    def get_prompt(self):
        """Get MCP prompt template."""
        prompt_names = [
            "sparql_query_generation",
            "schema_analysis",
            "ontology_mapping",
            "query_refinement"
        ]

        payload = {
            "name": random.choice(prompt_names),
            "arguments": {
                "question": "Find all entities",
                "schema": {"classes": ["Person"]}
            }
        }

        with self.client.post(
            "/mcp/prompts/get",
            json=payload,
            catch_response=True,
            name="MCP: Get Prompt"
        ) as response:
            if response.status_code == 200:
                result = response.json()
                if "messages" in result:
                    response.success()
                else:
                    response.failure("No messages in prompt")
            else:
                response.failure("Get prompt failed")

    @task(5)
    def list_prompts(self):
        """List available MCP prompts."""
        with self.client.get(
            "/mcp/prompts/list",
            catch_response=True,
            name="MCP: List Prompts"
        ) as response:
            if response.status_code == 200:
                result = response.json()
                if "prompts" in result:
                    response.success()
                else:
                    response.failure("No prompts in response")
            else:
                response.failure("List prompts failed")


class MCPBatchUser(HttpUser):
    """
    User executing batch operations via MCP.
    """
    wait_time = between(5, 10)

    @task
    def batch_tool_execution(self):
        """Execute multiple MCP tools in batch."""
        tools = [
            {
                "tool": "sparql_query",
                "parameters": {"query": f"SELECT ?s WHERE {{ ?s ?p ?o }} LIMIT {i*10}"}
            }
            for i in range(1, 6)
        ]

        payload = {
            "tools": tools,
            "parallel": True
        }

        with self.client.post(
            "/mcp/tools/batch",
            json=payload,
            catch_response=True,
            name="MCP: Batch Tool Execution"
        ) as response:
            if response.status_code == 200:
                result = response.json()
                if len(result.get("results", [])) == len(tools):
                    response.success()
                else:
                    response.failure("Incomplete batch results")
            else:
                response.failure(f"Batch execution failed: {response.status_code}")


class MCPWebSocketUser(HttpUser):
    """
    User testing MCP WebSocket connections.
    Note: This is a simplified HTTP-based simulation.
    For true WebSocket testing, use a dedicated WebSocket load testing tool.
    """
    wait_time = between(1, 2)

    @task
    def simulate_websocket_message(self):
        """Simulate WebSocket message via HTTP endpoint."""
        payload = {
            "type": "tool_call",
            "tool": "sparql_query",
            "parameters": {
                "query": "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10"
            }
        }

        with self.client.post(
            "/mcp/ws/message",
            json=payload,
            catch_response=True,
            name="MCP: WebSocket Message"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure("WebSocket message failed")


class MCPStressUser(HttpUser):
    """
    Stress test MCP server with high request rate.
    """
    wait_time = between(0.1, 0.5)

    @task
    def rapid_tool_calls(self):
        """Execute tools rapidly for stress testing."""
        payload = {
            "tool": "sparql_query",
            "parameters": {
                "query": "SELECT ?s WHERE { ?s ?p ?o } LIMIT 10"
            }
        }

        with self.client.post(
            "/mcp/tools/execute",
            json=payload,
            catch_response=True,
            name="MCP: Stress Test"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                response.success()  # Rate limiting expected
            elif response.status_code == 503:
                response.success()  # Service unavailable under stress is acceptable
            else:
                response.failure(f"Unexpected status: {response.status_code}")


class MCPMiddlewareUser(HttpUser):
    """
    Test MCP middleware performance.
    """
    wait_time = between(1, 3)

    @task
    def test_authentication_middleware(self):
        """Test authentication middleware overhead."""
        headers = {
            "Authorization": "Bearer test_token_12345"
        }

        with self.client.get(
            "/mcp/tools/list",
            headers=headers,
            catch_response=True,
            name="MCP: Auth Middleware Test"
        ) as response:
            if response.status_code in [200, 401]:
                response.success()
            else:
                response.failure("Auth middleware test failed")

    @task
    def test_rate_limiting_middleware(self):
        """Test rate limiting middleware."""
        # Make multiple requests to test rate limiting
        for i in range(5):
            with self.client.get(
                "/mcp/tools/list",
                catch_response=True,
                name="MCP: Rate Limit Test"
            ) as response:
                if response.status_code in [200, 429]:
                    response.success()
                else:
                    response.failure("Rate limit test failed")

    @task
    def test_caching_middleware(self):
        """Test caching middleware effectiveness."""
        # Same request should be cached
        params = {"cache_test": "true", "query": "test"}

        with self.client.get(
            "/mcp/tools/list",
            params=params,
            catch_response=True,
            name="MCP: Cache Middleware Test"
        ) as response:
            if response.status_code == 200:
                # Check for cache headers
                cache_status = response.headers.get("X-Cache-Status", "MISS")
                response.success()
            else:
                response.failure("Cache middleware test failed")


# Event handlers
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts."""
    print("Starting MCP server load test...")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops."""
    print("MCP server load test completed.")
    print(f"Total requests: {environment.stats.total.num_requests}")
    print(f"Total failures: {environment.stats.total.num_failures}")
    print(f"Average response time: {environment.stats.total.avg_response_time}ms")
    print(f"RPS: {environment.stats.total.total_rps}")

    # MCP-specific metrics
    tool_requests = sum(
        stat.num_requests
        for name, stat in environment.stats.entries.items()
        if "Tool" in name
    )
    print(f"Total tool executions: {tool_requests}")
