"""
Query execution module.

This module provides SPARQL query execution and endpoint management.
"""

from .validator import (
    QueryValidator,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
    validate_query,
    validate_and_raise,
)
from .executor import (
    QueryExecutor,
    ResultFormat,
    BindingType,
    Binding,
    ExecutionMetrics,
    FederatedQuery,
    ConnectionPool,
    ResultParser,
    StreamingResultIterator,
    execute_query,
    execute_query_with_validation,
    execute_federated_query,
)
from .error_handler import (
    ErrorHandler,
    ErrorCategory,
    ErrorContext,
    RetryStrategy,
    OptimizationLevel,
    QueryOptimization,
    RecoveryResult,
    handle_query_error,
    get_error_suggestions,
    optimize_query,
)

__all__ = [
    # Validation
    'QueryValidator',
    'ValidationIssue',
    'ValidationResult',
    'ValidationSeverity',
    'validate_query',
    'validate_and_raise',
    # Execution
    'QueryExecutor',
    'ResultFormat',
    'BindingType',
    'Binding',
    'ExecutionMetrics',
    'FederatedQuery',
    'ConnectionPool',
    'ResultParser',
    'StreamingResultIterator',
    'execute_query',
    'execute_query_with_validation',
    'execute_federated_query',
    # Error Handling
    'ErrorHandler',
    'ErrorCategory',
    'ErrorContext',
    'RetryStrategy',
    'OptimizationLevel',
    'QueryOptimization',
    'RecoveryResult',
    'handle_query_error',
    'get_error_suggestions',
    'optimize_query',
]
