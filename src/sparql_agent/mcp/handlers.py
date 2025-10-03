"""
MCP Request/Response Handlers and Routing.

This module provides comprehensive request handling and routing for the MCP server,
including parameter validation, authentication, rate limiting, and standardized
response formatting.

Features:
- RequestRouter: Routes MCP requests to appropriate handlers
- Handler classes for different operations (query, discovery, generation, etc.)
- Parameter validation and sanitization
- Rate limiting per client
- Standardized response formatting
- Error handling and recovery
- Progress updates and streaming support
- Authentication and authorization
- Request/response logging and metrics
"""

import asyncio
import hashlib
import logging
import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Set, Union
from urllib.parse import urlparse

from ..core.types import (
    EndpointInfo,
    GeneratedQuery,
    OntologyInfo,
    QueryResult,
    QueryStatus,
    SchemaInfo,
)
from ..core.exceptions import (
    SPARQLAgentError,
    QueryError,
    QueryExecutionError,
    QueryGenerationError,
    QueryValidationError,
    EndpointError,
    ValidationError,
    InputValidationError,
    ResourceExhaustedError,
)
from ..execution.executor import QueryExecutor
from ..execution.validator import QueryValidator, validate_query
from ..query.generator import SPARQLGenerator
from ..discovery.capabilities import CapabilitiesDetector
from ..discovery.statistics import EndpointStatistics
from ..formatting.structured import JSONFormatter, CSVFormatter
from ..formatting.text import TextFormatter
from ..ontology.ols_client import OLSClient


logger = logging.getLogger(__name__)


# ============================================================================
# Request/Response Types
# ============================================================================


class RequestType(Enum):
    """Types of MCP requests."""
    QUERY = "query"
    GENERATE = "generate"
    DISCOVER = "discover"
    VALIDATE = "validate"
    FORMAT = "format"
    ONTOLOGY = "ontology"
    HEALTH = "health"


class ResponseStatus(Enum):
    """Response status codes."""
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"
    PENDING = "pending"


@dataclass
class MCPRequest:
    """
    MCP request wrapper.

    Attributes:
        request_id: Unique request identifier
        request_type: Type of request
        params: Request parameters
        client_id: Client identifier for rate limiting
        timestamp: Request timestamp
        metadata: Additional request metadata
    """
    request_id: str
    request_type: RequestType
    params: Dict[str, Any]
    client_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPRequest":
        """Create request from dictionary."""
        return cls(
            request_id=data.get("request_id", cls._generate_id()),
            request_type=RequestType(data.get("type", "query")),
            params=data.get("params", {}),
            client_id=data.get("client_id"),
            metadata=data.get("metadata", {})
        )

    @staticmethod
    def _generate_id() -> str:
        """Generate unique request ID."""
        return hashlib.sha256(
            f"{time.time()}{id(object())}".encode()
        ).hexdigest()[:16]


@dataclass
class MCPResponse:
    """
    MCP response wrapper.

    Attributes:
        request_id: Original request identifier
        status: Response status
        data: Response data
        error: Error information if status is ERROR
        warnings: List of warning messages
        metadata: Response metadata (timing, caching, etc.)
        streaming: Whether response supports streaming
    """
    request_id: str
    status: ResponseStatus
    data: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    streaming: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary."""
        result = {
            "request_id": self.request_id,
            "status": self.status.value,
            "metadata": self.metadata
        }

        if self.data is not None:
            result["data"] = self.data

        if self.error:
            result["error"] = self.error

        if self.warnings:
            result["warnings"] = self.warnings

        if self.streaming:
            result["streaming"] = True

        return result

    @classmethod
    def success(
        cls,
        request_id: str,
        data: Any,
        metadata: Optional[Dict[str, Any]] = None,
        warnings: Optional[List[str]] = None
    ) -> "MCPResponse":
        """Create success response."""
        return cls(
            request_id=request_id,
            status=ResponseStatus.SUCCESS,
            data=data,
            metadata=metadata or {},
            warnings=warnings or []
        )

    @classmethod
    def error(
        cls,
        request_id: str,
        error_type: str,
        error_message: str,
        details: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "MCPResponse":
        """Create error response."""
        return cls(
            request_id=request_id,
            status=ResponseStatus.ERROR,
            error={
                "type": error_type,
                "message": error_message,
                "details": details or {}
            },
            metadata=metadata or {}
        )


@dataclass
class ProgressUpdate:
    """
    Progress update for long-running operations.

    Attributes:
        request_id: Request identifier
        progress: Progress percentage (0-100)
        message: Progress message
        current_step: Current step description
        total_steps: Total number of steps
        timestamp: Update timestamp
    """
    request_id: str
    progress: float
    message: str
    current_step: Optional[str] = None
    total_steps: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "request_id": self.request_id,
            "progress": self.progress,
            "message": self.message,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "timestamp": self.timestamp.isoformat()
        }


# ============================================================================
# Rate Limiting
# ============================================================================


@dataclass
class RateLimitConfig:
    """
    Rate limit configuration.

    Attributes:
        requests_per_minute: Maximum requests per minute
        requests_per_hour: Maximum requests per hour
        burst_size: Maximum burst size
        enable_per_client: Enable per-client rate limiting
    """
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_size: int = 10
    enable_per_client: bool = True


class RateLimiter:
    """
    Token bucket rate limiter with per-client tracking.
    """

    def __init__(self, config: RateLimitConfig):
        """
        Initialize rate limiter.

        Args:
            config: Rate limit configuration
        """
        self.config = config
        self.client_buckets: Dict[str, deque] = defaultdict(deque)
        self.client_hourly: Dict[str, deque] = defaultdict(deque)

    def check_rate_limit(self, client_id: str) -> tuple[bool, Optional[str]]:
        """
        Check if client is within rate limits.

        Args:
            client_id: Client identifier

        Returns:
            Tuple of (allowed, reason_if_denied)
        """
        now = datetime.now()

        # Clean old entries
        self._clean_old_entries(client_id, now)

        # Check per-minute limit
        minute_requests = self.client_buckets[client_id]
        if len(minute_requests) >= self.config.requests_per_minute:
            return False, "Rate limit exceeded: too many requests per minute"

        # Check per-hour limit
        hourly_requests = self.client_hourly[client_id]
        if len(hourly_requests) >= self.config.requests_per_hour:
            return False, "Rate limit exceeded: too many requests per hour"

        # Check burst size
        recent_requests = [
            t for t in minute_requests
            if (now - t).total_seconds() < 1.0
        ]
        if len(recent_requests) >= self.config.burst_size:
            return False, "Rate limit exceeded: burst size exceeded"

        # Record request
        minute_requests.append(now)
        hourly_requests.append(now)

        return True, None

    def _clean_old_entries(self, client_id: str, now: datetime):
        """Remove old timestamp entries."""
        # Clean minute bucket (keep last 60 seconds)
        minute_cutoff = now - timedelta(seconds=60)
        minute_bucket = self.client_buckets[client_id]
        while minute_bucket and minute_bucket[0] < minute_cutoff:
            minute_bucket.popleft()

        # Clean hourly bucket (keep last hour)
        hour_cutoff = now - timedelta(hours=1)
        hourly_bucket = self.client_hourly[client_id]
        while hourly_bucket and hourly_bucket[0] < hour_cutoff:
            hourly_bucket.popleft()

    def get_client_stats(self, client_id: str) -> Dict[str, Any]:
        """Get rate limit statistics for client."""
        now = datetime.now()
        self._clean_old_entries(client_id, now)

        return {
            "client_id": client_id,
            "requests_last_minute": len(self.client_buckets[client_id]),
            "requests_last_hour": len(self.client_hourly[client_id]),
            "limit_per_minute": self.config.requests_per_minute,
            "limit_per_hour": self.config.requests_per_hour,
            "burst_size": self.config.burst_size
        }


# ============================================================================
# Base Handler
# ============================================================================


class BaseHandler(ABC):
    """
    Abstract base class for request handlers.
    """

    def __init__(self, name: str):
        """
        Initialize handler.

        Args:
            name: Handler name
        """
        self.name = name
        self.logger = logging.getLogger(f"{__name__}.{name}")
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_duration": 0.0
        }

    @abstractmethod
    async def handle(self, request: MCPRequest) -> MCPResponse:
        """
        Handle request.

        Args:
            request: MCP request

        Returns:
            MCP response

        Raises:
            SPARQLAgentError: On handling error
        """
        pass

    def validate_params(
        self,
        params: Dict[str, Any],
        required: List[str],
        optional: Optional[List[str]] = None
    ) -> None:
        """
        Validate request parameters.

        Args:
            params: Request parameters
            required: Required parameter names
            optional: Optional parameter names

        Raises:
            InputValidationError: If validation fails
        """
        # Check required parameters
        missing = [p for p in required if p not in params]
        if missing:
            raise InputValidationError(
                f"Missing required parameters: {', '.join(missing)}",
                details={"missing": missing, "handler": self.name}
            )

        # Check for unknown parameters
        if optional:
            allowed = set(required) | set(optional)
            unknown = [p for p in params if p not in allowed]
            if unknown:
                self.logger.warning(
                    f"Unknown parameters in request: {', '.join(unknown)}"
                )

    def update_stats(self, success: bool, duration: float):
        """Update handler statistics."""
        self.stats["total_requests"] += 1
        if success:
            self.stats["successful_requests"] += 1
        else:
            self.stats["failed_requests"] += 1

        # Update average duration
        total = self.stats["total_requests"]
        current_avg = self.stats["average_duration"]
        self.stats["average_duration"] = (
            (current_avg * (total - 1) + duration) / total
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get handler statistics."""
        return dict(self.stats)


# ============================================================================
# Query Handler
# ============================================================================


class QueryHandler(BaseHandler):
    """
    Handler for executing SPARQL queries.
    """

    def __init__(self, executor: Optional[QueryExecutor] = None):
        """
        Initialize query handler.

        Args:
            executor: Query executor instance
        """
        super().__init__("QueryHandler")
        self.executor = executor or QueryExecutor()

    async def handle(self, request: MCPRequest) -> MCPResponse:
        """Execute SPARQL query."""
        start_time = time.time()

        try:
            # Validate parameters
            self.validate_params(
                request.params,
                required=["query", "endpoint"],
                optional=["timeout", "format", "limit"]
            )

            query = request.params["query"]
            endpoint_url = request.params["endpoint"]
            timeout = request.params.get("timeout", 30)
            result_format = request.params.get("format", "json")
            limit = request.params.get("limit")

            # Create endpoint info
            endpoint = EndpointInfo(url=endpoint_url, timeout=timeout)

            # Execute query
            self.logger.info(f"Executing query on {endpoint_url}")
            result = self.executor.execute(
                query=query,
                endpoint=endpoint
            )

            # Format response
            response_data = {
                "status": result.status.value,
                "bindings": result.bindings[:limit] if limit else result.bindings,
                "row_count": result.row_count,
                "variables": result.variables,
                "execution_time": result.execution_time,
                "warnings": result.warnings
            }

            duration = time.time() - start_time
            self.update_stats(success=True, duration=duration)

            return MCPResponse.success(
                request_id=request.request_id,
                data=response_data,
                metadata={
                    "duration": duration,
                    "endpoint": endpoint_url,
                    "format": result_format
                }
            )

        except Exception as e:
            duration = time.time() - start_time
            self.update_stats(success=False, duration=duration)
            self.logger.error(f"Query execution failed: {e}")

            return MCPResponse.error(
                request_id=request.request_id,
                error_type=type(e).__name__,
                error_message=str(e),
                details={"duration": duration},
                metadata={"duration": duration}
            )


# ============================================================================
# Discovery Handler
# ============================================================================


class DiscoveryHandler(BaseHandler):
    """
    Handler for endpoint introspection and discovery.
    """

    def __init__(self):
        """Initialize discovery handler."""
        super().__init__("DiscoveryHandler")

    async def handle(self, request: MCPRequest) -> MCPResponse:
        """Perform endpoint discovery."""
        start_time = time.time()

        try:
            # Validate parameters
            self.validate_params(
                request.params,
                required=["endpoint"],
                optional=["discover_schema", "discover_capabilities", "timeout"]
            )

            endpoint_url = request.params["endpoint"]
            discover_schema = request.params.get("discover_schema", True)
            discover_capabilities = request.params.get("discover_capabilities", True)
            timeout = request.params.get("timeout", 60)

            self.logger.info(f"Discovering endpoint: {endpoint_url}")

            response_data = {
                "endpoint": endpoint_url,
                "discovered_at": datetime.now().isoformat()
            }

            # Discover capabilities
            if discover_capabilities:
                detector = CapabilitiesDetector(endpoint_url, timeout=timeout)
                capabilities = detector.detect_all_capabilities()
                response_data["capabilities"] = capabilities

            # Discover schema
            if discover_schema:
                from ..schema.schema_inference import SchemaInference
                inference = SchemaInference(endpoint_url)
                schema = inference.infer_schema()
                response_data["schema"] = {
                    "classes": list(schema.classes),
                    "properties": list(schema.properties),
                    "namespaces": schema.namespaces,
                    "class_counts": schema.class_counts,
                    "property_counts": schema.property_counts
                }

            duration = time.time() - start_time
            self.update_stats(success=True, duration=duration)

            return MCPResponse.success(
                request_id=request.request_id,
                data=response_data,
                metadata={"duration": duration}
            )

        except Exception as e:
            duration = time.time() - start_time
            self.update_stats(success=False, duration=duration)
            self.logger.error(f"Discovery failed: {e}")

            return MCPResponse.error(
                request_id=request.request_id,
                error_type=type(e).__name__,
                error_message=str(e),
                metadata={"duration": duration}
            )


# ============================================================================
# Generation Handler
# ============================================================================


class GenerationHandler(BaseHandler):
    """
    Handler for natural language to SPARQL conversion.
    """

    def __init__(
        self,
        generator: Optional[SPARQLGenerator] = None
    ):
        """
        Initialize generation handler.

        Args:
            generator: SPARQL generator instance
        """
        super().__init__("GenerationHandler")
        self.generator = generator

    async def handle(self, request: MCPRequest) -> MCPResponse:
        """Generate SPARQL from natural language."""
        start_time = time.time()

        try:
            if not self.generator:
                return MCPResponse.error(
                    request_id=request.request_id,
                    error_type="ConfigurationError",
                    error_message="Generator not configured"
                )

            # Validate parameters
            self.validate_params(
                request.params,
                required=["natural_language"],
                optional=[
                    "endpoint", "schema", "ontology",
                    "strategy", "return_alternatives"
                ]
            )

            natural_language = request.params["natural_language"]
            schema_info = request.params.get("schema")
            ontology_info = request.params.get("ontology")
            strategy = request.params.get("strategy")
            return_alternatives = request.params.get("return_alternatives", False)

            self.logger.info(f"Generating query for: {natural_language}")

            # Generate query
            result = self.generator.generate(
                natural_language=natural_language,
                schema_info=schema_info,
                ontology_info=ontology_info,
                strategy=strategy,
                return_alternatives=return_alternatives
            )

            response_data = {
                "query": result.query,
                "natural_language": result.natural_language,
                "explanation": result.explanation,
                "confidence": result.confidence,
                "used_ontology": result.used_ontology,
                "validation_errors": result.validation_errors,
                "alternatives": result.alternatives if return_alternatives else []
            }

            duration = time.time() - start_time
            self.update_stats(success=True, duration=duration)

            return MCPResponse.success(
                request_id=request.request_id,
                data=response_data,
                metadata={
                    "duration": duration,
                    "strategy": result.metadata.get("strategy"),
                    "confidence": result.confidence
                },
                warnings=result.validation_errors
            )

        except Exception as e:
            duration = time.time() - start_time
            self.update_stats(success=False, duration=duration)
            self.logger.error(f"Query generation failed: {e}")

            return MCPResponse.error(
                request_id=request.request_id,
                error_type=type(e).__name__,
                error_message=str(e),
                metadata={"duration": duration}
            )


# ============================================================================
# Validation Handler
# ============================================================================


class ValidationHandler(BaseHandler):
    """
    Handler for SPARQL query validation.
    """

    def __init__(self):
        """Initialize validation handler."""
        super().__init__("ValidationHandler")
        self.validator = QueryValidator()

    async def handle(self, request: MCPRequest) -> MCPResponse:
        """Validate SPARQL query."""
        start_time = time.time()

        try:
            # Validate parameters
            self.validate_params(
                request.params,
                required=["query"],
                optional=["strict"]
            )

            query = request.params["query"]
            strict = request.params.get("strict", False)

            self.logger.info("Validating SPARQL query")

            # Validate
            result = validate_query(query, strict=strict)

            response_data = {
                "is_valid": result.is_valid,
                "errors": [str(e) for e in result.errors],
                "warnings": [str(w) for w in result.warning_issues],
                "suggestions": [str(s) for s in result.info_issues],
                "summary": result.get_summary()
            }

            duration = time.time() - start_time
            self.update_stats(success=True, duration=duration)

            return MCPResponse.success(
                request_id=request.request_id,
                data=response_data,
                metadata={"duration": duration},
                warnings=[str(w) for w in result.warning_issues]
            )

        except Exception as e:
            duration = time.time() - start_time
            self.update_stats(success=False, duration=duration)
            self.logger.error(f"Validation failed: {e}")

            return MCPResponse.error(
                request_id=request.request_id,
                error_type=type(e).__name__,
                error_message=str(e),
                metadata={"duration": duration}
            )


# ============================================================================
# Formatting Handler
# ============================================================================


class FormattingHandler(BaseHandler):
    """
    Handler for result formatting.
    """

    def __init__(self):
        """Initialize formatting handler."""
        super().__init__("FormattingHandler")
        self.json_formatter = JSONFormatter()
        self.csv_formatter = CSVFormatter()
        self.text_formatter = TextFormatter()

    async def handle(self, request: MCPRequest) -> MCPResponse:
        """Format query results."""
        start_time = time.time()

        try:
            # Validate parameters
            self.validate_params(
                request.params,
                required=["result", "format"],
                optional=["pretty", "include_metadata"]
            )

            result_data = request.params["result"]
            format_type = request.params["format"]
            pretty = request.params.get("pretty", False)
            include_metadata = request.params.get("include_metadata", False)

            self.logger.info(f"Formatting result as {format_type}")

            # Convert to QueryResult if needed
            if isinstance(result_data, dict):
                query_result = QueryResult(
                    status=QueryStatus(result_data.get("status", "success")),
                    bindings=result_data.get("bindings", []),
                    row_count=result_data.get("row_count", 0),
                    variables=result_data.get("variables", [])
                )
            else:
                query_result = result_data

            # Format based on type
            if format_type == "json":
                formatted = self.json_formatter.format(
                    query_result,
                    pretty=pretty,
                    include_metadata=include_metadata
                )
            elif format_type == "csv":
                formatted = self.csv_formatter.format(query_result)
            elif format_type == "text":
                formatted = self.text_formatter.format(query_result)
            else:
                raise InputValidationError(
                    f"Unsupported format: {format_type}",
                    details={"format": format_type}
                )

            response_data = {
                "formatted": formatted,
                "format": format_type
            }

            duration = time.time() - start_time
            self.update_stats(success=True, duration=duration)

            return MCPResponse.success(
                request_id=request.request_id,
                data=response_data,
                metadata={"duration": duration}
            )

        except Exception as e:
            duration = time.time() - start_time
            self.update_stats(success=False, duration=duration)
            self.logger.error(f"Formatting failed: {e}")

            return MCPResponse.error(
                request_id=request.request_id,
                error_type=type(e).__name__,
                error_message=str(e),
                metadata={"duration": duration}
            )


# ============================================================================
# Ontology Handler
# ============================================================================


class OntologyHandler(BaseHandler):
    """
    Handler for EBI OLS4 ontology operations.
    """

    def __init__(self, ols_client: Optional[OLSClient] = None):
        """
        Initialize ontology handler.

        Args:
            ols_client: OLS client instance
        """
        super().__init__("OntologyHandler")
        self.ols = ols_client or OLSClient()

    async def handle(self, request: MCPRequest) -> MCPResponse:
        """Handle ontology operations."""
        start_time = time.time()

        try:
            # Validate parameters
            self.validate_params(
                request.params,
                required=["operation"],
                optional=[
                    "query", "ontology", "term_id",
                    "limit", "exact"
                ]
            )

            operation = request.params["operation"]

            self.logger.info(f"Performing ontology operation: {operation}")

            # Route to appropriate operation
            if operation == "search":
                response_data = await self._handle_search(request.params)
            elif operation == "get_term":
                response_data = await self._handle_get_term(request.params)
            elif operation == "get_ontology":
                response_data = await self._handle_get_ontology(request.params)
            elif operation == "list_ontologies":
                response_data = await self._handle_list_ontologies(request.params)
            elif operation == "get_parents":
                response_data = await self._handle_get_parents(request.params)
            elif operation == "get_children":
                response_data = await self._handle_get_children(request.params)
            else:
                raise InputValidationError(
                    f"Unknown ontology operation: {operation}",
                    details={"operation": operation}
                )

            duration = time.time() - start_time
            self.update_stats(success=True, duration=duration)

            return MCPResponse.success(
                request_id=request.request_id,
                data=response_data,
                metadata={
                    "duration": duration,
                    "operation": operation
                }
            )

        except Exception as e:
            duration = time.time() - start_time
            self.update_stats(success=False, duration=duration)
            self.logger.error(f"Ontology operation failed: {e}")

            return MCPResponse.error(
                request_id=request.request_id,
                error_type=type(e).__name__,
                error_message=str(e),
                metadata={"duration": duration}
            )

    async def _handle_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle ontology search."""
        query = params["query"]
        ontology = params.get("ontology")
        limit = params.get("limit", 10)
        exact = params.get("exact", False)

        results = self.ols.search(
            query=query,
            ontology=ontology,
            limit=limit,
            exact=exact
        )

        return {
            "operation": "search",
            "query": query,
            "results": results,
            "count": len(results)
        }

    async def _handle_get_term(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get term details."""
        if "ontology" not in params or "term_id" not in params:
            raise InputValidationError(
                "get_term requires 'ontology' and 'term_id' parameters"
            )

        term = self.ols.get_term(
            ontology=params["ontology"],
            term_id=params["term_id"]
        )

        return {
            "operation": "get_term",
            "term": term
        }

    async def _handle_get_ontology(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get ontology info."""
        if "ontology" not in params:
            raise InputValidationError(
                "get_ontology requires 'ontology' parameter"
            )

        ontology = self.ols.get_ontology(params["ontology"])

        return {
            "operation": "get_ontology",
            "ontology": ontology
        }

    async def _handle_list_ontologies(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle list ontologies."""
        limit = params.get("limit", 100)
        ontologies = self.ols.list_ontologies(limit=limit)

        return {
            "operation": "list_ontologies",
            "ontologies": ontologies,
            "count": len(ontologies)
        }

    async def _handle_get_parents(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get parent terms."""
        if "ontology" not in params or "term_id" not in params:
            raise InputValidationError(
                "get_parents requires 'ontology' and 'term_id' parameters"
            )

        parents = self.ols.get_term_parents(
            ontology=params["ontology"],
            term_id=params["term_id"]
        )

        return {
            "operation": "get_parents",
            "parents": parents,
            "count": len(parents)
        }

    async def _handle_get_children(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get child terms."""
        if "ontology" not in params or "term_id" not in params:
            raise InputValidationError(
                "get_children requires 'ontology' and 'term_id' parameters"
            )

        children = self.ols.get_term_children(
            ontology=params["ontology"],
            term_id=params["term_id"]
        )

        return {
            "operation": "get_children",
            "children": children,
            "count": len(children)
        }


# ============================================================================
# Request Router
# ============================================================================


class RequestRouter:
    """
    Routes MCP requests to appropriate handlers with validation,
    authentication, and rate limiting.
    """

    def __init__(
        self,
        rate_limit_config: Optional[RateLimitConfig] = None,
        enable_auth: bool = False,
        auth_validator: Optional[Callable[[str], bool]] = None
    ):
        """
        Initialize request router.

        Args:
            rate_limit_config: Rate limiting configuration
            enable_auth: Enable authentication
            auth_validator: Function to validate auth tokens
        """
        self.logger = logging.getLogger(f"{__name__}.RequestRouter")

        # Rate limiting
        self.rate_limiter = RateLimiter(
            rate_limit_config or RateLimitConfig()
        )

        # Authentication
        self.enable_auth = enable_auth
        self.auth_validator = auth_validator

        # Initialize handlers
        self.handlers: Dict[RequestType, BaseHandler] = {}
        self._init_handlers()

        # Request tracking
        self.active_requests: Dict[str, MCPRequest] = {}
        self.request_history: deque = deque(maxlen=1000)

        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "rate_limited_requests": 0,
            "auth_failed_requests": 0
        }

    def _init_handlers(self):
        """Initialize default handlers."""
        self.handlers[RequestType.QUERY] = QueryHandler()
        self.handlers[RequestType.DISCOVER] = DiscoveryHandler()
        self.handlers[RequestType.VALIDATE] = ValidationHandler()
        self.handlers[RequestType.FORMAT] = FormattingHandler()
        self.handlers[RequestType.ONTOLOGY] = OntologyHandler()

    def register_handler(
        self,
        request_type: RequestType,
        handler: BaseHandler
    ):
        """
        Register a custom handler.

        Args:
            request_type: Type of request to handle
            handler: Handler instance
        """
        self.handlers[request_type] = handler
        self.logger.info(f"Registered handler for {request_type.value}")

    def register_generator(self, generator: SPARQLGenerator):
        """Register a SPARQL generator for the generation handler."""
        self.handlers[RequestType.GENERATE] = GenerationHandler(generator)
        self.logger.info("Registered SPARQL generator")

    async def route(self, request: MCPRequest) -> MCPResponse:
        """
        Route request to appropriate handler.

        Args:
            request: MCP request

        Returns:
            MCP response
        """
        self.stats["total_requests"] += 1
        self.active_requests[request.request_id] = request

        try:
            # Authentication check
            if self.enable_auth:
                if not self._check_auth(request):
                    self.stats["auth_failed_requests"] += 1
                    return MCPResponse.error(
                        request_id=request.request_id,
                        error_type="AuthenticationError",
                        error_message="Authentication failed"
                    )

            # Rate limiting check
            client_id = request.client_id or "default"
            allowed, reason = self.rate_limiter.check_rate_limit(client_id)
            if not allowed:
                self.stats["rate_limited_requests"] += 1
                return MCPResponse.error(
                    request_id=request.request_id,
                    error_type="RateLimitError",
                    error_message=reason or "Rate limit exceeded",
                    details=self.rate_limiter.get_client_stats(client_id)
                )

            # Get handler
            handler = self.handlers.get(request.request_type)
            if not handler:
                return MCPResponse.error(
                    request_id=request.request_id,
                    error_type="InvalidRequestError",
                    error_message=f"No handler for request type: {request.request_type.value}"
                )

            # Handle request
            response = await handler.handle(request)

            # Update statistics
            if response.status == ResponseStatus.SUCCESS:
                self.stats["successful_requests"] += 1
            else:
                self.stats["failed_requests"] += 1

            # Record in history
            self.request_history.append({
                "request_id": request.request_id,
                "type": request.request_type.value,
                "status": response.status.value,
                "timestamp": request.timestamp.isoformat()
            })

            return response

        except Exception as e:
            self.stats["failed_requests"] += 1
            self.logger.error(f"Request routing failed: {e}", exc_info=True)

            return MCPResponse.error(
                request_id=request.request_id,
                error_type="InternalError",
                error_message=str(e)
            )

        finally:
            # Clean up
            self.active_requests.pop(request.request_id, None)

    def _check_auth(self, request: MCPRequest) -> bool:
        """
        Check request authentication.

        Args:
            request: MCP request

        Returns:
            True if authenticated
        """
        if not self.auth_validator:
            return True

        auth_token = request.metadata.get("auth_token")
        if not auth_token:
            return False

        return self.auth_validator(auth_token)

    def get_stats(self) -> Dict[str, Any]:
        """Get router statistics."""
        stats = dict(self.stats)
        stats["active_requests"] = len(self.active_requests)
        stats["handler_stats"] = {
            req_type.value: handler.get_stats()
            for req_type, handler in self.handlers.items()
        }
        return stats

    def get_request_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent request history."""
        return list(self.request_history)[-limit:]


# ============================================================================
# Utility Functions
# ============================================================================


def create_router(
    enable_rate_limiting: bool = True,
    enable_auth: bool = False,
    generator: Optional[SPARQLGenerator] = None
) -> RequestRouter:
    """
    Create a request router with default configuration.

    Args:
        enable_rate_limiting: Enable rate limiting
        enable_auth: Enable authentication
        generator: Optional SPARQL generator

    Returns:
        Configured RequestRouter
    """
    rate_config = RateLimitConfig() if enable_rate_limiting else None
    router = RequestRouter(
        rate_limit_config=rate_config,
        enable_auth=enable_auth
    )

    if generator:
        router.register_generator(generator)

    return router


async def handle_request(
    router: RequestRouter,
    request_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Convenience function to handle a request.

    Args:
        router: Request router
        request_data: Request data dictionary

    Returns:
        Response dictionary
    """
    request = MCPRequest.from_dict(request_data)
    response = await router.route(request)
    return response.to_dict()
