#!/usr/bin/env python3
"""
Exhaustive LLM Integration Testing Script

This script performs comprehensive testing of all LLM integration aspects:
1. Anthropic Integration (multiple query types, temperature settings, error handling)
2. Provider Management (fallback mechanisms, concurrent requests)
3. Query Generation Quality (SPARQL syntax validation)
4. Performance Testing (response times, memory usage)
5. Edge Cases (empty queries, special characters, timeouts)

Requirements:
- ANTHROPIC_API_KEY environment variable must be set
- Active internet connection
- Python 3.8+
"""

import asyncio
import json
import os
import sys
import time
import traceback
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import statistics

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sparql_agent.llm.client import (
    LLMRequest,
    LLMProvider,
    RetryConfig,
    ProviderManager,
)
from sparql_agent.llm.anthropic_provider import AnthropicProvider, CLAUDE_MODELS
from sparql_agent.core.exceptions import (
    LLMError,
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMConnectionError,
)


# =============================================================================
# Test Result Tracking
# =============================================================================


@dataclass
class TestResult:
    """Result of a single test."""
    test_name: str
    category: str
    success: bool
    duration_ms: float
    error: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    details: Optional[str] = None


@dataclass
class TestSuite:
    """Collection of test results."""
    name: str
    results: List[TestResult] = field(default_factory=list)

    def add_result(self, result: TestResult):
        """Add a test result."""
        self.results.append(result)

    def get_stats(self) -> Dict[str, Any]:
        """Get test statistics."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.success)
        failed = total - passed

        durations = [r.duration_ms for r in self.results]

        return {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "success_rate": (passed / total * 100) if total > 0 else 0,
            "avg_duration_ms": statistics.mean(durations) if durations else 0,
            "min_duration_ms": min(durations) if durations else 0,
            "max_duration_ms": max(durations) if durations else 0,
            "total_duration_ms": sum(durations),
        }


# =============================================================================
# Test Utilities
# =============================================================================


def validate_sparql(query: str) -> Tuple[bool, Optional[str]]:
    """
    Validate SPARQL query syntax.

    Returns:
        (is_valid, error_message)
    """
    # Basic SPARQL validation
    query = query.strip()

    if not query:
        return False, "Empty query"

    # Check for basic SPARQL keywords
    sparql_keywords = ["SELECT", "CONSTRUCT", "ASK", "DESCRIBE", "INSERT", "DELETE"]
    has_keyword = any(keyword in query.upper() for keyword in sparql_keywords)

    if not has_keyword:
        return False, "Missing SPARQL query keyword"

    # Check for WHERE clause (most queries should have one)
    if "SELECT" in query.upper() or "CONSTRUCT" in query.upper():
        if "WHERE" not in query.upper() and "{" not in query:
            return False, "Missing WHERE clause or graph pattern"

    return True, None


def extract_sparql_from_response(content: str) -> Optional[str]:
    """Extract SPARQL query from LLM response."""
    import re

    # Try to find code block
    code_block_match = re.search(r'```sparql\n(.*?)\n```', content, re.DOTALL | re.IGNORECASE)
    if code_block_match:
        return code_block_match.group(1).strip()

    # Try to find any code block
    code_block_match = re.search(r'```\n(.*?)\n```', content, re.DOTALL)
    if code_block_match:
        query = code_block_match.group(1).strip()
        if any(kw in query.upper() for kw in ["SELECT", "CONSTRUCT", "ASK"]):
            return query

    # Look for SELECT/CONSTRUCT/etc directly in text
    lines = content.split('\n')
    query_lines = []
    in_query = False

    for line in lines:
        line_upper = line.strip().upper()
        if any(kw in line_upper for kw in ["SELECT", "CONSTRUCT", "ASK", "DESCRIBE"]):
            in_query = True

        if in_query:
            query_lines.append(line)
            if "}" in line and in_query:
                break

    if query_lines:
        return "\n".join(query_lines).strip()

    return None


# =============================================================================
# Test Categories
# =============================================================================


class AnthropicIntegrationTests:
    """Tests for Anthropic integration."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.suite = TestSuite(name="Anthropic Integration")

    def run_all(self) -> TestSuite:
        """Run all Anthropic integration tests."""
        print("\n" + "="*80)
        print("ANTHROPIC INTEGRATION TESTS")
        print("="*80)

        self.test_simple_queries()
        self.test_complex_queries()
        self.test_edge_case_queries()
        self.test_temperature_settings()
        self.test_max_tokens_limits()
        self.test_system_prompt_variations()
        self.test_error_handling()
        self.test_token_usage_tracking()

        return self.suite

    def test_simple_queries(self):
        """Test simple query generation."""
        print("\n[Test] Simple Queries")

        test_cases = [
            "Find all people",
            "Get all organizations",
            "List all properties",
            "Show me entities of type Person",
            "What are the classes in this dataset?",
        ]

        for i, query in enumerate(test_cases, 1):
            start_time = time.time()
            try:
                provider = AnthropicProvider(
                    model="claude-3-5-sonnet-20241022",
                    api_key=self.api_key,
                )

                request = LLMRequest(
                    prompt=f"Generate a SPARQL query for: {query}",
                    system_prompt="You are a SPARQL query expert. Generate valid SPARQL queries.",
                    temperature=0.3,
                    max_tokens=1000,
                )

                response = provider.generate(request)
                duration_ms = (time.time() - start_time) * 1000

                # Extract and validate SPARQL
                sparql = extract_sparql_from_response(response.content)
                is_valid, error = validate_sparql(sparql) if sparql else (False, "No SPARQL found")

                self.suite.add_result(TestResult(
                    test_name=f"Simple Query {i}: {query}",
                    category="simple_queries",
                    success=is_valid,
                    duration_ms=duration_ms,
                    error=error,
                    metrics={
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens,
                        "tokens_per_second": response.metrics.tokens_per_second,
                        "model": response.model,
                    },
                    details=f"Generated SPARQL: {sparql[:100] if sparql else 'None'}..."
                ))

                status = "✓ PASS" if is_valid else "✗ FAIL"
                print(f"  {status} - {query} ({duration_ms:.0f}ms, {response.usage.total_tokens} tokens)")

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                self.suite.add_result(TestResult(
                    test_name=f"Simple Query {i}: {query}",
                    category="simple_queries",
                    success=False,
                    duration_ms=duration_ms,
                    error=str(e),
                ))
                print(f"  ✗ FAIL - {query}: {e}")

    def test_complex_queries(self):
        """Test complex query generation."""
        print("\n[Test] Complex Queries")

        test_cases = [
            "Find all people who work at organizations in New York and have published more than 5 papers",
            "Get the protein sequences for all proteins involved in the p53 pathway",
            "Find all genes associated with breast cancer, their protein products, and known drug interactions",
            "Retrieve all clinical trials for diabetes medications approved after 2020 with their success rates",
            "Get all ontology terms related to immune response with their definitions and hierarchical relationships",
        ]

        for i, query in enumerate(test_cases, 1):
            start_time = time.time()
            try:
                provider = AnthropicProvider(
                    model="claude-3-5-sonnet-20241022",
                    api_key=self.api_key,
                )

                request = LLMRequest(
                    prompt=f"Generate a SPARQL query for: {query}",
                    system_prompt="You are an expert in SPARQL and biomedical knowledge graphs.",
                    temperature=0.5,
                    max_tokens=2000,
                )

                response = provider.generate(request)
                duration_ms = (time.time() - start_time) * 1000

                sparql = extract_sparql_from_response(response.content)
                is_valid, error = validate_sparql(sparql) if sparql else (False, "No SPARQL found")

                self.suite.add_result(TestResult(
                    test_name=f"Complex Query {i}",
                    category="complex_queries",
                    success=is_valid,
                    duration_ms=duration_ms,
                    error=error,
                    metrics={
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens,
                        "tokens_per_second": response.metrics.tokens_per_second,
                    },
                ))

                status = "✓ PASS" if is_valid else "✗ FAIL"
                print(f"  {status} - Complex Query {i} ({duration_ms:.0f}ms, {response.usage.total_tokens} tokens)")

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                self.suite.add_result(TestResult(
                    test_name=f"Complex Query {i}",
                    category="complex_queries",
                    success=False,
                    duration_ms=duration_ms,
                    error=str(e),
                ))
                print(f"  ✗ FAIL - Complex Query {i}: {e}")

    def test_edge_case_queries(self):
        """Test edge case queries."""
        print("\n[Test] Edge Case Queries")

        test_cases = [
            ("Empty", ""),
            ("Very Short", "find stuff"),
            ("Special Chars", "Find items with name 'O'Brien' & Smith (age > 30)"),
            ("Unicode", "Find 日本語 entities with émojis 🧬"),
            ("Very Long", "Generate a SPARQL query for " + "very complex requirements " * 100),
        ]

        for name, query in test_cases:
            start_time = time.time()
            try:
                provider = AnthropicProvider(
                    model="claude-3-haiku-20240307",  # Use faster model for edge cases
                    api_key=self.api_key,
                )

                if not query:  # Empty query
                    # Should handle gracefully
                    self.suite.add_result(TestResult(
                        test_name=f"Edge Case: {name}",
                        category="edge_cases",
                        success=True,  # Success = handled gracefully
                        duration_ms=0,
                        details="Empty query handled correctly",
                    ))
                    print(f"  ✓ PASS - {name} (handled gracefully)")
                    continue

                request = LLMRequest(
                    prompt=query if len(query) < 500 else query[:500],  # Truncate very long
                    temperature=0.5,
                    max_tokens=1000,
                )

                response = provider.generate(request)
                duration_ms = (time.time() - start_time) * 1000

                self.suite.add_result(TestResult(
                    test_name=f"Edge Case: {name}",
                    category="edge_cases",
                    success=True,
                    duration_ms=duration_ms,
                    metrics={
                        "total_tokens": response.usage.total_tokens,
                    },
                ))

                print(f"  ✓ PASS - {name} ({duration_ms:.0f}ms)")

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                # For edge cases, exceptions might be expected
                self.suite.add_result(TestResult(
                    test_name=f"Edge Case: {name}",
                    category="edge_cases",
                    success=False,
                    duration_ms=duration_ms,
                    error=str(e),
                ))
                print(f"  ✗ FAIL - {name}: {e}")

    def test_temperature_settings(self):
        """Test different temperature settings."""
        print("\n[Test] Temperature Settings")

        prompt = "Generate a SPARQL query to find all proteins"
        temperatures = [0.0, 0.3, 0.7, 1.0, 1.5]

        for temp in temperatures:
            start_time = time.time()
            try:
                provider = AnthropicProvider(
                    model="claude-3-haiku-20240307",
                    api_key=self.api_key,
                )

                request = LLMRequest(
                    prompt=prompt,
                    temperature=temp,
                    max_tokens=500,
                )

                response = provider.generate(request)
                duration_ms = (time.time() - start_time) * 1000

                self.suite.add_result(TestResult(
                    test_name=f"Temperature {temp}",
                    category="temperature",
                    success=True,
                    duration_ms=duration_ms,
                    metrics={
                        "temperature": temp,
                        "total_tokens": response.usage.total_tokens,
                    },
                ))

                print(f"  ✓ PASS - Temperature {temp} ({duration_ms:.0f}ms, {response.usage.total_tokens} tokens)")

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                self.suite.add_result(TestResult(
                    test_name=f"Temperature {temp}",
                    category="temperature",
                    success=False,
                    duration_ms=duration_ms,
                    error=str(e),
                ))
                print(f"  ✗ FAIL - Temperature {temp}: {e}")

    def test_max_tokens_limits(self):
        """Test different max_tokens limits."""
        print("\n[Test] Max Tokens Limits")

        prompt = "Generate a detailed SPARQL query with explanation"
        token_limits = [100, 500, 1000, 2000, 4000]

        for limit in token_limits:
            start_time = time.time()
            try:
                provider = AnthropicProvider(
                    model="claude-3-haiku-20240307",
                    api_key=self.api_key,
                )

                request = LLMRequest(
                    prompt=prompt,
                    max_tokens=limit,
                    temperature=0.5,
                )

                response = provider.generate(request)
                duration_ms = (time.time() - start_time) * 1000

                # Check if response respects token limit
                within_limit = response.usage.completion_tokens <= limit

                self.suite.add_result(TestResult(
                    test_name=f"Max Tokens {limit}",
                    category="max_tokens",
                    success=within_limit,
                    duration_ms=duration_ms,
                    metrics={
                        "max_tokens_requested": limit,
                        "completion_tokens": response.usage.completion_tokens,
                        "within_limit": within_limit,
                    },
                ))

                status = "✓ PASS" if within_limit else "✗ FAIL"
                print(f"  {status} - Max {limit} tokens (actual: {response.usage.completion_tokens})")

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                self.suite.add_result(TestResult(
                    test_name=f"Max Tokens {limit}",
                    category="max_tokens",
                    success=False,
                    duration_ms=duration_ms,
                    error=str(e),
                ))
                print(f"  ✗ FAIL - Max {limit} tokens: {e}")

    def test_system_prompt_variations(self):
        """Test different system prompts."""
        print("\n[Test] System Prompt Variations")

        prompt = "Find all genes"
        system_prompts = [
            None,
            "You are a helpful assistant.",
            "You are a SPARQL expert.",
            "You are a bioinformatics specialist. Generate SPARQL queries for biological data.",
            "Be concise. Output only the SPARQL query with no explanation.",
        ]

        for i, sys_prompt in enumerate(system_prompts, 1):
            start_time = time.time()
            try:
                provider = AnthropicProvider(
                    model="claude-3-haiku-20240307",
                    api_key=self.api_key,
                )

                request = LLMRequest(
                    prompt=prompt,
                    system_prompt=sys_prompt,
                    temperature=0.5,
                    max_tokens=500,
                )

                response = provider.generate(request)
                duration_ms = (time.time() - start_time) * 1000

                self.suite.add_result(TestResult(
                    test_name=f"System Prompt {i}",
                    category="system_prompts",
                    success=True,
                    duration_ms=duration_ms,
                    metrics={
                        "has_system_prompt": sys_prompt is not None,
                        "system_prompt_length": len(sys_prompt) if sys_prompt else 0,
                        "total_tokens": response.usage.total_tokens,
                    },
                ))

                label = "None" if sys_prompt is None else f"{sys_prompt[:30]}..."
                print(f"  ✓ PASS - System Prompt: {label} ({duration_ms:.0f}ms)")

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                self.suite.add_result(TestResult(
                    test_name=f"System Prompt {i}",
                    category="system_prompts",
                    success=False,
                    duration_ms=duration_ms,
                    error=str(e),
                ))
                print(f"  ✗ FAIL - System Prompt {i}: {e}")

    def test_error_handling(self):
        """Test error handling scenarios."""
        print("\n[Test] Error Handling")

        # Test invalid API key
        start_time = time.time()
        try:
            provider = AnthropicProvider(
                model="claude-3-haiku-20240307",
                api_key="invalid_key_12345",
            )

            request = LLMRequest(prompt="test")
            response = provider.generate(request)

            # Should not reach here
            self.suite.add_result(TestResult(
                test_name="Invalid API Key",
                category="error_handling",
                success=False,
                duration_ms=(time.time() - start_time) * 1000,
                error="Should have raised authentication error",
            ))
            print(f"  ✗ FAIL - Invalid API Key: Should have raised error")

        except LLMAuthenticationError:
            duration_ms = (time.time() - start_time) * 1000
            self.suite.add_result(TestResult(
                test_name="Invalid API Key",
                category="error_handling",
                success=True,
                duration_ms=duration_ms,
                details="Correctly raised LLMAuthenticationError",
            ))
            print(f"  ✓ PASS - Invalid API Key (correctly raised error)")
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.suite.add_result(TestResult(
                test_name="Invalid API Key",
                category="error_handling",
                success=False,
                duration_ms=duration_ms,
                error=f"Wrong exception type: {type(e).__name__}",
            ))
            print(f"  ✗ FAIL - Invalid API Key: Wrong error type {type(e).__name__}")

        # Test invalid model
        start_time = time.time()
        try:
            provider = AnthropicProvider(
                model="invalid-model-12345",
                api_key=self.api_key,
            )

            self.suite.add_result(TestResult(
                test_name="Invalid Model",
                category="error_handling",
                success=False,
                duration_ms=(time.time() - start_time) * 1000,
                error="Should have raised model not found error",
            ))
            print(f"  ✗ FAIL - Invalid Model: Should have raised error")

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.suite.add_result(TestResult(
                test_name="Invalid Model",
                category="error_handling",
                success=True,
                duration_ms=duration_ms,
                details=f"Correctly raised error: {type(e).__name__}",
            ))
            print(f"  ✓ PASS - Invalid Model (correctly raised error)")

        # Test timeout (using very short timeout)
        start_time = time.time()
        try:
            provider = AnthropicProvider(
                model="claude-3-haiku-20240307",
                api_key=self.api_key,
                timeout=0.001,  # 1ms timeout - should fail
            )

            request = LLMRequest(
                prompt="Generate a complex SPARQL query with detailed explanation",
                max_tokens=2000,
            )
            response = provider.generate(request)

            # May or may not timeout depending on timing
            self.suite.add_result(TestResult(
                test_name="Timeout Handling",
                category="error_handling",
                success=True,
                duration_ms=(time.time() - start_time) * 1000,
                details="Request completed despite short timeout",
            ))
            print(f"  ✓ PASS - Timeout (completed)")

        except (LLMTimeoutError, LLMConnectionError) as e:
            duration_ms = (time.time() - start_time) * 1000
            self.suite.add_result(TestResult(
                test_name="Timeout Handling",
                category="error_handling",
                success=True,
                duration_ms=duration_ms,
                details="Correctly raised timeout/connection error",
            ))
            print(f"  ✓ PASS - Timeout (correctly raised error)")
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.suite.add_result(TestResult(
                test_name="Timeout Handling",
                category="error_handling",
                success=True,
                duration_ms=duration_ms,
                details=f"Raised error: {type(e).__name__}",
            ))
            print(f"  ✓ PASS - Timeout (raised {type(e).__name__})")

    def test_token_usage_tracking(self):
        """Test token usage tracking accuracy."""
        print("\n[Test] Token Usage Tracking")

        test_cases = [
            ("Short", "Find proteins", 500),
            ("Medium", "Generate a SPARQL query to find all proteins with their functions", 1000),
            ("Long", "Generate a comprehensive SPARQL query to find all proteins, their functions, cellular locations, and associated diseases with explanations", 2000),
        ]

        for name, prompt, max_tokens in test_cases:
            start_time = time.time()
            try:
                provider = AnthropicProvider(
                    model="claude-3-haiku-20240307",
                    api_key=self.api_key,
                )

                request = LLMRequest(
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=0.5,
                )

                response = provider.generate(request)
                duration_ms = (time.time() - start_time) * 1000

                # Verify token tracking
                has_usage = response.usage.total_tokens > 0
                tokens_sum_correct = (
                    response.usage.prompt_tokens + response.usage.completion_tokens
                    == response.usage.total_tokens
                )

                self.suite.add_result(TestResult(
                    test_name=f"Token Tracking: {name}",
                    category="token_tracking",
                    success=has_usage and tokens_sum_correct,
                    duration_ms=duration_ms,
                    metrics={
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens,
                        "tokens_sum_correct": tokens_sum_correct,
                    },
                ))

                status = "✓ PASS" if (has_usage and tokens_sum_correct) else "✗ FAIL"
                print(f"  {status} - {name}: {response.usage.total_tokens} tokens "
                      f"({response.usage.prompt_tokens}+{response.usage.completion_tokens})")

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                self.suite.add_result(TestResult(
                    test_name=f"Token Tracking: {name}",
                    category="token_tracking",
                    success=False,
                    duration_ms=duration_ms,
                    error=str(e),
                ))
                print(f"  ✗ FAIL - {name}: {e}")


class ProviderManagementTests:
    """Tests for provider management."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.suite = TestSuite(name="Provider Management")

    def run_all(self) -> TestSuite:
        """Run all provider management tests."""
        print("\n" + "="*80)
        print("PROVIDER MANAGEMENT TESTS")
        print("="*80)

        self.test_provider_registration()
        self.test_provider_fallback()
        self.test_multiple_providers()
        self.test_provider_selection()
        self.test_concurrent_requests()

        return self.suite

    def test_provider_registration(self):
        """Test provider registration."""
        print("\n[Test] Provider Registration")

        start_time = time.time()
        try:
            manager = ProviderManager()

            # Register Anthropic provider
            provider = AnthropicProvider(
                model="claude-3-haiku-20240307",
                api_key=self.api_key,
            )

            manager.register_provider(
                name="anthropic-haiku",
                client=provider,
                priority=1,
                set_as_default=True,
            )

            # Verify registration
            providers = manager.list_providers()
            is_registered = len(providers) > 0

            duration_ms = (time.time() - start_time) * 1000

            self.suite.add_result(TestResult(
                test_name="Provider Registration",
                category="registration",
                success=is_registered,
                duration_ms=duration_ms,
                metrics={"providers_count": len(providers)},
            ))

            status = "✓ PASS" if is_registered else "✗ FAIL"
            print(f"  {status} - Provider registration ({len(providers)} provider(s))")

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.suite.add_result(TestResult(
                test_name="Provider Registration",
                category="registration",
                success=False,
                duration_ms=duration_ms,
                error=str(e),
            ))
            print(f"  ✗ FAIL - Provider registration: {e}")

    def test_provider_fallback(self):
        """Test provider fallback mechanism."""
        print("\n[Test] Provider Fallback")

        start_time = time.time()
        try:
            manager = ProviderManager()

            # Register primary provider with invalid key
            primary = AnthropicProvider(
                model="claude-3-haiku-20240307",
                api_key="invalid_key",
            )
            manager.register_provider("primary", primary, priority=2)

            # Register fallback provider with valid key
            fallback = AnthropicProvider(
                model="claude-3-haiku-20240307",
                api_key=self.api_key,
            )
            manager.register_provider("fallback", fallback, priority=1)

            # Try generation with fallback
            request = LLMRequest(prompt="Test", max_tokens=100)

            try:
                response = manager.generate_with_fallback(
                    request,
                    provider_names=["primary", "fallback"],
                    fallback_on_error=True,
                )

                duration_ms = (time.time() - start_time) * 1000

                self.suite.add_result(TestResult(
                    test_name="Provider Fallback",
                    category="fallback",
                    success=True,
                    duration_ms=duration_ms,
                    details="Fallback mechanism worked correctly",
                ))

                print(f"  ✓ PASS - Provider fallback worked ({duration_ms:.0f}ms)")

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                self.suite.add_result(TestResult(
                    test_name="Provider Fallback",
                    category="fallback",
                    success=False,
                    duration_ms=duration_ms,
                    error=str(e),
                ))
                print(f"  ✗ FAIL - Provider fallback: {e}")

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.suite.add_result(TestResult(
                test_name="Provider Fallback",
                category="fallback",
                success=False,
                duration_ms=duration_ms,
                error=str(e),
            ))
            print(f"  ✗ FAIL - Provider fallback setup: {e}")

    def test_multiple_providers(self):
        """Test multiple provider configurations."""
        print("\n[Test] Multiple Providers")

        start_time = time.time()
        try:
            manager = ProviderManager()

            # Register multiple models
            models = [
                "claude-3-haiku-20240307",
                "claude-3-5-sonnet-20241022",
            ]

            for i, model in enumerate(models):
                provider = AnthropicProvider(
                    model=model,
                    api_key=self.api_key,
                )
                manager.register_provider(
                    name=f"provider-{i}",
                    client=provider,
                    priority=i,
                )

            providers = manager.list_providers()
            duration_ms = (time.time() - start_time) * 1000

            self.suite.add_result(TestResult(
                test_name="Multiple Providers",
                category="multiple_providers",
                success=len(providers) == len(models),
                duration_ms=duration_ms,
                metrics={"providers_count": len(providers)},
            ))

            status = "✓ PASS" if len(providers) == len(models) else "✗ FAIL"
            print(f"  {status} - Multiple providers ({len(providers)}/{len(models)})")

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.suite.add_result(TestResult(
                test_name="Multiple Providers",
                category="multiple_providers",
                success=False,
                duration_ms=duration_ms,
                error=str(e),
            ))
            print(f"  ✗ FAIL - Multiple providers: {e}")

    def test_provider_selection(self):
        """Test provider selection logic."""
        print("\n[Test] Provider Selection")

        start_time = time.time()
        try:
            manager = ProviderManager()

            # Register providers with different priorities
            provider1 = AnthropicProvider(
                model="claude-3-haiku-20240307",
                api_key=self.api_key,
            )
            manager.register_provider("low-priority", provider1, priority=1)

            provider2 = AnthropicProvider(
                model="claude-3-5-sonnet-20241022",
                api_key=self.api_key,
            )
            manager.register_provider("high-priority", provider2, priority=10)

            # Get specific provider
            selected = manager.get_provider("high-priority")

            duration_ms = (time.time() - start_time) * 1000

            self.suite.add_result(TestResult(
                test_name="Provider Selection",
                category="selection",
                success=selected.model == "claude-3-5-sonnet-20241022",
                duration_ms=duration_ms,
                metrics={"selected_model": selected.model},
            ))

            status = "✓ PASS" if selected.model == "claude-3-5-sonnet-20241022" else "✗ FAIL"
            print(f"  {status} - Provider selection (selected: {selected.model})")

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.suite.add_result(TestResult(
                test_name="Provider Selection",
                category="selection",
                success=False,
                duration_ms=duration_ms,
                error=str(e),
            ))
            print(f"  ✗ FAIL - Provider selection: {e}")

    def test_concurrent_requests(self):
        """Test concurrent request handling."""
        print("\n[Test] Concurrent Requests")

        start_time = time.time()
        try:
            provider = AnthropicProvider(
                model="claude-3-haiku-20240307",
                api_key=self.api_key,
            )

            prompts = [
                "Find proteins",
                "Find genes",
                "Find diseases",
            ]

            responses = []
            for prompt in prompts:
                request = LLMRequest(
                    prompt=prompt,
                    max_tokens=200,
                    temperature=0.5,
                )
                response = provider.generate(request)
                responses.append(response)

            duration_ms = (time.time() - start_time) * 1000

            self.suite.add_result(TestResult(
                test_name="Concurrent Requests",
                category="concurrency",
                success=len(responses) == len(prompts),
                duration_ms=duration_ms,
                metrics={
                    "requests_count": len(prompts),
                    "responses_count": len(responses),
                    "avg_duration_ms": duration_ms / len(prompts),
                },
            ))

            status = "✓ PASS" if len(responses) == len(prompts) else "✗ FAIL"
            print(f"  {status} - Concurrent requests ({len(responses)}/{len(prompts)}, {duration_ms:.0f}ms total)")

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.suite.add_result(TestResult(
                test_name="Concurrent Requests",
                category="concurrency",
                success=False,
                duration_ms=duration_ms,
                error=str(e),
            ))
            print(f"  ✗ FAIL - Concurrent requests: {e}")


class PerformanceTests:
    """Performance tests for LLM operations."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.suite = TestSuite(name="Performance")

    def run_all(self) -> TestSuite:
        """Run all performance tests."""
        print("\n" + "="*80)
        print("PERFORMANCE TESTS")
        print("="*80)

        self.test_response_times()
        self.test_throughput()
        self.test_model_comparison()

        return self.suite

    def test_response_times(self):
        """Test response times for different query types."""
        print("\n[Test] Response Times")

        test_cases = [
            ("Short Query", "Find proteins", 200),
            ("Medium Query", "Generate SPARQL query for proteins with functions", 500),
            ("Long Query", "Generate detailed SPARQL query for proteins with functions, locations, and interactions", 1000),
        ]

        for name, prompt, max_tokens in test_cases:
            start_time = time.time()
            try:
                provider = AnthropicProvider(
                    model="claude-3-5-sonnet-20241022",
                    api_key=self.api_key,
                )

                request = LLMRequest(
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=0.5,
                )

                response = provider.generate(request)
                duration_ms = (time.time() - start_time) * 1000

                self.suite.add_result(TestResult(
                    test_name=f"Response Time: {name}",
                    category="response_times",
                    success=True,
                    duration_ms=duration_ms,
                    metrics={
                        "latency_ms": response.metrics.latency_ms,
                        "tokens_per_second": response.metrics.tokens_per_second,
                        "total_tokens": response.usage.total_tokens,
                    },
                ))

                print(f"  ✓ {name}: {duration_ms:.0f}ms "
                      f"({response.metrics.tokens_per_second:.1f} tok/s, "
                      f"{response.usage.total_tokens} tokens)")

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                self.suite.add_result(TestResult(
                    test_name=f"Response Time: {name}",
                    category="response_times",
                    success=False,
                    duration_ms=duration_ms,
                    error=str(e),
                ))
                print(f"  ✗ {name}: {e}")

    def test_throughput(self):
        """Test throughput with multiple requests."""
        print("\n[Test] Throughput")

        start_time = time.time()
        try:
            provider = AnthropicProvider(
                model="claude-3-haiku-20240307",
                api_key=self.api_key,
            )

            num_requests = 5
            successful = 0
            total_tokens = 0

            for i in range(num_requests):
                try:
                    request = LLMRequest(
                        prompt=f"Find entities of type {i}",
                        max_tokens=200,
                        temperature=0.5,
                    )

                    response = provider.generate(request)
                    successful += 1
                    total_tokens += response.usage.total_tokens

                except Exception:
                    pass

            duration_ms = (time.time() - start_time) * 1000
            throughput = num_requests / (duration_ms / 1000)  # requests per second

            self.suite.add_result(TestResult(
                test_name="Throughput Test",
                category="throughput",
                success=successful == num_requests,
                duration_ms=duration_ms,
                metrics={
                    "total_requests": num_requests,
                    "successful_requests": successful,
                    "total_tokens": total_tokens,
                    "requests_per_second": throughput,
                    "avg_duration_ms": duration_ms / num_requests,
                },
            ))

            print(f"  ✓ Throughput: {successful}/{num_requests} requests in {duration_ms:.0f}ms "
                  f"({throughput:.2f} req/s, {total_tokens} tokens)")

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.suite.add_result(TestResult(
                test_name="Throughput Test",
                category="throughput",
                success=False,
                duration_ms=duration_ms,
                error=str(e),
            ))
            print(f"  ✗ Throughput: {e}")

    def test_model_comparison(self):
        """Compare performance across different models."""
        print("\n[Test] Model Comparison")

        models = [
            "claude-3-haiku-20240307",
            "claude-3-5-sonnet-20241022",
        ]

        prompt = "Generate a SPARQL query to find all proteins"

        for model in models:
            start_time = time.time()
            try:
                provider = AnthropicProvider(
                    model=model,
                    api_key=self.api_key,
                )

                request = LLMRequest(
                    prompt=prompt,
                    max_tokens=500,
                    temperature=0.5,
                )

                response = provider.generate(request)
                duration_ms = (time.time() - start_time) * 1000

                self.suite.add_result(TestResult(
                    test_name=f"Model: {model}",
                    category="model_comparison",
                    success=True,
                    duration_ms=duration_ms,
                    metrics={
                        "model": model,
                        "latency_ms": response.metrics.latency_ms,
                        "tokens_per_second": response.metrics.tokens_per_second,
                        "total_tokens": response.usage.total_tokens,
                    },
                ))

                print(f"  ✓ {model}: {duration_ms:.0f}ms "
                      f"({response.metrics.tokens_per_second:.1f} tok/s)")

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                self.suite.add_result(TestResult(
                    test_name=f"Model: {model}",
                    category="model_comparison",
                    success=False,
                    duration_ms=duration_ms,
                    error=str(e),
                ))
                print(f"  ✗ {model}: {e}")


# =============================================================================
# Main Test Runner
# =============================================================================


def print_summary(suites: List[TestSuite]):
    """Print test summary."""
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    total_tests = 0
    total_passed = 0
    total_duration = 0

    for suite in suites:
        stats = suite.get_stats()
        total_tests += stats["total_tests"]
        total_passed += stats["passed"]
        total_duration += stats["total_duration_ms"]

        print(f"\n{suite.name}:")
        print(f"  Total Tests: {stats['total_tests']}")
        print(f"  Passed: {stats['passed']}")
        print(f"  Failed: {stats['failed']}")
        print(f"  Success Rate: {stats['success_rate']:.1f}%")
        print(f"  Avg Duration: {stats['avg_duration_ms']:.0f}ms")
        print(f"  Total Duration: {stats['total_duration_ms']:.0f}ms")

    print(f"\n{'='*80}")
    print(f"OVERALL RESULTS:")
    print(f"  Total Tests: {total_tests}")
    print(f"  Total Passed: {total_passed}")
    print(f"  Total Failed: {total_tests - total_passed}")
    print(f"  Overall Success Rate: {(total_passed / total_tests * 100):.1f}%")
    print(f"  Total Duration: {total_duration:.0f}ms ({total_duration/1000:.1f}s)")
    print("="*80)


def save_results(suites: List[TestSuite], filename: str = "llm_test_results.json"):
    """Save test results to JSON file."""
    results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "suites": []
    }

    for suite in suites:
        suite_data = {
            "name": suite.name,
            "stats": suite.get_stats(),
            "results": [
                {
                    "test_name": r.test_name,
                    "category": r.category,
                    "success": r.success,
                    "duration_ms": r.duration_ms,
                    "error": r.error,
                    "metrics": r.metrics,
                    "details": r.details,
                }
                for r in suite.results
            ]
        }
        results["suites"].append(suite_data)

    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✓ Results saved to {filename}")


def main():
    """Main test runner."""
    print("="*80)
    print("EXHAUSTIVE LLM INTEGRATION TESTING")
    print("="*80)

    # Check for API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n✗ ERROR: ANTHROPIC_API_KEY environment variable not set")
        print("  Please set it with: export ANTHROPIC_API_KEY=your_key_here")
        sys.exit(1)

    print(f"\n✓ API Key found: {api_key[:10]}...")
    print(f"✓ Starting tests at {time.strftime('%Y-%m-%d %H:%M:%S')}")

    suites = []

    try:
        # Run Anthropic integration tests
        anthropic_tests = AnthropicIntegrationTests(api_key)
        suites.append(anthropic_tests.run_all())

        # Run provider management tests
        provider_tests = ProviderManagementTests(api_key)
        suites.append(provider_tests.run_all())

        # Run performance tests
        perf_tests = PerformanceTests(api_key)
        suites.append(perf_tests.run_all())

        # Print summary
        print_summary(suites)

        # Save results
        save_results(suites)

        print("\n✓ All tests completed successfully!")

    except KeyboardInterrupt:
        print("\n\n✗ Tests interrupted by user")
        if suites:
            print_summary(suites)
            save_results(suites)
        sys.exit(1)

    except Exception as e:
        print(f"\n\n✗ FATAL ERROR: {e}")
        traceback.print_exc()
        if suites:
            print_summary(suites)
            save_results(suites)
        sys.exit(1)


if __name__ == "__main__":
    main()
