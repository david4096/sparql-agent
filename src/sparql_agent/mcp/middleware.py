"""
Middleware components for MCP Server.

This module provides production-ready middleware for error handling, logging,
and validation of MCP requests/responses. All middleware follows MCP conventions
and provides comprehensive observability, security, and reliability features.

Features:
- ErrorMiddleware: Exception catching, formatting, and sanitization
- LoggingMiddleware: Request/response logging with performance metrics
- ValidationMiddleware: Input validation and security sanitization
- Composable middleware chain architecture

Example:
    >>> from sparql_agent.mcp.middleware import (
    ...     ErrorMiddleware, LoggingMiddleware, ValidationMiddleware
    ... )
    >>> error_handler = ErrorMiddleware(debug=True)
    >>> logger = LoggingMiddleware(level="INFO")
    >>> validator = ValidationMiddleware(max_request_size=1024*1024)
"""

import asyncio
import json
import logging
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union
from functools import wraps
import re

from ..core.exceptions import (
    SPARQLAgentError,
    EndpointError,
    QueryError,
    SchemaError,
    OntologyError,
    LLMError,
    QueryGenerationError,
    FormattingError,
    ConfigurationError,
    ValidationError,
    ResourceError,
    CacheError,
)


logger = logging.getLogger(__name__)


# ============================================================================
# Middleware Configuration
# ============================================================================


class LogLevel(Enum):
    """Log level enumeration."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class ErrorMiddlewareConfig:
    """Configuration for error middleware."""
    debug: bool = False
    include_traceback: bool = False
    sanitize_errors: bool = True
    max_error_length: int = 1000
    log_errors: bool = True
    log_level: LogLevel = LogLevel.ERROR


@dataclass
class LoggingMiddlewareConfig:
    """Configuration for logging middleware."""
    level: LogLevel = LogLevel.INFO
    log_requests: bool = True
    log_responses: bool = True
    log_performance: bool = True
    log_user_actions: bool = True
    include_arguments: bool = True
    include_results: bool = False  # Can be verbose
    max_log_length: int = 2000
    performance_threshold_ms: float = 1000.0  # Warn if slower


@dataclass
class ValidationMiddlewareConfig:
    """Configuration for validation middleware."""
    max_request_size: int = 10 * 1024 * 1024  # 10MB
    max_query_length: int = 100000  # 100KB
    max_results_limit: int = 10000
    allowed_tool_names: Optional[Set[str]] = None
    validate_urls: bool = True
    validate_sparql: bool = True
    sanitize_inputs: bool = True
    rate_limit_enabled: bool = False
    rate_limit_per_minute: int = 60


# ============================================================================
# Error Middleware
# ============================================================================


class ErrorMiddleware:
    """
    Middleware for catching and formatting exceptions in MCP operations.

    Features:
    - Catches all exceptions and converts to MCP-compatible format
    - Sanitizes error messages to prevent information leakage
    - Provides debug mode for development
    - Maps internal exceptions to appropriate error codes
    - Logs errors for monitoring

    Example:
        >>> middleware = ErrorMiddleware(debug=True, include_traceback=True)
        >>> @middleware.wrap_handler
        ... async def my_handler(arg):
        ...     return await some_operation(arg)
    """

    def __init__(self, config: Optional[ErrorMiddlewareConfig] = None):
        """
        Initialize error middleware.

        Args:
            config: Middleware configuration
        """
        self.config = config or ErrorMiddlewareConfig()
        self._error_count = 0
        self._error_history: List[Dict[str, Any]] = []

    def wrap_handler(self, handler: Callable) -> Callable:
        """
        Decorator to wrap a handler with error handling.

        Args:
            handler: Async handler function

        Returns:
            Wrapped handler function
        """
        @wraps(handler)
        async def wrapper(*args, **kwargs):
            try:
                return await handler(*args, **kwargs)
            except Exception as e:
                return await self.handle_error(e, handler.__name__, kwargs)
        return wrapper

    async def handle_error(
        self,
        error: Exception,
        handler_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Handle an error and convert to MCP format.

        Args:
            error: Exception that occurred
            handler_name: Name of the handler where error occurred
            context: Additional context information

        Returns:
            Formatted error response
        """
        self._error_count += 1

        # Build error response
        error_response = {
            "error": self._format_error_message(error),
            "error_type": type(error).__name__,
            "handler": handler_name,
            "timestamp": datetime.now().isoformat(),
        }

        # Add error code based on exception type
        error_response["error_code"] = self._get_error_code(error)

        # Add debug information if enabled
        if self.config.debug:
            error_response["debug"] = {
                "error_class": f"{type(error).__module__}.{type(error).__name__}",
                "context": context,
            }

        # Add traceback if enabled
        if self.config.include_traceback:
            error_response["traceback"] = traceback.format_exc()

        # Add sanitized details for known exception types
        if isinstance(error, SPARQLAgentError) and hasattr(error, 'details'):
            error_response["details"] = self._sanitize_details(error.details)

        # Log the error
        if self.config.log_errors:
            self._log_error(error, handler_name, error_response)

        # Store in history (limited size)
        self._error_history.append({
            "timestamp": datetime.now().isoformat(),
            "handler": handler_name,
            "error_type": type(error).__name__,
            "message": str(error),
        })
        if len(self._error_history) > 100:
            self._error_history.pop(0)

        return error_response

    def _format_error_message(self, error: Exception) -> str:
        """
        Format error message with sanitization.

        Args:
            error: Exception to format

        Returns:
            Formatted error message
        """
        message = str(error)

        # Sanitize if enabled
        if self.config.sanitize_errors:
            message = self._sanitize_message(message)

        # Truncate if too long
        if len(message) > self.config.max_error_length:
            message = message[:self.config.max_error_length] + "... (truncated)"

        return message

    def _sanitize_message(self, message: str) -> str:
        """
        Sanitize error message to prevent information leakage.

        Args:
            message: Original error message

        Returns:
            Sanitized message
        """
        # Remove file paths
        message = re.sub(r'/[^\s]+\.py', '<file>', message)
        message = re.sub(r'[A-Z]:\\[^\s]+\.py', '<file>', message)

        # Remove API keys and tokens (common patterns)
        message = re.sub(r'[a-zA-Z0-9_-]{32,}', '<redacted>', message)
        message = re.sub(r'sk-[a-zA-Z0-9]+', '<redacted>', message)
        message = re.sub(r'Bearer [a-zA-Z0-9\-._~+/]+', 'Bearer <redacted>', message)

        # Remove email addresses
        message = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '<email>', message)

        # Remove IP addresses
        message = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '<ip>', message)

        return message

    def _sanitize_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize error details dictionary.

        Args:
            details: Original details

        Returns:
            Sanitized details
        """
        sanitized = {}
        for key, value in details.items():
            if isinstance(value, str):
                sanitized[key] = self._sanitize_message(value)
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_details(value)
            else:
                sanitized[key] = value
        return sanitized

    def _get_error_code(self, error: Exception) -> str:
        """
        Map exception type to error code.

        Args:
            error: Exception

        Returns:
            Error code string
        """
        error_code_map = {
            EndpointError: "ENDPOINT_ERROR",
            QueryError: "QUERY_ERROR",
            SchemaError: "SCHEMA_ERROR",
            OntologyError: "ONTOLOGY_ERROR",
            LLMError: "LLM_ERROR",
            QueryGenerationError: "GENERATION_ERROR",
            FormattingError: "FORMATTING_ERROR",
            ConfigurationError: "CONFIG_ERROR",
            ValidationError: "VALIDATION_ERROR",
            ResourceError: "RESOURCE_ERROR",
            CacheError: "CACHE_ERROR",
            ValueError: "INVALID_INPUT",
            KeyError: "MISSING_PARAMETER",
            TimeoutError: "TIMEOUT",
            ConnectionError: "CONNECTION_ERROR",
        }

        for exc_type, code in error_code_map.items():
            if isinstance(error, exc_type):
                return code

        return "INTERNAL_ERROR"

    def _log_error(
        self,
        error: Exception,
        handler_name: str,
        error_response: Dict[str, Any]
    ) -> None:
        """
        Log error information.

        Args:
            error: Exception that occurred
            handler_name: Handler name
            error_response: Formatted error response
        """
        log_level = getattr(logging, self.config.log_level.value)
        logger.log(
            log_level,
            f"Error in {handler_name}: {error_response['error_code']} - {error}",
            exc_info=self.config.include_traceback
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        return {
            "total_errors": self._error_count,
            "recent_errors": self._error_history[-10:],
        }


# ============================================================================
# Logging Middleware
# ============================================================================


class LoggingMiddleware:
    """
    Middleware for request/response logging and performance tracking.

    Features:
    - Request and response logging
    - Performance metrics collection
    - User action tracking
    - Configurable log levels and detail
    - Automatic slow operation detection

    Example:
        >>> middleware = LoggingMiddleware(
        ...     config=LoggingMiddlewareConfig(
        ...         level=LogLevel.INFO,
        ...         log_performance=True
        ...     )
        ... )
        >>> @middleware.wrap_handler
        ... async def my_handler(arg):
        ...     return await some_operation(arg)
    """

    def __init__(self, config: Optional[LoggingMiddlewareConfig] = None):
        """
        Initialize logging middleware.

        Args:
            config: Middleware configuration
        """
        self.config = config or LoggingMiddlewareConfig()
        self._request_count = 0
        self._total_duration = 0.0
        self._performance_history: List[Dict[str, Any]] = []

    def wrap_handler(self, handler: Callable) -> Callable:
        """
        Decorator to wrap a handler with logging.

        Args:
            handler: Async handler function

        Returns:
            Wrapped handler function
        """
        @wraps(handler)
        async def wrapper(*args, **kwargs):
            return await self.log_handler_execution(handler, *args, **kwargs)
        return wrapper

    async def log_handler_execution(
        self,
        handler: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute handler with logging.

        Args:
            handler: Handler function
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Handler result
        """
        start_time = time.time()
        handler_name = handler.__name__
        request_id = f"{handler_name}_{self._request_count}"

        self._request_count += 1

        # Log request
        if self.config.log_requests:
            self._log_request(handler_name, request_id, kwargs)

        try:
            # Execute handler
            result = await handler(*args, **kwargs)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            self._total_duration += duration_ms

            # Log response
            if self.config.log_responses:
                self._log_response(handler_name, request_id, result, duration_ms)

            # Log performance
            if self.config.log_performance:
                self._log_performance(handler_name, duration_ms)

            # Track user action
            if self.config.log_user_actions:
                self._track_user_action(handler_name, kwargs, True, duration_ms)

            return result

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._total_duration += duration_ms

            # Log failure
            self._log_failure(handler_name, request_id, e, duration_ms)

            # Track failed action
            if self.config.log_user_actions:
                self._track_user_action(handler_name, kwargs, False, duration_ms)

            raise

    def _log_request(
        self,
        handler_name: str,
        request_id: str,
        arguments: Dict[str, Any]
    ) -> None:
        """
        Log request details.

        Args:
            handler_name: Handler name
            request_id: Unique request ID
            arguments: Request arguments
        """
        log_message = f"Request [{request_id}] {handler_name}"

        if self.config.include_arguments:
            args_str = self._truncate_log(json.dumps(arguments, default=str))
            log_message += f" - Args: {args_str}"

        log_level = getattr(logging, self.config.level.value)
        logger.log(log_level, log_message)

    def _log_response(
        self,
        handler_name: str,
        request_id: str,
        result: Any,
        duration_ms: float
    ) -> None:
        """
        Log response details.

        Args:
            handler_name: Handler name
            request_id: Request ID
            result: Handler result
            duration_ms: Execution duration in milliseconds
        """
        log_message = f"Response [{request_id}] {handler_name} - {duration_ms:.2f}ms"

        if self.config.include_results:
            result_str = self._truncate_log(json.dumps(result, default=str))
            log_message += f" - Result: {result_str}"

        log_level = getattr(logging, self.config.level.value)
        logger.log(log_level, log_message)

    def _log_performance(self, handler_name: str, duration_ms: float) -> None:
        """
        Log performance metrics.

        Args:
            handler_name: Handler name
            duration_ms: Duration in milliseconds
        """
        # Store in history
        self._performance_history.append({
            "handler": handler_name,
            "duration_ms": duration_ms,
            "timestamp": datetime.now().isoformat(),
        })

        # Keep history limited
        if len(self._performance_history) > 1000:
            self._performance_history.pop(0)

        # Warn on slow operations
        if duration_ms > self.config.performance_threshold_ms:
            logger.warning(
                f"Slow operation: {handler_name} took {duration_ms:.2f}ms "
                f"(threshold: {self.config.performance_threshold_ms}ms)"
            )

    def _log_failure(
        self,
        handler_name: str,
        request_id: str,
        error: Exception,
        duration_ms: float
    ) -> None:
        """
        Log handler failure.

        Args:
            handler_name: Handler name
            request_id: Request ID
            error: Exception that occurred
            duration_ms: Duration before failure
        """
        logger.error(
            f"Failure [{request_id}] {handler_name} - {duration_ms:.2f}ms - "
            f"{type(error).__name__}: {error}"
        )

    def _track_user_action(
        self,
        handler_name: str,
        arguments: Dict[str, Any],
        success: bool,
        duration_ms: float
    ) -> None:
        """
        Track user action for analytics.

        Args:
            handler_name: Handler name
            arguments: Request arguments
            success: Whether action succeeded
            duration_ms: Duration in milliseconds
        """
        # Extract relevant action details
        action_type = handler_name.replace("handle_", "").replace("_", ".")

        action_log = {
            "action": action_type,
            "success": success,
            "duration_ms": duration_ms,
            "timestamp": datetime.now().isoformat(),
        }

        # Add key arguments (without sensitive data)
        if "tool_name" in arguments:
            action_log["tool"] = arguments["tool_name"]
        if "endpoint_url" in arguments:
            action_log["endpoint"] = arguments["endpoint_url"]

        logger.info(f"UserAction: {json.dumps(action_log)}")

    def _truncate_log(self, text: str) -> str:
        """
        Truncate log text to maximum length.

        Args:
            text: Text to truncate

        Returns:
            Truncated text
        """
        if len(text) > self.config.max_log_length:
            return text[:self.config.max_log_length] + "... (truncated)"
        return text

    def get_stats(self) -> Dict[str, Any]:
        """Get logging and performance statistics."""
        avg_duration = (
            self._total_duration / self._request_count
            if self._request_count > 0
            else 0
        )

        # Calculate percentiles
        durations = [p["duration_ms"] for p in self._performance_history]
        durations.sort()

        percentiles = {}
        if durations:
            percentiles = {
                "p50": durations[len(durations) // 2],
                "p95": durations[int(len(durations) * 0.95)] if len(durations) > 1 else durations[0],
                "p99": durations[int(len(durations) * 0.99)] if len(durations) > 1 else durations[0],
            }

        return {
            "total_requests": self._request_count,
            "total_duration_ms": self._total_duration,
            "avg_duration_ms": avg_duration,
            "percentiles": percentiles,
            "slow_operations": sum(
                1 for p in self._performance_history
                if p["duration_ms"] > self.config.performance_threshold_ms
            ),
        }


# ============================================================================
# Validation Middleware
# ============================================================================


class ValidationMiddleware:
    """
    Middleware for input validation and security sanitization.

    Features:
    - Request size limiting
    - Input parameter validation
    - URL and SPARQL syntax validation
    - Security sanitization (XSS, SQL injection prevention)
    - Rate limiting support
    - Type checking

    Example:
        >>> middleware = ValidationMiddleware(
        ...     config=ValidationMiddlewareConfig(
        ...         max_request_size=1024*1024,
        ...         validate_urls=True
        ...     )
        ... )
        >>> @middleware.wrap_handler
        ... async def my_handler(arg):
        ...     return await some_operation(arg)
    """

    def __init__(self, config: Optional[ValidationMiddlewareConfig] = None):
        """
        Initialize validation middleware.

        Args:
            config: Middleware configuration
        """
        self.config = config or ValidationMiddlewareConfig()
        self._validation_failures = 0
        self._rate_limit_cache: Dict[str, List[float]] = {}

        # URL validation regex
        self._url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or IP
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE
        )

    def wrap_handler(self, handler: Callable) -> Callable:
        """
        Decorator to wrap a handler with validation.

        Args:
            handler: Async handler function

        Returns:
            Wrapped handler function
        """
        @wraps(handler)
        async def wrapper(*args, **kwargs):
            # Validate before execution
            await self.validate_request(handler.__name__, kwargs)
            return await handler(*args, **kwargs)
        return wrapper

    async def validate_request(
        self,
        handler_name: str,
        arguments: Dict[str, Any]
    ) -> None:
        """
        Validate request arguments.

        Args:
            handler_name: Handler name
            arguments: Request arguments

        Raises:
            ValidationError: If validation fails
        """
        try:
            # Check rate limit
            if self.config.rate_limit_enabled:
                self._check_rate_limit(handler_name)

            # Validate request size
            self._validate_request_size(arguments)

            # Validate tool name if provided
            if "name" in arguments and self.config.allowed_tool_names:
                self._validate_tool_name(arguments["name"])

            # Validate specific argument types
            if "query" in arguments:
                self._validate_sparql_query(arguments["query"])

            if "endpoint_url" in arguments:
                self._validate_url(arguments["endpoint_url"])

            if "limit" in arguments:
                self._validate_limit(arguments["limit"])

            # Sanitize inputs if enabled
            if self.config.sanitize_inputs:
                self._sanitize_arguments(arguments)

        except ValidationError:
            self._validation_failures += 1
            raise
        except Exception as e:
            self._validation_failures += 1
            raise ValidationError(f"Validation failed: {e}")

    def _validate_request_size(self, arguments: Dict[str, Any]) -> None:
        """
        Validate request size.

        Args:
            arguments: Request arguments

        Raises:
            ValidationError: If request is too large
        """
        request_size = len(json.dumps(arguments, default=str).encode('utf-8'))
        if request_size > self.config.max_request_size:
            raise ValidationError(
                f"Request size {request_size} exceeds maximum {self.config.max_request_size}",
                details={"request_size": request_size, "max_size": self.config.max_request_size}
            )

    def _validate_tool_name(self, tool_name: str) -> None:
        """
        Validate tool name.

        Args:
            tool_name: Tool name to validate

        Raises:
            ValidationError: If tool name is not allowed
        """
        if self.config.allowed_tool_names and tool_name not in self.config.allowed_tool_names:
            raise ValidationError(
                f"Tool '{tool_name}' is not in allowed tools list",
                details={"tool_name": tool_name}
            )

    def _validate_sparql_query(self, query: str) -> None:
        """
        Validate SPARQL query.

        Args:
            query: SPARQL query string

        Raises:
            ValidationError: If query is invalid
        """
        if not query or not isinstance(query, str):
            raise ValidationError("Query must be a non-empty string")

        if len(query) > self.config.max_query_length:
            raise ValidationError(
                f"Query length {len(query)} exceeds maximum {self.config.max_query_length}",
                details={"query_length": len(query)}
            )

        # Basic SPARQL syntax check
        if self.config.validate_sparql:
            query_upper = query.upper()
            if not any(keyword in query_upper for keyword in ["SELECT", "CONSTRUCT", "ASK", "DESCRIBE"]):
                raise ValidationError(
                    "Query must contain a valid SPARQL query type (SELECT, CONSTRUCT, ASK, or DESCRIBE)"
                )

        # Check for potentially dangerous patterns
        dangerous_patterns = [
            r'LOAD\s+<',  # LOAD operation
            r'DROP\s+',   # DROP operation
            r'CLEAR\s+',  # CLEAR operation
            r'CREATE\s+', # CREATE operation
            r'INSERT\s+', # INSERT operation (in UPDATE context)
            r'DELETE\s+', # DELETE operation (in UPDATE context)
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                raise ValidationError(
                    f"Query contains potentially dangerous operation",
                    details={"pattern": pattern}
                )

    def _validate_url(self, url: str) -> None:
        """
        Validate URL.

        Args:
            url: URL to validate

        Raises:
            ValidationError: If URL is invalid
        """
        if not url or not isinstance(url, str):
            raise ValidationError("URL must be a non-empty string")

        if self.config.validate_urls:
            if not self._url_pattern.match(url):
                raise ValidationError(
                    f"Invalid URL format: {url}",
                    details={"url": url}
                )

            # Block dangerous schemes
            if url.startswith(('file://', 'ftp://', 'javascript:', 'data:')):
                raise ValidationError(
                    f"URL scheme not allowed: {url}",
                    details={"url": url}
                )

    def _validate_limit(self, limit: int) -> None:
        """
        Validate result limit.

        Args:
            limit: Result limit

        Raises:
            ValidationError: If limit is invalid
        """
        if not isinstance(limit, int):
            raise ValidationError(
                f"Limit must be an integer, got {type(limit).__name__}"
            )

        if limit < 0:
            raise ValidationError("Limit must be non-negative")

        if limit > self.config.max_results_limit:
            raise ValidationError(
                f"Limit {limit} exceeds maximum {self.config.max_results_limit}",
                details={"limit": limit, "max_limit": self.config.max_results_limit}
            )

    def _sanitize_arguments(self, arguments: Dict[str, Any]) -> None:
        """
        Sanitize input arguments to prevent XSS and injection attacks.

        Args:
            arguments: Arguments to sanitize (modified in-place)
        """
        for key, value in arguments.items():
            if isinstance(value, str):
                # Remove control characters
                value = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', value)

                # Remove potential XSS patterns
                value = re.sub(r'<script[^>]*>.*?</script>', '', value, flags=re.IGNORECASE | re.DOTALL)
                value = re.sub(r'javascript:', '', value, flags=re.IGNORECASE)
                value = re.sub(r'on\w+\s*=', '', value, flags=re.IGNORECASE)

                arguments[key] = value

            elif isinstance(value, dict):
                self._sanitize_arguments(value)

    def _check_rate_limit(self, handler_name: str) -> None:
        """
        Check rate limit for handler.

        Args:
            handler_name: Handler name

        Raises:
            ValidationError: If rate limit exceeded
        """
        current_time = time.time()
        window_start = current_time - 60  # 1 minute window

        # Initialize or clean old entries
        if handler_name not in self._rate_limit_cache:
            self._rate_limit_cache[handler_name] = []

        timestamps = self._rate_limit_cache[handler_name]
        timestamps = [ts for ts in timestamps if ts > window_start]

        # Check limit
        if len(timestamps) >= self.config.rate_limit_per_minute:
            raise ValidationError(
                f"Rate limit exceeded for {handler_name}",
                details={
                    "limit": self.config.rate_limit_per_minute,
                    "window": "1 minute"
                }
            )

        # Add current timestamp
        timestamps.append(current_time)
        self._rate_limit_cache[handler_name] = timestamps

    def get_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        return {
            "validation_failures": self._validation_failures,
            "rate_limit_cache_size": len(self._rate_limit_cache),
        }


# ============================================================================
# Middleware Chain
# ============================================================================


class MiddlewareChain:
    """
    Composable middleware chain for MCP handlers.

    Allows combining multiple middleware components in a flexible order.

    Example:
        >>> chain = MiddlewareChain()
        >>> chain.add(ValidationMiddleware())
        >>> chain.add(LoggingMiddleware())
        >>> chain.add(ErrorMiddleware())
        >>>
        >>> @chain.wrap_handler
        ... async def my_handler(arg):
        ...     return await some_operation(arg)
    """

    def __init__(self):
        """Initialize middleware chain."""
        self.middlewares: List[Any] = []

    def add(self, middleware: Any) -> "MiddlewareChain":
        """
        Add middleware to chain.

        Args:
            middleware: Middleware instance with wrap_handler method

        Returns:
            Self for chaining
        """
        if not hasattr(middleware, 'wrap_handler'):
            raise ValueError("Middleware must have wrap_handler method")

        self.middlewares.append(middleware)
        return self

    def wrap_handler(self, handler: Callable) -> Callable:
        """
        Wrap handler with all middleware in chain.

        Args:
            handler: Handler function to wrap

        Returns:
            Wrapped handler function
        """
        wrapped = handler
        # Apply middleware in reverse order (last added wraps first)
        for middleware in reversed(self.middlewares):
            wrapped = middleware.wrap_handler(wrapped)
        return wrapped

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics from all middleware."""
        stats = {}
        for i, middleware in enumerate(self.middlewares):
            if hasattr(middleware, 'get_stats'):
                stats[f"{type(middleware).__name__}_{i}"] = middleware.get_stats()
        return stats
