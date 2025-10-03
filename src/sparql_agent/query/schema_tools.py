#!/usr/bin/env python3
"""
Schema-Driven Query Tools for SPARQL Agent

This module provides intelligent query building tools that use VOID and SHEX
schema information to help LLMs construct valid SPARQL queries piece by piece.

Instead of just providing schema context, these tools allow iterative query
construction with validation at each step.
"""

import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any, Union
from urllib.parse import urlparse

from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL

from ..schema.void_parser import VoIDDataset, VoIDExtractor
from ..schema.shex_parser import ShExParser, ShExSchema
from ..discovery.capabilities import CapabilitiesDetector


@dataclass
class QueryComponent:
    """Represents a validated component of a SPARQL query."""

    component_type: str  # 'prefix', 'triple', 'filter', 'optional', 'service'
    sparql_fragment: str
    variables: Set[str] = field(default_factory=set)
    predicates: Set[str] = field(default_factory=set)
    classes: Set[str] = field(default_factory=set)
    confidence: float = 1.0
    validation_passed: bool = True
    validation_notes: List[str] = field(default_factory=list)


@dataclass
class QueryPattern:
    """Common query patterns extracted from schema information."""

    pattern_name: str
    description: str
    sparql_template: str
    required_prefixes: List[str] = field(default_factory=list)
    variables: List[str] = field(default_factory=list)
    example_usage: str = ""
    confidence: float = 1.0


class SchemaQueryTools:
    """
    Collection of tools for schema-driven SPARQL query construction.

    These tools allow LLMs to:
    1. Find available predicates for a class
    2. Validate triple patterns against schema
    3. Suggest query components based on VOID/SHEX data
    4. Build queries incrementally with validation
    """

    def __init__(self, endpoint_url: str, skip_discovery: bool = False):
        self.endpoint_url = endpoint_url
        self._skip_discovery = skip_discovery
        self.void_data: List[VoIDDataset] = []
        self.shex_schemas: Dict[str, ShExSchema] = {}
        self.discovered_patterns: List[QueryPattern] = []
        self.available_prefixes: Dict[str, str] = {}
        self.class_hierarchy: Dict[str, List[str]] = {}
        self.property_domains: Dict[str, List[str]] = {}
        self.property_ranges: Dict[str, List[str]] = {}

    def load_void_data(self, void_datasets: Optional[List[VoIDDataset]] = None) -> None:
        """Load VOID data for the endpoint."""
        if void_datasets:
            self.void_data = void_datasets
            self._extract_patterns_from_void()
        else:
            # Skip auto-extraction of VOID for now due to endpoint issues
            print("Skipping VOID auto-extraction - provide VOID datasets manually if needed")

    def load_shex_schema(self, schema_content: str, schema_name: str = "default") -> None:
        """Load ShEx schema for validation."""
        try:
            parser = ShExParser()
            schema = parser.parse(schema_content)
            self.shex_schemas[schema_name] = schema
        except Exception as e:
            print(f"Warning: Could not load ShEx schema: {e}")

    def discover_endpoint_capabilities(self) -> Dict[str, Any]:
        """Discover endpoint capabilities using the discovery system."""
        try:
            detector = CapabilitiesDetector(self.endpoint_url)
            # Use a shorter timeout to avoid hanging on problematic endpoints
            capabilities = detector.detect_all_capabilities()

            # Extract useful information
            result = {
                'namespaces': capabilities.get('namespaces', {}),
                'common_classes': capabilities.get('classes', [])[:20],
                'common_properties': capabilities.get('properties', [])[:50],
                'endpoint_type': capabilities.get('endpoint_type', 'generic'),
                'supported_features': capabilities.get('features', []),
            }

            # Update our internal state
            self.available_prefixes.update(capabilities.get('namespaces', {}))
            return result

        except Exception as e:
            print(f"Warning: Could not discover capabilities: {e}")
            # Return minimal fallback capabilities
            return {
                'namespaces': self.get_available_prefixes(),
                'common_classes': [],
                'common_properties': [],
                'endpoint_type': 'generic',
                'supported_features': [],
            }

    def find_predicates_for_class(self, class_uri: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Find predicates that can be used with a specific class.

        Args:
            class_uri: The RDF class URI
            limit: Maximum number of predicates to return

        Returns:
            List of predicate information with usage statistics
        """
        predicates = []

        # Check VOID data for property partitions
        for dataset in self.void_data:
            for prop, count in dataset.property_partitions.items():
                if count > 0:  # Has actual usage
                    predicates.append({
                        'predicate': prop,
                        'usage_count': count,
                        'source': 'void',
                        'confidence': 0.8
                    })

        # Check ShEx schemas for constraints
        for schema_name, schema in self.shex_schemas.items():
            for shape_name, shape in schema.shapes.items():
                if class_uri in shape_name or shape_name.endswith(class_uri.split('/')[-1]):
                    for tc in shape.triple_constraints:
                        predicates.append({
                            'predicate': tc.predicate,
                            'cardinality': tc.cardinality.value,
                            'value_type': str(tc.value_expr),
                            'source': f'shex:{schema_name}',
                            'confidence': 0.9
                        })

        # Sort by confidence and usage
        predicates.sort(key=lambda x: (x.get('confidence', 0), x.get('usage_count', 0)), reverse=True)
        return predicates[:limit]

    def validate_triple_pattern(self, subject: str, predicate: str, object_val: str) -> Dict[str, Any]:
        """
        Validate a triple pattern against schema information.

        Returns validation result with suggestions for fixes.
        """
        validation = {
            'valid': True,
            'confidence': 1.0,
            'issues': [],
            'suggestions': [],
            'schema_sources': []
        }

        # Rule 1: Check for problematic characters in URIs
        uri_validation = self._validate_uri_syntax(subject, predicate, object_val)
        validation['issues'].extend(uri_validation['issues'])
        validation['suggestions'].extend(uri_validation['suggestions'])
        if uri_validation['issues']:
            validation['valid'] = False

        # Check against ShEx constraints
        for schema_name, schema in self.shex_schemas.items():
            for shape_name, shape in schema.shapes.items():
                for tc in shape.triple_constraints:
                    if tc.predicate == predicate:
                        # Found matching constraint
                        validation['schema_sources'].append(f'shex:{schema_name}:{shape_name}')

                        # Check cardinality (simplified)
                        if tc.cardinality.value == '?' and object_val.count(',') > 0:
                            validation['issues'].append(f"Cardinality mismatch: {predicate} expects at most one value")
                            validation['valid'] = False

                        # Check value type constraints
                        if 'xsd:' in str(tc.value_expr) and not self._matches_datatype(object_val, str(tc.value_expr)):
                            validation['issues'].append(f"Type mismatch: {predicate} expects {tc.value_expr}")
                            validation['confidence'] *= 0.7

        # Check VOID statistics
        predicate_found = False
        for dataset in self.void_data:
            if predicate in dataset.property_partitions:
                predicate_found = True
                validation['schema_sources'].append('void:property_partition')
                if dataset.property_partitions[predicate] == 0:
                    validation['issues'].append(f"Predicate {predicate} has no known usage in dataset")
                    validation['confidence'] *= 0.5

        if not predicate_found and self.void_data:
            validation['suggestions'].append(f"Consider using common predicates from VOID data")
            validation['confidence'] *= 0.6

        return validation

    def suggest_query_patterns(self, intent: str) -> List[QueryPattern]:
        """
        Suggest query patterns based on natural language intent and schema.

        Args:
            intent: Natural language description of what user wants

        Returns:
            List of suggested query patterns ranked by relevance
        """
        suggestions = []

        # Extract key terms from intent
        intent_lower = intent.lower()

        # Pattern 1: If asking for entities of a type
        if any(word in intent_lower for word in ['find', 'get', 'show', 'list']):
            for dataset in self.void_data:
                for class_uri, count in dataset.class_partitions.items():
                    if count > 100:  # Only suggest classes with substantial data
                        class_name = class_uri.split('/')[-1]
                        if class_name.lower() in intent_lower:
                            pattern = QueryPattern(
                                pattern_name=f"list_{class_name.lower()}",
                                description=f"Find instances of {class_name}",
                                sparql_template=f"""
SELECT ?entity ?label WHERE {{
  ?entity rdf:type <{class_uri}> .
  OPTIONAL {{ ?entity rdfs:label ?label }}
}}
LIMIT 10""",
                                required_prefixes=['rdf', 'rdfs'],
                                variables=['entity', 'label'],
                                confidence=0.8
                            )
                            suggestions.append(pattern)

        # Pattern 2: Property-based queries
        if any(word in intent_lower for word in ['with', 'having', 'where']):
            # Look for property mentions
            for dataset in self.void_data:
                for prop, count in dataset.property_partitions.items():
                    prop_name = prop.split('/')[-1].lower()
                    if prop_name in intent_lower and count > 50:
                        pattern = QueryPattern(
                            pattern_name=f"filter_by_{prop_name}",
                            description=f"Filter by {prop_name} property",
                            sparql_template=f"""
SELECT ?entity ?value WHERE {{
  ?entity <{prop}> ?value .
  # Add type constraint as needed
}}
LIMIT 10""",
                            variables=['entity', 'value'],
                            confidence=0.7
                        )
                        suggestions.append(pattern)

        # Add ShEx-based patterns
        for schema_name, schema in self.shex_schemas.items():
            for shape_name, shape in schema.shapes.items():
                shape_name_lower = shape_name.lower()
                if any(word in shape_name_lower for word in intent_lower.split()):
                    # Build pattern from shape constraints
                    triple_patterns = []
                    variables = set()

                    for tc in shape.triple_constraints:
                        if tc.cardinality.value in ['+', '*', '1']:  # Required or common
                            triple_patterns.append(f"  ?entity <{tc.predicate}> ?{tc.predicate.split('/')[-1]} .")
                            variables.add(f"{tc.predicate.split('/')[-1]}")

                    if triple_patterns:
                        sparql_template = f"""
SELECT ?entity {' '.join(f'?{v}' for v in variables)} WHERE {{
{chr(10).join(triple_patterns)}
}}
LIMIT 10"""

                        pattern = QueryPattern(
                            pattern_name=f"shex_{shape_name.lower()}",
                            description=f"Query based on {shape_name} shape",
                            sparql_template=sparql_template,
                            variables=list(variables) + ['entity'],
                            confidence=0.9
                        )
                        suggestions.append(pattern)

        # Sort by confidence
        suggestions.sort(key=lambda x: x.confidence, reverse=True)
        return suggestions[:10]

    def fix_query_uri_issues(self, query: str) -> Dict[str, Any]:
        """
        Fix common URI syntax issues in a SPARQL query.

        Args:
            query: SPARQL query string

        Returns:
            Dictionary with fixed query and list of fixes applied
        """
        fixes_applied = []
        fixed_query = query

        # Common DBpedia URI fixes
        dbpedia_fixes = [
            (',', '%2C', 'comma'),
            (' ', '%20', 'space'),
            ('(', '%28', 'opening parenthesis'),
            (')', '%29', 'closing parenthesis'),
        ]

        for old_char, new_char, description in dbpedia_fixes:
            if f'dbr:' in fixed_query and old_char in fixed_query:
                # Find and fix DBpedia resource URIs
                import re
                pattern = r'(dbr:[^\s<>}\]]+)'
                matches = re.findall(pattern, fixed_query)

                for match in matches:
                    if old_char in match:
                        fixed_match = match.replace(old_char, new_char)
                        fixed_query = fixed_query.replace(match, fixed_match)
                        fixes_applied.append(f"Fixed {description} in URI: {match} → {fixed_match}")

        return {
            'query': fixed_query,
            'fixes_applied': fixes_applied,
            'issues_found': len(fixes_applied) > 0
        }

    def build_query_incrementally(self, components: List[QueryComponent]) -> Dict[str, Any]:
        """
        Build a SPARQL query from validated components.

        Args:
            components: List of validated query components

        Returns:
            Complete query with validation summary
        """
        query_parts = {
            'prefixes': [],
            'select': [],
            'where': [],
            'filters': [],
            'optionals': [],
            'services': []
        }

        all_variables = set()
        validation_issues = []

        # Organize components by type
        for component in components:
            if not component.validation_passed:
                validation_issues.extend(component.validation_notes)
                continue

            all_variables.update(component.variables)

            if component.component_type == 'prefix':
                query_parts['prefixes'].append(component.sparql_fragment)
            elif component.component_type == 'triple':
                query_parts['where'].append(component.sparql_fragment)
            elif component.component_type == 'filter':
                query_parts['filters'].append(component.sparql_fragment)
            elif component.component_type == 'optional':
                query_parts['optionals'].append(f"OPTIONAL {{ {component.sparql_fragment} }}")
            elif component.component_type == 'service':
                query_parts['services'].append(component.sparql_fragment)

        # Build final query
        query_lines = []

        # Add prefixes
        if query_parts['prefixes']:
            query_lines.extend(query_parts['prefixes'])
            query_lines.append("")

        # Add SELECT clause
        if all_variables:
            select_vars = ' '.join(f'?{var}' for var in sorted(all_variables))
            query_lines.append(f"SELECT {select_vars} WHERE {{")
        else:
            query_lines.append("SELECT * WHERE {")

        # Add WHERE clauses
        for triple in query_parts['where']:
            query_lines.append(f"  {triple}")

        # Add OPTIONAL clauses
        for optional in query_parts['optionals']:
            query_lines.append(f"  {optional}")

        # Add SERVICE clauses
        for service in query_parts['services']:
            query_lines.append(f"  {service}")

        # Add FILTER clauses
        for filter_clause in query_parts['filters']:
            query_lines.append(f"  {filter_clause}")

        query_lines.append("}")
        query_lines.append("LIMIT 10")

        final_query = "\n".join(query_lines)

        return {
            'query': final_query,
            'variables': list(all_variables),
            'validation_issues': validation_issues,
            'component_count': len([c for c in components if c.validation_passed]),
            'confidence': sum(c.confidence for c in components if c.validation_passed) / max(len(components), 1)
        }

    def get_available_prefixes(self) -> Dict[str, str]:
        """Get all known prefixes for this endpoint."""
        # Combine discovered prefixes with common ones
        common_prefixes = {
            'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
            'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
            'owl': 'http://www.w3.org/2002/07/owl#',
            'xsd': 'http://www.w3.org/2001/XMLSchema#',
            'skos': 'http://www.w3.org/2004/02/skos/core#',
            'dc': 'http://purl.org/dc/elements/1.1/',
            'dcterms': 'http://purl.org/dc/terms/',
            'foaf': 'http://xmlns.com/foaf/0.1/',
        }

        result = common_prefixes.copy()
        result.update(self.available_prefixes)
        return result

    def suggest_similar_predicates(self, predicate: str, limit: int = 5) -> List[str]:
        """Find similar predicates based on naming patterns and usage."""
        suggestions = []
        pred_name = predicate.split('/')[-1].lower()

        # Look through VOID property data
        for dataset in self.void_data:
            for prop in dataset.property_partitions.keys():
                prop_name = prop.split('/')[-1].lower()
                # Simple similarity based on shared words
                if self._calculate_similarity(pred_name, prop_name) > 0.3:
                    suggestions.append(prop)

        return suggestions[:limit]

    # Helper methods

    def _extract_patterns_from_void(self) -> None:
        """Extract query patterns from VOID data."""
        for dataset in self.void_data:
            # Create patterns for common classes
            for class_uri, count in dataset.class_partitions.items():
                if count > 100:  # Only significant classes
                    class_name = class_uri.split('/')[-1]
                    pattern = QueryPattern(
                        pattern_name=f"list_{class_name.lower()}",
                        description=f"List instances of {class_name} ({count} available)",
                        sparql_template=f"""
SELECT ?entity ?label WHERE {{
  ?entity rdf:type <{class_uri}> .
  OPTIONAL {{ ?entity rdfs:label ?label }}
}}
LIMIT 10""",
                        confidence=min(0.9, count / 10000)  # Higher confidence for more data
                    )
                    self.discovered_patterns.append(pattern)

    def _matches_datatype(self, value: str, expected_type: str) -> bool:
        """Check if a value matches expected XSD datatype."""
        if 'xsd:string' in expected_type:
            return '"' in value
        elif 'xsd:integer' in expected_type:
            return value.isdigit()
        elif 'xsd:boolean' in expected_type:
            return value.lower() in ['true', 'false']
        elif 'xsd:dateTime' in expected_type:
            return 'T' in value and '-' in value
        return True  # Default to true for unknown types

    def _validate_uri_syntax(self, subject: str, predicate: str, object_val: str) -> Dict[str, Any]:
        """Validate URI syntax for SPARQL compliance."""
        issues = []
        suggestions = []

        # Check for problematic characters in URI references
        problematic_chars = [',', ' ', '(', ')', '[', ']', '{', '}', '"', "'", '\\', '\n', '\r', '\t']

        for term, term_type in [(subject, 'subject'), (predicate, 'predicate'), (object_val, 'object')]:
            # Skip variables and literals
            if term.startswith('?') or term.startswith('$') or '^^' in term or term.startswith('"'):
                continue

            # Check for problematic characters in prefixed names and URIs
            for char in problematic_chars:
                if char in term:
                    issues.append(f"{term_type.capitalize()} '{term}' contains problematic character '{char}' that may break SPARQL syntax")

                    # Provide specific fix suggestions
                    if char == ',':
                        fixed_term = term.replace(',', '%2C')
                        suggestions.append(f"Replace '{term}' with '{fixed_term}' (URL-encoded comma)")
                    elif char == ' ':
                        fixed_term = term.replace(' ', '%20')
                        suggestions.append(f"Replace '{term}' with '{fixed_term}' (URL-encoded space)")
                    elif char in ['(', ')']:
                        fixed_term = term.replace('(', '%28').replace(')', '%29')
                        suggestions.append(f"Replace '{term}' with '{fixed_term}' (URL-encoded parentheses)")
                    else:
                        suggestions.append(f"URL-encode or properly escape the '{char}' character in '{term}'")

        return {'issues': issues, 'suggestions': suggestions}

    def _calculate_similarity(self, word1: str, word2: str) -> float:
        """Simple word similarity calculation."""
        if word1 == word2:
            return 1.0

        # Check for common substrings
        common_chars = set(word1) & set(word2)
        return len(common_chars) / max(len(word1), len(word2), 1)


def create_schema_tools(endpoint_url: str, skip_discovery: bool = False) -> SchemaQueryTools:
    """Factory function to create schema tools for an endpoint."""
    tools = SchemaQueryTools(endpoint_url, skip_discovery=skip_discovery)

    if not skip_discovery:
        # Auto-discover capabilities only if not skipped
        capabilities = tools.discover_endpoint_capabilities()
        # Try to load VOID data
        tools.load_void_data()
    else:
        print("Skipping auto-discovery - using provided schema data only")

    return tools


# Example usage and patterns
EXAMPLE_USAGE = '''
# Initialize tools
tools = create_schema_tools("https://query.wikidata.org/sparql")

# Find predicates for a class
predicates = tools.find_predicates_for_class("http://www.wikidata.org/entity/Q5")

# Validate a triple pattern
validation = tools.validate_triple_pattern("?person", "wdt:P31", "wd:Q5")

# Get query suggestions
patterns = tools.suggest_query_patterns("find people born in Paris")

# Build query incrementally
components = [
    QueryComponent('triple', '?person wdt:P31 wd:Q5', variables={'person'}),
    QueryComponent('triple', '?person wdt:P19 wd:Q90', variables={'person'})
]
result = tools.build_query_incrementally(components)
print(result['query'])
'''

if __name__ == "__main__":
    print("Schema-Driven Query Tools")
    print("=" * 50)
    print(EXAMPLE_USAGE)