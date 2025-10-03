#!/usr/bin/env python3
"""
SPARQL Query Validation with LLM Retry Logic

This module provides a validation system that checks SPARQL queries against
schema constraints and reattempts query generation through the LLM if issues
are found, with a configurable retry limit.
"""

import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

from ..llm.client import LLMClient, LLMRequest
from ..execution.validator import ValidationResult, ValidationSeverity, validate_query
from .schema_tools import SchemaQueryTools


@dataclass
class ValidationRetryResult:
    """Result of validation with retry attempts."""

    final_query: str
    is_valid: bool
    attempts_made: int
    validation_history: List[ValidationResult]
    schema_compliance: Dict[str, Any]
    final_validation: ValidationResult
    gave_up: bool = False
    execution_attempts: int = 0
    execution_errors: List[str] = None


class QueryValidationRetry:
    """
    Validates SPARQL queries and retries generation through LLM if validation fails.

    Features:
    - SPARQL syntax validation using rdflib
    - Schema compliance checking if schema provided
    - LLM-driven query refinement on validation failures
    - Configurable retry limits and validation strictness
    """

    def __init__(
        self,
        llm_client: LLMClient,
        schema_tools: Optional[SchemaQueryTools] = None,
        max_retries: int = 5,
        strict_validation: bool = False
    ):
        self.llm_client = llm_client
        self.schema_tools = schema_tools
        self.max_retries = max_retries
        self.strict_validation = strict_validation

    def validate_with_retry(
        self,
        query: str,
        original_intent: str,
        endpoint_url: str = ""
    ) -> ValidationRetryResult:
        """
        Validate a SPARQL query and retry generation if validation fails.

        Args:
            query: The SPARQL query to validate
            original_intent: The original natural language intent
            endpoint_url: The target SPARQL endpoint URL

        Returns:
            ValidationRetryResult with final query and validation details
        """
        print(f"🔍 Validating query with up to {self.max_retries} retry attempts...")

        validation_history = []
        current_query = query

        for attempt in range(self.max_retries + 1):  # +1 for initial validation
            print(f"   Attempt {attempt + 1}/{self.max_retries + 1}: Validating...")

            # Perform SPARQL syntax validation
            validation = validate_query(current_query, strict=self.strict_validation)
            validation_history.append(validation)

            # Perform schema compliance checking if available
            schema_compliance = {}
            if self.schema_tools:
                schema_compliance = self._check_schema_compliance(current_query)

            # Check if validation passed
            if validation.is_valid and (not schema_compliance.get('issues') or len(schema_compliance['issues']) == 0):
                print(f"   ✅ Query validated successfully on attempt {attempt + 1}")
                return ValidationRetryResult(
                    final_query=current_query,
                    is_valid=True,
                    attempts_made=attempt + 1,
                    validation_history=validation_history,
                    schema_compliance=schema_compliance,
                    final_validation=validation,
                    gave_up=False
                )

            # If this was the last attempt, give up
            if attempt >= self.max_retries:
                print(f"   ❌ Validation failed after {attempt + 1} attempts, giving up")
                return ValidationRetryResult(
                    final_query=current_query,
                    is_valid=False,
                    attempts_made=attempt + 1,
                    validation_history=validation_history,
                    schema_compliance=schema_compliance,
                    final_validation=validation,
                    gave_up=True
                )

            # Attempt to fix the query through LLM
            print(f"   🔧 Attempting to fix query issues...")
            current_query = self._request_query_fix(
                current_query,
                original_intent,
                validation,
                schema_compliance,
                attempt + 1
            )

    def _check_schema_compliance(self, query: str) -> Dict[str, Any]:
        """Check query compliance against loaded schema."""
        if not self.schema_tools:
            return {'issues': [], 'compliance_score': 1.0}

        try:
            # Use schema tools to validate query components
            issues = []

            # Check for URI syntax issues
            uri_fix_result = self.schema_tools.fix_query_uri_issues(query)
            if uri_fix_result['issues_found']:
                issues.extend([f"URI syntax issue: {fix}" for fix in uri_fix_result['fixes_applied']])

            # Extract and validate triple patterns
            # This is a simplified check - could be enhanced
            triple_patterns = self._extract_triple_patterns(query)
            for subject, predicate, obj in triple_patterns[:5]:  # Check first 5 patterns
                validation = self.schema_tools.validate_triple_pattern(subject, predicate, obj)
                if not validation['valid']:
                    issues.extend(validation['issues'])

            return {
                'issues': issues,
                'compliance_score': max(0.0, 1.0 - len(issues) * 0.1),
                'patterns_checked': len(triple_patterns)
            }

        except Exception as e:
            return {
                'issues': [f"Schema validation error: {str(e)}"],
                'compliance_score': 0.5,
                'patterns_checked': 0
            }

    def _extract_triple_patterns(self, query: str) -> List[tuple]:
        """Extract basic triple patterns from SPARQL query."""
        # Simple regex-based extraction - could be enhanced with proper parsing
        import re

        patterns = []
        # Look for patterns like "?var predicate ?var2" or "?var predicate <uri>"
        pattern_regex = r'(\?[\w]+|\<[^>]+\>)\s+(\<[^>]+\>|[\w]+:[\w]+)\s+(\?[\w]+|\<[^>]+\>|"[^"]*")'

        for match in re.finditer(pattern_regex, query):
            patterns.append((match.group(1), match.group(2), match.group(3)))

        return patterns

    def retry_after_execution_error(
        self,
        failed_query: str,
        original_intent: str,
        execution_error: str,
        endpoint_url: str = "",
        attempt_number: int = 1
    ) -> ValidationRetryResult:
        """
        Retry query generation after execution failed at the endpoint.

        This analyzes the endpoint error response and creates a new query
        that addresses the specific issues reported by the SPARQL endpoint.

        Args:
            failed_query: The query that failed to execute
            original_intent: Original natural language intent
            execution_error: Error message from the SPARQL endpoint
            endpoint_url: The endpoint that returned the error
            attempt_number: Current retry attempt number

        Returns:
            ValidationRetryResult with new query attempt
        """
        print(f"🔄 Analyzing execution error for retry attempt {attempt_number}")
        print(f"   Error: {execution_error[:200]}...")

        # Create a new query based on the execution error
        fixed_query = self._request_execution_error_fix(
            failed_query,
            original_intent,
            execution_error,
            endpoint_url,
            attempt_number
        )

        # Validate the newly generated query
        return self.validate_with_retry(fixed_query, original_intent, endpoint_url)

    def _request_execution_error_fix(
        self,
        failed_query: str,
        original_intent: str,
        execution_error: str,
        endpoint_url: str,
        attempt_number: int
    ) -> str:
        """Request LLM to fix query based on execution error from endpoint."""

        # Analyze the type of execution error
        error_analysis = self._analyze_execution_error(execution_error)

        # Create detailed prompt for fixing execution errors
        prompt = f"""
The following SPARQL query failed when executed against the endpoint with an error.
Please create a new query that addresses the specific execution error.

ORIGINAL INTENT: {original_intent}
ENDPOINT: {endpoint_url}
ATTEMPT: {attempt_number}

FAILED QUERY:
{failed_query}

EXECUTION ERROR:
{execution_error}

ERROR ANALYSIS:
{json.dumps(error_analysis, indent=2)}

INSTRUCTIONS:
1. Analyze the specific error message from the SPARQL endpoint
2. Create a completely new query that addresses the error cause
3. Consider common issues:
   - Unknown predicates/classes (suggest alternatives from common vocabularies)
   - Timeout errors (simplify query, reduce LIMIT, add more specific filters)
   - Service unavailable (use alternative predicates or endpoints)
   - Syntax errors not caught earlier (fix syntax issues)
   - Authentication/access issues (use publicly accessible predicates)
4. Maintain the original intent but adapt to what the endpoint actually supports
5. Return ONLY the corrected SPARQL query, no explanations
6. Ensure the query is more likely to succeed based on the error analysis

CORRECTED QUERY:"""

        try:
            request = LLMRequest(
                prompt=prompt,
                max_tokens=1200,
                temperature=0.2,  # Slightly higher for creative problem solving
                system_prompt="You are a SPARQL expert who analyzes endpoint execution errors and creates alternative queries that are more likely to succeed. Focus on practical solutions based on endpoint capabilities."
            )

            response = self.llm_client.generate(request)

            # Extract the query from the response
            fixed_query = response.content.strip()

            # Clean up any markdown formatting
            if fixed_query.startswith('```sparql'):
                fixed_query = fixed_query.replace('```sparql', '').replace('```', '').strip()
            elif fixed_query.startswith('```'):
                fixed_query = fixed_query.replace('```', '').strip()

            print(f"   🔧 Generated alternative query based on execution error")
            return fixed_query

        except Exception as e:
            print(f"   ⚠️  LLM execution error fix failed: {e}")
            return failed_query

    def _analyze_execution_error(self, error_message: str) -> Dict[str, Any]:
        """Analyze execution error to understand the root cause."""
        error_lower = error_message.lower()

        analysis = {
            'error_type': 'unknown',
            'suggestions': [],
            'severity': 'medium'
        }

        # Common SPARQL endpoint error patterns
        if 'timeout' in error_lower or 'time' in error_lower:
            analysis['error_type'] = 'timeout'
            analysis['suggestions'] = [
                'Reduce query complexity',
                'Add more specific filters',
                'Reduce LIMIT value',
                'Avoid expensive operations like OPTIONAL'
            ]
            analysis['severity'] = 'high'

        elif 'unknown' in error_lower or 'not found' in error_lower or 'undefined' in error_lower:
            analysis['error_type'] = 'unknown_term'
            analysis['suggestions'] = [
                'Use alternative predicates or classes',
                'Check endpoint documentation for supported vocabularies',
                'Try more common/standard predicates'
            ]
            analysis['severity'] = 'high'

        elif 'syntax' in error_lower or 'parse' in error_lower:
            analysis['error_type'] = 'syntax_error'
            analysis['suggestions'] = [
                'Fix SPARQL syntax errors',
                'Check prefix declarations',
                'Validate triple patterns'
            ]
            analysis['severity'] = 'high'

        elif 'service' in error_lower or 'unavailable' in error_lower or 'connection' in error_lower:
            analysis['error_type'] = 'service_error'
            analysis['suggestions'] = [
                'Simplify query to reduce load',
                'Avoid federated queries',
                'Use cached or alternative data sources'
            ]
            analysis['severity'] = 'medium'

        elif 'authentication' in error_lower or 'forbidden' in error_lower or 'access' in error_lower:
            analysis['error_type'] = 'access_error'
            analysis['suggestions'] = [
                'Use publicly accessible predicates',
                'Avoid restricted datasets',
                'Check if endpoint requires authentication'
            ]
            analysis['severity'] = 'high'

        elif 'limit' in error_lower or 'too many' in error_lower:
            analysis['error_type'] = 'limit_exceeded'
            analysis['suggestions'] = [
                'Reduce LIMIT clause',
                'Add more specific filters',
                'Use pagination'
            ]
            analysis['severity'] = 'medium'

        return analysis

    def _request_query_fix(
        self,
        problematic_query: str,
        original_intent: str,
        validation: ValidationResult,
        schema_compliance: Dict[str, Any],
        attempt_number: int
    ) -> str:
        """Request LLM to fix the problematic query."""

        # Prepare detailed error feedback for the LLM
        error_details = []

        # Add syntax errors
        for issue in validation.issues:
            if issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.WARNING]:
                error_details.append({
                    'type': 'syntax_error',
                    'severity': issue.severity.value,
                    'message': issue.message,
                    'suggestion': issue.suggestion,
                    'line': issue.line,
                    'fragment': issue.query_fragment
                })

        # Add schema compliance issues
        for issue in schema_compliance.get('issues', []):
            error_details.append({
                'type': 'schema_error',
                'severity': 'error',
                'message': issue,
                'suggestion': 'Check endpoint schema documentation'
            })

        # Create fix request prompt
        prompt = f"""
The following SPARQL query has validation issues and needs to be fixed:

ORIGINAL INTENT: {original_intent}

PROBLEMATIC QUERY:
{problematic_query}

VALIDATION ERRORS (Attempt {attempt_number}):
{json.dumps(error_details, indent=2)}

INSTRUCTIONS:
1. Fix all syntax errors identified in the validation
2. Address schema compliance issues if any
3. Maintain the original intent of the query
4. Return ONLY the corrected SPARQL query, no explanations
5. Ensure proper SPARQL 1.1 syntax compliance

CORRECTED QUERY:"""

        try:
            request = LLMRequest(
                prompt=prompt,
                max_tokens=1000,
                temperature=0.1,  # Low temperature for precise fixes
                system_prompt="You are a SPARQL expert focused on fixing query validation issues. Return only valid SPARQL syntax."
            )

            response = self.llm_client.generate(request)

            # Extract the query from the response
            fixed_query = response.content.strip()

            # Clean up any markdown formatting
            if fixed_query.startswith('```sparql'):
                fixed_query = fixed_query.replace('```sparql', '').replace('```', '').strip()
            elif fixed_query.startswith('```'):
                fixed_query = fixed_query.replace('```', '').strip()

            return fixed_query

        except Exception as e:
            print(f"   ⚠️  LLM fix request failed: {e}")
            return problematic_query  # Return original if fix fails


def validate_before_execution(
    query: str,
    original_intent: str,
    llm_client: LLMClient,
    schema_tools: Optional[SchemaQueryTools] = None,
    endpoint_url: str = "",
    max_retries: int = 5
) -> ValidationRetryResult:
    """
    Convenience function to validate a query with retry logic before execution.

    This is the main function that should be called before sending any query
    to a SPARQL endpoint.
    """
    validator = QueryValidationRetry(
        llm_client=llm_client,
        schema_tools=schema_tools,
        max_retries=max_retries,
        strict_validation=True
    )

    return validator.validate_with_retry(query, original_intent, endpoint_url)


# Example usage and testing
if __name__ == "__main__":
    print("SPARQL Query Validation with Retry Logic")
    print("=" * 50)

    # Example problematic query
    test_query = """
    PREFIX dbo: <http://dbpedia.org/ontology/>
    SELECT ?person ?name WHERE {
        ?person a dbo:Person ;
                dbo:birthPlace dbr:Santa_Cruz,_California ;
                rdfs:label ?name .
    }
    LIMIT 5
    """

    print("Test query with URI syntax error:")
    print(test_query)

    # This would need actual LLM client to test
    print("\nValidation system is ready for integration!")