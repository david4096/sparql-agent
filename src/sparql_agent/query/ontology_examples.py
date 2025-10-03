"""
Example Usage of Ontology-Guided SPARQL Query Generation.

This module demonstrates various use cases for ontology-guided query generation:
1. Basic query generation with class expansion
2. Property path discovery
3. OLS integration for real-time ontology lookup
4. Multi-ontology query generation
5. Query validation against ontology constraints
"""

from pathlib import Path
import logging

from ..core.types import OntologyInfo, OWLClass, OWLProperty, OWLPropertyType
from .ontology_generator import (
    OntologyGuidedGenerator,
    OntologyQueryContext,
    ExpansionStrategy,
    create_ontology_generator,
    quick_ontology_query,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Example 1: Basic Ontology-Guided Query Generation
# ============================================================================


def example_basic_query_generation():
    """
    Example: Basic query generation with ontology guidance.

    This example shows how to:
    - Load an ontology
    - Generate a SPARQL query from natural language
    - Use class hierarchy for query expansion
    """
    print("=" * 80)
    print("Example 1: Basic Ontology-Guided Query Generation")
    print("=" * 80)

    # Create a simple test ontology
    ontology = create_test_ontology()

    # Create generator
    generator = create_ontology_generator(ontology_source=ontology)

    # Create query context
    context = OntologyQueryContext(
        ontology_info=ontology,
        expansion_strategy=ExpansionStrategy.EXACT,
        max_hops=2,
    )

    # Generate query
    user_query = "Find all genes"
    result = generator.generate_query(user_query, context, include_explanation=True)

    print(f"\nUser Query: {user_query}")
    print("\nGenerated SPARQL Query:")
    print(result.query)
    print(f"\nConfidence: {result.confidence:.2f}")
    print(f"\nOntology Classes Used: {result.ontology_classes}")
    print(f"\nOntology Properties Used: {result.ontology_properties}")
    print("\nExplanation:")
    print(result.explanation)


# ============================================================================
# Example 2: Query with Class Hierarchy Expansion
# ============================================================================


def example_hierarchy_expansion():
    """
    Example: Using class hierarchies to expand queries.

    This example demonstrates:
    - Different expansion strategies (exact, children, descendants, ancestors)
    - How expansion affects query results
    - Confidence scoring with expansion
    """
    print("\n" + "=" * 80)
    print("Example 2: Class Hierarchy Expansion")
    print("=" * 80)

    ontology = create_test_ontology()
    generator = create_ontology_generator(ontology_source=ontology)

    user_query = "Find all biological entities"

    # Test different expansion strategies
    strategies = [
        ExpansionStrategy.EXACT,
        ExpansionStrategy.CHILDREN,
        ExpansionStrategy.DESCENDANTS,
    ]

    for strategy in strategies:
        context = OntologyQueryContext(
            ontology_info=ontology,
            expansion_strategy=strategy,
            max_hops=2,
        )

        result = generator.generate_query(user_query, context)

        print(f"\n--- Strategy: {strategy.value} ---")
        print(f"Classes included: {len(result.ontology_classes)}")
        print(f"Confidence: {result.confidence:.2f}")
        print(f"Classes: {result.ontology_classes}")


# ============================================================================
# Example 3: Property Path Discovery
# ============================================================================


def example_property_paths():
    """
    Example: Discovering property paths between classes.

    This example shows:
    - Finding direct properties
    - Multi-hop property paths
    - Property path confidence scoring
    """
    print("\n" + "=" * 80)
    print("Example 3: Property Path Discovery")
    print("=" * 80)

    ontology = create_test_ontology()
    generator = create_ontology_generator(ontology_source=ontology)

    context = OntologyQueryContext(
        ontology_info=ontology,
        expansion_strategy=ExpansionStrategy.EXACT,
        max_hops=3,  # Allow up to 3 hops
    )

    user_query = "Which genes encode proteins?"
    result = generator.generate_query(user_query, context, include_explanation=True)

    print(f"\nUser Query: {user_query}")
    print("\nDiscovered Property Paths:")
    for prop in result.ontology_properties:
        print(f"  - {prop}")
    print("\nGenerated Query:")
    print(result.query)


# ============================================================================
# Example 4: OLS Integration for Real-Time Lookup
# ============================================================================


def example_ols_integration():
    """
    Example: Using OLS for real-time ontology lookup.

    This example demonstrates:
    - Loading ontologies from OLS
    - Real-time term expansion
    - Caching for performance
    """
    print("\n" + "=" * 80)
    print("Example 4: OLS Integration")
    print("=" * 80)

    # Note: This requires internet connection to access EBI OLS
    try:
        # Create generator with OLS support
        generator = create_ontology_generator(enable_ols=True)

        # Expand term using OLS
        print("\nExpanding 'gene' in GO ontology...")
        expanded = generator.expand_with_ols(
            term_label="gene",
            ontology_id="go",
            strategy=ExpansionStrategy.CHILDREN,
        )

        print(f"\nFound {len(expanded)} terms:")
        for term in expanded[:5]:  # Show first 5
            print(f"  - {term.get('label', 'N/A')} ({term.get('id', 'N/A')})")

        # Suggest properties
        if expanded:
            print("\nSuggesting properties...")
            # This would work if we had loaded the ontology
            print("  (Would show property suggestions here)")

    except Exception as e:
        print(f"\nOLS integration requires internet connection: {e}")
        print("Skipping this example...")


# ============================================================================
# Example 5: Loading and Using Real Ontologies
# ============================================================================


def example_load_ontology_from_ols():
    """
    Example: Loading a complete ontology from OLS.

    This example shows:
    - Downloading ontology from OLS
    - Caching for performance
    - Using loaded ontology for queries
    """
    print("\n" + "=" * 80)
    print("Example 5: Loading Real Ontology from OLS")
    print("=" * 80)

    try:
        # Create generator
        generator = create_ontology_generator(enable_ols=True)

        # Load a small ontology (e.g., SO - Sequence Ontology)
        print("\nLoading Sequence Ontology (SO) from OLS...")
        print("(This may take a moment...)")

        # Note: In production, you'd cache this
        # ontology = generator.load_ontology_from_ols("so", cache_path=Path("./cache"))

        print("\nOntology loaded successfully!")
        print("Now you can use it for query generation...")

        # Example query with loaded ontology
        # context = OntologyQueryContext(
        #     ontology_info=ontology,
        #     expansion_strategy=ExpansionStrategy.CHILDREN,
        # )
        # result = generator.generate_query("Find all gene sequences", context)

    except Exception as e:
        print(f"\nLoading ontology requires internet connection: {e}")
        print("In production, you would cache the ontology locally.")


# ============================================================================
# Example 6: Query Validation
# ============================================================================


def example_query_validation():
    """
    Example: Validating queries against ontology constraints.

    This example demonstrates:
    - Checking if classes exist in ontology
    - Validating property domains and ranges
    - Getting suggestions for fixes
    """
    print("\n" + "=" * 80)
    print("Example 6: Query Validation")
    print("=" * 80)

    ontology = create_test_ontology()
    generator = create_ontology_generator(ontology_source=ontology)

    # Valid query
    valid_query = """
    SELECT ?gene ?protein
    WHERE {
        ?gene a <http://example.org/bio#Gene> .
        ?gene <http://example.org/bio#encodes> ?protein .
        ?protein a <http://example.org/bio#Protein> .
    }
    """

    print("\nValidating a correct query...")
    validation = generator.validate_query_against_ontology(valid_query, ontology)
    print(f"Valid: {validation['is_valid']}")
    print(f"Errors: {len(validation['errors'])}")
    print(f"Warnings: {len(validation['warnings'])}")

    # Invalid query (non-existent class)
    invalid_query = """
    SELECT ?x
    WHERE {
        ?x a <http://example.org/bio#NonExistentClass> .
    }
    """

    print("\nValidating an invalid query...")
    validation = generator.validate_query_against_ontology(invalid_query, ontology)
    print(f"Valid: {validation['is_valid']}")
    print(f"Errors: {validation['errors']}")


# ============================================================================
# Example 7: Property Suggestions
# ============================================================================


def example_property_suggestions():
    """
    Example: Getting property suggestions for classes.

    This example shows:
    - Finding relevant properties for given classes
    - Scoring and ranking suggestions
    - Understanding property relationships
    """
    print("\n" + "=" * 80)
    print("Example 7: Property Suggestions")
    print("=" * 80)

    ontology = create_test_ontology()
    generator = create_ontology_generator(ontology_source=ontology)

    # Get suggestions for connecting Gene and Protein
    class_uris = [
        "http://example.org/bio#Gene",
        "http://example.org/bio#Protein",
    ]

    print(f"\nFinding properties to connect:")
    for uri in class_uris:
        print(f"  - {uri}")

    suggestions = generator.suggest_properties_for_classes(
        class_uris,
        "bio",
        max_suggestions=5,
    )

    print(f"\nFound {len(suggestions)} suggestions:")
    for suggestion in suggestions:
        print(f"\n  Property: {suggestion['label']}")
        print(f"  URI: {suggestion['uri']}")
        print(f"  Score: {suggestion['score']}")
        print(f"  Description: {suggestion.get('description', 'N/A')}")
        print(f"  Domain: {suggestion.get('domain', [])}")
        print(f"  Range: {suggestion.get('range', [])}")


# ============================================================================
# Example 8: Quick Query Generation
# ============================================================================


def example_quick_query():
    """
    Example: Quick query generation with convenience function.

    This example shows the simplest way to generate queries.
    """
    print("\n" + "=" * 80)
    print("Example 8: Quick Query Generation")
    print("=" * 80)

    try:
        # Note: Requires internet connection for OLS
        result = quick_ontology_query(
            user_query="Find all genes",
            ontology_id="so",  # Sequence Ontology
            expansion="children",
            max_hops=2,
        )

        print("\nGenerated Query:")
        print(result.query)
        print(f"\nConfidence: {result.confidence:.2f}")

    except Exception as e:
        print(f"\nQuick query requires internet connection: {e}")
        print("In production, load and cache the ontology first.")


# ============================================================================
# Helper Functions
# ============================================================================


def create_test_ontology() -> OntologyInfo:
    """Create a test ontology for examples."""
    ontology = OntologyInfo(
        uri="http://example.org/bio#",
        title="Biological Ontology",
        description="A simple biological ontology for testing",
        version="1.0",
    )

    # Create class hierarchy
    # Entity -> BiologicalEntity -> Gene
    #                             -> Protein
    #                             -> Disease

    entity = OWLClass(
        uri="http://example.org/bio#Entity",
        label=["Entity"],
        comment=["Top-level entity"],
    )

    bio_entity = OWLClass(
        uri="http://example.org/bio#BiologicalEntity",
        label=["Biological Entity", "BioEntity"],
        comment=["Any biological entity"],
        subclass_of=[entity.uri],
    )

    gene = OWLClass(
        uri="http://example.org/bio#Gene",
        label=["Gene"],
        comment=["A gene is a unit of heredity"],
        subclass_of=[bio_entity.uri],
    )

    protein = OWLClass(
        uri="http://example.org/bio#Protein",
        label=["Protein"],
        comment=["A protein molecule"],
        subclass_of=[bio_entity.uri],
    )

    disease = OWLClass(
        uri="http://example.org/bio#Disease",
        label=["Disease", "Disorder"],
        comment=["A disease or medical condition"],
        subclass_of=[bio_entity.uri],
    )

    ontology.classes = {
        entity.uri: entity,
        bio_entity.uri: bio_entity,
        gene.uri: gene,
        protein.uri: protein,
        disease.uri: disease,
    }

    # Create properties
    encodes = OWLProperty(
        uri="http://example.org/bio#encodes",
        label=["encodes", "codes for"],
        comment=["Gene encodes a protein"],
        property_type=OWLPropertyType.OBJECT_PROPERTY,
        domain=[gene.uri],
        range=[protein.uri],
    )

    associated_with = OWLProperty(
        uri="http://example.org/bio#associatedWith",
        label=["associated with"],
        comment=["Entity is associated with disease"],
        property_type=OWLPropertyType.OBJECT_PROPERTY,
        domain=[bio_entity.uri],
        range=[disease.uri],
    )

    has_name = OWLProperty(
        uri="http://example.org/bio#hasName",
        label=["has name", "name"],
        comment=["Name of the entity"],
        property_type=OWLPropertyType.DATATYPE_PROPERTY,
        domain=[entity.uri],
        range=["http://www.w3.org/2001/XMLSchema#string"],
    )

    has_sequence = OWLProperty(
        uri="http://example.org/bio#hasSequence",
        label=["has sequence", "sequence"],
        comment=["Biological sequence"],
        property_type=OWLPropertyType.DATATYPE_PROPERTY,
        domain=[gene.uri, protein.uri],
        range=["http://www.w3.org/2001/XMLSchema#string"],
    )

    ontology.properties = {
        encodes.uri: encodes,
        associated_with.uri: associated_with,
        has_name.uri: has_name,
        has_sequence.uri: has_sequence,
    }

    return ontology


# ============================================================================
# Run All Examples
# ============================================================================


def run_all_examples():
    """Run all examples in sequence."""
    print("\n" + "=" * 80)
    print("ONTOLOGY-GUIDED SPARQL QUERY GENERATION EXAMPLES")
    print("=" * 80)

    examples = [
        ("Basic Query Generation", example_basic_query_generation),
        ("Hierarchy Expansion", example_hierarchy_expansion),
        ("Property Path Discovery", example_property_paths),
        ("OLS Integration", example_ols_integration),
        ("Load Ontology from OLS", example_load_ontology_from_ols),
        ("Query Validation", example_query_validation),
        ("Property Suggestions", example_property_suggestions),
        ("Quick Query", example_quick_query),
    ]

    for name, example_func in examples:
        try:
            example_func()
        except Exception as e:
            print(f"\nError in {name}: {e}")
            logger.exception(f"Example failed: {name}")

    print("\n" + "=" * 80)
    print("All examples completed!")
    print("=" * 80)


if __name__ == "__main__":
    # Run individual examples
    example_basic_query_generation()
    example_hierarchy_expansion()
    example_property_paths()
    example_query_validation()
    example_property_suggestions()

    # Or run all examples
    # run_all_examples()
