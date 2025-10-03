"""
VoID (Vocabulary of Interlinked Datasets) Parser and Extractor

This module provides classes for parsing and extracting VoID descriptions from SPARQL endpoints.
VoID is a vocabulary for expressing metadata about RDF datasets.

References:
    - VoID Specification: https://www.w3.org/TR/void/
    - VoID Namespace: http://rdfs.org/ns/void#
"""

from typing import Dict, List, Optional, Set, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
import logging
from urllib.parse import urlparse

from rdflib import Graph, Namespace, URIRef, Literal, BNode
from rdflib.namespace import RDF, RDFS, DCTERMS, FOAF, XSD
from SPARQLWrapper import SPARQLWrapper, JSON, XML, TURTLE

# VoID Namespace
VOID = Namespace("http://rdfs.org/ns/void#")

logger = logging.getLogger(__name__)


@dataclass
class VoIDDataset:
    """Represents a VoID Dataset with its metadata."""

    uri: str
    title: Optional[str] = None
    description: Optional[str] = None
    homepage: Optional[str] = None
    sparql_endpoint: Optional[str] = None

    # Statistics
    triples: Optional[int] = None
    entities: Optional[int] = None
    distinct_subjects: Optional[int] = None
    distinct_objects: Optional[int] = None
    properties: Optional[int] = None
    classes: Optional[int] = None

    # Vocabularies and classes
    vocabularies: Set[str] = field(default_factory=set)
    class_partitions: Dict[str, int] = field(default_factory=dict)
    property_partitions: Dict[str, int] = field(default_factory=dict)

    # Linksets
    linksets: List['VoIDLinkset'] = field(default_factory=list)

    # Technical details
    uri_space: Optional[str] = None
    uri_regex_pattern: Optional[str] = None
    example_resources: List[str] = field(default_factory=list)

    # Access information
    data_dumps: List[str] = field(default_factory=list)
    root_resource: Optional[str] = None

    # Provenance
    created: Optional[datetime] = None
    modified: Optional[datetime] = None
    creator: Optional[str] = None
    publisher: Optional[str] = None
    license: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert dataset to dictionary representation."""
        return {
            'uri': self.uri,
            'title': self.title,
            'description': self.description,
            'homepage': self.homepage,
            'sparql_endpoint': self.sparql_endpoint,
            'statistics': {
                'triples': self.triples,
                'entities': self.entities,
                'distinct_subjects': self.distinct_subjects,
                'distinct_objects': self.distinct_objects,
                'properties': self.properties,
                'classes': self.classes,
            },
            'vocabularies': list(self.vocabularies),
            'class_partitions': self.class_partitions,
            'property_partitions': self.property_partitions,
            'linksets': [ls.to_dict() for ls in self.linksets],
            'uri_space': self.uri_space,
            'uri_regex_pattern': self.uri_regex_pattern,
            'example_resources': self.example_resources,
            'data_dumps': self.data_dumps,
            'root_resource': self.root_resource,
            'provenance': {
                'created': self.created.isoformat() if self.created else None,
                'modified': self.modified.isoformat() if self.modified else None,
                'creator': self.creator,
                'publisher': self.publisher,
                'license': self.license,
            }
        }


@dataclass
class VoIDLinkset:
    """Represents a VoID Linkset connecting two datasets."""

    uri: str
    source_dataset: Optional[str] = None
    target_dataset: Optional[str] = None
    link_predicate: Optional[str] = None
    triples: Optional[int] = None
    subjects_target: Optional[str] = None
    objects_target: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert linkset to dictionary representation."""
        return {
            'uri': self.uri,
            'source_dataset': self.source_dataset,
            'target_dataset': self.target_dataset,
            'link_predicate': self.link_predicate,
            'triples': self.triples,
            'subjects_target': self.subjects_target,
            'objects_target': self.objects_target,
        }


class VoIDParser:
    """
    Parser for VoID descriptions from RDF graphs.

    This class parses VoID datasets and linksets from RDF graphs,
    extracting metadata, statistics, and relationships.
    """

    def __init__(self):
        """Initialize the VoID parser."""
        self.graph = Graph()
        self.graph.bind('void', VOID)
        self.graph.bind('dcterms', DCTERMS)
        self.graph.bind('foaf', FOAF)

    def parse(self, data: Union[str, Graph], format: str = 'turtle') -> List[VoIDDataset]:
        """
        Parse VoID descriptions from RDF data.

        Args:
            data: RDF data as string or rdflib Graph
            format: RDF serialization format (turtle, xml, n3, etc.)

        Returns:
            List of VoIDDataset objects
        """
        if isinstance(data, Graph):
            self.graph = data
        else:
            self.graph.parse(data=data, format=format)

        datasets = []

        # Find all void:Dataset instances
        for dataset_uri in self.graph.subjects(RDF.type, VOID.Dataset):
            dataset = self._parse_dataset(dataset_uri)
            if dataset:
                datasets.append(dataset)

        return datasets

    def parse_from_file(self, file_path: str, format: str = 'turtle') -> List[VoIDDataset]:
        """
        Parse VoID descriptions from a file.

        Args:
            file_path: Path to RDF file
            format: RDF serialization format

        Returns:
            List of VoIDDataset objects
        """
        self.graph.parse(file_path, format=format)
        return self.parse(self.graph)

    def _parse_dataset(self, dataset_uri: URIRef) -> Optional[VoIDDataset]:
        """Parse a single VoID dataset."""
        try:
            dataset = VoIDDataset(uri=str(dataset_uri))

            # Basic metadata
            dataset.title = self._get_literal(dataset_uri, DCTERMS.title)
            dataset.description = self._get_literal(dataset_uri, DCTERMS.description)
            dataset.homepage = self._get_uri(dataset_uri, FOAF.homepage)
            dataset.sparql_endpoint = self._get_uri(dataset_uri, VOID.sparqlEndpoint)

            # Statistics
            dataset.triples = self._get_int(dataset_uri, VOID.triples)
            dataset.entities = self._get_int(dataset_uri, VOID.entities)
            dataset.distinct_subjects = self._get_int(dataset_uri, VOID.distinctSubjects)
            dataset.distinct_objects = self._get_int(dataset_uri, VOID.distinctObjects)
            dataset.properties = self._get_int(dataset_uri, VOID.properties)
            dataset.classes = self._get_int(dataset_uri, VOID.classes)

            # Vocabularies
            for vocab in self.graph.objects(dataset_uri, VOID.vocabulary):
                dataset.vocabularies.add(str(vocab))

            # Class partitions
            for class_partition in self.graph.objects(dataset_uri, VOID.classPartition):
                class_uri = self._get_uri(class_partition, VOID['class'])
                if class_uri:
                    count = self._get_int(class_partition, VOID.entities)
                    if count is not None:
                        dataset.class_partitions[class_uri] = count

            # Property partitions
            for prop_partition in self.graph.objects(dataset_uri, VOID.propertyPartition):
                prop_uri = self._get_uri(prop_partition, VOID.property)
                if prop_uri:
                    count = self._get_int(prop_partition, VOID.triples)
                    if count is not None:
                        dataset.property_partitions[prop_uri] = count

            # URI space
            dataset.uri_space = self._get_literal(dataset_uri, VOID.uriSpace)
            dataset.uri_regex_pattern = self._get_literal(dataset_uri, VOID.uriRegexPattern)

            # Example resources
            for example in self.graph.objects(dataset_uri, VOID.exampleResource):
                dataset.example_resources.append(str(example))

            # Data dumps
            for dump in self.graph.objects(dataset_uri, VOID.dataDump):
                dataset.data_dumps.append(str(dump))

            # Root resource
            dataset.root_resource = self._get_uri(dataset_uri, VOID.rootResource)

            # Provenance
            created_str = self._get_literal(dataset_uri, DCTERMS.created)
            if created_str:
                dataset.created = self._parse_datetime(created_str)

            modified_str = self._get_literal(dataset_uri, DCTERMS.modified)
            if modified_str:
                dataset.modified = self._parse_datetime(modified_str)

            dataset.creator = self._get_literal(dataset_uri, DCTERMS.creator)
            dataset.publisher = self._get_literal(dataset_uri, DCTERMS.publisher)
            dataset.license = self._get_uri(dataset_uri, DCTERMS.license)

            # Linksets
            for linkset_uri in self.graph.objects(dataset_uri, VOID.subset):
                if (linkset_uri, RDF.type, VOID.Linkset) in self.graph:
                    linkset = self._parse_linkset(linkset_uri)
                    if linkset:
                        dataset.linksets.append(linkset)

            return dataset

        except Exception as e:
            logger.error(f"Error parsing dataset {dataset_uri}: {e}")
            return None

    def _parse_linkset(self, linkset_uri: URIRef) -> Optional[VoIDLinkset]:
        """Parse a single VoID linkset."""
        try:
            linkset = VoIDLinkset(uri=str(linkset_uri))

            linkset.source_dataset = self._get_uri(linkset_uri, VOID.subjectsTarget)
            linkset.target_dataset = self._get_uri(linkset_uri, VOID.objectsTarget)
            linkset.link_predicate = self._get_uri(linkset_uri, VOID.linkPredicate)
            linkset.triples = self._get_int(linkset_uri, VOID.triples)

            return linkset

        except Exception as e:
            logger.error(f"Error parsing linkset {linkset_uri}: {e}")
            return None

    def _get_literal(self, subject: URIRef, predicate: URIRef) -> Optional[str]:
        """Get a literal value from the graph."""
        for obj in self.graph.objects(subject, predicate):
            if isinstance(obj, Literal):
                return str(obj)
        return None

    def _get_uri(self, subject: URIRef, predicate: URIRef) -> Optional[str]:
        """Get a URI value from the graph."""
        for obj in self.graph.objects(subject, predicate):
            if isinstance(obj, (URIRef, BNode)):
                return str(obj)
        return None

    def _get_int(self, subject: URIRef, predicate: URIRef) -> Optional[int]:
        """Get an integer value from the graph."""
        value = self._get_literal(subject, predicate)
        if value:
            try:
                return int(value)
            except ValueError:
                return None
        return None

    def _parse_datetime(self, date_str: str) -> Optional[datetime]:
        """Parse datetime string."""
        try:
            # Try ISO format first
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except:
            try:
                # Try common date format
                return datetime.strptime(date_str, '%Y-%m-%d')
            except:
                return None


class VoIDExtractor:
    """
    Extractor for VoID data from SPARQL endpoints.

    This class queries SPARQL endpoints for existing VoID descriptions
    or generates VoID metadata when missing.
    """

    # Query templates
    VOID_DATASET_QUERY = """
    PREFIX void: <http://rdfs.org/ns/void#>
    PREFIX dcterms: <http://purl.org/dc/terms/>
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>

    SELECT ?dataset ?property ?value WHERE {
        ?dataset a void:Dataset .
        ?dataset ?property ?value
    }
    """

    VOID_LINKSET_QUERY = """
    PREFIX void: <http://rdfs.org/ns/void#>

    SELECT ?linkset ?property ?value WHERE {
        ?linkset a void:Linkset .
        ?linkset ?property ?value
    }
    """

    STATISTICS_QUERY = """
    PREFIX void: <http://rdfs.org/ns/void#>

    SELECT
        (COUNT(*) AS ?triples)
        (COUNT(DISTINCT ?s) AS ?subjects)
        (COUNT(DISTINCT ?o) AS ?objects)
    WHERE {
        ?s ?p ?o
    }
    LIMIT 1
    """

    PROPERTY_COUNT_QUERY = """
    PREFIX void: <http://rdfs.org/ns/void#>

    SELECT (COUNT(DISTINCT ?p) AS ?properties) WHERE {
        ?s ?p ?o
    }
    """

    CLASS_COUNT_QUERY = """
    PREFIX void: <http://rdfs.org/ns/void#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

    SELECT (COUNT(DISTINCT ?class) AS ?classes) WHERE {
        ?s rdf:type ?class
    }
    """

    CLASS_PARTITION_QUERY = """
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

    SELECT ?class (COUNT(?s) AS ?count) WHERE {
        ?s rdf:type ?class
    }
    GROUP BY ?class
    ORDER BY DESC(?count)
    LIMIT 100
    """

    PROPERTY_PARTITION_QUERY = """
    SELECT ?property (COUNT(*) AS ?count) WHERE {
        ?s ?property ?o
    }
    GROUP BY ?property
    ORDER BY DESC(?count)
    LIMIT 100
    """

    VOCABULARY_QUERY = """
    SELECT DISTINCT ?namespace WHERE {
        {
            ?s ?p ?o .
            BIND(REPLACE(STR(?p), "(.*[/#])[^/#]*$", "$1") AS ?namespace)
        }
        UNION
        {
            ?s a ?class .
            BIND(REPLACE(STR(?class), "(.*[/#])[^/#]*$", "$1") AS ?namespace)
        }
    }
    ORDER BY ?namespace
    LIMIT 100
    """

    def __init__(self, endpoint_url: str, timeout: int = 30):
        """
        Initialize the VoID extractor.

        Args:
            endpoint_url: SPARQL endpoint URL
            timeout: Query timeout in seconds
        """
        self.endpoint_url = endpoint_url
        self.timeout = timeout
        self.sparql = SPARQLWrapper(endpoint_url)
        self.sparql.setTimeout(timeout)
        self.parser = VoIDParser()

    def extract(self, generate_if_missing: bool = True) -> List[VoIDDataset]:
        """
        Extract VoID descriptions from the endpoint.

        Args:
            generate_if_missing: Generate VoID if not found at endpoint

        Returns:
            List of VoIDDataset objects
        """
        # First, try to query for existing VoID descriptions
        datasets = self._query_void_datasets()

        if not datasets and generate_if_missing:
            logger.info("No VoID descriptions found. Generating from statistics...")
            datasets = [self._generate_void_dataset()]

        return datasets

    def _query_void_datasets(self) -> List[VoIDDataset]:
        """Query endpoint for existing VoID datasets."""
        try:
            self.sparql.setQuery(self.VOID_DATASET_QUERY)
            self.sparql.setReturnFormat(TURTLE)
            results = self.sparql.query().convert()

            # Parse results as RDF graph
            if results:
                datasets = self.parser.parse(results, format='turtle')
                logger.info(f"Found {len(datasets)} VoID dataset(s)")
                return datasets

        except Exception as e:
            logger.warning(f"Failed to query VoID datasets: {e}")

        return []

    def _generate_void_dataset(self) -> VoIDDataset:
        """Generate VoID dataset from endpoint statistics."""
        dataset = VoIDDataset(
            uri=self.endpoint_url,
            sparql_endpoint=self.endpoint_url,
            title=f"Dataset at {self.endpoint_url}",
            created=datetime.now()
        )

        # Gather statistics
        try:
            # Basic triple statistics
            stats = self._query_statistics()
            if stats:
                dataset.triples = stats.get('triples')
                dataset.distinct_subjects = stats.get('subjects')
                dataset.distinct_objects = stats.get('objects')

            # Property count
            dataset.properties = self._query_property_count()

            # Class count
            dataset.classes = self._query_class_count()

            # Class partitions
            dataset.class_partitions = self._query_class_partitions()

            # Property partitions
            dataset.property_partitions = self._query_property_partitions()

            # Vocabularies
            dataset.vocabularies = self._query_vocabularies()

            logger.info(f"Generated VoID dataset with {dataset.triples} triples")

        except Exception as e:
            logger.error(f"Error generating VoID dataset: {e}")

        return dataset

    def _query_statistics(self) -> Optional[Dict[str, int]]:
        """Query basic statistics."""
        try:
            self.sparql.setQuery(self.STATISTICS_QUERY)
            self.sparql.setReturnFormat(JSON)
            results = self.sparql.query().convert()

            if results and 'results' in results and 'bindings' in results['results']:
                bindings = results['results']['bindings']
                if bindings:
                    row = bindings[0]
                    return {
                        'triples': int(row.get('triples', {}).get('value', 0)),
                        'subjects': int(row.get('subjects', {}).get('value', 0)),
                        'objects': int(row.get('objects', {}).get('value', 0)),
                    }
        except Exception as e:
            logger.warning(f"Failed to query statistics: {e}")

        return None

    def _query_property_count(self) -> Optional[int]:
        """Query property count."""
        try:
            self.sparql.setQuery(self.PROPERTY_COUNT_QUERY)
            self.sparql.setReturnFormat(JSON)
            results = self.sparql.query().convert()

            if results and 'results' in results and 'bindings' in results['results']:
                bindings = results['results']['bindings']
                if bindings:
                    return int(bindings[0].get('properties', {}).get('value', 0))
        except Exception as e:
            logger.warning(f"Failed to query property count: {e}")

        return None

    def _query_class_count(self) -> Optional[int]:
        """Query class count."""
        try:
            self.sparql.setQuery(self.CLASS_COUNT_QUERY)
            self.sparql.setReturnFormat(JSON)
            results = self.sparql.query().convert()

            if results and 'results' in results and 'bindings' in results['results']:
                bindings = results['results']['bindings']
                if bindings:
                    return int(bindings[0].get('classes', {}).get('value', 0))
        except Exception as e:
            logger.warning(f"Failed to query class count: {e}")

        return None

    def _query_class_partitions(self) -> Dict[str, int]:
        """Query class partitions."""
        partitions = {}
        try:
            self.sparql.setQuery(self.CLASS_PARTITION_QUERY)
            self.sparql.setReturnFormat(JSON)
            results = self.sparql.query().convert()

            if results and 'results' in results and 'bindings' in results['results']:
                for row in results['results']['bindings']:
                    class_uri = row.get('class', {}).get('value')
                    count = row.get('count', {}).get('value')
                    if class_uri and count:
                        partitions[class_uri] = int(count)
        except Exception as e:
            logger.warning(f"Failed to query class partitions: {e}")

        return partitions

    def _query_property_partitions(self) -> Dict[str, int]:
        """Query property partitions."""
        partitions = {}
        try:
            self.sparql.setQuery(self.PROPERTY_PARTITION_QUERY)
            self.sparql.setReturnFormat(JSON)
            results = self.sparql.query().convert()

            if results and 'results' in results and 'bindings' in results['results']:
                for row in results['results']['bindings']:
                    prop_uri = row.get('property', {}).get('value')
                    count = row.get('count', {}).get('value')
                    if prop_uri and count:
                        partitions[prop_uri] = int(count)
        except Exception as e:
            logger.warning(f"Failed to query property partitions: {e}")

        return partitions

    def _query_vocabularies(self) -> Set[str]:
        """Query used vocabularies."""
        vocabularies = set()
        try:
            self.sparql.setQuery(self.VOCABULARY_QUERY)
            self.sparql.setReturnFormat(JSON)
            results = self.sparql.query().convert()

            if results and 'results' in results and 'bindings' in results['results']:
                for row in results['results']['bindings']:
                    namespace = row.get('namespace', {}).get('value')
                    if namespace:
                        vocabularies.add(namespace)
        except Exception as e:
            logger.warning(f"Failed to query vocabularies: {e}")

        return vocabularies

    def validate_consistency(self, dataset: VoIDDataset) -> Dict[str, Any]:
        """
        Validate consistency of VoID description with actual endpoint data.

        Args:
            dataset: VoID dataset to validate

        Returns:
            Dictionary with validation results
        """
        validation = {
            'valid': True,
            'warnings': [],
            'errors': []
        }

        # Query actual statistics
        actual_stats = self._query_statistics()

        if actual_stats:
            # Check triple count
            if dataset.triples and abs(dataset.triples - actual_stats['triples']) > 0:
                validation['warnings'].append(
                    f"Triple count mismatch: VoID={dataset.triples}, Actual={actual_stats['triples']}"
                )

            # Check subject count
            if dataset.distinct_subjects and abs(dataset.distinct_subjects - actual_stats['subjects']) > 0:
                validation['warnings'].append(
                    f"Subject count mismatch: VoID={dataset.distinct_subjects}, Actual={actual_stats['subjects']}"
                )

        # Check SPARQL endpoint accessibility
        if dataset.sparql_endpoint:
            try:
                test_sparql = SPARQLWrapper(dataset.sparql_endpoint)
                test_sparql.setTimeout(5)
                test_sparql.setQuery("ASK { ?s ?p ?o }")
                test_sparql.setReturnFormat(JSON)
                test_sparql.query().convert()
            except Exception as e:
                validation['errors'].append(f"SPARQL endpoint not accessible: {e}")
                validation['valid'] = False

        return validation

    def export_to_rdf(self, datasets: List[VoIDDataset], format: str = 'turtle') -> str:
        """
        Export VoID datasets to RDF serialization.

        Args:
            datasets: List of VoID datasets
            format: RDF serialization format

        Returns:
            RDF serialization as string
        """
        graph = Graph()
        graph.bind('void', VOID)
        graph.bind('dcterms', DCTERMS)
        graph.bind('foaf', FOAF)

        for dataset in datasets:
            dataset_uri = URIRef(dataset.uri)
            graph.add((dataset_uri, RDF.type, VOID.Dataset))

            # Basic metadata
            if dataset.title:
                graph.add((dataset_uri, DCTERMS.title, Literal(dataset.title)))
            if dataset.description:
                graph.add((dataset_uri, DCTERMS.description, Literal(dataset.description)))
            if dataset.homepage:
                graph.add((dataset_uri, FOAF.homepage, URIRef(dataset.homepage)))
            if dataset.sparql_endpoint:
                graph.add((dataset_uri, VOID.sparqlEndpoint, URIRef(dataset.sparql_endpoint)))

            # Statistics
            if dataset.triples:
                graph.add((dataset_uri, VOID.triples, Literal(dataset.triples)))
            if dataset.entities:
                graph.add((dataset_uri, VOID.entities, Literal(dataset.entities)))
            if dataset.distinct_subjects:
                graph.add((dataset_uri, VOID.distinctSubjects, Literal(dataset.distinct_subjects)))
            if dataset.distinct_objects:
                graph.add((dataset_uri, VOID.distinctObjects, Literal(dataset.distinct_objects)))
            if dataset.properties:
                graph.add((dataset_uri, VOID.properties, Literal(dataset.properties)))
            if dataset.classes:
                graph.add((dataset_uri, VOID.classes, Literal(dataset.classes)))

            # Vocabularies
            for vocab in dataset.vocabularies:
                graph.add((dataset_uri, VOID.vocabulary, URIRef(vocab)))

            # Provenance
            if dataset.creator:
                graph.add((dataset_uri, DCTERMS.creator, Literal(dataset.creator)))
            if dataset.publisher:
                graph.add((dataset_uri, DCTERMS.publisher, Literal(dataset.publisher)))
            if dataset.license:
                graph.add((dataset_uri, DCTERMS.license, URIRef(dataset.license)))
            if dataset.created:
                graph.add((dataset_uri, DCTERMS.created, Literal(dataset.created.isoformat(), datatype=XSD.dateTime)))

        return graph.serialize(format=format)
