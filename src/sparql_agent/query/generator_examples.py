"""
Practical examples of SPARQL Generator usage.

This module demonstrates real-world usage of the SPARQLGenerator
for various scenarios including template-based, LLM-based, and
hybrid query generation.
"""

from typing import Optional
from ..core.types import SchemaInfo, OntologyInfo, OWLClass, OWLProperty, EndpointInfo
from ..llm.client import LLMClient
from .generator import (
    SPARQLGenerator,
    GenerationStrategy,
    QueryTemplate,
    create_generator,
    quick_generate
)


def example_1_basic_template_generation():
    """
    Example 1: Basic template-based generation.

    This example shows how to generate simple SPARQL queries using
    built-in templates without requiring an LLM.
    """
    print("=" * 80)
    print("Example 1: Basic Template-Based Generation")
    print("=" * 80)

    # Create a simple schema
    schema = SchemaInfo(
        classes={
            "http://example.org/Person",
            "http://example.org/Organization"
        },
        properties={
            "http://example.org/name",
            "http://example.org/age",
            "http://example.org/email"
        },
        namespaces={
            "ex": "http://example.org/",
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#"
        }
    )

    # Create generator
    generator = create_generator()

    # Generate queries for different patterns
    queries = [
        ("list all persons", "List instances of a class"),
        ("how many persons", "Count instances"),
        ("show all organizations", "List with different entity type")
    ]

    for nl_query, description in queries:
        print(f"\n{description}:")
        print(f"Natural Language: '{nl_query}'")
        print("-" * 80)

        result = generator.generate(
            natural_language=nl_query,
            schema_info=schema,
            strategy=GenerationStrategy.TEMPLATE
        )

        print("Generated SPARQL:")
        print(result.query)
        print(f"\nConfidence: {result.confidence:.2f}")
        print(f"Explanation: {result.explanation}")


def example_2_biomedical_ontology():
    """
    Example 2: Biomedical queries with ontology context.

    This demonstrates generating queries with rich ontology information
    from life science domains (UniProt, Gene Ontology, etc.).
    """
    print("\n" + "=" * 80)
    print("Example 2: Biomedical Queries with Ontology Context")
    print("=" * 80)

    # Create UniProt schema
    schema = SchemaInfo(
        classes={
            "http://purl.uniprot.org/core/Protein",
            "http://purl.uniprot.org/core/Taxon",
            "http://purl.obolibrary.org/obo/GO_0008150"  # GO biological process
        },
        properties={
            "http://purl.uniprot.org/core/organism",
            "http://purl.uniprot.org/core/recommendedName",
            "http://purl.uniprot.org/core/encodedBy",
            "http://purl.uniprot.org/core/classifiedWith"
        },
        namespaces={
            "up": "http://purl.uniprot.org/core/",
            "taxon": "http://purl.uniprot.org/taxonomy/",
            "obo": "http://purl.obolibrary.org/obo/"
        }
    )

    # Create ontology info
    ontology = OntologyInfo(
        uri="http://purl.uniprot.org/core/",
        title="UniProt Core Ontology",
        description="Core ontology for protein data",
        classes={
            "http://purl.uniprot.org/core/Protein": OWLClass(
                uri="http://purl.uniprot.org/core/Protein",
                label=["Protein", "Protein Entity"],
                comment=["A protein is a biological macromolecule"]
            ),
            "http://purl.uniprot.org/core/Taxon": OWLClass(
                uri="http://purl.uniprot.org/core/Taxon",
                label=["Taxonomic node", "Taxon"],
                comment=["A node in the taxonomic tree"]
            )
        },
        properties={
            "http://purl.uniprot.org/core/organism": OWLProperty(
                uri="http://purl.uniprot.org/core/organism",
                label=["organism"],
                comment=["The organism that the protein comes from"],
                domain=["http://purl.uniprot.org/core/Protein"],
                range=["http://purl.uniprot.org/core/Taxon"]
            )
        },
        namespaces={
            "up": "http://purl.uniprot.org/core/"
        }
    )

    # Create generator with validation
    generator = SPARQLGenerator(enable_validation=True, enable_optimization=True)

    # Biomedical queries
    queries = [
        "find all human proteins",
        "count proteins by organism",
        "show proteins classified with biological processes"
    ]

    for nl_query in queries:
        print(f"\nQuery: '{nl_query}'")
        print("-" * 80)

        result = generator.generate(
            natural_language=nl_query,
            schema_info=schema,
            ontology_info=ontology,
            strategy=GenerationStrategy.TEMPLATE,
            constraints={"limit": 100}
        )

        print("Generated SPARQL:")
        print(result.query)

        if 'validation' in result.metadata:
            validation = result.metadata['validation']
            print(f"\nValidation:")
            print(f"  Valid: {validation['is_valid']}")
            print(f"  Complexity Score: {validation['complexity_score']:.2f}")
            if validation.get('suggestions'):
                print(f"  Suggestions:")
                for suggestion in validation['suggestions'][:3]:
                    print(f"    - {suggestion}")


def example_3_custom_templates():
    """
    Example 3: Using custom query templates.

    This shows how to define and use custom templates for
    domain-specific query patterns.
    """
    print("\n" + "=" * 80)
    print("Example 3: Custom Query Templates")
    print("=" * 80)

    # Create generator
    generator = create_generator()

    # Define custom templates for a research database
    publication_template = QueryTemplate(
        name="find_publications_by_author",
        pattern=r"(find|get|show)\s+publications?\s+(by|from|authored by)\s+(\w+)",
        sparql_template="""PREFIX bibo: <http://purl.org/ontology/bibo/>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>

SELECT ?publication ?title ?date
WHERE {{
  ?publication a bibo:AcademicArticle .
  ?publication dcterms:creator ?author .
  ?author foaf:name ?authorName .
  ?publication dcterms:title ?title .
  OPTIONAL {{ ?publication dcterms:date ?date }}
  FILTER(CONTAINS(LCASE(?authorName), "{author_name}"))
}}
ORDER BY DESC(?date)
LIMIT {limit}""",
        required_context=["author_name"],
        confidence=0.85
    )

    citation_template = QueryTemplate(
        name="find_citing_papers",
        pattern=r"(papers?|articles?)\s+(citing|that cite)\s+(.+)",
        sparql_template="""PREFIX bibo: <http://purl.org/ontology/bibo/>
PREFIX dcterms: <http://purl.org/dc/terms/>

SELECT ?citing ?citingTitle
WHERE {{
  ?citing bibo:cites <{cited_paper_uri}> .
  ?citing dcterms:title ?citingTitle .
}}
LIMIT {limit}""",
        required_context=["cited_paper_uri"],
        confidence=0.8
    )

    # Add custom templates
    generator.add_template(publication_template)
    generator.add_template(citation_template)

    print("\nAdded 2 custom templates:")
    print(f"  1. {publication_template.name}")
    print(f"  2. {citation_template.name}")

    # Note: Full demonstration would require matching the pattern
    # and filling in the template parameters
    print("\nThese templates can now be used for publication queries.")


def example_4_federated_queries():
    """
    Example 4: Multi-dataset federated queries.

    This demonstrates generating queries that span multiple
    SPARQL endpoints using SERVICE federation.
    """
    print("\n" + "=" * 80)
    print("Example 4: Federated Query Generation")
    print("=" * 80)

    # Schema spanning multiple endpoints
    schema = SchemaInfo(
        classes={
            "http://purl.uniprot.org/core/Protein",  # UniProt
            "http://purl.obolibrary.org/obo/MONDO_0000001"  # Disease (Mondo)
        },
        properties={
            "http://purl.uniprot.org/core/organism",
            "http://example.org/associatedWith"
        },
        namespaces={
            "up": "http://purl.uniprot.org/core/",
            "mondo": "http://purl.obolibrary.org/obo/MONDO_",
            "sio": "http://semanticscience.org/resource/"
        }
    )

    # Define cross-reference information
    cross_refs = {
        "uniprot_endpoint": "https://sparql.uniprot.org/sparql",
        "disease_endpoint": "https://disease-ontology.org/sparql"
    }

    print("\nFederated query scenario:")
    print("  - Query proteins from UniProt endpoint")
    print("  - Join with disease data from Disease Ontology endpoint")
    print("\nNote: Federated query generation requires LLM or specialized templates")


def example_5_validation_and_optimization():
    """
    Example 5: Query validation and optimization.

    This shows the validation and optimization features that
    check query syntax and provide improvement suggestions.
    """
    print("\n" + "=" * 80)
    print("Example 5: Query Validation and Optimization")
    print("=" * 80)

    # Create generator with validation enabled
    generator = SPARQLGenerator(
        enable_validation=True,
        enable_optimization=True
    )

    schema = SchemaInfo(
        classes={"http://example.org/Dataset", "http://example.org/Distribution"},
        properties={"http://example.org/title", "http://example.org/description"},
        namespaces={
            "ex": "http://example.org/",
            "dcat": "http://www.w3.org/ns/dcat#"
        }
    )

    # Generate query
    result = generator.generate(
        natural_language="find all datasets with their distributions",
        schema_info=schema,
        strategy=GenerationStrategy.TEMPLATE
    )

    print("\nGenerated Query:")
    print(result.query)

    # Show validation results
    if 'validation' in result.metadata:
        validation = result.metadata['validation']

        print("\n" + "=" * 40)
        print("Validation Report")
        print("=" * 40)
        print(f"Valid: {validation['is_valid']}")
        print(f"Complexity Score: {validation['complexity_score']:.2f}/10")

        if validation.get('warnings'):
            print("\nWarnings:")
            for warning in validation['warnings']:
                print(f"  - {warning}")

        if validation.get('suggestions'):
            print("\nOptimization Suggestions:")
            for suggestion in validation['suggestions']:
                print(f"  - {suggestion}")


def example_6_statistics_monitoring():
    """
    Example 6: Monitoring generation statistics.

    This demonstrates how to track and monitor query generation
    performance and usage patterns.
    """
    print("\n" + "=" * 80)
    print("Example 6: Generation Statistics and Monitoring")
    print("=" * 80)

    generator = create_generator()

    schema = SchemaInfo(
        classes={"http://example.org/Book", "http://example.org/Author"},
        namespaces={"ex": "http://example.org/"}
    )

    # Generate multiple queries
    queries = [
        "list all books",
        "count authors",
        "show books with authors",
        "how many books per author"
    ]

    print("\nGenerating multiple queries...")
    for query in queries:
        result = generator.generate(
            natural_language=query,
            schema_info=schema,
            strategy=GenerationStrategy.TEMPLATE
        )
        print(f"  ✓ Generated: '{query}'")

    # Get statistics
    stats = generator.get_statistics()

    print("\n" + "=" * 40)
    print("Generation Statistics")
    print("=" * 40)
    print(f"Total Queries Generated: {stats['total_generated']}")
    print(f"Template-Based: {stats['template_used']}")
    print(f"LLM-Based: {stats['llm_used']}")
    print(f"Hybrid: {stats['hybrid_used']}")
    print(f"Validation Failures: {stats['validation_failures']}")
    print(f"Average Confidence: {stats['average_confidence']:.2f}")


def example_7_quick_generation():
    """
    Example 7: Quick generation utility.

    This demonstrates the simplified quick_generate function
    for rapid prototyping and simple use cases.
    """
    print("\n" + "=" * 80)
    print("Example 7: Quick Generation Utility")
    print("=" * 80)

    schema = SchemaInfo(
        classes={"http://schema.org/Person"},
        namespaces={"schema": "http://schema.org/"}
    )

    print("\nUsing quick_generate() for rapid query generation:")
    print("-" * 80)

    query = quick_generate(
        natural_language="list all people",
        schema_info=schema
    )

    print("Natural Language: 'list all people'")
    print("\nGenerated Query:")
    print(query)

    print("\nNote: quick_generate() returns just the query string,")
    print("      ideal for simple use cases and scripting.")


def example_8_error_handling():
    """
    Example 8: Error handling and fallback strategies.

    This demonstrates how the generator handles errors and
    provides fallback options.
    """
    print("\n" + "=" * 80)
    print("Example 8: Error Handling and Fallback")
    print("=" * 80)

    generator = create_generator()

    # Case 1: Insufficient context
    print("\nCase 1: Insufficient Context")
    print("-" * 80)
    try:
        # Try to generate without schema
        result = generator.generate(
            natural_language="list all items",
            strategy=GenerationStrategy.TEMPLATE
        )
        print("Query generated (may be generic):")
        print(result.query)
        print(f"Confidence: {result.confidence:.2f}")
    except Exception as e:
        print(f"Error: {e}")

    # Case 2: Ambiguous query
    print("\n\nCase 2: Ambiguous Natural Language")
    print("-" * 80)
    schema = SchemaInfo(
        classes={"http://example.org/Thing"},
        namespaces={"ex": "http://example.org/"}
    )

    result = generator.generate(
        natural_language="show me things",
        schema_info=schema,
        strategy=GenerationStrategy.TEMPLATE
    )
    print("Query generated:")
    print(result.query)
    print(f"Confidence: {result.confidence:.2f}")

    if result.confidence < 0.7:
        print("\n⚠️  Low confidence - consider:")
        print("   - Providing more specific natural language")
        print("   - Adding ontology information")
        print("   - Using LLM-based generation for better understanding")


def main():
    """Run all examples."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "     SPARQL GENERATOR - PRACTICAL EXAMPLES".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "=" * 78 + "╝")

    examples = [
        example_1_basic_template_generation,
        example_2_biomedical_ontology,
        example_3_custom_templates,
        example_4_federated_queries,
        example_5_validation_and_optimization,
        example_6_statistics_monitoring,
        example_7_quick_generation,
        example_8_error_handling
    ]

    for example_func in examples:
        try:
            example_func()
        except Exception as e:
            print(f"\n❌ Error in {example_func.__name__}: {e}")

    print("\n" + "=" * 80)
    print("Examples completed!")
    print("=" * 80)
    print("\nFor more information, see:")
    print("  - generator.py: Full implementation")
    print("  - test_generator.py: Comprehensive test suite")
    print("  - Documentation: [link to docs]")


if __name__ == "__main__":
    main()
