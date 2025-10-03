"""
Tests for SPARQL query validator.
"""

import pytest

from ..core.exceptions import QuerySyntaxError
from .validator import (
    QueryValidator,
    ValidationSeverity,
    validate_and_raise,
    validate_query,
)


class TestQueryValidator:
    """Test suite for QueryValidator."""

    def test_valid_simple_query(self):
        """Test validation of a simple valid query."""
        query = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT ?s ?p ?o
        WHERE {
            ?s ?p ?o .
        }
        LIMIT 10
        """
        result = validate_query(query)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_empty_query(self):
        """Test validation of empty query."""
        result = validate_query("")
        assert not result.is_valid
        assert len(result.errors) == 1
        assert "empty" in result.errors[0].message.lower()

    def test_unbalanced_parentheses(self):
        """Test detection of unbalanced parentheses."""
        query = """
        SELECT ?s
        WHERE {
            FILTER(?s > 10
        }
        """
        result = validate_query(query)
        assert not result.is_valid
        errors = [e for e in result.issues if "parenthes" in e.message.lower()]
        assert len(errors) > 0

    def test_unbalanced_braces(self):
        """Test detection of unbalanced braces."""
        query = """
        SELECT ?s
        WHERE {
            ?s ?p ?o .
        """
        result = validate_query(query)
        assert not result.is_valid
        errors = [e for e in result.issues if "brace" in e.message.lower()]
        assert len(errors) > 0

    def test_undeclared_prefix(self):
        """Test detection of undeclared prefix."""
        query = """
        SELECT ?s
        WHERE {
            ?s rdf:type foaf:Person .
        }
        """
        result = validate_query(query)
        assert not result.is_valid
        errors = [e for e in result.issues if "prefix" in e.message.lower()]
        assert len(errors) >= 2  # Both rdf and foaf undeclared

    def test_unused_prefix(self):
        """Test detection of unused prefix."""
        query = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX foaf: <http://xmlns.com/foaf/0.1/>
        SELECT ?s
        WHERE {
            ?s rdf:type ?type .
        }
        """
        result = validate_query(query)
        # Should have warning about unused foaf prefix
        warnings = [w for w in result.warning_issues if "foaf" in w.message]
        assert len(warnings) > 0

    def test_duplicate_prefix(self):
        """Test detection of duplicate prefix declarations."""
        query = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT ?s
        WHERE {
            ?s rdf:type ?type .
        }
        """
        result = validate_query(query)
        errors = [e for e in result.issues if "duplicate" in e.message.lower()]
        assert len(errors) > 0

    def test_unused_select_variable(self):
        """Test detection of selected but unused variables."""
        query = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT ?s ?p ?unused
        WHERE {
            ?s ?p ?o .
        }
        """
        result = validate_query(query)
        warnings = [w for w in result.warning_issues if "unused" in w.message.lower()]
        assert len(warnings) > 0

    def test_single_use_variable(self):
        """Test detection of variables used only once."""
        query = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT ?s
        WHERE {
            ?s rdf:type ?singleUse .
        }
        """
        result = validate_query(query)
        info_issues = [i for i in result.info_issues if "once" in i.message.lower()]
        assert len(info_issues) > 0

    def test_invalid_uri_with_spaces(self):
        """Test detection of URIs with spaces."""
        query = """
        SELECT ?s
        WHERE {
            ?s ?p <http://example.org/invalid uri> .
        }
        """
        result = validate_query(query)
        errors = [e for e in result.issues if "space" in e.message.lower()]
        assert len(errors) > 0

    def test_malformed_uri(self):
        """Test detection of malformed URIs."""
        query = """
        SELECT ?s
        WHERE {
            ?s ?p <not-a-valid-uri> .
        }
        """
        result = validate_query(query)
        # Should have warnings about malformed URI
        warnings = [w for w in result.issues if "malformed" in w.message.lower()]
        assert len(warnings) > 0

    def test_double_dot_error(self):
        """Test detection of double dots."""
        query = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT ?s
        WHERE {
            ?s rdf:type ?type ..
        }
        """
        result = validate_query(query)
        errors = [e for e in result.errors if "double dot" in e.message.lower()]
        assert len(errors) > 0

    def test_select_star_warning(self):
        """Test warning for SELECT * in strict mode."""
        query = """
        SELECT *
        WHERE {
            ?s ?p ?o .
        }
        """
        result = validate_query(query, strict=True)
        info_issues = [i for i in result.info_issues if "select *" in i.message.lower()]
        assert len(info_issues) > 0

    def test_missing_limit_warning(self):
        """Test warning for missing LIMIT in strict mode."""
        query = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT ?s
        WHERE {
            ?s rdf:type ?type .
        }
        """
        result = validate_query(query, strict=True)
        info_issues = [i for i in result.info_issues if "limit" in i.message.lower()]
        assert len(info_issues) > 0

    def test_valid_construct_query(self):
        """Test validation of CONSTRUCT query."""
        query = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX foaf: <http://xmlns.com/foaf/0.1/>
        CONSTRUCT {
            ?person foaf:name ?name .
        }
        WHERE {
            ?person rdf:type foaf:Person .
            ?person foaf:name ?name .
        }
        """
        result = validate_query(query)
        assert result.is_valid

    def test_valid_ask_query(self):
        """Test validation of ASK query."""
        query = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        ASK {
            ?s rdf:type ?type .
        }
        """
        result = validate_query(query)
        assert result.is_valid

    def test_valid_describe_query(self):
        """Test validation of DESCRIBE query."""
        query = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        DESCRIBE ?s
        WHERE {
            ?s rdf:type ?type .
        }
        """
        result = validate_query(query)
        assert result.is_valid

    def test_complex_valid_query(self):
        """Test validation of complex query with OPTIONAL, FILTER, UNION."""
        query = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX foaf: <http://xmlns.com/foaf/0.1/>

        SELECT ?person ?name ?age
        WHERE {
            ?person rdf:type foaf:Person .
            ?person foaf:name ?name .

            OPTIONAL {
                ?person foaf:age ?age .
                FILTER(?age > 18)
            }

            {
                ?person foaf:knows ?friend .
            } UNION {
                ?person foaf:member ?group .
            }
        }
        ORDER BY ?name
        LIMIT 100
        """
        result = validate_query(query)
        assert result.is_valid

    def test_validate_and_raise_valid(self):
        """Test validate_and_raise with valid query."""
        query = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT ?s WHERE { ?s rdf:type ?type . }
        """
        # Should not raise
        result = validate_and_raise(query)
        assert result.is_valid

    def test_validate_and_raise_invalid(self):
        """Test validate_and_raise with invalid query."""
        query = """
        SELECT ?s WHERE { ?s rdf:type ?type .
        """  # Missing closing brace
        with pytest.raises(QuerySyntaxError) as exc_info:
            validate_and_raise(query)
        assert "brace" in str(exc_info.value).lower()

    def test_validation_result_summary(self):
        """Test ValidationResult summary generation."""
        query = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT ?s ?p ?o
        WHERE {
            ?s ?p ?o .
        }
        """
        result = validate_query(query)
        summary = result.get_summary()
        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_validation_result_report(self):
        """Test ValidationResult report generation."""
        query = """
        SELECT ?s WHERE { ?s rdf:type ?type .
        """  # Invalid query
        result = validate_query(query)
        report = result.format_report()
        assert isinstance(report, str)
        assert len(report) > 0
        assert "ERROR" in report or "error" in report.lower()

    def test_language_tag_validation(self):
        """Test validation of language tags."""
        query = """
        SELECT ?s
        WHERE {
            ?s <http://example.org/name> "John"@en .
        }
        """
        result = validate_query(query)
        # Valid language tag should not produce errors
        assert result.is_valid

    def test_invalid_language_tag(self):
        """Test detection of invalid language tags."""
        query = """
        SELECT ?s
        WHERE {
            ?s <http://example.org/name> "John"@invalid123 .
        }
        """
        result = validate_query(query)
        # Should have warning about invalid language tag
        warnings = [w for w in result.warning_issues if "language tag" in w.message.lower()]
        assert len(warnings) > 0

    def test_validator_strict_mode(self):
        """Test validator in strict mode vs normal mode."""
        query = """
        SELECT *
        WHERE {
            ?s ?p ?o .
        }
        """

        # Normal mode - might not flag SELECT *
        result_normal = validate_query(query, strict=False)

        # Strict mode - should flag SELECT *
        result_strict = validate_query(query, strict=True)

        # Strict mode should have more issues
        assert len(result_strict.issues) >= len(result_normal.issues)

    def test_query_with_bind(self):
        """Test validation of query with BIND."""
        query = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT ?s ?label
        WHERE {
            ?s rdf:type ?type .
            BIND(str(?s) AS ?label)
        }
        """
        result = validate_query(query)
        assert result.is_valid

    def test_query_with_values(self):
        """Test validation of query with VALUES."""
        query = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT ?s ?type
        WHERE {
            ?s rdf:type ?type .
            VALUES ?type { <http://example.org/Type1> <http://example.org/Type2> }
        }
        """
        result = validate_query(query)
        assert result.is_valid

    def test_query_with_service(self):
        """Test validation of federated query with SERVICE."""
        query = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT ?s ?label
        WHERE {
            ?s rdf:type ?type .
            SERVICE <http://dbpedia.org/sparql> {
                ?s rdfs:label ?label .
            }
        }
        """
        result = validate_query(query)
        # SERVICE requires rdfs prefix
        assert not result.is_valid  # Should fail due to undeclared rdfs prefix

    def test_metadata_in_result(self):
        """Test that validation result includes metadata."""
        query = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT ?s WHERE { ?s rdf:type ?type . }
        """
        result = validate_query(query, strict=True)
        assert 'strict_mode' in result.metadata
        assert result.metadata['strict_mode'] is True
        assert 'total_issues' in result.metadata
        assert 'error_count' in result.metadata

    def test_issue_string_representation(self):
        """Test ValidationIssue string representation."""
        query = "SELECT ?s WHERE { ?s ?p ?o"  # Invalid
        result = validate_query(query)
        if result.issues:
            issue_str = str(result.issues[0])
            assert isinstance(issue_str, str)
            assert len(issue_str) > 0


class TestValidatorEdgeCases:
    """Test edge cases and corner cases."""

    def test_query_with_comments(self):
        """Test validation with comments."""
        query = """
        # This is a comment
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT ?s  # Inline comment
        WHERE {
            ?s rdf:type ?type .  # Another comment
        }
        """
        result = validate_query(query)
        assert result.is_valid

    def test_multiline_string_literal(self):
        """Test validation with multiline string literals."""
        query = '''
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT ?s
        WHERE {
            ?s <http://example.org/description> """This is a
            multiline
            string""" .
        }
        '''
        result = validate_query(query)
        assert result.is_valid

    def test_query_with_property_paths(self):
        """Test validation with property paths."""
        query = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT ?s ?o
        WHERE {
            ?s rdf:type/rdfs:subClassOf* ?o .
        }
        """
        result = validate_query(query)
        # Should fail due to undeclared rdfs prefix
        assert not result.is_valid

    def test_query_with_negation(self):
        """Test validation with negation (MINUS, NOT EXISTS)."""
        query = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX foaf: <http://xmlns.com/foaf/0.1/>
        SELECT ?person
        WHERE {
            ?person rdf:type foaf:Person .
            MINUS {
                ?person foaf:age ?age .
            }
        }
        """
        result = validate_query(query)
        assert result.is_valid

    def test_very_long_query(self):
        """Test validation with a very long query."""
        # Generate a long query
        prefixes = "\n".join([
            f"PREFIX p{i}: <http://example.org/prefix{i}#>"
            for i in range(50)
        ])

        query = f"""
        {prefixes}
        SELECT ?s
        WHERE {{
            ?s p1:prop ?o .
        }}
        """
        result = validate_query(query)
        # Should have warnings about unused prefixes
        assert len(result.warning_issues) > 0

    def test_query_with_blank_nodes(self):
        """Test validation with blank nodes."""
        query = """
        PREFIX foaf: <http://xmlns.com/foaf/0.1/>
        SELECT ?person
        WHERE {
            ?person foaf:knows _:friend .
            _:friend foaf:name "John" .
        }
        """
        result = validate_query(query)
        assert result.is_valid


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
