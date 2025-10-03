"""
Example usage of OntologyMapper and VocabularyDetector

This file demonstrates the capabilities of the ontology mapping
and vocabulary detection system.
"""

from ontology_mapper import (
    OntologyMapper,
    VocabularyDetector,
    OntologyMapping,
    OntologyDomain,
    detect_vocabularies_in_text
)


def example_basic_mapping():
    """Example 1: Basic vocabulary lookup and mapping"""
    print("=" * 70)
    print("Example 1: Basic Vocabulary Lookup")
    print("=" * 70)

    mapper = OntologyMapper()

    # Look up vocabulary by prefix
    foaf = mapper.get_vocabulary_by_prefix("foaf")
    print(f"\nFOAF Vocabulary:")
    print(f"  Name: {foaf.name}")
    print(f"  Namespace: {foaf.namespace}")
    print(f"  Description: {foaf.description}")
    print(f"  Domain: {foaf.domain.value}")

    # Extract prefix from URI
    uri = "http://xmlns.com/foaf/0.1/Person"
    prefix_info = mapper.extract_prefix_from_uri(uri)
    if prefix_info:
        prefix, local_name = prefix_info
        print(f"\nURI Analysis:")
        print(f"  Full URI: {uri}")
        print(f"  Prefix: {prefix}")
        print(f"  Local name: {local_name}")


def example_life_science_ontologies():
    """Example 2: Life science ontology support"""
    print("\n" + "=" * 70)
    print("Example 2: Life Science Ontologies")
    print("=" * 70)

    mapper = OntologyMapper()

    # List all life science ontologies
    life_sci_vocabs = mapper.list_vocabularies_by_domain(OntologyDomain.LIFE_SCIENCES)

    print(f"\nFound {len(life_sci_vocabs)} life science ontologies:")
    for vocab in life_sci_vocabs:
        print(f"  {vocab.prefix:12s} - {vocab.name}")

    # Look up specific life science vocabulary
    uniprot = mapper.get_vocabulary_by_prefix("uniprot")
    print(f"\nUniProt Core Ontology:")
    print(f"  Namespace: {uniprot.namespace}")
    print(f"  Homepage: {uniprot.homepage}")

    go = mapper.get_vocabulary_by_prefix("go")
    print(f"\nGene Ontology:")
    print(f"  Namespace: {go.namespace}")
    print(f"  Homepage: {go.homepage}")


def example_owl_same_as():
    """Example 3: owl:sameAs relationship handling"""
    print("\n" + "=" * 70)
    print("Example 3: owl:sameAs Relationships")
    print("=" * 70)

    mapper = OntologyMapper()

    # Schema.org has some built-in sameAs mappings
    schema_person = "http://schema.org/Person"
    foaf_person = "http://xmlns.com/foaf/0.1/Person"

    equivalents = mapper.get_equivalent_uris(schema_person)
    print(f"\nEquivalent URIs for {schema_person}:")
    for uri in equivalents:
        print(f"  {uri}")

    # Add custom mapping
    mapper.add_same_as_mapping(
        "http://example.org/Person",
        schema_person
    )

    equivalents = mapper.get_equivalent_uris("http://example.org/Person")
    print(f"\nAfter adding custom mapping, equivalent URIs for http://example.org/Person:")
    for uri in equivalents:
        print(f"  {uri}")

    # Resolve to preferred form
    resolved = mapper.resolve_uri("http://example.org/Person")
    print(f"\nResolved canonical form: {resolved}")


def example_vocabulary_detection():
    """Example 4: Detect vocabularies in SPARQL query"""
    print("\n" + "=" * 70)
    print("Example 4: Vocabulary Detection in SPARQL")
    print("=" * 70)

    sparql_query = """
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    PREFIX schema: <http://schema.org/>
    PREFIX dc: <http://purl.org/dc/elements/1.1/>
    PREFIX uniprot: <http://purl.uniprot.org/core/>
    PREFIX go: <http://purl.obolibrary.org/obo/GO_>

    SELECT ?person ?name ?protein ?function WHERE {
        ?person a foaf:Person ;
                foaf:name ?name ;
                schema:worksFor ?org .

        ?protein a uniprot:Protein ;
                 uniprot:annotation ?annotation .

        ?annotation uniprot:goTerm ?goterm .
        ?goterm a go:0003674 .
    }
    """

    detector = detect_vocabularies_in_text(sparql_query)

    print("\nTop vocabularies detected:")
    for prefix, count in detector.get_top_vocabularies(10):
        print(f"  {prefix:15s} {count:3d} occurrences")

    print("\nVocabularies by domain:")
    for domain, prefixes in detector.identify_ontologies().items():
        print(f"  {domain.value}:")
        for prefix in prefixes:
            usage = detector.usage_stats[prefix]
            vocab = detector.mapper.get_vocabulary_by_prefix(prefix)
            name = vocab.name if vocab else "Unknown"
            print(f"    {prefix:12s} ({name})")


def example_vocabulary_analysis():
    """Example 5: Detailed vocabulary usage analysis"""
    print("\n" + "=" * 70)
    print("Example 5: Detailed Vocabulary Analysis")
    print("=" * 70)

    mapper = OntologyMapper()
    detector = VocabularyDetector(mapper)

    # Simulate analyzing some triples
    triples = [
        ("http://example.org/person1", "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", "http://xmlns.com/foaf/0.1/Person"),
        ("http://example.org/person1", "http://xmlns.com/foaf/0.1/name", "Alice"),
        ("http://example.org/person1", "http://xmlns.com/foaf/0.1/mbox", "mailto:alice@example.org"),
        ("http://example.org/protein1", "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", "http://purl.uniprot.org/core/Protein"),
        ("http://example.org/protein1", "http://purl.uniprot.org/core/organism", "http://purl.uniprot.org/taxonomy/9606"),
        ("http://example.org/dataset1", "http://purl.org/dc/terms/title", "My Dataset"),
        ("http://example.org/dataset1", "http://purl.org/dc/terms/creator", "http://example.org/person1"),
    ]

    print("\nAnalyzing triples...")
    for s, p, o in triples:
        detector.analyze_triple(s, p, o)

    print("\nVocabulary Statistics:")
    stats = detector.export_statistics()
    print(f"  Total vocabularies: {stats['vocabulary_count']}")
    print(f"  Total term uses: {stats['total_terms']}")

    print("\nPer-vocabulary details:")
    for prefix, vocab_stats in stats['vocabularies'].items():
        print(f"\n  {prefix}:")
        print(f"    Namespace: {vocab_stats['namespace']}")
        print(f"    Term count: {vocab_stats['term_count']}")
        print(f"    Unique terms: {vocab_stats['unique_terms']}")
        print(f"    Properties: {vocab_stats['property_count']}")
        print(f"    Classes: {vocab_stats['class_count']}")

    # Generate full report
    print("\n" + "=" * 70)
    print(detector.get_coverage_report())


def example_search_vocabularies():
    """Example 6: Search for vocabularies"""
    print("\n" + "=" * 70)
    print("Example 6: Search Vocabularies")
    print("=" * 70)

    mapper = OntologyMapper()

    # Search for vocabularies
    queries = ["protein", "metadata", "person", "gene"]

    for query in queries:
        results = mapper.search_vocabularies(query)
        print(f"\nSearch results for '{query}':")
        for vocab in results:
            print(f"  {vocab.prefix:12s} - {vocab.name}")
            print(f"    {vocab.description}")


def example_fair_vocabulary():
    """Example 7: FAIR vocabulary support"""
    print("\n" + "=" * 70)
    print("Example 7: FAIR Vocabulary Support")
    print("=" * 70)

    mapper = OntologyMapper()

    # Look up FAIR vocabulary
    fair = mapper.get_vocabulary_by_prefix("fair")
    print(f"\nFAIR Principles Vocabulary:")
    print(f"  Name: {fair.name}")
    print(f"  Namespace: {fair.namespace}")
    print(f"  Description: {fair.description}")
    print(f"  Homepage: {fair.homepage}")

    fdp = mapper.get_vocabulary_by_prefix("fdp")
    print(f"\nFAIR Data Point Ontology:")
    print(f"  Name: {fdp.name}")
    print(f"  Namespace: {fdp.namespace}")
    print(f"  Description: {fdp.description}")


def example_lov_integration():
    """Example 8: Linked Open Vocabularies (LOV) integration"""
    print("\n" + "=" * 70)
    print("Example 8: LOV Integration")
    print("=" * 70)

    mapper = OntologyMapper()

    vocabs_with_lov = ["foaf", "dc", "dcterms", "schema", "prov", "dcat"]

    print("\nLinked Open Vocabularies URLs:")
    for prefix in vocabs_with_lov:
        lov_url = mapper.get_lov_url(prefix)
        vocab = mapper.get_vocabulary_by_prefix(prefix)
        if lov_url and vocab:
            print(f"  {prefix:10s} - {vocab.name}")
            print(f"    LOV: {lov_url}")


def example_cross_vocabulary_reasoning():
    """Example 9: Cross-vocabulary reasoning"""
    print("\n" + "=" * 70)
    print("Example 9: Cross-Vocabulary Reasoning")
    print("=" * 70)

    mapper = OntologyMapper()

    # Add custom mappings for reasoning
    mapping = OntologyMapping(
        source_uri="http://schema.org/name",
        target_uri="http://xmlns.com/foaf/0.1/name",
        mapping_type="owl:sameAs",
        confidence=1.0
    )
    mapper.add_mapping(mapping)

    mapping2 = OntologyMapping(
        source_uri="http://purl.org/dc/terms/creator",
        target_uri="http://schema.org/author",
        mapping_type="skos:closeMatch",
        confidence=0.8
    )
    mapper.add_mapping(mapping2)

    print("\nAdded cross-vocabulary mappings:")
    print(f"  schema:name ←→ foaf:name (owl:sameAs)")
    print(f"  dcterms:creator ≈ schema:author (skos:closeMatch, 0.8 confidence)")

    # Show equivalents
    name_equivalents = mapper.get_equivalent_uris("http://schema.org/name")
    print(f"\nEquivalent URIs for schema:name:")
    for uri in name_equivalents:
        prefix_info = mapper.extract_prefix_from_uri(uri)
        if prefix_info:
            prefix, local = prefix_info
            print(f"  {prefix}:{local}")


def example_obo_ontologies():
    """Example 10: OBO Foundry ontologies"""
    print("\n" + "=" * 70)
    print("Example 10: OBO Foundry Ontologies")
    print("=" * 70)

    mapper = OntologyMapper()

    obo_vocabs = ["go", "so", "chebi", "hp", "mondo", "ncit", "efo"]

    print("\nOBO Foundry Ontologies:")
    for prefix in obo_vocabs:
        vocab = mapper.get_vocabulary_by_prefix(prefix)
        if vocab:
            print(f"\n  {vocab.prefix.upper()}:")
            print(f"    Name: {vocab.name}")
            print(f"    Namespace: {vocab.namespace}")
            print(f"    Homepage: {vocab.homepage}")


def main():
    """Run all examples"""
    examples = [
        example_basic_mapping,
        example_life_science_ontologies,
        example_owl_same_as,
        example_vocabulary_detection,
        example_vocabulary_analysis,
        example_search_vocabularies,
        example_fair_vocabulary,
        example_lov_integration,
        example_cross_vocabulary_reasoning,
        example_obo_ontologies,
    ]

    print("\n" + "=" * 70)
    print("ONTOLOGY MAPPER AND VOCABULARY DETECTOR")
    print("Example Usage Demonstrations")
    print("=" * 70)

    for i, example_func in enumerate(examples, 1):
        try:
            example_func()
        except Exception as e:
            print(f"\nError in example {i}: {e}")

    print("\n" + "=" * 70)
    print("All examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
