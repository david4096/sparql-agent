"""
Constraint Checking and Validation Rules for RDF Data

This module provides comprehensive validation of RDF data against ShEx shapes,
including constraint checking, cardinality validation, datatype verification,
and detailed error reporting with fix suggestions.

Example:
    >>> from sparql_agent.schema import ShExParser, ConstraintValidator
    >>>
    >>> schema_text = '''
    ... PREFIX ex: <http://example.org/>
    ... PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    ...
    ... <PersonShape> {
    ...   ex:name xsd:string,
    ...   ex:age xsd:integer MININCLUSIVE 0 MAXINCLUSIVE 150,
    ...   ex:email xsd:string PATTERN "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
    ... }
    ... '''
    >>>
    >>> parser = ShExParser()
    >>> schema = parser.parse(schema_text)
    >>> validator = ConstraintValidator(schema)
    >>>
    >>> person_data = {
    ...     "ex:name": "John Doe",
    ...     "ex:age": 30,
    ...     "ex:email": "john@example.com"
    ... }
    >>>
    >>> report = validator.validate(person_data, "<PersonShape>")
    >>> print(report)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Union, Set, Tuple
from urllib.parse import urlparse
import re
from datetime import datetime, date
from decimal import Decimal, InvalidOperation

from .shex_parser import (
    ShExSchema,
    Shape,
    TripleConstraint,
    ValueSet,
    ValueSetValue,
    Cardinality,
    NodeKind,
)


class ViolationType(Enum):
    """Types of constraint violations."""
    CARDINALITY = "cardinality"
    DATATYPE = "datatype"
    NODE_KIND = "node_kind"
    VALUE_SET = "value_set"
    NUMERIC_RANGE = "numeric_range"
    STRING_PATTERN = "string_pattern"
    STRING_LENGTH = "string_length"
    CLOSED_SHAPE = "closed_shape"
    REQUIRED_PROPERTY = "required_property"
    CROSS_REFERENCE = "cross_reference"
    URI_PATTERN = "uri_pattern"


class Severity(Enum):
    """Severity levels for validation violations."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ConstraintViolation:
    """
    Represents a single constraint violation.

    Attributes:
        violation_type: The type of constraint that was violated
        severity: How severe the violation is
        predicate: The predicate that caused the violation (if applicable)
        message: Human-readable description of the violation
        actual_value: The actual value that violated the constraint
        expected: Description of what was expected
        fix_suggestion: Suggested way to fix the violation
        path: JSON path to the problematic value
    """
    violation_type: ViolationType
    severity: Severity
    message: str
    predicate: Optional[str] = None
    actual_value: Optional[Any] = None
    expected: Optional[str] = None
    fix_suggestion: Optional[str] = None
    path: Optional[str] = None

    def __str__(self) -> str:
        """Format violation as a readable string."""
        parts = [f"[{self.severity.value.upper()}]"]

        if self.predicate:
            parts.append(f"{self.predicate}:")

        parts.append(self.message)

        if self.actual_value is not None:
            parts.append(f"(got: {self._format_value(self.actual_value)})")

        if self.expected:
            parts.append(f"(expected: {self.expected})")

        result = " ".join(parts)

        if self.fix_suggestion:
            result += f"\n  💡 Fix: {self.fix_suggestion}"

        return result

    def _format_value(self, value: Any) -> str:
        """Format a value for display."""
        if isinstance(value, str):
            if len(value) > 50:
                return f'"{value[:47]}..."'
            return f'"{value}"'
        elif isinstance(value, list):
            if len(value) > 3:
                return f"[{', '.join(map(str, value[:3]))}, ...] ({len(value)} items)"
            return str(value)
        return str(value)


@dataclass
class ValidationReport:
    """
    Comprehensive validation report with detailed error information.

    Attributes:
        is_valid: Whether the data passed validation
        shape_id: ID of the shape that was validated against
        node_id: ID of the node that was validated (if applicable)
        violations: List of all constraint violations
        warnings: List of warnings (non-critical issues)
        info_messages: List of informational messages
        validation_time: Time taken to validate (in seconds)
        checked_constraints: Number of constraints checked
    """
    is_valid: bool
    shape_id: str
    violations: List[ConstraintViolation] = field(default_factory=list)
    warnings: List[ConstraintViolation] = field(default_factory=list)
    info_messages: List[str] = field(default_factory=list)
    node_id: Optional[str] = None
    validation_time: Optional[float] = None
    checked_constraints: int = 0

    def add_violation(self, violation: ConstraintViolation):
        """Add a violation to the report."""
        if violation.severity == Severity.ERROR:
            self.violations.append(violation)
            self.is_valid = False
        elif violation.severity == Severity.WARNING:
            self.warnings.append(violation)

    def add_info(self, message: str):
        """Add an informational message."""
        self.info_messages.append(message)

    @property
    def error_count(self) -> int:
        """Get the number of errors."""
        return len(self.violations)

    @property
    def warning_count(self) -> int:
        """Get the number of warnings."""
        return len(self.warnings)

    @property
    def total_issues(self) -> int:
        """Get total number of issues (errors + warnings)."""
        return self.error_count + self.warning_count

    def __str__(self) -> str:
        """Format report as a readable string."""
        lines = []
        lines.append("=" * 70)
        lines.append(f"Validation Report for Shape: {self.shape_id}")
        if self.node_id:
            lines.append(f"Node: {self.node_id}")
        lines.append("=" * 70)

        if self.is_valid and not self.warnings:
            lines.append("✓ VALIDATION PASSED")
            lines.append(f"  Checked {self.checked_constraints} constraints")
        else:
            if self.violations:
                lines.append(f"✗ VALIDATION FAILED with {self.error_count} error(s)")
                lines.append("")
                lines.append("Errors:")
                lines.append("-" * 70)
                for i, violation in enumerate(self.violations, 1):
                    lines.append(f"{i}. {violation}")
                    lines.append("")

            if self.warnings:
                lines.append(f"⚠ {self.warning_count} warning(s) found")
                lines.append("")
                lines.append("Warnings:")
                lines.append("-" * 70)
                for i, warning in enumerate(self.warnings, 1):
                    lines.append(f"{i}. {warning}")
                    lines.append("")

        if self.info_messages:
            lines.append("Information:")
            lines.append("-" * 70)
            for msg in self.info_messages:
                lines.append(f"ℹ {msg}")

        if self.validation_time:
            lines.append("")
            lines.append(f"Validation completed in {self.validation_time:.3f}s")

        lines.append("=" * 70)
        return "\n".join(lines)

    def get_violations_by_type(self, violation_type: ViolationType) -> List[ConstraintViolation]:
        """Get all violations of a specific type."""
        return [v for v in self.violations if v.violation_type == violation_type]

    def get_violations_by_predicate(self, predicate: str) -> List[ConstraintViolation]:
        """Get all violations for a specific predicate."""
        return [v for v in self.violations if v.predicate == predicate]

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to a dictionary."""
        return {
            "is_valid": self.is_valid,
            "shape_id": self.shape_id,
            "node_id": self.node_id,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "violations": [
                {
                    "type": v.violation_type.value,
                    "severity": v.severity.value,
                    "predicate": v.predicate,
                    "message": v.message,
                    "actual_value": str(v.actual_value) if v.actual_value is not None else None,
                    "expected": v.expected,
                    "fix_suggestion": v.fix_suggestion,
                }
                for v in self.violations
            ],
            "warnings": [
                {
                    "type": v.violation_type.value,
                    "severity": v.severity.value,
                    "predicate": v.predicate,
                    "message": v.message,
                    "fix_suggestion": v.fix_suggestion,
                }
                for v in self.warnings
            ],
            "info_messages": self.info_messages,
            "checked_constraints": self.checked_constraints,
            "validation_time": self.validation_time,
        }


class ConstraintValidator:
    """
    Comprehensive validator for RDF data against ShEx shapes.

    This validator provides:
    - Cardinality constraint checking
    - Datatype validation with XSD type support
    - Value set validation with stem matching
    - Numeric range validation
    - String pattern and length validation
    - Closed/open shape validation
    - Cross-reference validation
    - URI pattern validation
    - User-friendly error messages with fix suggestions

    Example:
        >>> validator = ConstraintValidator(schema)
        >>> report = validator.validate(node_data, "<PersonShape>")
        >>> if not report.is_valid:
        ...     print(report)
    """

    def __init__(self, schema: ShExSchema):
        """
        Initialize the validator with a ShEx schema.

        Args:
            schema: A parsed ShExSchema object
        """
        self.schema = schema
        self._init_xsd_validators()

    def _init_xsd_validators(self):
        """Initialize XSD datatype validators."""
        # Map XSD datatypes to validation functions
        self.xsd_validators = {
            "string": self._validate_string,
            "integer": self._validate_integer,
            "int": self._validate_integer,
            "long": self._validate_integer,
            "short": self._validate_integer,
            "byte": self._validate_integer,
            "decimal": self._validate_decimal,
            "float": self._validate_float,
            "double": self._validate_float,
            "boolean": self._validate_boolean,
            "date": self._validate_date,
            "dateTime": self._validate_datetime,
            "time": self._validate_time,
            "anyURI": self._validate_uri,
            "positiveInteger": self._validate_positive_integer,
            "nonNegativeInteger": self._validate_non_negative_integer,
            "negativeInteger": self._validate_negative_integer,
            "nonPositiveInteger": self._validate_non_positive_integer,
        }

    def validate(self, node_data: Dict[str, Any], shape_id: str,
                 node_id: Optional[str] = None) -> ValidationReport:
        """
        Validate RDF node data against a shape.

        Args:
            node_data: Dictionary mapping predicates to values
            shape_id: ID of the shape to validate against
            node_id: Optional ID of the node being validated

        Returns:
            A ValidationReport with detailed results
        """
        import time
        start_time = time.time()

        report = ValidationReport(
            is_valid=True,
            shape_id=shape_id,
            node_id=node_id
        )

        # Get the shape
        shape = self.schema.get_shape(shape_id)
        if not shape:
            report.add_violation(ConstraintViolation(
                violation_type=ViolationType.REQUIRED_PROPERTY,
                severity=Severity.ERROR,
                message=f"Shape {shape_id} not found in schema",
                fix_suggestion=f"Ensure the shape {shape_id} is defined in the schema"
            ))
            return report

        # Track which predicates we've seen
        seen_predicates: Set[str] = set()

        # Validate each constraint in the shape
        for constraint in shape.expression:
            report.checked_constraints += 1
            predicate = self._expand_predicate(constraint.predicate)
            seen_predicates.add(predicate)

            # Get values for this predicate
            values = self._get_predicate_values(node_data, constraint.predicate)

            # Validate cardinality
            self._validate_cardinality(constraint, values, report)

            # Validate each value
            for value in values:
                self._validate_value(constraint, value, report)

        # Check for closed shape violations
        if shape.closed:
            self._validate_closed_shape(shape, node_data, seen_predicates, report)

        report.validation_time = time.time() - start_time
        return report

    def validate_graph(self, graph_data: Dict[str, Dict[str, Any]],
                       node_shape_map: Dict[str, str]) -> Dict[str, ValidationReport]:
        """
        Validate multiple nodes in an RDF graph.

        Args:
            graph_data: Dictionary mapping node IRIs to their data
            node_shape_map: Dictionary mapping node IRIs to shape IDs

        Returns:
            Dictionary mapping node IRIs to ValidationReport objects
        """
        results = {}

        for node_iri, shape_id in node_shape_map.items():
            if node_iri in graph_data:
                node_data = graph_data[node_iri]
                results[node_iri] = self.validate(node_data, shape_id, node_iri)
            else:
                report = ValidationReport(is_valid=False, shape_id=shape_id, node_id=node_iri)
                report.add_violation(ConstraintViolation(
                    violation_type=ViolationType.REQUIRED_PROPERTY,
                    severity=Severity.ERROR,
                    message=f"Node {node_iri} not found in graph data",
                    fix_suggestion=f"Ensure node {node_iri} exists in the graph"
                ))
                results[node_iri] = report

        return results

    def validate_batch(self, nodes: List[Dict[str, Any]], shape_id: str) -> List[ValidationReport]:
        """
        Validate multiple nodes against the same shape.

        Args:
            nodes: List of node data dictionaries
            shape_id: ID of the shape to validate against

        Returns:
            List of ValidationReport objects
        """
        return [self.validate(node, shape_id, f"node_{i}") for i, node in enumerate(nodes)]

    def _get_predicate_values(self, node_data: Dict[str, Any], predicate: str) -> List[Any]:
        """Get values for a predicate, handling expanded and prefixed forms."""
        values = []

        # Try exact match
        if predicate in node_data:
            values = node_data[predicate]
        else:
            # Try expanded form
            expanded = self._expand_predicate(predicate)
            if expanded in node_data:
                values = node_data[expanded]
            else:
                # Try to find by local name
                for key in node_data.keys():
                    if key.endswith(predicate.split(":")[-1]):
                        values = node_data[key]
                        break

        # Ensure values is a list
        if not isinstance(values, list):
            values = [values] if values is not None and values != "" else []

        return values

    def _expand_predicate(self, predicate: str) -> str:
        """Expand a prefixed predicate to full IRI."""
        return self.schema.expand_prefix(predicate)

    def _validate_cardinality(self, constraint: TripleConstraint,
                             values: List[Any], report: ValidationReport):
        """Validate cardinality constraints."""
        predicate = constraint.predicate
        value_count = len(values)

        expected = None
        fix_suggestion = None

        if constraint.cardinality == Cardinality.EXACTLY_ONE:
            if value_count != 1:
                expected = "exactly 1 value"
                if value_count == 0:
                    fix_suggestion = f"Add a value for {predicate}"
                else:
                    fix_suggestion = f"Reduce {predicate} to a single value"

                report.add_violation(ConstraintViolation(
                    violation_type=ViolationType.CARDINALITY,
                    severity=Severity.ERROR,
                    predicate=predicate,
                    message=f"Property must have exactly one value",
                    actual_value=value_count,
                    expected=expected,
                    fix_suggestion=fix_suggestion
                ))

        elif constraint.cardinality == Cardinality.ONE_OR_MORE:
            if value_count < 1:
                report.add_violation(ConstraintViolation(
                    violation_type=ViolationType.CARDINALITY,
                    severity=Severity.ERROR,
                    predicate=predicate,
                    message=f"Property must have at least one value",
                    actual_value=value_count,
                    expected="at least 1 value",
                    fix_suggestion=f"Add at least one value for {predicate}"
                ))

        elif constraint.cardinality == Cardinality.ZERO_OR_ONE:
            if value_count > 1:
                report.add_violation(ConstraintViolation(
                    violation_type=ViolationType.CARDINALITY,
                    severity=Severity.ERROR,
                    predicate=predicate,
                    message=f"Property must have at most one value",
                    actual_value=value_count,
                    expected="0 or 1 value",
                    fix_suggestion=f"Remove extra values from {predicate}, keeping only one"
                ))

        # ZERO_OR_MORE accepts any count - no validation needed

    def _validate_value(self, constraint: TripleConstraint,
                       value: Any, report: ValidationReport):
        """Validate a single value against a constraint."""
        predicate = constraint.predicate

        # Validate node kind
        if constraint.node_kind:
            self._validate_node_kind(constraint.node_kind, value, predicate, report)

        # Validate datatype
        if constraint.datatype:
            self._validate_datatype_constraint(constraint.datatype, value, predicate, report)

        # Validate value set
        if isinstance(constraint.value_expr, ValueSet):
            self._validate_value_set(constraint.value_expr, value, predicate, report)

        # Validate numeric constraints
        self._validate_numeric_constraints(constraint, value, predicate, report)

        # Validate string constraints
        self._validate_string_constraints(constraint, value, predicate, report)

    def _validate_node_kind(self, node_kind: NodeKind, value: Any,
                           predicate: str, report: ValidationReport):
        """Validate node kind constraints."""
        if node_kind == NodeKind.IRI:
            if not self._is_iri(value):
                report.add_violation(ConstraintViolation(
                    violation_type=ViolationType.NODE_KIND,
                    severity=Severity.ERROR,
                    predicate=predicate,
                    message="Value must be an IRI",
                    actual_value=value,
                    expected="IRI",
                    fix_suggestion=f"Use a valid IRI for {predicate}, e.g., <http://example.org/resource>"
                ))

        elif node_kind == NodeKind.LITERAL:
            if self._is_iri(value):
                report.add_violation(ConstraintViolation(
                    violation_type=ViolationType.NODE_KIND,
                    severity=Severity.ERROR,
                    predicate=predicate,
                    message="Value must be a literal, not an IRI",
                    actual_value=value,
                    expected="literal value",
                    fix_suggestion=f"Use a literal value for {predicate}, not an IRI"
                ))

        elif node_kind == NodeKind.BNODE:
            if not self._is_blank_node(value):
                report.add_violation(ConstraintViolation(
                    violation_type=ViolationType.NODE_KIND,
                    severity=Severity.ERROR,
                    predicate=predicate,
                    message="Value must be a blank node",
                    actual_value=value,
                    expected="blank node",
                    fix_suggestion=f"Use a blank node identifier for {predicate}"
                ))

        elif node_kind == NodeKind.NONLITERAL:
            if not (self._is_iri(value) or self._is_blank_node(value)):
                report.add_violation(ConstraintViolation(
                    violation_type=ViolationType.NODE_KIND,
                    severity=Severity.ERROR,
                    predicate=predicate,
                    message="Value must be an IRI or blank node (not a literal)",
                    actual_value=value,
                    expected="IRI or blank node",
                    fix_suggestion=f"Use an IRI or blank node for {predicate}"
                ))

    def _validate_datatype_constraint(self, datatype: str, value: Any,
                                     predicate: str, report: ValidationReport):
        """Validate datatype constraints using XSD validators."""
        # Extract the datatype local name
        datatype_local = datatype.split(":")[-1].split("#")[-1].split("/")[-1]

        # Get the appropriate validator
        validator = self.xsd_validators.get(datatype_local)

        if validator:
            is_valid, error_msg, suggestion = validator(value)
            if not is_valid:
                report.add_violation(ConstraintViolation(
                    violation_type=ViolationType.DATATYPE,
                    severity=Severity.ERROR,
                    predicate=predicate,
                    message=error_msg,
                    actual_value=value,
                    expected=f"value of type {datatype}",
                    fix_suggestion=suggestion
                ))
        else:
            # Unknown datatype - just check basic type compatibility
            report.add_violation(ConstraintViolation(
                violation_type=ViolationType.DATATYPE,
                severity=Severity.WARNING,
                predicate=predicate,
                message=f"Unknown datatype {datatype}, cannot validate",
                actual_value=value,
                fix_suggestion=f"Use a standard XSD datatype"
            ))

    def _validate_value_set(self, value_set: ValueSet, value: Any,
                           predicate: str, report: ValidationReport):
        """Validate value against a value set."""
        value_str = str(value).strip("<>")
        matched = False
        excluded = False

        for vs_value in value_set.values:
            if vs_value.value_type == "iri":
                if value_str == vs_value.value.strip("<>"):
                    matched = True
                    break

            elif vs_value.value_type == "stem":
                stem = vs_value.value.strip("<>")
                if value_str.startswith(stem):
                    matched = True
                    break

            elif vs_value.value_type == "exclusion":
                if value_str == vs_value.value.strip("<>"):
                    excluded = True
                    break

        if excluded or not matched:
            allowed_values = [str(v) for v in value_set.values if v.value_type != "exclusion"]
            report.add_violation(ConstraintViolation(
                violation_type=ViolationType.VALUE_SET,
                severity=Severity.ERROR,
                predicate=predicate,
                message="Value not in allowed value set",
                actual_value=value,
                expected=f"one of {allowed_values[:5]}{'...' if len(allowed_values) > 5 else ''}",
                fix_suggestion=f"Use one of the allowed values: {', '.join(allowed_values[:3])}"
            ))

    def _validate_numeric_constraints(self, constraint: TripleConstraint, value: Any,
                                     predicate: str, report: ValidationReport):
        """Validate numeric range constraints."""
        # Try to convert value to number
        try:
            numeric_value = float(value)
        except (ValueError, TypeError):
            # Not a numeric value, skip numeric validation
            return

        if constraint.min_inclusive is not None:
            try:
                min_val = float(constraint.min_inclusive)
                if numeric_value < min_val:
                    report.add_violation(ConstraintViolation(
                        violation_type=ViolationType.NUMERIC_RANGE,
                        severity=Severity.ERROR,
                        predicate=predicate,
                        message=f"Value is below minimum",
                        actual_value=value,
                        expected=f">= {constraint.min_inclusive}",
                        fix_suggestion=f"Use a value >= {constraint.min_inclusive}"
                    ))
            except (ValueError, TypeError):
                pass

        if constraint.max_inclusive is not None:
            try:
                max_val = float(constraint.max_inclusive)
                if numeric_value > max_val:
                    report.add_violation(ConstraintViolation(
                        violation_type=ViolationType.NUMERIC_RANGE,
                        severity=Severity.ERROR,
                        predicate=predicate,
                        message=f"Value is above maximum",
                        actual_value=value,
                        expected=f"<= {constraint.max_inclusive}",
                        fix_suggestion=f"Use a value <= {constraint.max_inclusive}"
                    ))
            except (ValueError, TypeError):
                pass

        if constraint.min_exclusive is not None:
            try:
                min_val = float(constraint.min_exclusive)
                if numeric_value <= min_val:
                    report.add_violation(ConstraintViolation(
                        violation_type=ViolationType.NUMERIC_RANGE,
                        severity=Severity.ERROR,
                        predicate=predicate,
                        message=f"Value must be greater than minimum",
                        actual_value=value,
                        expected=f"> {constraint.min_exclusive}",
                        fix_suggestion=f"Use a value > {constraint.min_exclusive}"
                    ))
            except (ValueError, TypeError):
                pass

        if constraint.max_exclusive is not None:
            try:
                max_val = float(constraint.max_exclusive)
                if numeric_value >= max_val:
                    report.add_violation(ConstraintViolation(
                        violation_type=ViolationType.NUMERIC_RANGE,
                        severity=Severity.ERROR,
                        predicate=predicate,
                        message=f"Value must be less than maximum",
                        actual_value=value,
                        expected=f"< {constraint.max_exclusive}",
                        fix_suggestion=f"Use a value < {constraint.max_exclusive}"
                    ))
            except (ValueError, TypeError):
                pass

    def _validate_string_constraints(self, constraint: TripleConstraint, value: Any,
                                    predicate: str, report: ValidationReport):
        """Validate string pattern and length constraints."""
        value_str = str(value)

        # Pattern validation
        if constraint.pattern:
            try:
                if not re.search(constraint.pattern, value_str):
                    report.add_violation(ConstraintViolation(
                        violation_type=ViolationType.STRING_PATTERN,
                        severity=Severity.ERROR,
                        predicate=predicate,
                        message=f"Value does not match required pattern",
                        actual_value=value,
                        expected=f"pattern: {constraint.pattern}",
                        fix_suggestion=f"Ensure value matches the pattern {constraint.pattern}"
                    ))
            except re.error as e:
                report.add_violation(ConstraintViolation(
                    violation_type=ViolationType.STRING_PATTERN,
                    severity=Severity.WARNING,
                    predicate=predicate,
                    message=f"Invalid regex pattern: {e}",
                    fix_suggestion="Fix the regex pattern in the shape definition"
                ))

        # Length validation
        value_length = len(value_str)

        if constraint.length is not None:
            if value_length != constraint.length:
                report.add_violation(ConstraintViolation(
                    violation_type=ViolationType.STRING_LENGTH,
                    severity=Severity.ERROR,
                    predicate=predicate,
                    message=f"Value length must be exactly {constraint.length}",
                    actual_value=f"{value} (length: {value_length})",
                    expected=f"length = {constraint.length}",
                    fix_suggestion=f"Adjust value to be exactly {constraint.length} characters"
                ))

        if constraint.min_length is not None:
            if value_length < constraint.min_length:
                report.add_violation(ConstraintViolation(
                    violation_type=ViolationType.STRING_LENGTH,
                    severity=Severity.ERROR,
                    predicate=predicate,
                    message=f"Value is too short",
                    actual_value=f"{value} (length: {value_length})",
                    expected=f"length >= {constraint.min_length}",
                    fix_suggestion=f"Use a value with at least {constraint.min_length} characters"
                ))

        if constraint.max_length is not None:
            if value_length > constraint.max_length:
                report.add_violation(ConstraintViolation(
                    violation_type=ViolationType.STRING_LENGTH,
                    severity=Severity.ERROR,
                    predicate=predicate,
                    message=f"Value is too long",
                    actual_value=f"{value} (length: {value_length})",
                    expected=f"length <= {constraint.max_length}",
                    fix_suggestion=f"Use a value with at most {constraint.max_length} characters"
                ))

    def _validate_closed_shape(self, shape: Shape, node_data: Dict[str, Any],
                              seen_predicates: Set[str], report: ValidationReport):
        """Validate closed shape constraints."""
        # Get all predicates in the data
        data_predicates = set()
        for pred in node_data.keys():
            data_predicates.add(pred)
            data_predicates.add(self._expand_predicate(pred))

        # Get extra allowed predicates
        extra_predicates = set()
        for extra in shape.extra:
            extra_predicates.add(extra)
            extra_predicates.add(self._expand_predicate(extra))

        # Find unexpected predicates
        unexpected = data_predicates - seen_predicates - extra_predicates

        if unexpected:
            unexpected_list = sorted(list(unexpected))
            report.add_violation(ConstraintViolation(
                violation_type=ViolationType.CLOSED_SHAPE,
                severity=Severity.ERROR,
                message=f"Closed shape violation: found {len(unexpected)} unexpected predicate(s)",
                actual_value=unexpected_list,
                expected="only predicates defined in the shape",
                fix_suggestion=f"Remove these predicates: {', '.join(unexpected_list[:3])}"
            ))

    # XSD Datatype Validators

    def _validate_string(self, value: Any) -> Tuple[bool, str, str]:
        """Validate xsd:string."""
        if isinstance(value, str):
            return True, "", ""
        return False, f"Expected string, got {type(value).__name__}", "Convert value to a string"

    def _validate_integer(self, value: Any) -> Tuple[bool, str, str]:
        """Validate xsd:integer."""
        try:
            int(value)
            # Check if it's actually an integer (not a float with decimals)
            if isinstance(value, float) and value != int(value):
                return False, f"Expected integer, got float with decimals", "Remove decimal places"
            return True, "", ""
        except (ValueError, TypeError):
            return False, f"Expected integer, got invalid value", "Use a valid integer value"

    def _validate_decimal(self, value: Any) -> Tuple[bool, str, str]:
        """Validate xsd:decimal."""
        try:
            Decimal(str(value))
            return True, "", ""
        except (ValueError, InvalidOperation):
            return False, f"Expected decimal number", "Use a valid decimal number"

    def _validate_float(self, value: Any) -> Tuple[bool, str, str]:
        """Validate xsd:float/xsd:double."""
        try:
            float(value)
            return True, "", ""
        except (ValueError, TypeError):
            return False, f"Expected numeric value", "Use a valid number"

    def _validate_boolean(self, value: Any) -> Tuple[bool, str, str]:
        """Validate xsd:boolean."""
        if isinstance(value, bool):
            return True, "", ""
        if isinstance(value, str) and value.lower() in ['true', 'false', '1', '0']:
            return True, "", ""
        return False, f"Expected boolean value", "Use true/false or 1/0"

    def _validate_date(self, value: Any) -> Tuple[bool, str, str]:
        """Validate xsd:date."""
        try:
            if isinstance(value, date):
                return True, "", ""
            # Try parsing ISO format
            datetime.fromisoformat(str(value).split('T')[0])
            return True, "", ""
        except (ValueError, AttributeError):
            return False, f"Expected date in ISO format (YYYY-MM-DD)", "Use format: YYYY-MM-DD"

    def _validate_datetime(self, value: Any) -> Tuple[bool, str, str]:
        """Validate xsd:dateTime."""
        try:
            if isinstance(value, datetime):
                return True, "", ""
            # Try parsing ISO format
            datetime.fromisoformat(str(value).replace('Z', '+00:00'))
            return True, "", ""
        except (ValueError, AttributeError):
            return False, f"Expected datetime in ISO format", "Use format: YYYY-MM-DDTHH:MM:SS"

    def _validate_time(self, value: Any) -> Tuple[bool, str, str]:
        """Validate xsd:time."""
        try:
            # Simple time format check
            time_pattern = r'^\d{2}:\d{2}:\d{2}(\.\d+)?$'
            if re.match(time_pattern, str(value)):
                return True, "", ""
            return False, f"Expected time in format HH:MM:SS", "Use format: HH:MM:SS"
        except:
            return False, f"Expected time in format HH:MM:SS", "Use format: HH:MM:SS"

    def _validate_uri(self, value: Any) -> Tuple[bool, str, str]:
        """Validate xsd:anyURI."""
        if self._is_iri(value):
            return True, "", ""
        return False, f"Expected valid URI", "Use a valid URI format"

    def _validate_positive_integer(self, value: Any) -> Tuple[bool, str, str]:
        """Validate xsd:positiveInteger."""
        try:
            int_val = int(value)
            if int_val > 0:
                return True, "", ""
            return False, f"Expected positive integer (> 0)", "Use a positive integer"
        except (ValueError, TypeError):
            return False, f"Expected positive integer", "Use a valid positive integer"

    def _validate_non_negative_integer(self, value: Any) -> Tuple[bool, str, str]:
        """Validate xsd:nonNegativeInteger."""
        try:
            int_val = int(value)
            if int_val >= 0:
                return True, "", ""
            return False, f"Expected non-negative integer (>= 0)", "Use a non-negative integer"
        except (ValueError, TypeError):
            return False, f"Expected non-negative integer", "Use a valid non-negative integer"

    def _validate_negative_integer(self, value: Any) -> Tuple[bool, str, str]:
        """Validate xsd:negativeInteger."""
        try:
            int_val = int(value)
            if int_val < 0:
                return True, "", ""
            return False, f"Expected negative integer (< 0)", "Use a negative integer"
        except (ValueError, TypeError):
            return False, f"Expected negative integer", "Use a valid negative integer"

    def _validate_non_positive_integer(self, value: Any) -> Tuple[bool, str, str]:
        """Validate xsd:nonPositiveInteger."""
        try:
            int_val = int(value)
            if int_val <= 0:
                return True, "", ""
            return False, f"Expected non-positive integer (<= 0)", "Use a non-positive integer"
        except (ValueError, TypeError):
            return False, f"Expected non-positive integer", "Use a valid non-positive integer"

    # Helper methods

    def _is_iri(self, value: Any) -> bool:
        """Check if a value is an IRI."""
        if not isinstance(value, str):
            return False

        # Remove angle brackets if present
        value = value.strip()
        if value.startswith('<') and value.endswith('>'):
            value = value[1:-1]

        # Check for URI scheme
        try:
            result = urlparse(value)
            return bool(result.scheme)
        except:
            return False

    def _is_blank_node(self, value: Any) -> bool:
        """Check if a value is a blank node."""
        if not isinstance(value, str):
            return False
        return value.startswith('_:')


# Common validation patterns

def create_required_optional_validator(
    required_properties: List[str],
    optional_properties: List[str],
    datatype_map: Optional[Dict[str, str]] = None
) -> str:
    """
    Create a ShEx schema for common required/optional property pattern.

    Args:
        required_properties: List of required property URIs
        optional_properties: List of optional property URIs
        datatype_map: Optional mapping of property URIs to XSD datatypes

    Returns:
        ShEx schema text
    """
    lines = ["<Shape> {"]

    datatype_map = datatype_map or {}

    for prop in required_properties:
        datatype = datatype_map.get(prop, "xsd:string")
        lines.append(f"  {prop} {datatype},")

    for prop in optional_properties:
        datatype = datatype_map.get(prop, "xsd:string")
        lines.append(f"  {prop} {datatype}?,")

    lines.append("}")

    return "\n".join(lines)


def validate_uri_pattern(uri: str, pattern: str, namespace: Optional[str] = None) -> bool:
    """
    Validate a URI against a pattern.

    Args:
        uri: The URI to validate
        pattern: Regex pattern to match
        namespace: Optional namespace that the URI must start with

    Returns:
        True if valid, False otherwise
    """
    if namespace and not uri.startswith(namespace):
        return False

    try:
        return bool(re.match(pattern, uri))
    except re.error:
        return False


def validate_cross_reference(
    source_value: Any,
    target_graph: Dict[str, Dict[str, Any]],
    required_properties: Optional[List[str]] = None
) -> Tuple[bool, Optional[str]]:
    """
    Validate that a reference points to an existing node with required properties.

    Args:
        source_value: The IRI being referenced
        target_graph: Graph data to search in
        required_properties: Properties that must exist on the target node

    Returns:
        Tuple of (is_valid, error_message)
    """
    source_str = str(source_value).strip("<>")

    if source_str not in target_graph:
        return False, f"Referenced node {source_str} not found in graph"

    if required_properties:
        target_node = target_graph[source_str]
        missing = [p for p in required_properties if p not in target_node]
        if missing:
            return False, f"Referenced node missing required properties: {missing}"

    return True, None


# Example usage
if __name__ == "__main__":
    from .shex_parser import ShExParser

    print("Constraint Validator Example")
    print("=" * 70)

    # Define a schema with various constraints
    schema_text = """
    PREFIX ex: <http://example.org/>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>

    <PersonShape> {
      ex:name xsd:string,
      ex:age xsd:integer MININCLUSIVE 0 MAXINCLUSIVE 150,
      ex:email xsd:string PATTERN "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
      ex:phone xsd:string? MINLENGTH 10 MAXLENGTH 15,
      foaf:homepage IRI?
    } CLOSED
    """

    # Parse schema
    parser = ShExParser()
    schema = parser.parse(schema_text)

    # Create validator
    validator = ConstraintValidator(schema)

    # Test case 1: Valid data
    print("\nTest 1: Valid Person Data")
    print("-" * 70)
    valid_person = {
        "ex:name": "Alice Johnson",
        "ex:age": 30,
        "ex:email": "alice@example.com",
        "ex:phone": "555-123-4567",
        "foaf:homepage": "http://alice.example.com"
    }

    report = validator.validate(valid_person, "<PersonShape>")
    print(report)

    # Test case 2: Invalid data - multiple errors
    print("\nTest 2: Invalid Person Data (Multiple Errors)")
    print("-" * 70)
    invalid_person = {
        "ex:name": "Bob Smith",
        "ex:age": 200,  # Too old
        "ex:email": "invalid-email",  # Invalid format
        "ex:phone": "123",  # Too short
        "foaf:homepage": "not-a-uri",  # Not an IRI
        "ex:unexpectedProp": "value"  # Closed shape violation
    }

    report = validator.validate(invalid_person, "<PersonShape>")
    print(report)

    # Test case 3: Missing required properties
    print("\nTest 3: Missing Required Properties")
    print("-" * 70)
    incomplete_person = {
        "ex:age": 25
    }

    report = validator.validate(incomplete_person, "<PersonShape>")
    print(report)

    # Test case 4: Batch validation
    print("\nTest 4: Batch Validation")
    print("-" * 70)
    people = [
        {"ex:name": "Charlie", "ex:age": 35, "ex:email": "charlie@example.com"},
        {"ex:name": "Diana", "ex:age": -5, "ex:email": "diana@example.com"},  # Invalid age
        {"ex:name": "Eve", "ex:age": 40, "ex:email": "eve.example.com"},  # Invalid email
    ]

    reports = validator.validate_batch(people, "<PersonShape>")
    for i, report in enumerate(reports):
        print(f"\nPerson {i+1}:")
        if report.is_valid:
            print("  ✓ Valid")
        else:
            print(f"  ✗ {report.error_count} error(s)")
            for violation in report.violations[:2]:  # Show first 2 errors
                print(f"    - {violation.message}")
