"""
ShEx (Shape Expressions) Parser and Validator

This module provides comprehensive ShEx 2.0+ parsing and validation capabilities.
It supports parsing ShEx schemas from text, validating RDF data against shapes,
and integrating with PyShEx when available.

Example:
    >>> parser = ShExParser()
    >>> schema = parser.parse('''
    ... PREFIX up: <http://purl.uniprot.org/core/>
    ... PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    ...
    ... <ProteinShape> {
    ...   up:name xsd:string+,
    ...   up:organism IRI,
    ...   up:sequence xsd:string?
    ... }
    ... ''')
    >>> print(schema.shapes['ProteinShape'])
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Union, Any, Tuple
from urllib.parse import urlparse


class Cardinality(Enum):
    """Cardinality modifiers for ShEx triple constraints."""
    EXACTLY_ONE = "1"      # No modifier
    ZERO_OR_ONE = "?"      # Optional
    ONE_OR_MORE = "+"      # Required, repeatable
    ZERO_OR_MORE = "*"     # Optional, repeatable


class NodeKind(Enum):
    """Node types in ShEx."""
    IRI = "iri"
    BNODE = "bnode"
    LITERAL = "literal"
    NONLITERAL = "nonliteral"


@dataclass
class ValueSetValue:
    """A single value in a value set."""
    value: str
    value_type: str = "iri"  # iri, literal, stem, exclusion

    def __str__(self):
        if self.value_type == "stem":
            return f"{self.value}~"
        elif self.value_type == "exclusion":
            return f"- {self.value}"
        return self.value


@dataclass
class ValueSet:
    """A set of allowed values for a property."""
    values: List[ValueSetValue] = field(default_factory=list)

    def add_value(self, value: str, value_type: str = "iri"):
        """Add a value to the set."""
        self.values.append(ValueSetValue(value, value_type))

    def __str__(self):
        return "[" + " ".join(str(v) for v in self.values) + "]"


@dataclass
class TripleConstraint:
    """A constraint on a single property in a ShEx shape."""
    predicate: str
    value_expr: Optional[Union[str, ValueSet, 'Shape']] = None
    cardinality: Cardinality = Cardinality.EXACTLY_ONE
    node_kind: Optional[NodeKind] = None
    datatype: Optional[str] = None
    min_inclusive: Optional[Any] = None
    max_inclusive: Optional[Any] = None
    min_exclusive: Optional[Any] = None
    max_exclusive: Optional[Any] = None
    pattern: Optional[str] = None
    length: Optional[int] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None

    def __str__(self):
        parts = [self.predicate]

        if self.node_kind:
            parts.append(self.node_kind.value.upper())
        elif self.datatype:
            parts.append(self.datatype)
        elif isinstance(self.value_expr, ValueSet):
            parts.append(str(self.value_expr))
        elif isinstance(self.value_expr, str):
            parts.append(self.value_expr)

        if self.cardinality != Cardinality.EXACTLY_ONE:
            parts.append(self.cardinality.value)

        return " ".join(parts)


@dataclass
class Shape:
    """A ShEx shape definition."""
    id: str
    closed: bool = False
    extra: List[str] = field(default_factory=list)
    expression: List[TripleConstraint] = field(default_factory=list)
    extends: Optional[str] = None

    def add_constraint(self, constraint: TripleConstraint):
        """Add a triple constraint to the shape."""
        self.expression.append(constraint)

    def __str__(self):
        lines = [f"{self.id} {{"]
        for constraint in self.expression:
            lines.append(f"  {constraint},")
        if self.closed:
            lines.append("} CLOSED")
        else:
            lines.append("}")
        return "\n".join(lines)


@dataclass
class ShExSchema:
    """A complete ShEx schema."""
    prefixes: Dict[str, str] = field(default_factory=dict)
    shapes: Dict[str, Shape] = field(default_factory=dict)
    base: Optional[str] = None
    start: Optional[str] = None

    def add_prefix(self, prefix: str, iri: str):
        """Add a prefix to the schema."""
        self.prefixes[prefix] = iri

    def add_shape(self, shape: Shape):
        """Add a shape to the schema."""
        self.shapes[shape.id] = shape

    def get_shape(self, shape_id: str) -> Optional[Shape]:
        """Get a shape by ID."""
        return self.shapes.get(shape_id)

    def expand_prefix(self, prefixed_name: str) -> str:
        """Expand a prefixed name to a full IRI."""
        if ":" in prefixed_name:
            prefix, local_name = prefixed_name.split(":", 1)
            if prefix in self.prefixes:
                return self.prefixes[prefix] + local_name
        return prefixed_name

    def __str__(self):
        lines = []

        # Add base if present
        if self.base:
            lines.append(f"BASE <{self.base}>")
            lines.append("")

        # Add prefixes
        for prefix, iri in self.prefixes.items():
            lines.append(f"PREFIX {prefix}: <{iri}>")

        if self.prefixes:
            lines.append("")

        # Add start if present
        if self.start:
            lines.append(f"start = {self.start}")
            lines.append("")

        # Add shapes
        for shape in self.shapes.values():
            lines.append(str(shape))
            lines.append("")

        return "\n".join(lines)


class ShExParser:
    """
    Parser for ShEx (Shape Expressions) schemas.

    Supports ShEx 2.0+ syntax including:
    - Shape definitions
    - Triple constraints
    - Value sets and datatypes
    - Cardinality modifiers
    - Node kinds (IRI, BNODE, LITERAL)
    - String and numeric constraints
    - Prefixes and base declarations
    """

    def __init__(self):
        self.schema = ShExSchema()
        self.current_position = 0
        self.text = ""

    def parse(self, shex_text: str) -> ShExSchema:
        """
        Parse a ShEx schema from text.

        Args:
            shex_text: The ShEx schema text

        Returns:
            A parsed ShExSchema object
        """
        self.schema = ShExSchema()
        self.text = shex_text
        self.current_position = 0

        # Remove comments
        self.text = self._remove_comments(self.text)

        # Parse base declaration
        self._parse_base()

        # Parse prefixes
        self._parse_prefixes()

        # Parse start declaration
        self._parse_start()

        # Parse shapes
        self._parse_shapes()

        return self.schema

    def _remove_comments(self, text: str) -> str:
        """Remove comments from ShEx text."""
        # Remove single-line comments - but not # inside <>
        # Only match # that's not inside angle brackets
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            # Check if # appears outside of < >
            in_brackets = False
            comment_pos = -1
            for i, char in enumerate(line):
                if char == '<':
                    in_brackets = True
                elif char == '>':
                    in_brackets = False
                elif char == '#' and not in_brackets:
                    comment_pos = i
                    break

            if comment_pos >= 0:
                cleaned_lines.append(line[:comment_pos])
            else:
                cleaned_lines.append(line)

        text = '\n'.join(cleaned_lines)

        # Remove multi-line comments
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
        return text

    def _parse_base(self):
        """Parse BASE declaration."""
        match = re.search(r'BASE\s+<([^>]+)>', self.text, re.IGNORECASE)
        if match:
            self.schema.base = match.group(1)

    def _parse_prefixes(self):
        """Parse PREFIX declarations."""
        # Match PREFIX lines explicitly to avoid capturing too much
        pattern = r'^\s*PREFIX\s+([a-zA-Z0-9_-]*):?\s*<([^>]+)>\s*$'
        for match in re.finditer(pattern, self.text, re.IGNORECASE | re.MULTILINE):
            prefix = match.group(1)
            iri = match.group(2)
            self.schema.add_prefix(prefix, iri)

    def _parse_start(self):
        """Parse start declaration."""
        match = re.search(r'start\s*=\s*(@?<[^>]+>|[a-zA-Z0-9_:]+)', self.text, re.IGNORECASE)
        if match:
            self.schema.start = match.group(1)

    def _parse_shapes(self):
        """Parse all shape definitions."""
        # Pattern for shape definitions: <ShapeID> { ... }
        # Use a more careful approach to match braces
        # Match shape IDs on their own line or after whitespace, not within PREFIX declarations

        # First, find all potential shape starts
        # Negative lookbehind to ensure we're not inside a PREFIX line
        shape_pattern = r'(?:^|\n)\s*(<[^>\s]+>|[a-zA-Z0-9_:]+)\s*(\bEXTENDS\s+(<[^>\s]+>|[a-zA-Z0-9_:]+))?\s*\{'

        matches = list(re.finditer(shape_pattern, self.text, re.IGNORECASE | re.MULTILINE))

        for i, match in enumerate(matches):
            shape_id = match.group(1).strip()
            extends = match.group(3).strip() if match.group(2) else None

            # Find the matching closing brace
            start_pos = match.end()
            brace_count = 1
            pos = start_pos

            while pos < len(self.text) and brace_count > 0:
                if self.text[pos] == '{':
                    brace_count += 1
                elif self.text[pos] == '}':
                    brace_count -= 1
                pos += 1

            if brace_count == 0:
                body = self.text[start_pos:pos-1]

                # Check for CLOSED after the closing brace
                closed_match = re.match(r'\s+CLOSED', self.text[pos:], re.IGNORECASE)
                closed = bool(closed_match)

                shape = Shape(id=shape_id, closed=closed, extends=extends)

                # Parse triple constraints in the shape body
                self._parse_triple_constraints(body, shape)

                self.schema.add_shape(shape)

    def _parse_triple_constraints(self, body: str, shape: Shape):
        """Parse triple constraints within a shape body."""
        # Split by commas or semicolons
        constraints = re.split(r'[,;]\s*', body)

        for constraint_text in constraints:
            constraint_text = constraint_text.strip()
            if not constraint_text:
                continue

            constraint = self._parse_single_constraint(constraint_text)
            if constraint:
                shape.add_constraint(constraint)

    def _parse_single_constraint(self, text: str) -> Optional[TripleConstraint]:
        """Parse a single triple constraint."""
        text = text.strip()
        if not text:
            return None

        # Pattern: predicate value_expr cardinality
        # Examples:
        # up:name xsd:string+
        # up:organism IRI
        # up:sequence xsd:string?
        # foaf:age xsd:integer MININCLUSIVE 0

        parts = text.split(None, 1)
        if not parts:
            return None

        predicate = parts[0]
        constraint = TripleConstraint(predicate=predicate)

        if len(parts) > 1:
            rest = parts[1].strip()

            # Parse cardinality at the end
            cardinality_match = re.search(r'([?*+]|\{(\d+)(,(\d*)?)?\})$', rest)
            if cardinality_match:
                card_str = cardinality_match.group(1)
                rest = rest[:cardinality_match.start()].strip()

                if card_str == '?':
                    constraint.cardinality = Cardinality.ZERO_OR_ONE
                elif card_str == '+':
                    constraint.cardinality = Cardinality.ONE_OR_MORE
                elif card_str == '*':
                    constraint.cardinality = Cardinality.ZERO_OR_MORE

            # Parse value expression
            if rest.upper() == 'IRI':
                constraint.node_kind = NodeKind.IRI
            elif rest.upper() == 'BNODE':
                constraint.node_kind = NodeKind.BNODE
            elif rest.upper() == 'LITERAL':
                constraint.node_kind = NodeKind.LITERAL
            elif rest.upper() == 'NONLITERAL':
                constraint.node_kind = NodeKind.NONLITERAL
            elif rest.startswith('['):
                # Value set
                constraint.value_expr = self._parse_value_set(rest)
            elif ':' in rest or rest.startswith('<'):
                # Datatype or shape reference
                # Check for facets (MININCLUSIVE, MAXINCLUSIVE, etc.)
                facet_pattern = r'\b(MININCLUSIVE|MAXINCLUSIVE|MINEXCLUSIVE|MAXEXCLUSIVE|LENGTH|MINLENGTH|MAXLENGTH|PATTERN)\s+(.+?)(?=\s+[A-Z]+|$)'
                facets = re.finditer(facet_pattern, rest, re.IGNORECASE)

                for facet_match in facets:
                    facet_name = facet_match.group(1).upper()
                    facet_value = facet_match.group(2).strip()

                    if facet_name == 'MININCLUSIVE':
                        constraint.min_inclusive = self._parse_value(facet_value)
                    elif facet_name == 'MAXINCLUSIVE':
                        constraint.max_inclusive = self._parse_value(facet_value)
                    elif facet_name == 'MINEXCLUSIVE':
                        constraint.min_exclusive = self._parse_value(facet_value)
                    elif facet_name == 'MAXEXCLUSIVE':
                        constraint.max_exclusive = self._parse_value(facet_value)
                    elif facet_name == 'LENGTH':
                        constraint.length = int(facet_value)
                    elif facet_name == 'MINLENGTH':
                        constraint.min_length = int(facet_value)
                    elif facet_name == 'MAXLENGTH':
                        constraint.max_length = int(facet_value)
                    elif facet_name == 'PATTERN':
                        constraint.pattern = facet_value.strip('"\'')

                    # Remove facet from rest
                    rest = rest[:facet_match.start()].strip()

                constraint.datatype = rest

        return constraint

    def _parse_value_set(self, text: str) -> ValueSet:
        """Parse a value set [...] expression."""
        value_set = ValueSet()

        # Remove brackets
        text = text.strip()[1:-1] if text.startswith('[') else text

        # Split by whitespace, handling stems and exclusions
        tokens = text.split()
        i = 0
        while i < len(tokens):
            token = tokens[i]

            if token == '-':
                # Exclusion
                if i + 1 < len(tokens):
                    value_set.add_value(tokens[i + 1], "exclusion")
                    i += 2
                else:
                    i += 1
            elif token.endswith('~'):
                # Stem
                value_set.add_value(token[:-1], "stem")
                i += 1
            else:
                # Regular value
                value_set.add_value(token, "iri")
                i += 1

        return value_set

    def _parse_value(self, text: str) -> Union[int, float, str]:
        """Parse a value, attempting to detect its type."""
        text = text.strip().strip('"\'')

        # Try integer
        try:
            return int(text)
        except ValueError:
            pass

        # Try float
        try:
            return float(text)
        except ValueError:
            pass

        # Return as string
        return text

    def validate_node(self, node_data: Dict[str, Any], shape_id: str) -> Tuple[bool, List[str]]:
        """
        Validate an RDF node against a shape.

        Args:
            node_data: Dictionary mapping predicates to values
            shape_id: ID of the shape to validate against

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        shape = self.schema.get_shape(shape_id)
        if not shape:
            return False, [f"Shape {shape_id} not found"]

        errors = []

        # Track which predicates we've seen
        seen_predicates = set()

        # Validate each constraint
        for constraint in shape.expression:
            predicate = constraint.predicate
            values = node_data.get(predicate, [])

            # Ensure values is a list
            if not isinstance(values, list):
                values = [values] if values else []

            seen_predicates.add(predicate)

            # Check cardinality
            value_count = len(values)

            if constraint.cardinality == Cardinality.EXACTLY_ONE:
                if value_count != 1:
                    errors.append(f"{predicate}: expected exactly 1 value, got {value_count}")
            elif constraint.cardinality == Cardinality.ONE_OR_MORE:
                if value_count < 1:
                    errors.append(f"{predicate}: expected at least 1 value, got {value_count}")
            elif constraint.cardinality == Cardinality.ZERO_OR_ONE:
                if value_count > 1:
                    errors.append(f"{predicate}: expected at most 1 value, got {value_count}")
            # ZERO_OR_MORE accepts any count

            # Validate each value
            for value in values:
                value_errors = self._validate_value(value, constraint)
                errors.extend([f"{predicate}: {e}" for e in value_errors])

        # Check for closed shapes
        if shape.closed:
            extra_predicates = set(node_data.keys()) - seen_predicates - set(shape.extra)
            if extra_predicates:
                errors.append(f"Closed shape violation: unexpected predicates {extra_predicates}")

        return len(errors) == 0, errors

    def _validate_value(self, value: Any, constraint: TripleConstraint) -> List[str]:
        """Validate a single value against a constraint."""
        errors = []

        # Check node kind
        if constraint.node_kind:
            if constraint.node_kind == NodeKind.IRI:
                if not self._is_iri(value):
                    errors.append(f"expected IRI, got {type(value).__name__}")
            elif constraint.node_kind == NodeKind.LITERAL:
                if self._is_iri(value):
                    errors.append(f"expected literal, got IRI")

        # Check datatype (basic check)
        if constraint.datatype:
            datatype_errors = self._validate_datatype(value, constraint.datatype)
            errors.extend(datatype_errors)

        # Check numeric constraints
        if constraint.min_inclusive is not None:
            try:
                if float(value) < float(constraint.min_inclusive):
                    errors.append(f"value {value} less than minimum {constraint.min_inclusive}")
            except (ValueError, TypeError):
                pass

        if constraint.max_inclusive is not None:
            try:
                if float(value) > float(constraint.max_inclusive):
                    errors.append(f"value {value} greater than maximum {constraint.max_inclusive}")
            except (ValueError, TypeError):
                pass

        # Check string constraints
        if constraint.pattern:
            if not re.match(constraint.pattern, str(value)):
                errors.append(f"value does not match pattern {constraint.pattern}")

        if constraint.length is not None:
            if len(str(value)) != constraint.length:
                errors.append(f"length {len(str(value))} != required length {constraint.length}")

        if constraint.min_length is not None:
            if len(str(value)) < constraint.min_length:
                errors.append(f"length {len(str(value))} < minimum length {constraint.min_length}")

        if constraint.max_length is not None:
            if len(str(value)) > constraint.max_length:
                errors.append(f"length {len(str(value))} > maximum length {constraint.max_length}")

        # Check value sets
        if isinstance(constraint.value_expr, ValueSet):
            if not self._value_in_set(value, constraint.value_expr):
                errors.append(f"value not in allowed value set")

        return errors

    def _is_iri(self, value: Any) -> bool:
        """Check if a value looks like an IRI."""
        if not isinstance(value, str):
            return False

        # Check for URI scheme
        if value.startswith('<') and value.endswith('>'):
            value = value[1:-1]

        try:
            result = urlparse(value)
            return bool(result.scheme and result.netloc)
        except:
            return False

    def _validate_datatype(self, value: Any, datatype: str) -> List[str]:
        """Validate a value against a datatype."""
        errors = []

        # Map common XSD datatypes to Python types
        datatype_lower = datatype.lower()

        if 'string' in datatype_lower:
            if not isinstance(value, str):
                errors.append(f"expected string, got {type(value).__name__}")
        elif 'integer' in datatype_lower or 'int' in datatype_lower:
            try:
                int(value)
            except (ValueError, TypeError):
                errors.append(f"expected integer, got {value}")
        elif 'decimal' in datatype_lower or 'float' in datatype_lower or 'double' in datatype_lower:
            try:
                float(value)
            except (ValueError, TypeError):
                errors.append(f"expected numeric value, got {value}")
        elif 'boolean' in datatype_lower:
            if not isinstance(value, bool) and str(value).lower() not in ['true', 'false', '0', '1']:
                errors.append(f"expected boolean, got {value}")

        return errors

    def _value_in_set(self, value: Any, value_set: ValueSet) -> bool:
        """Check if a value is in a value set."""
        value_str = str(value)

        for vs_value in value_set.values:
            if vs_value.value_type == "iri":
                if value_str == vs_value.value:
                    return True
            elif vs_value.value_type == "stem":
                if value_str.startswith(vs_value.value):
                    return True
            elif vs_value.value_type == "exclusion":
                if value_str == vs_value.value:
                    return False

        return False


class ShExValidator:
    """
    Validator for RDF data against ShEx schemas.

    This class provides high-level validation functionality,
    including integration with PyShEx if available.
    """

    def __init__(self, schema: Union[str, ShExSchema]):
        """
        Initialize the validator with a ShEx schema.

        Args:
            schema: Either a ShEx schema string or a parsed ShExSchema object
        """
        if isinstance(schema, str):
            parser = ShExParser()
            self.schema = parser.parse(schema)
        else:
            self.schema = schema

        self.pyshex_available = False
        try:
            import pyshex
            self.pyshex_available = True
        except ImportError:
            pass

    def validate(self, node_data: Dict[str, Any], shape_id: str) -> Tuple[bool, List[str]]:
        """
        Validate RDF node data against a shape.

        Args:
            node_data: Dictionary mapping predicates to values
            shape_id: ID of the shape to validate against

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        parser = ShExParser()
        parser.schema = self.schema
        return parser.validate_node(node_data, shape_id)

    def validate_graph(self, graph_data: Dict[str, Dict[str, Any]],
                       node_shape_map: Dict[str, str]) -> Dict[str, Tuple[bool, List[str]]]:
        """
        Validate multiple nodes in an RDF graph.

        Args:
            graph_data: Dictionary mapping node IRIs to their data
            node_shape_map: Dictionary mapping node IRIs to shape IDs

        Returns:
            Dictionary mapping node IRIs to (is_valid, errors) tuples
        """
        results = {}

        for node_iri, shape_id in node_shape_map.items():
            if node_iri in graph_data:
                node_data = graph_data[node_iri]
                results[node_iri] = self.validate(node_data, shape_id)
            else:
                results[node_iri] = (False, [f"Node {node_iri} not found in graph"])

        return results


# Example usage and common protein shape
PROTEIN_SHAPE_EXAMPLE = """
PREFIX up: <http://purl.uniprot.org/core/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

<ProteinShape> {
  rdf:type [up:Protein],
  up:name xsd:string+,
  up:organism IRI,
  up:sequence xsd:string?,
  up:mnemonic xsd:string,
  up:mass xsd:integer?,
  up:created xsd:date?,
  up:modified xsd:date?
}

<OrganismShape> {
  rdf:type [up:Organism],
  up:scientificName xsd:string,
  up:commonName xsd:string*,
  up:taxonId xsd:integer
}

<SequenceShape> {
  rdf:type [up:Sequence],
  rdf:value xsd:string,
  up:length xsd:integer MININCLUSIVE 1
}
"""


def main():
    """Example usage of the ShEx parser."""
    print("ShEx Parser Example")
    print("=" * 60)

    # Parse the protein shape example
    parser = ShExParser()
    schema = parser.parse(PROTEIN_SHAPE_EXAMPLE)

    print("\nParsed Schema:")
    print("-" * 60)
    print(schema)

    # Example validation
    print("\nValidation Example:")
    print("-" * 60)

    protein_data = {
        "rdf:type": "up:Protein",
        "up:name": ["Hemoglobin subunit alpha"],
        "up:organism": "<http://purl.uniprot.org/taxonomy/9606>",
        "up:sequence": "MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHF",
        "up:mnemonic": "HBA_HUMAN"
    }

    is_valid, errors = parser.validate_node(protein_data, "<ProteinShape>")

    if is_valid:
        print("✓ Protein data is valid")
    else:
        print("✗ Validation errors:")
        for error in errors:
            print(f"  - {error}")

    # Test validator class
    print("\nValidator Class Example:")
    print("-" * 60)

    validator = ShExValidator(PROTEIN_SHAPE_EXAMPLE)
    is_valid, errors = validator.validate(protein_data, "<ProteinShape>")

    if is_valid:
        print("✓ Validation passed")
    else:
        print("✗ Validation failed:")
        for error in errors:
            print(f"  - {error}")


if __name__ == "__main__":
    main()
