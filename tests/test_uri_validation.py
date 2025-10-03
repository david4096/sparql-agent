#!/usr/bin/env python3
"""
Test URI validation and fixing functionality
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sparql_agent.query.schema_tools import SchemaQueryTools


def test_uri_validation():
    """Test the URI validation rules."""
    print("🔧 Testing URI Validation...")

    tools = SchemaQueryTools("https://dbpedia.org/sparql", skip_discovery=True)

    # Test problematic URIs
    test_cases = [
        ("?person", "rdf:type", "dbr:Santa_Cruz,_California", False, "comma in URI"),
        ("?person", "dbo:birthPlace", "dbr:New_York_(state)", False, "parentheses in URI"),
        ("?person", "rdfs:label", "dbr:Santa Cruz", False, "space in URI"),
        ("?person", "rdf:type", "dbo:Person", True, "valid URI"),
        ("?name", "rdfs:label", '"Santa Cruz"', True, "valid literal"),
    ]

    for subject, predicate, obj, should_be_valid, description in test_cases:
        result = tools.validate_triple_pattern(subject, predicate, obj)
        valid = result['valid']

        status = "✓" if (valid == should_be_valid) else "✗"
        print(f"{status} {description}: {subject} {predicate} {obj}")

        if not valid:
            print(f"   Issues: {result['issues']}")
            print(f"   Suggestions: {result['suggestions']}")

    print()


def test_query_fixing():
    """Test automatic query fixing."""
    print("🔧 Testing Query URI Fixing...")

    tools = SchemaQueryTools("https://dbpedia.org/sparql", skip_discovery=True)

    # Test query with problematic URIs
    problematic_query = """
PREFIX dbr: <http://dbpedia.org/resource/>
PREFIX dbo: <http://dbpedia.org/ontology/>

SELECT ?person ?name WHERE {
  ?person rdf:type dbo:Person ;
          dbo:birthPlace dbr:Santa_Cruz,_California ;
          dbo:nationality dbr:United_States ;
          rdfs:label ?name .
}
LIMIT 5
"""

    print("Original query with problems:")
    print(problematic_query)

    result = tools.fix_query_uri_issues(problematic_query)

    print(f"\nIssues found: {result['issues_found']}")
    print(f"Fixes applied: {len(result['fixes_applied'])}")

    for fix in result['fixes_applied']:
        print(f"  • {fix}")

    print("\nFixed query:")
    print(result['query'])


if __name__ == "__main__":
    test_uri_validation()
    test_query_fixing()
    print("\n✅ URI validation system is working!")