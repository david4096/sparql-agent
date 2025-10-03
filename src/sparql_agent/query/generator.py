"""
Context-Aware SPARQL Query Generation Module.

This module provides sophisticated SPARQL query generation capabilities including:
- Template-based generation for simple queries
- LLM-based generation for complex queries
- Hybrid generation with validation
- Context-aware query construction using schema and ontology information
- Multi-dataset and federated query support
- Automatic syntax validation and optimization
- Missing prefix detection and addition
- Query quality assessment

Example:
    >>> from sparql_agent.query import SPARQLGenerator
    >>> from sparql_agent.core.types import SchemaInfo, OntologyInfo
    >>>
    >>> generator = SPARQLGenerator(llm_client=client)
    >>> result = generator.generate(
    ...     "Find all proteins from human",
    ...     schema_info=schema,
    ...     ontology_info=ontology
    ... )
    >>> print(result.query)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import re
import logging
from pathlib import Path
import time

from ..core.types import (
    SchemaInfo,
    OntologyInfo,
    GeneratedQuery,
    EndpointInfo,
)
from ..core.exceptions import (
    QueryGenerationError,
    NaturalLanguageParseError,
    QueryMappingError,
    InsufficientContextError,
    AmbiguousQueryError,
    QuerySyntaxError,
    QueryValidationError,
)
from ..llm.client import LLMClient, LLMRequest, LLMResponse, ProviderManager
from .prompt_engine import (
    PromptEngine,
    PromptContext,
    QueryScenario,
    PromptTemplate,
)
from ..schema.ontology_mapper import OntologyMapper


logger = logging.getLogger(__name__)


class GenerationStrategy(Enum):
    """Strategy for SPARQL query generation."""
    TEMPLATE = "template"
    LLM = "llm"
    HYBRID = "hybrid"
    AUTO = "auto"


class ConfidenceLevel(Enum):
    """Confidence level for generated queries."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNCERTAIN = "uncertain"


@dataclass
class QueryTemplate:
    """
    Template for common SPARQL query patterns.

    Attributes:
        name: Template name
        pattern: Natural language pattern to match
        sparql_template: SPARQL query template with placeholders
        required_context: Required context elements (classes, properties)
        scenario: Query scenario type
        confidence: Base confidence score
        examples: Example uses of this template
    """
    name: str
    pattern: str
    sparql_template: str
    required_context: List[str] = field(default_factory=list)
    scenario: QueryScenario = QueryScenario.BASIC
    confidence: float = 0.8
    examples: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class GenerationContext:
    """
    Context for SPARQL query generation.

    Attributes:
        natural_language: User's natural language query
        schema_info: Schema information from endpoint
        ontology_info: Ontology information
        endpoint_info: Endpoint configuration
        available_prefixes: Available namespace prefixes
        scenario: Query scenario (auto-detected or specified)
        strategy: Generation strategy to use
        constraints: Query constraints (limit, timeout, etc.)
        examples: Relevant example queries
        vocabulary_hints: Vocabulary usage hints
        cross_references: Cross-reference information for multi-dataset queries
    """
    natural_language: str
    schema_info: Optional[SchemaInfo] = None
    ontology_info: Optional[OntologyInfo] = None
    endpoint_info: Optional[EndpointInfo] = None
    available_prefixes: Dict[str, str] = field(default_factory=dict)
    scenario: Optional[QueryScenario] = None
    strategy: GenerationStrategy = GenerationStrategy.AUTO
    constraints: Dict[str, Any] = field(default_factory=dict)
    examples: List[Dict[str, str]] = field(default_factory=list)
    vocabulary_hints: Dict[str, List[str]] = field(default_factory=dict)
    cross_references: Dict[str, str] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """
    Result of query validation.

    Attributes:
        is_valid: Whether query is syntactically valid
        syntax_errors: List of syntax errors
        warnings: List of warnings
        suggestions: List of optimization suggestions
        missing_prefixes: Missing prefix declarations
        detected_prefixes: Prefixes detected in query
        complexity_score: Query complexity (0-10)
    """
    is_valid: bool
    syntax_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    missing_prefixes: Dict[str, str] = field(default_factory=dict)
    detected_prefixes: Set[str] = field(default_factory=set)
    complexity_score: float = 0.0


class SPARQLValidator:
    """
    Validates and analyzes SPARQL queries.

    Provides syntax checking, prefix detection, complexity analysis,
    and optimization suggestions.
    """

    def __init__(self, ontology_mapper: Optional[OntologyMapper] = None):
        """
        Initialize SPARQL validator.

        Args:
            ontology_mapper: Optional ontology mapper for prefix resolution
        """
        self.ontology_mapper = ontology_mapper or OntologyMapper()
        self._init_patterns()

    def _init_patterns(self):
        """Initialize regex patterns for SPARQL analysis."""
        # SPARQL keywords
        self.sparql_keywords = {
            'SELECT', 'CONSTRUCT', 'ASK', 'DESCRIBE', 'INSERT', 'DELETE',
            'WHERE', 'OPTIONAL', 'FILTER', 'UNION', 'MINUS', 'BIND',
            'SERVICE', 'GRAPH', 'VALUES', 'GROUP', 'ORDER', 'LIMIT',
            'OFFSET', 'DISTINCT', 'REDUCED', 'FROM', 'NAMED'
        }

        # Pattern for PREFIX declarations
        self.prefix_pattern = re.compile(
            r'PREFIX\s+(\w+):\s*<([^>]+)>',
            re.IGNORECASE
        )

        # Pattern for prefixed names in query
        self.prefixed_name_pattern = re.compile(r'\b(\w+):(\w+)')

        # Pattern for URIs
        self.uri_pattern = re.compile(r'<([^>]+)>')

        # Pattern for variables
        self.variable_pattern = re.compile(r'[\?\$](\w+)')

    def validate(self, query: str, context: Optional[GenerationContext] = None) -> ValidationResult:
        """
        Validate a SPARQL query.

        Args:
            query: SPARQL query string
            context: Optional generation context for enhanced validation

        Returns:
            ValidationResult with validation details
        """
        result = ValidationResult(is_valid=True)

        # Basic syntax validation
        self._check_basic_syntax(query, result)

        # Detect prefixes
        self._detect_prefixes(query, result)

        # Check for missing prefixes
        self._check_missing_prefixes(query, result, context)

        # Analyze complexity
        result.complexity_score = self._calculate_complexity(query)

        # Generate suggestions
        self._generate_suggestions(query, result, context)

        # Set overall validity
        result.is_valid = len(result.syntax_errors) == 0

        return result

    def _check_basic_syntax(self, query: str, result: ValidationResult):
        """Check basic SPARQL syntax."""
        query_upper = query.upper()

        # Check for query type
        has_query_type = any(
            keyword in query_upper
            for keyword in ['SELECT', 'CONSTRUCT', 'ASK', 'DESCRIBE']
        )

        if not has_query_type:
            result.syntax_errors.append(
                "Query must contain a query form (SELECT, CONSTRUCT, ASK, or DESCRIBE)"
            )

        # Check for WHERE clause (for SELECT/ASK queries)
        if 'SELECT' in query_upper or 'ASK' in query_upper:
            if 'WHERE' not in query_upper and '{' not in query:
                result.warnings.append(
                    "Query should contain a WHERE clause"
                )

        # Check for balanced braces
        open_braces = query.count('{')
        close_braces = query.count('}')
        if open_braces != close_braces:
            result.syntax_errors.append(
                f"Unbalanced braces: {open_braces} opening, {close_braces} closing"
            )

        # Check for balanced parentheses
        open_parens = query.count('(')
        close_parens = query.count(')')
        if open_parens != close_parens:
            result.syntax_errors.append(
                f"Unbalanced parentheses: {open_parens} opening, {close_parens} closing"
            )

        # Check for variables in SELECT clause
        if 'SELECT' in query_upper:
            select_match = re.search(
                r'SELECT\s+(DISTINCT\s+|REDUCED\s+)?(.*?)\s+(WHERE|{)',
                query,
                re.IGNORECASE | re.DOTALL
            )
            if select_match:
                variables = select_match.group(2).strip()
                if not variables or variables == '':
                    result.syntax_errors.append("SELECT clause is empty")
                elif variables != '*':
                    # Check that variables start with ? or $
                    var_tokens = variables.split()
                    for token in var_tokens:
                        if not token.startswith(('?', '$', '(')):
                            if not token.upper() in ['AS', 'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'SAMPLE']:
                                result.warnings.append(
                                    f"Potential issue with SELECT variable: {token}"
                                )

    def _detect_prefixes(self, query: str, result: ValidationResult):
        """Detect PREFIX declarations and prefixed names in query."""
        # Find PREFIX declarations
        for match in self.prefix_pattern.finditer(query):
            prefix, namespace = match.groups()
            result.detected_prefixes.add(prefix)

    def _check_missing_prefixes(
        self,
        query: str,
        result: ValidationResult,
        context: Optional[GenerationContext]
    ):
        """Check for missing PREFIX declarations."""
        # Find all prefixed names used in query
        used_prefixes = set()
        for match in self.prefixed_name_pattern.finditer(query):
            prefix = match.group(1)
            # Skip common SPARQL functions and keywords
            if prefix.lower() not in ['xsd', 'fn', 'afn', 'math']:
                used_prefixes.add(prefix)

        # Find missing prefixes
        missing = used_prefixes - result.detected_prefixes

        for prefix in missing:
            # Try to resolve from mapper or context
            vocab = self.ontology_mapper.get_vocabulary_by_prefix(prefix)
            if vocab:
                result.missing_prefixes[prefix] = vocab.namespace
            elif context and prefix in context.available_prefixes:
                result.missing_prefixes[prefix] = context.available_prefixes[prefix]
            else:
                result.warnings.append(
                    f"Unknown prefix '{prefix}' used without declaration"
                )

    def _calculate_complexity(self, query: str) -> float:
        """
        Calculate query complexity score (0-10).

        Factors:
        - Number of triple patterns
        - Use of OPTIONAL
        - Use of FILTER
        - Use of UNION
        - Use of subqueries
        - Use of aggregation
        - Use of property paths
        - Use of SERVICE (federation)
        """
        score = 0.0
        query_upper = query.upper()

        # Count triple patterns (rough estimate)
        triple_count = query.count('.') + query.count(';')
        score += min(triple_count * 0.1, 2.0)

        # OPTIONAL clauses
        optional_count = query_upper.count('OPTIONAL')
        score += optional_count * 0.5

        # FILTER clauses
        filter_count = query_upper.count('FILTER')
        score += filter_count * 0.3

        # UNION
        union_count = query_upper.count('UNION')
        score += union_count * 0.7

        # Subqueries
        select_count = query_upper.count('SELECT')
        if select_count > 1:
            score += (select_count - 1) * 1.0

        # Aggregation
        aggregates = ['COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'GROUP_CONCAT']
        aggregate_count = sum(query_upper.count(agg) for agg in aggregates)
        score += aggregate_count * 0.4

        # Property paths
        property_path_indicators = ['/', '*', '+', '?', '^']
        for indicator in property_path_indicators:
            # Only count within WHERE clause
            if indicator in query:
                score += 0.3

        # Federation
        if 'SERVICE' in query_upper:
            score += 2.0

        # Negation
        if 'MINUS' in query_upper or 'NOT EXISTS' in query_upper:
            score += 0.8

        return min(score, 10.0)

    def _generate_suggestions(
        self,
        query: str,
        result: ValidationResult,
        context: Optional[GenerationContext]
    ):
        """Generate optimization suggestions."""
        query_upper = query.upper()

        # Suggest adding LIMIT for unbounded queries
        if 'LIMIT' not in query_upper:
            if 'SELECT' in query_upper:
                result.suggestions.append(
                    "Consider adding a LIMIT clause to prevent large result sets"
                )

        # Suggest DISTINCT for potential duplicates
        if 'SELECT' in query_upper and 'DISTINCT' not in query_upper:
            if 'OPTIONAL' in query_upper or 'UNION' in query_upper:
                result.suggestions.append(
                    "Consider using SELECT DISTINCT to eliminate potential duplicates"
                )

        # Suggest optimization for multiple OPTIONAL
        optional_count = query_upper.count('OPTIONAL')
        if optional_count > 3:
            result.suggestions.append(
                f"Query has {optional_count} OPTIONAL clauses - consider if all are necessary"
            )

        # Suggest FILTER placement optimization
        if 'FILTER' in query_upper:
            # Check if FILTER comes early (good for performance)
            where_pos = query_upper.find('WHERE')
            filter_pos = query_upper.find('FILTER')
            if where_pos != -1 and filter_pos != -1:
                # Rough check - if filter is late in query
                relative_pos = (filter_pos - where_pos) / len(query)
                if relative_pos > 0.7:
                    result.suggestions.append(
                        "Consider moving FILTER clauses earlier in the WHERE clause for better performance"
                    )

        # Check for unused variables
        variables = set(self.variable_pattern.findall(query))
        if 'SELECT' in query_upper:
            select_match = re.search(
                r'SELECT\s+(DISTINCT\s+|REDUCED\s+)?(.*?)\s+(WHERE|{)',
                query,
                re.IGNORECASE | re.DOTALL
            )
            if select_match and select_match.group(2) != '*':
                selected_vars = set(
                    self.variable_pattern.findall(select_match.group(2))
                )
                unused = selected_vars - variables
                if unused:
                    result.warnings.append(
                        f"Variables selected but not used: {', '.join(unused)}"
                    )


class SPARQLGenerator:
    """
    Main SPARQL query generator with multiple generation strategies.

    Features:
    - Template-based generation for common patterns
    - LLM-based generation for complex queries
    - Hybrid approach with validation and fallback
    - Context-aware generation using schema and ontology
    - Multi-dataset and federated query support
    - Automatic validation and optimization
    - Confidence scoring

    Example:
        >>> generator = SPARQLGenerator(llm_client=client)
        >>> result = generator.generate(
        ...     "Find all proteins from human with their functions",
        ...     schema_info=schema,
        ...     strategy=GenerationStrategy.HYBRID
        ... )
        >>> print(result.query)
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        provider_manager: Optional[ProviderManager] = None,
        ontology_mapper: Optional[OntologyMapper] = None,
        prompt_engine: Optional[PromptEngine] = None,
        template_dir: Optional[Path] = None,
        enable_validation: bool = True,
        enable_optimization: bool = True,
    ):
        """
        Initialize SPARQL generator.

        Args:
            llm_client: LLM client for generation
            provider_manager: Provider manager for multi-provider support
            ontology_mapper: Ontology mapper for vocabulary resolution
            prompt_engine: Prompt engine for template management
            template_dir: Directory containing custom templates
            enable_validation: Enable automatic validation
            enable_optimization: Enable automatic optimization
        """
        self.llm_client = llm_client
        self.provider_manager = provider_manager
        self.ontology_mapper = ontology_mapper or OntologyMapper()
        self.prompt_engine = prompt_engine or PromptEngine(
            template_dir=template_dir,
            ontology_mapper=self.ontology_mapper
        )
        self.validator = SPARQLValidator(self.ontology_mapper)
        self.enable_validation = enable_validation
        self.enable_optimization = enable_optimization

        # Initialize templates
        self.templates: List[QueryTemplate] = []
        self._load_default_templates()

        # Generation statistics
        self.stats = {
            'total_generated': 0,
            'template_used': 0,
            'llm_used': 0,
            'hybrid_used': 0,
            'validation_failures': 0,
            'average_confidence': 0.0,
        }

    def _load_default_templates(self):
        """Load default query templates."""
        self.templates.extend([
            QueryTemplate(
                name="list_instances",
                pattern=r"(list|show|find|get)\s+(all\s+)?(\w+)",
                sparql_template="""SELECT ?instance ?label
WHERE {{
  ?instance a {class_uri} .
  OPTIONAL {{ ?instance rdfs:label ?label }}
}}
LIMIT {limit}""",
                required_context=["class_uri"],
                scenario=QueryScenario.BASIC,
                confidence=0.85
            ),
            QueryTemplate(
                name="count_instances",
                pattern=r"(how many|count|number of)\s+(\w+)",
                sparql_template="""SELECT (COUNT(?instance) AS ?count)
WHERE {{
  ?instance a {class_uri} .
}}""",
                required_context=["class_uri"],
                scenario=QueryScenario.AGGREGATION,
                confidence=0.9
            ),
            QueryTemplate(
                name="filter_by_property",
                pattern=r"(find|get|show)\s+(\w+)\s+(with|having|where)\s+(\w+)",
                sparql_template="""SELECT ?instance ?label
WHERE {{
  ?instance a {class_uri} .
  ?instance {property_uri} ?value .
  FILTER({filter_condition})
  OPTIONAL {{ ?instance rdfs:label ?label }}
}}
LIMIT {limit}""",
                required_context=["class_uri", "property_uri"],
                scenario=QueryScenario.FILTER,
                confidence=0.75
            ),
            QueryTemplate(
                name="relationship_query",
                pattern=r"(\w+)\s+(related to|associated with|linked to)\s+(\w+)",
                sparql_template="""SELECT ?subject ?object ?label
WHERE {{
  ?subject a {subject_class} .
  ?subject {property_uri} ?object .
  ?object a {object_class} .
  OPTIONAL {{ ?object rdfs:label ?label }}
}}
LIMIT {limit}""",
                required_context=["subject_class", "property_uri", "object_class"],
                scenario=QueryScenario.COMPLEX_JOIN,
                confidence=0.7
            ),
        ])

    def generate(
        self,
        natural_language: str,
        schema_info: Optional[SchemaInfo] = None,
        ontology_info: Optional[OntologyInfo] = None,
        endpoint_info: Optional[EndpointInfo] = None,
        strategy: Optional[GenerationStrategy] = None,
        scenario: Optional[QueryScenario] = None,
        constraints: Optional[Dict[str, Any]] = None,
        return_alternatives: bool = False,
        max_alternatives: int = 3,
    ) -> GeneratedQuery:
        """
        Generate SPARQL query from natural language.

        Args:
            natural_language: User's natural language query
            schema_info: Schema information from endpoint
            ontology_info: Ontology information
            endpoint_info: Endpoint configuration
            strategy: Generation strategy (AUTO if None)
            scenario: Query scenario (auto-detected if None)
            constraints: Query constraints (limit, timeout, etc.)
            return_alternatives: Return alternative formulations
            max_alternatives: Maximum number of alternatives

        Returns:
            GeneratedQuery with query and metadata

        Raises:
            QueryGenerationError: If generation fails
        """
        start_time = time.time()
        self.stats['total_generated'] += 1

        # Build generation context
        context = self._build_context(
            natural_language=natural_language,
            schema_info=schema_info,
            ontology_info=ontology_info,
            endpoint_info=endpoint_info,
            strategy=strategy or GenerationStrategy.AUTO,
            scenario=scenario,
            constraints=constraints or {}
        )

        # Determine strategy
        if context.strategy == GenerationStrategy.AUTO:
            context.strategy = self._select_strategy(context)

        # Generate query based on strategy
        try:
            if context.strategy == GenerationStrategy.TEMPLATE:
                result = self._generate_template(context)
                self.stats['template_used'] += 1

            elif context.strategy == GenerationStrategy.LLM:
                result = self._generate_llm(context)
                self.stats['llm_used'] += 1

            elif context.strategy == GenerationStrategy.HYBRID:
                result = self._generate_hybrid(context)
                self.stats['hybrid_used'] += 1

            else:
                raise QueryGenerationError(
                    f"Unknown generation strategy: {context.strategy}"
                )

        except Exception as e:
            logger.error(f"Query generation failed: {e}")
            raise QueryGenerationError(
                f"Failed to generate query: {e}",
                details={"natural_language": natural_language, "strategy": str(context.strategy)}
            )

        # Validate if enabled
        if self.enable_validation:
            validation = self.validator.validate(result.query, context)
            result.validation_errors = validation.syntax_errors

            # Add missing prefixes
            if validation.missing_prefixes:
                result.query = self._add_missing_prefixes(
                    result.query,
                    validation.missing_prefixes
                )
                # Re-validate after adding prefixes
                validation = self.validator.validate(result.query, context)
                result.validation_errors = validation.syntax_errors

            # Store suggestions in metadata
            result.metadata['validation'] = {
                'is_valid': validation.is_valid,
                'warnings': validation.warnings,
                'suggestions': validation.suggestions,
                'complexity_score': validation.complexity_score,
            }

            if not validation.is_valid:
                self.stats['validation_failures'] += 1

        # Generate alternatives if requested
        if return_alternatives:
            result.alternatives = self._generate_alternatives(
                context,
                primary_query=result.query,
                max_count=max_alternatives
            )

        # Update metadata
        result.metadata['generation_time'] = time.time() - start_time
        result.metadata['strategy'] = context.strategy.value
        result.metadata['scenario'] = context.scenario.value if context.scenario else None

        # Update statistics
        self._update_confidence_stats(result.confidence)

        return result

    def _build_context(
        self,
        natural_language: str,
        schema_info: Optional[SchemaInfo],
        ontology_info: Optional[OntologyInfo],
        endpoint_info: Optional[EndpointInfo],
        strategy: GenerationStrategy,
        scenario: Optional[QueryScenario],
        constraints: Dict[str, Any]
    ) -> GenerationContext:
        """Build complete generation context."""
        # Collect available prefixes
        available_prefixes = {}

        if schema_info and schema_info.namespaces:
            available_prefixes.update(schema_info.namespaces)

        if ontology_info and ontology_info.namespaces:
            available_prefixes.update(ontology_info.namespaces)

        # Add standard prefixes
        standard_prefixes = {
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "owl": "http://www.w3.org/2002/07/owl#",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
        }
        for prefix, uri in standard_prefixes.items():
            if prefix not in available_prefixes:
                available_prefixes[prefix] = uri

        # Auto-detect scenario if not provided
        if scenario is None:
            scenario = self.prompt_engine.detect_scenario(natural_language)

        # Get relevant examples
        examples = []
        if schema_info or ontology_info:
            prompt_examples = self.prompt_engine.get_examples(
                scenario=scenario,
                limit=3
            )
            examples = [
                {"question": ex.question, "sparql": ex.sparql}
                for ex in prompt_examples
            ]

        # Build vocabulary hints
        vocabulary_hints = self._extract_vocabulary_hints(
            natural_language,
            schema_info,
            ontology_info
        )

        return GenerationContext(
            natural_language=natural_language,
            schema_info=schema_info,
            ontology_info=ontology_info,
            endpoint_info=endpoint_info,
            available_prefixes=available_prefixes,
            scenario=scenario,
            strategy=strategy,
            constraints=constraints,
            examples=examples,
            vocabulary_hints=vocabulary_hints
        )

    def _extract_vocabulary_hints(
        self,
        query: str,
        schema_info: Optional[SchemaInfo],
        ontology_info: Optional[OntologyInfo]
    ) -> Dict[str, List[str]]:
        """Extract vocabulary hints from natural language query."""
        hints = {
            "classes": [],
            "properties": [],
            "individuals": []
        }

        query_lower = query.lower()
        words = query_lower.split()

        # Try to match ontology classes
        if ontology_info:
            for class_uri, owl_class in ontology_info.classes.items():
                for label in owl_class.label:
                    if label.lower() in query_lower:
                        hints["classes"].append(class_uri)

            for prop_uri, owl_prop in ontology_info.properties.items():
                for label in owl_prop.label:
                    if label.lower() in query_lower:
                        hints["properties"].append(prop_uri)

        # Try to match schema info
        if schema_info:
            for class_uri in schema_info.classes:
                local_name = class_uri.split('#')[-1].split('/')[-1]
                if local_name.lower() in query_lower:
                    hints["classes"].append(class_uri)

            for prop_uri in schema_info.properties:
                local_name = prop_uri.split('#')[-1].split('/')[-1]
                if local_name.lower() in query_lower:
                    hints["properties"].append(prop_uri)

        return hints

    def _select_strategy(self, context: GenerationContext) -> GenerationStrategy:
        """
        Automatically select best generation strategy.

        Logic:
        - Use TEMPLATE for simple, pattern-matching queries WITH sufficient context
        - Use LLM for complex queries or when context is insufficient
        - Use HYBRID for medium complexity with validation
        """
        query_lower = context.natural_language.lower()

        # Check for template matches
        template_matches = self._find_matching_templates(context)
        if template_matches and len(template_matches) > 0:
            # Check if we have sufficient context
            best_match = template_matches[0]
            if self._has_required_context(best_match, context):
                return GenerationStrategy.TEMPLATE
            else:
                # Template matches but insufficient context - need LLM
                if self.llm_client or self.provider_manager:
                    logger.debug(
                        f"Template '{best_match.name}' matches but lacks context. "
                        f"Falling back to LLM strategy."
                    )
                    return GenerationStrategy.LLM

        # Check complexity indicators for LLM
        complexity_indicators = [
            'compare', 'analyze', 'correlate', 'relationship',
            'across', 'between', 'complex', 'detailed'
        ]
        if any(indicator in query_lower for indicator in complexity_indicators):
            if self.llm_client or self.provider_manager:
                return GenerationStrategy.LLM

        # Default to LLM if available (safer than failing with templates), otherwise TEMPLATE
        # This ensures we don't generate malformed queries
        if self.llm_client or self.provider_manager:
            return GenerationStrategy.HYBRID
        else:
            # No LLM available - try template but it may fail
            return GenerationStrategy.TEMPLATE

    def _generate_template(self, context: GenerationContext) -> GeneratedQuery:
        """Generate query using template matching."""
        templates = self._find_matching_templates(context)

        if not templates:
            raise QueryGenerationError(
                "No matching templates found",
                details={"query": context.natural_language}
            )

        best_template = templates[0]

        # Fill template placeholders
        try:
            filled_query = self._fill_template(best_template, context)
        except Exception as e:
            raise QueryMappingError(
                f"Failed to fill template: {e}",
                details={"template": best_template.name}
            )

        return GeneratedQuery(
            query=filled_query,
            natural_language=context.natural_language,
            explanation=f"Generated using template: {best_template.name}",
            confidence=best_template.confidence,
            used_ontology=bool(context.ontology_info),
            metadata={
                "template": best_template.name,
                "strategy": "template"
            }
        )

    def _generate_llm(self, context: GenerationContext) -> GeneratedQuery:
        """Generate query using LLM."""
        if not self.llm_client and not self.provider_manager:
            raise QueryGenerationError(
                "LLM client not available",
                details={"strategy": "llm"}
            )

        # Build prompt context
        prompt_context = PromptContext(
            user_query=context.natural_language,
            schema_info=context.schema_info,
            ontology_info=context.ontology_info,
            available_prefixes=context.available_prefixes,
            example_queries=context.examples,
            ontology_mapper=self.ontology_mapper,
            scenario=context.scenario,
            constraints=context.constraints
        )

        # Generate prompt
        prompt = self.prompt_engine.generate_prompt(
            user_query=context.natural_language,
            schema_info=context.schema_info,
            ontology_info=context.ontology_info,
            scenario=context.scenario,
            constraints=context.constraints
        )

        # Generate with LLM
        try:
            if self.provider_manager:
                llm_response = self.provider_manager.generate_with_fallback(
                    LLMRequest(
                        prompt=prompt,
                        max_tokens=1500,
                        temperature=0.3  # Lower temperature for more consistent queries
                    )
                )
            else:
                llm_response = self.llm_client.generate_text(
                    prompt=prompt,
                    max_tokens=1500,
                    temperature=0.3
                )

            query_text = self._extract_sparql_from_llm_response(llm_response.content)

        except Exception as e:
            raise QueryGenerationError(
                f"LLM generation failed: {e}",
                details={"provider": "llm"}
            )

        # Assess confidence based on LLM response
        confidence = self._assess_llm_confidence(llm_response, context)

        return GeneratedQuery(
            query=query_text,
            natural_language=context.natural_language,
            explanation="Generated using LLM",
            confidence=confidence,
            used_ontology=bool(context.ontology_info),
            metadata={
                "strategy": "llm",
                "model": llm_response.model,
                "tokens_used": llm_response.usage.total_tokens
            }
        )

    def _generate_hybrid(self, context: GenerationContext) -> GeneratedQuery:
        """Generate query using hybrid approach (template + LLM validation)."""
        # Try template first
        templates = self._find_matching_templates(context)

        if templates and self._has_required_context(templates[0], context):
            # Generate with template
            template_result = self._generate_template(context)

            # Validate with LLM if available
            if self.llm_client or self.provider_manager:
                try:
                    validation_prompt = f"""Validate and improve this SPARQL query:

Query: {template_result.query}

Original question: {context.natural_language}

Please:
1. Check if the query correctly answers the question
2. Fix any syntax errors
3. Optimize if possible
4. Return the improved query

Only return the SPARQL query, no explanation."""

                    if self.provider_manager:
                        llm_response = self.provider_manager.generate_with_fallback(
                            LLMRequest(prompt=validation_prompt, max_tokens=1000, temperature=0.2)
                        )
                    else:
                        llm_response = self.llm_client.generate_text(
                            prompt=validation_prompt, max_tokens=1000, temperature=0.2
                        )

                    improved_query = self._extract_sparql_from_llm_response(
                        llm_response.content
                    )

                    template_result.query = improved_query
                    template_result.confidence = min(template_result.confidence + 0.1, 1.0)
                    template_result.metadata['strategy'] = 'hybrid'
                    template_result.metadata['llm_validated'] = True

                except Exception as e:
                    logger.warning(f"LLM validation failed, using template result: {e}")

            return template_result

        # Fall back to pure LLM generation
        return self._generate_llm(context)

    def _find_matching_templates(self, context: GenerationContext) -> List[QueryTemplate]:
        """Find templates matching the natural language query."""
        matches = []

        for template in self.templates:
            # Try pattern matching
            if re.search(template.pattern, context.natural_language, re.IGNORECASE):
                matches.append(template)

            # Also consider scenario matching
            elif template.scenario == context.scenario:
                matches.append(template)

        # Sort by confidence
        matches.sort(key=lambda t: t.confidence, reverse=True)
        return matches

    def _has_required_context(self, template: QueryTemplate, context: GenerationContext) -> bool:
        """Check if context has all required elements for template."""
        for required in template.required_context:
            if required == "class_uri":
                if not context.vocabulary_hints.get("classes"):
                    return False
            elif required == "property_uri":
                if not context.vocabulary_hints.get("properties"):
                    return False

        return True

    def _fill_template(self, template: QueryTemplate, context: GenerationContext) -> str:
        """Fill template placeholders with context information."""
        query = template.sparql_template
        unfilled_placeholders = []

        # Fill class_uri
        if "{class_uri}" in query:
            if context.vocabulary_hints.get("classes"):
                class_uri = context.vocabulary_hints["classes"][0]
                # Convert to prefixed form if possible
                prefix_result = self.ontology_mapper.extract_prefix_from_uri(class_uri)
                if prefix_result:
                    prefix, local = prefix_result
                    query = query.replace("{class_uri}", f"{prefix}:{local}")
                else:
                    query = query.replace("{class_uri}", f"<{class_uri}>")
            else:
                unfilled_placeholders.append("class_uri")

        # Fill property_uri
        if "{property_uri}" in query:
            if context.vocabulary_hints.get("properties"):
                prop_uri = context.vocabulary_hints["properties"][0]
                prefix_result = self.ontology_mapper.extract_prefix_from_uri(prop_uri)
                if prefix_result:
                    prefix, local = prefix_result
                    query = query.replace("{property_uri}", f"{prefix}:{local}")
                else:
                    query = query.replace("{property_uri}", f"<{prop_uri}>")
            else:
                unfilled_placeholders.append("property_uri")

        # Fill limit
        limit = context.constraints.get("limit", 100)
        query = query.replace("{limit}", str(limit))

        # Fill filter_condition (simplified)
        if "{filter_condition}" in query:
            query = query.replace("{filter_condition}", "true")

        # Check for any remaining unfilled placeholders
        if unfilled_placeholders:
            raise InsufficientContextError(
                f"Cannot fill template: missing context for {', '.join(unfilled_placeholders)}. "
                f"Please provide schema_info or ontology_info, or use --strategy llm for LLM-based generation.",
                details={
                    "template": template.name,
                    "missing_placeholders": unfilled_placeholders,
                    "query": context.natural_language
                }
            )

        # Add PREFIX declarations
        query = self._add_prefix_declarations(query, context)

        return query

    def _add_prefix_declarations(self, query: str, context: GenerationContext) -> str:
        """Add PREFIX declarations to query."""
        # Find prefixes used in query
        used_prefixes = set()
        for match in re.finditer(r'\b(\w+):(\w+)', query):
            prefix = match.group(1)
            if prefix.lower() not in ['http', 'https', 'ftp']:
                used_prefixes.add(prefix)

        # Build PREFIX declarations
        prefix_lines = []
        for prefix in sorted(used_prefixes):
            if prefix in context.available_prefixes:
                uri = context.available_prefixes[prefix]
                prefix_lines.append(f"PREFIX {prefix}: <{uri}>")

        if prefix_lines:
            return "\n".join(prefix_lines) + "\n\n" + query
        return query

    def _add_missing_prefixes(self, query: str, missing_prefixes: Dict[str, str]) -> str:
        """Add missing PREFIX declarations to query."""
        prefix_lines = []
        for prefix, uri in sorted(missing_prefixes.items()):
            prefix_lines.append(f"PREFIX {prefix}: <{uri}>")

        if prefix_lines:
            # Insert at the beginning
            return "\n".join(prefix_lines) + "\n\n" + query
        return query

    def _extract_sparql_from_llm_response(self, response: str) -> str:
        """Extract SPARQL query from LLM response."""
        # Try to find SPARQL code block
        sparql_match = re.search(
            r'```(?:sparql)?\s*(.*?)\s*```',
            response,
            re.DOTALL | re.IGNORECASE
        )

        if sparql_match:
            return sparql_match.group(1).strip()

        # Try to find SELECT/CONSTRUCT/ASK/DESCRIBE
        query_match = re.search(
            r'(PREFIX.*?)?(SELECT|CONSTRUCT|ASK|DESCRIBE).*',
            response,
            re.DOTALL | re.IGNORECASE
        )

        if query_match:
            return query_match.group(0).strip()

        # Return entire response if no pattern matches
        return response.strip()

    def _assess_llm_confidence(self, llm_response: LLMResponse, context: GenerationContext) -> float:
        """Assess confidence in LLM-generated query."""
        confidence = 0.7  # Base confidence

        # Increase if response is well-structured
        if "PREFIX" in llm_response.content:
            confidence += 0.05

        if "WHERE" in llm_response.content:
            confidence += 0.05

        # Increase if ontology was used
        if context.ontology_info:
            confidence += 0.1

        # Decrease if response is very short or very long
        query_length = len(llm_response.content)
        if query_length < 50:
            confidence -= 0.1
        elif query_length > 2000:
            confidence -= 0.05

        return min(max(confidence, 0.0), 1.0)

    def _generate_alternatives(
        self,
        context: GenerationContext,
        primary_query: str,
        max_count: int
    ) -> List[str]:
        """Generate alternative query formulations."""
        alternatives = []

        # Try different templates
        templates = self._find_matching_templates(context)
        for template in templates[:max_count]:
            if self._has_required_context(template, context):
                try:
                    alt_query = self._fill_template(template, context)
                    if alt_query != primary_query:
                        alternatives.append(alt_query)
                except:
                    continue

        return alternatives[:max_count]

    def _update_confidence_stats(self, confidence: float):
        """Update running confidence statistics."""
        total = self.stats['total_generated']
        current_avg = self.stats['average_confidence']
        self.stats['average_confidence'] = (
            (current_avg * (total - 1) + confidence) / total
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Get generation statistics."""
        return dict(self.stats)

    def add_template(self, template: QueryTemplate):
        """Add a custom query template."""
        self.templates.append(template)

    def clear_templates(self):
        """Clear all templates."""
        self.templates.clear()


# Utility functions

def create_generator(
    llm_client: Optional[LLMClient] = None,
    enable_validation: bool = True
) -> SPARQLGenerator:
    """
    Create a SPARQL generator with default configuration.

    Args:
        llm_client: Optional LLM client
        enable_validation: Enable validation

    Returns:
        Configured SPARQLGenerator
    """
    return SPARQLGenerator(
        llm_client=llm_client,
        enable_validation=enable_validation,
        enable_optimization=True
    )


def quick_generate(
    natural_language: str,
    schema_info: Optional[SchemaInfo] = None,
    llm_client: Optional[LLMClient] = None
) -> str:
    """
    Quick utility to generate a SPARQL query.

    Args:
        natural_language: Natural language query
        schema_info: Optional schema information
        llm_client: Optional LLM client

    Returns:
        Generated SPARQL query string
    """
    generator = create_generator(llm_client=llm_client)
    result = generator.generate(
        natural_language=natural_language,
        schema_info=schema_info
    )
    return result.query
