"""
Integrated Example: Ontology-Guided Query Generation with Full System.

This example demonstrates how to integrate the ontology-guided generator
with other components of the SPARQL-Agent system:

1. Schema discovery
2. Ontology mapping
3. Prompt engineering
4. Query generation
5. Validation and execution
"""

import logging
from typing import Optional

from ..core.types import (
    OntologyInfo,
    SchemaInfo,
    EndpointInfo,
    GeneratedQuery,
)
from .ontology_generator import (
    OntologyGuidedGenerator,
    OntologyQueryContext,
    ExpansionStrategy,
    create_ontology_generator,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IntegratedQuerySystem:
    """
    Integrated query system combining ontology guidance with schema discovery.

    This class demonstrates how to:
    - Load ontologies and schemas
    - Map between different vocabularies
    - Generate queries with ontology guidance
    - Validate and optimize generated queries
    """

    def __init__(
        self,
        endpoint_url: str,
        ontology_id: Optional[str] = None,
        ontology_file: Optional[str] = None,
    ):
        """
        Initialize the integrated query system.

        Args:
            endpoint_url: SPARQL endpoint URL
            ontology_id: OLS ontology ID (e.g., "go", "efo")
            ontology_file: Path to local ontology file
        """
        self.endpoint_url = endpoint_url
        self.endpoint_info = EndpointInfo(url=endpoint_url)

        # Initialize ontology generator
        if ontology_id:
            logger.info(f"Loading ontology from OLS: {ontology_id}")
            self.generator = create_ontology_generator(
                ontology_id=ontology_id,
                enable_ols=True,
            )
        elif ontology_file:
            logger.info(f"Loading ontology from file: {ontology_file}")
            self.generator = create_ontology_generator(
                ontology_source=ontology_file,
                enable_ols=False,
            )
        else:
            logger.info("Creating generator without ontology")
            self.generator = create_ontology_generator(enable_ols=True)

        # Schema discovery (would be implemented separately)
        self.schema_info: Optional[SchemaInfo] = None

    def discover_schema(self) -> SchemaInfo:
        """
        Discover schema from SPARQL endpoint.

        In a real implementation, this would query the endpoint to discover:
        - Available classes
        - Available properties
        - Namespaces
        - Class/property usage statistics
        """
        logger.info(f"Discovering schema from {self.endpoint_url}")

        # Placeholder - would use discovery module
        schema_info = SchemaInfo()

        self.schema_info = schema_info
        return schema_info

    def generate_query(
        self,
        natural_language: str,
        expansion_strategy: ExpansionStrategy = ExpansionStrategy.CHILDREN,
        max_hops: int = 3,
        use_schema: bool = True,
    ) -> GeneratedQuery:
        """
        Generate SPARQL query from natural language.

        Args:
            natural_language: Natural language query
            expansion_strategy: Class expansion strategy
            max_hops: Maximum property path hops
            use_schema: Whether to use discovered schema

        Returns:
            Generated SPARQL query with metadata
        """
        logger.info(f"Generating query for: '{natural_language}'")

        # Create context
        context = OntologyQueryContext(
            ontology_info=self.generator.ontology_info,
            expansion_strategy=expansion_strategy,
            max_hops=max_hops,
        )

        # Add schema information if available
        if use_schema and self.schema_info:
            context.metadata["schema_info"] = self.schema_info

        # Generate query
        result = self.generator.generate_query(
            natural_language,
            context,
            include_explanation=True,
        )

        logger.info(f"Generated query with confidence: {result.confidence:.2f}")
        return result

    def validate_and_optimize(self, query: str) -> dict:
        """
        Validate and optimize generated query.

        Args:
            query: SPARQL query string

        Returns:
            Validation results and optimization suggestions
        """
        logger.info("Validating query against ontology...")

        if not self.generator.ontology_info:
            logger.warning("No ontology loaded, skipping validation")
            return {"valid": True, "warnings": [], "suggestions": []}

        validation = self.generator.validate_query_against_ontology(
            query,
            self.generator.ontology_info,
        )

        if not validation["is_valid"]:
            logger.warning(f"Query validation failed: {validation['errors']}")
        else:
            logger.info("Query validation passed")

        return validation

    def execute_query(self, query: str) -> dict:
        """
        Execute SPARQL query on endpoint.

        Args:
            query: SPARQL query string

        Returns:
            Query results
        """
        logger.info("Executing query...")

        # This would use the execution module
        # For now, just return placeholder
        return {
            "status": "success",
            "message": "Query execution would happen here",
        }

    def full_pipeline(
        self,
        natural_language: str,
        expansion: str = "children",
        execute: bool = False,
    ) -> dict:
        """
        Run full pipeline from natural language to results.

        Args:
            natural_language: Natural language query
            expansion: Expansion strategy name
            execute: Whether to execute the query

        Returns:
            Complete pipeline results
        """
        logger.info("=" * 80)
        logger.info(f"Starting full pipeline for: '{natural_language}'")
        logger.info("=" * 80)

        # Map expansion string to enum
        strategy_map = {
            "exact": ExpansionStrategy.EXACT,
            "children": ExpansionStrategy.CHILDREN,
            "descendants": ExpansionStrategy.DESCENDANTS,
            "ancestors": ExpansionStrategy.ANCESTORS,
            "siblings": ExpansionStrategy.SIBLINGS,
            "related": ExpansionStrategy.RELATED,
        }
        strategy = strategy_map.get(expansion.lower(), ExpansionStrategy.CHILDREN)

        # Step 1: Generate query
        logger.info("Step 1: Generating query...")
        result = self.generate_query(
            natural_language,
            expansion_strategy=strategy,
            max_hops=3,
        )

        # Step 2: Validate
        logger.info("Step 2: Validating query...")
        validation = self.validate_and_optimize(result.query)

        # Step 3: Execute (if requested)
        execution_result = None
        if execute and validation["is_valid"]:
            logger.info("Step 3: Executing query...")
            execution_result = self.execute_query(result.query)

        # Compile results
        pipeline_result = {
            "natural_language": natural_language,
            "generated_query": result.query,
            "confidence": result.confidence,
            "explanation": result.explanation,
            "ontology_classes": result.ontology_classes,
            "ontology_properties": result.ontology_properties,
            "validation": validation,
            "execution": execution_result,
        }

        logger.info("Pipeline complete!")
        return pipeline_result


# ============================================================================
# Example Usage Scenarios
# ============================================================================


def example_basic_integration():
    """Example: Basic integration with ontology guidance."""
    print("\n" + "=" * 80)
    print("Example: Basic Integration")
    print("=" * 80)

    # Create system with Gene Ontology
    system = IntegratedQuerySystem(
        endpoint_url="http://sparql.hegroup.org/sparql",
        ontology_id="go",
    )

    # Generate query
    result = system.full_pipeline(
        "Find all genes involved in DNA repair",
        expansion="children",
        execute=False,
    )

    print("\nNatural Language:", result["natural_language"])
    print("\nGenerated Query:")
    print(result["generated_query"])
    print(f"\nConfidence: {result['confidence']:.2f}")
    print(f"\nClasses used: {len(result['ontology_classes'])}")
    print(f"\nProperties used: {len(result['ontology_properties'])}")


def example_multi_step_query():
    """Example: Multi-step query with property paths."""
    print("\n" + "=" * 80)
    print("Example: Multi-Step Query")
    print("=" * 80)

    system = IntegratedQuerySystem(
        endpoint_url="http://example.org/sparql",
        ontology_id="go",
    )

    # Complex query requiring multiple hops
    result = system.full_pipeline(
        "Which genes encode proteins that participate in immune response?",
        expansion="descendants",
        execute=False,
    )

    print("\nNatural Language:", result["natural_language"])
    print("\nGenerated Query:")
    print(result["generated_query"])
    print("\nExplanation:")
    print(result["explanation"])


def example_validation_pipeline():
    """Example: Query generation with validation."""
    print("\n" + "=" * 80)
    print("Example: Validation Pipeline")
    print("=" * 80)

    system = IntegratedQuerySystem(
        endpoint_url="http://example.org/sparql",
        ontology_id="so",  # Sequence Ontology
    )

    # Generate and validate
    result = system.full_pipeline(
        "Find all protein coding genes",
        expansion="exact",
        execute=False,
    )

    print("\nValidation Results:")
    print(f"  Valid: {result['validation']['is_valid']}")
    print(f"  Errors: {len(result['validation']['errors'])}")
    print(f"  Warnings: {len(result['validation']['warnings'])}")

    if result['validation']['errors']:
        print("\nErrors:")
        for error in result['validation']['errors']:
            print(f"  - {error}")

    if result['validation']['warnings']:
        print("\nWarnings:")
        for warning in result['validation']['warnings']:
            print(f"  - {warning}")


def example_property_discovery():
    """Example: Discovering property paths between concepts."""
    print("\n" + "=" * 80)
    print("Example: Property Path Discovery")
    print("=" * 80)

    system = IntegratedQuerySystem(
        endpoint_url="http://example.org/sparql",
        ontology_id="go",
    )

    # Query that requires finding property paths
    result = system.generate_query(
        "What are the molecular functions of proteins in mitochondria?",
        expansion_strategy=ExpansionStrategy.RELATED,
        max_hops=4,
    )

    print("\nNatural Language: What are the molecular functions of proteins in mitochondria?")
    print("\nProperty paths discovered:")
    for prop in result.ontology_properties[:5]:
        print(f"  - {prop}")

    print("\nGenerated Query:")
    print(result.query)


def example_with_local_ontology():
    """Example: Using local ontology file instead of OLS."""
    print("\n" + "=" * 80)
    print("Example: Local Ontology File")
    print("=" * 80)

    # This would use a local OWL file
    # system = IntegratedQuerySystem(
    #     endpoint_url="http://example.org/sparql",
    #     ontology_file="/path/to/ontology.owl",
    # )

    print("In production, you would load from a local file:")
    print("  system = IntegratedQuerySystem(")
    print("      endpoint_url='http://example.org/sparql',")
    print("      ontology_file='/path/to/ontology.owl',")
    print("  )")


def example_comparison_strategies():
    """Example: Compare different expansion strategies."""
    print("\n" + "=" * 80)
    print("Example: Comparing Expansion Strategies")
    print("=" * 80)

    system = IntegratedQuerySystem(
        endpoint_url="http://example.org/sparql",
        ontology_id="go",
    )

    query = "Find biological processes"

    strategies = ["exact", "children", "descendants"]

    for strategy in strategies:
        result = system.full_pipeline(
            query,
            expansion=strategy,
            execute=False,
        )

        print(f"\n--- Strategy: {strategy} ---")
        print(f"Classes included: {len(result['ontology_classes'])}")
        print(f"Confidence: {result['confidence']:.2f}")


# ============================================================================
# Main
# ============================================================================


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("INTEGRATED ONTOLOGY-GUIDED QUERY GENERATION EXAMPLES")
    print("=" * 80)

    examples = [
        example_basic_integration,
        example_multi_step_query,
        example_validation_pipeline,
        example_property_discovery,
        example_with_local_ontology,
        example_comparison_strategies,
    ]

    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"\nError in example: {e}")
            logger.exception("Example failed")

    print("\n" + "=" * 80)
    print("All examples completed!")
    print("=" * 80)


if __name__ == "__main__":
    # Run specific example
    example_basic_integration()

    # Or run all examples
    # main()
