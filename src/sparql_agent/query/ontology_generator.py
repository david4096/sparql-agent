"""
Ontology-Guided SPARQL Query Generation.

This module provides intelligent SPARQL query generation using OWL ontologies.
It leverages class hierarchies, property domains/ranges, and reasoning capabilities
to generate semantically enriched queries.

Key Features:
- Class hierarchy traversal for query expansion
- Property path suggestions based on ontology structure
- Constraint validation using OWL axioms
- Semantic query expansion with reasoning
- Integration with EBI OLS4 for real-time ontology lookup
- Cached ontology reasoning for performance
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from pathlib import Path
import logging
from collections import defaultdict
from functools import lru_cache

from rdflib import Graph, Namespace, RDF, RDFS, OWL, URIRef, Literal
from rdflib.namespace import SKOS

from ..core.types import (
    OntologyInfo,
    OWLClass,
    OWLProperty,
    OWLPropertyType,
    GeneratedQuery,
)
from ..ontology.ols_client import OLSClient
from ..ontology.owl_parser import OWLParser


# Configure logging
logger = logging.getLogger(__name__)


class ExpansionStrategy(Enum):
    """Strategy for query expansion."""
    EXACT = "exact"  # No expansion, exact terms only
    CHILDREN = "children"  # Include direct subclasses
    DESCENDANTS = "descendants"  # Include all descendants
    ANCESTORS = "ancestors"  # Include all ancestors
    SIBLINGS = "siblings"  # Include sibling classes
    RELATED = "related"  # Include related classes via properties


class PropertyPathType(Enum):
    """Types of property paths in SPARQL."""
    DIRECT = "direct"  # Direct property
    INVERSE = "inverse"  # Inverse property (^)
    SEQUENCE = "sequence"  # Sequence of properties (/)
    ALTERNATIVE = "alternative"  # Alternative paths (|)
    ZERO_OR_MORE = "zero_or_more"  # Zero or more (*)
    ONE_OR_MORE = "one_or_more"  # One or more (+)
    ZERO_OR_ONE = "zero_or_one"  # Zero or one (?)


@dataclass
class PropertyPath:
    """
    Represents a property path in SPARQL.

    Attributes:
        properties: List of property URIs in the path
        path_type: Type of property path
        label: Human-readable label
        description: Description of what this path represents
        confidence: Confidence score (0-1)
        hops: Number of hops in the path
    """
    properties: List[str]
    path_type: PropertyPathType = PropertyPathType.DIRECT
    label: Optional[str] = None
    description: Optional[str] = None
    confidence: float = 1.0
    hops: int = 1

    def to_sparql(self) -> str:
        """Convert property path to SPARQL syntax."""
        if self.path_type == PropertyPathType.DIRECT:
            return f"<{self.properties[0]}>"
        elif self.path_type == PropertyPathType.INVERSE:
            return f"^<{self.properties[0]}>"
        elif self.path_type == PropertyPathType.SEQUENCE:
            return "/".join(f"<{p}>" for p in self.properties)
        elif self.path_type == PropertyPathType.ALTERNATIVE:
            return "|".join(f"<{p}>" for p in self.properties)
        elif self.path_type == PropertyPathType.ZERO_OR_MORE:
            return f"<{self.properties[0]}>*"
        elif self.path_type == PropertyPathType.ONE_OR_MORE:
            return f"<{self.properties[0]}>+"
        elif self.path_type == PropertyPathType.ZERO_OR_ONE:
            return f"<{self.properties[0]}>?"
        return f"<{self.properties[0]}>"


@dataclass
class QueryConstraint:
    """
    Represents a constraint derived from OWL axioms.

    Attributes:
        constraint_type: Type of constraint (domain, range, cardinality, etc.)
        property_uri: Property URI this constraint applies to
        class_uri: Class URI involved in the constraint
        value: Constraint value (for cardinality, etc.)
        description: Human-readable description
        is_required: Whether this constraint is required
    """
    constraint_type: str
    property_uri: str
    class_uri: Optional[str] = None
    value: Optional[Any] = None
    description: Optional[str] = None
    is_required: bool = False

    def to_sparql_filter(self) -> Optional[str]:
        """Convert constraint to SPARQL FILTER clause."""
        if self.constraint_type == "min_cardinality":
            return None  # Handled by query structure
        elif self.constraint_type == "max_cardinality":
            return None  # Handled by query structure
        elif self.constraint_type == "datatype":
            var = "?value"
            return f"FILTER(datatype({var}) = <{self.value}>)"
        elif self.constraint_type == "value_restriction":
            var = "?value"
            return f"FILTER({var} = <{self.value}>)"
        return None


@dataclass
class OntologyQueryContext:
    """
    Context for ontology-guided query generation.

    Attributes:
        ontology_info: Loaded ontology information
        target_classes: Target classes for the query
        required_properties: Required properties to include
        expansion_strategy: Strategy for class hierarchy expansion
        max_hops: Maximum property path hops
        use_reasoning: Whether to use reasoning
        constraints: List of OWL constraints to apply
        metadata: Additional metadata
    """
    ontology_info: OntologyInfo
    target_classes: List[str] = field(default_factory=list)
    required_properties: List[str] = field(default_factory=list)
    expansion_strategy: ExpansionStrategy = ExpansionStrategy.EXACT
    max_hops: int = 3
    use_reasoning: bool = False
    constraints: List[QueryConstraint] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class OntologyGuidedGenerator:
    """
    Generates SPARQL queries guided by OWL ontologies.

    This class uses ontology structure to:
    - Expand queries using class hierarchies
    - Suggest property paths between classes
    - Validate queries against OWL axioms
    - Apply semantic reasoning for implicit relationships
    """

    def __init__(
        self,
        ontology_info: Optional[OntologyInfo] = None,
        ols_client: Optional[OLSClient] = None,
        enable_caching: bool = True,
    ):
        """
        Initialize the ontology-guided generator.

        Args:
            ontology_info: Pre-loaded ontology information
            ols_client: OLS client for real-time ontology lookup
            enable_caching: Enable caching for ontology operations
        """
        self.ontology_info = ontology_info
        self.ols_client = ols_client or OLSClient()
        self.enable_caching = enable_caching

        # Cache for ontology lookups
        self._class_hierarchy_cache: Dict[str, Dict[str, Any]] = {}
        self._property_path_cache: Dict[Tuple[str, str], List[PropertyPath]] = {}
        self._constraint_cache: Dict[str, List[QueryConstraint]] = {}

    def generate_query(
        self,
        user_query: str,
        context: OntologyQueryContext,
        include_explanation: bool = True,
    ) -> GeneratedQuery:
        """
        Generate a SPARQL query using ontology guidance.

        Args:
            user_query: Natural language query
            context: Ontology query context
            include_explanation: Include explanation of ontology usage

        Returns:
            Generated SPARQL query with ontology metadata
        """
        # Parse user query to identify key concepts
        concepts = self._extract_concepts(user_query, context.ontology_info)

        # Expand classes using hierarchy
        expanded_classes = self._expand_classes(
            concepts["classes"],
            context.expansion_strategy,
            context.ontology_info,
        )

        # Find property paths between classes
        property_paths = self._find_property_paths(
            expanded_classes,
            context.required_properties,
            context.ontology_info,
            max_hops=context.max_hops,
        )

        # Apply OWL constraints
        constraints = self._extract_constraints(
            expanded_classes,
            property_paths,
            context.ontology_info,
        )
        context.constraints.extend(constraints)

        # Build SPARQL query
        query = self._build_sparql_query(
            expanded_classes,
            property_paths,
            context.constraints,
            concepts.get("filters", []),
        )

        # Build explanation
        explanation = None
        if include_explanation:
            explanation = self._build_explanation(
                user_query,
                concepts,
                expanded_classes,
                property_paths,
                constraints,
            )

        return GeneratedQuery(
            query=query,
            natural_language=user_query,
            explanation=explanation,
            confidence=self._calculate_confidence(concepts, expanded_classes, property_paths),
            used_ontology=True,
            ontology_classes=list(expanded_classes.keys()),
            ontology_properties=[p for path in property_paths for p in path.properties],
            metadata={
                "concepts": concepts,
                "expansion_strategy": context.expansion_strategy.value,
                "property_paths": [p.to_sparql() for p in property_paths],
                "constraints_applied": len(constraints),
            },
        )

    def _extract_concepts(
        self,
        user_query: str,
        ontology_info: OntologyInfo,
    ) -> Dict[str, Any]:
        """
        Extract ontology concepts from natural language query.

        Args:
            user_query: Natural language query
            ontology_info: Ontology information

        Returns:
            Dictionary of extracted concepts
        """
        concepts: Dict[str, Any] = {
            "classes": [],
            "properties": [],
            "filters": [],
            "keywords": [],
        }

        # Normalize query
        query_lower = user_query.lower()
        words = query_lower.split()

        # Match class labels
        for class_uri, owl_class in ontology_info.classes.items():
            for label in owl_class.label:
                label_lower = label.lower()
                if label_lower in query_lower or any(
                    word in label_lower.split() for word in words
                ):
                    concepts["classes"].append({
                        "uri": class_uri,
                        "label": label,
                        "matched_text": label_lower,
                        "confidence": 0.8,
                    })

        # Match property labels
        for prop_uri, owl_prop in ontology_info.properties.items():
            for label in owl_prop.label:
                label_lower = label.lower()
                if label_lower in query_lower or any(
                    word in label_lower.split() for word in words
                ):
                    concepts["properties"].append({
                        "uri": prop_uri,
                        "label": label,
                        "matched_text": label_lower,
                        "confidence": 0.8,
                    })

        # Extract filter keywords
        filter_keywords = {
            "greater": ">",
            "less": "<",
            "equal": "=",
            "contains": "CONTAINS",
            "starts with": "STRSTARTS",
            "ends with": "STRENDS",
        }

        for keyword, operator in filter_keywords.items():
            if keyword in query_lower:
                concepts["filters"].append({
                    "keyword": keyword,
                    "operator": operator,
                })

        return concepts

    def _expand_classes(
        self,
        target_classes: List[Dict[str, Any]],
        strategy: ExpansionStrategy,
        ontology_info: OntologyInfo,
    ) -> Dict[str, OWLClass]:
        """
        Expand classes using hierarchy based on strategy.

        Args:
            target_classes: Target classes to expand
            strategy: Expansion strategy
            ontology_info: Ontology information

        Returns:
            Dictionary of expanded classes (URI -> OWLClass)
        """
        expanded: Dict[str, OWLClass] = {}

        if strategy == ExpansionStrategy.EXACT:
            # No expansion, just return target classes
            for class_info in target_classes:
                uri = class_info["uri"]
                if uri in ontology_info.classes:
                    expanded[uri] = ontology_info.classes[uri]

        elif strategy == ExpansionStrategy.CHILDREN:
            # Include direct subclasses
            for class_info in target_classes:
                uri = class_info["uri"]
                if uri in ontology_info.classes:
                    expanded[uri] = ontology_info.classes[uri]
                    # Add direct children
                    children = ontology_info.get_subclasses(uri, recursive=False)
                    for child_uri in children:
                        if child_uri in ontology_info.classes:
                            expanded[child_uri] = ontology_info.classes[child_uri]

        elif strategy == ExpansionStrategy.DESCENDANTS:
            # Include all descendants
            for class_info in target_classes:
                uri = class_info["uri"]
                if uri in ontology_info.classes:
                    expanded[uri] = ontology_info.classes[uri]
                    # Add all descendants
                    descendants = ontology_info.get_subclasses(uri, recursive=True)
                    for desc_uri in descendants:
                        if desc_uri in ontology_info.classes:
                            expanded[desc_uri] = ontology_info.classes[desc_uri]

        elif strategy == ExpansionStrategy.ANCESTORS:
            # Include all ancestors
            for class_info in target_classes:
                uri = class_info["uri"]
                if uri in ontology_info.classes:
                    expanded[uri] = ontology_info.classes[uri]
                    # Add all ancestors
                    ancestors = ontology_info.get_superclasses(uri, recursive=True)
                    for anc_uri in ancestors:
                        if anc_uri in ontology_info.classes:
                            expanded[anc_uri] = ontology_info.classes[anc_uri]

        elif strategy == ExpansionStrategy.SIBLINGS:
            # Include sibling classes (same parent)
            for class_info in target_classes:
                uri = class_info["uri"]
                if uri in ontology_info.classes:
                    expanded[uri] = ontology_info.classes[uri]
                    owl_class = ontology_info.classes[uri]
                    # Get siblings through parents
                    for parent_uri in owl_class.subclass_of:
                        siblings = ontology_info.get_subclasses(parent_uri, recursive=False)
                        for sib_uri in siblings:
                            if sib_uri != uri and sib_uri in ontology_info.classes:
                                expanded[sib_uri] = ontology_info.classes[sib_uri]

        elif strategy == ExpansionStrategy.RELATED:
            # Include related classes via properties
            for class_info in target_classes:
                uri = class_info["uri"]
                if uri in ontology_info.classes:
                    expanded[uri] = ontology_info.classes[uri]
                    # Find properties that have this class in domain or range
                    related = self._find_related_classes(uri, ontology_info)
                    for rel_uri in related:
                        if rel_uri in ontology_info.classes:
                            expanded[rel_uri] = ontology_info.classes[rel_uri]

        return expanded

    def _find_related_classes(
        self,
        class_uri: str,
        ontology_info: OntologyInfo,
    ) -> Set[str]:
        """Find classes related via properties."""
        related: Set[str] = set()

        for prop_uri, owl_prop in ontology_info.properties.items():
            # Check if class is in domain
            if class_uri in owl_prop.domain:
                # Add range classes
                related.update(owl_prop.range)
            # Check if class is in range
            if class_uri in owl_prop.range:
                # Add domain classes
                related.update(owl_prop.domain)

        return related

    def _find_property_paths(
        self,
        expanded_classes: Dict[str, OWLClass],
        required_properties: List[str],
        ontology_info: OntologyInfo,
        max_hops: int = 3,
    ) -> List[PropertyPath]:
        """
        Find property paths connecting classes.

        Args:
            expanded_classes: Expanded classes to connect
            required_properties: Required properties to include
            ontology_info: Ontology information
            max_hops: Maximum path length

        Returns:
            List of property paths
        """
        property_paths: List[PropertyPath] = []

        # Direct properties from required list
        for prop_uri in required_properties:
            if prop_uri in ontology_info.properties:
                owl_prop = ontology_info.properties[prop_uri]
                property_paths.append(
                    PropertyPath(
                        properties=[prop_uri],
                        path_type=PropertyPathType.DIRECT,
                        label=owl_prop.get_primary_label(),
                        description=owl_prop.get_primary_comment(),
                        confidence=1.0,
                        hops=1,
                    )
                )

        # Find paths between pairs of classes
        class_uris = list(expanded_classes.keys())
        for i, source_uri in enumerate(class_uris):
            for target_uri in class_uris[i + 1 :]:
                paths = self._find_paths_between_classes(
                    source_uri,
                    target_uri,
                    ontology_info,
                    max_hops,
                )
                property_paths.extend(paths)

        # Remove duplicates and sort by confidence
        unique_paths = self._deduplicate_paths(property_paths)
        unique_paths.sort(key=lambda p: p.confidence, reverse=True)

        return unique_paths

    def _find_paths_between_classes(
        self,
        source_uri: str,
        target_uri: str,
        ontology_info: OntologyInfo,
        max_hops: int,
    ) -> List[PropertyPath]:
        """Find property paths between two classes using BFS."""
        # Check cache
        cache_key = (source_uri, target_uri)
        if self.enable_caching and cache_key in self._property_path_cache:
            return self._property_path_cache[cache_key]

        paths: List[PropertyPath] = []

        # BFS to find paths
        queue: List[Tuple[str, List[str], int]] = [(source_uri, [], 0)]
        visited: Set[Tuple[str, int]] = set()

        while queue:
            current_class, path_props, hops = queue.pop(0)

            if hops > max_hops:
                continue

            # Check if we reached target
            if current_class == target_uri and path_props:
                # Create property path
                paths.append(
                    PropertyPath(
                        properties=path_props,
                        path_type=PropertyPathType.SEQUENCE if len(path_props) > 1 else PropertyPathType.DIRECT,
                        confidence=1.0 / (hops + 1),  # Decrease confidence with hops
                        hops=hops,
                    )
                )
                continue

            # Avoid revisiting
            state = (current_class, hops)
            if state in visited:
                continue
            visited.add(state)

            # Explore properties
            for prop_uri, owl_prop in ontology_info.properties.items():
                # Check if property can be used from current class
                if current_class in owl_prop.domain:
                    # Follow property to range classes
                    for range_class in owl_prop.range:
                        new_path = path_props + [prop_uri]
                        queue.append((range_class, new_path, hops + 1))

        # Cache results
        if self.enable_caching:
            self._property_path_cache[cache_key] = paths

        return paths

    def _deduplicate_paths(self, paths: List[PropertyPath]) -> List[PropertyPath]:
        """Remove duplicate property paths."""
        seen: Set[str] = set()
        unique: List[PropertyPath] = []

        for path in paths:
            key = ":".join(path.properties)
            if key not in seen:
                seen.add(key)
                unique.append(path)

        return unique

    def _extract_constraints(
        self,
        expanded_classes: Dict[str, OWLClass],
        property_paths: List[PropertyPath],
        ontology_info: OntologyInfo,
    ) -> List[QueryConstraint]:
        """
        Extract OWL constraints for query validation.

        Args:
            expanded_classes: Expanded classes
            property_paths: Property paths in query
            ontology_info: Ontology information

        Returns:
            List of query constraints
        """
        constraints: List[QueryConstraint] = []

        # Extract constraints from property restrictions
        for class_uri, owl_class in expanded_classes.items():
            for restriction in owl_class.restrictions:
                constraint = self._restriction_to_constraint(restriction, class_uri)
                if constraint:
                    constraints.append(constraint)

        # Extract domain/range constraints from properties
        for path in property_paths:
            for prop_uri in path.properties:
                if prop_uri in ontology_info.properties:
                    owl_prop = ontology_info.properties[prop_uri]

                    # Domain constraint
                    if owl_prop.domain:
                        constraints.append(
                            QueryConstraint(
                                constraint_type="domain",
                                property_uri=prop_uri,
                                class_uri=owl_prop.domain[0] if owl_prop.domain else None,
                                description=f"Property {owl_prop.get_primary_label()} requires domain",
                            )
                        )

                    # Range constraint
                    if owl_prop.range:
                        constraints.append(
                            QueryConstraint(
                                constraint_type="range",
                                property_uri=prop_uri,
                                class_uri=owl_prop.range[0] if owl_prop.range else None,
                                description=f"Property {owl_prop.get_primary_label()} requires range",
                            )
                        )

        return constraints

    def _restriction_to_constraint(
        self,
        restriction: Dict[str, Any],
        class_uri: str,
    ) -> Optional[QueryConstraint]:
        """Convert OWL restriction to query constraint."""
        restriction_type = restriction.get("type")
        property_uri = restriction.get("property")

        if not restriction_type or not property_uri:
            return None

        if restriction_type == "some_values_from":
            return QueryConstraint(
                constraint_type="existential",
                property_uri=property_uri,
                class_uri=restriction.get("value"),
                description=f"Class {class_uri} requires some values from property",
                is_required=True,
            )
        elif restriction_type == "min_cardinality":
            return QueryConstraint(
                constraint_type="min_cardinality",
                property_uri=property_uri,
                value=restriction.get("cardinality", 1),
                description=f"Minimum cardinality constraint",
            )
        elif restriction_type == "max_cardinality":
            return QueryConstraint(
                constraint_type="max_cardinality",
                property_uri=property_uri,
                value=restriction.get("cardinality", 1),
                description=f"Maximum cardinality constraint",
            )

        return None

    def _build_sparql_query(
        self,
        expanded_classes: Dict[str, OWLClass],
        property_paths: List[PropertyPath],
        constraints: List[QueryConstraint],
        filters: List[Dict[str, Any]],
    ) -> str:
        """
        Build SPARQL query from ontology-guided components.

        Args:
            expanded_classes: Expanded classes
            property_paths: Property paths
            constraints: OWL constraints
            filters: Additional filters

        Returns:
            SPARQL query string
        """
        # Start query
        query_parts = ["SELECT DISTINCT ?subject ?label"]
        query_parts.append("WHERE {")

        # Add class patterns
        if expanded_classes:
            class_uris = list(expanded_classes.keys())
            if len(class_uris) == 1:
                query_parts.append(f"  ?subject a <{class_uris[0]}> .")
            else:
                # Use VALUES for multiple classes
                class_list = " ".join(f"<{uri}>" for uri in class_uris)
                query_parts.append(f"  VALUES ?type {{ {class_list} }}")
                query_parts.append("  ?subject a ?type .")

        # Add property paths
        for i, path in enumerate(property_paths[:5]):  # Limit to top 5 paths
            sparql_path = path.to_sparql()
            var_name = f"?value{i}" if i > 0 else "?value"
            query_parts.append(f"  ?subject {sparql_path} {var_name} .")

        # Add label
        query_parts.append("  OPTIONAL { ?subject rdfs:label ?label . }")

        # Add filters from constraints
        for constraint in constraints:
            filter_clause = constraint.to_sparql_filter()
            if filter_clause:
                query_parts.append(f"  {filter_clause}")

        # Add user filters
        for filter_info in filters:
            operator = filter_info.get("operator", "=")
            # Basic filter - would need more sophisticated parsing
            query_parts.append(f"  # Filter: {filter_info.get('keyword')}")

        query_parts.append("}")
        query_parts.append("LIMIT 100")

        return "\n".join(query_parts)

    def _build_explanation(
        self,
        user_query: str,
        concepts: Dict[str, Any],
        expanded_classes: Dict[str, OWLClass],
        property_paths: List[PropertyPath],
        constraints: List[QueryConstraint],
    ) -> str:
        """Build human-readable explanation of query generation."""
        lines = []
        lines.append(f"Query Analysis: '{user_query}'")
        lines.append("")

        # Concepts identified
        lines.append("Identified Concepts:")
        if concepts["classes"]:
            lines.append("  Classes:")
            for cls in concepts["classes"][:5]:
                lines.append(f"    - {cls['label']} ({cls['confidence']:.2f})")
        if concepts["properties"]:
            lines.append("  Properties:")
            for prop in concepts["properties"][:5]:
                lines.append(f"    - {prop['label']} ({prop['confidence']:.2f})")
        lines.append("")

        # Class expansion
        lines.append(f"Expanded to {len(expanded_classes)} classes using ontology hierarchy")
        lines.append("")

        # Property paths
        if property_paths:
            lines.append(f"Found {len(property_paths)} property paths:")
            for path in property_paths[:3]:
                lines.append(f"  - {path.to_sparql()} (confidence: {path.confidence:.2f})")
        lines.append("")

        # Constraints
        if constraints:
            lines.append(f"Applied {len(constraints)} OWL constraints:")
            for constraint in constraints[:3]:
                if constraint.description:
                    lines.append(f"  - {constraint.description}")

        return "\n".join(lines)

    def _calculate_confidence(
        self,
        concepts: Dict[str, Any],
        expanded_classes: Dict[str, OWLClass],
        property_paths: List[PropertyPath],
    ) -> float:
        """Calculate overall confidence score for the generated query."""
        scores = []

        # Concept matching confidence
        if concepts["classes"]:
            avg_class_conf = sum(c["confidence"] for c in concepts["classes"]) / len(
                concepts["classes"]
            )
            scores.append(avg_class_conf)

        if concepts["properties"]:
            avg_prop_conf = sum(p["confidence"] for p in concepts["properties"]) / len(
                concepts["properties"]
            )
            scores.append(avg_prop_conf)

        # Path confidence
        if property_paths:
            avg_path_conf = sum(p.confidence for p in property_paths) / len(property_paths)
            scores.append(avg_path_conf)

        # Overall confidence
        if scores:
            return sum(scores) / len(scores)
        return 0.5

    # ============================================================================
    # OLS Integration Methods
    # ============================================================================

    def expand_with_ols(
        self,
        term_label: str,
        ontology_id: str,
        strategy: ExpansionStrategy = ExpansionStrategy.DESCENDANTS,
    ) -> List[Dict[str, Any]]:
        """
        Expand terms using EBI OLS4 real-time lookup.

        Args:
            term_label: Term label to search for
            ontology_id: Ontology ID (e.g., "go", "efo", "hp")
            strategy: Expansion strategy

        Returns:
            List of expanded terms with metadata
        """
        # Search for term
        results = self.ols_client.search(
            query=term_label,
            ontology=ontology_id,
            exact=False,
            limit=1,
        )

        if not results:
            logger.warning(f"No results found for term: {term_label}")
            return []

        term = results[0]
        term_id = term["id"]

        # Expand based on strategy
        expanded = [term]

        if strategy == ExpansionStrategy.CHILDREN:
            children = self.ols_client.get_term_children(ontology_id, term_id)
            expanded.extend(children)

        elif strategy == ExpansionStrategy.DESCENDANTS:
            descendants = self.ols_client.get_term_descendants(ontology_id, term_id)
            expanded.extend(descendants)

        elif strategy == ExpansionStrategy.ANCESTORS:
            ancestors = self.ols_client.get_term_ancestors(ontology_id, term_id)
            expanded.extend(ancestors)

        return expanded

    def suggest_properties_for_classes(
        self,
        class_uris: List[str],
        ontology_id: str,
        max_suggestions: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Suggest properties that connect given classes.

        Args:
            class_uris: List of class URIs
            ontology_id: Ontology ID
            max_suggestions: Maximum suggestions to return

        Returns:
            List of property suggestions
        """
        suggestions = []

        if not self.ontology_info:
            logger.warning("No ontology loaded, cannot suggest properties")
            return suggestions

        # Find properties that connect the classes
        for prop_uri, owl_prop in self.ontology_info.properties.items():
            score = 0
            relevant_classes = []

            # Check domain
            for class_uri in class_uris:
                if class_uri in owl_prop.domain:
                    score += 1
                    relevant_classes.append(class_uri)

            # Check range
            for class_uri in class_uris:
                if class_uri in owl_prop.range:
                    score += 1
                    relevant_classes.append(class_uri)

            if score > 0:
                suggestions.append({
                    "uri": prop_uri,
                    "label": owl_prop.get_primary_label(),
                    "description": owl_prop.get_primary_comment(),
                    "score": score,
                    "relevant_classes": list(set(relevant_classes)),
                    "domain": owl_prop.domain,
                    "range": owl_prop.range,
                })

        # Sort by score and return top suggestions
        suggestions.sort(key=lambda s: s["score"], reverse=True)
        return suggestions[:max_suggestions]

    def validate_query_against_ontology(
        self,
        query: str,
        ontology_info: OntologyInfo,
    ) -> Dict[str, Any]:
        """
        Validate a SPARQL query against ontology constraints.

        Args:
            query: SPARQL query string
            ontology_info: Ontology information

        Returns:
            Validation results with errors and warnings
        """
        validation = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": [],
        }

        # Extract classes and properties from query
        # This is a simplified extraction - would need proper SPARQL parsing
        used_classes = self._extract_classes_from_query(query)
        used_properties = self._extract_properties_from_query(query)

        # Check if classes exist in ontology
        for class_uri in used_classes:
            if class_uri not in ontology_info.classes:
                validation["errors"].append(
                    f"Class not found in ontology: {class_uri}"
                )
                validation["is_valid"] = False

        # Check if properties exist and have correct domain/range
        for prop_uri in used_properties:
            if prop_uri not in ontology_info.properties:
                validation["warnings"].append(
                    f"Property not found in ontology: {prop_uri}"
                )
            else:
                owl_prop = ontology_info.properties[prop_uri]
                # Check domain/range consistency
                if owl_prop.domain and used_classes:
                    domain_match = any(c in owl_prop.domain for c in used_classes)
                    if not domain_match:
                        validation["warnings"].append(
                            f"Property {prop_uri} domain mismatch"
                        )

        return validation

    def _extract_classes_from_query(self, query: str) -> List[str]:
        """Extract class URIs from SPARQL query (simplified)."""
        classes = []
        # Look for "a <URI>" patterns
        import re
        pattern = r'a\s+<([^>]+)>'
        matches = re.findall(pattern, query)
        classes.extend(matches)
        return classes

    def _extract_properties_from_query(self, query: str) -> List[str]:
        """Extract property URIs from SPARQL query (simplified)."""
        properties = []
        # Look for "<URI>" in triple patterns
        import re
        pattern = r'<([^>]+)>'
        matches = re.findall(pattern, query)
        # Filter out known classes and types
        properties = [m for m in matches if not m.endswith("#type")]
        return properties

    def load_ontology_from_ols(
        self,
        ontology_id: str,
        cache_path: Optional[Path] = None,
    ) -> OntologyInfo:
        """
        Load ontology from OLS and optionally cache it.

        Args:
            ontology_id: Ontology ID (e.g., "go", "efo")
            cache_path: Optional path to cache the ontology

        Returns:
            Loaded ontology information
        """
        logger.info(f"Loading ontology '{ontology_id}' from OLS...")

        # Download ontology
        if cache_path:
            ontology_file = cache_path / f"{ontology_id}.owl"
            if not ontology_file.exists():
                downloaded = self.ols_client.download_ontology(ontology_id, ontology_file)
            else:
                downloaded = ontology_file
        else:
            downloaded = self.ols_client.download_ontology(ontology_id)

        # Parse with OWL parser
        parser = OWLParser(str(downloaded), enable_reasoning=False)

        # Convert to OntologyInfo
        ontology_info = self._convert_parser_to_ontology_info(parser)

        # Store for reuse
        self.ontology_info = ontology_info

        logger.info(f"Loaded {len(ontology_info.classes)} classes and {len(ontology_info.properties)} properties")

        return ontology_info

    def _convert_parser_to_ontology_info(self, parser: OWLParser) -> OntologyInfo:
        """Convert OWLParser output to OntologyInfo."""
        metadata = parser.get_metadata()

        ontology_info = OntologyInfo(
            uri=metadata.get("iri", ""),
            title=metadata.get("label"),
            description=metadata.get("description"),
            version=metadata.get("version"),
        )

        # Convert classes
        for class_dict in parser.get_classes():
            owl_class = OWLClass(
                uri=class_dict["uri"],
                label=[class_dict["label"]] if class_dict["label"] else [],
                comment=[class_dict["comment"]] if class_dict["comment"] else [],
                subclass_of=class_dict.get("parents", []),
                equivalent_classes=class_dict.get("equivalent", []),
                disjoint_with=class_dict.get("disjoint", []),
            )
            ontology_info.classes[owl_class.uri] = owl_class

        # Convert properties
        for prop_dict in parser.get_properties():
            prop_type = OWLPropertyType.OBJECT_PROPERTY
            if prop_dict["type"] == "data":
                prop_type = OWLPropertyType.DATATYPE_PROPERTY
            elif prop_dict["type"] == "annotation":
                prop_type = OWLPropertyType.ANNOTATION_PROPERTY

            owl_prop = OWLProperty(
                uri=prop_dict["uri"],
                label=[prop_dict["label"]] if prop_dict["label"] else [],
                comment=[prop_dict["comment"]] if prop_dict["comment"] else [],
                property_type=prop_type,
                domain=prop_dict.get("domain", []),
                range=prop_dict.get("range", []),
                subproperty_of=prop_dict.get("parents", []),
            )
            ontology_info.properties[owl_prop.uri] = owl_prop

        return ontology_info


# ============================================================================
# Convenience Functions
# ============================================================================


def create_ontology_generator(
    ontology_source: Optional[Union[str, Path, OntologyInfo]] = None,
    ontology_id: Optional[str] = None,
    enable_ols: bool = True,
) -> OntologyGuidedGenerator:
    """
    Create an ontology-guided generator.

    Args:
        ontology_source: Path to ontology file or OntologyInfo object
        ontology_id: OLS ontology ID (if loading from OLS)
        enable_ols: Enable OLS integration

    Returns:
        Configured OntologyGuidedGenerator
    """
    ols_client = OLSClient() if enable_ols else None
    generator = OntologyGuidedGenerator(ols_client=ols_client)

    if isinstance(ontology_source, OntologyInfo):
        generator.ontology_info = ontology_source
    elif ontology_source:
        # Load from file
        parser = OWLParser(str(ontology_source))
        generator.ontology_info = generator._convert_parser_to_ontology_info(parser)
    elif ontology_id and enable_ols:
        # Load from OLS
        generator.load_ontology_from_ols(ontology_id)

    return generator


def quick_ontology_query(
    user_query: str,
    ontology_id: str,
    expansion: str = "exact",
    max_hops: int = 3,
) -> GeneratedQuery:
    """
    Quick ontology-guided query generation.

    Args:
        user_query: Natural language query
        ontology_id: OLS ontology ID
        expansion: Expansion strategy ("exact", "children", "descendants", etc.)
        max_hops: Maximum property path hops

    Returns:
        Generated query with ontology guidance
    """
    generator = create_ontology_generator(ontology_id=ontology_id)

    strategy = ExpansionStrategy[expansion.upper()]

    context = OntologyQueryContext(
        ontology_info=generator.ontology_info,
        expansion_strategy=strategy,
        max_hops=max_hops,
    )

    return generator.generate_query(user_query, context)
