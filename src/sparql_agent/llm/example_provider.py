"""
Example LLM Provider Implementation.

This module demonstrates how to implement custom LLM providers by extending
the LLMClient abstract base class. Includes examples for OpenAI-compatible APIs
and mock providers for testing.
"""

from typing import Iterator, Optional
import time
import logging

from .client import (
    LLMClient,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    StreamChunk,
    StreamChunkType,
    TokenUsage,
    GenerationMetrics,
    ModelCapabilities,
    RetryConfig,
)
from ..core.exceptions import (
    LLMError,
    LLMConnectionError,
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMTimeoutError,
)

logger = logging.getLogger(__name__)


# ============================================================================
# OpenAI Provider Example
# ============================================================================


class OpenAIClient(LLMClient):
    """
    OpenAI LLM client implementation.

    Supports GPT-3.5, GPT-4, and other OpenAI models with streaming,
    function calling, and vision capabilities.
    """

    def __init__(
        self,
        model: str = "gpt-4",
        api_key: Optional[str] = None,
        organization: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize OpenAI client.

        Args:
            model: Model name (e.g., 'gpt-4', 'gpt-3.5-turbo')
            api_key: OpenAI API key
            organization: OpenAI organization ID
            **kwargs: Additional parameters
        """
        super().__init__(
            model=model,
            api_key=api_key,
            **kwargs
        )
        self.organization = organization
        self._client = None

    def get_provider(self) -> LLMProvider:
        """Return OpenAI provider type."""
        return LLMProvider.OPENAI

    def get_capabilities(self) -> ModelCapabilities:
        """Return model capabilities based on model name."""
        # Model-specific capabilities
        capabilities_map = {
            "gpt-4": ModelCapabilities(
                supports_streaming=True,
                supports_function_calling=True,
                supports_vision=False,
                supports_json_mode=True,
                max_context_length=8192,
                max_output_tokens=4096,
                supports_system_message=True,
                cost_per_1k_prompt_tokens=0.03,
                cost_per_1k_completion_tokens=0.06,
            ),
            "gpt-4-turbo": ModelCapabilities(
                supports_streaming=True,
                supports_function_calling=True,
                supports_vision=True,
                supports_json_mode=True,
                max_context_length=128000,
                max_output_tokens=4096,
                supports_system_message=True,
                cost_per_1k_prompt_tokens=0.01,
                cost_per_1k_completion_tokens=0.03,
            ),
            "gpt-3.5-turbo": ModelCapabilities(
                supports_streaming=True,
                supports_function_calling=True,
                supports_vision=False,
                supports_json_mode=True,
                max_context_length=16385,
                max_output_tokens=4096,
                supports_system_message=True,
                cost_per_1k_prompt_tokens=0.0015,
                cost_per_1k_completion_tokens=0.002,
            ),
        }

        # Return specific capabilities or default
        for key in capabilities_map:
            if key in self.model:
                return capabilities_map[key]

        # Default capabilities
        return ModelCapabilities(
            supports_streaming=True,
            supports_function_calling=True,
            max_context_length=4096,
            max_output_tokens=2048,
        )

    def _get_client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            try:
                import openai
                self._client = openai.OpenAI(
                    api_key=self.api_key,
                    organization=self.organization,
                    timeout=self.timeout,
                )
            except ImportError:
                raise LLMError(
                    "OpenAI package not installed. Install with: pip install openai"
                )
        return self._client

    def _generate_impl(self, request: LLMRequest) -> LLMResponse:
        """OpenAI-specific generation implementation."""
        client = self._get_client()

        # Build messages
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        # Prepare API call parameters
        params = {
            "model": self.model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
        }

        if request.stop_sequences:
            params["stop"] = request.stop_sequences
        if request.frequency_penalty:
            params["frequency_penalty"] = request.frequency_penalty
        if request.presence_penalty:
            params["presence_penalty"] = request.presence_penalty
        if request.seed is not None:
            params["seed"] = request.seed
        if request.tools:
            params["tools"] = request.tools
        if request.response_format == "json":
            params["response_format"] = {"type": "json_object"}

        try:
            start_time = time.time()
            response = client.chat.completions.create(**params)
            latency_ms = (time.time() - start_time) * 1000

            # Extract response data
            choice = response.choices[0]
            content = choice.message.content or ""
            finish_reason = choice.finish_reason

            # Parse usage
            usage = TokenUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            )

            # Calculate metrics
            metrics = GenerationMetrics(
                latency_ms=latency_ms,
                tokens_per_second=(usage.completion_tokens / latency_ms * 1000)
                if latency_ms > 0 else 0,
                provider=self.get_provider().value,
                model=self.model,
            )

            # Extract tool calls if present
            tool_calls = None
            if choice.message.tool_calls:
                tool_calls = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        }
                    }
                    for tc in choice.message.tool_calls
                ]

            return LLMResponse(
                content=content,
                model=response.model,
                provider=self.get_provider().value,
                finish_reason=finish_reason,
                usage=usage,
                metrics=metrics,
                tool_calls=tool_calls,
                raw_response=response,
            )

        except Exception as e:
            self._handle_openai_error(e)

    def _generate_streaming_impl(
        self,
        request: LLMRequest
    ) -> Iterator[StreamChunk]:
        """OpenAI-specific streaming implementation."""
        client = self._get_client()

        # Build messages
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        # Prepare API call parameters
        params = {
            "model": self.model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "stream": True,
        }

        try:
            stream = client.chat.completions.create(**params)

            for chunk in stream:
                if chunk.choices:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        yield StreamChunk(
                            type=StreamChunkType.CONTENT,
                            content=delta.content,
                            metadata={"finish_reason": chunk.choices[0].finish_reason}
                        )

                    # Handle tool calls in streaming
                    if delta.tool_calls:
                        yield StreamChunk(
                            type=StreamChunkType.TOOL_USE,
                            content="",
                            metadata={"tool_calls": delta.tool_calls}
                        )

            # Send completion signal
            yield StreamChunk(type=StreamChunkType.DONE, content="")

        except Exception as e:
            yield StreamChunk(
                type=StreamChunkType.ERROR,
                content=str(e),
                metadata={"error": e}
            )
            self._handle_openai_error(e)

    def count_tokens(self, text: str) -> int:
        """
        Count tokens using tiktoken.

        Args:
            text: Text to count

        Returns:
            Number of tokens
        """
        try:
            import tiktoken

            # Get encoding for model
            try:
                encoding = tiktoken.encoding_for_model(self.model)
            except KeyError:
                # Fallback to cl100k_base for unknown models
                encoding = tiktoken.get_encoding("cl100k_base")

            return len(encoding.encode(text))

        except ImportError:
            # Fallback to approximate counting
            logger.warning("tiktoken not installed, using approximate token counting")
            return len(text) // 4

    def _handle_openai_error(self, error: Exception) -> None:
        """Convert OpenAI errors to our exception types."""
        error_str = str(error).lower()

        if "timeout" in error_str:
            raise LLMTimeoutError(f"Request timed out: {error}")
        elif "rate limit" in error_str or "429" in error_str:
            raise LLMRateLimitError(f"Rate limit exceeded: {error}")
        elif "authentication" in error_str or "401" in error_str:
            raise LLMAuthenticationError(f"Authentication failed: {error}")
        elif "connection" in error_str or "network" in error_str:
            raise LLMConnectionError(f"Connection error: {error}")
        else:
            raise LLMError(f"OpenAI API error: {error}")


# ============================================================================
# Mock Provider for Testing
# ============================================================================


class MockLLMClient(LLMClient):
    """
    Mock LLM client for testing and development.

    Returns predefined responses without making actual API calls.
    Useful for unit tests and local development.
    """

    def __init__(
        self,
        model: str = "mock-model",
        default_response: str = "This is a mock response.",
        latency_ms: float = 100.0,
        **kwargs
    ):
        """
        Initialize mock client.

        Args:
            model: Mock model name
            default_response: Default response text
            latency_ms: Simulated latency
            **kwargs: Additional parameters
        """
        super().__init__(model=model, **kwargs)
        self.default_response = default_response
        self.latency_ms = latency_ms
        self.call_history = []

    def get_provider(self) -> LLMProvider:
        """Return mock provider type."""
        return LLMProvider.CUSTOM

    def get_capabilities(self) -> ModelCapabilities:
        """Return mock capabilities."""
        return ModelCapabilities(
            supports_streaming=True,
            supports_function_calling=True,
            supports_vision=False,
            supports_json_mode=True,
            max_context_length=100000,
            max_output_tokens=10000,
            supports_system_message=True,
            cost_per_1k_prompt_tokens=0.0,
            cost_per_1k_completion_tokens=0.0,
        )

    def _generate_impl(self, request: LLMRequest) -> LLMResponse:
        """Mock generation implementation."""
        # Record call for inspection
        self.call_history.append({
            "prompt": request.prompt,
            "system_prompt": request.system_prompt,
            "timestamp": time.time(),
        })

        # Simulate latency
        time.sleep(self.latency_ms / 1000)

        # Generate mock response
        prompt_tokens = self.count_tokens(request.prompt or "")
        system_tokens = self.count_tokens(request.system_prompt or "")
        completion_tokens = self.count_tokens(self.default_response)

        usage = TokenUsage(
            prompt_tokens=prompt_tokens + system_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + system_tokens + completion_tokens,
        )

        metrics = GenerationMetrics(
            latency_ms=self.latency_ms,
            tokens_per_second=completion_tokens / (self.latency_ms / 1000),
            provider=self.get_provider().value,
            model=self.model,
        )

        return LLMResponse(
            content=self.default_response,
            model=self.model,
            provider=self.get_provider().value,
            finish_reason="stop",
            usage=usage,
            metrics=metrics,
        )

    def _generate_streaming_impl(
        self,
        request: LLMRequest
    ) -> Iterator[StreamChunk]:
        """Mock streaming implementation."""
        # Split response into chunks
        words = self.default_response.split()
        chunk_size = 3

        for i in range(0, len(words), chunk_size):
            chunk_words = words[i:i + chunk_size]
            content = " ".join(chunk_words)

            # Simulate streaming delay
            time.sleep(self.latency_ms / 1000 / len(words) * chunk_size)

            yield StreamChunk(
                type=StreamChunkType.CONTENT,
                content=content + (" " if i + chunk_size < len(words) else ""),
            )

        yield StreamChunk(type=StreamChunkType.DONE, content="")

    def count_tokens(self, text: str) -> int:
        """Simple token counting (approximate)."""
        return len(text.split())

    def set_response(self, response: str) -> None:
        """Set the default response for testing."""
        self.default_response = response

    def get_call_history(self) -> list:
        """Get history of all calls made to this client."""
        return self.call_history

    def clear_history(self) -> None:
        """Clear call history."""
        self.call_history.clear()
