"""
Custom exception hierarchy for the SPARQL-LLM system.

This module defines all custom exceptions used throughout the system,
organized in a hierarchical structure for better error handling and debugging.
"""


class SPARQLAgentError(Exception):
    """
    Base exception for all SPARQL-LLM system errors.

    All custom exceptions in the system inherit from this base class,
    allowing for easy catching of all system-specific errors.
    """

    def __init__(self, message: str, details: dict = None):
        """
        Initialize the exception.

        Args:
            message: Human-readable error message
            details: Additional error details as key-value pairs
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        """String representation of the error."""
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({details_str})"
        return self.message


# ============================================================================
# Endpoint Exceptions
# ============================================================================


class EndpointError(SPARQLAgentError):
    """Base exception for SPARQL endpoint-related errors."""
    pass


class EndpointConnectionError(EndpointError):
    """Raised when unable to connect to a SPARQL endpoint."""
    pass


class EndpointTimeoutError(EndpointError):
    """Raised when a SPARQL endpoint request times out."""
    pass


class EndpointAuthenticationError(EndpointError):
    """Raised when authentication to a SPARQL endpoint fails."""
    pass


class EndpointNotFoundError(EndpointError):
    """Raised when a SPARQL endpoint is not found (404)."""
    pass


class EndpointRateLimitError(EndpointError):
    """Raised when rate limit is exceeded for a SPARQL endpoint."""
    pass


class EndpointUnavailableError(EndpointError):
    """Raised when a SPARQL endpoint is temporarily unavailable."""
    pass


# ============================================================================
# Query Exceptions
# ============================================================================


class QueryError(SPARQLAgentError):
    """Base exception for SPARQL query-related errors."""
    pass


class QuerySyntaxError(QueryError):
    """Raised when a SPARQL query has syntax errors."""
    pass


class QueryValidationError(QueryError):
    """Raised when a SPARQL query fails validation."""
    pass


class QueryExecutionError(QueryError):
    """Raised when a SPARQL query execution fails."""
    pass


class QueryTimeoutError(QueryError):
    """Raised when a SPARQL query execution times out."""
    pass


class QueryResultError(QueryError):
    """Raised when there's an error processing query results."""
    pass


class QueryTooComplexError(QueryError):
    """Raised when a query is too complex to execute or generate."""
    pass


# ============================================================================
# Schema Discovery Exceptions
# ============================================================================


class SchemaError(SPARQLAgentError):
    """Base exception for schema discovery errors."""
    pass


class SchemaDiscoveryError(SchemaError):
    """Raised when schema discovery fails."""
    pass


class SchemaValidationError(SchemaError):
    """Raised when schema validation fails."""
    pass


class SchemaNotFoundError(SchemaError):
    """Raised when expected schema elements are not found."""
    pass


class SchemaIncompleteError(SchemaError):
    """Raised when discovered schema is incomplete."""
    pass


# ============================================================================
# Ontology Exceptions
# ============================================================================


class OntologyError(SPARQLAgentError):
    """Base exception for ontology-related errors."""
    pass


class OntologyLoadError(OntologyError):
    """Raised when loading an ontology fails."""
    pass


class OntologyParseError(OntologyError):
    """Raised when parsing an ontology fails."""
    pass


class OntologyValidationError(OntologyError):
    """Raised when ontology validation fails."""
    pass


class OntologyNotFoundError(OntologyError):
    """Raised when a required ontology is not found."""
    pass


class OntologyInconsistentError(OntologyError):
    """Raised when an ontology is logically inconsistent."""
    pass


class OntologyClassNotFoundError(OntologyError):
    """Raised when a required OWL class is not found in the ontology."""
    pass


class OntologyPropertyNotFoundError(OntologyError):
    """Raised when a required OWL property is not found in the ontology."""
    pass


# ============================================================================
# LLM Provider Exceptions
# ============================================================================


class LLMError(SPARQLAgentError):
    """Base exception for LLM provider errors."""
    pass


class LLMConnectionError(LLMError):
    """Raised when unable to connect to an LLM provider."""
    pass


class LLMAuthenticationError(LLMError):
    """Raised when LLM provider authentication fails."""
    pass


class LLMRateLimitError(LLMError):
    """Raised when LLM provider rate limit is exceeded."""
    pass


class LLMTimeoutError(LLMError):
    """Raised when an LLM request times out."""
    pass


class LLMResponseError(LLMError):
    """Raised when an LLM response is invalid or cannot be parsed."""
    pass


class LLMModelNotFoundError(LLMError):
    """Raised when a requested LLM model is not found or not available."""
    pass


class LLMQuotaExceededError(LLMError):
    """Raised when LLM provider quota is exceeded."""
    pass


class LLMContentFilterError(LLMError):
    """Raised when content is filtered/blocked by the LLM provider."""
    pass


# ============================================================================
# Query Generation Exceptions
# ============================================================================


class QueryGenerationError(SPARQLAgentError):
    """Base exception for query generation errors."""
    pass


class NaturalLanguageParseError(QueryGenerationError):
    """Raised when natural language input cannot be parsed."""
    pass


class QueryMappingError(QueryGenerationError):
    """Raised when mapping natural language to SPARQL fails."""
    pass


class QueryOptimizationError(QueryGenerationError):
    """Raised when query optimization fails."""
    pass


class InsufficientContextError(QueryGenerationError):
    """Raised when there's insufficient context to generate a query."""
    pass


class AmbiguousQueryError(QueryGenerationError):
    """Raised when natural language input is ambiguous."""
    pass


# ============================================================================
# Result Formatting Exceptions
# ============================================================================


class FormattingError(SPARQLAgentError):
    """Base exception for result formatting errors."""
    pass


class InvalidFormatError(FormattingError):
    """Raised when an invalid format is requested."""
    pass


class FormattingNotSupportedError(FormattingError):
    """Raised when a formatting operation is not supported."""
    pass


class SerializationError(FormattingError):
    """Raised when result serialization fails."""
    pass


class VisualizationError(FormattingError):
    """Raised when visualization generation fails."""
    pass


# ============================================================================
# Configuration Exceptions
# ============================================================================


class ConfigurationError(SPARQLAgentError):
    """Base exception for configuration errors."""
    pass


class InvalidConfigurationError(ConfigurationError):
    """Raised when configuration is invalid."""
    pass


class MissingConfigurationError(ConfigurationError):
    """Raised when required configuration is missing."""
    pass


class ConfigurationLoadError(ConfigurationError):
    """Raised when loading configuration fails."""
    pass


# ============================================================================
# Validation Exceptions
# ============================================================================


class ValidationError(SPARQLAgentError):
    """Base exception for validation errors."""
    pass


class InputValidationError(ValidationError):
    """Raised when input validation fails."""
    pass


class OutputValidationError(ValidationError):
    """Raised when output validation fails."""
    pass


class ConstraintViolationError(ValidationError):
    """Raised when a constraint is violated."""
    pass


# ============================================================================
# Resource Exceptions
# ============================================================================


class ResourceError(SPARQLAgentError):
    """Base exception for resource-related errors."""
    pass


class ResourceNotFoundError(ResourceError):
    """Raised when a required resource is not found."""
    pass


class ResourceExhaustedError(ResourceError):
    """Raised when system resources are exhausted."""
    pass


class ResourceLockedError(ResourceError):
    """Raised when a resource is locked and cannot be accessed."""
    pass


# ============================================================================
# Cache Exceptions
# ============================================================================


class CacheError(SPARQLAgentError):
    """Base exception for caching errors."""
    pass


class CacheReadError(CacheError):
    """Raised when reading from cache fails."""
    pass


class CacheWriteError(CacheError):
    """Raised when writing to cache fails."""
    pass


class CacheInvalidationError(CacheError):
    """Raised when cache invalidation fails."""
    pass
