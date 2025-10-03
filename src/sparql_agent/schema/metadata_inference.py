"""
Metadata Inference Module for SPARQL Datasets

This module provides automatic schema discovery and metadata inference from SPARQL queries
and data patterns using ML-inspired pattern recognition techniques.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Optional, Any
from collections import defaultdict, Counter
from enum import Enum
import re
from urllib.parse import urlparse
import statistics


class DataType(Enum):
    """Inferred data types"""
    URI = "uri"
    LITERAL = "literal"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    STRING = "string"
    LANGUAGE_STRING = "language_string"
    UNKNOWN = "unknown"


class CardinalityType(Enum):
    """Cardinality constraints"""
    ONE_TO_ONE = "1:1"
    ONE_TO_MANY = "1:N"
    MANY_TO_ONE = "N:1"
    MANY_TO_MANY = "N:N"


@dataclass
class PropertyMetadata:
    """Metadata about a discovered property"""
    uri: str
    label: Optional[str] = None
    usage_count: int = 0
    domains: Counter = field(default_factory=Counter)  # Subject types
    ranges: Counter = field(default_factory=Counter)  # Object types
    data_types: Counter = field(default_factory=Counter)
    cardinality: Optional[CardinalityType] = None
    is_functional: bool = False  # One value per subject
    is_inverse_functional: bool = False  # One subject per value
    sample_values: List[Any] = field(default_factory=list)
    value_patterns: Set[str] = field(default_factory=set)
    quality_score: float = 1.0
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    avg_value: Optional[float] = None


@dataclass
class ClassMetadata:
    """Metadata about a discovered class"""
    uri: str
    label: Optional[str] = None
    instance_count: int = 0
    properties: Set[str] = field(default_factory=set)
    super_classes: Set[str] = field(default_factory=set)
    sub_classes: Set[str] = field(default_factory=set)
    sample_instances: List[str] = field(default_factory=list)
    uri_patterns: Set[str] = field(default_factory=set)


@dataclass
class URIPattern:
    """Discovered URI pattern"""
    pattern: str
    regex: str
    examples: List[str]
    frequency: int
    associated_types: Set[str] = field(default_factory=set)


@dataclass
class Relationship:
    """Discovered implicit relationship"""
    subject_type: str
    predicate: str
    object_type: str
    confidence: float
    examples: List[Tuple[str, str, str]]


@dataclass
class DataQualityIssue:
    """Data quality issue discovered during inference"""
    issue_type: str
    severity: str  # "low", "medium", "high"
    description: str
    affected_properties: List[str]
    sample_cases: List[str]
    recommendation: str


@dataclass
class InferredMetadata:
    """Complete inferred metadata for a dataset"""
    classes: Dict[str, ClassMetadata] = field(default_factory=dict)
    properties: Dict[str, PropertyMetadata] = field(default_factory=dict)
    uri_patterns: List[URIPattern] = field(default_factory=list)
    relationships: List[Relationship] = field(default_factory=list)
    namespaces: Dict[str, str] = field(default_factory=dict)
    quality_issues: List[DataQualityIssue] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)


class MetadataInferencer:
    """
    Analyzes SPARQL queries and sample data to infer dataset schema and metadata.

    Uses ML-inspired pattern recognition to discover:
    - Classes and their hierarchies
    - Properties and their domains/ranges
    - Cardinality constraints
    - URI patterns
    - Implicit relationships
    - Data quality issues
    """

    def __init__(self, min_confidence: float = 0.7, max_samples: int = 1000):
        """
        Initialize the metadata inferencer.

        Args:
            min_confidence: Minimum confidence threshold for inferences
            max_samples: Maximum number of sample values to store per property
        """
        self.min_confidence = min_confidence
        self.max_samples = max_samples
        self.metadata = InferredMetadata()

        # Pattern detection
        self.uri_pattern_cache: Dict[str, List[str]] = defaultdict(list)
        self.type_inference_cache: Dict[str, str] = {}

        # Statistical tracking
        self.subject_property_counts: Dict[Tuple[str, str], int] = defaultdict(int)
        self.property_object_counts: Dict[Tuple[str, str], int] = defaultdict(int)

    def analyze_triple(self, subject: str, predicate: str, obj: str,
                       subject_type: Optional[str] = None,
                       object_type: Optional[str] = None) -> None:
        """
        Analyze a single RDF triple to extract metadata.

        Args:
            subject: Subject URI
            predicate: Predicate URI
            obj: Object (URI or literal)
            subject_type: Known type of subject (optional)
            object_type: Known type of object (optional)
        """
        # Update property metadata
        if predicate not in self.metadata.properties:
            self.metadata.properties[predicate] = PropertyMetadata(uri=predicate)

        prop_meta = self.metadata.properties[predicate]
        prop_meta.usage_count += 1

        # Infer or record types
        if subject_type:
            prop_meta.domains[subject_type] += 1
            self._update_class_metadata(subject_type, predicate, subject)

        # Determine object type and update ranges
        inferred_obj_type = self._infer_data_type(obj)
        prop_meta.data_types[inferred_obj_type.value] += 1

        if object_type:
            prop_meta.ranges[object_type] += 1
            self._update_class_metadata(object_type, None, obj)
        elif inferred_obj_type == DataType.URI:
            # Try to infer type from URI pattern
            inferred_type = self._infer_type_from_uri(obj)
            if inferred_type:
                prop_meta.ranges[inferred_type] += 1

        # Store sample values (limited)
        if len(prop_meta.sample_values) < self.max_samples:
            prop_meta.sample_values.append(obj)

        # Track URI patterns
        if inferred_obj_type == DataType.URI:
            pattern = self._extract_uri_pattern(obj)
            if pattern:
                prop_meta.value_patterns.add(pattern)
                self.uri_pattern_cache[pattern].append(obj)

        # Track for cardinality inference
        self.subject_property_counts[(subject, predicate)] += 1
        self.property_object_counts[(predicate, obj)] += 1

        # Extract namespace
        self._extract_namespace(predicate)
        if self._is_uri(obj):
            self._extract_namespace(obj)

    def analyze_query(self, query: str, results: Optional[List[Dict[str, str]]] = None) -> None:
        """
        Analyze a SPARQL query to learn schema patterns.

        Args:
            query: SPARQL query string
            results: Optional query results to analyze
        """
        # Extract patterns from query structure
        patterns = self._extract_query_patterns(query)

        for pattern in patterns:
            subject, predicate, obj = pattern

            # Learn from query structure
            if self._is_variable(predicate):
                continue  # Skip variable predicates for now

            # Infer relationships from query patterns
            if self._is_variable(subject) and self._is_variable(obj):
                # This predicate connects two variables
                self._infer_relationship_from_pattern(pattern, query)

        # Analyze results if provided
        if results:
            self._analyze_query_results(patterns, results)

    def analyze_sample_data(self, triples: List[Tuple[str, str, str]],
                           type_map: Optional[Dict[str, List[str]]] = None) -> None:
        """
        Analyze a sample of triples to infer metadata.

        Args:
            triples: List of (subject, predicate, object) triples
            type_map: Optional mapping of resources to their types
        """
        # First pass: collect basic statistics
        for subject, predicate, obj in triples:
            subject_type = None
            object_type = None

            if type_map:
                subject_type = type_map.get(subject, [None])[0]
                if self._is_uri(obj):
                    object_type = type_map.get(obj, [None])[0]

            self.analyze_triple(subject, predicate, obj, subject_type, object_type)

        # Second pass: infer constraints and relationships
        self._infer_cardinality_constraints()
        self._infer_functional_properties()
        self._discover_implicit_relationships()
        self._detect_data_quality_issues()
        self._compute_statistics()
        self._consolidate_uri_patterns()

    def _update_class_metadata(self, class_uri: str, property_uri: Optional[str],
                               instance: str) -> None:
        """Update metadata for a class."""
        if class_uri not in self.metadata.classes:
            self.metadata.classes[class_uri] = ClassMetadata(uri=class_uri)

        class_meta = self.metadata.classes[class_uri]
        class_meta.instance_count += 1

        if property_uri:
            class_meta.properties.add(property_uri)

        if len(class_meta.sample_instances) < self.max_samples:
            class_meta.sample_instances.append(instance)

        # Track URI pattern
        pattern = self._extract_uri_pattern(instance)
        if pattern:
            class_meta.uri_patterns.add(pattern)

    def _infer_data_type(self, value: str) -> DataType:
        """Infer the data type of a value."""
        # Check if URI
        if self._is_uri(value):
            return DataType.URI

        # Check if integer
        try:
            int(value)
            return DataType.INTEGER
        except (ValueError, TypeError):
            pass

        # Check if float
        try:
            float(value)
            return DataType.FLOAT
        except (ValueError, TypeError):
            pass

        # Check if boolean
        if value.lower() in ('true', 'false', '1', '0'):
            return DataType.BOOLEAN

        # Check date patterns
        date_pattern = r'^\d{4}-\d{2}-\d{2}$'
        if re.match(date_pattern, value):
            return DataType.DATE

        datetime_pattern = r'^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}'
        if re.match(datetime_pattern, value):
            return DataType.DATETIME

        # Check for language-tagged strings
        if '@' in value and value.rfind('@') > value.rfind('"'):
            return DataType.LANGUAGE_STRING

        # Default to string
        return DataType.STRING

    def _is_uri(self, value: str) -> bool:
        """Check if a value is a URI."""
        try:
            result = urlparse(value)
            return bool(result.scheme and result.netloc)
        except:
            return False

    def _is_variable(self, value: str) -> bool:
        """Check if a value is a SPARQL variable."""
        return value.startswith('?') or value.startswith('$')

    def _extract_uri_pattern(self, uri: str) -> Optional[str]:
        """
        Extract a pattern from a URI by replacing specific components with placeholders.

        Example: http://example.org/person/123 -> http://example.org/person/{id}
        """
        if not self._is_uri(uri):
            return None

        # Replace numeric IDs
        pattern = re.sub(r'/\d+', '/{id}', uri)

        # Replace UUIDs
        uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
        pattern = re.sub(uuid_pattern, '{uuid}', pattern, flags=re.IGNORECASE)

        # Replace alphanumeric IDs (longer than 6 chars)
        pattern = re.sub(r'/[a-zA-Z0-9]{7,}', '/{code}', pattern)

        return pattern if pattern != uri else None

    def _infer_type_from_uri(self, uri: str) -> Optional[str]:
        """Infer the type of a resource from its URI pattern."""
        if uri in self.type_inference_cache:
            return self.type_inference_cache[uri]

        # Extract the path component
        parsed = urlparse(uri)
        path_parts = parsed.path.strip('/').split('/')

        if len(path_parts) >= 2:
            # Often the type is in the path: /type/id
            potential_type = path_parts[-2]

            # Construct a potential class URI
            base_uri = f"{parsed.scheme}://{parsed.netloc}"
            type_uri = f"{base_uri}/{potential_type}"

            self.type_inference_cache[uri] = type_uri
            return type_uri

        return None

    def _extract_namespace(self, uri: str) -> None:
        """Extract and store namespace from URI."""
        if not self._is_uri(uri):
            return

        parsed = urlparse(uri)

        # Try to extract namespace
        if '#' in uri:
            namespace = uri.rsplit('#', 1)[0] + '#'
            prefix = parsed.netloc.split('.')[0]
        elif '/' in parsed.path:
            # Use last path component as namespace boundary
            namespace = '/'.join(uri.rsplit('/', 1)[:-1]) + '/'
            prefix = parsed.path.strip('/').split('/')[0]
        else:
            return

        if namespace not in self.metadata.namespaces.values():
            self.metadata.namespaces[prefix] = namespace

    def _extract_query_patterns(self, query: str) -> List[Tuple[str, str, str]]:
        """Extract triple patterns from SPARQL query."""
        patterns = []

        # Simple pattern extraction (can be enhanced with full SPARQL parser)
        # Look for triple patterns in WHERE clause
        where_match = re.search(r'WHERE\s*\{(.*?)\}', query, re.IGNORECASE | re.DOTALL)
        if not where_match:
            return patterns

        where_clause = where_match.group(1)

        # Extract triples (simplified - doesn't handle all SPARQL syntax)
        triple_pattern = r'(\??\w+|<[^>]+>)\s+(\??\w+|<[^>]+>)\s+(\??\w+|<[^>]+>|"[^"]*")'
        matches = re.findall(triple_pattern, where_clause)

        for match in matches:
            subject, predicate, obj = match
            patterns.append((subject.strip(), predicate.strip(), obj.strip()))

        return patterns

    def _infer_relationship_from_pattern(self, pattern: Tuple[str, str, str],
                                        query: str) -> None:
        """Infer relationship from query pattern context."""
        subject, predicate, obj = pattern

        # Skip if predicate is a variable
        if self._is_variable(predicate):
            return

        # Look for type declarations in the query
        type_pattern = r'(\?\w+)\s+a\s+<([^>]+)>'
        type_matches = re.findall(type_pattern, query)

        type_map = {var: typ for var, typ in type_matches}

        subject_type = type_map.get(subject, "unknown")
        object_type = type_map.get(obj, "unknown")

        if subject_type != "unknown" or object_type != "unknown":
            relationship = Relationship(
                subject_type=subject_type,
                predicate=predicate,
                object_type=object_type,
                confidence=0.8,  # High confidence from explicit query
                examples=[]
            )

            # Check if relationship already exists
            existing = None
            for rel in self.metadata.relationships:
                if (rel.subject_type == subject_type and
                    rel.predicate == predicate and
                    rel.object_type == object_type):
                    existing = rel
                    break

            if existing:
                existing.confidence = min(1.0, existing.confidence + 0.1)
            else:
                self.metadata.relationships.append(relationship)

    def _analyze_query_results(self, patterns: List[Tuple[str, str, str]],
                               results: List[Dict[str, str]]) -> None:
        """Analyze query results to infer types and values."""
        for result in results:
            # Map variables to values
            for pattern in patterns:
                subject, predicate, obj = pattern

                if (self._is_variable(subject) and subject[1:] in result and
                    not self._is_variable(predicate) and
                    self._is_variable(obj) and obj[1:] in result):

                    subject_val = result[subject[1:]]
                    obj_val = result[obj[1:]]

                    self.analyze_triple(subject_val, predicate, obj_val)

    def _infer_cardinality_constraints(self) -> None:
        """Infer cardinality constraints for properties."""
        for predicate, prop_meta in self.metadata.properties.items():
            # Count subjects per object and objects per subject
            subjects_per_object = defaultdict(set)
            objects_per_subject = defaultdict(set)

            for (subj, pred), count in self.subject_property_counts.items():
                if pred == predicate:
                    objects_per_subject[subj].add(count)

            for (pred, obj), count in self.property_object_counts.items():
                if pred == predicate:
                    subjects_per_object[obj].add(count)

            # Compute average cardinalities
            avg_objects_per_subject = statistics.mean(
                [len(objs) for objs in objects_per_subject.values()]
            ) if objects_per_subject else 0

            avg_subjects_per_object = statistics.mean(
                [len(subjs) for subjs in subjects_per_object.values()]
            ) if subjects_per_object else 0

            # Infer cardinality type
            if avg_objects_per_subject <= 1.1 and avg_subjects_per_object <= 1.1:
                prop_meta.cardinality = CardinalityType.ONE_TO_ONE
            elif avg_objects_per_subject > 1.1 and avg_subjects_per_object <= 1.1:
                prop_meta.cardinality = CardinalityType.ONE_TO_MANY
            elif avg_objects_per_subject <= 1.1 and avg_subjects_per_object > 1.1:
                prop_meta.cardinality = CardinalityType.MANY_TO_ONE
            else:
                prop_meta.cardinality = CardinalityType.MANY_TO_MANY

    def _infer_functional_properties(self) -> None:
        """Infer which properties are functional or inverse functional."""
        for predicate, prop_meta in self.metadata.properties.items():
            # Check if functional (each subject has at most one value)
            subject_counts = defaultdict(int)
            object_counts = defaultdict(int)

            for (subj, pred), count in self.subject_property_counts.items():
                if pred == predicate:
                    subject_counts[subj] += count

            for (pred, obj), count in self.property_object_counts.items():
                if pred == predicate:
                    object_counts[obj] += count

            # Functional if >90% of subjects have exactly one value
            if subject_counts:
                functional_ratio = sum(1 for c in subject_counts.values() if c == 1) / len(subject_counts)
                prop_meta.is_functional = functional_ratio > 0.9

            # Inverse functional if >90% of objects appear with exactly one subject
            if object_counts:
                inv_functional_ratio = sum(1 for c in object_counts.values() if c == 1) / len(object_counts)
                prop_meta.is_inverse_functional = inv_functional_ratio > 0.9

    def _discover_implicit_relationships(self) -> None:
        """Discover implicit relationships through property co-occurrence."""
        # Group properties by subject type
        type_properties = defaultdict(set)

        for predicate, prop_meta in self.metadata.properties.items():
            for domain in prop_meta.domains:
                type_properties[domain].add(predicate)

        # Look for common patterns
        for class_uri, class_meta in self.metadata.classes.items():
            properties = class_meta.properties

            # Check property combinations
            for prop1 in properties:
                prop1_meta = self.metadata.properties[prop1]

                for prop2 in properties:
                    if prop1 == prop2:
                        continue

                    prop2_meta = self.metadata.properties[prop2]

                    # Check if prop1's range overlaps with prop2's domain
                    range_domain_overlap = set(prop1_meta.ranges.keys()) & set(prop2_meta.domains.keys())

                    if range_domain_overlap:
                        # Possible transitive relationship
                        confidence = len(range_domain_overlap) / max(
                            len(prop1_meta.ranges),
                            len(prop2_meta.domains)
                        )

                        if confidence >= self.min_confidence:
                            # Create an implicit relationship
                            for overlap_type in range_domain_overlap:
                                relationship = Relationship(
                                    subject_type=class_uri,
                                    predicate=f"{prop1}→{prop2}",
                                    object_type=overlap_type,
                                    confidence=confidence,
                                    examples=[]
                                )
                                self.metadata.relationships.append(relationship)

    def _detect_data_quality_issues(self) -> None:
        """Detect potential data quality issues."""
        for predicate, prop_meta in self.metadata.properties.items():
            # Check for missing values (low usage relative to domain instances)
            if prop_meta.domains:
                for domain, count in prop_meta.domains.items():
                    if domain in self.metadata.classes:
                        class_meta = self.metadata.classes[domain]
                        coverage = count / class_meta.instance_count

                        if coverage < 0.5:
                            issue = DataQualityIssue(
                                issue_type="incomplete_data",
                                severity="medium",
                                description=f"Property {predicate} is only used in {coverage*100:.1f}% of {domain} instances",
                                affected_properties=[predicate],
                                sample_cases=[],
                                recommendation=f"Consider if {predicate} should be mandatory for {domain}"
                            )
                            self.metadata.quality_issues.append(issue)

            # Check for inconsistent data types
            if len(prop_meta.data_types) > 2:
                issue = DataQualityIssue(
                    issue_type="inconsistent_types",
                    severity="high",
                    description=f"Property {predicate} has inconsistent data types: {list(prop_meta.data_types.keys())}",
                    affected_properties=[predicate],
                    sample_cases=prop_meta.sample_values[:5],
                    recommendation=f"Standardize data type for {predicate}"
                )
                self.metadata.quality_issues.append(issue)

            # Check for numeric properties and compute stats
            if DataType.INTEGER.value in prop_meta.data_types or DataType.FLOAT.value in prop_meta.data_types:
                numeric_values = []
                for val in prop_meta.sample_values:
                    try:
                        numeric_values.append(float(val))
                    except (ValueError, TypeError):
                        pass

                if numeric_values:
                    prop_meta.min_value = min(numeric_values)
                    prop_meta.max_value = max(numeric_values)
                    prop_meta.avg_value = statistics.mean(numeric_values)

                    # Check for outliers
                    if len(numeric_values) > 10:
                        std_dev = statistics.stdev(numeric_values)
                        mean = prop_meta.avg_value
                        outliers = [v for v in numeric_values if abs(v - mean) > 3 * std_dev]

                        if outliers:
                            issue = DataQualityIssue(
                                issue_type="outliers",
                                severity="low",
                                description=f"Property {predicate} has {len(outliers)} potential outliers",
                                affected_properties=[predicate],
                                sample_cases=[str(o) for o in outliers[:5]],
                                recommendation="Review outlier values for data entry errors"
                            )
                            self.metadata.quality_issues.append(issue)

    def _compute_statistics(self) -> None:
        """Compute overall dataset statistics."""
        self.metadata.statistics = {
            "total_classes": len(self.metadata.classes),
            "total_properties": len(self.metadata.properties),
            "total_instances": sum(c.instance_count for c in self.metadata.classes.values()),
            "total_relationships": len(self.metadata.relationships),
            "total_namespaces": len(self.metadata.namespaces),
            "total_quality_issues": len(self.metadata.quality_issues),
            "functional_properties": sum(1 for p in self.metadata.properties.values() if p.is_functional),
            "inverse_functional_properties": sum(1 for p in self.metadata.properties.values() if p.is_inverse_functional),
        }

    def _consolidate_uri_patterns(self) -> None:
        """Consolidate and rank URI patterns."""
        pattern_stats = defaultdict(lambda: {"count": 0, "examples": []})

        for pattern, uris in self.uri_pattern_cache.items():
            pattern_stats[pattern]["count"] = len(uris)
            pattern_stats[pattern]["examples"] = uris[:10]

        # Create URIPattern objects
        for pattern, stats in sorted(pattern_stats.items(),
                                     key=lambda x: x[1]["count"],
                                     reverse=True):
            # Convert pattern to regex
            regex = pattern.replace('{id}', r'\d+')
            regex = regex.replace('{uuid}', r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
            regex = regex.replace('{code}', r'[a-zA-Z0-9]+')

            uri_pattern = URIPattern(
                pattern=pattern,
                regex=regex,
                examples=stats["examples"],
                frequency=stats["count"]
            )

            self.metadata.uri_patterns.append(uri_pattern)

    def get_metadata(self) -> InferredMetadata:
        """Get the complete inferred metadata."""
        return self.metadata

    def get_property_info(self, property_uri: str) -> Optional[PropertyMetadata]:
        """Get metadata for a specific property."""
        return self.metadata.properties.get(property_uri)

    def get_class_info(self, class_uri: str) -> Optional[ClassMetadata]:
        """Get metadata for a specific class."""
        return self.metadata.classes.get(class_uri)

    def get_relationships_for_class(self, class_uri: str) -> List[Relationship]:
        """Get all relationships involving a specific class."""
        return [
            rel for rel in self.metadata.relationships
            if rel.subject_type == class_uri or rel.object_type == class_uri
        ]

    def generate_summary_report(self) -> str:
        """Generate a human-readable summary report of inferred metadata."""
        report = ["=" * 80]
        report.append("DATASET METADATA INFERENCE REPORT")
        report.append("=" * 80)
        report.append("")

        # Statistics
        report.append("STATISTICS")
        report.append("-" * 80)
        for key, value in self.metadata.statistics.items():
            report.append(f"  {key.replace('_', ' ').title()}: {value}")
        report.append("")

        # Namespaces
        report.append("NAMESPACES")
        report.append("-" * 80)
        for prefix, namespace in sorted(self.metadata.namespaces.items()):
            report.append(f"  {prefix}: {namespace}")
        report.append("")

        # Classes
        report.append("DISCOVERED CLASSES")
        report.append("-" * 80)
        for class_uri, class_meta in sorted(self.metadata.classes.items(),
                                           key=lambda x: x[1].instance_count,
                                           reverse=True)[:10]:
            report.append(f"  {class_uri}")
            report.append(f"    Instances: {class_meta.instance_count}")
            report.append(f"    Properties: {len(class_meta.properties)}")
            if class_meta.uri_patterns:
                report.append(f"    URI Patterns: {', '.join(list(class_meta.uri_patterns)[:3])}")
            report.append("")

        # Properties
        report.append("TOP PROPERTIES")
        report.append("-" * 80)
        for prop_uri, prop_meta in sorted(self.metadata.properties.items(),
                                         key=lambda x: x[1].usage_count,
                                         reverse=True)[:10]:
            report.append(f"  {prop_uri}")
            report.append(f"    Usage Count: {prop_meta.usage_count}")
            report.append(f"    Data Types: {list(prop_meta.data_types.keys())}")
            if prop_meta.cardinality:
                report.append(f"    Cardinality: {prop_meta.cardinality.value}")
            if prop_meta.is_functional:
                report.append(f"    Functional: Yes")
            if prop_meta.domains:
                report.append(f"    Domains: {list(prop_meta.domains.keys())[:3]}")
            if prop_meta.ranges:
                report.append(f"    Ranges: {list(prop_meta.ranges.keys())[:3]}")
            report.append("")

        # Relationships
        if self.metadata.relationships:
            report.append("DISCOVERED RELATIONSHIPS")
            report.append("-" * 80)
            for rel in sorted(self.metadata.relationships,
                            key=lambda x: x.confidence,
                            reverse=True)[:10]:
                report.append(f"  {rel.subject_type} --[{rel.predicate}]--> {rel.object_type}")
                report.append(f"    Confidence: {rel.confidence:.2f}")
                report.append("")

        # URI Patterns
        if self.metadata.uri_patterns:
            report.append("URI PATTERNS")
            report.append("-" * 80)
            for pattern in self.metadata.uri_patterns[:10]:
                report.append(f"  {pattern.pattern}")
                report.append(f"    Frequency: {pattern.frequency}")
                report.append(f"    Example: {pattern.examples[0] if pattern.examples else 'N/A'}")
                report.append("")

        # Quality Issues
        if self.metadata.quality_issues:
            report.append("DATA QUALITY ISSUES")
            report.append("-" * 80)
            for issue in self.metadata.quality_issues[:10]:
                report.append(f"  [{issue.severity.upper()}] {issue.issue_type}")
                report.append(f"    {issue.description}")
                report.append(f"    Recommendation: {issue.recommendation}")
                report.append("")

        report.append("=" * 80)

        return "\n".join(report)
