#!/usr/bin/env python3
"""
Discovery-Based SPARQL Query Generator

A comprehensive system that uses endpoint discovery results to generate accurate,
validated SPARQL queries. This system combines:
- Rule-based vocabulary and pattern matching from discovery data
- Incremental query building with validation at each step
- LLM integration for natural language understanding
- Fast and reliable query generation for real endpoints

The key innovation is using actual endpoint capabilities and vocabulary discovered
through introspection rather than relying purely on LLM knowledge.
"""

import sys
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, Counter

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sparql_agent.discovery.capabilities import CapabilitiesDetector, PrefixExtractor
from sparql_agent.discovery.connectivity import EndpointPinger, ConnectionConfig
from sparql_agent.llm.client import LLMRequest

# Optional LLM imports
try:
    from sparql_agent.llm import create_anthropic_provider
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    from sparql_agent.llm import create_openai_provider
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


class QueryComponent(Enum):
    """Types of SPARQL query components."""
    PREFIX = "prefix"
    SELECT = "select"
    WHERE = "where"
    FILTER = "filter"
    OPTIONAL = "optional"
    LIMIT = "limit"
    ORDER_BY = "order_by"
    GROUP_BY = "group_by"


@dataclass
class DiscoveryKnowledge:
    """
    Knowledge base extracted from endpoint discovery.

    Attributes:
        endpoint_url: SPARQL endpoint URL
        namespaces: Discovered namespace URIs
        prefixes: Prefix mappings (prefix -> namespace)
        classes: Available RDF classes
        properties: Available properties
        features: Supported SPARQL features
        functions: Supported SPARQL functions
        statistics: Dataset statistics
        patterns: Common query patterns extracted from analysis
    """
    endpoint_url: str
    namespaces: List[str] = field(default_factory=list)
    prefixes: Dict[str, str] = field(default_factory=dict)
    classes: List[str] = field(default_factory=list)
    properties: List[str] = field(default_factory=list)
    features: Dict[str, bool] = field(default_factory=dict)
    functions: Dict[str, bool] = field(default_factory=dict)
    statistics: Dict[str, Any] = field(default_factory=dict)
    patterns: Dict[str, str] = field(default_factory=dict)

    @property
    def has_property_paths(self) -> bool:
        """Check if endpoint supports property paths."""
        return self.features.get('PROPERTY_PATHS', False)

    @property
    def has_subqueries(self) -> bool:
        """Check if endpoint supports subqueries."""
        return self.features.get('SUBQUERY', False)

    @property
    def has_named_graphs(self) -> bool:
        """Check if endpoint supports named graphs."""
        return self.features.get('NAMED_GRAPHS', False)


@dataclass
class QueryPattern:
    """
    A reusable SPARQL query pattern.

    Attributes:
        name: Pattern name
        description: What this pattern does
        template: SPARQL template with placeholders
        required_prefixes: Required prefix namespaces
        keywords: Natural language keywords that trigger this pattern
        variables: Variables used in the pattern
        confidence: Confidence score for this pattern
    """
    name: str
    description: str
    template: str
    required_prefixes: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    variables: List[str] = field(default_factory=list)
    confidence: float = 0.8


@dataclass
class QueryBuildState:
    """
    State tracking during incremental query building.

    Attributes:
        prefixes: Accumulated prefix declarations
        select_vars: Variables in SELECT clause
        where_clauses: WHERE clause patterns
        filters: FILTER expressions
        optional_clauses: OPTIONAL patterns
        limit: LIMIT value
        order_by: ORDER BY clause
        validated_components: Components that passed validation
        errors: Validation errors encountered
    """
    prefixes: Set[str] = field(default_factory=set)
    select_vars: List[str] = field(default_factory=list)
    where_clauses: List[str] = field(default_factory=list)
    filters: List[str] = field(default_factory=list)
    optional_clauses: List[str] = field(default_factory=list)
    limit: Optional[int] = None
    order_by: Optional[str] = None
    validated_components: Set[QueryComponent] = field(default_factory=set)
    errors: List[str] = field(default_factory=list)

    def add_prefix(self, prefix: str, namespace: str) -> None:
        """Add a prefix declaration."""
        self.prefixes.add(f"PREFIX {prefix}: <{namespace}>")

    def add_where_clause(self, clause: str) -> None:
        """Add a WHERE clause pattern."""
        self.where_clauses.append(clause.strip())

    def add_filter(self, filter_expr: str) -> None:
        """Add a FILTER expression."""
        self.filters.append(filter_expr.strip())

    def add_optional(self, optional_pattern: str) -> None:
        """Add an OPTIONAL pattern."""
        self.optional_clauses.append(optional_pattern.strip())

    def build_query(self) -> str:
        """Build the complete SPARQL query."""
        parts = []

        # Prefixes
        if self.prefixes:
            parts.append('\n'.join(sorted(self.prefixes)))
            parts.append('')

        # SELECT
        if self.select_vars:
            parts.append(f"SELECT {' '.join(self.select_vars)}")
        else:
            parts.append("SELECT *")

        # WHERE
        parts.append("WHERE {")

        # Main patterns
        for clause in self.where_clauses:
            parts.append(f"  {clause}")

        # Optional patterns
        for optional in self.optional_clauses:
            parts.append(f"  OPTIONAL {{ {optional} }}")

        # Filters
        for filter_expr in self.filters:
            parts.append(f"  FILTER({filter_expr})")

        parts.append("}")

        # Modifiers
        if self.order_by:
            parts.append(f"ORDER BY {self.order_by}")

        if self.limit:
            parts.append(f"LIMIT {self.limit}")

        return '\n'.join(parts)


class VocabularyMatcher:
    """
    Matches natural language terms to endpoint vocabulary.

    Uses discovery results to find relevant classes, properties, and patterns
    based on URI analysis and namespace knowledge.
    """

    def __init__(self, knowledge: DiscoveryKnowledge):
        """
        Initialize vocabulary matcher.

        Args:
            knowledge: Discovery knowledge base
        """
        self.knowledge = knowledge
        self._build_vocabulary_index()

    def _build_vocabulary_index(self) -> None:
        """Build searchable index of vocabulary terms."""
        self.class_index: Dict[str, List[str]] = defaultdict(list)
        self.property_index: Dict[str, List[str]] = defaultdict(list)

        # Index classes by local name and keywords
        for class_uri in self.knowledge.classes:
            terms = self._extract_search_terms(class_uri)
            for term in terms:
                self.class_index[term.lower()].append(class_uri)

        # Index properties by local name and keywords
        for prop_uri in self.knowledge.properties:
            terms = self._extract_search_terms(prop_uri)
            for term in terms:
                self.property_index[term.lower()].append(prop_uri)

    def _extract_search_terms(self, uri: str) -> List[str]:
        """
        Extract searchable terms from a URI.

        Args:
            uri: Full URI

        Returns:
            List of search terms
        """
        terms = []

        # Extract local name
        if '#' in uri:
            local_name = uri.split('#')[-1]
        elif '/' in uri:
            local_name = uri.split('/')[-1]
        else:
            local_name = uri

        # Add the full local name
        terms.append(local_name)

        # Split camelCase and snake_case
        # Split on uppercase letters
        parts = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)', local_name)
        terms.extend(parts)

        # Split on underscores and hyphens
        for sep in ['_', '-']:
            if sep in local_name:
                terms.extend(local_name.split(sep))

        return [t for t in terms if len(t) > 2]  # Filter very short terms

    def find_classes(self, keywords: List[str], limit: int = 5) -> List[Tuple[str, float]]:
        """
        Find classes matching keywords.

        Args:
            keywords: Search keywords
            limit: Maximum number of results

        Returns:
            List of (class_uri, score) tuples
        """
        scores: Counter = Counter()

        for keyword in keywords:
            keyword_lower = keyword.lower()
            # Exact matches
            if keyword_lower in self.class_index:
                for class_uri in self.class_index[keyword_lower]:
                    scores[class_uri] += 2.0

            # Partial matches
            for term, class_uris in self.class_index.items():
                if keyword_lower in term or term in keyword_lower:
                    for class_uri in class_uris:
                        scores[class_uri] += 1.0

        # Return top matches
        return scores.most_common(limit)

    def find_properties(self, keywords: List[str], limit: int = 5) -> List[Tuple[str, float]]:
        """
        Find properties matching keywords.

        Args:
            keywords: Search keywords
            limit: Maximum number of results

        Returns:
            List of (property_uri, score) tuples
        """
        scores: Counter = Counter()

        for keyword in keywords:
            keyword_lower = keyword.lower()
            # Exact matches
            if keyword_lower in self.property_index:
                for prop_uri in self.property_index[keyword_lower]:
                    scores[prop_uri] += 2.0

            # Partial matches
            for term, prop_uris in self.property_index.items():
                if keyword_lower in term or term in keyword_lower:
                    for prop_uri in prop_uris:
                        scores[prop_uri] += 1.0

        # Return top matches
        return scores.most_common(limit)

    def shorten_uri(self, uri: str) -> str:
        """
        Shorten URI using known prefixes.

        Args:
            uri: Full URI

        Returns:
            Shortened URI or original if no prefix found
        """
        for prefix, namespace in self.knowledge.prefixes.items():
            if uri.startswith(namespace):
                local = uri[len(namespace):]
                return f"{prefix}:{local}"
        return f"<{uri}>"


class QueryValidator:
    """
    Validates query components against discovery knowledge.

    Ensures generated queries use correct vocabulary, syntax, and
    supported features for the target endpoint.
    """

    def __init__(self, knowledge: DiscoveryKnowledge):
        """
        Initialize validator.

        Args:
            knowledge: Discovery knowledge base
        """
        self.knowledge = knowledge

    def validate_prefix(self, prefix: str, namespace: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a prefix declaration.

        Args:
            prefix: Prefix name
            namespace: Namespace URI

        Returns:
            (is_valid, error_message)
        """
        # Check if namespace is in discovered namespaces
        if namespace not in self.knowledge.namespaces:
            return False, f"Namespace {namespace} not found in endpoint"

        # Check prefix naming
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', prefix):
            return False, f"Invalid prefix name: {prefix}"

        return True, None

    def validate_class(self, class_uri: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a class URI.

        Args:
            class_uri: Class URI

        Returns:
            (is_valid, error_message)
        """
        if class_uri in self.knowledge.classes:
            return True, None
        return False, f"Class {class_uri} not found in endpoint"

    def validate_property(self, prop_uri: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a property URI.

        Args:
            prop_uri: Property URI

        Returns:
            (is_valid, error_message)
        """
        if prop_uri in self.knowledge.properties:
            return True, None
        return False, f"Property {prop_uri} not found in endpoint"

    def validate_feature(self, feature: str) -> Tuple[bool, Optional[str]]:
        """
        Validate use of a SPARQL feature.

        Args:
            feature: Feature name (e.g., 'PROPERTY_PATHS')

        Returns:
            (is_valid, error_message)
        """
        if feature in self.knowledge.features:
            if self.knowledge.features[feature]:
                return True, None
            else:
                return False, f"Feature {feature} not supported by endpoint"
        return True, None  # Unknown features are allowed (conservative)

    def validate_function(self, function: str) -> Tuple[bool, Optional[str]]:
        """
        Validate use of a SPARQL function.

        Args:
            function: Function name (e.g., 'STRLEN')

        Returns:
            (is_valid, error_message)
        """
        if function in self.knowledge.functions:
            if self.knowledge.functions[function]:
                return True, None
            else:
                return False, f"Function {function} not supported by endpoint"
        return True, None  # Unknown functions are allowed (conservative)

    def validate_query(self, query: str) -> Tuple[bool, List[str]]:
        """
        Validate a complete SPARQL query.

        Args:
            query: SPARQL query string

        Returns:
            (is_valid, list of errors/warnings)
        """
        errors = []

        # Basic syntax checks
        if not query.strip():
            errors.append("Query is empty")
            return False, errors

        # Check for SELECT/ASK/CONSTRUCT/DESCRIBE
        query_upper = query.upper()
        if not any(kw in query_upper for kw in ['SELECT', 'ASK', 'CONSTRUCT', 'DESCRIBE']):
            errors.append("Query must contain SELECT, ASK, CONSTRUCT, or DESCRIBE")

        # Check for WHERE clause
        if 'WHERE' not in query_upper:
            errors.append("Query must contain WHERE clause")

        # Check for balanced braces
        if query.count('{') != query.count('}'):
            errors.append("Unbalanced braces in query")

        # Check for balanced parentheses
        if query.count('(') != query.count(')'):
            errors.append("Unbalanced parentheses in query")

        return len(errors) == 0, errors


class DiscoveryBasedQueryGenerator:
    """
    Discovery-driven SPARQL query generator.

    This system generates accurate SPARQL queries by:
    1. Using actual endpoint vocabulary from discovery
    2. Building queries incrementally with validation
    3. Using LLM for understanding, rules for construction
    4. Validating each component against endpoint capabilities

    The key advantage is that it generates queries that actually work
    with real endpoints because it uses real discovery data.
    """

    def __init__(
        self,
        llm_client=None,
        fast_mode: bool = False,
        validate_components: bool = True
    ):
        """
        Initialize the generator.

        Args:
            llm_client: LLM client for natural language understanding
            fast_mode: Skip detailed validation for faster generation
            validate_components: Validate each component during building
        """
        self.llm_client = llm_client
        self.fast_mode = fast_mode
        self.validate_components = validate_components
        self.knowledge_cache: Dict[str, DiscoveryKnowledge] = {}

    def discover_endpoint(
        self,
        endpoint_url: str,
        force_refresh: bool = False
    ) -> DiscoveryKnowledge:
        """
        Discover endpoint capabilities and build knowledge base.

        Args:
            endpoint_url: SPARQL endpoint URL
            force_refresh: Force re-discovery even if cached

        Returns:
            Discovery knowledge base
        """
        # Check cache
        if endpoint_url in self.knowledge_cache and not force_refresh:
            logger.info(f"Using cached discovery results for {endpoint_url}")
            return self.knowledge_cache[endpoint_url]

        logger.info(f"Discovering endpoint: {endpoint_url}")

        # Run discovery
        detector = CapabilitiesDetector(
            endpoint_url,
            timeout=30,
            fast_mode=self.fast_mode
        )

        try:
            capabilities = detector.detect_all_capabilities()
        except Exception as e:
            logger.error(f"Discovery failed: {e}")
            # Return minimal knowledge base
            return DiscoveryKnowledge(endpoint_url=endpoint_url)

        # Extract knowledge
        knowledge = DiscoveryKnowledge(
            endpoint_url=endpoint_url,
            namespaces=capabilities.get('namespaces', []),
            features=capabilities.get('features', {}),
            functions=capabilities.get('supported_functions', {}),
            statistics=capabilities.get('statistics', {})
        )

        # Extract prefixes
        prefix_extractor = PrefixExtractor()
        if knowledge.namespaces:
            prefix_extractor.extract_from_namespaces(knowledge.namespaces)
            knowledge.prefixes = prefix_extractor.prefix_mappings

        # Extract common patterns for well-known endpoints
        knowledge.patterns = self._extract_endpoint_patterns(endpoint_url, capabilities)

        # Cache the knowledge
        self.knowledge_cache[endpoint_url] = knowledge

        logger.info(f"Discovery complete: {len(knowledge.namespaces)} namespaces, "
                   f"{len(knowledge.prefixes)} prefixes")

        return knowledge

    def _extract_endpoint_patterns(
        self,
        endpoint_url: str,
        capabilities: Dict
    ) -> Dict[str, str]:
        """
        Extract common query patterns for specific endpoints.

        Args:
            endpoint_url: Endpoint URL
            capabilities: Raw capability data

        Returns:
            Dictionary of pattern templates
        """
        patterns = {}

        # Wikidata patterns
        if 'wikidata' in endpoint_url.lower():
            patterns['entity_label'] = '?entity rdfs:label ?label . FILTER(LANG(?label) = "en")'
            patterns['entity_type'] = '?entity wdt:P31 ?type'
            patterns['human'] = '?person wdt:P31 wd:Q5'
            patterns['label_service'] = 'SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }'

        # UniProt patterns
        elif 'uniprot' in endpoint_url.lower():
            patterns['protein'] = '?protein a up:Protein'
            patterns['human_protein'] = '?protein a up:Protein ; up:organism taxon:9606'
            patterns['protein_name'] = '?protein up:recommendedName/up:fullName ?name'
            patterns['reviewed'] = '?protein up:reviewed true'

        # DBpedia patterns
        elif 'dbpedia' in endpoint_url.lower():
            patterns['resource'] = '?resource a dbo:Thing'
            patterns['label'] = '?resource rdfs:label ?label . FILTER(LANG(?label) = "en")'
            patterns['abstract'] = '?resource dbo:abstract ?abstract . FILTER(LANG(?abstract) = "en")'

        return patterns

    def parse_intent(self, natural_language: str, knowledge: DiscoveryKnowledge) -> Dict[str, Any]:
        """
        Parse natural language query to extract intent.

        Args:
            natural_language: User's query in natural language
            knowledge: Endpoint knowledge base

        Returns:
            Parsed intent with action, entities, filters, etc.
        """
        intent = {
            'action': 'select',  # select, count, ask, etc.
            'keywords': [],
            'filters': [],
            'limit': 10,  # Default limit for testing
            'order_by': None
        }

        # Extract keywords (simple tokenization)
        words = re.findall(r'\b\w+\b', natural_language.lower())
        intent['keywords'] = [w for w in words if len(w) > 3]

        # Detect action
        if any(w in natural_language.lower() for w in ['count', 'how many']):
            intent['action'] = 'count'
        elif any(w in natural_language.lower() for w in ['list', 'show', 'find', 'get']):
            intent['action'] = 'select'

        # Extract limit - try multiple patterns
        # Pattern 1: "N results/items/entries/rows"
        limit_match = re.search(r'(\d+)\s+(?:results|items|entries|rows)', natural_language.lower())
        if limit_match:
            intent['limit'] = int(limit_match.group(1))
        # Pattern 2: "first N" or "top N"
        elif any(w in natural_language.lower() for w in ['first', 'top']):
            num_match = re.search(r'(?:first|top)\s+(\d+)', natural_language.lower())
            if num_match:
                intent['limit'] = int(num_match.group(1))
        # Pattern 3: "find/show/list N items" - number at the start
        else:
            num_match = re.search(r'\b(\d+)\b', natural_language)
            if num_match:
                # Check if it's at the beginning (like "Find 5 items")
                intent['limit'] = int(num_match.group(1))

        # Use LLM for better understanding if available
        if self.llm_client:
            try:
                llm_intent = self._llm_parse_intent(natural_language, knowledge)
                intent.update(llm_intent)
            except Exception as e:
                logger.warning(f"LLM intent parsing failed: {e}")

        return intent

    def _llm_parse_intent(self, natural_language: str, knowledge: DiscoveryKnowledge) -> Dict[str, Any]:
        """
        Use LLM to parse query intent.

        Args:
            natural_language: User's query
            knowledge: Endpoint knowledge

        Returns:
            Parsed intent
        """
        prompt = f"""Parse this natural language query and extract the intent:

Query: "{natural_language}"

Target endpoint: {knowledge.endpoint_url}
Available namespaces: {', '.join(knowledge.namespaces[:10])}

Extract:
1. Action (select, count, ask, etc.)
2. Main entity/concept being queried
3. Properties/attributes to retrieve
4. Filters/constraints
5. Limit/ordering requirements

Return as JSON with keys: action, entity, properties, filters, limit, order_by"""

        request = LLMRequest(prompt=prompt, max_tokens=500)
        response = self.llm_client.generate(request)

        # Parse JSON response (simplified - production would be more robust)
        try:
            import json
            content = response.content.strip()
            # Extract JSON from markdown code blocks if present
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0]
            elif '```' in content:
                content = content.split('```')[1].split('```')[0]
            return json.loads(content)
        except:
            return {}

    def build_query_incremental(
        self,
        intent: Dict[str, Any],
        knowledge: DiscoveryKnowledge
    ) -> QueryBuildState:
        """
        Build query incrementally with validation.

        Args:
            intent: Parsed intent
            knowledge: Endpoint knowledge

        Returns:
            Query build state
        """
        state = QueryBuildState()
        matcher = VocabularyMatcher(knowledge)
        validator = QueryValidator(knowledge)

        # Add required prefixes
        for prefix, namespace in knowledge.prefixes.items():
            if self.validate_components:
                valid, error = validator.validate_prefix(prefix, namespace)
                if not valid:
                    state.errors.append(error)
                    continue
            state.add_prefix(prefix, namespace)

        # Build based on action
        if intent['action'] == 'count':
            state.select_vars = ['(COUNT(*) AS ?count)']
        else:
            state.select_vars = ['*']

        # Find relevant classes/properties from keywords
        keywords = intent.get('keywords', [])
        if keywords:
            classes = matcher.find_classes(keywords, limit=3)
            properties = matcher.find_properties(keywords, limit=3)

            # Build WHERE clause using top matches
            if classes:
                class_uri, _ = classes[0]
                class_short = matcher.shorten_uri(class_uri)
                state.add_where_clause(f"?s a {class_short} .")
                state.select_vars = ['?s']

            if properties:
                for prop_uri, score in properties[:2]:  # Use top 2 properties
                    prop_short = matcher.shorten_uri(prop_uri)
                    var_name = f"?{prop_short.split(':')[-1] if ':' in prop_short else 'value'}"
                    state.add_where_clause(f"?s {prop_short} {var_name} .")
                    if var_name not in state.select_vars:
                        state.select_vars.append(var_name)

        # Add pattern-based clauses
        if 'human' in ' '.join(keywords).lower() and 'human' in knowledge.patterns:
            state.add_where_clause(knowledge.patterns['human'])

        # Add filters from intent
        for filter_expr in intent.get('filters', []):
            state.add_filter(filter_expr)

        # Add limit
        if intent.get('limit'):
            state.limit = intent['limit']

        # Add ordering
        if intent.get('order_by'):
            state.order_by = intent['order_by']

        # Validate final query
        if self.validate_components:
            query = state.build_query()
            valid, errors = validator.validate_query(query)
            if not valid:
                state.errors.extend(errors)

        return state

    def generate(
        self,
        natural_language: str,
        endpoint_url: str,
        force_discovery: bool = False
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate SPARQL query from natural language.

        Args:
            natural_language: User's query in natural language
            endpoint_url: Target SPARQL endpoint URL
            force_discovery: Force endpoint re-discovery

        Returns:
            (sparql_query, metadata)
        """
        logger.info(f"Generating query for: {natural_language}")

        # Discover endpoint
        knowledge = self.discover_endpoint(endpoint_url, force_refresh=force_discovery)

        # Parse intent
        intent = self.parse_intent(natural_language, knowledge)
        logger.debug(f"Parsed intent: {intent}")

        # Build query incrementally
        state = self.build_query_incremental(intent, knowledge)

        # Generate final query
        query = state.build_query()

        # Build metadata
        metadata = {
            'endpoint_url': endpoint_url,
            'intent': intent,
            'validation_errors': state.errors,
            'prefixes_used': len(state.prefixes),
            'where_clauses': len(state.where_clauses),
            'is_valid': len(state.errors) == 0
        }

        logger.info(f"Query generated successfully: {len(query)} characters")

        return query, metadata


def demo_wikidata():
    """Demonstrate with Wikidata endpoint."""
    print("=" * 80)
    print("Discovery-Based Query Generator Demo - Wikidata")
    print("=" * 80)

    # Create generator (without LLM for now)
    generator = DiscoveryBasedQueryGenerator(fast_mode=True)

    # Test queries
    test_queries = [
        "Find 5 people born in Paris",
        "Show me 10 scientists",
        "List French physicists",
    ]

    endpoint_url = "https://query.wikidata.org/sparql"

    for nl_query in test_queries:
        print(f"\nNatural Language: {nl_query}")
        print("-" * 80)

        try:
            sparql, metadata = generator.generate(nl_query, endpoint_url)
            print("Generated SPARQL:")
            print(sparql)
            print(f"\nMetadata: {metadata}")
        except Exception as e:
            print(f"Error: {e}")

        print("=" * 80)


def demo_with_real_discovery():
    """Demonstrate using actual discovery results."""
    print("=" * 80)
    print("Discovery-Based Query Generator - Real Discovery Demo")
    print("=" * 80)

    # Simulate real discovery data (from wikidata file)
    knowledge = DiscoveryKnowledge(
        endpoint_url="https://query.wikidata.org/sparql",
        namespaces=[
            "http://wikiba.se/ontology#",
            "http://www.wikidata.org/entity/",
            "http://www.wikidata.org/prop/direct/",
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "http://www.w3.org/2000/01/rdf-schema#",
            "http://schema.org/",
        ],
        prefixes={
            "wikibase": "http://wikiba.se/ontology#",
            "wd": "http://www.wikidata.org/entity/",
            "wdt": "http://www.wikidata.org/prop/direct/",
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "schema": "http://schema.org/",
        },
        features={
            'BIND': True,
            'MINUS': True,
            'SUBQUERY': True,
            'VALUES': True,
        },
        patterns={
            'human': '?person wdt:P31 wd:Q5',
            'label': '?entity rdfs:label ?label . FILTER(LANG(?label) = "en")',
        }
    )

    # Create generator and use the knowledge
    generator = DiscoveryBasedQueryGenerator(fast_mode=True)
    generator.knowledge_cache[knowledge.endpoint_url] = knowledge

    # Generate query
    nl_query = "Find 10 humans"
    print(f"Natural Language: {nl_query}\n")

    intent = generator.parse_intent(nl_query, knowledge)
    print(f"Parsed Intent: {intent}\n")

    state = generator.build_query_incremental(intent, knowledge)
    query = state.build_query()

    print("Generated SPARQL:")
    print(query)
    print(f"\nValidation Errors: {state.errors}")
    print("=" * 80)


if __name__ == "__main__":
    # Run demos
    demo_with_real_discovery()
    print("\n")

    # Try with actual endpoint (requires network)
    try:
        demo_wikidata()
    except Exception as e:
        print(f"Network demo skipped: {e}")
