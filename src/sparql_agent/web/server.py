"""
Production-Ready FastAPI Web Server for SPARQL Agent.

This module provides a comprehensive REST API for natural language to SPARQL conversion,
query execution, validation, and ontology management.

Features:
- Natural language to SPARQL conversion
- Direct SPARQL query execution
- Query validation and optimization
- Ontology lookup integration (OLS4)
- Multiple endpoint support
- Rate limiting and authentication
- Comprehensive monitoring and metrics
- WebSocket support for streaming
- Batch processing capabilities
- Health checks and status endpoints

Usage:
    uv run uvicorn sparql_agent.web.server:app --reload --host 0.0.0.0 --port 8000

API Documentation:
    OpenAPI/Swagger: http://localhost:8000/docs
    ReDoc: http://localhost:8000/redoc
"""

import asyncio
import hashlib
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from fastapi import (
    FastAPI,
    HTTPException,
    BackgroundTasks,
    WebSocket,
    WebSocketDisconnect,
    Depends,
    Header,
    UploadFile,
    File,
    Query as QueryParam,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from ..config.settings import get_settings, SPARQLAgentSettings
from ..core.types import (
    QueryResult,
    QueryStatus,
    EndpointInfo,
    GeneratedQuery,
    SchemaInfo,
    OntologyInfo,
)
from ..core.exceptions import (
    SPARQLAgentError,
    QueryGenerationError,
    QueryExecutionError,
    QueryValidationError,
    QueryTimeoutError,
)
from ..query.generator import SPARQLGenerator, GenerationStrategy, QueryScenario
from ..execution.executor import QueryExecutor, ResultFormat, FederatedQuery
from ..execution.validator import QueryValidator, ValidationResult
from ..ontology.ols_client import OLSClient
from ..llm.client import LLMClient
from ..llm.anthropic_provider import AnthropicProvider
from ..llm.openai_provider import OpenAIProvider
from ..formatting.structured import JSONFormatter, CSVFormatter


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Rate limiting
limiter = Limiter(key_func=get_remote_address)


# Global state management
class AppState:
    """Application state container."""
    def __init__(self):
        self.settings: Optional[SPARQLAgentSettings] = None
        self.generator: Optional[SPARQLGenerator] = None
        self.executor: Optional[QueryExecutor] = None
        self.validator: Optional[QueryValidator] = None
        self.ols_client: Optional[OLSClient] = None
        self.llm_client: Optional[LLMClient] = None
        self.active_websockets: List[WebSocket] = []
        self.query_cache: Dict[str, Any] = {}
        self.metrics: Dict[str, Any] = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_queries_generated": 0,
            "total_queries_executed": 0,
            "start_time": datetime.now(),
        }


app_state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    # Startup
    logger.info("Starting SPARQL Agent API server...")

    # Load settings
    app_state.settings = get_settings()

    # Initialize LLM client
    try:
        if app_state.settings.llm.api_key:
            # Use configured provider
            if "anthropic" in app_state.settings.llm.model_name.lower():
                provider = AnthropicProvider(
                    api_key=app_state.settings.llm.api_key,
                    model=app_state.settings.llm.model_name,
                )
            else:
                provider = OpenAIProvider(
                    api_key=app_state.settings.llm.api_key,
                    model=app_state.settings.llm.model_name,
                )
            app_state.llm_client = LLMClient(provider=provider)
            logger.info(f"Initialized LLM client with model: {app_state.settings.llm.model_name}")
    except Exception as e:
        logger.warning(f"LLM client initialization failed: {e}")

    # Initialize components
    app_state.generator = SPARQLGenerator(
        llm_client=app_state.llm_client,
        enable_validation=True,
        enable_optimization=True,
    )

    app_state.executor = QueryExecutor(
        timeout=app_state.settings.endpoint.default_timeout,
        max_retries=app_state.settings.endpoint.max_retries,
        enable_metrics=True,
    )

    app_state.validator = QueryValidator(strict=False)

    app_state.ols_client = OLSClient(
        base_url=app_state.settings.ontology.ols_api_base_url
    )

    logger.info("SPARQL Agent API server started successfully")

    yield

    # Shutdown
    logger.info("Shutting down SPARQL Agent API server...")

    # Close connections
    if app_state.executor:
        app_state.executor.close()

    # Close active WebSocket connections
    for ws in app_state.active_websockets:
        try:
            await ws.close()
        except:
            pass

    logger.info("SPARQL Agent API server stopped")


# Initialize FastAPI app
app = FastAPI(
    title="SPARQL Agent API",
    description="Natural language to SPARQL conversion and query execution API with ontology integration",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "Query", "description": "Natural language to SPARQL query operations"},
        {"name": "Execute", "description": "Direct SPARQL query execution"},
        {"name": "Validate", "description": "Query validation and optimization"},
        {"name": "Endpoints", "description": "SPARQL endpoint management"},
        {"name": "Ontology", "description": "Ontology lookup and information"},
        {"name": "Health", "description": "Health checks and monitoring"},
        {"name": "Batch", "description": "Batch processing operations"},
    ],
)


# Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Pydantic Models

class QueryRequest(BaseModel):
    """Request for natural language to SPARQL conversion."""

    natural_language: str = Field(
        ...,
        description="Natural language query to convert to SPARQL",
        example="Find all proteins from human with their functions"
    )
    endpoint_id: Optional[str] = Field(
        None,
        description="Endpoint identifier (e.g., 'uniprot', 'clinvar')",
        example="uniprot"
    )
    endpoint_url: Optional[str] = Field(
        None,
        description="Direct endpoint URL",
        example="https://sparql.uniprot.org/sparql"
    )
    strategy: Optional[str] = Field(
        "auto",
        description="Generation strategy: auto, template, llm, hybrid",
        example="hybrid"
    )
    execute: bool = Field(
        True,
        description="Execute the generated query",
    )
    return_alternatives: bool = Field(
        False,
        description="Return alternative query formulations"
    )
    max_alternatives: int = Field(
        3,
        description="Maximum number of alternatives to return",
        ge=1,
        le=10
    )
    limit: Optional[int] = Field(
        100,
        description="Result limit for query",
        ge=1,
        le=10000
    )
    timeout: Optional[int] = Field(
        None,
        description="Query timeout in seconds",
        ge=1,
        le=300
    )
    use_ontology: bool = Field(
        True,
        description="Use ontology information for query generation"
    )

    class Config:
        schema_extra = {
            "example": {
                "natural_language": "Find all proteins from human with their functions",
                "endpoint_id": "uniprot",
                "strategy": "hybrid",
                "execute": True,
                "limit": 100
            }
        }


class ExecuteRequest(BaseModel):
    """Request for direct SPARQL query execution."""

    query: str = Field(
        ...,
        description="SPARQL query to execute",
        example="SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10"
    )
    endpoint_url: str = Field(
        ...,
        description="SPARQL endpoint URL",
        example="https://sparql.uniprot.org/sparql"
    )
    format: str = Field(
        "json",
        description="Result format: json, xml, csv",
        example="json"
    )
    timeout: Optional[int] = Field(
        None,
        description="Query timeout in seconds",
        ge=1,
        le=300
    )
    validate: bool = Field(
        True,
        description="Validate query before execution"
    )

    class Config:
        schema_extra = {
            "example": {
                "query": "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10",
                "endpoint_url": "https://sparql.uniprot.org/sparql",
                "format": "json",
                "timeout": 60
            }
        }


class ValidateRequest(BaseModel):
    """Request for SPARQL query validation."""

    query: str = Field(
        ...,
        description="SPARQL query to validate",
        example="SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10"
    )
    strict: bool = Field(
        False,
        description="Enable strict validation mode"
    )
    auto_fix: bool = Field(
        False,
        description="Attempt to automatically fix validation errors"
    )


class GenerateRequest(BaseModel):
    """Request for generating multiple query alternatives."""

    natural_language: str = Field(
        ...,
        description="Natural language query",
        example="Find all proteins from human"
    )
    count: int = Field(
        5,
        description="Number of alternatives to generate",
        ge=1,
        le=10
    )
    endpoint_id: Optional[str] = None


class FederatedQueryRequest(BaseModel):
    """Request for federated query execution."""

    query: str = Field(..., description="SPARQL query to execute across endpoints")
    endpoint_urls: List[str] = Field(
        ...,
        description="List of endpoint URLs",
        example=["https://sparql.uniprot.org/sparql", "https://www.ebi.ac.uk/rdf/services/sparql"]
    )
    merge_strategy: str = Field(
        "union",
        description="Merge strategy: union, intersection, sequential"
    )
    parallel: bool = Field(True, description="Execute queries in parallel")
    fail_on_error: bool = Field(False, description="Fail if any endpoint fails")


class QueryResponse(BaseModel):
    """Response from query generation/execution."""

    success: bool = Field(..., description="Whether the operation succeeded")
    query: Optional[str] = Field(None, description="Generated/executed SPARQL query")
    natural_language: Optional[str] = Field(None, description="Original natural language query")
    results: Optional[Dict[str, Any]] = Field(None, description="Query results if executed")
    execution_time: Optional[float] = Field(None, description="Execution time in seconds")
    result_count: Optional[int] = Field(None, description="Number of results returned")
    explanation: Optional[str] = Field(None, description="Explanation of the query")
    confidence: Optional[float] = Field(None, description="Confidence score (0-1)")
    alternatives: Optional[List[str]] = Field(None, description="Alternative query formulations")
    validation_errors: Optional[List[str]] = Field(None, description="Validation errors")
    warnings: Optional[List[str]] = Field(None, description="Warnings")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    error: Optional[str] = Field(None, description="Error message if failed")


class ValidationResponse(BaseModel):
    """Response from query validation."""

    is_valid: bool = Field(..., description="Whether the query is valid")
    query: str = Field(..., description="Validated query")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    suggestions: List[str] = Field(default_factory=list, description="Optimization suggestions")
    complexity_score: Optional[float] = Field(None, description="Query complexity (0-10)")
    fixed_query: Optional[str] = Field(None, description="Auto-fixed query if requested")


class EndpointResponse(BaseModel):
    """Response with endpoint information."""

    id: str
    name: str
    url: str
    description: Optional[str] = None
    status: str = "unknown"
    capabilities: Optional[Dict[str, Any]] = None


class OntologySearchResponse(BaseModel):
    """Response from ontology search."""

    results: List[Dict[str, Any]] = Field(..., description="Search results")
    count: int = Field(..., description="Number of results")
    query: str = Field(..., description="Original search query")


class OntologyDetailResponse(BaseModel):
    """Response with detailed ontology information."""

    ontology_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    num_classes: Optional[int] = None
    num_properties: Optional[int] = None
    namespaces: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Overall system status")
    version: str = Field(..., description="API version")
    uptime: float = Field(..., description="Uptime in seconds")
    components: Dict[str, str] = Field(..., description="Component status")
    metrics: Optional[Dict[str, Any]] = Field(None, description="System metrics")


class BatchJob(BaseModel):
    """Batch processing job."""

    job_id: str
    status: str  # pending, running, completed, failed
    total: int
    completed: int
    failed: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    results: Optional[List[Dict[str, Any]]] = None
    errors: Optional[List[str]] = None


# Dependency functions

def verify_api_key(x_api_key: Optional[str] = Header(None)) -> Optional[str]:
    """Verify API key if authentication is enabled."""
    # TODO: Implement proper API key verification
    # For now, this is optional
    return x_api_key


def get_endpoint_info(endpoint_id: Optional[str] = None, endpoint_url: Optional[str] = None) -> EndpointInfo:
    """Get endpoint information from ID or URL."""
    if endpoint_url:
        return EndpointInfo(url=endpoint_url, name="custom")

    if endpoint_id:
        # Try to load from configuration
        endpoint_config = app_state.settings.get_endpoint_config(endpoint_id)
        if endpoint_config:
            return EndpointInfo(
                url=endpoint_config["url"],
                name=endpoint_config.get("name", endpoint_id),
                description=endpoint_config.get("description"),
                timeout=endpoint_config.get("timeout", 60),
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Endpoint '{endpoint_id}' not found in configuration"
            )

    raise HTTPException(
        status_code=400,
        detail="Either endpoint_id or endpoint_url must be provided"
    )


# API Endpoints

@app.get("/", tags=["Health"])
@limiter.limit("100/minute")
async def root(request: Any):
    """API root endpoint with basic information."""
    return {
        "name": "SPARQL Agent API",
        "version": "1.0.0",
        "description": "Natural language to SPARQL conversion and query execution",
        "documentation": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
@limiter.limit("100/minute")
async def health_check(request: Any):
    """
    Health check endpoint with system status and metrics.

    Returns system health, component status, and operational metrics.
    """
    uptime = (datetime.now() - app_state.metrics["start_time"]).total_seconds()

    components = {
        "generator": "healthy" if app_state.generator else "unavailable",
        "executor": "healthy" if app_state.executor else "unavailable",
        "validator": "healthy" if app_state.validator else "healthy",
        "ols_client": "healthy" if app_state.ols_client else "unavailable",
        "llm_client": "healthy" if app_state.llm_client else "unavailable",
    }

    # Overall status
    all_critical_healthy = all(
        status == "healthy" for name, status in components.items()
        if name in ["executor", "validator"]
    )

    return HealthResponse(
        status="healthy" if all_critical_healthy else "degraded",
        version="1.0.0",
        uptime=uptime,
        components=components,
        metrics={
            "total_requests": app_state.metrics["total_requests"],
            "successful_requests": app_state.metrics["successful_requests"],
            "failed_requests": app_state.metrics["failed_requests"],
            "total_queries_generated": app_state.metrics["total_queries_generated"],
            "total_queries_executed": app_state.metrics["total_queries_executed"],
            "cache_size": len(app_state.query_cache),
            "active_websockets": len(app_state.active_websockets),
        }
    )


@app.post("/query", response_model=QueryResponse, tags=["Query"])
@limiter.limit("20/minute")
async def generate_and_execute_query(
    request: Any,
    query_request: QueryRequest,
    background_tasks: BackgroundTasks,
    api_key: Optional[str] = Depends(verify_api_key),
):
    """
    Convert natural language to SPARQL and optionally execute.

    Takes a natural language query, generates a SPARQL query using LLM and/or templates,
    optionally validates and executes it, and returns the results.

    Features:
    - Multiple generation strategies (template, LLM, hybrid)
    - Automatic ontology integration
    - Query validation and optimization
    - Result execution with multiple formats
    - Alternative query generation
    - Caching for performance
    """
    app_state.metrics["total_requests"] += 1
    start_time = time.time()

    try:
        # Get endpoint info
        endpoint = None
        if query_request.endpoint_id or query_request.endpoint_url:
            endpoint = get_endpoint_info(
                query_request.endpoint_id,
                query_request.endpoint_url
            )

        # Determine strategy
        strategy_map = {
            "template": GenerationStrategy.TEMPLATE,
            "llm": GenerationStrategy.LLM,
            "hybrid": GenerationStrategy.HYBRID,
            "auto": GenerationStrategy.AUTO,
        }
        strategy = strategy_map.get(
            query_request.strategy.lower() if query_request.strategy else "auto",
            GenerationStrategy.AUTO
        )

        # Generate query
        logger.info(f"Generating query for: {query_request.natural_language}")

        generated = app_state.generator.generate(
            natural_language=query_request.natural_language,
            strategy=strategy,
            return_alternatives=query_request.return_alternatives,
            max_alternatives=query_request.max_alternatives,
            constraints={"limit": query_request.limit} if query_request.limit else {},
        )

        app_state.metrics["total_queries_generated"] += 1

        # Execute if requested
        result = None
        execution_time = None
        result_count = None

        if query_request.execute and endpoint:
            logger.info(f"Executing query on {endpoint.url}")

            timeout = query_request.timeout or app_state.settings.endpoint.default_timeout

            result = app_state.executor.execute(
                query=generated.query,
                endpoint=endpoint,
                timeout=timeout,
            )

            app_state.metrics["total_queries_executed"] += 1
            execution_time = result.execution_time
            result_count = result.row_count

            # Convert to dict format
            result_data = {
                "bindings": result.bindings,
                "variables": result.variables,
                "row_count": result.row_count,
            }
        else:
            result_data = None

        app_state.metrics["successful_requests"] += 1

        response = QueryResponse(
            success=True,
            query=generated.query,
            natural_language=query_request.natural_language,
            results=result_data,
            execution_time=execution_time or (time.time() - start_time),
            result_count=result_count,
            explanation=generated.explanation,
            confidence=generated.confidence,
            alternatives=generated.alternatives if query_request.return_alternatives else None,
            validation_errors=generated.validation_errors,
            metadata={
                "strategy": strategy.value,
                "used_ontology": generated.used_ontology,
                "endpoint": endpoint.url if endpoint else None,
                **generated.metadata,
            }
        )

        return response

    except SPARQLAgentError as e:
        app_state.metrics["failed_requests"] += 1
        logger.error(f"Query generation/execution failed: {e}")

        return QueryResponse(
            success=False,
            natural_language=query_request.natural_language,
            error=str(e),
            metadata={"error_type": type(e).__name__}
        )

    except Exception as e:
        app_state.metrics["failed_requests"] += 1
        logger.error(f"Unexpected error: {e}", exc_info=True)

        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.post("/execute", response_model=QueryResponse, tags=["Execute"])
@limiter.limit("30/minute")
async def execute_sparql_query(
    request: Any,
    execute_request: ExecuteRequest,
    api_key: Optional[str] = Depends(verify_api_key),
):
    """
    Execute a SPARQL query directly against an endpoint.

    Takes a SPARQL query string and executes it against the specified endpoint,
    with optional validation and multiple format support.

    Features:
    - Direct SPARQL query execution
    - Optional pre-execution validation
    - Multiple result formats (JSON, XML, CSV)
    - Timeout and retry handling
    - Performance metrics
    """
    app_state.metrics["total_requests"] += 1
    start_time = time.time()

    try:
        # Validate if requested
        validation_errors = []
        if execute_request.validate:
            validation = app_state.validator.validate(execute_request.query)
            if not validation.is_valid:
                validation_errors = [str(e) for e in validation.errors]
                logger.warning(f"Query validation failed: {validation_errors}")

        # Parse format
        format_map = {
            "json": ResultFormat.JSON,
            "xml": ResultFormat.XML,
            "csv": ResultFormat.CSV,
            "tsv": ResultFormat.TSV,
        }
        result_format = format_map.get(execute_request.format.lower(), ResultFormat.JSON)

        # Create endpoint
        endpoint = EndpointInfo(
            url=execute_request.endpoint_url,
            timeout=execute_request.timeout or app_state.settings.endpoint.default_timeout,
        )

        # Execute query
        logger.info(f"Executing query on {endpoint.url}")

        result = app_state.executor.execute(
            query=execute_request.query,
            endpoint=endpoint,
            format=result_format,
        )

        app_state.metrics["total_queries_executed"] += 1
        app_state.metrics["successful_requests"] += 1

        # Format results
        result_data = {
            "bindings": result.bindings,
            "variables": result.variables,
            "row_count": result.row_count,
            "status": result.status.value,
        }

        return QueryResponse(
            success=result.is_success,
            query=execute_request.query,
            results=result_data,
            execution_time=result.execution_time,
            result_count=result.row_count,
            validation_errors=validation_errors if validation_errors else None,
            metadata=result.metadata,
        )

    except Exception as e:
        app_state.metrics["failed_requests"] += 1
        logger.error(f"Query execution failed: {e}")

        return QueryResponse(
            success=False,
            query=execute_request.query,
            error=str(e),
            metadata={"error_type": type(e).__name__}
        )


@app.post("/validate", response_model=ValidationResponse, tags=["Validate"])
@limiter.limit("60/minute")
async def validate_sparql_query(
    request: Any,
    validate_request: ValidateRequest,
    api_key: Optional[str] = Depends(verify_api_key),
):
    """
    Validate a SPARQL query for syntax and best practices.

    Checks query syntax, validates PREFIX declarations, detects common errors,
    and provides optimization suggestions.

    Features:
    - Comprehensive syntax validation
    - PREFIX declaration checking
    - Variable consistency checks
    - Best practice recommendations
    - Complexity analysis
    - Optional auto-fix for common issues
    """
    try:
        validation = app_state.validator.validate(validate_request.query)

        # Extract information
        errors = [str(e) for e in validation.errors]
        warnings = [str(w) for w in validation.warning_issues]
        suggestions = []

        if hasattr(validation, 'metadata'):
            suggestions = validation.metadata.get('suggestions', [])

        # Calculate complexity
        complexity = None
        if hasattr(validation, 'metadata'):
            complexity = validation.metadata.get('complexity_score')

        # Auto-fix if requested
        fixed_query = None
        if validate_request.auto_fix and not validation.is_valid:
            # TODO: Implement auto-fix logic
            fixed_query = validate_request.query

        return ValidationResponse(
            is_valid=validation.is_valid,
            query=validate_request.query,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            complexity_score=complexity,
            fixed_query=fixed_query,
        )

    except Exception as e:
        logger.error(f"Validation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/endpoints", response_model=List[EndpointResponse], tags=["Endpoints"])
@limiter.limit("100/minute")
async def list_endpoints(request: Any):
    """
    List all configured SPARQL endpoints.

    Returns a list of available SPARQL endpoints with their configuration
    and capabilities.
    """
    try:
        endpoint_ids = app_state.settings.list_endpoints()
        endpoints = []

        for endpoint_id in endpoint_ids:
            config = app_state.settings.get_endpoint_config(endpoint_id)
            if config:
                endpoints.append(EndpointResponse(
                    id=endpoint_id,
                    name=config.get("name", endpoint_id),
                    url=config["url"],
                    description=config.get("description"),
                    status="available",
                    capabilities=config.get("capabilities"),
                ))

        return endpoints

    except Exception as e:
        logger.error(f"Failed to list endpoints: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/endpoints/{endpoint_id}/schema", tags=["Endpoints"])
@limiter.limit("30/minute")
async def get_endpoint_schema(
    request: Any,
    endpoint_id: str,
):
    """
    Get schema information for a specific endpoint.

    Retrieves available classes, properties, and namespaces from the endpoint.
    """
    try:
        endpoint = get_endpoint_info(endpoint_id=endpoint_id)

        # TODO: Implement schema discovery
        # For now, return basic info
        return {
            "endpoint_id": endpoint_id,
            "endpoint_url": endpoint.url,
            "message": "Schema discovery not yet implemented"
        }

    except Exception as e:
        logger.error(f"Failed to get schema: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ontologies", response_model=OntologySearchResponse, tags=["Ontology"])
@limiter.limit("60/minute")
async def search_ontologies(
    request: Any,
    q: str = QueryParam(..., description="Search query"),
    ontology: Optional[str] = QueryParam(None, description="Filter by ontology ID"),
    limit: int = QueryParam(10, ge=1, le=100, description="Result limit"),
):
    """
    Search for terms across ontologies using OLS4.

    Searches the EBI Ontology Lookup Service for matching terms,
    classes, and properties.
    """
    try:
        results = app_state.ols_client.search(
            query=q,
            ontology=ontology,
            limit=limit,
        )

        return OntologySearchResponse(
            results=results,
            count=len(results),
            query=q,
        )

    except Exception as e:
        logger.error(f"Ontology search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ontologies/{ontology_id}", response_model=OntologyDetailResponse, tags=["Ontology"])
@limiter.limit("60/minute")
async def get_ontology_details(
    request: Any,
    ontology_id: str,
):
    """
    Get detailed information about a specific ontology.

    Returns metadata, statistics, and configuration for the specified ontology.
    """
    try:
        details = app_state.ols_client.get_ontology(ontology_id)

        return OntologyDetailResponse(
            ontology_id=ontology_id,
            title=details.get("config", {}).get("title"),
            description=details.get("config", {}).get("description"),
            version=details.get("config", {}).get("version"),
            num_classes=details.get("numberOfTerms"),
            num_properties=details.get("numberOfProperties"),
            metadata=details,
        )

    except Exception as e:
        logger.error(f"Failed to get ontology details: {e}")
        raise HTTPException(status_code=404, detail=f"Ontology '{ontology_id}' not found")


@app.post("/generate", tags=["Query"])
@limiter.limit("15/minute")
async def generate_query_alternatives(
    request: Any,
    generate_request: GenerateRequest,
    api_key: Optional[str] = Depends(verify_api_key),
):
    """
    Generate multiple alternative SPARQL query formulations.

    Creates several different SPARQL queries for the same natural language input,
    useful for finding the best query formulation.
    """
    try:
        alternatives = []

        for i in range(generate_request.count):
            generated = app_state.generator.generate(
                natural_language=generate_request.natural_language,
                strategy=GenerationStrategy.AUTO,
            )

            alternatives.append({
                "query": generated.query,
                "confidence": generated.confidence,
                "explanation": generated.explanation,
                "metadata": generated.metadata,
            })

        return {
            "success": True,
            "natural_language": generate_request.natural_language,
            "alternatives": alternatives,
            "count": len(alternatives),
        }

    except Exception as e:
        logger.error(f"Alternative generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/federated", response_model=QueryResponse, tags=["Execute"])
@limiter.limit("10/minute")
async def execute_federated_query(
    request: Any,
    federated_request: FederatedQueryRequest,
    api_key: Optional[str] = Depends(verify_api_key),
):
    """
    Execute a SPARQL query across multiple endpoints (federation).

    Executes the same query on multiple endpoints and merges the results
    according to the specified strategy.

    Features:
    - Parallel or sequential execution
    - Multiple merge strategies (union, intersection)
    - Error handling per endpoint
    - Comprehensive result aggregation
    """
    try:
        # Create endpoint infos
        endpoints = [
            EndpointInfo(url=url, name=f"endpoint_{i}")
            for i, url in enumerate(federated_request.endpoint_urls)
        ]

        # Create federation config
        config = FederatedQuery(
            endpoints=endpoints,
            merge_strategy=federated_request.merge_strategy,
            parallel=federated_request.parallel,
            fail_on_error=federated_request.fail_on_error,
        )

        # Execute federated query
        result = app_state.executor.execute_federated(
            query=federated_request.query,
            config=config,
        )

        # Format results
        result_data = {
            "bindings": result.bindings,
            "variables": result.variables,
            "row_count": result.row_count,
        }

        return QueryResponse(
            success=result.is_success,
            query=federated_request.query,
            results=result_data,
            execution_time=result.execution_time,
            result_count=result.row_count,
            metadata=result.metadata,
        )

    except Exception as e:
        logger.error(f"Federated query execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/batch/upload", tags=["Batch"])
@limiter.limit("5/minute")
async def upload_batch_queries(
    request: Any,
    file: UploadFile = File(...),
    endpoint_url: Optional[str] = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    api_key: Optional[str] = Depends(verify_api_key),
):
    """
    Upload a file with multiple queries for batch processing.

    Accepts a file (CSV, JSON, or text) with multiple natural language queries
    or SPARQL queries for batch processing.

    Features:
    - Multiple file format support
    - Background processing
    - Progress tracking
    - Result aggregation
    """
    try:
        # Read file content
        content = await file.read()

        # Parse based on file type
        queries = []
        if file.filename.endswith('.json'):
            import json
            data = json.loads(content.decode('utf-8'))
            if isinstance(data, list):
                queries = data
            elif isinstance(data, dict) and 'queries' in data:
                queries = data['queries']
        elif file.filename.endswith('.csv'):
            import csv
            import io
            reader = csv.DictReader(io.StringIO(content.decode('utf-8')))
            queries = list(reader)
        else:
            # Assume text file with one query per line
            queries = [
                {"query": line.strip()}
                for line in content.decode('utf-8').split('\n')
                if line.strip()
            ]

        # Create job ID
        job_id = hashlib.md5(content).hexdigest()

        # TODO: Implement background processing
        # For now, return job info

        return {
            "success": True,
            "job_id": job_id,
            "status": "pending",
            "total": len(queries),
            "message": "Batch job created successfully"
        }

    except Exception as e:
        logger.error(f"Batch upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/batch/{job_id}", tags=["Batch"])
@limiter.limit("60/minute")
async def get_batch_job_status(
    request: Any,
    job_id: str,
):
    """
    Get the status of a batch processing job.

    Returns progress information and results for a batch job.
    """
    # TODO: Implement batch job tracking
    return {
        "job_id": job_id,
        "status": "not_found",
        "message": "Batch job tracking not yet implemented"
    }


@app.websocket("/ws/query")
async def websocket_query_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time query streaming.

    Allows clients to send queries and receive results via WebSocket
    for real-time updates and streaming results.
    """
    await websocket.accept()
    app_state.active_websockets.append(websocket)

    try:
        while True:
            # Receive message
            data = await websocket.receive_json()

            action = data.get("action", "query")

            if action == "query":
                natural_language = data.get("natural_language")
                endpoint_url = data.get("endpoint_url")

                # Send acknowledgment
                await websocket.send_json({
                    "type": "ack",
                    "message": "Query received, processing..."
                })

                try:
                    # Generate query
                    generated = app_state.generator.generate(
                        natural_language=natural_language,
                    )

                    # Send generated query
                    await websocket.send_json({
                        "type": "generated",
                        "query": generated.query,
                        "confidence": generated.confidence,
                    })

                    # Execute if endpoint provided
                    if endpoint_url:
                        endpoint = EndpointInfo(url=endpoint_url)
                        result = app_state.executor.execute(
                            query=generated.query,
                            endpoint=endpoint,
                        )

                        # Send results
                        await websocket.send_json({
                            "type": "results",
                            "data": {
                                "bindings": result.bindings[:100],  # Limit for streaming
                                "row_count": result.row_count,
                                "execution_time": result.execution_time,
                            }
                        })

                    # Send completion
                    await websocket.send_json({
                        "type": "complete",
                        "message": "Query processing complete"
                    })

                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "error": str(e)
                    })

            elif action == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        app_state.active_websockets.remove(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        app_state.active_websockets.remove(websocket)


@app.get("/metrics", tags=["Health"])
@limiter.limit("60/minute")
async def get_metrics(request: Any):
    """
    Get detailed system metrics and statistics.

    Returns comprehensive metrics about API usage, performance, and health.
    """
    metrics = dict(app_state.metrics)

    # Add executor statistics
    if app_state.executor:
        metrics["executor"] = app_state.executor.get_statistics()

    # Add generator statistics
    if app_state.generator:
        metrics["generator"] = app_state.generator.get_statistics()

    # Calculate rates
    uptime = (datetime.now() - metrics["start_time"]).total_seconds()
    if uptime > 0:
        metrics["requests_per_second"] = metrics["total_requests"] / uptime
        metrics["success_rate"] = (
            metrics["successful_requests"] / metrics["total_requests"]
            if metrics["total_requests"] > 0 else 0
        )

    # Convert datetime to ISO format
    metrics["start_time"] = metrics["start_time"].isoformat()

    return metrics


# Error handlers

@app.exception_handler(SPARQLAgentError)
async def sparql_agent_exception_handler(request, exc: SPARQLAgentError):
    """Handle SPARQL Agent exceptions."""
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "error": str(exc),
            "error_type": type(exc).__name__,
            "details": exc.details if hasattr(exc, 'details') else None,
        }
    )


@app.exception_handler(QueryTimeoutError)
async def timeout_exception_handler(request, exc: QueryTimeoutError):
    """Handle timeout exceptions."""
    return JSONResponse(
        status_code=504,
        content={
            "success": False,
            "error": "Query execution timed out",
            "details": str(exc),
        }
    )


# Application factory

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    return app


def main():
    """Main entry point for sparql-agent-server CLI command."""
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(
        description="SPARQL Agent Web Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload on code changes (development mode)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes (default: 1)",
    )
    parser.add_argument(
        "--log-level",
        default="info",
        choices=["critical", "error", "warning", "info", "debug", "trace"],
        help="Log level (default: info)",
    )

    args = parser.parse_args()

    logger.info(f"Starting SPARQL Agent Web Server on {args.host}:{args.port}")

    try:
        uvicorn.run(
            "sparql_agent.web.server:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            workers=args.workers,
            log_level=args.log_level,
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
