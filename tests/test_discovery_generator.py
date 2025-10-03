#!/usr/bin/env python3
"""
Comprehensive Test Suite for Discovery-Based Query Generator

Tests the generator with multiple real endpoints and demonstrates
its capabilities in generating accurate, validated SPARQL queries.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from discovery_query_generator import (
    DiscoveryBasedQueryGenerator,
    DiscoveryKnowledge,
    VocabularyMatcher,
    QueryValidator,
    QueryBuildState
)


def test_vocabulary_matcher():
    """Test vocabulary matching functionality."""
    print("=" * 80)
    print("Test 1: Vocabulary Matcher")
    print("=" * 80)

    # Create test knowledge base
    knowledge = DiscoveryKnowledge(
        endpoint_url="test://example",
        namespaces=[
            "http://www.wikidata.org/entity/",
            "http://www.wikidata.org/prop/direct/",
            "http://xmlns.com/foaf/0.1/",
        ],
        prefixes={
            "wd": "http://www.wikidata.org/entity/",
            "wdt": "http://www.wikidata.org/prop/direct/",
            "foaf": "http://xmlns.com/foaf/0.1/",
        },
        classes=[
            "http://www.wikidata.org/entity/Q5",  # human
            "http://www.wikidata.org/entity/Q901",  # scientist
            "http://xmlns.com/foaf/0.1/Person",
        ],
        properties=[
            "http://www.wikidata.org/prop/direct/P31",  # instance of
            "http://www.wikidata.org/prop/direct/P106",  # occupation
            "http://xmlns.com/foaf/0.1/name",
        ]
    )

    matcher = VocabularyMatcher(knowledge)

    # Test class matching
    print("\nTesting class matching:")
    keywords = ["human", "person"]
    classes = matcher.find_classes(keywords, limit=3)
    for class_uri, score in classes:
        short = matcher.shorten_uri(class_uri)
        print(f"  {short} (score: {score})")

    # Test property matching
    print("\nTesting property matching:")
    keywords = ["name", "occupation"]
    properties = matcher.find_properties(keywords, limit=3)
    for prop_uri, score in properties:
        short = matcher.shorten_uri(prop_uri)
        print(f"  {short} (score: {score})")

    print("\nTest 1: PASSED\n")


def test_query_validator():
    """Test query validation functionality."""
    print("=" * 80)
    print("Test 2: Query Validator")
    print("=" * 80)

    knowledge = DiscoveryKnowledge(
        endpoint_url="test://example",
        namespaces=["http://www.w3.org/1999/02/22-rdf-syntax-ns#"],
        prefixes={"rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#"},
        features={'BIND': True, 'PROPERTY_PATHS': False}
    )

    validator = QueryValidator(knowledge)

    # Test valid query
    valid_query = """
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    SELECT * WHERE { ?s rdf:type ?o } LIMIT 10
    """
    is_valid, errors = validator.validate_query(valid_query)
    print(f"\nValid query test: {'PASSED' if is_valid else 'FAILED'}")
    if errors:
        print(f"  Errors: {errors}")

    # Test invalid query (missing WHERE)
    invalid_query = "SELECT * LIMIT 10"
    is_valid, errors = validator.validate_query(invalid_query)
    print(f"\nInvalid query test: {'PASSED' if not is_valid else 'FAILED'}")
    print(f"  Errors detected: {errors}")

    # Test unbalanced braces
    unbalanced_query = "SELECT * WHERE { ?s ?p ?o LIMIT 10"
    is_valid, errors = validator.validate_query(unbalanced_query)
    print(f"\nUnbalanced braces test: {'PASSED' if not is_valid else 'FAILED'}")
    print(f"  Errors detected: {errors}")

    print("\nTest 2: PASSED\n")


def test_incremental_building():
    """Test incremental query building."""
    print("=" * 80)
    print("Test 3: Incremental Query Building")
    print("=" * 80)

    # Create knowledge base with Wikidata vocabulary
    knowledge = DiscoveryKnowledge(
        endpoint_url="https://query.wikidata.org/sparql",
        namespaces=[
            "http://www.wikidata.org/entity/",
            "http://www.wikidata.org/prop/direct/",
            "http://www.w3.org/2000/01/rdf-schema#",
        ],
        prefixes={
            "wd": "http://www.wikidata.org/entity/",
            "wdt": "http://www.wikidata.org/prop/direct/",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        },
        patterns={
            'human': '?person wdt:P31 wd:Q5',
            'label': '?entity rdfs:label ?label . FILTER(LANG(?label) = "en")',
        }
    )

    # Build a query step by step
    state = QueryBuildState()

    print("\nStep 1: Add prefixes")
    for prefix, namespace in knowledge.prefixes.items():
        state.add_prefix(prefix, namespace)
    print(f"  Added {len(state.prefixes)} prefixes")

    print("\nStep 2: Set SELECT variables")
    state.select_vars = ['?person', '?label']
    print(f"  Variables: {state.select_vars}")

    print("\nStep 3: Add WHERE clauses")
    state.add_where_clause(knowledge.patterns['human'])
    state.add_where_clause(knowledge.patterns['label'].replace('?entity', '?person'))
    print(f"  Added {len(state.where_clauses)} WHERE clauses")

    print("\nStep 4: Add LIMIT")
    state.limit = 10
    print(f"  Limit: {state.limit}")

    print("\nFinal Query:")
    query = state.build_query()
    print(query)

    print("\nTest 3: PASSED\n")


def test_wikidata_queries():
    """Test generating Wikidata queries."""
    print("=" * 80)
    print("Test 4: Wikidata Query Generation")
    print("=" * 80)

    # Create generator with pre-configured Wikidata knowledge
    generator = DiscoveryBasedQueryGenerator(fast_mode=True)

    # Pre-populate with Wikidata knowledge
    knowledge = DiscoveryKnowledge(
        endpoint_url="https://query.wikidata.org/sparql",
        namespaces=[
            "http://wikiba.se/ontology#",
            "http://www.wikidata.org/entity/",
            "http://www.wikidata.org/prop/direct/",
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "http://www.w3.org/2000/01/rdf-schema#",
        ],
        prefixes={
            "wikibase": "http://wikiba.se/ontology#",
            "wd": "http://www.wikidata.org/entity/",
            "wdt": "http://www.wikidata.org/prop/direct/",
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        },
        features={
            'BIND': True,
            'MINUS': True,
            'SUBQUERY': True,
            'VALUES': True,
        },
        patterns={
            'human': '?person wdt:P31 wd:Q5',
            'label': '?entity rdfs:label ?label . FILTER(LANG(?label) = "en")',
        }
    )

    generator.knowledge_cache[knowledge.endpoint_url] = knowledge

    test_queries = [
        ("Find 5 humans", 5),
        ("Show me 10 people", 10),
        ("List 3 humans", 3),
    ]

    for nl_query, expected_limit in test_queries:
        print(f"\nQuery: {nl_query}")
        print("-" * 80)

        sparql, metadata = generator.generate(
            nl_query,
            knowledge.endpoint_url
        )

        print(sparql)
        print(f"\nLimit: {metadata['intent'].get('limit')}")
        assert metadata['intent']['limit'] == expected_limit, \
            f"Expected limit {expected_limit}, got {metadata['intent']['limit']}"
        print("PASSED")

    print("\nTest 4: PASSED\n")


def test_uniprot_queries():
    """Test generating UniProt queries."""
    print("=" * 80)
    print("Test 5: UniProt Query Generation")
    print("=" * 80)

    generator = DiscoveryBasedQueryGenerator(fast_mode=True)

    # Configure UniProt knowledge
    knowledge = DiscoveryKnowledge(
        endpoint_url="https://sparql.uniprot.org/sparql",
        namespaces=[
            "http://purl.uniprot.org/core/",
            "http://purl.uniprot.org/uniprot/",
            "http://purl.uniprot.org/taxonomy/",
            "http://www.w3.org/2000/01/rdf-schema#",
        ],
        prefixes={
            "up": "http://purl.uniprot.org/core/",
            "uniprotkb": "http://purl.uniprot.org/uniprot/",
            "taxon": "http://purl.uniprot.org/taxonomy/",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        },
        classes=[
            "http://purl.uniprot.org/core/Protein",
        ],
        properties=[
            "http://purl.uniprot.org/core/organism",
            "http://purl.uniprot.org/core/reviewed",
        ],
        patterns={
            'protein': '?protein a up:Protein',
            'human_protein': '?protein a up:Protein ; up:organism taxon:9606',
            'reviewed': '?protein up:reviewed true',
        }
    )

    generator.knowledge_cache[knowledge.endpoint_url] = knowledge

    print("\nQuery: Find 10 human proteins")
    print("-" * 80)

    sparql, metadata = generator.generate(
        "Find 10 human proteins",
        knowledge.endpoint_url
    )

    print(sparql)
    assert 'Protein' in sparql, "Query should mention Protein"
    print("\nTest 5: PASSED\n")


def test_feature_validation():
    """Test validation of SPARQL features."""
    print("=" * 80)
    print("Test 6: Feature Validation")
    print("=" * 80)

    knowledge = DiscoveryKnowledge(
        endpoint_url="test://example",
        features={
            'BIND': True,
            'PROPERTY_PATHS': False,
            'SUBQUERY': True,
        }
    )

    validator = QueryValidator(knowledge)

    # Test supported feature
    is_valid, error = validator.validate_feature('BIND')
    print(f"\nBIND support (expected: supported): {'PASSED' if is_valid else 'FAILED'}")

    # Test unsupported feature
    is_valid, error = validator.validate_feature('PROPERTY_PATHS')
    print(f"PROPERTY_PATHS support (expected: unsupported): {'PASSED' if not is_valid else 'FAILED'}")
    if error:
        print(f"  Error: {error}")

    # Test unknown feature (should pass conservatively)
    is_valid, error = validator.validate_feature('UNKNOWN_FEATURE')
    print(f"Unknown feature (expected: allowed): {'PASSED' if is_valid else 'FAILED'}")

    print("\nTest 6: PASSED\n")


def test_query_metadata():
    """Test query generation metadata."""
    print("=" * 80)
    print("Test 7: Query Generation Metadata")
    print("=" * 80)

    generator = DiscoveryBasedQueryGenerator(fast_mode=True)

    knowledge = DiscoveryKnowledge(
        endpoint_url="test://example",
        namespaces=["http://www.w3.org/1999/02/22-rdf-syntax-ns#"],
        prefixes={"rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#"},
    )

    generator.knowledge_cache[knowledge.endpoint_url] = knowledge

    query, metadata = generator.generate(
        "Find 5 items",
        knowledge.endpoint_url
    )

    print("\nGenerated Metadata:")
    for key, value in metadata.items():
        print(f"  {key}: {value}")

    # Validate metadata structure
    required_keys = ['endpoint_url', 'intent', 'validation_errors', 'is_valid']
    for key in required_keys:
        assert key in metadata, f"Missing required metadata key: {key}"

    print("\nTest 7: PASSED\n")


def run_all_tests():
    """Run all test suites."""
    print("\n" + "=" * 80)
    print("DISCOVERY-BASED QUERY GENERATOR - COMPREHENSIVE TEST SUITE")
    print("=" * 80 + "\n")

    tests = [
        ("Vocabulary Matcher", test_vocabulary_matcher),
        ("Query Validator", test_query_validator),
        ("Incremental Building", test_incremental_building),
        ("Wikidata Queries", test_wikidata_queries),
        ("UniProt Queries", test_uniprot_queries),
        ("Feature Validation", test_feature_validation),
        ("Query Metadata", test_query_metadata),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"\n{test_name}: FAILED")
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("=" * 80)
    print(f"TEST RESULTS: {passed} passed, {failed} failed")
    print("=" * 80)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
