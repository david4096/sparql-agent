"""
Tests for OWL ontology parsing and OLS integration.

This module contains unit tests for the OLSClient and OWLParser classes.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from sparql_agent.core.exceptions import OntologyLoadError, OntologyParseError
from sparql_agent.ontology import (
    COMMON_ONTOLOGIES,
    OLSClient,
    OWLParser,
    get_ontology_config,
    list_common_ontologies,
)


class TestOLSClient:
    """Tests for the OLSClient class."""

    def test_client_initialization(self):
        """Test OLS client initialization."""
        client = OLSClient()
        assert client.base_url == "https://www.ebi.ac.uk/ols4/api/"

    def test_custom_base_url(self):
        """Test client with custom base URL."""
        custom_url = "https://custom.ols.org/api"
        client = OLSClient(base_url=custom_url)
        assert client.base_url == "https://custom.ols.org/api/"

    @patch('requests.Session.get')
    def test_search(self, mock_get):
        """Test term search."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": {
                "docs": [
                    {
                        "obo_id": "GO:0008150",
                        "iri": "http://purl.obolibrary.org/obo/GO_0008150",
                        "label": "biological_process",
                        "description": ["Any process specifically pertinent to biology"],
                        "ontology_name": "go",
                        "synonym": ["biological process"],
                    }
                ]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = OLSClient()
        results = client.search("biological process")

        assert len(results) == 1
        assert results[0]["id"] == "GO:0008150"
        assert results[0]["label"] == "biological_process"
        assert results[0]["ontology"] == "go"

    @patch('requests.Session.get')
    def test_get_ontology(self, mock_get):
        """Test getting ontology information."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "ontologyId": "go",
            "config": {
                "title": "Gene Ontology",
                "description": "The Gene Ontology",
                "version": "2024-01-01",
                "namespace": "http://purl.obolibrary.org/obo/go",
            },
            "numberOfTerms": 50000,
            "numberOfProperties": 100,
            "status": "LOADED",
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = OLSClient()
        info = client.get_ontology("go")

        assert info["id"] == "go"
        assert info["title"] == "Gene Ontology"
        assert info["num_terms"] == 50000

    @patch('requests.Session.get')
    def test_list_ontologies(self, mock_get):
        """Test listing available ontologies."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "_embedded": {
                "ontologies": [
                    {
                        "ontologyId": "go",
                        "config": {
                            "title": "Gene Ontology",
                            "description": "GO Description",
                        },
                        "numberOfTerms": 50000,
                    },
                    {
                        "ontologyId": "chebi",
                        "config": {
                            "title": "ChEBI",
                            "description": "Chemical Entities",
                        },
                        "numberOfTerms": 100000,
                    },
                ]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = OLSClient()
        ontologies = client.list_ontologies()

        assert len(ontologies) == 2
        assert ontologies[0]["id"] == "go"
        assert ontologies[1]["id"] == "chebi"

    def test_repr(self):
        """Test string representation."""
        client = OLSClient()
        assert "OLSClient" in repr(client)
        assert "https://www.ebi.ac.uk/ols4/api/" in repr(client)


class TestCommonOntologies:
    """Tests for common ontology configurations."""

    def test_common_ontologies_present(self):
        """Test that common ontologies are defined."""
        assert "GO" in COMMON_ONTOLOGIES
        assert "CHEBI" in COMMON_ONTOLOGIES
        assert "PRO" in COMMON_ONTOLOGIES
        assert "HPO" in COMMON_ONTOLOGIES
        assert "MONDO" in COMMON_ONTOLOGIES

    def test_get_ontology_config(self):
        """Test getting ontology configuration."""
        go_config = get_ontology_config("GO")
        assert go_config is not None
        assert go_config["id"] == "go"
        assert go_config["name"] == "Gene Ontology"
        assert "url" in go_config
        assert "namespace" in go_config

    def test_get_ontology_config_case_insensitive(self):
        """Test that ontology lookup is case-insensitive."""
        go_config = get_ontology_config("go")
        assert go_config is not None
        assert go_config["id"] == "go"

    def test_get_ontology_config_not_found(self):
        """Test handling of non-existent ontology."""
        config = get_ontology_config("NONEXISTENT")
        assert config is None

    def test_list_common_ontologies(self):
        """Test listing all common ontologies."""
        ontologies = list_common_ontologies()
        assert len(ontologies) > 0
        assert all("id" in o for o in ontologies)
        assert all("name" in o for o in ontologies)
        assert all("url" in o for o in ontologies)

    def test_ontology_fields(self):
        """Test that all ontologies have required fields."""
        for onto in list_common_ontologies():
            assert "id" in onto
            assert "name" in onto
            assert "description" in onto
            assert "url" in onto
            assert "homepage" in onto
            assert "namespace" in onto


class TestOWLParser:
    """Tests for the OWLParser class."""

    def test_parser_initialization(self):
        """Test parser initialization."""
        try:
            parser = OWLParser()
            assert parser is not None
            assert parser.enable_reasoning is False
        except ImportError:
            pytest.skip("owlready2 not available")

    def test_parser_with_reasoning(self):
        """Test parser with reasoning enabled."""
        try:
            parser = OWLParser(enable_reasoning=True)
            assert parser.enable_reasoning is True
        except ImportError:
            pytest.skip("owlready2 not available")

    def test_load_nonexistent_file(self):
        """Test loading non-existent file raises error."""
        try:
            parser = OWLParser()
            with pytest.raises(OntologyLoadError):
                parser.load_ontology("/nonexistent/path/file.owl")
        except ImportError:
            pytest.skip("owlready2 not available")

    def test_parse_without_loading(self):
        """Test parsing without loading raises error."""
        try:
            parser = OWLParser()
            with pytest.raises(OntologyParseError):
                parser.search_classes("test")
        except ImportError:
            pytest.skip("owlready2 not available")

    def test_context_manager(self):
        """Test parser as context manager."""
        try:
            with OWLParser() as parser:
                assert parser is not None
        except ImportError:
            pytest.skip("owlready2 not available")

    def test_repr(self):
        """Test string representation."""
        try:
            parser = OWLParser()
            assert "OWLParser" in repr(parser)
        except ImportError:
            pytest.skip("owlready2 not available")


class TestIntegration:
    """Integration tests for OLS and OWL parsing."""

    @pytest.mark.skip(reason="Requires network and downloads large files")
    def test_download_and_parse_workflow(self):
        """Test complete workflow: download from OLS and parse with owlready2."""
        try:
            # Download a small ontology
            client = OLSClient()
            owl_file = client.download_ontology("pato")

            assert owl_file.exists()
            assert owl_file.stat().st_size > 0

            # Parse it
            parser = OWLParser()
            ontology_info = parser.load_ontology(owl_file)

            assert ontology_info is not None
            assert ontology_info.uri is not None
            assert len(ontology_info.classes) > 0

            parser.close()

            # Clean up
            owl_file.unlink()

        except ImportError:
            pytest.skip("owlready2 not available")
        except Exception as e:
            pytest.skip(f"Network or download issue: {e}")


def test_module_imports():
    """Test that all module exports are available."""
    from sparql_agent.ontology import (
        COMMON_ONTOLOGIES,
        OLSClient,
        OWLParser,
        get_ontology_config,
        list_common_ontologies,
    )

    assert OLSClient is not None
    assert OWLParser is not None
    assert COMMON_ONTOLOGIES is not None
    assert get_ontology_config is not None
    assert list_common_ontologies is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
