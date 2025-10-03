"""
Schema Inference from RDF Data

This module provides intelligent ShEx schema generation from RDF data patterns,
using statistical analysis and pattern recognition to infer constraints, cardinalities,
and shape hierarchies with quality metrics.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any, Union
from collections import defaultdict, Counter
from enum import Enum
from urllib.parse import urlparse
import statistics as stats

from .shex_parser import (
    ShExSchema, Shape, TripleConstraint, ValueSet, Cardinality, NodeKind
)


logger = logging.getLogger(__name__)


class ConstraintConfidence(Enum):
    """Confidence levels for inferred constraints."""
    HIGH = "high"      # > 90% pattern match
    MEDIUM = "medium"  # 70-90% pattern match
    LOW = "low"        # 50-70% pattern match
    UNCERTAIN = "uncertain"  # < 50% pattern match


@dataclass
class PropertyStats:
    """Statistical information about a property."""
    uri: str
    usage_count: int = 0
    subject_count: int = 0  # Distinct subjects
    object_count: int = 0   # Distinct objects

    # Value analysis
    value_types: Counter = field(default_factory=Counter)
    datatypes: Counter = field(default_factory=Counter)
    languages: Counter = field(default_factory=Counter)

    # Cardinality tracking
    subjects_with_property: Set[str] = field(default_factory=set)
    values_per_subject: List[int] = field(default_factory=list)
    subjects_per_value: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    # Domain/Range
    subject_types: Counter = field(default_factory=Counter)
    object_types: Counter = field(default_factory=Counter)

    # Value patterns
    sample_values: List[Any] = field(default_factory=list)
    numeric_values: List[float] = field(default_factory=list)
    string_patterns: Counter = field(default_factory=Counter)

    # Quality metrics
    null_count: int = 0
    malformed_count: int = 0

    def add_value(self, subject: str, obj: Any, obj_type: str,
                  datatype: Optional[str] = None, lang: Optional[str] = None):
        """Record a property value occurrence."""
        self.usage_count += 1
        self.subjects_with_property.add(subject)
        self.value_types[obj_type] += 1

        if datatype:
            self.datatypes[datatype] += 1
        if lang:
            self.languages[lang] += 1

        # Track for cardinality inference
        if obj:
            self.subjects_per_value[str(obj)] += 1
        else:
            self.null_count += 1

        # Store samples
        if len(self.sample_values) < 100:
            self.sample_values.append(obj)

        # Track numeric values
        if obj_type in ['integer', 'float', 'decimal']:
            try:
                self.numeric_values.append(float(obj))
            except (ValueError, TypeError):
                self.malformed_count += 1

    def finalize_stats(self):
        """Calculate derived statistics after data collection."""
        # Calculate values per subject distribution
        subject_value_counts = defaultdict(int)
        for subj in self.subjects_with_property:
            # This would need to be tracked during collection
            # For now, estimate from usage patterns
            pass

        self.subject_count = len(self.subjects_with_property)
        self.object_count = len(self.subjects_per_value)


@dataclass
class ClassStats:
    """Statistical information about a class."""
    uri: str
    instance_count: int = 0
    instances: Set[str] = field(default_factory=set)

    # Property usage within this class
    properties: Set[str] = field(default_factory=set)
    property_usage: Counter = field(default_factory=Counter)
    optional_properties: Set[str] = field(default_factory=set)
    required_properties: Set[str] = field(default_factory=set)

    # Inheritance
    super_classes: Set[str] = field(default_factory=set)
    sub_classes: Set[str] = field(default_factory=set)

    # Patterns
    uri_patterns: Set[str] = field(default_factory=set)

    def add_instance(self, instance_uri: str):
        """Record an instance of this class."""
        self.instances.add(instance_uri)
        self.instance_count = len(self.instances)

    def add_property_usage(self, property_uri: str):
        """Record property usage in this class."""
        self.properties.add(property_uri)
        self.property_usage[property_uri] += 1


@dataclass
class InferredConstraint:
    """An inferred constraint with confidence metrics."""
    constraint_type: str
    value: Any
    confidence: ConstraintConfidence
    support: int  # Number of instances supporting this constraint
    counter_examples: int  # Number of violations
    explanation: str

    def confidence_score(self) -> float:
        """Calculate numeric confidence score."""
        if self.support + self.counter_examples == 0:
            return 0.0
        return self.support / (self.support + self.counter_examples)


@dataclass
class QualityMetrics:
    """Quality metrics for inferred schema."""
    coverage: float = 0.0  # % of data covered by schema
    constraint_confidence: float = 0.0  # Average constraint confidence
    completeness: float = 0.0  # % of properties captured
    consistency: float = 0.0  # % of data that validates

    # Detailed metrics
    total_instances: int = 0
    covered_instances: int = 0
    total_properties: int = 0
    covered_properties: int = 0
    validation_errors: List[str] = field(default_factory=list)

    def calculate_metrics(self):
        """Calculate derived metrics."""
        if self.total_instances > 0:
            self.coverage = self.covered_instances / self.total_instances
        if self.total_properties > 0:
            self.completeness = self.covered_properties / self.total_properties


@dataclass
class SchemaInferenceResult:
    """Result of schema inference process."""
    schema: ShExSchema
    property_stats: Dict[str, PropertyStats]
    class_stats: Dict[str, ClassStats]
    constraints: Dict[str, List[InferredConstraint]]
    quality_metrics: QualityMetrics
    warnings: List[str] = field(default_factory=list)
    inference_metadata: Dict[str, Any] = field(default_factory=dict)


class SchemaInferencer:
    """
    Intelligent ShEx schema generation from RDF data.

    Features:
    - Statistical property analysis
    - Cardinality inference with confidence scores
    - Optional vs required property detection
    - Value constraint generation
    - Shape hierarchy inference
    - Data quality assessment

    Example:
        >>> inferencer = SchemaInferencer()
        >>> inferencer.add_triple(subject, predicate, obj, subject_type)
        >>> result = inferencer.generate_schema()
        >>> print(result.schema)
    """

    def __init__(
        self,
        min_confidence: float = 0.7,
        cardinality_threshold: float = 0.9,
        optional_threshold: float = 0.8,
        max_samples: int = 1000
    ):
        """
        Initialize schema inferencer.

        Args:
            min_confidence: Minimum confidence for including constraints
            cardinality_threshold: Threshold for inferring cardinality (% consistency)
            optional_threshold: Threshold for marking properties as optional
            max_samples: Maximum samples to collect per property
        """
        self.min_confidence = min_confidence
        self.cardinality_threshold = cardinality_threshold
        self.optional_threshold = optional_threshold
        self.max_samples = max_samples

        # Statistics collection
        self.property_stats: Dict[str, PropertyStats] = {}
        self.class_stats: Dict[str, ClassStats] = {}

        # Raw data tracking
        self.triples: List[Tuple[str, str, Any, Optional[str]]] = []
        self.type_assertions: Dict[str, Set[str]] = defaultdict(set)
        self.instance_properties: Dict[str, Set[str]] = defaultdict(set)

        # Pattern recognition
        self.uri_patterns: Dict[str, int] = Counter()
        self.namespace_map: Dict[str, str] = {}

        # Quality tracking
        self.warnings: List[str] = []

    def add_triple(
        self,
        subject: str,
        predicate: str,
        obj: Any,
        subject_type: Optional[str] = None,
        object_type: Optional[str] = None,
        datatype: Optional[str] = None,
        language: Optional[str] = None
    ):
        """
        Add a triple for analysis.

        Args:
            subject: Subject URI
            predicate: Predicate URI
            obj: Object value (URI or literal)
            subject_type: Type of subject (rdf:type)
            object_type: Type of object
            datatype: XSD datatype for literals
            language: Language tag for literals
        """
        # Handle rdf:type specially
        if predicate in ['http://www.w3.org/1999/02/22-rdf-syntax-ns#type',
                         'rdf:type', 'a']:
            self.type_assertions[subject].add(obj)
            if obj not in self.class_stats:
                self.class_stats[obj] = ClassStats(uri=obj)
            self.class_stats[obj].add_instance(subject)
            return

        # Track property usage
        if predicate not in self.property_stats:
            self.property_stats[predicate] = PropertyStats(uri=predicate)

        # Infer types
        obj_type = self._infer_value_type(obj, datatype)

        # Update statistics
        self.property_stats[predicate].add_value(
            subject, obj, obj_type, datatype, language
        )

        # Track subject types
        if subject_type:
            self.property_stats[predicate].subject_types[subject_type] += 1
            if subject_type in self.class_stats:
                self.class_stats[subject_type].add_property_usage(predicate)
            self.instance_properties[subject].add(predicate)

        # Track object types for URIs
        if object_type:
            self.property_stats[predicate].object_types[object_type] += 1
        elif obj_type == 'iri':
            # Try to infer from data
            inferred_type = self._infer_type_from_uri(obj)
            if inferred_type:
                self.property_stats[predicate].object_types[inferred_type] += 1

        # Store triple
        self.triples.append((subject, predicate, obj, subject_type))

        # Extract namespaces
        self._extract_namespace(predicate)
        if isinstance(obj, str) and self._is_uri(obj):
            self._extract_namespace(obj)

    def add_triples_from_query_result(self, bindings: List[Dict[str, Any]]):
        """
        Add triples from SPARQL query result bindings.

        Args:
            bindings: List of variable bindings from SPARQL result
        """
        for binding in bindings:
            subject = binding.get('s', {}).get('value')
            predicate = binding.get('p', {}).get('value')
            obj_binding = binding.get('o', {})
            obj = obj_binding.get('value')

            if not (subject and predicate and obj):
                continue

            obj_type = obj_binding.get('type')
            datatype = obj_binding.get('datatype')
            language = obj_binding.get('xml:lang')

            # Get subject type if available
            subject_type = binding.get('type', {}).get('value')

            self.add_triple(subject, predicate, obj, subject_type,
                          obj_type=obj_type, datatype=datatype, language=language)

    def generate_schema(
        self,
        base_uri: Optional[str] = None,
        include_examples: bool = True,
        generate_hierarchy: bool = True
    ) -> SchemaInferenceResult:
        """
        Generate ShEx schema from collected data.

        Args:
            base_uri: Base URI for schema
            include_examples: Include example values in comments
            generate_hierarchy: Generate shape inheritance

        Returns:
            SchemaInferenceResult with schema and metrics
        """
        logger.info(f"Generating schema from {len(self.triples)} triples")

        # Finalize statistics
        self._finalize_statistics()

        # Create schema
        schema = ShExSchema(base=base_uri)

        # Add namespaces
        for prefix, uri in self.namespace_map.items():
            schema.add_prefix(prefix, uri)

        # Generate shapes for each class
        constraints_map: Dict[str, List[InferredConstraint]] = {}

        for class_uri, class_stats in self.class_stats.items():
            if class_stats.instance_count == 0:
                continue

            shape, constraints = self._generate_shape(class_uri, class_stats)
            schema.add_shape(shape)
            constraints_map[class_uri] = constraints

            # Detect hierarchy
            if generate_hierarchy:
                self._infer_hierarchy(class_stats)

        # Calculate quality metrics
        quality = self._calculate_quality_metrics()

        # Build result
        result = SchemaInferenceResult(
            schema=schema,
            property_stats=self.property_stats,
            class_stats=self.class_stats,
            constraints=constraints_map,
            quality_metrics=quality,
            warnings=self.warnings,
            inference_metadata={
                'total_triples': len(self.triples),
                'num_classes': len(self.class_stats),
                'num_properties': len(self.property_stats),
                'num_instances': sum(cs.instance_count for cs in self.class_stats.values())
            }
        )

        logger.info(f"Generated schema with {len(schema.shapes)} shapes")
        return result

    def _generate_shape(
        self,
        class_uri: str,
        class_stats: ClassStats
    ) -> Tuple[Shape, List[InferredConstraint]]:
        """Generate a shape for a class."""
        shape_id = self._uri_to_shape_id(class_uri)
        shape = Shape(id=shape_id)
        constraints: List[InferredConstraint] = []

        # Determine which properties to include
        for property_uri in class_stats.properties:
            if property_uri not in self.property_stats:
                continue

            prop_stats = self.property_stats[property_uri]

            # Calculate coverage for this class
            usage_in_class = class_stats.property_usage[property_uri]
            coverage = usage_in_class / class_stats.instance_count

            # Generate constraint with cardinality
            constraint, prop_constraints = self._generate_constraint(
                property_uri, prop_stats, coverage
            )

            shape.add_constraint(constraint)
            constraints.extend(prop_constraints)

        return shape, constraints

    def _generate_constraint(
        self,
        property_uri: str,
        prop_stats: PropertyStats,
        coverage: float
    ) -> Tuple[TripleConstraint, List[InferredConstraint]]:
        """Generate a triple constraint with inferred properties."""
        constraint = TripleConstraint(predicate=property_uri)
        inferred_constraints: List[InferredConstraint] = []

        # Infer cardinality
        cardinality, card_constraint = self._infer_cardinality(prop_stats, coverage)
        constraint.cardinality = cardinality
        if card_constraint:
            inferred_constraints.append(card_constraint)

        # Infer value type
        value_expr, node_kind, datatype = self._infer_value_constraint(prop_stats)

        if node_kind:
            constraint.node_kind = node_kind
        if datatype:
            constraint.datatype = datatype
        if value_expr:
            constraint.value_expr = value_expr

        # Infer numeric constraints
        if prop_stats.numeric_values:
            numeric_constraints = self._infer_numeric_constraints(prop_stats)
            inferred_constraints.extend(numeric_constraints)

            if numeric_constraints:
                # Apply to constraint
                for nc in numeric_constraints:
                    if nc.constraint_type == 'min_inclusive':
                        constraint.min_inclusive = nc.value
                    elif nc.constraint_type == 'max_inclusive':
                        constraint.max_inclusive = nc.value

        # Infer string patterns
        if prop_stats.string_patterns:
            pattern_constraint = self._infer_string_pattern(prop_stats)
            if pattern_constraint:
                inferred_constraints.append(pattern_constraint)
                if pattern_constraint.confidence != ConstraintConfidence.LOW:
                    constraint.pattern = pattern_constraint.value

        return constraint, inferred_constraints

    def _infer_cardinality(
        self,
        prop_stats: PropertyStats,
        coverage: float
    ) -> Tuple[Cardinality, Optional[InferredConstraint]]:
        """
        Infer cardinality for a property.

        Returns tuple of (Cardinality, InferredConstraint with confidence)
        """
        # Check if optional or required based on coverage
        is_optional = coverage < self.optional_threshold

        # Check if multi-valued
        avg_values_per_subject = prop_stats.usage_count / max(prop_stats.subject_count, 1)
        is_multi = avg_values_per_subject > 1.2  # Allow some margin

        # Determine cardinality
        if is_optional:
            if is_multi:
                cardinality = Cardinality.ZERO_OR_MORE
            else:
                cardinality = Cardinality.ZERO_OR_ONE
        else:
            if is_multi:
                cardinality = Cardinality.ONE_OR_MORE
            else:
                cardinality = Cardinality.EXACTLY_ONE

        # Calculate confidence
        if coverage >= 0.95:
            confidence = ConstraintConfidence.HIGH
        elif coverage >= 0.8:
            confidence = ConstraintConfidence.MEDIUM
        elif coverage >= 0.6:
            confidence = ConstraintConfidence.LOW
        else:
            confidence = ConstraintConfidence.UNCERTAIN

        constraint = InferredConstraint(
            constraint_type='cardinality',
            value=cardinality.value,
            confidence=confidence,
            support=int(coverage * 100),
            counter_examples=int((1 - coverage) * 100),
            explanation=f"Coverage: {coverage:.1%}, Avg values: {avg_values_per_subject:.2f}"
        )

        return cardinality, constraint

    def _infer_value_constraint(
        self,
        prop_stats: PropertyStats
    ) -> Tuple[Optional[ValueSet], Optional[NodeKind], Optional[str]]:
        """Infer value type constraints."""
        # Get most common value type
        if not prop_stats.value_types:
            return None, None, None

        most_common_type, count = prop_stats.value_types.most_common(1)[0]
        total = sum(prop_stats.value_types.values())
        confidence_ratio = count / total

        # If highly consistent type, use it
        if confidence_ratio >= self.cardinality_threshold:
            if most_common_type in ['uri', 'iri']:
                # Check if we should use a value set
                if len(prop_stats.object_types) <= 10 and confidence_ratio > 0.95:
                    value_set = ValueSet()
                    for obj_type in prop_stats.object_types:
                        value_set.add_value(obj_type, 'iri')
                    return value_set, None, None
                else:
                    return None, NodeKind.IRI, None

            elif most_common_type == 'literal':
                # Check for specific datatype
                if prop_stats.datatypes:
                    most_common_dt, dt_count = prop_stats.datatypes.most_common(1)[0]
                    if dt_count / total >= self.cardinality_threshold:
                        return None, None, most_common_dt
                return None, NodeKind.LITERAL, None

            elif most_common_type in ['integer', 'float', 'decimal']:
                datatype_map = {
                    'integer': 'xsd:integer',
                    'float': 'xsd:float',
                    'decimal': 'xsd:decimal'
                }
                return None, None, datatype_map.get(most_common_type, 'xsd:decimal')

            elif most_common_type in ['date', 'datetime']:
                datatype = 'xsd:dateTime' if most_common_type == 'datetime' else 'xsd:date'
                return None, None, datatype

            elif most_common_type == 'boolean':
                return None, None, 'xsd:boolean'

            else:  # string
                return None, None, 'xsd:string'

        return None, None, None

    def _infer_numeric_constraints(
        self,
        prop_stats: PropertyStats
    ) -> List[InferredConstraint]:
        """Infer numeric range constraints."""
        constraints = []

        if not prop_stats.numeric_values:
            return constraints

        values = prop_stats.numeric_values
        min_val = min(values)
        max_val = max(values)
        mean_val = stats.mean(values)

        # Check if all values are non-negative (common constraint)
        if min_val >= 0:
            constraints.append(InferredConstraint(
                constraint_type='min_inclusive',
                value=0,
                confidence=ConstraintConfidence.HIGH,
                support=len(values),
                counter_examples=0,
                explanation="All observed values are non-negative"
            ))

        # If tight range, include bounds
        value_range = max_val - min_val
        if value_range > 0:
            std_dev = stats.stdev(values) if len(values) > 1 else 0
            # If standard deviation is small relative to range, suggest bounds
            if std_dev / value_range < 0.3:
                constraints.append(InferredConstraint(
                    constraint_type='min_inclusive',
                    value=min_val,
                    confidence=ConstraintConfidence.MEDIUM,
                    support=len(values),
                    counter_examples=0,
                    explanation=f"Min observed: {min_val}, tight distribution"
                ))
                constraints.append(InferredConstraint(
                    constraint_type='max_inclusive',
                    value=max_val,
                    confidence=ConstraintConfidence.MEDIUM,
                    support=len(values),
                    counter_examples=0,
                    explanation=f"Max observed: {max_val}, tight distribution"
                ))

        return constraints

    def _infer_string_pattern(
        self,
        prop_stats: PropertyStats
    ) -> Optional[InferredConstraint]:
        """Infer regex pattern for string values."""
        if not prop_stats.sample_values:
            return None

        # Analyze string samples
        string_samples = [str(v) for v in prop_stats.sample_values[:100]]

        # Common patterns
        patterns = {
            'email': (r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', 'email address'),
            'url': (r'^https?://[^\s]+$', 'URL'),
            'uuid': (r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$', 'UUID'),
            'date_iso': (r'^\d{4}-\d{2}-\d{2}$', 'ISO date'),
            'phone': (r'^\+?[\d\s\-\(\)]+$', 'phone number'),
            'numeric': (r'^\d+(\.\d+)?$', 'numeric string'),
        }

        for pattern_name, (regex, description) in patterns.items():
            matches = sum(1 for s in string_samples if re.match(regex, s))
            if matches / len(string_samples) >= 0.9:
                return InferredConstraint(
                    constraint_type='pattern',
                    value=regex,
                    confidence=ConstraintConfidence.HIGH,
                    support=matches,
                    counter_examples=len(string_samples) - matches,
                    explanation=f"Values match {description} pattern"
                )

        return None

    def _finalize_statistics(self):
        """Finalize statistics after all data is collected."""
        for prop_stats in self.property_stats.values():
            prop_stats.finalize_stats()

        # Determine required vs optional properties for each class
        for class_uri, class_stats in self.class_stats.items():
            for property_uri in class_stats.properties:
                usage = class_stats.property_usage[property_uri]
                coverage = usage / class_stats.instance_count

                if coverage >= self.optional_threshold:
                    class_stats.required_properties.add(property_uri)
                else:
                    class_stats.optional_properties.add(property_uri)

    def _infer_hierarchy(self, class_stats: ClassStats):
        """Infer class hierarchy from property overlap."""
        # Find super classes based on property subset relationships
        for other_uri, other_stats in self.class_stats.items():
            if other_uri == class_stats.uri:
                continue

            # If this class has all properties of another + more,
            # the other might be a superclass
            if (other_stats.properties.issubset(class_stats.properties) and
                len(other_stats.properties) < len(class_stats.properties)):
                class_stats.super_classes.add(other_uri)
                other_stats.sub_classes.add(class_stats.uri)

    def _calculate_quality_metrics(self) -> QualityMetrics:
        """Calculate schema quality metrics."""
        metrics = QualityMetrics()

        # Count totals
        metrics.total_instances = sum(cs.instance_count for cs in self.class_stats.values())
        metrics.total_properties = len(self.property_stats)

        # Coverage: % of instances that have a type
        typed_instances = len(self.type_assertions)
        metrics.covered_instances = typed_instances

        # Completeness: all discovered properties are in shapes
        covered_props = set()
        for class_stats in self.class_stats.values():
            covered_props.update(class_stats.properties)
        metrics.covered_properties = len(covered_props)

        # Calculate derived metrics
        metrics.calculate_metrics()

        # Constraint confidence: average across all constraints
        all_confidences = []
        for prop_stats in self.property_stats.values():
            if prop_stats.usage_count > 0:
                # Simplified: use type consistency as proxy
                if prop_stats.value_types:
                    most_common_count = prop_stats.value_types.most_common(1)[0][1]
                    confidence = most_common_count / prop_stats.usage_count
                    all_confidences.append(confidence)

        if all_confidences:
            metrics.constraint_confidence = sum(all_confidences) / len(all_confidences)

        # Consistency: check for quality issues
        for prop_stats in self.property_stats.values():
            if prop_stats.malformed_count > 0:
                error_rate = prop_stats.malformed_count / prop_stats.usage_count
                if error_rate > 0.05:  # More than 5% errors
                    metrics.validation_errors.append(
                        f"{prop_stats.uri}: {error_rate:.1%} malformed values"
                    )

        return metrics

    def _infer_value_type(self, value: Any, datatype: Optional[str] = None) -> str:
        """Infer the type of a value."""
        if datatype:
            if 'integer' in datatype.lower() or 'int' in datatype.lower():
                return 'integer'
            elif 'float' in datatype.lower() or 'double' in datatype.lower():
                return 'float'
            elif 'decimal' in datatype.lower():
                return 'decimal'
            elif 'boolean' in datatype.lower():
                return 'boolean'
            elif 'date' in datatype.lower():
                return 'datetime' if 'time' in datatype.lower() else 'date'
            elif 'string' in datatype.lower():
                return 'string'

        # Infer from value
        if isinstance(value, bool):
            return 'boolean'
        elif isinstance(value, int):
            return 'integer'
        elif isinstance(value, float):
            return 'float'
        elif isinstance(value, str):
            if self._is_uri(value):
                return 'iri'
            else:
                return 'string'

        return 'literal'

    def _is_uri(self, value: str) -> bool:
        """Check if a string is a URI."""
        if not isinstance(value, str):
            return False

        # Check for common URI patterns
        if value.startswith(('http://', 'https://', 'ftp://', 'urn:')):
            return True

        # Check if it has a scheme
        try:
            result = urlparse(value)
            return bool(result.scheme and (result.netloc or result.path))
        except:
            return False

    def _infer_type_from_uri(self, uri: str) -> Optional[str]:
        """Try to infer type from URI pattern."""
        # Common patterns
        if '/protein/' in uri.lower() or uri.endswith('/protein'):
            return 'Protein'
        elif '/gene/' in uri.lower() or uri.endswith('/gene'):
            return 'Gene'
        elif '/organism/' in uri.lower() or '/taxon/' in uri.lower():
            return 'Organism'

        # Try to extract from last path segment
        parts = uri.rstrip('/').split('/')
        if len(parts) >= 2:
            potential_type = parts[-2].title()
            if potential_type and not potential_type[0].isdigit():
                return potential_type

        return None

    def _extract_namespace(self, uri: str):
        """Extract namespace from URI."""
        if not self._is_uri(uri):
            return

        # Extract namespace
        if '#' in uri:
            namespace = uri.rsplit('#', 1)[0] + '#'
            prefix = self._suggest_prefix(namespace)
        else:
            namespace = uri.rsplit('/', 1)[0] + '/'
            prefix = self._suggest_prefix(namespace)

        if prefix and prefix not in self.namespace_map:
            self.namespace_map[prefix] = namespace

    def _suggest_prefix(self, namespace: str) -> str:
        """Suggest a prefix for a namespace."""
        # Common namespaces
        common_prefixes = {
            'http://www.w3.org/1999/02/22-rdf-syntax-ns#': 'rdf',
            'http://www.w3.org/2000/01/rdf-schema#': 'rdfs',
            'http://www.w3.org/2001/XMLSchema#': 'xsd',
            'http://www.w3.org/2002/07/owl#': 'owl',
            'http://purl.org/dc/terms/': 'dcterms',
            'http://purl.org/dc/elements/1.1/': 'dc',
            'http://xmlns.com/foaf/0.1/': 'foaf',
            'http://www.w3.org/2004/02/skos/core#': 'skos',
            'http://purl.uniprot.org/core/': 'up',
        }

        if namespace in common_prefixes:
            return common_prefixes[namespace]

        # Extract from domain or path
        try:
            parsed = urlparse(namespace)
            domain = parsed.netloc.replace('www.', '').split('.')[0]
            if domain and len(domain) <= 10:
                return domain

            # Try last path segment
            path_parts = [p for p in parsed.path.split('/') if p]
            if path_parts:
                return path_parts[-1].rstrip('#')[:10].lower()
        except:
            pass

        return f"ns{len(self.namespace_map)}"

    def _uri_to_shape_id(self, uri: str) -> str:
        """Convert a class URI to a shape ID."""
        # Extract local name
        if '#' in uri:
            local_name = uri.split('#')[-1]
        else:
            local_name = uri.split('/')[-1]

        # Make it a shape name
        if not local_name.endswith('Shape'):
            local_name += 'Shape'

        return f"<{local_name}>"


def infer_schema_from_sparql(
    endpoint_url: str,
    query: Optional[str] = None,
    limit: int = 1000,
    **kwargs
) -> SchemaInferenceResult:
    """
    Convenience function to infer schema directly from SPARQL endpoint.

    Args:
        endpoint_url: SPARQL endpoint URL
        query: Optional custom query (default: SELECT * with types)
        limit: Result limit
        **kwargs: Additional arguments for SchemaInferencer

    Returns:
        SchemaInferenceResult
    """
    from SPARQLWrapper import SPARQLWrapper, JSON

    inferencer = SchemaInferencer(**kwargs)

    # Default query: get all triples with types
    if not query:
        query = f"""
        SELECT ?s ?type ?p ?o
        WHERE {{
            ?s a ?type .
            ?s ?p ?o .
        }}
        LIMIT {limit}
        """

    # Execute query
    sparql = SPARQLWrapper(endpoint_url)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)

    try:
        results = sparql.query().convert()
        inferencer.add_triples_from_query_result(results['results']['bindings'])
        return inferencer.generate_schema()
    except Exception as e:
        logger.error(f"Failed to query endpoint: {e}")
        raise


# Export public API
__all__ = [
    'SchemaInferencer',
    'SchemaInferenceResult',
    'PropertyStats',
    'ClassStats',
    'InferredConstraint',
    'QualityMetrics',
    'ConstraintConfidence',
    'infer_schema_from_sparql',
]
