"""
Natural Language Intent Parser for SPARQL Query Generation.

This module provides comprehensive intent detection and parsing for natural language
queries, extracting query types, entities, filters, constraints, and aggregation needs.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from ..core.types import OntologyInfo, SchemaInfo, OWLClass, OWLProperty


class QueryType(Enum):
    """SPARQL query types."""
    SELECT = "SELECT"
    CONSTRUCT = "CONSTRUCT"
    ASK = "ASK"
    DESCRIBE = "DESCRIBE"
    COUNT = "COUNT"  # Special case of SELECT with COUNT aggregation


class AggregationType(Enum):
    """Types of aggregation functions."""
    COUNT = "COUNT"
    SUM = "SUM"
    AVG = "AVG"
    MIN = "MIN"
    MAX = "MAX"
    GROUP_CONCAT = "GROUP_CONCAT"
    SAMPLE = "SAMPLE"


class FilterOperator(Enum):
    """Filter operators for constraints."""
    EQUALS = "="
    NOT_EQUALS = "!="
    GREATER_THAN = ">"
    LESS_THAN = "<"
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    CONTAINS = "CONTAINS"
    REGEX = "REGEX"
    IN = "IN"
    NOT_IN = "NOT IN"
    LANG_MATCHES = "LANG_MATCHES"
    BOUND = "BOUND"


class OrderDirection(Enum):
    """Order direction for sorting."""
    ASC = "ASC"
    DESC = "DESC"


@dataclass
class Entity:
    """
    Represents an entity extracted from natural language.

    Attributes:
        text: Original text of the entity
        type: Entity type (class, property, literal, etc.)
        uri: Resolved URI (if available)
        confidence: Confidence score (0-1)
        alternatives: Alternative URIs/interpretations
        context: Additional context about the entity
    """
    text: str
    type: str
    uri: Optional[str] = None
    confidence: float = 1.0
    alternatives: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Filter:
    """
    Represents a filter constraint.

    Attributes:
        variable: Variable to filter on
        operator: Filter operator
        value: Filter value
        datatype: Datatype of the value
        language: Language tag (for literals)
        negated: Whether the filter is negated
    """
    variable: str
    operator: FilterOperator
    value: Any
    datatype: Optional[str] = None
    language: Optional[str] = None
    negated: bool = False


@dataclass
class Aggregation:
    """
    Represents an aggregation operation.

    Attributes:
        type: Aggregation type
        variable: Variable to aggregate
        result_variable: Variable name for the result
        distinct: Whether to use DISTINCT
        group_by: Variables to group by
    """
    type: AggregationType
    variable: str
    result_variable: str
    distinct: bool = False
    group_by: List[str] = field(default_factory=list)


@dataclass
class OrderClause:
    """
    Represents an ORDER BY clause.

    Attributes:
        variable: Variable to order by
        direction: Order direction (ASC/DESC)
    """
    variable: str
    direction: OrderDirection = OrderDirection.ASC


@dataclass
class ParsedIntent:
    """
    Represents the parsed intent from natural language.

    Attributes:
        original_query: Original natural language query
        query_type: Detected SPARQL query type
        entities: Extracted entities
        filters: Extracted filters/constraints
        aggregations: Detected aggregations
        order_by: Order clauses
        limit: Result limit
        offset: Result offset
        distinct: Whether to use DISTINCT
        optional_patterns: Variables/patterns that are optional
        property_paths: Detected property paths
        text_search: Text search terms
        confidence: Overall confidence score
        ambiguities: Detected ambiguities needing resolution
        metadata: Additional metadata
    """
    original_query: str
    query_type: QueryType
    entities: List[Entity] = field(default_factory=list)
    filters: List[Filter] = field(default_factory=list)
    aggregations: List[Aggregation] = field(default_factory=list)
    order_by: List[OrderClause] = field(default_factory=list)
    limit: Optional[int] = None
    offset: Optional[int] = None
    distinct: bool = False
    optional_patterns: List[str] = field(default_factory=list)
    property_paths: List[str] = field(default_factory=list)
    text_search: List[str] = field(default_factory=list)
    confidence: float = 1.0
    ambiguities: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class IntentParser:
    """
    Natural language intent parser for SPARQL query generation.

    This class analyzes natural language queries and extracts structured information
    including query types, entities, filters, aggregations, and constraints.
    """

    # Query type patterns
    QUERY_TYPE_PATTERNS = {
        QueryType.SELECT: [
            r'\b(find|list|show|get|retrieve|display|what|which)\b',
            r'\b(tell me|give me)\b',
        ],
        QueryType.COUNT: [
            r'\b(how many|count|number of|total)\b',
        ],
        QueryType.ASK: [
            r'\b(is|are|does|do|has|have|can|was|were)\b.*\?',
            r'\b(true or false|yes or no|check if|verify)\b',
        ],
        QueryType.DESCRIBE: [
            r'\b(describe|tell me about|information about|details about)\b',
            r'\b(what is|who is)\b',
        ],
        QueryType.CONSTRUCT: [
            r'\b(build|construct|create graph|generate graph)\b',
            r'\b(transform|convert|map)\b',
        ],
    }

    # Aggregation patterns
    AGGREGATION_PATTERNS = {
        AggregationType.COUNT: [
            r'\b(count|number of|how many|total number)\b',
        ],
        AggregationType.SUM: [
            r'\b(sum|total|add up|accumulate)\b',
        ],
        AggregationType.AVG: [
            r'\b(average|mean|avg)\b',
        ],
        AggregationType.MIN: [
            r'\b(minimum|min|smallest|lowest|least)\b',
        ],
        AggregationType.MAX: [
            r'\b(maximum|max|largest|highest|greatest|most)\b',
        ],
    }

    # Filter operator patterns
    FILTER_PATTERNS = {
        FilterOperator.EQUALS: [
            r'\b(is|equals|equal to|exactly|named|called)\b',
            r'\b(=|==)\b',
        ],
        FilterOperator.NOT_EQUALS: [
            r'\b(is not|not equal|not|different from|other than)\b',
            r'\b(!=|<>)\b',
        ],
        FilterOperator.GREATER_THAN: [
            r'\b(greater than|more than|above|over|exceeds)\b',
            r'\b(>)\b',
        ],
        FilterOperator.LESS_THAN: [
            r'\b(less than|fewer than|below|under)\b',
            r'\b(<)\b',
        ],
        FilterOperator.GREATER_EQUAL: [
            r'\b(at least|no less than|greater than or equal|minimum of)\b',
            r'\b(>=)\b',
        ],
        FilterOperator.LESS_EQUAL: [
            r'\b(at most|no more than|less than or equal|maximum of)\b',
            r'\b(<=)\b',
        ],
        FilterOperator.CONTAINS: [
            r'\b(contains|containing|includes|including|with)\b',
        ],
        FilterOperator.REGEX: [
            r'\b(matches|matching|pattern|like)\b',
        ],
    }

    # Order patterns
    ORDER_PATTERNS = {
        OrderDirection.ASC: [
            r'\b(ascending|asc|lowest first|smallest first|increasing)\b',
            r'\b(order by)\b(?!.*desc)',
        ],
        OrderDirection.DESC: [
            r'\b(descending|desc|highest first|largest first|decreasing)\b',
            r'\b(top|best|highest|largest)\b',
        ],
    }

    # Common entity types
    ENTITY_TYPE_KEYWORDS = {
        'person': ['person', 'people', 'human', 'individual', 'user', 'author', 'creator'],
        'organization': ['organization', 'company', 'institution', 'agency', 'group'],
        'location': ['location', 'place', 'city', 'country', 'region', 'area'],
        'gene': ['gene', 'genes', 'genetic'],
        'protein': ['protein', 'proteins'],
        'disease': ['disease', 'diseases', 'disorder', 'condition', 'illness'],
        'drug': ['drug', 'drugs', 'medication', 'medicine', 'compound'],
        'publication': ['paper', 'article', 'publication', 'study', 'research'],
        'dataset': ['dataset', 'data', 'collection'],
    }

    # Limit patterns
    LIMIT_PATTERN = r'\b(top|first|limit|maximum)\s+(\d+)\b'

    # Optional/nullable patterns
    OPTIONAL_PATTERNS = [
        r'\b(optional|optionally|if available|if exists|may have)\b',
    ]

    def __init__(
        self,
        schema_info: Optional[SchemaInfo] = None,
        ontology_info: Optional[OntologyInfo] = None,
        custom_patterns: Optional[Dict[str, List[str]]] = None
    ):
        """
        Initialize the intent parser.

        Args:
            schema_info: Schema information for entity resolution
            ontology_info: Ontology information for entity resolution
            custom_patterns: Custom pattern definitions
        """
        self.schema_info = schema_info
        self.ontology_info = ontology_info
        self.custom_patterns = custom_patterns or {}

    def parse(self, query: str) -> ParsedIntent:
        """
        Parse a natural language query and extract intent.

        Args:
            query: Natural language query

        Returns:
            ParsedIntent object with extracted information
        """
        query_lower = query.lower().strip()

        # Detect query type
        query_type = self._detect_query_type(query_lower)

        # Extract entities
        entities = self._extract_entities(query, query_lower)

        # Extract filters
        filters = self._extract_filters(query, query_lower, entities)

        # Detect aggregations
        aggregations = self._detect_aggregations(query_lower, query_type)

        # Extract ordering
        order_by = self._extract_order_by(query_lower)

        # Extract limit
        limit = self._extract_limit(query_lower)

        # Detect distinct
        distinct = self._detect_distinct(query_lower)

        # Detect optional patterns
        optional_patterns = self._detect_optional_patterns(query_lower)

        # Detect property paths
        property_paths = self._detect_property_paths(query_lower)

        # Extract text search terms
        text_search = self._extract_text_search(query, query_lower)

        # Calculate confidence
        confidence = self._calculate_confidence(query_type, entities, aggregations)

        # Detect ambiguities
        ambiguities = self._detect_ambiguities(entities, filters)

        return ParsedIntent(
            original_query=query,
            query_type=query_type,
            entities=entities,
            filters=filters,
            aggregations=aggregations,
            order_by=order_by,
            limit=limit,
            distinct=distinct,
            optional_patterns=optional_patterns,
            property_paths=property_paths,
            text_search=text_search,
            confidence=confidence,
            ambiguities=ambiguities,
            metadata={
                'has_aggregation': len(aggregations) > 0,
                'has_filters': len(filters) > 0,
                'has_ordering': len(order_by) > 0,
                'entity_count': len(entities),
            }
        )

    def _detect_query_type(self, query_lower: str) -> QueryType:
        """Detect the SPARQL query type."""
        scores = {qt: 0 for qt in QueryType}

        for query_type, patterns in self.QUERY_TYPE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower, re.IGNORECASE):
                    scores[query_type] += 1

        # Count has priority if detected
        if scores[QueryType.COUNT] > 0:
            return QueryType.COUNT

        # ASK for yes/no questions
        if scores[QueryType.ASK] > 0 and query_lower.endswith('?'):
            return QueryType.ASK

        # Get the highest score
        max_score = max(scores.values())
        if max_score > 0:
            for qt, score in scores.items():
                if score == max_score:
                    return qt

        # Default to SELECT
        return QueryType.SELECT

    def _extract_entities(self, query: str, query_lower: str) -> List[Entity]:
        """Extract entities from the query."""
        entities = []

        # Extract quoted strings as potential entity values
        quoted_strings = re.findall(r'"([^"]+)"', query)
        for qs in quoted_strings:
            entities.append(Entity(
                text=qs,
                type='literal',
                confidence=0.9,
                context={'quoted': True}
            ))

        # Single quoted strings
        quoted_strings = re.findall(r"'([^']+)'", query)
        for qs in quoted_strings:
            entities.append(Entity(
                text=qs,
                type='literal',
                confidence=0.9,
                context={'quoted': True}
            ))

        # Detect entity types from keywords
        for entity_type, keywords in self.ENTITY_TYPE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in query_lower:
                    # Try to find the specific entity value nearby
                    pattern = rf'\b{keyword}\b\s+(\w+(?:\s+\w+)?)'
                    matches = re.finditer(pattern, query_lower)
                    for match in matches:
                        entity_value = match.group(1)

                        # Skip common words
                        if entity_value not in ['of', 'in', 'for', 'with', 'that', 'the', 'a', 'an']:
                            entities.append(Entity(
                                text=entity_value,
                                type=entity_type,
                                confidence=0.7,
                                context={'keyword': keyword}
                            ))

        # Resolve entities using schema/ontology
        if self.ontology_info:
            entities = self._resolve_entities_with_ontology(entities)
        elif self.schema_info:
            entities = self._resolve_entities_with_schema(entities)

        return entities

    def _resolve_entities_with_ontology(self, entities: List[Entity]) -> List[Entity]:
        """Resolve entities using ontology information."""
        for entity in entities:
            # Skip already resolved entities
            if entity.uri:
                continue

            # Try to match with ontology classes
            owl_class = self.ontology_info.get_class_by_label(entity.text)
            if owl_class:
                entity.uri = owl_class.uri
                entity.type = 'class'
                entity.confidence = 0.9
                continue

            # Try to match with ontology properties
            owl_property = self.ontology_info.get_property_by_label(entity.text)
            if owl_property:
                entity.uri = owl_property.uri
                entity.type = 'property'
                entity.confidence = 0.9
                continue

            # Fuzzy matching for partial matches
            for class_uri, owl_class in self.ontology_info.classes.items():
                for label in owl_class.label:
                    if self._fuzzy_match(entity.text, label):
                        entity.alternatives.append(class_uri)

        return entities

    def _resolve_entities_with_schema(self, entities: List[Entity]) -> List[Entity]:
        """Resolve entities using schema information."""
        for entity in entities:
            if entity.uri:
                continue

            # Try to match with schema classes
            entity_lower = entity.text.lower()
            for class_uri in self.schema_info.classes:
                class_name = class_uri.split('#')[-1].split('/')[-1].lower()
                if entity_lower in class_name or class_name in entity_lower:
                    entity.uri = class_uri
                    entity.type = 'class'
                    entity.confidence = 0.7
                    break

            # Try to match with properties
            if not entity.uri:
                for prop_uri in self.schema_info.properties:
                    prop_name = prop_uri.split('#')[-1].split('/')[-1].lower()
                    if entity_lower in prop_name or prop_name in entity_lower:
                        entity.uri = prop_uri
                        entity.type = 'property'
                        entity.confidence = 0.7
                        break

        return entities

    def _fuzzy_match(self, text1: str, text2: str, threshold: float = 0.8) -> bool:
        """Simple fuzzy string matching."""
        text1, text2 = text1.lower(), text2.lower()

        # Exact match
        if text1 == text2:
            return True

        # One contains the other
        if text1 in text2 or text2 in text1:
            return True

        # Simple Levenshtein-like check (word overlap)
        words1 = set(text1.split())
        words2 = set(text2.split())

        if not words1 or not words2:
            return False

        overlap = len(words1 & words2)
        similarity = overlap / max(len(words1), len(words2))

        return similarity >= threshold

    def _extract_filters(
        self,
        query: str,
        query_lower: str,
        entities: List[Entity]
    ) -> List[Filter]:
        """Extract filter constraints."""
        filters = []

        # Pattern: "where X is Y"
        where_pattern = r'\bwhere\s+(\w+)\s+(is|equals?|=)\s+(["\']?)([^"\']+)\3'
        matches = re.finditer(where_pattern, query_lower)
        for match in matches:
            variable = match.group(1)
            value = match.group(4)
            filters.append(Filter(
                variable=variable,
                operator=FilterOperator.EQUALS,
                value=value
            ))

        # Pattern: "with X greater than Y"
        comparison_pattern = r'\bwith\s+(\w+)\s+(greater than|less than|more than|fewer than)\s+(\d+(?:\.\d+)?)'
        matches = re.finditer(comparison_pattern, query_lower)
        for match in matches:
            variable = match.group(1)
            operator_text = match.group(2)
            value = float(match.group(3))

            if 'greater' in operator_text or 'more' in operator_text:
                operator = FilterOperator.GREATER_THAN
            else:
                operator = FilterOperator.LESS_THAN

            filters.append(Filter(
                variable=variable,
                operator=operator,
                value=value
            ))

        # Pattern: "containing X"
        contains_pattern = r'\bcontaining\s+(["\']?)([^"\']+)\1'
        matches = re.finditer(contains_pattern, query_lower)
        for match in matches:
            value = match.group(2)
            filters.append(Filter(
                variable='label',  # Common assumption
                operator=FilterOperator.CONTAINS,
                value=value
            ))

        # Extract filters from entities
        for entity in entities:
            if entity.type == 'literal' and entity.context.get('quoted'):
                # Quoted strings often represent filter values
                filters.append(Filter(
                    variable='label',  # Default to label
                    operator=FilterOperator.CONTAINS,
                    value=entity.text,
                    confidence=0.7
                ))

        return filters

    def _detect_aggregations(
        self,
        query_lower: str,
        query_type: QueryType
    ) -> List[Aggregation]:
        """Detect aggregation requirements."""
        aggregations = []

        # If query type is COUNT, add count aggregation
        if query_type == QueryType.COUNT:
            aggregations.append(Aggregation(
                type=AggregationType.COUNT,
                variable='*',
                result_variable='count'
            ))

        # Detect other aggregations
        for agg_type, patterns in self.AGGREGATION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    # Try to find the variable being aggregated
                    var_pattern = rf'{pattern}\s+(?:of\s+)?(\w+)'
                    var_match = re.search(var_pattern, query_lower)

                    variable = var_match.group(1) if var_match else '*'
                    result_var = agg_type.value.lower()

                    # Check for DISTINCT
                    distinct = bool(re.search(r'\bdistinct\b', query_lower))

                    aggregations.append(Aggregation(
                        type=agg_type,
                        variable=variable,
                        result_variable=result_var,
                        distinct=distinct
                    ))

        # Detect GROUP BY
        group_by_pattern = r'\bgroup(?:ed)?\s+by\s+(\w+(?:,\s*\w+)*)'
        group_match = re.search(group_by_pattern, query_lower)
        if group_match and aggregations:
            group_vars = [v.strip() for v in group_match.group(1).split(',')]
            for agg in aggregations:
                agg.group_by = group_vars

        return aggregations

    def _extract_order_by(self, query_lower: str) -> List[OrderClause]:
        """Extract ORDER BY clauses."""
        order_clauses = []

        # Pattern: "order by X"
        order_pattern = r'\border\s+by\s+(\w+)(?:\s+(asc|desc|ascending|descending))?'
        matches = re.finditer(order_pattern, query_lower)
        for match in matches:
            variable = match.group(1)
            direction_text = match.group(2)

            direction = OrderDirection.ASC
            if direction_text and ('desc' in direction_text):
                direction = OrderDirection.DESC

            order_clauses.append(OrderClause(
                variable=variable,
                direction=direction
            ))

        # Pattern: "top X" or "highest X" implies DESC order
        if re.search(r'\b(top|highest|largest|best)\b', query_lower):
            # Try to find what to order by
            match = re.search(r'\b(?:top|highest|largest|best)\s+\d+\s+(\w+)', query_lower)
            if match:
                variable = match.group(1)
                order_clauses.append(OrderClause(
                    variable=variable,
                    direction=OrderDirection.DESC
                ))

        return order_clauses

    def _extract_limit(self, query_lower: str) -> Optional[int]:
        """Extract LIMIT value."""
        match = re.search(self.LIMIT_PATTERN, query_lower)
        if match:
            return int(match.group(2))

        # Default limit for "top X" queries
        top_match = re.search(r'\btop\s+(\d+)\b', query_lower)
        if top_match:
            return int(top_match.group(1))

        return None

    def _detect_distinct(self, query_lower: str) -> bool:
        """Detect if DISTINCT should be used."""
        return bool(re.search(r'\b(distinct|unique|different)\b', query_lower))

    def _detect_optional_patterns(self, query_lower: str) -> List[str]:
        """Detect optional patterns."""
        optional_terms = []

        for pattern in self.OPTIONAL_PATTERNS:
            matches = re.finditer(rf'{pattern}\s+(\w+(?:\s+\w+)?)', query_lower)
            for match in matches:
                term = match.group(1)
                if term not in ['the', 'a', 'an', 'that', 'this']:
                    optional_terms.append(term)

        return optional_terms

    def _detect_property_paths(self, query_lower: str) -> List[str]:
        """Detect property path requirements."""
        property_paths = []

        # Pattern: "X through Y"
        through_pattern = r'\bthrough\s+(\w+)'
        matches = re.finditer(through_pattern, query_lower)
        for match in matches:
            property_paths.append(match.group(1))

        # Pattern: "X via Y"
        via_pattern = r'\bvia\s+(\w+)'
        matches = re.finditer(via_pattern, query_lower)
        for match in matches:
            property_paths.append(match.group(1))

        # Transitive relationships
        if re.search(r'\b(all|any|transitively|recursively)\b.*\b(parent|child|ancestor|descendant)\b', query_lower):
            property_paths.append('transitive')

        return property_paths

    def _extract_text_search(self, query: str, query_lower: str) -> List[str]:
        """Extract text search terms."""
        search_terms = []

        # Pattern: "search for X"
        search_pattern = r'\bsearch(?:ing)?\s+for\s+(["\']?)([^"\']+)\1'
        matches = re.finditer(search_pattern, query_lower)
        for match in matches:
            search_terms.append(match.group(2))

        # Pattern: "containing X"
        contains_pattern = r'\bcontaining\s+(["\']?)([^"\']+)\1'
        matches = re.finditer(contains_pattern, query_lower)
        for match in matches:
            search_terms.append(match.group(2))

        # Pattern: "related to X"
        related_pattern = r'\brelated\s+to\s+(["\']?)([^"\']+)\1'
        matches = re.finditer(related_pattern, query_lower)
        for match in matches:
            search_terms.append(match.group(2))

        return search_terms

    def _calculate_confidence(
        self,
        query_type: QueryType,
        entities: List[Entity],
        aggregations: List[Aggregation]
    ) -> float:
        """Calculate overall confidence score."""
        confidence = 1.0

        # Reduce confidence if no entities found
        if not entities:
            confidence *= 0.7

        # Reduce confidence for unresolved entities
        unresolved = sum(1 for e in entities if not e.uri)
        if unresolved > 0:
            confidence *= (1.0 - (unresolved / max(len(entities), 1)) * 0.3)

        # Reduce confidence if aggregation detected but no group by
        if aggregations:
            for agg in aggregations:
                if agg.type != AggregationType.COUNT and not agg.group_by:
                    confidence *= 0.9

        return round(confidence, 2)

    def _detect_ambiguities(
        self,
        entities: List[Entity],
        filters: List[Filter]
    ) -> List[Dict[str, Any]]:
        """Detect ambiguities that need resolution."""
        ambiguities = []

        # Entities with multiple alternatives
        for entity in entities:
            if len(entity.alternatives) > 1:
                ambiguities.append({
                    'type': 'entity_ambiguity',
                    'entity': entity.text,
                    'alternatives': entity.alternatives,
                    'message': f"Multiple possible interpretations for '{entity.text}'"
                })

        # Entities without URIs
        for entity in entities:
            if not entity.uri and entity.type not in ['literal']:
                ambiguities.append({
                    'type': 'unresolved_entity',
                    'entity': entity.text,
                    'message': f"Could not resolve '{entity.text}' to a known URI"
                })

        # Filters without clear variables
        for filter_obj in filters:
            if not filter_obj.variable or filter_obj.variable == 'label':
                ambiguities.append({
                    'type': 'ambiguous_filter',
                    'filter': filter_obj,
                    'message': f"Filter target for '{filter_obj.value}' is ambiguous"
                })

        return ambiguities

    def classify_query_pattern(self, intent: ParsedIntent) -> str:
        """
        Classify the query into common SPARQL patterns.

        Args:
            intent: Parsed intent

        Returns:
            Pattern classification string
        """
        # Count query
        if intent.query_type == QueryType.COUNT or any(
            agg.type == AggregationType.COUNT for agg in intent.aggregations
        ):
            if intent.aggregations and intent.aggregations[0].group_by:
                return "COUNT_GROUP_BY"
            return "COUNT_SIMPLE"

        # Aggregation with ordering (e.g., "top 10 by X")
        if intent.aggregations and intent.order_by and intent.limit:
            return "TOP_N_AGGREGATION"

        # Text search
        if intent.text_search:
            return "FULL_TEXT_SEARCH"

        # Complex join (multiple entities with relationships)
        if len(intent.entities) >= 2:
            entity_types = set(e.type for e in intent.entities)
            if 'class' in entity_types or len(entity_types) > 1:
                return "COMPLEX_JOIN"

        # Simple filter
        if intent.filters and len(intent.entities) <= 1:
            return "SIMPLE_FILTER"

        # Property path
        if intent.property_paths:
            return "PROPERTY_PATH"

        # Basic list
        if intent.query_type == QueryType.SELECT and not intent.filters:
            return "BASIC_LIST"

        # Ask query
        if intent.query_type == QueryType.ASK:
            return "ASK_VERIFICATION"

        # Describe query
        if intent.query_type == QueryType.DESCRIBE:
            return "DESCRIBE_ENTITY"

        return "GENERIC_SELECT"

    def suggest_query_structure(self, intent: ParsedIntent) -> Dict[str, Any]:
        """
        Suggest a SPARQL query structure based on the intent.

        Args:
            intent: Parsed intent

        Returns:
            Dictionary with query structure suggestions
        """
        pattern = self.classify_query_pattern(intent)

        structure = {
            'pattern': pattern,
            'query_type': intent.query_type.value,
            'select_variables': [],
            'where_patterns': [],
            'filters': [],
            'aggregations': [],
            'modifiers': {}
        }

        # Build select variables
        if intent.aggregations:
            for agg in intent.aggregations:
                structure['select_variables'].append(
                    f'({agg.type.value}(?{agg.variable}) AS ?{agg.result_variable})'
                )
                if agg.group_by:
                    structure['select_variables'].extend(f'?{v}' for v in agg.group_by)
        else:
            # Default variables based on entities
            for entity in intent.entities:
                if entity.type == 'class':
                    structure['select_variables'].append('?instance')
                elif entity.type == 'property':
                    structure['select_variables'].append('?value')

        # Build WHERE patterns
        for entity in intent.entities:
            if entity.uri:
                if entity.type == 'class':
                    structure['where_patterns'].append(
                        f'?instance a <{entity.uri}>'
                    )
                elif entity.type == 'property':
                    structure['where_patterns'].append(
                        f'?subject <{entity.uri}> ?value'
                    )

        # Add filters
        for filter_obj in intent.filters:
            structure['filters'].append({
                'variable': filter_obj.variable,
                'operator': filter_obj.operator.value,
                'value': filter_obj.value
            })

        # Add modifiers
        if intent.distinct:
            structure['modifiers']['distinct'] = True

        if intent.limit:
            structure['modifiers']['limit'] = intent.limit

        if intent.offset:
            structure['modifiers']['offset'] = intent.offset

        if intent.order_by:
            structure['modifiers']['order_by'] = [
                {'variable': oc.variable, 'direction': oc.direction.value}
                for oc in intent.order_by
            ]

        return structure


# Utility functions

def parse_query(
    query: str,
    schema_info: Optional[SchemaInfo] = None,
    ontology_info: Optional[OntologyInfo] = None
) -> ParsedIntent:
    """
    Quick utility to parse a query.

    Args:
        query: Natural language query
        schema_info: Optional schema information
        ontology_info: Optional ontology information

    Returns:
        ParsedIntent object
    """
    parser = IntentParser(schema_info=schema_info, ontology_info=ontology_info)
    return parser.parse(query)


def classify_query(
    query: str,
    schema_info: Optional[SchemaInfo] = None,
    ontology_info: Optional[OntologyInfo] = None
) -> str:
    """
    Quick utility to classify a query pattern.

    Args:
        query: Natural language query
        schema_info: Optional schema information
        ontology_info: Optional ontology information

    Returns:
        Pattern classification string
    """
    parser = IntentParser(schema_info=schema_info, ontology_info=ontology_info)
    intent = parser.parse(query)
    return parser.classify_query_pattern(intent)
