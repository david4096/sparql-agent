#!/usr/bin/env python3
"""
Smart SPARQL Query Generator using Schema Tools

This module provides an intelligent query generator that uses VOID and SHEX
schema information through actionable tools rather than just context.

The LLM can use these tools to:
1. Discover available predicates step-by-step
2. Validate components before adding them
3. Build queries incrementally with real-time feedback
4. Self-correct based on schema constraints
"""

import json
import re
from typing import Dict, List, Optional, Any, Tuple

from ..llm.client import LLMClient, LLMRequest
from .schema_tools import SchemaQueryTools, QueryComponent, QueryPattern, create_schema_tools


class SmartQueryGenerator:
    """
    Schema-aware SPARQL query generator that uses tools instead of just context.

    This generator builds queries by:
    1. Analyzing user intent
    2. Using schema tools to find valid components
    3. Building query piece by piece with validation
    4. Self-correcting when validation fails
    """

    def __init__(self, endpoint_url: str, llm_client: LLMClient, skip_discovery: bool = False):
        self.endpoint_url = endpoint_url
        self.llm_client = llm_client
        self.schema_tools = create_schema_tools(endpoint_url, skip_discovery=skip_discovery)
        self.query_history: List[Dict[str, Any]] = []

    def generate_query(self, natural_language: str) -> Dict[str, Any]:
        """
        Generate a SPARQL query using schema-driven tools.

        Returns comprehensive result with query, reasoning, and validation.
        """
        print(f"🔍 Generating query for: {natural_language}")

        # Step 1: Analyze intent and suggest patterns
        patterns = self.schema_tools.suggest_query_patterns(natural_language)

        # Skip discovery if schema tools were configured to skip it
        if hasattr(self.schema_tools, '_skip_discovery') and self.schema_tools._skip_discovery:
            print("Using provided schema only - skipping endpoint discovery")
            capabilities = {
                'namespaces': self.schema_tools.get_available_prefixes(),
                'common_classes': [],
                'common_properties': [],
                'endpoint_type': 'generic',
                'supported_features': [],
            }
        else:
            # Use fallback capabilities if discovery fails or takes too long
            try:
                capabilities = self.schema_tools.discover_endpoint_capabilities()
            except Exception as e:
                print(f"Discovery failed, using fallback capabilities: {e}")
                capabilities = {
                    'namespaces': self.schema_tools.get_available_prefixes(),
                    'common_classes': [],
                    'common_properties': [],
                    'endpoint_type': 'generic',
                    'supported_features': [],
                }

        # Step 2: Use LLM with schema tools to build query
        result = self._build_query_with_tools(natural_language, patterns, capabilities)

        # Step 3: Validate and refine if needed
        if result.get('needs_refinement'):
            result = self._refine_query(result)

        # Step 4: Store in history
        self.query_history.append({
            'input': natural_language,
            'result': result,
            'timestamp': self._get_timestamp()
        })

        return result

    def _build_query_with_tools(self, intent: str, patterns: List[QueryPattern], capabilities: Dict[str, Any]) -> Dict[str, Any]:
        """Build query using available schema tools."""

        # Prepare tool descriptions for the LLM
        tools_description = self._format_tools_for_llm()

        # Create structured prompt with available tools
        prompt = f"""
You are a SPARQL query generator with access to schema-driven tools. Build a query for:
"{intent}"

AVAILABLE TOOLS:
{tools_description}

DISCOVERED PATTERNS:
{self._format_patterns_for_llm(patterns)}

ENDPOINT CAPABILITIES:
{json.dumps(capabilities, indent=2)}

INSTRUCTIONS:
1. Use the schema tools to find valid predicates and classes
2. Build the query incrementally, validating each component
3. Provide reasoning for each step
4. If validation fails, use the tools to find alternatives

Build the query step by step using the available tools.
"""

        # Use a multi-step approach
        steps = self._execute_query_building_steps(prompt, intent)

        return {
            'query': steps.get('final_query', ''),
            'steps': steps.get('steps', []),
            'validation': steps.get('validation', {}),
            'reasoning': steps.get('reasoning', ''),
            'confidence': steps.get('confidence', 0.0),
            'components_used': steps.get('components', []),
            'needs_refinement': steps.get('needs_refinement', False),
            'endpoint_url': self.endpoint_url
        }

    def _execute_query_building_steps(self, initial_prompt: str, intent: str) -> Dict[str, Any]:
        """Execute the step-by-step query building process."""

        steps = []
        components = []
        reasoning_parts = []

        # Step 1: Identify key concepts
        step1_result = self._identify_concepts(intent)
        steps.append(step1_result)
        reasoning_parts.append(f"Identified concepts: {step1_result.get('concepts', [])}")

        # Step 2: Find relevant classes
        concepts = step1_result.get('concepts', [])
        step2_result = self._find_relevant_classes(concepts)
        steps.append(step2_result)

        # Step 3: Find predicates for identified classes
        classes = step2_result.get('classes', [])
        step3_result = self._find_predicates_for_classes(classes)
        steps.append(step3_result)

        # Step 4: Build triple patterns
        predicates_info = step3_result.get('predicates', {})
        step4_result = self._build_triple_patterns(intent, classes, predicates_info)
        steps.append(step4_result)
        components.extend(step4_result.get('components', []))

        # Step 5: Validate and assemble final query
        step5_result = self._validate_and_assemble(components, intent)
        steps.append(step5_result)

        return {
            'steps': steps,
            'final_query': step5_result.get('query', ''),
            'components': components,
            'validation': step5_result.get('validation', {}),
            'reasoning': ' -> '.join(reasoning_parts),
            'confidence': step5_result.get('confidence', 0.0),
            'needs_refinement': step5_result.get('validation', {}).get('issues', []) != []
        }

    def _identify_concepts(self, intent: str) -> Dict[str, Any]:
        """Step 1: Identify key concepts from natural language."""
        print("🔍 Step 1: Identifying concepts...")

        # Simple concept extraction (could be enhanced with NER)
        concepts = []

        # Look for entity types
        entity_words = ['person', 'people', 'human', 'protein', 'gene', 'drug', 'compound', 'disease']
        for word in entity_words:
            if word in intent.lower():
                concepts.append(word)

        # Look for properties mentioned
        property_words = ['born', 'birth', 'name', 'age', 'located', 'type', 'sequence', 'length']
        properties = []
        for word in property_words:
            if word in intent.lower():
                properties.append(word)

        return {
            'step': 'identify_concepts',
            'concepts': concepts,
            'properties': properties,
            'success': True
        }

    def _find_relevant_classes(self, concepts: List[str]) -> Dict[str, Any]:
        """Step 2: Find RDF classes for identified concepts."""
        print("🔍 Step 2: Finding relevant classes...")

        classes = []

        # Use capabilities to find matching classes (skip discovery if configured)
        if hasattr(self.schema_tools, '_skip_discovery') and self.schema_tools._skip_discovery:
            capabilities = {
                'common_classes': [],
                'namespaces': self.schema_tools.get_available_prefixes()
            }
        else:
            capabilities = self.schema_tools.discover_endpoint_capabilities()
        common_classes = capabilities.get('common_classes', [])

        for concept in concepts:
            concept_lower = concept.lower()
            for class_uri in common_classes:
                class_name = class_uri.split('/')[-1].lower()
                if concept_lower in class_name or class_name in concept_lower:
                    classes.append({
                        'concept': concept,
                        'class_uri': class_uri,
                        'match_type': 'name_similarity'
                    })

        # Add some common mappings for known endpoints
        endpoint_lower = self.endpoint_url.lower()
        if 'wikidata' in endpoint_lower:
            concept_mappings = {
                'person': 'wd:Q5',
                'people': 'wd:Q5',
                'human': 'wd:Q5'
            }
            for concept in concepts:
                if concept in concept_mappings:
                    classes.append({
                        'concept': concept,
                        'class_uri': concept_mappings[concept],
                        'match_type': 'known_mapping'
                    })

        return {
            'step': 'find_classes',
            'classes': classes,
            'success': len(classes) > 0
        }

    def _find_predicates_for_classes(self, classes: List[Dict[str, str]]) -> Dict[str, Any]:
        """Step 3: Find predicates for identified classes."""
        print("🔍 Step 3: Finding predicates for classes...")

        predicates_by_class = {}

        for class_info in classes:
            class_uri = class_info['class_uri']
            print(f"   Finding predicates for {class_uri}...")

            predicates = self.schema_tools.find_predicates_for_class(class_uri, limit=10)
            predicates_by_class[class_uri] = predicates

        return {
            'step': 'find_predicates',
            'predicates': predicates_by_class,
            'success': len(predicates_by_class) > 0
        }

    def _build_triple_patterns(self, intent: str, classes: List[Dict], predicates_info: Dict) -> Dict[str, Any]:
        """Step 4: Build triple patterns based on intent and available predicates."""
        print("🔍 Step 4: Building triple patterns...")

        components = []
        intent_lower = intent.lower()

        # Build basic type patterns
        for class_info in classes:
            class_uri = class_info['class_uri']
            variable_name = class_info['concept']

            component = QueryComponent(
                component_type='triple',
                sparql_fragment=f'?{variable_name} rdf:type {class_uri} .',
                variables={variable_name},
                classes={class_uri}
            )

            # Validate this component
            validation = self.schema_tools.validate_triple_pattern(
                f'?{variable_name}', 'rdf:type', class_uri
            )
            component.validation_passed = validation['valid']
            component.confidence = validation['confidence']

            components.append(component)

        # Add property patterns based on intent
        for class_info in classes:
            class_uri = class_info['class_uri']
            variable_name = class_info['concept']
            predicates = predicates_info.get(class_uri, [])

            for pred_info in predicates[:5]:  # Limit to top 5
                predicate = pred_info['predicate']
                pred_name = predicate.split('/')[-1].lower()

                # Check if this predicate is relevant to the intent
                if any(word in pred_name for word in intent_lower.split()):
                    object_var = f'{pred_name}_value'

                    component = QueryComponent(
                        component_type='triple',
                        sparql_fragment=f'?{variable_name} <{predicate}> ?{object_var} .',
                        variables={variable_name, object_var},
                        predicates={predicate}
                    )

                    # Validate
                    validation = self.schema_tools.validate_triple_pattern(
                        f'?{variable_name}', f'<{predicate}>', f'?{object_var}'
                    )
                    component.validation_passed = validation['valid']
                    component.confidence = validation.get('confidence', 0.5)

                    if component.validation_passed:
                        components.append(component)

        return {
            'step': 'build_patterns',
            'components': components,
            'success': len(components) > 0
        }

    def _validate_and_assemble(self, components: List[QueryComponent], intent: str) -> Dict[str, Any]:
        """Step 5: Validate components and assemble final query."""
        print("🔍 Step 5: Assembling final query...")

        # Use schema tools to build the query
        result = self.schema_tools.build_query_incrementally(components)

        # Add labels if this looks like a listing query
        if any(word in intent.lower() for word in ['find', 'list', 'show', 'get']):
            # Try to add label service for better results
            if 'wikidata' in self.endpoint_url.lower():
                query = result['query']
                if 'SERVICE wikibase:label' not in query:
                    # Insert label service before the closing brace
                    lines = query.split('\n')
                    insert_point = -2  # Before "}" and "LIMIT"
                    lines.insert(insert_point, '  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }')
                    result['query'] = '\n'.join(lines)

        # Fix URI syntax issues in the final query
        uri_fix_result = self.schema_tools.fix_query_uri_issues(result['query'])
        if uri_fix_result['issues_found']:
            print(f"🔧 Applied {len(uri_fix_result['fixes_applied'])} URI fixes:")
            for fix in uri_fix_result['fixes_applied']:
                print(f"   • {fix}")
            result['query'] = uri_fix_result['query']
            result['uri_fixes_applied'] = uri_fix_result['fixes_applied']

        return {
            'step': 'validate_assemble',
            'query': result['query'],
            'validation': {
                'issues': result['validation_issues'],
                'component_count': result['component_count'],
                'confidence': result['confidence'],
                'uri_fixes': uri_fix_result.get('fixes_applied', [])
            },
            'success': len(result['validation_issues']) == 0,
            'confidence': result['confidence']
        }

    def _refine_query(self, initial_result: Dict[str, Any]) -> Dict[str, Any]:
        """Refine query based on validation issues."""
        print("🔧 Refining query based on validation issues...")

        issues = initial_result.get('validation', {}).get('issues', [])
        if not issues:
            return initial_result

        # For now, return the initial result with refinement notes
        # This could be enhanced to actually fix common issues
        initial_result['refinement_notes'] = f"Identified {len(issues)} issues but no automatic fixes applied yet"
        initial_result['needs_manual_review'] = True

        return initial_result

    def _format_tools_for_llm(self) -> str:
        """Format available tools for LLM consumption."""
        return """
Available Schema Tools:
1. find_predicates_for_class(class_uri) - Find predicates that can be used with a class
2. validate_triple_pattern(subject, predicate, object) - Validate a triple against schema
3. suggest_query_patterns(intent) - Get query pattern suggestions
4. get_available_prefixes() - Get all known prefixes for this endpoint
5. suggest_similar_predicates(predicate) - Find similar predicates
6. build_query_incrementally(components) - Assemble validated components into query

These tools provide real-time validation and suggestions based on VOID and ShEx schema data.
"""

    def _format_patterns_for_llm(self, patterns: List[QueryPattern]) -> str:
        """Format query patterns for LLM consumption."""
        if not patterns:
            return "No specific patterns found for this intent."

        formatted = []
        for i, pattern in enumerate(patterns[:5]):  # Top 5 patterns
            formatted.append(f"""
Pattern {i+1}: {pattern.pattern_name}
Description: {pattern.description}
Confidence: {pattern.confidence:.2f}
Template:
{pattern.sparql_template}
""")

        return "\n".join(formatted)

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()

    def get_query_history(self) -> List[Dict[str, Any]]:
        """Get history of generated queries."""
        return self.query_history

    def explain_query(self, sparql_query: str) -> Dict[str, Any]:
        """Explain what a SPARQL query does using schema knowledge."""
        # This could use the schema tools to provide detailed explanations
        # of what each part of the query does and why it's valid
        return {
            'explanation': 'Query explanation feature to be implemented',
            'components': [],
            'schema_compliance': {}
        }


def create_smart_generator(endpoint_url: str, llm_client: LLMClient, skip_discovery: bool = False) -> SmartQueryGenerator:
    """Factory function to create a smart generator."""
    return SmartQueryGenerator(endpoint_url, llm_client, skip_discovery=skip_discovery)


# Example usage
EXAMPLE_USAGE = '''
from sparql_agent.llm import create_anthropic_provider

# Create LLM client
llm_client = create_anthropic_provider(api_key="your-key")

# Create smart generator
generator = create_smart_generator("https://query.wikidata.org/sparql", llm_client)

# Generate query with schema tools
result = generator.generate_query("Find 5 people born in Paris")

print("Generated Query:")
print(result['query'])
print("\\nReasoning:")
print(result['reasoning'])
print("\\nValidation:")
print(result['validation'])
'''

if __name__ == "__main__":
    print("Smart SPARQL Query Generator with Schema Tools")
    print("=" * 60)
    print(EXAMPLE_USAGE)