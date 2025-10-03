"""
Example usage of the Prompt Engineering and Template System.

This module demonstrates how to use the prompt engine for
SPARQL query generation with ontology integration.
"""

from pathlib import Path
from typing import Dict

from ..core.types import SchemaInfo, OntologyInfo, OWLClass, OWLProperty, OWLPropertyType
from ..schema.ontology_mapper import OntologyMapper
from .prompt_engine import (
    PromptEngine,
    PromptTemplate,
    PromptContext,
    FewShotExample,
    QueryScenario,
    create_prompt_engine,
    quick_prompt
)


def example_basic_prompt():
    """Example: Generate a basic prompt."""
    print("=" * 80)
    print("EXAMPLE 1: Basic Prompt Generation")
    print("=" * 80)

    # Create engine
    engine = create_prompt_engine()

    # Generate prompt for a simple query
    user_query = "Find all proteins from human organism"

    prompt = engine.generate_prompt(user_query)

    print(f"\nUser Query: {user_query}")
    print("\n" + "-" * 80)
    print("Generated Prompt:")
    print("-" * 80)
    print(prompt)


def example_with_schema():
    """Example: Generate prompt with schema information."""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Prompt with Schema Information")
    print("=" * 80)

    # Create schema info
    schema_info = SchemaInfo()
    schema_info.classes.update([
        "http://purl.uniprot.org/core/Protein",
        "http://purl.uniprot.org/core/Taxon",
        "http://purl.obolibrary.org/obo/GO_0003674"
    ])
    schema_info.properties.update([
        "http://purl.uniprot.org/core/organism",
        "http://purl.uniprot.org/core/encodedBy",
        "http://purl.uniprot.org/core/classifiedWith"
    ])
    schema_info.namespaces = {
        "up": "http://purl.uniprot.org/core/",
        "taxon": "http://purl.uniprot.org/taxonomy/",
        "obo": "http://purl.obolibrary.org/obo/"
    }
    schema_info.class_counts = {
        "http://purl.uniprot.org/core/Protein": 500000,
        "http://purl.uniprot.org/core/Taxon": 50000,
        "http://purl.obolibrary.org/obo/GO_0003674": 10000
    }

    # Create engine
    engine = create_prompt_engine()

    # Generate prompt
    user_query = "Find proteins encoded by genes on chromosome 7"

    prompt = engine.generate_prompt(
        user_query=user_query,
        schema_info=schema_info
    )

    print(f"\nUser Query: {user_query}")
    print("\n" + "-" * 80)
    print("Generated Prompt:")
    print("-" * 80)
    print(prompt)


def example_with_ontology():
    """Example: Generate prompt with ontology context."""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Prompt with Ontology Integration")
    print("=" * 80)

    # Create ontology info
    ontology_info = OntologyInfo(
        uri="http://purl.uniprot.org/core/",
        title="UniProt Core Ontology",
        description="Ontology for protein and gene data"
    )

    # Add some OWL classes
    protein_class = OWLClass(
        uri="http://purl.uniprot.org/core/Protein",
        label=["Protein"],
        comment=["A biological macromolecule composed of one or more chains of amino acids"],
        instances_count=500000
    )

    taxon_class = OWLClass(
        uri="http://purl.uniprot.org/core/Taxon",
        label=["Taxon"],
        comment=["A group of organisms at any hierarchical level"],
        instances_count=50000
    )

    ontology_info.classes[protein_class.uri] = protein_class
    ontology_info.classes[taxon_class.uri] = taxon_class

    # Add some properties
    organism_prop = OWLProperty(
        uri="http://purl.uniprot.org/core/organism",
        label=["organism"],
        comment=["Links a protein to its source organism"],
        property_type=OWLPropertyType.OBJECT_PROPERTY,
        domain=["http://purl.uniprot.org/core/Protein"],
        range=["http://purl.uniprot.org/core/Taxon"]
    )

    ontology_info.properties[organism_prop.uri] = organism_prop

    ontology_info.namespaces = {
        "up": "http://purl.uniprot.org/core/",
        "taxon": "http://purl.uniprot.org/taxonomy/"
    }

    # Create engine
    engine = create_prompt_engine()

    # Generate prompt
    user_query = "Find all human proteins and their functions"

    prompt = engine.generate_prompt(
        user_query=user_query,
        ontology_info=ontology_info
    )

    print(f"\nUser Query: {user_query}")
    print("\n" + "-" * 80)
    print("Generated Prompt:")
    print("-" * 80)
    print(prompt)


def example_aggregation_query():
    """Example: Generate prompt for aggregation query."""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Aggregation Query Prompt")
    print("=" * 80)

    # Create engine
    engine = create_prompt_engine()

    # Generate prompt for aggregation
    user_query = "Count the number of proteins per organism"

    prompt = engine.generate_prompt(
        user_query=user_query,
        scenario=QueryScenario.AGGREGATION
    )

    print(f"\nUser Query: {user_query}")
    print(f"Scenario: AGGREGATION")
    print("\n" + "-" * 80)
    print("Generated Prompt:")
    print("-" * 80)
    print(prompt)


def example_complex_join_query():
    """Example: Generate prompt for complex join query."""
    print("\n" + "=" * 80)
    print("EXAMPLE 5: Complex Join Query Prompt")
    print("=" * 80)

    # Create schema info
    schema_info = SchemaInfo()
    schema_info.namespaces = {
        "obo": "http://purl.obolibrary.org/obo/",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#"
    }

    # Create engine
    engine = create_prompt_engine()

    # Generate prompt
    user_query = "Find genes associated with cancer diseases and their functions"

    prompt = engine.generate_prompt(
        user_query=user_query,
        schema_info=schema_info,
        scenario=QueryScenario.COMPLEX_JOIN
    )

    print(f"\nUser Query: {user_query}")
    print(f"Scenario: COMPLEX_JOIN")
    print("\n" + "-" * 80)
    print("Generated Prompt:")
    print("-" * 80)
    print(prompt)


def example_full_text_search():
    """Example: Generate prompt for full-text search."""
    print("\n" + "=" * 80)
    print("EXAMPLE 6: Full-Text Search Query Prompt")
    print("=" * 80)

    # Create engine
    engine = create_prompt_engine()

    # Generate prompt
    user_query = "Search for genes related to Alzheimer's disease"

    prompt = engine.generate_prompt(
        user_query=user_query,
        scenario=QueryScenario.FULL_TEXT
    )

    print(f"\nUser Query: {user_query}")
    print(f"Scenario: FULL_TEXT")
    print("\n" + "-" * 80)
    print("Generated Prompt:")
    print("-" * 80)
    print(prompt)


def example_auto_scenario_detection():
    """Example: Automatic scenario detection."""
    print("\n" + "=" * 80)
    print("EXAMPLE 7: Automatic Scenario Detection")
    print("=" * 80)

    queries = [
        "Find all proteins from human",
        "Count the number of variants per chromosome",
        "Search for genes containing 'BRCA'",
        "Find genes associated with diseases and their pathways"
    ]

    engine = create_prompt_engine()

    for query in queries:
        scenario = engine.detect_scenario(query)
        print(f"\nQuery: {query}")
        print(f"Detected Scenario: {scenario.value}")


def example_custom_template():
    """Example: Using custom template."""
    print("\n" + "=" * 80)
    print("EXAMPLE 8: Custom Template")
    print("=" * 80)

    custom_template_str = """Generate a SPARQL query for: {{ user_query }}

Available Ontologies:
{{ ontology_context }}

Please provide:
1. A SELECT query
2. Include LIMIT 10
3. Add comments

SPARQL Query:
"""

    # Create custom template
    template = PromptTemplate(template_string=custom_template_str)

    # Create context
    context = PromptContext(
        user_query="Find all diseases",
        available_prefixes={
            "mondo": "http://purl.obolibrary.org/obo/MONDO_",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#"
        }
    )

    # Render
    prompt = template.render(context)

    print("\nCustom Template:")
    print("-" * 80)
    print(prompt)


def example_add_custom_example():
    """Example: Adding custom few-shot examples."""
    print("\n" + "=" * 80)
    print("EXAMPLE 9: Adding Custom Few-Shot Examples")
    print("=" * 80)

    # Create engine
    engine = create_prompt_engine()

    # Add custom example
    custom_example = FewShotExample(
        question="Find proteins with molecular weight greater than 50000",
        sparql="""PREFIX up: <http://purl.uniprot.org/core/>

SELECT ?protein ?weight
WHERE {
  ?protein a up:Protein ;
           up:molecularWeight ?weight .

  FILTER(?weight > 50000)
}
LIMIT 100""",
        explanation="Filter proteins by molecular weight using FILTER clause",
        scenario=QueryScenario.FILTER,
        difficulty=2,
        tags=["protein", "filter", "numeric"]
    )

    engine.add_example(custom_example)

    print("Added custom example:")
    print(f"  Question: {custom_example.question}")
    print(f"  Scenario: {custom_example.scenario.value}")
    print(f"  Difficulty: {custom_example.difficulty}")
    print(f"  Tags: {', '.join(custom_example.tags)}")


def example_multi_scenario():
    """Example: Generate prompts for multiple scenarios."""
    print("\n" + "=" * 80)
    print("EXAMPLE 10: Multi-Scenario Prompt Generation")
    print("=" * 80)

    engine = create_prompt_engine()

    user_query = "Find genes and their associated diseases"

    scenarios = [
        QueryScenario.BASIC,
        QueryScenario.COMPLEX_JOIN
    ]

    prompts = engine.generate_multi_scenario_prompts(
        user_query=user_query,
        scenarios=scenarios
    )

    for scenario, prompt in prompts.items():
        print(f"\n{scenario.value.upper()} Scenario:")
        print("-" * 80)
        print(prompt[:500] + "...\n")  # Print first 500 chars


def example_with_constraints():
    """Example: Generate prompt with constraints."""
    print("\n" + "=" * 80)
    print("EXAMPLE 11: Prompt with Constraints")
    print("=" * 80)

    engine = create_prompt_engine()

    user_query = "Find all proteins"

    prompt = engine.generate_prompt(
        user_query=user_query,
        constraints={
            "LIMIT": 100,
            "timeout": "30 seconds",
            "distinct": "required",
            "performance": "optimize for speed"
        }
    )

    print(f"\nUser Query: {user_query}")
    print("\n" + "-" * 80)
    print("Generated Prompt:")
    print("-" * 80)
    print(prompt)


def example_quick_prompt():
    """Example: Using quick_prompt utility."""
    print("\n" + "=" * 80)
    print("EXAMPLE 12: Quick Prompt Utility")
    print("=" * 80)

    user_query = "Find all genes on chromosome 17"

    # Quick prompt without creating engine
    prompt = quick_prompt(user_query)

    print(f"\nUser Query: {user_query}")
    print("\n" + "-" * 80)
    print("Generated Prompt (first 500 chars):")
    print("-" * 80)
    print(prompt[:500] + "...")


def run_all_examples():
    """Run all examples."""
    examples = [
        example_basic_prompt,
        example_with_schema,
        example_with_ontology,
        example_aggregation_query,
        example_complex_join_query,
        example_full_text_search,
        example_auto_scenario_detection,
        example_custom_template,
        example_add_custom_example,
        example_multi_scenario,
        example_with_constraints,
        example_quick_prompt
    ]

    for example_func in examples:
        try:
            example_func()
            print("\n")
        except Exception as e:
            print(f"\nError in {example_func.__name__}: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    # Run specific example
    import sys

    if len(sys.argv) > 1:
        example_num = sys.argv[1]
        example_map = {
            "1": example_basic_prompt,
            "2": example_with_schema,
            "3": example_with_ontology,
            "4": example_aggregation_query,
            "5": example_complex_join_query,
            "6": example_full_text_search,
            "7": example_auto_scenario_detection,
            "8": example_custom_template,
            "9": example_add_custom_example,
            "10": example_multi_scenario,
            "11": example_with_constraints,
            "12": example_quick_prompt
        }

        if example_num in example_map:
            example_map[example_num]()
        elif example_num == "all":
            run_all_examples()
        else:
            print(f"Unknown example: {example_num}")
            print("Available examples: 1-12, or 'all'")
    else:
        # Run all examples by default
        run_all_examples()
