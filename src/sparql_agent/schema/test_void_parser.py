"""
Unit tests for VoID Parser and Extractor

Run with: python -m pytest test_void_parser.py
"""

import pytest
from datetime import datetime
from void_parser import (
    VoIDParser,
    VoIDExtractor,
    VoIDDataset,
    VoIDLinkset,
    VOID
)


class TestVoIDParser:
    """Tests for VoIDParser class."""

    def test_parse_basic_dataset(self):
        """Test parsing a basic VoID dataset."""
        void_data = """
        @prefix void: <http://rdfs.org/ns/void#> .
        @prefix dcterms: <http://purl.org/dc/terms/> .

        <http://example.org/dataset> a void:Dataset ;
            dcterms:title "Test Dataset" ;
            dcterms:description "A test dataset" ;
            void:triples 1000 ;
            void:entities 500 .
        """

        parser = VoIDParser()
        datasets = parser.parse(void_data, format='turtle')

        assert len(datasets) == 1
        dataset = datasets[0]
        assert dataset.uri == "http://example.org/dataset"
        assert dataset.title == "Test Dataset"
        assert dataset.description == "A test dataset"
        assert dataset.triples == 1000
        assert dataset.entities == 500

    def test_parse_dataset_with_statistics(self):
        """Test parsing dataset with full statistics."""
        void_data = """
        @prefix void: <http://rdfs.org/ns/void#> .

        <http://example.org/dataset> a void:Dataset ;
            void:triples 10000 ;
            void:entities 5000 ;
            void:distinctSubjects 4000 ;
            void:distinctObjects 6000 ;
            void:properties 50 ;
            void:classes 25 .
        """

        parser = VoIDParser()
        datasets = parser.parse(void_data, format='turtle')

        assert len(datasets) == 1
        dataset = datasets[0]
        assert dataset.triples == 10000
        assert dataset.entities == 5000
        assert dataset.distinct_subjects == 4000
        assert dataset.distinct_objects == 6000
        assert dataset.properties == 50
        assert dataset.classes == 25

    def test_parse_vocabularies(self):
        """Test parsing vocabulary usage."""
        void_data = """
        @prefix void: <http://rdfs.org/ns/void#> .

        <http://example.org/dataset> a void:Dataset ;
            void:vocabulary <http://xmlns.com/foaf/0.1/> ;
            void:vocabulary <http://purl.org/dc/terms/> ;
            void:vocabulary <http://www.w3.org/2004/02/skos/core#> .
        """

        parser = VoIDParser()
        datasets = parser.parse(void_data, format='turtle')

        assert len(datasets) == 1
        dataset = datasets[0]
        assert len(dataset.vocabularies) == 3
        assert "http://xmlns.com/foaf/0.1/" in dataset.vocabularies
        assert "http://purl.org/dc/terms/" in dataset.vocabularies
        assert "http://www.w3.org/2004/02/skos/core#" in dataset.vocabularies

    def test_parse_linkset(self):
        """Test parsing VoID linkset."""
        void_data = """
        @prefix void: <http://rdfs.org/ns/void#> .
        @prefix owl: <http://www.w3.org/2002/07/owl#> .

        <http://example.org/dataset1> a void:Dataset ;
            void:subset <http://example.org/linkset1> .

        <http://example.org/linkset1> a void:Linkset ;
            void:subjectsTarget <http://example.org/dataset1> ;
            void:objectsTarget <http://example.org/dataset2> ;
            void:linkPredicate owl:sameAs ;
            void:triples 5000 .
        """

        parser = VoIDParser()
        datasets = parser.parse(void_data, format='turtle')

        assert len(datasets) == 1
        dataset = datasets[0]
        assert len(dataset.linksets) == 1

        linkset = dataset.linksets[0]
        assert linkset.uri == "http://example.org/linkset1"
        assert linkset.source_dataset == "http://example.org/dataset1"
        assert linkset.target_dataset == "http://example.org/dataset2"
        assert linkset.link_predicate == "http://www.w3.org/2002/07/owl#sameAs"
        assert linkset.triples == 5000

    def test_parse_provenance(self):
        """Test parsing provenance information."""
        void_data = """
        @prefix void: <http://rdfs.org/ns/void#> .
        @prefix dcterms: <http://purl.org/dc/terms/> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

        <http://example.org/dataset> a void:Dataset ;
            dcterms:created "2025-01-01"^^xsd:date ;
            dcterms:creator "John Doe" ;
            dcterms:publisher "Example Org" ;
            dcterms:license <http://creativecommons.org/licenses/by/4.0/> .
        """

        parser = VoIDParser()
        datasets = parser.parse(void_data, format='turtle')

        assert len(datasets) == 1
        dataset = datasets[0]
        assert dataset.created is not None
        assert dataset.creator == "John Doe"
        assert dataset.publisher == "Example Org"
        assert dataset.license == "http://creativecommons.org/licenses/by/4.0/"

    def test_parse_multiple_datasets(self):
        """Test parsing multiple datasets."""
        void_data = """
        @prefix void: <http://rdfs.org/ns/void#> .
        @prefix dcterms: <http://purl.org/dc/terms/> .

        <http://example.org/dataset1> a void:Dataset ;
            dcterms:title "Dataset 1" ;
            void:triples 1000 .

        <http://example.org/dataset2> a void:Dataset ;
            dcterms:title "Dataset 2" ;
            void:triples 2000 .
        """

        parser = VoIDParser()
        datasets = parser.parse(void_data, format='turtle')

        assert len(datasets) == 2
        titles = {d.title for d in datasets}
        assert "Dataset 1" in titles
        assert "Dataset 2" in titles


class TestVoIDDataset:
    """Tests for VoIDDataset class."""

    def test_dataset_creation(self):
        """Test creating a VoIDDataset."""
        dataset = VoIDDataset(
            uri="http://example.org/dataset",
            title="Test Dataset",
            triples=1000
        )

        assert dataset.uri == "http://example.org/dataset"
        assert dataset.title == "Test Dataset"
        assert dataset.triples == 1000
        assert len(dataset.vocabularies) == 0
        assert len(dataset.linksets) == 0

    def test_dataset_to_dict(self):
        """Test converting dataset to dictionary."""
        dataset = VoIDDataset(
            uri="http://example.org/dataset",
            title="Test Dataset",
            triples=1000,
            entities=500
        )
        dataset.vocabularies.add("http://xmlns.com/foaf/0.1/")

        result = dataset.to_dict()

        assert isinstance(result, dict)
        assert result['uri'] == "http://example.org/dataset"
        assert result['title'] == "Test Dataset"
        assert result['statistics']['triples'] == 1000
        assert result['statistics']['entities'] == 500
        assert "http://xmlns.com/foaf/0.1/" in result['vocabularies']


class TestVoIDLinkset:
    """Tests for VoIDLinkset class."""

    def test_linkset_creation(self):
        """Test creating a VoIDLinkset."""
        linkset = VoIDLinkset(
            uri="http://example.org/linkset",
            source_dataset="http://example.org/dataset1",
            target_dataset="http://example.org/dataset2",
            link_predicate="http://www.w3.org/2002/07/owl#sameAs",
            triples=5000
        )

        assert linkset.uri == "http://example.org/linkset"
        assert linkset.source_dataset == "http://example.org/dataset1"
        assert linkset.target_dataset == "http://example.org/dataset2"
        assert linkset.link_predicate == "http://www.w3.org/2002/07/owl#sameAs"
        assert linkset.triples == 5000

    def test_linkset_to_dict(self):
        """Test converting linkset to dictionary."""
        linkset = VoIDLinkset(
            uri="http://example.org/linkset",
            triples=1000
        )

        result = linkset.to_dict()

        assert isinstance(result, dict)
        assert result['uri'] == "http://example.org/linkset"
        assert result['triples'] == 1000


class TestVoIDExtractor:
    """Tests for VoIDExtractor class."""

    def test_extractor_initialization(self):
        """Test initializing VoIDExtractor."""
        extractor = VoIDExtractor("http://example.org/sparql", timeout=30)

        assert extractor.endpoint_url == "http://example.org/sparql"
        assert extractor.timeout == 30
        assert extractor.parser is not None

    def test_export_to_rdf_turtle(self):
        """Test exporting VoID to Turtle format."""
        dataset = VoIDDataset(
            uri="http://example.org/dataset",
            title="Test Dataset",
            triples=1000
        )
        dataset.vocabularies.add("http://xmlns.com/foaf/0.1/")

        extractor = VoIDExtractor("http://example.org/sparql", timeout=30)
        output = extractor.export_to_rdf([dataset], format='turtle')

        assert isinstance(output, str)
        assert "void:Dataset" in output
        assert "Test Dataset" in output
        assert "1000" in output

    def test_export_to_rdf_xml(self):
        """Test exporting VoID to RDF/XML format."""
        dataset = VoIDDataset(
            uri="http://example.org/dataset",
            title="Test Dataset"
        )

        extractor = VoIDExtractor("http://example.org/sparql", timeout=30)
        output = extractor.export_to_rdf([dataset], format='xml')

        assert isinstance(output, str)
        assert "rdf:RDF" in output or "RDF" in output

    def test_export_multiple_datasets(self):
        """Test exporting multiple datasets."""
        dataset1 = VoIDDataset(
            uri="http://example.org/dataset1",
            title="Dataset 1"
        )
        dataset2 = VoIDDataset(
            uri="http://example.org/dataset2",
            title="Dataset 2"
        )

        extractor = VoIDExtractor("http://example.org/sparql", timeout=30)
        output = extractor.export_to_rdf([dataset1, dataset2], format='turtle')

        assert isinstance(output, str)
        assert "Dataset 1" in output
        assert "Dataset 2" in output


def test_void_namespace():
    """Test VOID namespace is correctly defined."""
    assert VOID is not None
    assert str(VOID) == "http://rdfs.org/ns/void#"
    assert str(VOID.Dataset) == "http://rdfs.org/ns/void#Dataset"
    assert str(VOID.Linkset) == "http://rdfs.org/ns/void#Linkset"
    assert str(VOID.triples) == "http://rdfs.org/ns/void#triples"
    assert str(VOID.vocabulary) == "http://rdfs.org/ns/void#vocabulary"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
