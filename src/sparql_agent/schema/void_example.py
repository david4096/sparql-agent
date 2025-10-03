"""
Example usage of VoID Parser and Extractor

This script demonstrates how to use the VoIDParser and VoIDExtractor classes
to work with VoID descriptions from SPARQL endpoints.
"""

import logging
from void_parser import VoIDParser, VoIDExtractor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def example_parse_void_file():
    """Example: Parse VoID description from a file."""
    logger.info("=== Example 1: Parsing VoID from File ===")

    # Sample VoID description
    void_turtle = """
    @prefix void: <http://rdfs.org/ns/void#> .
    @prefix dcterms: <http://purl.org/dc/terms/> .
    @prefix foaf: <http://xmlns.com/foaf/0.1/> .

    <http://example.org/dataset> a void:Dataset ;
        dcterms:title "Example Dataset" ;
        dcterms:description "A sample RDF dataset" ;
        void:sparqlEndpoint <http://example.org/sparql> ;
        void:triples 1000000 ;
        void:entities 50000 ;
        void:distinctSubjects 50000 ;
        void:distinctObjects 75000 ;
        void:properties 100 ;
        void:classes 50 ;
        void:vocabulary <http://xmlns.com/foaf/0.1/> ;
        void:vocabulary <http://purl.org/dc/terms/> ;
        void:uriSpace "http://example.org/resource/" ;
        dcterms:created "2025-01-01"^^<http://www.w3.org/2001/XMLSchema#date> ;
        dcterms:license <http://creativecommons.org/licenses/by/4.0/> .
    """

    parser = VoIDParser()
    datasets = parser.parse(void_turtle, format='turtle')

    for dataset in datasets:
        logger.info(f"Dataset URI: {dataset.uri}")
        logger.info(f"Title: {dataset.title}")
        logger.info(f"Description: {dataset.description}")
        logger.info(f"SPARQL Endpoint: {dataset.sparql_endpoint}")
        logger.info(f"Triples: {dataset.triples:,}")
        logger.info(f"Entities: {dataset.entities:,}")
        logger.info(f"Properties: {dataset.properties}")
        logger.info(f"Classes: {dataset.classes}")
        logger.info(f"Vocabularies: {', '.join(dataset.vocabularies)}")
        logger.info(f"License: {dataset.license}")

        # Export to dict
        dataset_dict = dataset.to_dict()
        logger.info(f"Dataset as dict: {dataset_dict}")


def example_extract_from_endpoint():
    """Example: Extract VoID from a SPARQL endpoint."""
    logger.info("=== Example 2: Extracting VoID from Endpoint ===")

    # Using DBpedia as an example (public endpoint)
    endpoint_url = "https://dbpedia.org/sparql"

    try:
        extractor = VoIDExtractor(endpoint_url, timeout=30)

        # Try to extract existing VoID descriptions
        logger.info(f"Querying endpoint: {endpoint_url}")
        datasets = extractor.extract(generate_if_missing=False)

        if datasets:
            logger.info(f"Found {len(datasets)} VoID dataset(s)")
            for dataset in datasets:
                logger.info(f"Dataset: {dataset.uri}")
                logger.info(f"  Triples: {dataset.triples:,}" if dataset.triples else "  Triples: N/A")
                logger.info(f"  SPARQL Endpoint: {dataset.sparql_endpoint}")
        else:
            logger.info("No VoID descriptions found at endpoint")

    except Exception as e:
        logger.error(f"Error extracting from endpoint: {e}")


def example_generate_void():
    """Example: Generate VoID description from statistics."""
    logger.info("=== Example 3: Generating VoID from Statistics ===")

    # Using a smaller endpoint for generation example
    endpoint_url = "https://query.wikidata.org/sparql"

    try:
        extractor = VoIDExtractor(endpoint_url, timeout=60)

        # Generate VoID from statistics (this may take a while)
        logger.info(f"Generating VoID for endpoint: {endpoint_url}")
        logger.info("This may take some time...")

        # Note: For large endpoints like Wikidata, this will timeout
        # It's better suited for smaller endpoints
        datasets = extractor.extract(generate_if_missing=True)

        if datasets:
            dataset = datasets[0]
            logger.info(f"Generated VoID dataset:")
            logger.info(f"  URI: {dataset.uri}")
            logger.info(f"  Triples: {dataset.triples:,}" if dataset.triples else "  Triples: N/A")
            logger.info(f"  Distinct Subjects: {dataset.distinct_subjects:,}" if dataset.distinct_subjects else "  Subjects: N/A")
            logger.info(f"  Properties: {dataset.properties}" if dataset.properties else "  Properties: N/A")
            logger.info(f"  Classes: {dataset.classes}" if dataset.classes else "  Classes: N/A")
            logger.info(f"  Vocabularies: {len(dataset.vocabularies)}")

            # Show top vocabularies
            if dataset.vocabularies:
                logger.info("  Top vocabularies:")
                for vocab in list(dataset.vocabularies)[:5]:
                    logger.info(f"    - {vocab}")

            # Show class partitions
            if dataset.class_partitions:
                logger.info("  Top classes:")
                sorted_classes = sorted(
                    dataset.class_partitions.items(),
                    key=lambda x: x[1],
                    reverse=True
                )
                for class_uri, count in sorted_classes[:5]:
                    logger.info(f"    - {class_uri}: {count:,} instances")

            # Show property partitions
            if dataset.property_partitions:
                logger.info("  Top properties:")
                sorted_props = sorted(
                    dataset.property_partitions.items(),
                    key=lambda x: x[1],
                    reverse=True
                )
                for prop_uri, count in sorted_props[:5]:
                    logger.info(f"    - {prop_uri}: {count:,} triples")

    except Exception as e:
        logger.error(f"Error generating VoID: {e}")


def example_validate_void():
    """Example: Validate VoID consistency."""
    logger.info("=== Example 4: Validating VoID Consistency ===")

    # Create a sample dataset
    void_turtle = """
    @prefix void: <http://rdfs.org/ns/void#> .
    @prefix dcterms: <http://purl.org/dc/terms/> .

    <http://example.org/dataset> a void:Dataset ;
        dcterms:title "Test Dataset" ;
        void:sparqlEndpoint <https://dbpedia.org/sparql> ;
        void:triples 1000000 ;
        void:distinctSubjects 50000 .
    """

    parser = VoIDParser()
    datasets = parser.parse(void_turtle, format='turtle')

    if datasets:
        dataset = datasets[0]

        try:
            extractor = VoIDExtractor(dataset.sparql_endpoint, timeout=30)
            validation = extractor.validate_consistency(dataset)

            logger.info(f"Validation result: {'VALID' if validation['valid'] else 'INVALID'}")

            if validation['warnings']:
                logger.info("Warnings:")
                for warning in validation['warnings']:
                    logger.warning(f"  - {warning}")

            if validation['errors']:
                logger.info("Errors:")
                for error in validation['errors']:
                    logger.error(f"  - {error}")

        except Exception as e:
            logger.error(f"Error during validation: {e}")


def example_export_void():
    """Example: Export VoID to RDF."""
    logger.info("=== Example 5: Exporting VoID to RDF ===")

    # Create a sample dataset programmatically
    from void_parser import VoIDDataset
    from datetime import datetime

    dataset = VoIDDataset(
        uri="http://example.org/my-dataset",
        title="My Custom Dataset",
        description="A programmatically created dataset",
        sparql_endpoint="http://example.org/sparql",
        triples=500000,
        entities=25000,
        distinct_subjects=25000,
        distinct_objects=30000,
        properties=75,
        classes=25,
        created=datetime.now(),
        license="http://creativecommons.org/licenses/by/4.0/"
    )

    dataset.vocabularies.add("http://xmlns.com/foaf/0.1/")
    dataset.vocabularies.add("http://purl.org/dc/terms/")
    dataset.vocabularies.add("http://www.w3.org/2004/02/skos/core#")

    # Export to Turtle
    try:
        extractor = VoIDExtractor("http://example.org/sparql", timeout=30)
        turtle_output = extractor.export_to_rdf([dataset], format='turtle')

        logger.info("Exported VoID description (Turtle format):")
        logger.info(turtle_output)

        # Also export to RDF/XML
        xml_output = extractor.export_to_rdf([dataset], format='xml')
        logger.info("\nExported VoID description (RDF/XML format):")
        logger.info(xml_output[:500] + "...")  # Show first 500 chars

    except Exception as e:
        logger.error(f"Error exporting VoID: {e}")


def example_parse_linkset():
    """Example: Parse VoID Linkset."""
    logger.info("=== Example 6: Parsing VoID Linkset ===")

    void_turtle = """
    @prefix void: <http://rdfs.org/ns/void#> .
    @prefix dcterms: <http://purl.org/dc/terms/> .

    <http://example.org/dataset1> a void:Dataset ;
        dcterms:title "Dataset 1" ;
        void:subset <http://example.org/linkset1> .

    <http://example.org/linkset1> a void:Linkset ;
        dcterms:title "Link to Dataset 2" ;
        void:subjectsTarget <http://example.org/dataset1> ;
        void:objectsTarget <http://example.org/dataset2> ;
        void:linkPredicate <http://www.w3.org/2002/07/owl#sameAs> ;
        void:triples 10000 .
    """

    parser = VoIDParser()
    datasets = parser.parse(void_turtle, format='turtle')

    for dataset in datasets:
        logger.info(f"Dataset: {dataset.title}")
        logger.info(f"Linksets: {len(dataset.linksets)}")

        for linkset in dataset.linksets:
            logger.info(f"  Linkset URI: {linkset.uri}")
            logger.info(f"  Source: {linkset.source_dataset}")
            logger.info(f"  Target: {linkset.target_dataset}")
            logger.info(f"  Predicate: {linkset.link_predicate}")
            logger.info(f"  Triples: {linkset.triples:,}")


if __name__ == "__main__":
    logger.info("VoID Parser and Extractor Examples")
    logger.info("=" * 50)

    # Run examples
    try:
        example_parse_void_file()
        print("\n")

        # Uncomment to run additional examples
        # Note: These examples make real network requests to SPARQL endpoints

        # example_extract_from_endpoint()
        # print("\n")

        # example_generate_void()
        # print("\n")

        # example_validate_void()
        # print("\n")

        example_export_void()
        print("\n")

        example_parse_linkset()

    except KeyboardInterrupt:
        logger.info("\nExamples interrupted by user")
    except Exception as e:
        logger.error(f"Error running examples: {e}", exc_info=True)
