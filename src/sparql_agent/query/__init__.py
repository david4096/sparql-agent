"""
Query generation and validation module.

This module provides SPARQL query generation, validation, and optimization.
"""

from .prompt_engine import (
    PromptEngine,
    PromptTemplate,
    PromptContext,
    FewShotExample,
    QueryScenario,
    create_prompt_engine,
    quick_prompt
)

from .intent_parser import (
    IntentParser,
    ParsedIntent,
    Entity,
    Filter,
    Aggregation,
    OrderClause,
    QueryType,
    AggregationType,
    FilterOperator,
    OrderDirection,
    parse_query,
    classify_query
)

from .ontology_generator import (
    OntologyGuidedGenerator,
    OntologyQueryContext,
    PropertyPath,
    PropertyPathType,
    QueryConstraint,
    ExpansionStrategy,
    create_ontology_generator,
    quick_ontology_query
)

from .generator import (
    SPARQLGenerator,
    SPARQLValidator,
    GenerationStrategy,
    GenerationContext,
    QueryTemplate,
    ValidationResult,
    ConfidenceLevel,
    create_generator,
    quick_generate
)

__all__ = [
    # Prompt engine
    "PromptEngine",
    "PromptTemplate",
    "PromptContext",
    "FewShotExample",
    "QueryScenario",
    "create_prompt_engine",
    "quick_prompt",
    # Intent parser
    "IntentParser",
    "ParsedIntent",
    "Entity",
    "Filter",
    "Aggregation",
    "OrderClause",
    "QueryType",
    "AggregationType",
    "FilterOperator",
    "OrderDirection",
    "parse_query",
    "classify_query",
    # Ontology generator
    "OntologyGuidedGenerator",
    "OntologyQueryContext",
    "PropertyPath",
    "PropertyPathType",
    "QueryConstraint",
    "ExpansionStrategy",
    "create_ontology_generator",
    "quick_ontology_query",
    # SPARQL Generator
    "SPARQLGenerator",
    "SPARQLValidator",
    "GenerationStrategy",
    "GenerationContext",
    "QueryTemplate",
    "ValidationResult",
    "ConfidenceLevel",
    "create_generator",
    "quick_generate"
]
