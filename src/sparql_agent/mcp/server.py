"""
Model Context Protocol (MCP) Server for SPARQL Agent.

This module implements a complete MCP server that exposes SPARQL operations,
endpoint discovery, query generation, validation, and ontology lookup capabilities
to AI agents and other MCP clients.

MCP Specification: https://modelcontextprotocol.io/

Features:
- Complete MCP protocol implementation
- SPARQL query execution with multiple endpoints
- Natural language to SPARQL query generation
- Endpoint capability discovery and analysis
- Query validation and optimization
- Result formatting in multiple formats
- Ontology lookup via EBI OLS4
- Resource management for endpoints and schemas
- Prompt templates for query generation

Example:
    Run the MCP server:
    $ sparql-agent-mcp

    Or programmatically:
    >>> from sparql_agent.mcp.server import MCPServer
    >>> server = MCPServer()
    >>> await server.run()
"""

import asyncio
import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

# MCP SDK imports
try:
    from mcp import Server, StdioServerParameters
    from mcp.server import Server as MCPServerBase
    from mcp.server.models import InitializationOptions
    from mcp.types import (
        Tool,
        Resource,
        Prompt,
        TextContent,
        ImageContent,
        EmbeddedResource,
        CallToolResult,
        ListResourcesResult,
        ListPromptsResult,
        ListToolsResult,
        GetPromptResult,
        ReadResourceResult,
    )
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    # Create dummy types for when MCP is not available
    class Server:
        pass
    class StdioServerParameters:
        pass
    class Tool:
        pass
    class Resource:
        pass
    class Prompt:
        pass
    class TextContent:
        pass
    class ImageContent:
        pass
    class EmbeddedResource:
        pass
    class CallToolResult:
        pass
    class ListResourcesResult:
        pass
    class ListPromptsResult:
        pass
    class ListToolsResult:
        pass
    class GetPromptResult:
        pass
    class ReadResourceResult:
        pass

from ..core.types import (
    QueryResult,
    QueryStatus,
    EndpointInfo,
    SchemaInfo,
    OntologyInfo,
    GeneratedQuery,
)
from ..core.exceptions import (
    QueryExecutionError,
    QueryGenerationError,
    QueryValidationError,
    EndpointConnectionError,
)
from ..execution.executor import QueryExecutor, ResultFormat
from ..execution.validator import QueryValidator, validate_query
from ..query.generator import SPARQLGenerator, GenerationStrategy
from ..discovery.capabilities import CapabilitiesDetector, PrefixExtractor
from ..discovery.statistics import DatasetStatistics
from ..formatting.structured import (
    JSONFormatter,
    CSVFormatter,
    format_as_json,
    format_as_csv,
)
from ..formatting.text import TextFormatter
from ..ontology.ols_client import OLSClient, COMMON_ONTOLOGIES, list_common_ontologies
from ..llm.client import LLMClient, ProviderManager
from ..config.settings import SPARQLAgentSettings, get_settings


logger = logging.getLogger(__name__)


class MCPServerCapability(Enum):
    """MCP server capabilities."""
    TOOLS = "tools"
    RESOURCES = "resources"
    PROMPTS = "prompts"
    LOGGING = "logging"


@dataclass
class MCPServerConfig:
    """
    Configuration for MCP server.

    Attributes:
        name: Server name
        version: Server version
        capabilities: Enabled capabilities
        default_timeout: Default query timeout
        max_results_per_query: Maximum results per query
        enable_caching: Enable result caching
        enable_telemetry: Enable telemetry logging
        llm_provider: Default LLM provider
        log_level: Logging level
    """
    name: str = "sparql-agent-mcp"
    version: str = "0.1.0"
    capabilities: List[MCPServerCapability] = field(default_factory=lambda: [
        MCPServerCapability.TOOLS,
        MCPServerCapability.RESOURCES,
        MCPServerCapability.PROMPTS,
    ])
    default_timeout: int = 30
    max_results_per_query: int = 1000
    enable_caching: bool = True
    enable_telemetry: bool = True
    llm_provider: Optional[str] = None
    log_level: str = "INFO"


class MCPServer:
    """
    Model Context Protocol server for SPARQL Agent.

    Provides AI agents with:
    - SPARQL query execution tools
    - Endpoint discovery and analysis
    - Natural language to SPARQL generation
    - Query validation and optimization
    - Result formatting
    - Ontology lookup via EBI OLS4
    - Resource management
    - Prompt templates
    """

    def __init__(
        self,
        config: Optional[MCPServerConfig] = None,
        settings: Optional[SPARQLAgentSettings] = None,
    ):
        """
        Initialize MCP server.

        Args:
            config: Server configuration
            settings: Application settings
        """
        if not MCP_AVAILABLE:
            raise ImportError(
                "MCP SDK not available. Install with: pip install mcp"
            )

        self.config = config or MCPServerConfig()
        self.settings = settings or get_settings()

        # Initialize MCP server
        self.mcp = Server(self.config.name)

        # Initialize components
        self.query_executor = QueryExecutor()
        self.query_validator = QueryValidator()
        self.query_generator: Optional[SPARQLGenerator] = None
        self.ols_client = OLSClient()
        self.prefix_extractor = PrefixExtractor()

        # Initialize LLM client if configured
        self.llm_client: Optional[LLMClient] = None
        self.provider_manager: Optional[ProviderManager] = None
        self._init_llm_clients()

        # Caches
        self.endpoint_cache: Dict[str, EndpointInfo] = {}
        self.schema_cache: Dict[str, SchemaInfo] = {}
        self.ontology_cache: Dict[str, OntologyInfo] = {}

        # Statistics
        self.stats = {
            "queries_executed": 0,
            "queries_generated": 0,
            "endpoints_discovered": 0,
            "ontology_lookups": 0,
            "errors": 0,
            "start_time": datetime.now(),
        }

        # Setup MCP handlers
        self._setup_handlers()

        logger.info(f"MCP Server initialized: {self.config.name} v{self.config.version}")

    def _init_llm_clients(self):
        """Initialize LLM clients for query generation."""
        try:
            # Initialize provider manager if configured
            if self.settings.llm_api_key:
                self.provider_manager = ProviderManager()

                # Add configured providers
                if self.settings.llm_provider == "anthropic" and self.settings.anthropic_api_key:
                    from ..llm.anthropic_provider import AnthropicProvider
                    self.provider_manager.add_provider(
                        "anthropic",
                        AnthropicProvider(api_key=self.settings.anthropic_api_key)
                    )

                if self.settings.openai_api_key:
                    from ..llm.openai_provider import OpenAIProvider
                    self.provider_manager.add_provider(
                        "openai",
                        OpenAIProvider(api_key=self.settings.openai_api_key)
                    )

                # Initialize query generator
                self.query_generator = SPARQLGenerator(
                    provider_manager=self.provider_manager,
                    enable_validation=True,
                    enable_optimization=True,
                )

                logger.info("LLM clients initialized successfully")

        except Exception as e:
            logger.warning(f"Could not initialize LLM clients: {e}")

    def _setup_handlers(self):
        """Setup MCP protocol handlers."""
        # Tool handlers
        if MCPServerCapability.TOOLS in self.config.capabilities:
            self.mcp.list_tools()(self.handle_list_tools)
            self.mcp.call_tool()(self.handle_call_tool)

        # Resource handlers
        if MCPServerCapability.RESOURCES in self.config.capabilities:
            self.mcp.list_resources()(self.handle_list_resources)
            self.mcp.read_resource()(self.handle_read_resource)

        # Prompt handlers
        if MCPServerCapability.PROMPTS in self.config.capabilities:
            self.mcp.list_prompts()(self.handle_list_prompts)
            self.mcp.get_prompt()(self.handle_get_prompt)

        logger.debug("MCP handlers configured")

    # =========================================================================
    # Tool Handlers
    # =========================================================================

    async def handle_list_tools(self) -> ListToolsResult:
        """
        Handle list_tools request.

        Returns list of available tools for SPARQL operations.
        """
        tools = [
            # Core SPARQL execution
            Tool(
                name="query_sparql",
                description=(
                    "Execute a SPARQL query against a specified endpoint. "
                    "Supports SELECT, CONSTRUCT, ASK, and DESCRIBE queries. "
                    "Returns results in JSON format with bindings and metadata."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "SPARQL query to execute"
                        },
                        "endpoint_url": {
                            "type": "string",
                            "description": "SPARQL endpoint URL"
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Query timeout in seconds",
                            "default": self.config.default_timeout
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": self.config.max_results_per_query
                        },
                        "format": {
                            "type": "string",
                            "enum": ["json", "csv", "text"],
                            "description": "Output format",
                            "default": "json"
                        }
                    },
                    "required": ["query", "endpoint_url"]
                }
            ),

            # Endpoint discovery
            Tool(
                name="discover_endpoint",
                description=(
                    "Analyze a SPARQL endpoint to discover its capabilities, "
                    "supported features, available namespaces, schema information, "
                    "and statistics. Returns comprehensive endpoint metadata."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "endpoint_url": {
                            "type": "string",
                            "description": "SPARQL endpoint URL to analyze"
                        },
                        "include_statistics": {
                            "type": "boolean",
                            "description": "Include detailed statistics",
                            "default": True
                        },
                        "include_schema": {
                            "type": "boolean",
                            "description": "Discover schema information",
                            "default": True
                        },
                        "sample_size": {
                            "type": "integer",
                            "description": "Number of triples to sample for analysis",
                            "default": 1000
                        }
                    },
                    "required": ["endpoint_url"]
                }
            ),

            # Query generation
            Tool(
                name="generate_query",
                description=(
                    "Generate a SPARQL query from natural language using LLM. "
                    "Supports context-aware generation with schema and ontology information. "
                    "Returns generated query with explanation and confidence score."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "natural_language": {
                            "type": "string",
                            "description": "Natural language question or description"
                        },
                        "endpoint_url": {
                            "type": "string",
                            "description": "Optional endpoint URL for context"
                        },
                        "schema_context": {
                            "type": "string",
                            "description": "Optional schema information as JSON"
                        },
                        "ontology_context": {
                            "type": "string",
                            "description": "Optional ontology information as JSON"
                        },
                        "strategy": {
                            "type": "string",
                            "enum": ["auto", "template", "llm", "hybrid"],
                            "description": "Generation strategy",
                            "default": "auto"
                        },
                        "include_alternatives": {
                            "type": "boolean",
                            "description": "Include alternative query formulations",
                            "default": False
                        }
                    },
                    "required": ["natural_language"]
                }
            ),

            # Query validation
            Tool(
                name="validate_query",
                description=(
                    "Validate SPARQL query syntax and check for common errors. "
                    "Provides detailed error messages, suggestions, and warnings. "
                    "Checks syntax, prefixes, variables, URIs, and best practices."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "SPARQL query to validate"
                        },
                        "strict": {
                            "type": "boolean",
                            "description": "Enable strict validation mode",
                            "default": False
                        }
                    },
                    "required": ["query"]
                }
            ),

            # Result formatting
            Tool(
                name="format_results",
                description=(
                    "Format SPARQL query results into various output formats. "
                    "Supports JSON, CSV, TSV, and human-readable text formats. "
                    "Handles complex data types and nested structures."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "results": {
                            "type": "string",
                            "description": "Query results as JSON string"
                        },
                        "format": {
                            "type": "string",
                            "enum": ["json", "csv", "tsv", "text", "table"],
                            "description": "Output format",
                            "default": "json"
                        },
                        "pretty": {
                            "type": "boolean",
                            "description": "Pretty print output",
                            "default": True
                        },
                        "include_metadata": {
                            "type": "boolean",
                            "description": "Include query metadata",
                            "default": False
                        }
                    },
                    "required": ["results", "format"]
                }
            ),

            # Ontology lookup (NEW)
            Tool(
                name="lookup_ontology",
                description=(
                    "Search and lookup ontology terms using EBI Ontology Lookup Service (OLS4). "
                    "Search across biomedical ontologies including GO, EFO, MONDO, HP, CHEBI, etc. "
                    "Returns term details with labels, descriptions, and relationships."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (term, label, or description)"
                        },
                        "ontology": {
                            "type": "string",
                            "description": "Filter by specific ontology (e.g., 'go', 'efo', 'mondo')"
                        },
                        "exact": {
                            "type": "boolean",
                            "description": "Require exact match",
                            "default": False
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 10
                        },
                        "include_relationships": {
                            "type": "boolean",
                            "description": "Include parent/child relationships",
                            "default": False
                        }
                    },
                    "required": ["query"]
                }
            ),

            # Get ontology details
            Tool(
                name="get_ontology_term",
                description=(
                    "Get detailed information about a specific ontology term by ID or IRI. "
                    "Returns complete term metadata including labels, definitions, "
                    "synonyms, and hierarchical relationships."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "ontology": {
                            "type": "string",
                            "description": "Ontology ID (e.g., 'go', 'efo')"
                        },
                        "term_id": {
                            "type": "string",
                            "description": "Term ID (e.g., 'GO:0008150', 'EFO_0000001')"
                        },
                        "iri": {
                            "type": "string",
                            "description": "Alternative IRI-based lookup"
                        }
                    },
                    "required": ["ontology"]
                }
            ),

            # List ontologies
            Tool(
                name="list_ontologies",
                description=(
                    "List available ontologies in EBI OLS4. "
                    "Returns metadata about biomedical ontologies including "
                    "titles, descriptions, and term counts."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of ontologies to return",
                            "default": 50
                        },
                        "common_only": {
                            "type": "boolean",
                            "description": "Return only common/well-known ontologies",
                            "default": False
                        }
                    }
                }
            ),
        ]

        return ListToolsResult(tools=tools)

    async def handle_call_tool(self, name: str, arguments: Dict[str, Any]) -> CallToolResult:
        """
        Handle call_tool request.

        Routes tool calls to appropriate handlers.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        try:
            logger.info(f"Tool called: {name}")

            # Route to appropriate handler
            if name == "query_sparql":
                result = await self._handle_query_sparql(**arguments)
            elif name == "discover_endpoint":
                result = await self._handle_discover_endpoint(**arguments)
            elif name == "generate_query":
                result = await self._handle_generate_query(**arguments)
            elif name == "validate_query":
                result = await self._handle_validate_query(**arguments)
            elif name == "format_results":
                result = await self._handle_format_results(**arguments)
            elif name == "lookup_ontology":
                result = await self._handle_lookup_ontology(**arguments)
            elif name == "get_ontology_term":
                result = await self._handle_get_ontology_term(**arguments)
            elif name == "list_ontologies":
                result = await self._handle_list_ontologies(**arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")

            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps(result, indent=2, default=str)
                )],
                isError=False
            )

        except Exception as e:
            logger.error(f"Tool execution failed: {e}", exc_info=True)
            self.stats["errors"] += 1

            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps({
                        "error": str(e),
                        "tool": name,
                        "arguments": arguments
                    }, indent=2)
                )],
                isError=True
            )

    # =========================================================================
    # Tool Implementation Methods
    # =========================================================================

    async def _handle_query_sparql(
        self,
        query: str,
        endpoint_url: str,
        timeout: Optional[int] = None,
        limit: Optional[int] = None,
        format: str = "json",
        **kwargs
    ) -> Dict[str, Any]:
        """Execute SPARQL query."""
        timeout = timeout or self.config.default_timeout

        # Create endpoint info
        endpoint = EndpointInfo(
            url=endpoint_url,
            timeout=timeout
        )

        # Execute query
        result = await asyncio.to_thread(
            self.query_executor.execute,
            query=query,
            endpoint=endpoint,
            timeout=timeout
        )

        self.stats["queries_executed"] += 1

        # Format result
        if format == "csv":
            formatted = format_as_csv(result)
            return {
                "format": "csv",
                "data": formatted,
                "row_count": result.row_count,
                "execution_time": result.execution_time
            }
        elif format == "text":
            text_formatter = TextFormatter()
            formatted = text_formatter.format_result(result)
            return {
                "format": "text",
                "data": formatted,
                "row_count": result.row_count,
                "execution_time": result.execution_time
            }
        else:
            # JSON format (default)
            return {
                "status": result.status.value,
                "bindings": result.bindings,
                "variables": result.variables,
                "row_count": result.row_count,
                "execution_time": result.execution_time,
                "metadata": result.metadata
            }

    async def _handle_discover_endpoint(
        self,
        endpoint_url: str,
        include_statistics: bool = True,
        include_schema: bool = True,
        sample_size: int = 1000,
        **kwargs
    ) -> Dict[str, Any]:
        """Discover endpoint capabilities."""
        # Check cache
        if endpoint_url in self.endpoint_cache:
            endpoint_info = self.endpoint_cache[endpoint_url]
        else:
            endpoint_info = EndpointInfo(url=endpoint_url)
            self.endpoint_cache[endpoint_url] = endpoint_info

        # Discover capabilities
        detector = CapabilitiesDetector(
            endpoint_url=endpoint_url,
            timeout=self.config.default_timeout
        )

        capabilities = await asyncio.to_thread(
            detector.detect_all_capabilities
        )

        result = {
            "endpoint_url": endpoint_url,
            "capabilities": capabilities
        }

        # Add statistics if requested
        if include_statistics:
            stats_collector = EndpointStatistics(
                endpoint_url=endpoint_url,
                timeout=self.config.default_timeout
            )
            stats = await asyncio.to_thread(
                stats_collector.gather_statistics,
                sample_size=sample_size
            )
            result["statistics"] = stats

        self.stats["endpoints_discovered"] += 1

        return result

    async def _handle_generate_query(
        self,
        natural_language: str,
        endpoint_url: Optional[str] = None,
        schema_context: Optional[str] = None,
        ontology_context: Optional[str] = None,
        strategy: str = "auto",
        include_alternatives: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate SPARQL query from natural language."""
        if not self.query_generator:
            raise QueryGenerationError(
                "Query generation not available. LLM client not configured."
            )

        # Parse contexts
        schema_info = None
        if schema_context:
            try:
                schema_data = json.loads(schema_context)
                # Convert to SchemaInfo (simplified)
                schema_info = SchemaInfo(
                    classes=set(schema_data.get("classes", [])),
                    properties=set(schema_data.get("properties", [])),
                    namespaces=schema_data.get("namespaces", {})
                )
            except Exception as e:
                logger.warning(f"Could not parse schema context: {e}")

        ontology_info = None
        if ontology_context:
            try:
                ontology_data = json.loads(ontology_context)
                # Would convert to OntologyInfo here
            except Exception as e:
                logger.warning(f"Could not parse ontology context: {e}")

        # Get endpoint info from cache if available
        endpoint_info = None
        if endpoint_url and endpoint_url in self.endpoint_cache:
            endpoint_info = self.endpoint_cache[endpoint_url]

        # Generate query
        result = await asyncio.to_thread(
            self.query_generator.generate,
            natural_language=natural_language,
            schema_info=schema_info,
            ontology_info=ontology_info,
            endpoint_info=endpoint_info,
            strategy=GenerationStrategy(strategy),
            return_alternatives=include_alternatives
        )

        self.stats["queries_generated"] += 1

        return {
            "query": result.query,
            "natural_language": result.natural_language,
            "explanation": result.explanation,
            "confidence": result.confidence,
            "used_ontology": result.used_ontology,
            "alternatives": result.alternatives,
            "validation_errors": result.validation_errors,
            "metadata": result.metadata
        }

    async def _handle_validate_query(
        self,
        query: str,
        strict: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """Validate SPARQL query."""
        result = await asyncio.to_thread(
            validate_query,
            query=query,
            strict=strict
        )

        return {
            "is_valid": result.is_valid,
            "errors": [str(e) for e in result.errors],
            "warnings": [str(w) for w in result.warning_issues],
            "suggestions": [str(s) for s in result.info_issues],
            "summary": result.get_summary(),
            "report": result.format_report()
        }

    async def _handle_format_results(
        self,
        results: str,
        format: str = "json",
        pretty: bool = True,
        include_metadata: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """Format query results."""
        # Parse results JSON
        try:
            results_data = json.loads(results)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid results JSON: {e}")

        # Create QueryResult object (simplified)
        query_result = QueryResult(
            status=QueryStatus(results_data.get("status", "success")),
            bindings=results_data.get("bindings", []),
            variables=results_data.get("variables", []),
            row_count=results_data.get("row_count", 0),
            execution_time=results_data.get("execution_time"),
            metadata=results_data.get("metadata", {})
        )

        # Format based on requested format
        if format == "json":
            formatter = JSONFormatter(pretty=pretty)
            formatted = formatter.format(query_result)
        elif format == "csv":
            formatter = CSVFormatter()
            formatted = formatter.format(query_result)
        elif format == "tsv":
            formatter = CSVFormatter(delimiter="\t")
            formatted = formatter.format(query_result)
        elif format in ["text", "table"]:
            text_formatter = TextFormatter()
            formatted = text_formatter.format_result(query_result)
        else:
            raise ValueError(f"Unknown format: {format}")

        return {
            "format": format,
            "data": formatted,
            "row_count": query_result.row_count
        }

    async def _handle_lookup_ontology(
        self,
        query: str,
        ontology: Optional[str] = None,
        exact: bool = False,
        limit: int = 10,
        include_relationships: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """Lookup ontology terms via EBI OLS4."""
        # Search for terms
        results = await asyncio.to_thread(
            self.ols_client.search,
            query=query,
            ontology=ontology,
            exact=exact,
            limit=limit
        )

        # Optionally include relationships
        if include_relationships and results:
            for term in results[:3]:  # Limit relationship lookup to first 3 results
                try:
                    if term.get("ontology") and term.get("id"):
                        # Get parent terms
                        parents = await asyncio.to_thread(
                            self.ols_client.get_term_parents,
                            ontology=term["ontology"],
                            term_id=term["id"]
                        )
                        term["parents"] = parents

                        # Get child terms
                        children = await asyncio.to_thread(
                            self.ols_client.get_term_children,
                            ontology=term["ontology"],
                            term_id=term["id"]
                        )
                        term["children"] = children
                except Exception as e:
                    logger.warning(f"Could not fetch relationships for term: {e}")

        self.stats["ontology_lookups"] += 1

        return {
            "query": query,
            "ontology": ontology,
            "count": len(results),
            "results": results
        }

    async def _handle_get_ontology_term(
        self,
        ontology: str,
        term_id: Optional[str] = None,
        iri: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Get detailed ontology term information."""
        if not term_id and not iri:
            raise ValueError("Either term_id or iri must be provided")

        # Get term details
        term = await asyncio.to_thread(
            self.ols_client.get_term,
            ontology=ontology,
            term_id=term_id or "",
            iri=iri
        )

        # Get relationships
        try:
            if term_id:
                # Get parents
                parents = await asyncio.to_thread(
                    self.ols_client.get_term_parents,
                    ontology=ontology,
                    term_id=term_id
                )
                term["parents"] = parents

                # Get children
                children = await asyncio.to_thread(
                    self.ols_client.get_term_children,
                    ontology=ontology,
                    term_id=term_id
                )
                term["children"] = children
        except Exception as e:
            logger.warning(f"Could not fetch relationships: {e}")

        return {
            "ontology": ontology,
            "term": term
        }

    async def _handle_list_ontologies(
        self,
        limit: int = 50,
        common_only: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """List available ontologies."""
        if common_only:
            # Return common ontologies
            ontologies = list_common_ontologies()
        else:
            # List all from OLS4
            ontologies = await asyncio.to_thread(
                self.ols_client.list_ontologies,
                limit=limit
            )

        return {
            "count": len(ontologies),
            "ontologies": ontologies
        }

    # =========================================================================
    # Resource Handlers
    # =========================================================================

    async def handle_list_resources(self) -> ListResourcesResult:
        """
        Handle list_resources request.

        Returns list of available resources for endpoints and schemas.
        """
        resources = [
            Resource(
                uri="sparql://endpoints/common",
                name="Common SPARQL Endpoints",
                description="List of commonly used public SPARQL endpoints",
                mimeType="application/json"
            ),
            Resource(
                uri="sparql://prefixes/standard",
                name="Standard Namespace Prefixes",
                description="Standard RDF/OWL namespace prefix mappings",
                mimeType="application/json"
            ),
            Resource(
                uri="sparql://ontologies/biomedical",
                name="Common Biomedical Ontologies",
                description="List of common biomedical ontologies from OLS4",
                mimeType="application/json"
            ),
            Resource(
                uri="sparql://examples/queries",
                name="Example SPARQL Queries",
                description="Collection of example SPARQL queries",
                mimeType="application/json"
            ),
        ]

        # Add cached endpoints as resources
        for url in self.endpoint_cache.keys():
            resources.append(Resource(
                uri=f"sparql://endpoint/{url}",
                name=f"Endpoint: {url}",
                description=f"Cached information for endpoint {url}",
                mimeType="application/json"
            ))

        return ListResourcesResult(resources=resources)

    async def handle_read_resource(self, uri: str) -> ReadResourceResult:
        """
        Handle read_resource request.

        Args:
            uri: Resource URI

        Returns:
            Resource content
        """
        if uri == "sparql://endpoints/common":
            # Return common endpoints
            endpoints = {
                "uniprot": "https://sparql.uniprot.org/sparql",
                "wikidata": "https://query.wikidata.org/sparql",
                "dbpedia": "https://dbpedia.org/sparql",
                "bio2rdf": "http://bio2rdf.org/sparql",
            }
            content = json.dumps(endpoints, indent=2)

        elif uri == "sparql://prefixes/standard":
            # Return standard prefixes
            content = json.dumps(
                self.prefix_extractor.COMMON_PREFIXES,
                indent=2
            )

        elif uri == "sparql://ontologies/biomedical":
            # Return common biomedical ontologies
            content = json.dumps(COMMON_ONTOLOGIES, indent=2, default=str)

        elif uri == "sparql://examples/queries":
            # Return example queries
            examples = [
                {
                    "name": "List classes",
                    "query": "SELECT DISTINCT ?class WHERE { ?s a ?class } LIMIT 10"
                },
                {
                    "name": "Count instances",
                    "query": "SELECT ?class (COUNT(?instance) AS ?count) WHERE { ?instance a ?class } GROUP BY ?class ORDER BY DESC(?count)"
                },
            ]
            content = json.dumps(examples, indent=2)

        elif uri.startswith("sparql://endpoint/"):
            # Return cached endpoint info
            endpoint_url = uri.replace("sparql://endpoint/", "")
            if endpoint_url in self.endpoint_cache:
                endpoint = self.endpoint_cache[endpoint_url]
                content = json.dumps(asdict(endpoint), indent=2, default=str)
            else:
                raise ValueError(f"Endpoint not in cache: {endpoint_url}")

        else:
            raise ValueError(f"Unknown resource URI: {uri}")

        return ReadResourceResult(
            contents=[TextContent(
                type="text",
                text=content
            )]
        )

    # =========================================================================
    # Prompt Handlers
    # =========================================================================

    async def handle_list_prompts(self) -> ListPromptsResult:
        """
        Handle list_prompts request.

        Returns list of available prompt templates.
        """
        prompts = [
            Prompt(
                name="sparql_query_from_question",
                description="Generate SPARQL query from natural language question",
                arguments=[
                    {
                        "name": "question",
                        "description": "Natural language question",
                        "required": True
                    },
                    {
                        "name": "endpoint_info",
                        "description": "Endpoint context (optional)",
                        "required": False
                    }
                ]
            ),
            Prompt(
                name="explain_query",
                description="Explain what a SPARQL query does in natural language",
                arguments=[
                    {
                        "name": "query",
                        "description": "SPARQL query to explain",
                        "required": True
                    }
                ]
            ),
            Prompt(
                name="optimize_query",
                description="Suggest optimizations for a SPARQL query",
                arguments=[
                    {
                        "name": "query",
                        "description": "SPARQL query to optimize",
                        "required": True
                    }
                ]
            ),
        ]

        return ListPromptsResult(prompts=prompts)

    async def handle_get_prompt(
        self,
        name: str,
        arguments: Optional[Dict[str, str]] = None
    ) -> GetPromptResult:
        """
        Handle get_prompt request.

        Args:
            name: Prompt name
            arguments: Prompt arguments

        Returns:
            Rendered prompt
        """
        arguments = arguments or {}

        if name == "sparql_query_from_question":
            question = arguments.get("question", "")
            endpoint_info = arguments.get("endpoint_info", "")

            prompt = f"""Generate a SPARQL query to answer this question:

Question: {question}

{f'Endpoint Context: {endpoint_info}' if endpoint_info else ''}

Please provide:
1. The SPARQL query
2. A brief explanation of the query logic
3. Any assumptions made

Format the query properly with PREFIX declarations."""

        elif name == "explain_query":
            query = arguments.get("query", "")

            prompt = f"""Explain what this SPARQL query does in plain English:

```sparql
{query}
```

Provide:
1. High-level purpose of the query
2. What data it retrieves
3. Any filters or conditions applied
4. Expected result structure"""

        elif name == "optimize_query":
            query = arguments.get("query", "")

            prompt = f"""Analyze this SPARQL query and suggest optimizations:

```sparql
{query}
```

Consider:
1. Query performance and efficiency
2. Proper use of FILTER placement
3. OPTIONAL clause ordering
4. Use of LIMIT clauses
5. Index-friendly patterns

Provide specific, actionable suggestions."""

        else:
            raise ValueError(f"Unknown prompt: {name}")

        return GetPromptResult(
            messages=[
                {
                    "role": "user",
                    "content": TextContent(
                        type="text",
                        text=prompt
                    )
                }
            ]
        )

    # =========================================================================
    # Server Lifecycle
    # =========================================================================

    async def run(self):
        """Run the MCP server."""
        logger.info(f"Starting MCP server: {self.config.name}")

        # Configure logging
        logging.basicConfig(
            level=getattr(logging, self.config.log_level),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # Run server with stdio transport
        async with self.mcp.stdio_server() as (read_stream, write_stream):
            await self.mcp.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name=self.config.name,
                    server_version=self.config.version,
                )
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get server statistics."""
        uptime = (datetime.now() - self.stats["start_time"]).total_seconds()
        return {
            **self.stats,
            "uptime_seconds": uptime,
            "cached_endpoints": len(self.endpoint_cache),
            "cached_schemas": len(self.schema_cache),
        }


def main():
    """Main entry point for MCP server."""
    if not MCP_AVAILABLE:
        print("Error: MCP SDK not installed. Install with: pip install mcp")
        sys.exit(1)

    # Create and run server
    config = MCPServerConfig()
    server = MCPServer(config=config)

    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
