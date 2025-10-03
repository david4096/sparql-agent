"""
SPARQL Error Handling and Query Optimization Module.

This module provides comprehensive error handling and query optimization for SPARQL queries:
- Intelligent error categorization and recovery
- User-friendly error messages with actionable suggestions
- Query optimization detection and recommendations
- Retry strategies for transient errors
- Fallback mechanisms and graceful degradation
- Performance optimization suggestions
"""

import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from urllib.parse import urlparse
import hashlib

from ..core.exceptions import (
    SPARQLAgentError,
    QueryError,
    QuerySyntaxError,
    QueryValidationError,
    QueryExecutionError,
    QueryTimeoutError,
    QueryTooComplexError,
    EndpointError,
    EndpointConnectionError,
    EndpointTimeoutError,
    EndpointAuthenticationError,
    EndpointRateLimitError,
    EndpointUnavailableError,
    EndpointNotFoundError,
)
from ..core.types import EndpointInfo, QueryResult, QueryStatus


logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Categories of SPARQL errors."""
    SYNTAX = "syntax"
    TIMEOUT = "timeout"
    MEMORY = "memory"
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    ENDPOINT_UNAVAILABLE = "endpoint_unavailable"
    QUERY_TOO_COMPLEX = "query_too_complex"
    RESOURCE_NOT_FOUND = "resource_not_found"
    PERMISSION_DENIED = "permission_denied"
    MALFORMED_RESPONSE = "malformed_response"
    UNKNOWN = "unknown"


class RetryStrategy(Enum):
    """Retry strategies for error recovery."""
    NONE = "none"
    IMMEDIATE = "immediate"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    ALTERNATIVE_ENDPOINT = "alternative_endpoint"


class OptimizationLevel(Enum):
    """Query optimization levels."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    AGGRESSIVE = "aggressive"


@dataclass
class ErrorContext:
    """
    Context information for an error.

    Attributes:
        original_error: The original exception
        category: Error category
        severity: How severe the error is (1-10)
        message: User-friendly error message
        technical_details: Technical error details
        suggestions: List of actionable suggestions
        retry_strategy: Recommended retry strategy
        is_recoverable: Whether error is recoverable
        metadata: Additional context
    """
    original_error: Exception
    category: ErrorCategory
    severity: int
    message: str
    technical_details: str
    suggestions: List[str] = field(default_factory=list)
    retry_strategy: RetryStrategy = RetryStrategy.NONE
    is_recoverable: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QueryOptimization:
    """
    Query optimization suggestion.

    Attributes:
        level: Optimization level
        issue: Description of the issue
        impact: Expected performance impact (low, medium, high)
        suggestion: How to optimize
        optimized_query: Optimized version of query (if applicable)
        estimated_improvement: Estimated performance improvement percentage
        category: Category of optimization
    """
    level: OptimizationLevel
    issue: str
    impact: str
    suggestion: str
    optimized_query: Optional[str] = None
    estimated_improvement: Optional[int] = None
    category: str = "general"


@dataclass
class RecoveryResult:
    """
    Result of error recovery attempt.

    Attributes:
        success: Whether recovery was successful
        result: Query result (if successful)
        attempts: Number of attempts made
        strategy_used: Strategy that was used
        fallback_used: Whether fallback was used
        errors_encountered: List of errors encountered
        recovery_time: Time taken for recovery
        metadata: Additional recovery metadata
    """
    success: bool
    result: Optional[QueryResult] = None
    attempts: int = 0
    strategy_used: Optional[RetryStrategy] = None
    fallback_used: bool = False
    errors_encountered: List[ErrorContext] = field(default_factory=list)
    recovery_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ErrorHandler:
    """
    Comprehensive error handler for SPARQL queries.

    Features:
    - Intelligent error categorization
    - User-friendly error messages
    - Actionable suggestions for error resolution
    - Retry strategies for transient errors
    - Fallback mechanisms
    - Pattern-based error detection
    """

    # Error patterns for categorization
    ERROR_PATTERNS = {
        ErrorCategory.SYNTAX: [
            r'syntax error',
            r'parse error',
            r'malformed query',
            r'unexpected token',
            r'expected.*but found',
        ],
        ErrorCategory.TIMEOUT: [
            r'timeout',
            r'timed out',
            r'query execution time exceeded',
            r'deadline exceeded',
        ],
        ErrorCategory.MEMORY: [
            r'out of memory',
            r'memory limit',
            r'heap space',
            r'too many results',
            r'result set too large',
        ],
        ErrorCategory.NETWORK: [
            r'connection refused',
            r'connection failed',
            r'network error',
            r'could not connect',
            r'connection reset',
            r'no route to host',
        ],
        ErrorCategory.AUTHENTICATION: [
            r'unauthorized',
            r'authentication failed',
            r'401',
            r'invalid credentials',
            r'access denied',
        ],
        ErrorCategory.RATE_LIMIT: [
            r'rate limit',
            r'429',
            r'too many requests',
            r'quota exceeded',
        ],
        ErrorCategory.ENDPOINT_UNAVAILABLE: [
            r'503',
            r'service unavailable',
            r'endpoint unavailable',
            r'temporarily unavailable',
            r'502 bad gateway',
        ],
        ErrorCategory.QUERY_TOO_COMPLEX: [
            r'query too complex',
            r'complexity limit',
            r'query depth exceeded',
            r'too many joins',
        ],
        ErrorCategory.RESOURCE_NOT_FOUND: [
            r'404',
            r'not found',
            r'no such resource',
        ],
        ErrorCategory.PERMISSION_DENIED: [
            r'403',
            r'forbidden',
            r'permission denied',
            r'access forbidden',
        ],
        ErrorCategory.MALFORMED_RESPONSE: [
            r'malformed response',
            r'invalid response',
            r'corrupt data',
            r'cannot parse response',
        ],
    }

    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        enable_fallback: bool = True,
        enable_optimization_suggestions: bool = True,
    ):
        """
        Initialize error handler.

        Args:
            max_retries: Maximum number of retry attempts
            retry_delay: Initial retry delay in seconds
            enable_fallback: Enable fallback mechanisms
            enable_optimization_suggestions: Enable query optimization suggestions
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.enable_fallback = enable_fallback
        self.enable_optimization_suggestions = enable_optimization_suggestions

        # Statistics
        self.stats = {
            "total_errors": 0,
            "errors_by_category": {},
            "successful_recoveries": 0,
            "failed_recoveries": 0,
            "retry_counts": {},
        }

    def categorize_error(self, error: Exception, query: str = "", endpoint: Optional[EndpointInfo] = None) -> ErrorContext:
        """
        Categorize an error and create context with suggestions.

        Args:
            error: The exception to categorize
            query: The SPARQL query that caused the error
            endpoint: Endpoint information

        Returns:
            ErrorContext with categorization and suggestions
        """
        self.stats["total_errors"] += 1

        error_str = str(error).lower()
        error_type = type(error).__name__

        # Determine category
        category = self._determine_category(error, error_str)

        # Update statistics
        self.stats["errors_by_category"][category.value] = \
            self.stats["errors_by_category"].get(category.value, 0) + 1

        # Build context based on category
        context = self._build_error_context(error, category, error_str, error_type, query, endpoint)

        logger.debug(f"Categorized error as {category.value}: {context.message}")

        return context

    def _determine_category(self, error: Exception, error_str: str) -> ErrorCategory:
        """Determine error category from exception and message."""
        # Check exception type first
        if isinstance(error, QuerySyntaxError):
            return ErrorCategory.SYNTAX
        elif isinstance(error, QueryTimeoutError) or isinstance(error, EndpointTimeoutError):
            return ErrorCategory.TIMEOUT
        elif isinstance(error, EndpointAuthenticationError):
            return ErrorCategory.AUTHENTICATION
        elif isinstance(error, EndpointRateLimitError):
            return ErrorCategory.RATE_LIMIT
        elif isinstance(error, EndpointUnavailableError):
            return ErrorCategory.ENDPOINT_UNAVAILABLE
        elif isinstance(error, EndpointNotFoundError):
            return ErrorCategory.RESOURCE_NOT_FOUND
        elif isinstance(error, EndpointConnectionError):
            return ErrorCategory.NETWORK
        elif isinstance(error, QueryTooComplexError):
            return ErrorCategory.QUERY_TOO_COMPLEX

        # Check error message patterns
        for category, patterns in self.ERROR_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, error_str, re.IGNORECASE):
                    return category

        return ErrorCategory.UNKNOWN

    def _build_error_context(
        self,
        error: Exception,
        category: ErrorCategory,
        error_str: str,
        error_type: str,
        query: str,
        endpoint: Optional[EndpointInfo],
    ) -> ErrorContext:
        """Build detailed error context with suggestions."""
        context = ErrorContext(
            original_error=error,
            category=category,
            severity=5,
            message="",
            technical_details=f"{error_type}: {str(error)}",
        )

        # Build category-specific context
        if category == ErrorCategory.SYNTAX:
            self._handle_syntax_error(context, error, query)
        elif category == ErrorCategory.TIMEOUT:
            self._handle_timeout_error(context, error, query, endpoint)
        elif category == ErrorCategory.MEMORY:
            self._handle_memory_error(context, error, query)
        elif category == ErrorCategory.NETWORK:
            self._handle_network_error(context, error, endpoint)
        elif category == ErrorCategory.AUTHENTICATION:
            self._handle_authentication_error(context, error, endpoint)
        elif category == ErrorCategory.RATE_LIMIT:
            self._handle_rate_limit_error(context, error, endpoint)
        elif category == ErrorCategory.ENDPOINT_UNAVAILABLE:
            self._handle_unavailable_error(context, error, endpoint)
        elif category == ErrorCategory.QUERY_TOO_COMPLEX:
            self._handle_complexity_error(context, error, query)
        elif category == ErrorCategory.RESOURCE_NOT_FOUND:
            self._handle_not_found_error(context, error, endpoint)
        elif category == ErrorCategory.PERMISSION_DENIED:
            self._handle_permission_error(context, error, endpoint)
        elif category == ErrorCategory.MALFORMED_RESPONSE:
            self._handle_malformed_response_error(context, error)
        else:
            self._handle_unknown_error(context, error)

        return context

    def _handle_syntax_error(self, context: ErrorContext, error: Exception, query: str):
        """Handle syntax errors."""
        context.severity = 3
        context.message = "Your SPARQL query has a syntax error"
        context.is_recoverable = True
        context.retry_strategy = RetryStrategy.NONE

        # Extract specific syntax issue if available
        if hasattr(error, 'details'):
            details = error.details
            if 'line' in details:
                context.message += f" at line {details['line']}"
            if 'suggestion' in details:
                context.suggestions.append(details['suggestion'])

        # Common syntax issue suggestions
        context.suggestions.extend([
            "Check for missing or extra punctuation (dots, semicolons, commas)",
            "Verify all PREFIX declarations are correct",
            "Ensure all brackets {} [] () are properly balanced",
            "Confirm variable names start with ? or $",
            "Validate URI syntax - URIs should be in <angle brackets>",
        ])

        # Check for common mistakes
        if 'prefix' in str(error).lower():
            context.suggestions.insert(0, "Check that all prefixes are declared before use")
        if 'bracket' in str(error).lower() or 'brace' in str(error).lower():
            context.suggestions.insert(0, "Check for unbalanced brackets or braces")

    def _handle_timeout_error(
        self,
        context: ErrorContext,
        error: Exception,
        query: str,
        endpoint: Optional[EndpointInfo],
    ):
        """Handle timeout errors with pagination suggestions."""
        context.severity = 6
        context.message = "Query execution timed out"
        context.is_recoverable = True
        context.retry_strategy = RetryStrategy.EXPONENTIAL_BACKOFF

        if endpoint and endpoint.timeout:
            context.message += f" (timeout: {endpoint.timeout}s)"

        # Analyze query for optimization
        optimizations = self._analyze_query_performance(query)

        context.suggestions = [
            "Add or reduce LIMIT clause to fetch fewer results",
            "Use pagination with LIMIT and OFFSET for large result sets",
            "Add more specific FILTER conditions to narrow results",
            "Consider breaking complex query into smaller queries",
            "Check if endpoint supports longer timeout values",
        ]

        # Add specific suggestions based on query analysis
        if not re.search(r'\bLIMIT\b', query, re.IGNORECASE):
            context.suggestions.insert(0, "Add LIMIT clause (e.g., LIMIT 1000) to prevent fetching all results")
            context.metadata["suggested_limit"] = 1000

        if len(re.findall(r'\bOPTIONAL\b', query, re.IGNORECASE)) > 3:
            context.suggestions.append("Too many OPTIONAL clauses can slow queries - consider if all are necessary")

        if re.search(r'\*\s+\*\s+\*', query):
            context.suggestions.append("Avoid triple wildcards (?s ?p ?o) - be more specific")

        # Add optimization suggestions
        for opt in optimizations:
            if opt.impact == "high":
                context.suggestions.append(opt.suggestion)

    def _handle_memory_error(self, context: ErrorContext, error: Exception, query: str):
        """Handle memory/result size errors."""
        context.severity = 7
        context.message = "Query result set is too large or memory limit exceeded"
        context.is_recoverable = True
        context.retry_strategy = RetryStrategy.NONE

        context.suggestions = [
            "Add LIMIT clause to fetch results in smaller batches",
            "Use OFFSET with LIMIT for pagination through large results",
            "Add more selective FILTER conditions",
            "Remove DISTINCT if not necessary (it requires buffering all results)",
            "Simplify SELECT clause to return fewer variables",
            "Consider using ASK query if you only need yes/no answer",
            "Use COUNT(*) instead of fetching all results if you just need count",
        ]

        # Detect if query lacks LIMIT
        if not re.search(r'\bLIMIT\b', query, re.IGNORECASE):
            context.suggestions.insert(0, "CRITICAL: Add LIMIT clause immediately (e.g., LIMIT 1000)")
            context.metadata["critical_fix"] = "add_limit"
            context.metadata["suggested_limit"] = 1000

    def _handle_network_error(
        self,
        context: ErrorContext,
        error: Exception,
        endpoint: Optional[EndpointInfo],
    ):
        """Handle network/connection errors."""
        context.severity = 7
        context.message = "Failed to connect to SPARQL endpoint"
        context.is_recoverable = True
        context.retry_strategy = RetryStrategy.EXPONENTIAL_BACKOFF

        if endpoint:
            context.message += f": {endpoint.url}"

        context.suggestions = [
            "Check your internet connection",
            "Verify the endpoint URL is correct",
            "Check if endpoint is currently available",
            "Try again in a few moments - may be temporary network issue",
            "Check for firewall or proxy settings blocking connection",
        ]

        if endpoint:
            context.metadata["endpoint_url"] = endpoint.url
            context.metadata["can_retry"] = True

    def _handle_authentication_error(
        self,
        context: ErrorContext,
        error: Exception,
        endpoint: Optional[EndpointInfo],
    ):
        """Handle authentication errors."""
        context.severity = 8
        context.message = "Authentication failed"
        context.is_recoverable = False
        context.retry_strategy = RetryStrategy.NONE

        context.suggestions = [
            "Verify your username and password are correct",
            "Check if authentication credentials have expired",
            "Confirm you have permission to access this endpoint",
            "Check if endpoint requires API key or token authentication",
            "Contact endpoint administrator if problem persists",
        ]

        if endpoint and endpoint.authentication_required:
            context.suggestions.insert(0, "This endpoint requires authentication - provide valid credentials")

    def _handle_rate_limit_error(
        self,
        context: ErrorContext,
        error: Exception,
        endpoint: Optional[EndpointInfo],
    ):
        """Handle rate limit errors."""
        context.severity = 6
        context.message = "Rate limit exceeded"
        context.is_recoverable = True
        context.retry_strategy = RetryStrategy.LINEAR_BACKOFF

        # Try to extract retry-after header
        retry_after = None
        if hasattr(error, 'details') and 'retry_after' in error.details:
            retry_after = error.details['retry_after']
            context.metadata["retry_after"] = retry_after

        if retry_after:
            context.suggestions = [
                f"Wait {retry_after} seconds before retrying",
                "Reduce query frequency",
                "Consider batching multiple queries",
            ]
        else:
            context.suggestions = [
                "Wait a few minutes before retrying",
                "Reduce query frequency to stay within rate limits",
                "Check endpoint documentation for rate limit details",
                "Consider caching results to reduce query frequency",
                "Contact endpoint provider about rate limit increases",
            ]

    def _handle_unavailable_error(
        self,
        context: ErrorContext,
        error: Exception,
        endpoint: Optional[EndpointInfo],
    ):
        """Handle endpoint unavailable errors."""
        context.severity = 7
        context.message = "SPARQL endpoint is temporarily unavailable"
        context.is_recoverable = True
        context.retry_strategy = RetryStrategy.EXPONENTIAL_BACKOFF

        context.suggestions = [
            "Wait a few minutes and try again",
            "Check endpoint status page if available",
            "Use alternative endpoint if available",
            "Enable fallback to alternative endpoints",
            "Contact endpoint administrator if prolonged outage",
        ]

        context.metadata["can_retry"] = True
        context.metadata["suggest_fallback"] = self.enable_fallback

    def _handle_complexity_error(self, context: ErrorContext, error: Exception, query: str):
        """Handle query too complex errors."""
        context.severity = 6
        context.message = "Query is too complex for endpoint to process"
        context.is_recoverable = True
        context.retry_strategy = RetryStrategy.NONE

        context.suggestions = [
            "Simplify query by removing unnecessary OPTIONAL clauses",
            "Break complex query into multiple simpler queries",
            "Reduce number of UNION clauses",
            "Add more specific FILTER conditions earlier in query",
            "Limit depth of nested subqueries",
            "Remove complex FILTER expressions",
        ]

        # Analyze query complexity
        optional_count = len(re.findall(r'\bOPTIONAL\b', query, re.IGNORECASE))
        union_count = len(re.findall(r'\bUNION\b', query, re.IGNORECASE))

        if optional_count > 5:
            context.suggestions.insert(0, f"Query has {optional_count} OPTIONAL clauses - try reducing to fewer")
        if union_count > 3:
            context.suggestions.insert(0, f"Query has {union_count} UNION clauses - consider breaking into separate queries")

    def _handle_not_found_error(
        self,
        context: ErrorContext,
        error: Exception,
        endpoint: Optional[EndpointInfo],
    ):
        """Handle resource not found errors."""
        context.severity = 5
        context.message = "Endpoint or resource not found"
        context.is_recoverable = False
        context.retry_strategy = RetryStrategy.NONE

        context.suggestions = [
            "Verify the endpoint URL is correct",
            "Check if endpoint has moved to new URL",
            "Confirm endpoint is still active and maintained",
            "Check endpoint documentation for current URL",
        ]

        if endpoint:
            parsed = urlparse(endpoint.url)
            context.suggestions.append(f"Double-check URL: {endpoint.url}")

    def _handle_permission_error(
        self,
        context: ErrorContext,
        error: Exception,
        endpoint: Optional[EndpointInfo],
    ):
        """Handle permission denied errors."""
        context.severity = 7
        context.message = "Permission denied - you don't have access to this resource"
        context.is_recoverable = False
        context.retry_strategy = RetryStrategy.NONE

        context.suggestions = [
            "Verify you have necessary permissions",
            "Check if authentication is required",
            "Contact endpoint administrator to request access",
            "Confirm you're accessing the correct endpoint",
        ]

    def _handle_malformed_response_error(self, context: ErrorContext, error: Exception):
        """Handle malformed response errors."""
        context.severity = 6
        context.message = "Received malformed response from endpoint"
        context.is_recoverable = True
        context.retry_strategy = RetryStrategy.IMMEDIATE

        context.suggestions = [
            "Retry query - may be temporary endpoint issue",
            "Try different result format (JSON, XML, CSV)",
            "Check if endpoint is functioning correctly",
            "Report issue to endpoint administrator",
        ]

    def _handle_unknown_error(self, context: ErrorContext, error: Exception):
        """Handle unknown/uncategorized errors."""
        context.severity = 5
        context.message = f"An unexpected error occurred: {type(error).__name__}"
        context.is_recoverable = True
        context.retry_strategy = RetryStrategy.IMMEDIATE

        context.suggestions = [
            "Check error details for more information",
            "Verify query syntax is correct",
            "Try simpler version of query",
            "Check endpoint status and availability",
            "Report issue if problem persists",
        ]

    def recover_from_error(
        self,
        error: Exception,
        query: str,
        endpoint: EndpointInfo,
        execute_func: Callable,
        alternative_endpoints: Optional[List[EndpointInfo]] = None,
    ) -> RecoveryResult:
        """
        Attempt to recover from an error using appropriate strategy.

        Args:
            error: The exception to recover from
            query: Original query
            endpoint: Original endpoint
            execute_func: Function to execute query
            alternative_endpoints: Alternative endpoints for fallback

        Returns:
            RecoveryResult with recovery status and result
        """
        start_time = time.time()

        # Categorize error
        context = self.categorize_error(error, query, endpoint)

        result = RecoveryResult(
            success=False,
            errors_encountered=[context],
        )

        # Check if recoverable
        if not context.is_recoverable:
            logger.info(f"Error is not recoverable: {context.message}")
            result.recovery_time = time.time() - start_time
            self.stats["failed_recoveries"] += 1
            return result

        # Attempt recovery based on strategy
        if context.retry_strategy == RetryStrategy.IMMEDIATE:
            result = self._retry_immediate(query, endpoint, execute_func, result)
        elif context.retry_strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            result = self._retry_exponential_backoff(query, endpoint, execute_func, result)
        elif context.retry_strategy == RetryStrategy.LINEAR_BACKOFF:
            result = self._retry_linear_backoff(query, endpoint, execute_func, result)

        # Try alternative endpoints if enabled and available
        if not result.success and self.enable_fallback and alternative_endpoints:
            result = self._try_alternative_endpoints(
                query, alternative_endpoints, execute_func, result
            )

        # Try query optimization as last resort
        if not result.success and self.enable_optimization_suggestions:
            result = self._try_optimized_query(query, endpoint, execute_func, result, context)

        result.recovery_time = time.time() - start_time

        # Update statistics
        if result.success:
            self.stats["successful_recoveries"] += 1
        else:
            self.stats["failed_recoveries"] += 1

        self.stats["retry_counts"][result.attempts] = \
            self.stats["retry_counts"].get(result.attempts, 0) + 1

        return result

    def _retry_immediate(
        self,
        query: str,
        endpoint: EndpointInfo,
        execute_func: Callable,
        result: RecoveryResult,
    ) -> RecoveryResult:
        """Retry immediately once."""
        logger.info("Attempting immediate retry")
        result.strategy_used = RetryStrategy.IMMEDIATE

        try:
            result.attempts += 1
            query_result = execute_func(query, endpoint)
            result.success = True
            result.result = query_result
            logger.info("Immediate retry succeeded")
        except Exception as e:
            context = self.categorize_error(e, query, endpoint)
            result.errors_encountered.append(context)
            logger.info("Immediate retry failed")

        return result

    def _retry_exponential_backoff(
        self,
        query: str,
        endpoint: EndpointInfo,
        execute_func: Callable,
        result: RecoveryResult,
    ) -> RecoveryResult:
        """Retry with exponential backoff."""
        logger.info("Attempting retry with exponential backoff")
        result.strategy_used = RetryStrategy.EXPONENTIAL_BACKOFF

        delay = self.retry_delay

        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    logger.info(f"Waiting {delay:.1f}s before retry attempt {attempt + 1}")
                    time.sleep(delay)

                result.attempts += 1
                query_result = execute_func(query, endpoint)
                result.success = True
                result.result = query_result
                logger.info(f"Retry succeeded on attempt {attempt + 1}")
                break
            except Exception as e:
                context = self.categorize_error(e, query, endpoint)
                result.errors_encountered.append(context)
                logger.info(f"Retry attempt {attempt + 1} failed")

                # Exponential backoff
                delay *= 2

        return result

    def _retry_linear_backoff(
        self,
        query: str,
        endpoint: EndpointInfo,
        execute_func: Callable,
        result: RecoveryResult,
    ) -> RecoveryResult:
        """Retry with linear backoff."""
        logger.info("Attempting retry with linear backoff")
        result.strategy_used = RetryStrategy.LINEAR_BACKOFF

        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    delay = self.retry_delay * (attempt + 1)
                    logger.info(f"Waiting {delay:.1f}s before retry attempt {attempt + 1}")
                    time.sleep(delay)

                result.attempts += 1
                query_result = execute_func(query, endpoint)
                result.success = True
                result.result = query_result
                logger.info(f"Retry succeeded on attempt {attempt + 1}")
                break
            except Exception as e:
                context = self.categorize_error(e, query, endpoint)
                result.errors_encountered.append(context)
                logger.info(f"Retry attempt {attempt + 1} failed")

        return result

    def _try_alternative_endpoints(
        self,
        query: str,
        endpoints: List[EndpointInfo],
        execute_func: Callable,
        result: RecoveryResult,
    ) -> RecoveryResult:
        """Try alternative endpoints."""
        logger.info(f"Trying {len(endpoints)} alternative endpoints")
        result.fallback_used = True

        for i, endpoint in enumerate(endpoints, 1):
            try:
                logger.info(f"Trying alternative endpoint {i}: {endpoint.url}")
                result.attempts += 1
                query_result = execute_func(query, endpoint)
                result.success = True
                result.result = query_result
                result.metadata["fallback_endpoint"] = endpoint.url
                logger.info(f"Alternative endpoint {i} succeeded")
                break
            except Exception as e:
                context = self.categorize_error(e, query, endpoint)
                result.errors_encountered.append(context)
                logger.info(f"Alternative endpoint {i} failed")

        return result

    def _try_optimized_query(
        self,
        query: str,
        endpoint: EndpointInfo,
        execute_func: Callable,
        result: RecoveryResult,
        original_context: ErrorContext,
    ) -> RecoveryResult:
        """Try executing optimized version of query."""
        logger.info("Attempting query optimization")

        # Auto-optimize based on error type
        optimized_query = self._auto_optimize_query(query, original_context)

        if optimized_query and optimized_query != query:
            try:
                logger.info("Trying optimized query")
                result.attempts += 1
                query_result = execute_func(optimized_query, endpoint)
                result.success = True
                result.result = query_result
                result.metadata["query_optimized"] = True
                result.metadata["original_query"] = query
                result.metadata["optimized_query"] = optimized_query
                logger.info("Optimized query succeeded")
            except Exception as e:
                context = self.categorize_error(e, optimized_query, endpoint)
                result.errors_encountered.append(context)
                logger.info("Optimized query failed")

        return result

    def _auto_optimize_query(self, query: str, context: ErrorContext) -> Optional[str]:
        """Automatically optimize query based on error context."""
        optimized = query

        # Add LIMIT for timeout/memory errors
        if context.category in [ErrorCategory.TIMEOUT, ErrorCategory.MEMORY]:
            if not re.search(r'\bLIMIT\b', optimized, re.IGNORECASE):
                # Add LIMIT before any ORDER BY or at end
                if 'ORDER BY' in optimized.upper():
                    optimized = re.sub(
                        r'(ORDER\s+BY\s+[^\}]+)',
                        r'\1 LIMIT 1000',
                        optimized,
                        flags=re.IGNORECASE
                    )
                else:
                    optimized = optimized.rstrip() + " LIMIT 1000"

                logger.info("Added LIMIT 1000 to query")

        return optimized if optimized != query else None

    def _analyze_query_performance(self, query: str) -> List[QueryOptimization]:
        """Analyze query for performance issues and optimization opportunities."""
        optimizations = []

        # Check for LIMIT clause
        if not re.search(r'\bLIMIT\b', query, re.IGNORECASE):
            optimizations.append(QueryOptimization(
                level=OptimizationLevel.HIGH,
                issue="No LIMIT clause",
                impact="high",
                suggestion="Add LIMIT clause to prevent fetching excessive results",
                category="pagination",
                estimated_improvement=50,
            ))

        # Check for SELECT *
        if re.search(r'SELECT\s+\*', query, re.IGNORECASE):
            optimizations.append(QueryOptimization(
                level=OptimizationLevel.MEDIUM,
                issue="Using SELECT *",
                impact="medium",
                suggestion="Select only needed variables instead of *",
                category="projection",
                estimated_improvement=20,
            ))

        # Check for excessive OPTIONAL clauses
        optional_count = len(re.findall(r'\bOPTIONAL\b', query, re.IGNORECASE))
        if optional_count > 3:
            optimizations.append(QueryOptimization(
                level=OptimizationLevel.HIGH,
                issue=f"Too many OPTIONAL clauses ({optional_count})",
                impact="high",
                suggestion="Reduce number of OPTIONAL clauses or split into multiple queries",
                category="complexity",
                estimated_improvement=40,
            ))

        # Check for DISTINCT with large results
        if re.search(r'SELECT\s+DISTINCT', query, re.IGNORECASE):
            if not re.search(r'\bLIMIT\b', query, re.IGNORECASE):
                optimizations.append(QueryOptimization(
                    level=OptimizationLevel.MEDIUM,
                    issue="DISTINCT without LIMIT",
                    impact="medium",
                    suggestion="DISTINCT requires buffering - add LIMIT or remove if not necessary",
                    category="memory",
                    estimated_improvement=30,
                ))

        # Check for ORDER BY without LIMIT
        if re.search(r'\bORDER\s+BY\b', query, re.IGNORECASE):
            if not re.search(r'\bLIMIT\b', query, re.IGNORECASE):
                optimizations.append(QueryOptimization(
                    level=OptimizationLevel.MEDIUM,
                    issue="ORDER BY without LIMIT",
                    impact="medium",
                    suggestion="ORDER BY requires sorting all results - add LIMIT",
                    category="sorting",
                    estimated_improvement=25,
                ))

        # Check for triple wildcards
        if re.search(r'\?\w+\s+\?\w+\s+\?\w+', query):
            optimizations.append(QueryOptimization(
                level=OptimizationLevel.HIGH,
                issue="Triple wildcard pattern detected",
                impact="high",
                suggestion="Make at least one part of triple pattern more specific",
                category="pattern",
                estimated_improvement=60,
            ))

        # Check for FILTER placement
        filter_matches = list(re.finditer(r'\bFILTER\b', query, re.IGNORECASE))
        if filter_matches:
            # Check if FILTERs come late in query
            query_pos = len(query)
            for match in filter_matches:
                if match.start() > query_pos * 0.7:
                    optimizations.append(QueryOptimization(
                        level=OptimizationLevel.MEDIUM,
                        issue="FILTER clause appears late in query",
                        impact="medium",
                        suggestion="Move FILTER clauses earlier to reduce intermediate results",
                        category="filter_placement",
                        estimated_improvement=25,
                    ))
                    break

        # Check for regex FILTER
        if re.search(r'FILTER\s*\(\s*regex', query, re.IGNORECASE):
            optimizations.append(QueryOptimization(
                level=OptimizationLevel.LOW,
                issue="Using regex in FILTER",
                impact="low",
                suggestion="Regex can be slow - use exact matches when possible",
                category="filter_performance",
                estimated_improvement=15,
            ))

        # Check for nested subqueries
        subquery_count = len(re.findall(r'\{\s*SELECT', query, re.IGNORECASE))
        if subquery_count > 2:
            optimizations.append(QueryOptimization(
                level=OptimizationLevel.MEDIUM,
                issue=f"Multiple nested subqueries ({subquery_count})",
                impact="medium",
                suggestion="Consider flattening nested subqueries for better performance",
                category="complexity",
                estimated_improvement=30,
            ))

        return optimizations

    def suggest_optimizations(self, query: str) -> List[QueryOptimization]:
        """
        Analyze query and suggest optimizations.

        Args:
            query: SPARQL query to analyze

        Returns:
            List of optimization suggestions
        """
        return self._analyze_query_performance(query)

    def optimize_query(self, query: str, level: OptimizationLevel = OptimizationLevel.MEDIUM) -> str:
        """
        Automatically optimize a query.

        Args:
            query: Original query
            level: Optimization level

        Returns:
            Optimized query
        """
        optimized = query

        if level == OptimizationLevel.NONE:
            return optimized

        # Level: LOW - Basic optimizations
        if level.value in ["low", "medium", "high", "aggressive"]:
            # Add LIMIT if missing
            if not re.search(r'\bLIMIT\b', optimized, re.IGNORECASE):
                optimized = optimized.rstrip() + " LIMIT 10000"

        # Level: MEDIUM - More aggressive optimizations
        if level.value in ["medium", "high", "aggressive"]:
            # Replace SELECT * with explicit variables (if we can detect them)
            # This is complex, so just suggest for now
            pass

        # Level: HIGH - Aggressive optimizations
        if level.value in ["high", "aggressive"]:
            # Reduce LIMIT if it's very high
            limit_match = re.search(r'LIMIT\s+(\d+)', optimized, re.IGNORECASE)
            if limit_match and int(limit_match.group(1)) > 10000:
                optimized = re.sub(
                    r'LIMIT\s+\d+',
                    'LIMIT 10000',
                    optimized,
                    flags=re.IGNORECASE
                )

        # Level: AGGRESSIVE - Maximum optimizations
        if level == OptimizationLevel.AGGRESSIVE:
            # Add timeout hints if supported
            # This is endpoint-specific
            pass

        return optimized

    def get_statistics(self) -> Dict[str, Any]:
        """Get error handler statistics."""
        total_attempts = self.stats["successful_recoveries"] + self.stats["failed_recoveries"]
        recovery_rate = (
            self.stats["successful_recoveries"] / total_attempts * 100
            if total_attempts > 0
            else 0
        )

        return {
            **self.stats,
            "recovery_rate": f"{recovery_rate:.1f}%",
            "total_recovery_attempts": total_attempts,
        }

    def format_error_report(self, context: ErrorContext) -> str:
        """
        Format a user-friendly error report.

        Args:
            context: Error context

        Returns:
            Formatted error report
        """
        lines = []

        lines.append("=" * 70)
        lines.append(f"ERROR: {context.message}")
        lines.append("=" * 70)
        lines.append("")

        lines.append(f"Category: {context.category.value}")
        lines.append(f"Severity: {context.severity}/10")
        lines.append(f"Recoverable: {'Yes' if context.is_recoverable else 'No'}")
        lines.append("")

        if context.suggestions:
            lines.append("SUGGESTIONS:")
            for i, suggestion in enumerate(context.suggestions, 1):
                lines.append(f"  {i}. {suggestion}")
            lines.append("")

        if context.retry_strategy != RetryStrategy.NONE:
            lines.append(f"Recommended Action: {context.retry_strategy.value}")
            lines.append("")

        lines.append("Technical Details:")
        lines.append(f"  {context.technical_details}")
        lines.append("")

        lines.append("=" * 70)

        return "\n".join(lines)


# Convenience functions

def handle_query_error(
    error: Exception,
    query: str,
    endpoint: Optional[EndpointInfo] = None,
) -> ErrorContext:
    """
    Quick function to handle and categorize a query error.

    Args:
        error: The exception
        query: SPARQL query
        endpoint: Endpoint info

    Returns:
        ErrorContext with suggestions
    """
    handler = ErrorHandler()
    return handler.categorize_error(error, query, endpoint)


def get_error_suggestions(error: Exception, query: str = "") -> List[str]:
    """
    Get actionable suggestions for an error.

    Args:
        error: The exception
        query: SPARQL query

    Returns:
        List of suggestions
    """
    context = handle_query_error(error, query)
    return context.suggestions


def optimize_query(query: str) -> Tuple[str, List[QueryOptimization]]:
    """
    Optimize a query and return suggestions.

    Args:
        query: SPARQL query

    Returns:
        Tuple of (optimized_query, optimization_suggestions)
    """
    handler = ErrorHandler()
    optimizations = handler.suggest_optimizations(query)
    optimized = handler.optimize_query(query, OptimizationLevel.MEDIUM)
    return optimized, optimizations
