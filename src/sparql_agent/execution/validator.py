"""
SPARQL Query Validation Module.

This module provides comprehensive validation for SPARQL queries, including:
- Syntax validation using rdflib
- SPARQL 1.1 specification compliance
- Common error detection
- Detailed error reporting with suggestions
- Variable consistency checks
- URI and literal validation
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

from rdflib import Graph
from rdflib.plugins.sparql import prepareQuery
from rdflib.plugins.sparql.parser import parseQuery
from rdflib.plugins.sparql.sparql import Query

from ..core.exceptions import QuerySyntaxError, QueryValidationError


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """
    Represents a validation issue found in a SPARQL query.

    Attributes:
        severity: Severity level of the issue
        message: Human-readable description of the issue
        line: Line number where the issue occurs (1-indexed)
        column: Column number where the issue occurs (1-indexed)
        query_fragment: The problematic fragment of the query
        suggestion: Suggested fix for the issue
        rule: The validation rule that detected this issue
    """
    severity: ValidationSeverity
    message: str
    line: Optional[int] = None
    column: Optional[int] = None
    query_fragment: Optional[str] = None
    suggestion: Optional[str] = None
    rule: Optional[str] = None

    def __str__(self) -> str:
        """Format the issue for display."""
        parts = [f"[{self.severity.value.upper()}]"]

        if self.line is not None:
            if self.column is not None:
                parts.append(f"Line {self.line}:{self.column}:")
            else:
                parts.append(f"Line {self.line}:")

        parts.append(self.message)

        if self.query_fragment:
            parts.append(f"\n  Fragment: {self.query_fragment}")

        if self.suggestion:
            parts.append(f"\n  Suggestion: {self.suggestion}")

        return " ".join(parts)


@dataclass
class ValidationResult:
    """
    Result of query validation.

    Attributes:
        is_valid: Whether the query is valid
        query: The original query
        issues: List of validation issues found
        warnings: List of warning messages
        parsed_query: The parsed query object (if successful)
        metadata: Additional validation metadata
    """
    is_valid: bool
    query: str
    issues: List[ValidationIssue] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    parsed_query: Optional[Query] = None
    metadata: Dict[str, any] = field(default_factory=dict)

    @property
    def errors(self) -> List[ValidationIssue]:
        """Get only error-level issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]

    @property
    def warning_issues(self) -> List[ValidationIssue]:
        """Get only warning-level issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]

    @property
    def info_issues(self) -> List[ValidationIssue]:
        """Get only info-level issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.INFO]

    def get_summary(self) -> str:
        """Get a summary of validation results."""
        if self.is_valid:
            summary = "Query is valid"
            if self.issues:
                summary += f" with {len(self.warning_issues)} warnings and {len(self.info_issues)} suggestions"
        else:
            summary = f"Query is invalid with {len(self.errors)} errors"
            if self.warning_issues:
                summary += f" and {len(self.warning_issues)} warnings"
        return summary

    def format_report(self) -> str:
        """Format a detailed validation report."""
        lines = [self.get_summary(), ""]

        if self.errors:
            lines.append("ERRORS:")
            for issue in self.errors:
                lines.append(f"  {issue}")
            lines.append("")

        if self.warning_issues:
            lines.append("WARNINGS:")
            for issue in self.warning_issues:
                lines.append(f"  {issue}")
            lines.append("")

        if self.info_issues:
            lines.append("SUGGESTIONS:")
            for issue in self.info_issues:
                lines.append(f"  {issue}")
            lines.append("")

        return "\n".join(lines)


class QueryValidator:
    """
    Validates SPARQL queries against SPARQL 1.1 specification.

    This validator performs comprehensive checks including:
    - Syntax validation using rdflib
    - Prefix declaration validation
    - Variable consistency checks
    - Balanced parentheses and braces
    - URI and literal validation
    - Common error detection
    - Best practice suggestions
    """

    # Common SPARQL keywords
    KEYWORDS = {
        'SELECT', 'CONSTRUCT', 'ASK', 'DESCRIBE',
        'WHERE', 'FROM', 'FILTER', 'OPTIONAL', 'UNION', 'MINUS',
        'GRAPH', 'SERVICE', 'BIND', 'VALUES',
        'ORDER', 'BY', 'LIMIT', 'OFFSET', 'DISTINCT', 'REDUCED',
        'GROUP', 'HAVING', 'AS',
        'PREFIX', 'BASE',
        'a'  # rdf:type shorthand
    }

    # Standard SPARQL prefixes
    STANDARD_PREFIXES = {
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
        'owl': 'http://www.w3.org/2002/07/owl#',
        'xsd': 'http://www.w3.org/2001/XMLSchema#',
        'skos': 'http://www.w3.org/2004/02/skos/core#',
        'dc': 'http://purl.org/dc/elements/1.1/',
        'dcterms': 'http://purl.org/dc/terms/',
        'foaf': 'http://xmlns.com/foaf/0.1/',
        'schema': 'http://schema.org/',
    }

    def __init__(self, strict: bool = False):
        """
        Initialize the validator.

        Args:
            strict: If True, enable strict validation mode with more checks
        """
        self.strict = strict

    def validate(self, query: str) -> ValidationResult:
        """
        Validate a SPARQL query.

        Args:
            query: The SPARQL query string to validate

        Returns:
            ValidationResult containing validation status and any issues found
        """
        issues: List[ValidationIssue] = []
        warnings: List[str] = []
        parsed_query = None

        # Basic checks
        if not query or not query.strip():
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message="Query is empty",
                rule="empty_query"
            ))
            return ValidationResult(is_valid=False, query=query, issues=issues)

        # Check for balanced brackets
        bracket_issues = self._check_balanced_brackets(query)
        issues.extend(bracket_issues)

        # Check for common syntax errors before parsing
        common_issues = self._check_common_errors(query)
        issues.extend(common_issues)

        # Try to parse with rdflib
        try:
            parsed_query = prepareQuery(query)

            # If parsing succeeded, do deeper validation
            deeper_issues = self._validate_parsed_query(query, parsed_query)
            issues.extend(deeper_issues)

        except Exception as e:
            # Parse failed - extract useful information from error
            error_info = self._parse_error_message(str(e), query)
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=error_info['message'],
                line=error_info.get('line'),
                column=error_info.get('column'),
                query_fragment=error_info.get('fragment'),
                suggestion=error_info.get('suggestion'),
                rule="parse_error"
            ))

        # Additional validation checks
        issues.extend(self._check_prefixes(query))
        issues.extend(self._check_variables(query))
        issues.extend(self._check_uris(query))
        issues.extend(self._check_literals(query))

        if self.strict:
            issues.extend(self._check_best_practices(query))

        # Determine if query is valid (no errors)
        has_errors = any(i.severity == ValidationSeverity.ERROR for i in issues)

        return ValidationResult(
            is_valid=not has_errors,
            query=query,
            issues=issues,
            warnings=warnings,
            parsed_query=parsed_query,
            metadata={
                'strict_mode': self.strict,
                'total_issues': len(issues),
                'error_count': len([i for i in issues if i.severity == ValidationSeverity.ERROR]),
                'warning_count': len([i for i in issues if i.severity == ValidationSeverity.WARNING]),
            }
        )

    def _check_balanced_brackets(self, query: str) -> List[ValidationIssue]:
        """Check for balanced parentheses, braces, and brackets."""
        issues = []

        # Track different bracket types
        brackets = {
            '(': (')', 'parenthesis', 'parentheses'),
            '{': ('}', 'brace', 'braces'),
            '[': (']', 'bracket', 'brackets'),
        }

        for open_char, (close_char, singular, plural) in brackets.items():
            stack = []
            for i, char in enumerate(query):
                if char == open_char:
                    stack.append(i)
                elif char == close_char:
                    if not stack:
                        issues.append(ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            message=f"Unmatched closing {singular}",
                            column=i + 1,
                            query_fragment=self._get_context(query, i),
                            suggestion=f"Remove extra '{close_char}' or add matching '{open_char}'",
                            rule="unbalanced_brackets"
                        ))
                    else:
                        stack.pop()

            if stack:
                pos = stack[-1]
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Unclosed {singular}",
                    column=pos + 1,
                    query_fragment=self._get_context(query, pos),
                    suggestion=f"Add closing '{close_char}'",
                    rule="unbalanced_brackets"
                ))

        return issues

    def _check_common_errors(self, query: str) -> List[ValidationIssue]:
        """Check for common SPARQL syntax errors."""
        issues = []
        lines = query.split('\n')

        for line_num, line in enumerate(lines, 1):
            # Check for missing dots at end of triples
            if re.search(r'\}\s*\w', line):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message="Possible missing dot after closing brace",
                    line=line_num,
                    query_fragment=line.strip(),
                    suggestion="Add '.' after '}' to end triple pattern",
                    rule="missing_dot"
                ))

            # Check for double dots
            if '..' in line:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message="Double dot found",
                    line=line_num,
                    query_fragment=line.strip(),
                    suggestion="Use single '.' to end triple patterns",
                    rule="double_dot"
                ))

            # Check for semicolon without previous statement
            if re.match(r'^\s*;', line):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message="Semicolon without previous statement",
                    line=line_num,
                    query_fragment=line.strip(),
                    suggestion="Remove semicolon or add subject",
                    rule="orphan_semicolon"
                ))

            # Check for comma without previous statement
            if re.match(r'^\s*,', line):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message="Comma without previous statement",
                    line=line_num,
                    query_fragment=line.strip(),
                    suggestion="Remove comma or add predicate-object pair",
                    rule="orphan_comma"
                ))

        return issues

    def _check_prefixes(self, query: str) -> List[ValidationIssue]:
        """Validate prefix declarations and usage."""
        issues = []

        # Extract declared prefixes
        declared_prefixes = {}
        prefix_pattern = r'PREFIX\s+(\w+):\s*<([^>]+)>'
        for match in re.finditer(prefix_pattern, query, re.IGNORECASE):
            prefix_name = match.group(1)
            prefix_uri = match.group(2)
            declared_prefixes[prefix_name] = prefix_uri

        # Find used prefixes (e.g., rdf:type, foaf:name)
        used_prefixes = set()
        usage_pattern = r'\b(\w+):(\w+)'
        for match in re.finditer(usage_pattern, query):
            prefix = match.group(1)
            # Skip if it looks like a URL scheme
            if prefix.lower() not in ['http', 'https', 'ftp', 'mailto', 'file']:
                used_prefixes.add(prefix)

        # Check for undeclared prefixes
        for prefix in used_prefixes:
            if prefix not in declared_prefixes:
                suggestion = None
                if prefix in self.STANDARD_PREFIXES:
                    suggestion = f"Add: PREFIX {prefix}: <{self.STANDARD_PREFIXES[prefix]}>"

                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Prefix '{prefix}' used but not declared",
                    suggestion=suggestion,
                    rule="undeclared_prefix"
                ))

        # Check for unused prefixes (warning only)
        for prefix in declared_prefixes:
            if prefix not in used_prefixes:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message=f"Prefix '{prefix}' declared but never used",
                    suggestion=f"Remove unused PREFIX declaration for '{prefix}'",
                    rule="unused_prefix"
                ))

        # Check for duplicate prefix declarations
        prefix_positions = {}
        for match in re.finditer(prefix_pattern, query, re.IGNORECASE):
            prefix_name = match.group(1)
            if prefix_name in prefix_positions:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Duplicate PREFIX declaration for '{prefix_name}'",
                    suggestion=f"Remove duplicate PREFIX declaration",
                    rule="duplicate_prefix"
                ))
            prefix_positions[prefix_name] = match.start()

        return issues

    def _check_variables(self, query: str) -> List[ValidationIssue]:
        """Check variable consistency and usage."""
        issues = []

        # Extract variables from SELECT clause
        select_pattern = r'SELECT\s+(DISTINCT\s+|REDUCED\s+)?(.*?)(?:WHERE|{)'
        select_match = re.search(select_pattern, query, re.IGNORECASE | re.DOTALL)

        if select_match:
            select_clause = select_match.group(2)

            # Don't validate if SELECT *
            if '*' in select_clause:
                return issues

            # Extract selected variables
            selected_vars = set(re.findall(r'\?(\w+)', select_clause))

            # Extract variables used in WHERE clause
            where_pattern = r'WHERE\s*{(.*?)}'
            where_match = re.search(where_pattern, query, re.IGNORECASE | re.DOTALL)

            if where_match:
                where_clause = where_match.group(1)
                used_vars = set(re.findall(r'\?(\w+)', where_clause))

                # Check for selected variables not used in WHERE
                for var in selected_vars:
                    if var not in used_vars:
                        issues.append(ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            message=f"Variable ?{var} selected but not used in WHERE clause",
                            suggestion=f"Remove ?{var} from SELECT or use it in WHERE clause",
                            rule="unused_select_variable"
                        ))

        # Check for variables that appear only once (might be typos)
        all_vars = re.findall(r'\?(\w+)', query)
        var_counts = {}
        for var in all_vars:
            var_counts[var] = var_counts.get(var, 0) + 1

        for var, count in var_counts.items():
            if count == 1:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    message=f"Variable ?{var} appears only once (might be intentional)",
                    suggestion=f"Verify ?{var} is correct or consider using blank node _:{var}",
                    rule="single_use_variable"
                ))

        return issues

    def _check_uris(self, query: str) -> List[ValidationIssue]:
        """Validate URIs in the query."""
        issues = []

        # Find URIs enclosed in angle brackets
        uri_pattern = r'<([^>]+)>'

        for match in re.finditer(uri_pattern, query):
            uri = match.group(1)

            # Check for common URI issues
            if ' ' in uri:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"URI contains spaces: {uri}",
                    query_fragment=f"<{uri}>",
                    suggestion="Remove spaces from URI or encode them as %20",
                    rule="invalid_uri_spaces"
                ))

            # Check for proper protocol
            if not re.match(r'https?://', uri) and not uri.startswith('urn:'):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message=f"URI may be malformed: {uri}",
                    query_fragment=f"<{uri}>",
                    suggestion="Ensure URI starts with http://, https://, or urn:",
                    rule="malformed_uri"
                ))

            # Check for unescaped special characters
            invalid_chars = ['<', '>', '"', '{', '}', '|', '\\', '^', '`']
            for char in invalid_chars:
                if char in uri:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        message=f"URI contains invalid character '{char}': {uri}",
                        query_fragment=f"<{uri}>",
                        suggestion=f"Escape or remove '{char}' from URI",
                        rule="invalid_uri_character"
                    ))

        return issues

    def _check_literals(self, query: str) -> List[ValidationIssue]:
        """Validate literals in the query."""
        issues = []

        # Check for unescaped quotes in literals
        # String literals: "..." or '...'
        string_patterns = [
            (r'"([^"\\]|\\.)*"', 'double'),  # Double quoted
            (r"'([^'\\]|\\.)*'", 'single'),  # Single quoted
        ]

        for pattern, quote_type in string_patterns:
            matches = list(re.finditer(pattern, query))

            # Check for potential unterminated strings
            # (This is a heuristic check)
            lines = query.split('\n')
            for line_num, line in enumerate(lines, 1):
                quote_char = '"' if quote_type == 'double' else "'"
                count = line.count(quote_char)
                # Count escaped quotes
                escaped_count = line.count(f'\\{quote_char}')
                # Odd number of unescaped quotes suggests unterminated string
                if (count - escaped_count) % 2 != 0:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        message=f"Possible unterminated {quote_type}-quoted string",
                        line=line_num,
                        query_fragment=line.strip()[:50],
                        suggestion=f"Check for missing {quote_type} quote",
                        rule="unterminated_string"
                    ))

        # Check for literals with language tags
        lang_pattern = r'"([^"]*)"@(\w+)'
        for match in re.finditer(lang_pattern, query):
            lang_tag = match.group(2)
            # Basic check for valid language tag format (ISO 639)
            if not re.match(r'^[a-z]{2,3}(-[A-Z]{2})?$', lang_tag):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message=f"Potentially invalid language tag: @{lang_tag}",
                    query_fragment=match.group(0),
                    suggestion="Use ISO 639 language codes (e.g., @en, @en-US)",
                    rule="invalid_language_tag"
                ))

        return issues

    def _check_best_practices(self, query: str) -> List[ValidationIssue]:
        """Check for best practices and style guidelines."""
        issues = []

        # Check for SELECT * (discouraged in production)
        if re.search(r'SELECT\s+\*', query, re.IGNORECASE):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                message="Using SELECT * is discouraged in production",
                suggestion="Explicitly list the variables you need",
                rule="select_star"
            ))

        # Check for missing LIMIT (can cause performance issues)
        query_upper = query.upper()
        if 'SELECT' in query_upper and 'LIMIT' not in query_upper:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                message="Query has no LIMIT clause",
                suggestion="Consider adding LIMIT to prevent large result sets",
                rule="missing_limit"
            ))

        # Check for inefficient OPTIONAL placement
        # OPTIONALs should generally come after required patterns
        lines = query.split('\n')
        in_where = False
        found_required_after_optional = False

        for line in lines:
            if 'WHERE' in line.upper():
                in_where = True
            if in_where:
                if 'OPTIONAL' in line.upper():
                    found_required_after_optional = True
                elif found_required_after_optional and re.search(r'\?\w+\s+\?\w+\s+\?\w+', line):
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.INFO,
                        message="Required patterns after OPTIONAL may be inefficient",
                        suggestion="Place required patterns before OPTIONAL when possible",
                        rule="optional_ordering"
                    ))
                    break

        return issues

    def _validate_parsed_query(self, query: str, parsed_query: Query) -> List[ValidationIssue]:
        """Validate the successfully parsed query."""
        issues = []

        # Additional validation on parsed structure
        # This can be extended based on the parsed query structure

        return issues

    def _parse_error_message(self, error_msg: str, query: str) -> Dict[str, any]:
        """Extract useful information from parser error message."""
        info = {'message': error_msg}

        # Try to extract line and column information
        # rdflib errors often contain line/column info
        line_match = re.search(r'line (\d+)', error_msg, re.IGNORECASE)
        col_match = re.search(r'column (\d+)', error_msg, re.IGNORECASE)

        if line_match:
            info['line'] = int(line_match.group(1))
        if col_match:
            info['column'] = int(col_match.group(1))

        # Extract query fragment if we have location
        if 'line' in info:
            lines = query.split('\n')
            if 0 < info['line'] <= len(lines):
                info['fragment'] = lines[info['line'] - 1].strip()

        # Provide suggestions based on common error patterns
        if 'unexpected' in error_msg.lower():
            info['suggestion'] = "Check syntax near the indicated position"
        elif 'expected' in error_msg.lower():
            expected_match = re.search(r"expected '([^']+)'", error_msg, re.IGNORECASE)
            if expected_match:
                info['suggestion'] = f"Add missing '{expected_match.group(1)}'"

        # Simplify error message
        if 'ParseException' in error_msg:
            # Try to extract just the meaningful part
            parts = error_msg.split(':', 1)
            if len(parts) > 1:
                info['message'] = parts[1].strip()

        return info

    def _get_context(self, query: str, position: int, context_size: int = 20) -> str:
        """Get context around a position in the query."""
        start = max(0, position - context_size)
        end = min(len(query), position + context_size)
        context = query[start:end]

        # Add ellipsis if we're not at the boundaries
        if start > 0:
            context = '...' + context
        if end < len(query):
            context = context + '...'

        return context


def validate_query(query: str, strict: bool = False) -> ValidationResult:
    """
    Convenience function to validate a SPARQL query.

    Args:
        query: The SPARQL query string to validate
        strict: If True, enable strict validation mode

    Returns:
        ValidationResult containing validation status and issues

    Example:
        >>> result = validate_query("SELECT * WHERE { ?s ?p ?o }")
        >>> if result.is_valid:
        ...     print("Query is valid!")
        >>> else:
        ...     print(result.format_report())
    """
    validator = QueryValidator(strict=strict)
    return validator.validate(query)


def validate_and_raise(query: str, strict: bool = False) -> ValidationResult:
    """
    Validate a query and raise an exception if invalid.

    Args:
        query: The SPARQL query string to validate
        strict: If True, enable strict validation mode

    Returns:
        ValidationResult if query is valid

    Raises:
        QuerySyntaxError: If query has syntax errors
        QueryValidationError: If query fails validation

    Example:
        >>> try:
        ...     result = validate_and_raise("INVALID QUERY")
        ... except QuerySyntaxError as e:
        ...     print(f"Invalid query: {e}")
    """
    result = validate_query(query, strict=strict)

    if not result.is_valid:
        if result.errors:
            # Get first error
            first_error = result.errors[0]
            error_msg = str(first_error)

            raise QuerySyntaxError(
                message=first_error.message,
                details={
                    'line': first_error.line,
                    'column': first_error.column,
                    'fragment': first_error.query_fragment,
                    'suggestion': first_error.suggestion,
                    'all_errors': [str(e) for e in result.errors],
                    'report': result.format_report()
                }
            )

    return result
