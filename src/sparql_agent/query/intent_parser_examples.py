"""
Example usage of the Intent Parser for natural language query understanding.

This module demonstrates how to use the IntentParser to extract structured information
from natural language queries for SPARQL generation.
"""

from sparql_agent.query.intent_parser import (
    IntentParser,
    QueryType,
    AggregationType,
    parse_query,
    classify_query
)
from sparql_agent.core.types import SchemaInfo, OntologyInfo, OWLClass, OWLProperty


def example_basic_queries():
    """Examples of parsing basic queries."""
    print("=" * 80)
    print("BASIC QUERY EXAMPLES")
    print("=" * 80)

    parser = IntentParser()

    queries = [
        "Find all proteins from human",
        "List diseases in the dataset",
        "Show me all genes",
        "Get publications about cancer",
        "What are the available datasets?",
    ]

    for query in queries:
        print(f"\nQuery: {query}")
        intent = parser.parse(query)
        print(f"  Type: {intent.query_type.value}")
        print(f"  Entities: {len(intent.entities)}")
        for entity in intent.entities:
            print(f"    - {entity.text} (type: {entity.type}, confidence: {entity.confidence})")
        print(f"  Confidence: {intent.confidence}")
        print(f"  Pattern: {parser.classify_query_pattern(intent)}")


def example_aggregation_queries():
    """Examples of parsing aggregation queries."""
    print("\n" + "=" * 80)
    print("AGGREGATION QUERY EXAMPLES")
    print("=" * 80)

    parser = IntentParser()

    queries = [
        "How many proteins are there?",
        "Count the number of diseases",
        "What is the average expression level?",
        "Show me the total number of variants per gene",
        "Find the maximum score for each protein",
        "Count distinct organisms",
    ]

    for query in queries:
        print(f"\nQuery: {query}")
        intent = parser.parse(query)
        print(f"  Type: {intent.query_type.value}")
        print(f"  Aggregations:")
        for agg in intent.aggregations:
            print(f"    - {agg.type.value}(?{agg.variable}) AS ?{agg.result_variable}")
            if agg.group_by:
                print(f"      GROUP BY: {', '.join(agg.group_by)}")
            if agg.distinct:
                print(f"      DISTINCT: True")
        print(f"  Pattern: {parser.classify_query_pattern(intent)}")


def example_filter_queries():
    """Examples of parsing queries with filters."""
    print("\n" + "=" * 80)
    print("FILTER QUERY EXAMPLES")
    print("=" * 80)

    parser = IntentParser()

    queries = [
        "Find proteins where organism is 9606",
        "Show genes with expression greater than 100",
        "List diseases containing 'cancer'",
        "Get publications with year less than 2020",
        "Find proteins with mass at least 50000",
    ]

    for query in queries:
        print(f"\nQuery: {query}")
        intent = parser.parse(query)
        print(f"  Type: {intent.query_type.value}")
        print(f"  Filters:")
        for filter_obj in intent.filters:
            print(f"    - ?{filter_obj.variable} {filter_obj.operator.value} {filter_obj.value}")
        print(f"  Pattern: {parser.classify_query_pattern(intent)}")


def example_ordering_queries():
    """Examples of parsing queries with ordering."""
    print("\n" + "=" * 80)
    print("ORDERING QUERY EXAMPLES")
    print("=" * 80)

    parser = IntentParser()

    queries = [
        "Top 10 proteins by score",
        "Show me the first 5 genes order by name",
        "Find highest scoring publications",
        "List diseases in descending order of prevalence",
        "Top 20 organisms by protein count",
    ]

    for query in queries:
        print(f"\nQuery: {query}")
        intent = parser.parse(query)
        print(f"  Type: {intent.query_type.value}")
        print(f"  Order By:")
        for order in intent.order_by:
            print(f"    - ?{order.variable} {order.direction.value}")
        print(f"  Limit: {intent.limit}")
        print(f"  Pattern: {parser.classify_query_pattern(intent)}")


def example_text_search_queries():
    """Examples of parsing text search queries."""
    print("\n" + "=" * 80)
    print("TEXT SEARCH QUERY EXAMPLES")
    print("=" * 80)

    parser = IntentParser()

    queries = [
        "Search for genes related to 'immune response'",
        "Find proteins containing 'kinase'",
        "Show diseases matching 'diabetes'",
        "Get publications about 'machine learning' and 'genomics'",
    ]

    for query in queries:
        print(f"\nQuery: {query}")
        intent = parser.parse(query)
        print(f"  Type: {intent.query_type.value}")
        print(f"  Text Search Terms:")
        for term in intent.text_search:
            print(f"    - '{term}'")
        print(f"  Pattern: {parser.classify_query_pattern(intent)}")


def example_complex_queries():
    """Examples of parsing complex queries."""
    print("\n" + "=" * 80)
    print("COMPLEX QUERY EXAMPLES")
    print("=" * 80)

    parser = IntentParser()

    queries = [
        "Find genes associated with diseases and their functions",
        "Show proteins from human with expression greater than 100 ordered by score",
        "Count distinct diseases per gene where prevalence is greater than 0.01",
        "Top 10 publications about cancer with citations greater than 100",
        "List genes with optional protein interactions",
    ]

    for query in queries:
        print(f"\nQuery: {query}")
        intent = parser.parse(query)
        print(f"  Type: {intent.query_type.value}")
        print(f"  Entities: {len(intent.entities)}")
        print(f"  Filters: {len(intent.filters)}")
        print(f"  Aggregations: {len(intent.aggregations)}")
        print(f"  Order By: {len(intent.order_by)}")
        print(f"  Limit: {intent.limit}")
        print(f"  Optional: {intent.optional_patterns}")
        print(f"  Confidence: {intent.confidence}")
        print(f"  Pattern: {parser.classify_query_pattern(intent)}")


def example_ask_queries():
    """Examples of parsing ASK queries."""
    print("\n" + "=" * 80)
    print("ASK QUERY EXAMPLES")
    print("=" * 80)

    parser = IntentParser()

    queries = [
        "Is TP53 a gene?",
        "Does this protein have kinase activity?",
        "Are there any diseases associated with this gene?",
        "Has this publication been cited?",
    ]

    for query in queries:
        print(f"\nQuery: {query}")
        intent = parser.parse(query)
        print(f"  Type: {intent.query_type.value}")
        print(f"  Pattern: {parser.classify_query_pattern(intent)}")


def example_describe_queries():
    """Examples of parsing DESCRIBE queries."""
    print("\n" + "=" * 80)
    print("DESCRIBE QUERY EXAMPLES")
    print("=" * 80)

    parser = IntentParser()

    queries = [
        "Describe the gene TP53",
        "Tell me about Alzheimer's disease",
        "What is UniProt?",
        "Show information about this protein",
    ]

    for query in queries:
        print(f"\nQuery: {query}")
        intent = parser.parse(query)
        print(f"  Type: {intent.query_type.value}")
        print(f"  Entities: {[e.text for e in intent.entities]}")
        print(f"  Pattern: {parser.classify_query_pattern(intent)}")


def example_with_ontology():
    """Example using ontology information for entity resolution."""
    print("\n" + "=" * 80)
    print("ENTITY RESOLUTION WITH ONTOLOGY")
    print("=" * 80)

    # Create mock ontology info
    ontology = OntologyInfo(uri="http://example.org/ontology")

    # Add some classes
    protein_class = OWLClass(
        uri="http://purl.uniprot.org/core/Protein",
        label=["Protein", "protein"],
        comment=["A protein entry"]
    )
    gene_class = OWLClass(
        uri="http://purl.obolibrary.org/obo/SO_0000704",
        label=["Gene", "gene"],
        comment=["A gene"]
    )

    ontology.classes = {
        protein_class.uri: protein_class,
        gene_class.uri: gene_class
    }

    # Add some properties
    organism_prop = OWLProperty(
        uri="http://purl.uniprot.org/core/organism",
        label=["organism", "from organism"],
        comment=["The organism this protein is from"]
    )
    ontology.properties = {organism_prop.uri: organism_prop}

    # Create parser with ontology
    parser = IntentParser(ontology_info=ontology)

    query = "Find all proteins from human"
    print(f"Query: {query}")
    intent = parser.parse(query)

    print(f"\nEntities with resolved URIs:")
    for entity in intent.entities:
        if entity.uri:
            print(f"  - {entity.text} -> {entity.uri}")
        else:
            print(f"  - {entity.text} (unresolved)")


def example_with_schema():
    """Example using schema information for entity resolution."""
    print("\n" + "=" * 80)
    print("ENTITY RESOLUTION WITH SCHEMA")
    print("=" * 80)

    # Create mock schema info
    schema = SchemaInfo()
    schema.classes = {
        "http://purl.uniprot.org/core/Protein",
        "http://purl.obolibrary.org/obo/SO_0000704",  # Gene
        "http://purl.obolibrary.org/obo/MONDO_0000001",  # Disease
    }
    schema.properties = {
        "http://purl.uniprot.org/core/organism",
        "http://purl.uniprot.org/core/recommendedName",
    }

    # Create parser with schema
    parser = IntentParser(schema_info=schema)

    query = "Find all proteins and genes"
    print(f"Query: {query}")
    intent = parser.parse(query)

    print(f"\nEntities with resolved URIs:")
    for entity in intent.entities:
        if entity.uri:
            print(f"  - {entity.text} -> {entity.uri}")
        else:
            print(f"  - {entity.text} (unresolved)")


def example_query_structure_suggestion():
    """Example of suggesting query structure."""
    print("\n" + "=" * 80)
    print("QUERY STRUCTURE SUGGESTION")
    print("=" * 80)

    parser = IntentParser()

    queries = [
        "Count proteins per organism",
        "Top 10 genes by expression",
        "Find diseases containing 'cancer'",
    ]

    for query in queries:
        print(f"\nQuery: {query}")
        intent = parser.parse(query)
        structure = parser.suggest_query_structure(intent)

        print(f"  Pattern: {structure['pattern']}")
        print(f"  Query Type: {structure['query_type']}")
        print(f"  SELECT Variables:")
        for var in structure['select_variables']:
            print(f"    - {var}")
        print(f"  WHERE Patterns:")
        for pattern in structure['where_patterns']:
            print(f"    - {pattern}")
        if structure['filters']:
            print(f"  FILTERS:")
            for filter_obj in structure['filters']:
                print(f"    - {filter_obj}")
        if structure['modifiers']:
            print(f"  MODIFIERS:")
            for key, value in structure['modifiers'].items():
                print(f"    - {key}: {value}")


def example_ambiguity_detection():
    """Example of detecting ambiguities."""
    print("\n" + "=" * 80)
    print("AMBIGUITY DETECTION")
    print("=" * 80)

    parser = IntentParser()

    # Queries with potential ambiguities
    queries = [
        "Find proteins with high expression",  # "high" is ambiguous
        "Show genes related to cancer",  # "related to" is vague
        "Get recent publications",  # "recent" needs definition
    ]

    for query in queries:
        print(f"\nQuery: {query}")
        intent = parser.parse(query)

        if intent.ambiguities:
            print(f"  Ambiguities detected:")
            for amb in intent.ambiguities:
                print(f"    - [{amb['type']}] {amb['message']}")
        else:
            print(f"  No ambiguities detected")

        print(f"  Confidence: {intent.confidence}")


def example_quick_utilities():
    """Example using quick utility functions."""
    print("\n" + "=" * 80)
    print("QUICK UTILITY FUNCTIONS")
    print("=" * 80)

    query = "Count proteins per organism"

    # Quick parse
    print(f"Query: {query}")
    intent = parse_query(query)
    print(f"  Type: {intent.query_type.value}")
    print(f"  Entities: {len(intent.entities)}")
    print(f"  Aggregations: {len(intent.aggregations)}")

    # Quick classify
    pattern = classify_query(query)
    print(f"  Pattern: {pattern}")


def run_all_examples():
    """Run all examples."""
    example_basic_queries()
    example_aggregation_queries()
    example_filter_queries()
    example_ordering_queries()
    example_text_search_queries()
    example_complex_queries()
    example_ask_queries()
    example_describe_queries()
    example_with_ontology()
    example_with_schema()
    example_query_structure_suggestion()
    example_ambiguity_detection()
    example_quick_utilities()


if __name__ == "__main__":
    run_all_examples()
