"""
OWL Ontology Parser.

This module provides functionality for parsing and working with OWL ontologies
using owlready2 and rdflib.
"""

from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse
from pathlib import Path

import owlready2 as owl2
from rdflib import Graph, Namespace, RDF, RDFS, OWL, URIRef
from rdflib.namespace import SKOS


class OWLParser:
    """
    Parser for OWL ontologies with reasoning support.
    
    This class provides high-level methods for loading, parsing, and querying
    OWL ontologies using owlready2 for reasoning and rdflib for RDF processing.
    """

    def __init__(
        self, 
        source: Optional[str] = None,
        enable_reasoning: bool = False,
        reasoner: str = "pellet"
    ):
        """
        Initialize the OWL parser.
        
        Args:
            source: Path or URL to ontology file
            enable_reasoning: Enable OWL reasoning
            reasoner: Reasoner to use ("pellet" or "hermit")
        """
        self.source = source
        self.enable_reasoning = enable_reasoning
        self.reasoner = reasoner
        
        # Initialize storage
        self.world = owl2.World()
        self.ontology: Optional[owl2.Ontology] = None
        self.graph: Optional[Graph] = None
        
        # Namespace cache
        self.namespaces: Dict[str, Namespace] = {}
        
        if source:
            self.load(source)

    def load(self, source: str, format: Optional[str] = None) -> None:
        """
        Load an ontology from a file or URL.
        
        Args:
            source: Path or URL to ontology file
            format: Optional format specification (e.g., 'rdfxml', 'turtle')
        """
        self.source = source
        
        # Load with owlready2 for reasoning
        try:
            if source.startswith("http://") or source.startswith("https://"):
                self.ontology = self.world.get_ontology(source).load()
            else:
                path = Path(source).resolve()
                self.ontology = self.world.get_ontology(f"file://{path}").load()
        except Exception as e:
            raise ValueError(f"Failed to load ontology with owlready2: {e}")
        
        # Also load with rdflib for RDF processing
        self.graph = Graph()
        try:
            if format:
                self.graph.parse(source, format=format)
            else:
                self.graph.parse(source)
        except Exception as e:
            raise ValueError(f"Failed to load ontology with rdflib: {e}")
        
        # Extract namespaces
        self._extract_namespaces()
        
        # Run reasoner if enabled
        if self.enable_reasoning:
            self.run_reasoner()

    def run_reasoner(self) -> None:
        """Run the OWL reasoner to infer additional facts."""
        if not self.ontology:
            raise ValueError("No ontology loaded")
        
        try:
            if self.reasoner == "pellet":
                owl2.sync_reasoner_pellet(
                    self.world, 
                    infer_property_values=True,
                    infer_data_property_values=True
                )
            elif self.reasoner == "hermit":
                owl2.sync_reasoner_hermit(
                    self.world,
                    infer_property_values=True
                )
            else:
                raise ValueError(f"Unknown reasoner: {self.reasoner}")
        except Exception as e:
            raise ValueError(f"Reasoner failed: {e}")

    def _extract_namespaces(self) -> None:
        """Extract namespaces from the loaded graph."""
        if not self.graph:
            return
        
        for prefix, namespace in self.graph.namespaces():
            self.namespaces[prefix] = namespace

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get ontology metadata.
        
        Returns:
            Dictionary containing ontology metadata
        """
        if not self.ontology:
            raise ValueError("No ontology loaded")
        
        metadata = {
            "iri": self.ontology.base_iri,
            "imported_ontologies": [o.base_iri for o in self.ontology.imported_ontologies],
        }
        
        # Extract metadata from RDF graph
        if self.graph:
            onto_uri = URIRef(self.ontology.base_iri)
            
            # Get labels
            labels = list(self.graph.objects(onto_uri, RDFS.label))
            if labels:
                metadata["label"] = str(labels[0])
            
            # Get comments/descriptions
            comments = list(self.graph.objects(onto_uri, RDFS.comment))
            if comments:
                metadata["description"] = str(comments[0])
            
            # Get version
            versions = list(self.graph.objects(onto_uri, OWL.versionInfo))
            if versions:
                metadata["version"] = str(versions[0])
        
        return metadata

    def get_classes(self, include_imported: bool = True) -> List[Dict[str, Any]]:
        """
        Get all classes from the ontology.
        
        Args:
            include_imported: Include classes from imported ontologies
            
        Returns:
            List of class dictionaries with metadata
        """
        if not self.ontology:
            raise ValueError("No ontology loaded")
        
        classes = []
        
        for cls in self.ontology.classes():
            if not include_imported and cls.namespace != self.ontology:
                continue
            
            class_info = self._format_class(cls)
            classes.append(class_info)
        
        return classes

    def get_properties(self, include_imported: bool = True) -> List[Dict[str, Any]]:
        """
        Get all properties from the ontology.
        
        Args:
            include_imported: Include properties from imported ontologies
            
        Returns:
            List of property dictionaries with metadata
        """
        if not self.ontology:
            raise ValueError("No ontology loaded")
        
        properties = []
        
        # Object properties
        for prop in self.ontology.object_properties():
            if not include_imported and prop.namespace != self.ontology:
                continue
            properties.append(self._format_property(prop, "object"))
        
        # Data properties
        for prop in self.ontology.data_properties():
            if not include_imported and prop.namespace != self.ontology:
                continue
            properties.append(self._format_property(prop, "data"))
        
        # Annotation properties
        for prop in self.ontology.annotation_properties():
            if not include_imported and prop.namespace != self.ontology:
                continue
            properties.append(self._format_property(prop, "annotation"))
        
        return properties

    def get_class(self, uri: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific class by URI.
        
        Args:
            uri: URI of the class
            
        Returns:
            Class information or None if not found
        """
        if not self.ontology:
            raise ValueError("No ontology loaded")
        
        try:
            cls = self.world[uri]
            if isinstance(cls, owl2.ThingClass):
                return self._format_class(cls)
        except KeyError:
            pass
        
        return None

    def get_property(self, uri: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific property by URI.
        
        Args:
            uri: URI of the property
            
        Returns:
            Property information or None if not found
        """
        if not self.ontology:
            raise ValueError("No ontology loaded")
        
        try:
            prop = self.world[uri]
            if isinstance(prop, owl2.ObjectPropertyClass):
                return self._format_property(prop, "object")
            elif isinstance(prop, owl2.DataPropertyClass):
                return self._format_property(prop, "data")
            elif isinstance(prop, owl2.AnnotationPropertyClass):
                return self._format_property(prop, "annotation")
        except KeyError:
            pass
        
        return None

    def find_classes_by_label(
        self, 
        label: str, 
        fuzzy: bool = False,
        case_sensitive: bool = False
    ) -> List[str]:
        """
        Find classes by their label.
        
        Args:
            label: Label to search for
            fuzzy: Use fuzzy matching
            case_sensitive: Use case-sensitive matching
            
        Returns:
            List of matching class URIs
        """
        if not self.ontology:
            raise ValueError("No ontology loaded")
        
        matches = []
        search_label = label if case_sensitive else label.lower()
        
        for cls in self.ontology.classes():
            cls_labels = cls.label
            if not cls_labels:
                continue
            
            for cls_label in cls_labels:
                compare_label = cls_label if case_sensitive else cls_label.lower()
                
                if fuzzy:
                    if search_label in compare_label:
                        matches.append(cls.iri)
                        break
                else:
                    if search_label == compare_label:
                        matches.append(cls.iri)
                        break
        
        return matches

    def get_class_hierarchy(
        self, 
        class_uri: str, 
        max_depth: int = -1
    ) -> Dict[str, Any]:
        """
        Get the class hierarchy for a class.
        
        Args:
            class_uri: URI of the class
            max_depth: Maximum depth to traverse (-1 for unlimited)
            
        Returns:
            Dictionary representing the class hierarchy
        """
        if not self.ontology:
            raise ValueError("No ontology loaded")
        
        try:
            cls = self.world[class_uri]
            if not isinstance(cls, owl2.ThingClass):
                raise ValueError(f"Not a class: {class_uri}")
        except KeyError:
            raise ValueError(f"Class not found: {class_uri}")
        
        def build_hierarchy(current_cls: Any, depth: int = 0) -> Dict[str, Any]:
            if max_depth >= 0 and depth > max_depth:
                return {}
            
            hierarchy: Dict[str, Any] = {
                "uri": current_cls.iri,
                "label": current_cls.label[0] if current_cls.label else None,
                "parents": [],
                "children": []
            }
            
            # Get parents
            for parent in current_cls.is_a:
                if isinstance(parent, owl2.ThingClass):
                    hierarchy["parents"].append({
                        "uri": parent.iri,
                        "label": parent.label[0] if parent.label else None
                    })
            
            # Get children
            for child in current_cls.subclasses():
                if child != current_cls:
                    hierarchy["children"].append(build_hierarchy(child, depth + 1))
            
            return hierarchy
        
        return build_hierarchy(cls)

    def _format_class(self, cls: owl2.ThingClass) -> Dict[str, Any]:
        """Format a class into a dictionary."""
        return {
            "uri": cls.iri,
            "label": cls.label[0] if cls.label else None,
            "comment": cls.comment[0] if cls.comment else None,
            "parents": [p.iri for p in cls.is_a if isinstance(p, owl2.ThingClass)],
            "equivalent": [e.iri for e in cls.equivalent_to if isinstance(e, owl2.ThingClass)],
            "disjoint": [d.iri for d in cls.disjoints() if isinstance(d, owl2.ThingClass)],
        }

    def _format_property(self, prop: Any, prop_type: str) -> Dict[str, Any]:
        """Format a property into a dictionary."""
        info: Dict[str, Any] = {
            "uri": prop.iri,
            "label": prop.label[0] if prop.label else None,
            "comment": prop.comment[0] if prop.comment else None,
            "type": prop_type,
        }
        
        if prop_type in ["object", "data"]:
            info["domain"] = [d.iri for d in prop.domain if hasattr(d, 'iri')]
            info["range"] = [r.iri for r in prop.range if hasattr(r, 'iri')]
            info["parents"] = [p.iri for p in prop.is_a if hasattr(p, 'iri')]
        
        return info

    def to_rdf(self, format: str = "turtle") -> str:
        """
        Serialize the ontology to RDF.
        
        Args:
            format: Output format (turtle, xml, n3, etc.)
            
        Returns:
            Serialized RDF string
        """
        if not self.graph:
            raise ValueError("No ontology loaded")
        
        return self.graph.serialize(format=format)

    def __repr__(self) -> str:
        """String representation of the parser."""
        return f"OWLParser(source={self.source}, reasoning={self.enable_reasoning})"
