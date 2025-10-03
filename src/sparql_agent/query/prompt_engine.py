"""
Prompt Engineering and Template System for SPARQL Query Generation.

This module provides a comprehensive templating system for generating prompts
that guide LLMs to generate SPARQL queries. It includes:
- Jinja2-based templates with context-aware generation
- Few-shot examples for different query patterns
- Schema-aware prompts with ontology integration
- Support for various query scenarios (basic, complex joins, aggregation, full-text)
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from jinja2 import Environment, FileSystemLoader, Template, select_autoescape

from ..core.types import OntologyInfo, SchemaInfo, OWLClass, OWLProperty
from ..schema.ontology_mapper import OntologyMapper, VocabularyInfo


class QueryScenario(Enum):
    """Types of SPARQL query scenarios."""
    BASIC = "basic"
    COMPLEX_JOIN = "complex_join"
    AGGREGATION = "aggregation"
    FULL_TEXT = "full_text"
    GRAPH_PATTERN = "graph_pattern"
    FEDERATION = "federation"
    PROPERTY_PATH = "property_path"
    OPTIONAL = "optional"
    FILTER = "filter"
    SUBQUERY = "subquery"


@dataclass
class PromptContext:
    """
    Context information for prompt generation.

    Attributes:
        user_query: Natural language query from the user
        schema_info: Discovered schema information
        ontology_info: Ontology information (if available)
        available_prefixes: Available namespace prefixes
        example_queries: Example queries for few-shot learning
        ontology_mapper: Mapper for vocabulary resolution
        scenario: Query scenario type
        constraints: Additional constraints (limit, timeout, etc.)
        metadata: Additional metadata for context
    """
    user_query: str
    schema_info: Optional[SchemaInfo] = None
    ontology_info: Optional[OntologyInfo] = None
    available_prefixes: Dict[str, str] = field(default_factory=dict)
    example_queries: List[Dict[str, str]] = field(default_factory=list)
    ontology_mapper: Optional[OntologyMapper] = None
    scenario: QueryScenario = QueryScenario.BASIC
    constraints: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_ontology_context(self) -> str:
        """Generate ontology context summary for the prompt."""
        if not self.ontology_info:
            return "No ontology information available."

        lines = []
        lines.append(f"Ontology: {self.ontology_info.title or self.ontology_info.uri}")

        if self.ontology_info.description:
            lines.append(f"Description: {self.ontology_info.description}")

        # Top classes
        if self.ontology_info.classes:
            top_classes = list(self.ontology_info.classes.values())[:10]
            lines.append("\nKey Classes:")
            for owl_class in top_classes:
                label = owl_class.get_primary_label()
                comment = owl_class.get_primary_comment()
                if comment:
                    lines.append(f"  - {label}: {comment[:100]}...")
                else:
                    lines.append(f"  - {label}")

        # Top properties
        if self.ontology_info.properties:
            top_props = list(self.ontology_info.properties.values())[:10]
            lines.append("\nKey Properties:")
            for owl_prop in top_props:
                label = owl_prop.get_primary_label()
                comment = owl_prop.get_primary_comment()
                if comment:
                    lines.append(f"  - {label}: {comment[:100]}...")
                else:
                    lines.append(f"  - {label}")

        return "\n".join(lines)

    def get_schema_summary(self) -> str:
        """Generate schema summary for the prompt."""
        if not self.schema_info:
            return "No schema information available."

        lines = []

        # Top classes
        top_classes = self.schema_info.get_most_common_classes(10)
        if top_classes:
            lines.append("Most Common Classes:")
            for class_uri, count in top_classes:
                lines.append(f"  - {class_uri} ({count:,} instances)")

        # Top properties
        top_properties = self.schema_info.get_most_common_properties(10)
        if top_properties:
            lines.append("\nMost Common Properties:")
            for prop_uri, count in top_properties:
                lines.append(f"  - {prop_uri} ({count:,} uses)")

        # Property domains and ranges
        if self.schema_info.property_domains:
            lines.append("\nProperty Domains and Ranges (sample):")
            sample_props = list(self.schema_info.property_domains.items())[:5]
            for prop, domains in sample_props:
                ranges = self.schema_info.property_ranges.get(prop, set())
                lines.append(f"  - {prop}")
                if domains:
                    lines.append(f"    Domain: {', '.join(list(domains)[:3])}")
                if ranges:
                    lines.append(f"    Range: {', '.join(list(ranges)[:3])}")

        return "\n".join(lines)

    def get_prefix_declarations(self) -> str:
        """Generate PREFIX declarations for SPARQL."""
        if not self.available_prefixes:
            return ""

        lines = []
        for prefix, uri in sorted(self.available_prefixes.items()):
            lines.append(f"PREFIX {prefix}: <{uri}>")

        return "\n".join(lines)

    def get_examples_formatted(self) -> str:
        """Format example queries for the prompt."""
        if not self.example_queries:
            return "No examples available."

        lines = []
        for i, example in enumerate(self.example_queries, 1):
            lines.append(f"Example {i}:")
            lines.append(f"Question: {example.get('question', 'N/A')}")
            lines.append(f"SPARQL:")
            lines.append(example.get('sparql', 'N/A'))
            lines.append("")

        return "\n".join(lines)


@dataclass
class FewShotExample:
    """
    A few-shot example for prompt learning.

    Attributes:
        question: Natural language question
        sparql: Corresponding SPARQL query
        explanation: Explanation of the query
        scenario: Query scenario this example demonstrates
        difficulty: Difficulty level (1-5)
        tags: Tags for categorization
    """
    question: str
    sparql: str
    explanation: Optional[str] = None
    scenario: QueryScenario = QueryScenario.BASIC
    difficulty: int = 1
    tags: List[str] = field(default_factory=list)


class PromptTemplate:
    """
    Jinja2-based prompt template for SPARQL query generation.

    This class provides flexible templating with context injection,
    few-shot examples, and ontology awareness.
    """

    def __init__(
        self,
        template_string: Optional[str] = None,
        template_file: Optional[Path] = None,
        template_dir: Optional[Path] = None,
        scenario: QueryScenario = QueryScenario.BASIC
    ):
        """
        Initialize the prompt template.

        Args:
            template_string: Template string (if provided directly)
            template_file: Path to template file
            template_dir: Directory containing templates
            scenario: Query scenario type
        """
        self.scenario = scenario

        if template_dir:
            # Use file system loader
            env = Environment(
                loader=FileSystemLoader(str(template_dir)),
                autoescape=select_autoescape(['html', 'xml']),
                trim_blocks=True,
                lstrip_blocks=True
            )

            if template_file:
                template_name = template_file.name
                self.template = env.get_template(template_name)
            else:
                # Use default template for scenario
                default_name = f"{scenario.value}.j2"
                try:
                    self.template = env.get_template(default_name)
                except Exception:
                    # Fall back to base template
                    self.template = env.from_string(self._get_default_template())
        elif template_string:
            # Use string template
            env = Environment(
                autoescape=select_autoescape(['html', 'xml']),
                trim_blocks=True,
                lstrip_blocks=True
            )
            self.template = env.from_string(template_string)
        else:
            # Use default template
            env = Environment(
                autoescape=select_autoescape(['html', 'xml']),
                trim_blocks=True,
                lstrip_blocks=True
            )
            self.template = env.from_string(self._get_default_template())

    def _get_default_template(self) -> str:
        """Get default template based on scenario."""
        if self.scenario == QueryScenario.BASIC:
            return self._get_basic_template()
        elif self.scenario == QueryScenario.COMPLEX_JOIN:
            return self._get_complex_join_template()
        elif self.scenario == QueryScenario.AGGREGATION:
            return self._get_aggregation_template()
        elif self.scenario == QueryScenario.FULL_TEXT:
            return self._get_full_text_template()
        else:
            return self._get_basic_template()

    def _get_basic_template(self) -> str:
        """Basic SPARQL generation template."""
        return """You are a SPARQL query generation expert. Generate a valid SPARQL query for the following natural language question.

## Question
{{ user_query }}

## Available Ontologies
{{ ontology_context }}

## Schema Information
{{ schema_summary }}

## Available Prefixes
{{ prefix_declarations }}

{% if examples %}
## Examples
{{ examples }}
{% endif %}

## Instructions
1. Generate a valid SPARQL 1.1 query
2. Use appropriate prefixes from the available list
3. Leverage ontology classes and properties when available
4. Include comments explaining the query logic
5. Use proper indentation and formatting
6. Consider query performance and avoid expensive patterns

{% if constraints %}
## Constraints
{% for key, value in constraints.items() %}
- {{ key }}: {{ value }}
{% endfor %}
{% endif %}

## Generated SPARQL Query
Please provide the SPARQL query below:
"""

    def _get_complex_join_template(self) -> str:
        """Template for complex joins across datasets."""
        return """You are a SPARQL query generation expert. Generate a SPARQL query that performs complex joins across multiple datasets.

## Question
{{ user_query }}

## Available Ontologies
{{ ontology_context }}

## Schema Information
{{ schema_summary }}

## Available Prefixes
{{ prefix_declarations }}

{% if examples %}
## Examples of Complex Joins
{{ examples }}
{% endif %}

## Instructions for Complex Joins
1. Identify the entities and relationships to join
2. Use appropriate join patterns (INNER, LEFT OUTER via OPTIONAL)
3. Consider using SERVICE for federated queries if joining across endpoints
4. Use FILTER to constrain join conditions
5. Pay attention to performance with large joins
6. Consider using DISTINCT if duplicates are a concern
7. Use property paths for transitive relationships if needed

## Join Patterns to Consider
- Basic Triple Pattern Join: ?s p1 ?o1 . ?o1 p2 ?o2
- Optional Join: ?s p1 ?o1 . OPTIONAL { ?o1 p2 ?o2 }
- Federated Join: SERVICE <endpoint> { ?s p1 ?o1 } . ?o1 p2 ?o2
- Property Path: ?s p1/p2/p3 ?o  # transitive path

{% if constraints %}
## Constraints
{% for key, value in constraints.items() %}
- {{ key }}: {{ value }}
{% endfor %}
{% endif %}

## Generated SPARQL Query
Please provide the SPARQL query with complex joins:
"""

    def _get_aggregation_template(self) -> str:
        """Template for aggregation queries."""
        return """You are a SPARQL query generation expert. Generate a SPARQL query with aggregation functions.

## Question
{{ user_query }}

## Available Ontologies
{{ ontology_context }}

## Schema Information
{{ schema_summary }}

## Available Prefixes
{{ prefix_declarations }}

{% if examples %}
## Examples of Aggregation Queries
{{ examples }}
{% endif %}

## Instructions for Aggregation
1. Identify the aggregation type needed: COUNT, SUM, AVG, MIN, MAX, GROUP_CONCAT, SAMPLE
2. Determine grouping variables (GROUP BY clause)
3. Use HAVING to filter aggregated results
4. Consider using sub-queries for complex aggregations
5. Handle NULL values appropriately
6. Use DISTINCT within aggregates if needed (e.g., COUNT(DISTINCT ?x))

## Common Aggregation Patterns
- Count instances: SELECT (COUNT(?s) AS ?count) WHERE { ?s a :Class }
- Group by property: SELECT ?type (COUNT(?s) AS ?count) WHERE { ?s a ?type } GROUP BY ?type
- Average: SELECT (AVG(?value) AS ?average) WHERE { ?s :property ?value }
- Multiple aggregates: SELECT ?group (COUNT(?x) AS ?count) (AVG(?y) AS ?avg) WHERE { ... } GROUP BY ?group

{% if constraints %}
## Constraints
{% for key, value in constraints.items() %}
- {{ key }}: {{ value }}
{% endfor %}
{% endif %}

## Generated SPARQL Query
Please provide the SPARQL query with aggregation:
"""

    def _get_full_text_template(self) -> str:
        """Template for full-text search queries."""
        return """You are a SPARQL query generation expert. Generate a SPARQL query with full-text search capabilities.

## Question
{{ user_query }}

## Available Ontologies
{{ ontology_context }}

## Schema Information
{{ schema_summary }}

## Available Prefixes
{{ prefix_declarations }}

{% if examples %}
## Examples of Full-Text Search Queries
{{ examples }}
{% endif %}

## Instructions for Full-Text Search
1. Identify the search terms and target properties
2. Use the appropriate full-text search predicate based on the endpoint:
   - Virtuoso: bif:contains
   - Blazegraph: bds:search
   - Apache Jena: text:query
   - Standard SPARQL 1.1: FILTER with CONTAINS, REGEX, or STRSTARTS
3. Consider case sensitivity with LCASE() or UCASE()
4. Use proper escaping for special characters in search terms
5. Combine with FILTER for additional constraints
6. Consider performance with large text indexes

## Full-Text Search Patterns
- Basic contains: FILTER(CONTAINS(LCASE(?label), "search term"))
- Regex: FILTER(REGEX(?label, "pattern", "i"))
- Virtuoso: ?s ?p ?o . ?o bif:contains "'search term'"
- Blazegraph: ?s bds:search "search term" . ?s bds:matchAllTerms "true"

{% if constraints %}
## Constraints
{% for key, value in constraints.items() %}
- {{ key }}: {{ value }}
{% endfor %}
{% endif %}

## Generated SPARQL Query
Please provide the SPARQL query with full-text search:
"""

    def render(self, context: PromptContext) -> str:
        """
        Render the template with the given context.

        Args:
            context: Prompt context with all necessary information

        Returns:
            Rendered prompt string
        """
        template_vars = {
            "user_query": context.user_query,
            "ontology_context": context.get_ontology_context(),
            "schema_summary": context.get_schema_summary(),
            "prefix_declarations": context.get_prefix_declarations(),
            "examples": context.get_examples_formatted() if context.example_queries else None,
            "constraints": context.constraints,
            "metadata": context.metadata,
            "scenario": self.scenario.value
        }

        return self.template.render(**template_vars)


class PromptEngine:
    """
    Main engine for prompt generation and management.

    This class orchestrates prompt generation with template selection,
    example retrieval, and context building.
    """

    def __init__(
        self,
        template_dir: Optional[Path] = None,
        ontology_mapper: Optional[OntologyMapper] = None
    ):
        """
        Initialize the prompt engine.

        Args:
            template_dir: Directory containing template files
            ontology_mapper: Ontology mapper for vocabulary resolution
        """
        self.template_dir = template_dir
        self.ontology_mapper = ontology_mapper or OntologyMapper()
        self.examples_db: Dict[QueryScenario, List[FewShotExample]] = {
            scenario: [] for scenario in QueryScenario
        }
        self._load_default_examples()

    def _load_default_examples(self):
        """Load default few-shot examples."""
        # Basic queries
        self.examples_db[QueryScenario.BASIC].extend([
            FewShotExample(
                question="Find all proteins from human",
                sparql="""PREFIX up: <http://purl.uniprot.org/core/>
PREFIX taxon: <http://purl.uniprot.org/taxonomy/>

SELECT ?protein ?name
WHERE {
  ?protein a up:Protein ;
           up:organism taxon:9606 ;
           up:recommendedName ?name .
}
LIMIT 100""",
                explanation="Basic query to find proteins filtered by organism (human, taxon:9606)",
                difficulty=1,
                tags=["protein", "organism", "filter"]
            ),
            FewShotExample(
                question="List all diseases in the dataset",
                sparql="""PREFIX mondo: <http://purl.obolibrary.org/obo/MONDO_>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?disease ?label
WHERE {
  ?disease a mondo:Disease ;
           rdfs:label ?label .
}
LIMIT 100""",
                explanation="Query to list diseases using MONDO ontology",
                difficulty=1,
                tags=["disease", "ontology", "list"]
            )
        ])

        # Complex join queries
        self.examples_db[QueryScenario.COMPLEX_JOIN].extend([
            FewShotExample(
                question="Find genes associated with diseases and their functions",
                sparql="""PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?gene ?geneName ?disease ?diseaseName ?function
WHERE {
  # Gene to disease association
  ?gene a obo:SO_0000704 ;
        rdfs:label ?geneName ;
        obo:RO_0002200 ?disease .

  # Disease information
  ?disease a obo:MONDO_0000001 ;
           rdfs:label ?diseaseName .

  # Gene function (optional)
  OPTIONAL {
    ?gene obo:RO_0000085 ?function .
  }
}
LIMIT 100""",
                explanation="Join across genes, diseases, and functions using OBO relations",
                difficulty=3,
                tags=["gene", "disease", "function", "join", "optional"]
            )
        ])

        # Aggregation queries
        self.examples_db[QueryScenario.AGGREGATION].extend([
            FewShotExample(
                question="Count the number of proteins per organism",
                sparql="""PREFIX up: <http://purl.uniprot.org/core/>
PREFIX taxon: <http://purl.uniprot.org/taxonomy/>

SELECT ?organism ?name (COUNT(?protein) AS ?count)
WHERE {
  ?protein a up:Protein ;
           up:organism ?organism .

  ?organism a up:Taxon ;
            up:scientificName ?name .
}
GROUP BY ?organism ?name
ORDER BY DESC(?count)
LIMIT 20""",
                explanation="Aggregate proteins by organism with counting",
                difficulty=2,
                tags=["protein", "organism", "count", "aggregation", "group-by"]
            ),
            FewShotExample(
                question="What is the average number of variants per gene?",
                sparql="""PREFIX obo: <http://purl.obolibrary.org/obo/>

SELECT (AVG(?variantCount) AS ?avgVariants)
WHERE {
  {
    SELECT ?gene (COUNT(?variant) AS ?variantCount)
    WHERE {
      ?gene a obo:SO_0000704 .
      ?variant obo:RO_0002205 ?gene .
    }
    GROUP BY ?gene
  }
}""",
                explanation="Use subquery to calculate average variants per gene",
                difficulty=3,
                tags=["variant", "gene", "average", "subquery"]
            )
        ])

        # Full-text search queries
        self.examples_db[QueryScenario.FULL_TEXT].extend([
            FewShotExample(
                question="Search for genes related to 'cancer'",
                sparql="""PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX obo: <http://purl.obolibrary.org/obo/>

SELECT ?gene ?label ?description
WHERE {
  ?gene a obo:SO_0000704 ;
        rdfs:label ?label .

  OPTIONAL { ?gene obo:IAO_0000115 ?description }

  FILTER(
    CONTAINS(LCASE(?label), "cancer") ||
    CONTAINS(LCASE(?description), "cancer")
  )
}
LIMIT 50""",
                explanation="Full-text search across gene labels and descriptions",
                difficulty=2,
                tags=["gene", "search", "text", "filter"]
            )
        ])

    def add_example(self, example: FewShotExample):
        """Add a few-shot example to the database."""
        self.examples_db[example.scenario].append(example)

    def get_examples(
        self,
        scenario: QueryScenario,
        limit: int = 5,
        min_difficulty: int = 1,
        max_difficulty: int = 5,
        tags: Optional[List[str]] = None
    ) -> List[FewShotExample]:
        """
        Get relevant examples for a scenario.

        Args:
            scenario: Query scenario
            limit: Maximum number of examples to return
            min_difficulty: Minimum difficulty level
            max_difficulty: Maximum difficulty level
            tags: Filter by tags

        Returns:
            List of relevant examples
        """
        examples = self.examples_db[scenario]

        # Filter by difficulty
        examples = [
            ex for ex in examples
            if min_difficulty <= ex.difficulty <= max_difficulty
        ]

        # Filter by tags
        if tags:
            examples = [
                ex for ex in examples
                if any(tag in ex.tags for tag in tags)
            ]

        return examples[:limit]

    def detect_scenario(self, query: str) -> QueryScenario:
        """
        Detect the most likely scenario for a query.

        Args:
            query: Natural language query

        Returns:
            Detected query scenario
        """
        query_lower = query.lower()

        # Aggregation keywords
        if any(kw in query_lower for kw in [
            "count", "average", "sum", "total", "how many", "number of",
            "maximum", "minimum", "mean", "median"
        ]):
            return QueryScenario.AGGREGATION

        # Full-text search keywords
        if any(kw in query_lower for kw in [
            "search", "find all", "contains", "matching", "like",
            "similar to", "related to"
        ]):
            return QueryScenario.FULL_TEXT

        # Complex join keywords
        if any(kw in query_lower for kw in [
            "and", "associated with", "related to", "connected to",
            "linked to", "correlated with", "along with"
        ]):
            return QueryScenario.COMPLEX_JOIN

        # Default to basic
        return QueryScenario.BASIC

    def build_context(
        self,
        user_query: str,
        schema_info: Optional[SchemaInfo] = None,
        ontology_info: Optional[OntologyInfo] = None,
        scenario: Optional[QueryScenario] = None,
        use_examples: bool = True,
        max_examples: int = 5,
        **kwargs
    ) -> PromptContext:
        """
        Build a complete prompt context.

        Args:
            user_query: Natural language query
            schema_info: Schema information
            ontology_info: Ontology information
            scenario: Query scenario (auto-detected if not provided)
            use_examples: Whether to include examples
            max_examples: Maximum number of examples
            **kwargs: Additional context parameters

        Returns:
            Complete prompt context
        """
        # Auto-detect scenario if not provided
        if scenario is None:
            scenario = self.detect_scenario(user_query)

        # Build available prefixes
        available_prefixes = {}

        if schema_info and schema_info.namespaces:
            available_prefixes.update(schema_info.namespaces)

        if ontology_info and ontology_info.namespaces:
            available_prefixes.update(ontology_info.namespaces)

        # Add common prefixes
        common_prefixes = {
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "owl": "http://www.w3.org/2002/07/owl#",
            "xsd": "http://www.w3.org/2001/XMLSchema#"
        }
        for prefix, uri in common_prefixes.items():
            if prefix not in available_prefixes:
                available_prefixes[prefix] = uri

        # Get examples
        example_queries = []
        if use_examples:
            examples = self.get_examples(scenario, limit=max_examples)
            example_queries = [
                {"question": ex.question, "sparql": ex.sparql}
                for ex in examples
            ]

        return PromptContext(
            user_query=user_query,
            schema_info=schema_info,
            ontology_info=ontology_info,
            available_prefixes=available_prefixes,
            example_queries=example_queries,
            ontology_mapper=self.ontology_mapper,
            scenario=scenario,
            constraints=kwargs.get("constraints", {}),
            metadata=kwargs.get("metadata", {})
        )

    def generate_prompt(
        self,
        user_query: str,
        schema_info: Optional[SchemaInfo] = None,
        ontology_info: Optional[OntologyInfo] = None,
        scenario: Optional[QueryScenario] = None,
        template: Optional[PromptTemplate] = None,
        use_examples: bool = True,
        max_examples: int = 5,
        **kwargs
    ) -> str:
        """
        Generate a complete prompt for SPARQL query generation.

        Args:
            user_query: Natural language query
            schema_info: Schema information
            ontology_info: Ontology information
            scenario: Query scenario (auto-detected if not provided)
            template: Custom template (uses default if not provided)
            use_examples: Whether to include examples
            max_examples: Maximum number of examples
            **kwargs: Additional parameters

        Returns:
            Complete rendered prompt
        """
        # Build context
        context = self.build_context(
            user_query=user_query,
            schema_info=schema_info,
            ontology_info=ontology_info,
            scenario=scenario,
            use_examples=use_examples,
            max_examples=max_examples,
            **kwargs
        )

        # Get or create template
        if template is None:
            template = PromptTemplate(
                template_dir=self.template_dir,
                scenario=context.scenario
            )

        # Render prompt
        return template.render(context)

    def generate_multi_scenario_prompts(
        self,
        user_query: str,
        scenarios: List[QueryScenario],
        **kwargs
    ) -> Dict[QueryScenario, str]:
        """
        Generate prompts for multiple scenarios.

        Useful for generating multiple query candidates.

        Args:
            user_query: Natural language query
            scenarios: List of scenarios to generate prompts for
            **kwargs: Additional parameters

        Returns:
            Dictionary mapping scenarios to prompts
        """
        prompts = {}

        for scenario in scenarios:
            prompt = self.generate_prompt(
                user_query=user_query,
                scenario=scenario,
                **kwargs
            )
            prompts[scenario] = prompt

        return prompts


# Utility functions

def create_prompt_engine(
    template_dir: Optional[Path] = None,
    ontology_mapper: Optional[OntologyMapper] = None
) -> PromptEngine:
    """
    Create a prompt engine with default configuration.

    Args:
        template_dir: Directory containing template files
        ontology_mapper: Ontology mapper instance

    Returns:
        Configured prompt engine
    """
    return PromptEngine(
        template_dir=template_dir,
        ontology_mapper=ontology_mapper
    )


def quick_prompt(
    user_query: str,
    schema_info: Optional[SchemaInfo] = None,
    ontology_info: Optional[OntologyInfo] = None
) -> str:
    """
    Quick utility to generate a prompt without creating an engine.

    Args:
        user_query: Natural language query
        schema_info: Schema information
        ontology_info: Ontology information

    Returns:
        Generated prompt
    """
    engine = create_prompt_engine()
    return engine.generate_prompt(
        user_query=user_query,
        schema_info=schema_info,
        ontology_info=ontology_info
    )
