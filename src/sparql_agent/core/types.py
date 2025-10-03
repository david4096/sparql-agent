"""
Core types for the SPARQL-LLM system.

This module defines the fundamental data structures used throughout the system,
including types for query results, endpoint information, schema information,
LLM responses, and ontology representations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union


class QueryStatus(Enum):
    """Status of a SPARQL query execution."""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    INVALID = "invalid"
    PENDING = "pending"


class OWLPropertyType(Enum):
    """Types of OWL properties."""
    OBJECT_PROPERTY = "object_property"
    DATATYPE_PROPERTY = "datatype_property"
    ANNOTATION_PROPERTY = "annotation_property"
    FUNCTIONAL = "functional"
    INVERSE_FUNCTIONAL = "inverse_functional"
    TRANSITIVE = "transitive"
    SYMMETRIC = "symmetric"


class OWLRestrictionType(Enum):
    """Types of OWL class restrictions."""
    SOME_VALUES_FROM = "some_values_from"
    ALL_VALUES_FROM = "all_values_from"
    HAS_VALUE = "has_value"
    MIN_CARDINALITY = "min_cardinality"
    MAX_CARDINALITY = "max_cardinality"
    EXACT_CARDINALITY = "exact_cardinality"


@dataclass
class OWLClass:
    """
    Represents an OWL class definition.

    Attributes:
        uri: The URI of the OWL class
        label: Human-readable label(s) for the class
        comment: Documentation/comment(s) about the class
        subclass_of: List of parent class URIs
        equivalent_classes: List of equivalent class URIs
        disjoint_with: List of disjoint class URIs
        restrictions: List of class restrictions
        properties: Properties associated with this class
        instances_count: Approximate number of instances (if available)
        is_deprecated: Whether the class is marked as deprecated
        see_also: Related resource URIs
    """
    uri: str
    label: List[str] = field(default_factory=list)
    comment: List[str] = field(default_factory=list)
    subclass_of: List[str] = field(default_factory=list)
    equivalent_classes: List[str] = field(default_factory=list)
    disjoint_with: List[str] = field(default_factory=list)
    restrictions: List[Dict[str, Any]] = field(default_factory=list)
    properties: List[str] = field(default_factory=list)
    instances_count: Optional[int] = None
    is_deprecated: bool = False
    see_also: List[str] = field(default_factory=list)

    def get_primary_label(self) -> str:
        """Get the primary label, falling back to URI if none exists."""
        if self.label:
            return self.label[0]
        return self.uri.split("#")[-1].split("/")[-1]

    def get_primary_comment(self) -> Optional[str]:
        """Get the primary comment/description."""
        return self.comment[0] if self.comment else None


@dataclass
class OWLProperty:
    """
    Represents an OWL property definition.

    Attributes:
        uri: The URI of the OWL property
        label: Human-readable label(s) for the property
        comment: Documentation/comment(s) about the property
        property_type: Type of property (object, datatype, etc.)
        domain: List of class URIs that can have this property
        range: List of class/datatype URIs that this property can have as values
        subproperty_of: List of parent property URIs
        inverse_of: URI of inverse property (if any)
        equivalent_properties: List of equivalent property URIs
        is_functional: Whether the property is functional
        is_inverse_functional: Whether the property is inverse functional
        is_transitive: Whether the property is transitive
        is_symmetric: Whether the property is symmetric
        is_deprecated: Whether the property is marked as deprecated
        usage_count: Approximate number of triples using this property
        see_also: Related resource URIs
    """
    uri: str
    label: List[str] = field(default_factory=list)
    comment: List[str] = field(default_factory=list)
    property_type: OWLPropertyType = OWLPropertyType.OBJECT_PROPERTY
    domain: List[str] = field(default_factory=list)
    range: List[str] = field(default_factory=list)
    subproperty_of: List[str] = field(default_factory=list)
    inverse_of: Optional[str] = None
    equivalent_properties: List[str] = field(default_factory=list)
    is_functional: bool = False
    is_inverse_functional: bool = False
    is_transitive: bool = False
    is_symmetric: bool = False
    is_deprecated: bool = False
    usage_count: Optional[int] = None
    see_also: List[str] = field(default_factory=list)

    def get_primary_label(self) -> str:
        """Get the primary label, falling back to URI if none exists."""
        if self.label:
            return self.label[0]
        return self.uri.split("#")[-1].split("/")[-1]

    def get_primary_comment(self) -> Optional[str]:
        """Get the primary comment/description."""
        return self.comment[0] if self.comment else None


@dataclass
class OntologyInfo:
    """
    Information about an ontology.

    Attributes:
        uri: The ontology URI/IRI
        title: Ontology title
        description: Ontology description
        version: Version information
        classes: Dictionary of OWL classes (URI -> OWLClass)
        properties: Dictionary of OWL properties (URI -> OWLProperty)
        namespaces: Namespace prefixes and URIs
        imports: List of imported ontology URIs
        authors: List of ontology authors
        license: License information
        created: Creation date
        modified: Last modified date
        metadata: Additional metadata as key-value pairs
    """
    uri: str
    title: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    classes: Dict[str, OWLClass] = field(default_factory=dict)
    properties: Dict[str, OWLProperty] = field(default_factory=dict)
    namespaces: Dict[str, str] = field(default_factory=dict)
    imports: List[str] = field(default_factory=list)
    authors: List[str] = field(default_factory=list)
    license: Optional[str] = None
    created: Optional[datetime] = None
    modified: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_class_by_label(self, label: str) -> Optional[OWLClass]:
        """Find a class by its label."""
        for owl_class in self.classes.values():
            if label.lower() in [lbl.lower() for lbl in owl_class.label]:
                return owl_class
        return None

    def get_property_by_label(self, label: str) -> Optional[OWLProperty]:
        """Find a property by its label."""
        for owl_property in self.properties.values():
            if label.lower() in [lbl.lower() for lbl in owl_property.label]:
                return owl_property
        return None

    def get_subclasses(self, class_uri: str, recursive: bool = False) -> List[str]:
        """Get all subclasses of a given class."""
        subclasses = []
        for uri, owl_class in self.classes.items():
            if class_uri in owl_class.subclass_of:
                subclasses.append(uri)
                if recursive:
                    subclasses.extend(self.get_subclasses(uri, recursive=True))
        return list(set(subclasses))

    def get_superclasses(self, class_uri: str, recursive: bool = False) -> List[str]:
        """Get all superclasses of a given class."""
        if class_uri not in self.classes:
            return []

        superclasses = list(self.classes[class_uri].subclass_of)
        if recursive:
            for parent in list(superclasses):
                superclasses.extend(self.get_superclasses(parent, recursive=True))
        return list(set(superclasses))


@dataclass
class EndpointInfo:
    """
    Information about a SPARQL endpoint.

    Attributes:
        url: The endpoint URL
        name: Human-readable endpoint name
        description: Description of the endpoint
        graph_uri: Default graph URI (if applicable)
        supports_update: Whether the endpoint supports SPARQL UPDATE
        timeout: Default timeout in seconds
        rate_limit: Rate limit (requests per second)
        authentication_required: Whether authentication is required
        version: SPARQL version supported
        metadata: Additional metadata as key-value pairs
    """
    url: str
    name: Optional[str] = None
    description: Optional[str] = None
    graph_uri: Optional[str] = None
    supports_update: bool = False
    timeout: int = 30
    rate_limit: Optional[float] = None
    authentication_required: bool = False
    version: str = "1.1"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SchemaInfo:
    """
    Schema information discovered from a SPARQL endpoint.

    Attributes:
        classes: Set of class URIs found in the dataset
        properties: Set of property URIs found in the dataset
        namespaces: Dictionary of namespace prefixes to URIs
        class_counts: Dictionary of class URIs to instance counts
        property_counts: Dictionary of property URIs to usage counts
        predicates: Set of all predicates (properties) used
        ontology: Associated ontology information (if available)
        sample_instances: Sample instances for each class
        property_domains: Inferred domains for properties
        property_ranges: Inferred ranges for properties
        discovered_at: Timestamp when schema was discovered
        endpoint_info: Information about the source endpoint
    """
    classes: Set[str] = field(default_factory=set)
    properties: Set[str] = field(default_factory=set)
    namespaces: Dict[str, str] = field(default_factory=dict)
    class_counts: Dict[str, int] = field(default_factory=dict)
    property_counts: Dict[str, int] = field(default_factory=dict)
    predicates: Set[str] = field(default_factory=set)
    ontology: Optional[OntologyInfo] = None
    sample_instances: Dict[str, List[str]] = field(default_factory=dict)
    property_domains: Dict[str, Set[str]] = field(default_factory=dict)
    property_ranges: Dict[str, Set[str]] = field(default_factory=dict)
    discovered_at: datetime = field(default_factory=datetime.now)
    endpoint_info: Optional[EndpointInfo] = None

    def get_most_common_classes(self, limit: int = 10) -> List[tuple[str, int]]:
        """Get the most common classes by instance count."""
        return sorted(
            self.class_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]

    def get_most_common_properties(self, limit: int = 10) -> List[tuple[str, int]]:
        """Get the most common properties by usage count."""
        return sorted(
            self.property_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]


@dataclass
class QueryResult:
    """
    Result of a SPARQL query execution.

    Attributes:
        status: Status of the query execution
        data: Query result data (list of bindings or boolean for ASK queries)
        query: The original SPARQL query
        execution_time: Time taken to execute the query in seconds
        error_message: Error message if query failed
        warnings: List of warning messages
        bindings: List of variable bindings (for SELECT queries)
        row_count: Number of rows returned
        variables: List of variables in the SELECT clause
        metadata: Additional metadata about the query execution
    """
    status: QueryStatus
    data: Optional[Union[List[Dict[str, Any]], bool]] = None
    query: Optional[str] = None
    execution_time: Optional[float] = None
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    bindings: List[Dict[str, Any]] = field(default_factory=list)
    row_count: int = 0
    variables: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        """Check if the query was successful."""
        return self.status == QueryStatus.SUCCESS

    @property
    def is_empty(self) -> bool:
        """Check if the result is empty."""
        return self.row_count == 0


@dataclass
class LLMResponse:
    """
    Response from an LLM provider.

    Attributes:
        content: The generated content
        model: Model used for generation
        prompt: The original prompt
        tokens_used: Number of tokens used (prompt + completion)
        prompt_tokens: Number of tokens in the prompt
        completion_tokens: Number of tokens in the completion
        finish_reason: Reason for completion (stop, length, etc.)
        cost: Estimated cost of the request
        latency: Time taken for the request in seconds
        metadata: Additional metadata from the provider
    """
    content: str
    model: str
    prompt: Optional[str] = None
    tokens_used: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    finish_reason: Optional[str] = None
    cost: Optional[float] = None
    latency: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GeneratedQuery:
    """
    A SPARQL query generated by the system.

    Attributes:
        query: The SPARQL query string
        natural_language: The original natural language question
        explanation: Explanation of the query logic
        confidence: Confidence score (0-1)
        used_ontology: Whether ontology information was used
        ontology_classes: OWL classes used in the query
        ontology_properties: OWL properties used in the query
        fallback_reason: Reason if this is a fallback query
        alternatives: Alternative query formulations
        validation_errors: Any validation errors found
        metadata: Additional generation metadata
    """
    query: str
    natural_language: str
    explanation: Optional[str] = None
    confidence: float = 1.0
    used_ontology: bool = False
    ontology_classes: List[str] = field(default_factory=list)
    ontology_properties: List[str] = field(default_factory=list)
    fallback_reason: Optional[str] = None
    alternatives: List[str] = field(default_factory=list)
    validation_errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FormattedResult:
    """
    Formatted query result for presentation.

    Attributes:
        format_type: Type of formatting (table, json, markdown, etc.)
        content: The formatted content
        original_result: The original QueryResult
        summary: Human-readable summary of the results
        visualizations: List of visualization suggestions
        metadata: Additional formatting metadata
    """
    format_type: str
    content: str
    original_result: QueryResult
    summary: Optional[str] = None
    visualizations: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
