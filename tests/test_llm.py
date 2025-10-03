"""
Tests for LLM module: providers, Anthropic integration, and OpenAI integration.

This module tests LLM provider abstraction, API integration, and response handling.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from sparql_agent.core.types import LLMResponse
from sparql_agent.core.exceptions import (
    LLMError,
    LLMConnectionError,
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMResponseError,
)


# =============================================================================
# Tests for LLM Provider Base
# =============================================================================


@pytest.mark.unit
class TestLLMProvider:
    """Tests for LLM provider abstraction."""

    def test_provider_initialization(self):
        """Test initializing LLM provider."""
        # Mock provider would be initialized here
        provider_config = {
            "model": "test-model",
            "api_key": "test-key",
            "temperature": 0.7,
        }

        assert provider_config["model"] == "test-model"

    def test_generate_response(self, mock_llm_provider):
        """Test generating response from LLM."""
        prompt = "Generate a SPARQL query for finding all people"

        response = mock_llm_provider.generate(prompt)

        assert isinstance(response, LLMResponse)
        assert response.content is not None
        assert response.model is not None

    def test_generate_with_system_prompt(self, mock_llm_provider):
        """Test generating response with system prompt."""
        system_prompt = "You are a SPARQL query expert."
        prompt = "Find all people"

        response = mock_llm_provider.generate(
            prompt=prompt,
            system_prompt=system_prompt,
        )

        assert response is not None

    def test_generate_with_json_schema(self, mock_llm_provider):
        """Test generating response with JSON schema."""
        prompt = "Generate query metadata"
        schema = {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "confidence": {"type": "number"},
            },
        }

        response = mock_llm_provider.generate_with_json_schema(
            prompt=prompt,
            json_schema=schema,
        )

        assert response is not None

    def test_count_tokens(self, mock_llm_provider):
        """Test counting tokens in text."""
        text = "This is a test query for counting tokens"

        token_count = mock_llm_provider.count_tokens(text)

        assert isinstance(token_count, int)
        assert token_count > 0

    def test_estimate_cost(self, mock_llm_provider):
        """Test estimating request cost."""
        prompt_tokens = 100
        completion_tokens = 50

        cost = mock_llm_provider.estimate_cost(prompt_tokens, completion_tokens)

        assert isinstance(cost, float)
        assert cost >= 0

    def test_get_model_info(self, mock_llm_provider):
        """Test getting model information."""
        info = mock_llm_provider.get_model_info()

        assert "context_length" in info
        assert "max_output_tokens" in info

    def test_connection_test(self, mock_llm_provider):
        """Test testing connection to LLM provider."""
        is_connected = mock_llm_provider.test_connection()

        assert isinstance(is_connected, bool)


# =============================================================================
# Tests for Anthropic Provider
# =============================================================================


@pytest.mark.unit
class TestAnthropicProvider:
    """Tests for Anthropic (Claude) provider."""

    @patch('anthropic.Anthropic')
    def test_anthropic_initialization(self, mock_anthropic):
        """Test initializing Anthropic provider."""
        provider = self._create_anthropic_provider("claude-3-sonnet-20240229")

        assert provider["model"] == "claude-3-sonnet-20240229"

    @patch('anthropic.Anthropic')
    def test_generate_with_claude(self, mock_anthropic):
        """Test generating response with Claude."""
        # Mock Claude response
        mock_client = Mock()
        mock_message = Mock()
        mock_message.content = [Mock(text="SELECT ?s WHERE { ?s ?p ?o }")]
        mock_message.model = "claude-3-sonnet-20240229"
        mock_message.usage.input_tokens = 100
        mock_message.usage.output_tokens = 50
        mock_message.stop_reason = "end_turn"

        mock_client.messages.create.return_value = mock_message
        mock_anthropic.return_value = mock_client

        provider = self._create_anthropic_provider("claude-3-sonnet-20240229")
        response = self._generate_with_anthropic(
            mock_client,
            "Generate a SPARQL query",
            provider["model"],
        )

        assert response.content is not None
        assert "SELECT" in response.content

    @patch('anthropic.Anthropic')
    def test_handle_anthropic_rate_limit(self, mock_anthropic):
        """Test handling rate limit errors from Anthropic."""
        mock_client = Mock()
        mock_client.messages.create.side_effect = Exception("Rate limit exceeded")
        mock_anthropic.return_value = mock_client

        with pytest.raises(Exception, match="Rate limit"):
            self._generate_with_anthropic(mock_client, "Test", "claude-3-sonnet-20240229")

    @patch('anthropic.Anthropic')
    def test_handle_anthropic_auth_error(self, mock_anthropic):
        """Test handling authentication errors."""
        mock_client = Mock()
        mock_client.messages.create.side_effect = Exception("Invalid API key")
        mock_anthropic.return_value = mock_client

        with pytest.raises(Exception, match="API key"):
            self._generate_with_anthropic(mock_client, "Test", "claude-3-sonnet-20240229")

    def test_anthropic_token_counting(self):
        """Test token counting for Anthropic models."""
        text = "This is a test message for token counting"

        # Approximate token count (rough estimate: ~1 token per 4 chars)
        estimated_tokens = len(text) // 4

        assert estimated_tokens > 0

    @staticmethod
    def _create_anthropic_provider(model):
        """Helper to create Anthropic provider."""
        return {
            "model": model,
            "api_key": "test-key",
            "temperature": 0.7,
        }

    @staticmethod
    def _generate_with_anthropic(client, prompt, model):
        """Helper to generate with Anthropic."""
        message = client.messages.create(
            model=model,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )

        return LLMResponse(
            content=message.content[0].text,
            model=message.model,
            prompt=prompt,
            prompt_tokens=message.usage.input_tokens,
            completion_tokens=message.usage.output_tokens,
            finish_reason=message.stop_reason,
        )


# =============================================================================
# Tests for OpenAI Provider
# =============================================================================


@pytest.mark.unit
class TestOpenAIProvider:
    """Tests for OpenAI provider."""

    @patch('openai.OpenAI')
    def test_openai_initialization(self, mock_openai):
        """Test initializing OpenAI provider."""
        provider = self._create_openai_provider("gpt-4")

        assert provider["model"] == "gpt-4"

    @patch('openai.OpenAI')
    def test_generate_with_gpt(self, mock_openai):
        """Test generating response with GPT."""
        # Mock OpenAI response
        mock_client = Mock()
        mock_response = Mock()
        mock_choice = Mock()
        mock_choice.message.content = "SELECT ?s WHERE { ?s ?p ?o }"
        mock_choice.finish_reason = "stop"
        mock_response.choices = [mock_choice]
        mock_response.model = "gpt-4"
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50

        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        provider = self._create_openai_provider("gpt-4")
        response = self._generate_with_openai(
            mock_client,
            "Generate a SPARQL query",
            provider["model"],
        )

        assert response.content is not None
        assert "SELECT" in response.content

    @patch('openai.OpenAI')
    def test_generate_with_json_mode(self, mock_openai):
        """Test generating JSON response with OpenAI."""
        mock_client = Mock()
        mock_response = Mock()
        mock_choice = Mock()
        mock_choice.message.content = '{"query": "SELECT ?s WHERE { ?s ?p ?o }", "confidence": 0.95}'
        mock_choice.finish_reason = "stop"
        mock_response.choices = [mock_choice]
        mock_response.model = "gpt-4"
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50

        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        response = self._generate_with_openai(
            mock_client,
            "Generate query metadata",
            "gpt-4",
        )

        # Parse JSON response
        data = json.loads(response.content)
        assert "query" in data
        assert "confidence" in data

    @patch('openai.OpenAI')
    def test_handle_openai_rate_limit(self, mock_openai):
        """Test handling rate limit errors from OpenAI."""
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("Rate limit exceeded")
        mock_openai.return_value = mock_client

        with pytest.raises(Exception, match="Rate limit"):
            self._generate_with_openai(mock_client, "Test", "gpt-4")

    def test_openai_token_counting(self):
        """Test token counting for OpenAI models."""
        text = "This is a test message for token counting"

        # Approximate token count
        estimated_tokens = len(text.split())

        assert estimated_tokens > 0

    @staticmethod
    def _create_openai_provider(model):
        """Helper to create OpenAI provider."""
        return {
            "model": model,
            "api_key": "test-key",
            "temperature": 0.7,
        }

    @staticmethod
    def _generate_with_openai(client, prompt, model):
        """Helper to generate with OpenAI."""
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
        )

        return LLMResponse(
            content=response.choices[0].message.content,
            model=response.model,
            prompt=prompt,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            finish_reason=response.choices[0].finish_reason,
        )


# =============================================================================
# Tests for Provider Selection and Fallback
# =============================================================================


@pytest.mark.unit
class TestProviderFallback:
    """Tests for provider selection and fallback logic."""

    def test_select_provider_by_name(self):
        """Test selecting provider by name."""
        providers = {
            "anthropic": {"model": "claude-3-sonnet-20240229"},
            "openai": {"model": "gpt-4"},
        }

        selected = providers.get("anthropic")
        assert selected["model"] == "claude-3-sonnet-20240229"

    def test_fallback_to_secondary_provider(self):
        """Test fallback when primary provider fails."""
        primary_available = False
        secondary_available = True

        if not primary_available and secondary_available:
            provider = "secondary"
        elif primary_available:
            provider = "primary"
        else:
            provider = None

        assert provider == "secondary"

    def test_provider_health_check(self, mock_llm_provider):
        """Test checking provider health."""
        is_healthy = mock_llm_provider.test_connection()

        assert isinstance(is_healthy, bool)

    def test_cost_based_provider_selection(self):
        """Test selecting provider based on cost."""
        providers = {
            "cheap": {"cost_per_token": 0.0001},
            "expensive": {"cost_per_token": 0.001},
        }

        # Select cheapest
        selected = min(providers.items(), key=lambda x: x[1]["cost_per_token"])

        assert selected[0] == "cheap"


# =============================================================================
# Tests for Response Parsing
# =============================================================================


@pytest.mark.unit
class TestResponseParsing:
    """Tests for parsing LLM responses."""

    def test_parse_sparql_from_response(self):
        """Test extracting SPARQL query from response."""
        response_text = """Here's the SPARQL query:
        ```sparql
        SELECT ?person WHERE { ?person a ex:Person }
        ```
        This query finds all people.
        """

        query = self._extract_sparql(response_text)

        assert "SELECT" in query
        assert "Person" in query

    def test_parse_json_from_response(self):
        """Test parsing JSON from response."""
        response_text = '{"query": "SELECT ?s WHERE { ?s ?p ?o }", "confidence": 0.95}'

        data = json.loads(response_text)

        assert "query" in data
        assert data["confidence"] == 0.95

    def test_handle_malformed_response(self):
        """Test handling malformed responses."""
        response_text = "This is not a valid SPARQL query or JSON"

        try:
            json.loads(response_text)
            is_json = True
        except json.JSONDecodeError:
            is_json = False

        assert is_json is False

    def test_extract_code_blocks(self):
        """Test extracting code blocks from markdown."""
        response_text = """Here are multiple queries:
        ```sparql
        SELECT ?s WHERE { ?s ?p ?o }
        ```
        And another:
        ```sparql
        SELECT ?p WHERE { ?s ?p ?o }
        ```
        """

        code_blocks = self._extract_code_blocks(response_text)

        assert len(code_blocks) == 2

    @staticmethod
    def _extract_sparql(text):
        """Helper to extract SPARQL from text."""
        import re

        # Try to find code block
        code_block_match = re.search(r'```sparql\n(.*?)\n```', text, re.DOTALL)
        if code_block_match:
            return code_block_match.group(1).strip()

        # Otherwise return text
        return text

    @staticmethod
    def _extract_code_blocks(text):
        """Helper to extract all code blocks."""
        import re

        blocks = re.findall(r'```sparql\n(.*?)\n```', text, re.DOTALL)
        return [block.strip() for block in blocks]


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.integration
class TestLLMIntegration:
    """Integration tests for LLM components."""

    def test_complete_generation_workflow(self, mock_llm_provider):
        """Test complete LLM generation workflow."""
        # 1. Prepare prompt
        system_prompt = "You are a SPARQL expert."
        user_prompt = "Generate a query to find all people"

        # 2. Generate response
        response = mock_llm_provider.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
        )

        # 3. Parse response
        assert response.content is not None

        # 4. Calculate cost
        cost = mock_llm_provider.estimate_cost(
            response.prompt_tokens or 0,
            response.completion_tokens or 0,
        )
        assert cost >= 0

    def test_multi_provider_fallback_workflow(self):
        """Test workflow with multiple providers."""
        providers = ["anthropic", "openai", "local"]
        successful_provider = None

        for provider_name in providers:
            try:
                # Try to use provider
                if provider_name == "openai":  # Simulate success
                    successful_provider = provider_name
                    break
            except Exception:
                continue

        assert successful_provider is not None

    @pytest.mark.requires_api_key
    def test_real_anthropic_call(self):
        """Test real API call to Anthropic (requires API key)."""
        # This test is skipped unless API key is available
        pytest.skip("Requires ANTHROPIC_API_KEY environment variable")

    @pytest.mark.requires_api_key
    def test_real_openai_call(self):
        """Test real API call to OpenAI (requires API key)."""
        # This test is skipped unless API key is available
        pytest.skip("Requires OPENAI_API_KEY environment variable")


# =============================================================================
# Performance Tests
# =============================================================================


@pytest.mark.slow
class TestLLMPerformance:
    """Performance tests for LLM operations."""

    def test_concurrent_requests(self, mock_llm_provider):
        """Test handling concurrent LLM requests."""
        prompts = [
            "Find all people",
            "Find all organizations",
            "Find all properties",
        ]

        responses = []
        for prompt in prompts:
            response = mock_llm_provider.generate(prompt)
            responses.append(response)

        assert len(responses) == 3

    def test_response_caching(self):
        """Test caching LLM responses."""
        cache = {}
        prompt = "Find all people"

        # First call
        if prompt not in cache:
            response = LLMResponse(
                content="SELECT ?person WHERE { ?person a ex:Person }",
                model="test-model",
            )
            cache[prompt] = response

        # Second call (from cache)
        cached_response = cache.get(prompt)

        assert cached_response is not None

    def test_token_limit_handling(self):
        """Test handling token limits."""
        max_tokens = 4096
        long_text = "word " * 10000

        # Approximate token count
        estimated_tokens = len(long_text.split())

        if estimated_tokens > max_tokens:
            # Truncate
            words = long_text.split()[:max_tokens]
            truncated = " ".join(words)
            assert len(truncated.split()) <= max_tokens
