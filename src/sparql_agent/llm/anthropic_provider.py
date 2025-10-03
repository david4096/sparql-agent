"""
Anthropic Claude LLM Provider Implementation.

This module provides integration with Anthropic's Claude models, supporting
Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Sonnet, Claude 3 Haiku, and other models.

Features:
- Full support for Claude 3 family models
- Message-based conversations with system prompts
- Streaming response support
- Function/tool calling capabilities
- Token counting and cost estimation
- Rate limiting compliance
- Comprehensive error handling
"""

import json
import os
import time
from typing import Any, Dict, Iterator, List, Optional, Union

try:
    import anthropic
    from anthropic import Anthropic, AsyncAnthropic
    from anthropic.types import (
        ContentBlock,
        Message,
        TextBlock,
        ToolUseBlock,
    )
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    # Define stub types for type hints when anthropic is not installed
    Message = Any
    TextBlock = Any
    ToolUseBlock = Any

from .client import (
    LLMClient,
    LLMProvider,
    LLMRequest,
    LLMResponse as ClientLLMResponse,
    StreamChunk,
    StreamChunkType,
    TokenUsage,
    GenerationMetrics,
    ModelCapabilities,
    RetryConfig,
)
from ..core.exceptions import (
    LLMAuthenticationError,
    LLMConnectionError,
    LLMContentFilterError,
    LLMError,
    LLMModelNotFoundError,
    LLMQuotaExceededError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
)


# Claude model configurations with pricing (per 1M tokens)
CLAUDE_MODELS = {
    "claude-3-5-sonnet-20241022": {
        "context_window": 200000,
        "max_output": 8192,
        "input_price": 3.00,  # $3 per 1M input tokens
        "output_price": 15.00,  # $15 per 1M output tokens
        "supports_vision": True,
        "supports_tools": True,
        "supports_streaming": True,
        "supports_json_mode": True,
        "description": "Latest Claude 3.5 Sonnet - highest intelligence, best for complex tasks"
    },
    "claude-3-5-sonnet-20240620": {
        "context_window": 200000,
        "max_output": 8192,
        "input_price": 3.00,
        "output_price": 15.00,
        "supports_vision": True,
        "supports_tools": True,
        "supports_streaming": True,
        "supports_json_mode": True,
        "description": "Claude 3.5 Sonnet - excellent balance of intelligence and speed"
    },
    "claude-3-opus-20240229": {
        "context_window": 200000,
        "max_output": 4096,
        "input_price": 15.00,
        "output_price": 75.00,
        "supports_vision": True,
        "supports_tools": True,
        "supports_streaming": True,
        "supports_json_mode": True,
        "description": "Claude 3 Opus - most capable model for highly complex tasks"
    },
    "claude-3-sonnet-20240229": {
        "context_window": 200000,
        "max_output": 4096,
        "input_price": 3.00,
        "output_price": 15.00,
        "supports_vision": True,
        "supports_tools": True,
        "supports_streaming": True,
        "supports_json_mode": True,
        "description": "Claude 3 Sonnet - balanced performance for various tasks"
    },
    "claude-3-haiku-20240307": {
        "context_window": 200000,
        "max_output": 4096,
        "input_price": 0.25,
        "output_price": 1.25,
        "supports_vision": True,
        "supports_tools": True,
        "supports_streaming": True,
        "supports_json_mode": True,
        "description": "Claude 3 Haiku - fastest model for simple tasks"
    },
}

# Default model
DEFAULT_MODEL = "claude-3-5-sonnet-20241022"


class AnthropicProvider(LLMClient):
    """
    Anthropic Claude LLM Provider.

    This class implements the LLMClient interface for Anthropic's Claude models,
    providing access to Claude 3.5 Sonnet, Opus, Sonnet, and Haiku models.

    Example:
        >>> provider = AnthropicProvider(model="claude-3-5-sonnet-20241022")
        >>> request = LLMRequest(
        ...     prompt="Explain SPARQL queries",
        ...     system_prompt="You are a semantic web expert.",
        ...     temperature=0.7
        ... )
        >>> response = provider.generate(request)
        >>> print(response.content)
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        timeout: float = 60.0,
        retry_config: Optional[RetryConfig] = None,
        default_max_tokens: int = 4096,
        **kwargs
    ):
        """
        Initialize the Anthropic provider.

        Args:
            model: Claude model to use (default: claude-3-5-sonnet-20241022)
            api_key: Anthropic API key (if None, reads from ANTHROPIC_API_KEY env var)
            api_base: API base URL (optional, for custom endpoints)
            timeout: Request timeout in seconds (default: 60.0)
            retry_config: Retry configuration
            default_max_tokens: Default maximum tokens to generate (default: 4096)
            **kwargs: Additional arguments

        Raises:
            ImportError: If anthropic package is not installed
            LLMAuthenticationError: If API key is not provided
            LLMModelNotFoundError: If model is not supported
        """
        if not ANTHROPIC_AVAILABLE:
            raise ImportError(
                "anthropic package is not installed. "
                "Install it with: pip install anthropic"
            )

        # Get API key from parameter or environment
        api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise LLMAuthenticationError(
                "Anthropic API key is required. "
                "Set ANTHROPIC_API_KEY environment variable or pass api_key parameter."
            )

        # Validate model
        if model not in CLAUDE_MODELS:
            available_models = ", ".join(CLAUDE_MODELS.keys())
            raise LLMModelNotFoundError(
                f"Model '{model}' is not supported. "
                f"Available models: {available_models}",
                details={"model": model, "available_models": list(CLAUDE_MODELS.keys())}
            )

        # Initialize parent
        super().__init__(
            model=model,
            api_key=api_key,
            api_base=api_base,
            timeout=timeout,
            retry_config=retry_config,
            **kwargs
        )

        self.default_max_tokens = default_max_tokens

        # Initialize Anthropic client
        client_kwargs = {
            "api_key": self.api_key,
            "timeout": float(timeout),
            "max_retries": 0,  # We handle retries in the base class
        }

        if api_base:
            client_kwargs["base_url"] = api_base

        self.client = Anthropic(**client_kwargs)

        # Rate limiting tracking
        self._last_request_time = 0.0
        self._min_request_interval = 0.05  # 50ms minimum between requests

    def get_provider(self) -> LLMProvider:
        """Return the provider type."""
        return LLMProvider.ANTHROPIC

    def get_capabilities(self) -> ModelCapabilities:
        """Return model capabilities."""
        model_config = CLAUDE_MODELS.get(self.model, {})

        return ModelCapabilities(
            supports_streaming=model_config.get("supports_streaming", True),
            supports_function_calling=model_config.get("supports_tools", True),
            supports_vision=model_config.get("supports_vision", True),
            supports_json_mode=model_config.get("supports_json_mode", True),
            max_context_length=model_config.get("context_window", 200000),
            max_output_tokens=model_config.get("max_output", 4096),
            supports_system_message=True,
            cost_per_1k_prompt_tokens=model_config.get("input_price", 0.0) / 1000,
            cost_per_1k_completion_tokens=model_config.get("output_price", 0.0) / 1000,
        )

    def _generate_impl(self, request: LLMRequest) -> ClientLLMResponse:
        """
        Provider-specific implementation of text generation.

        Args:
            request: Generation request

        Returns:
            LLM response

        Raises:
            LLMError: On generation failure
        """
        # Enforce rate limiting
        self._enforce_rate_limit()

        # Set default max_tokens
        max_tokens = request.max_tokens or self.default_max_tokens
        max_tokens = min(max_tokens, CLAUDE_MODELS[self.model]["max_output"])

        # Build messages
        messages = [
            {
                "role": "user",
                "content": request.prompt
            }
        ]

        # Build request parameters
        request_params = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": request.temperature,
        }

        if request.system_prompt:
            request_params["system"] = request.system_prompt

        if request.stop_sequences:
            request_params["stop_sequences"] = request.stop_sequences

        if request.top_p != 1.0:
            request_params["top_p"] = request.top_p

        if request.top_k is not None:
            request_params["top_k"] = request.top_k

        # Handle tools/function calling
        if request.tools:
            request_params["tools"] = self._convert_tools_to_anthropic_format(request.tools)

        try:
            start_time = time.time()

            # Make API request
            response = self.client.messages.create(**request_params)

            latency_ms = (time.time() - start_time) * 1000

            # Extract content
            content = self._extract_content(response)

            # Extract tool calls if present
            tool_calls = self._extract_tool_calls(response)

            # Calculate metrics
            prompt_tokens = response.usage.input_tokens
            completion_tokens = response.usage.output_tokens
            total_tokens = prompt_tokens + completion_tokens

            tokens_per_second = completion_tokens / (latency_ms / 1000) if latency_ms > 0 else 0

            return ClientLLMResponse(
                content=content,
                model=response.model,
                provider=self.get_provider().value,
                finish_reason=response.stop_reason or "stop",
                usage=TokenUsage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                ),
                metrics=GenerationMetrics(
                    latency_ms=latency_ms,
                    tokens_per_second=tokens_per_second,
                    provider=self.get_provider().value,
                    model=response.model,
                ),
                tool_calls=tool_calls if tool_calls else None,
                raw_response=response,
                metadata={
                    "stop_reason": response.stop_reason,
                    "system_prompt": request.system_prompt,
                    "temperature": request.temperature,
                    "max_tokens": max_tokens,
                    "message_id": response.id,
                }
            )

        except anthropic.AuthenticationError as e:
            raise LLMAuthenticationError(
                f"Anthropic authentication failed: {str(e)}",
                details={"error": str(e)}
            ) from e

        except anthropic.RateLimitError as e:
            raise LLMRateLimitError(
                f"Anthropic rate limit exceeded: {str(e)}",
                details={"error": str(e)}
            ) from e

        except anthropic.APITimeoutError as e:
            raise LLMTimeoutError(
                f"Anthropic request timed out: {str(e)}",
                details={"timeout": self.timeout}
            ) from e

        except anthropic.APIConnectionError as e:
            raise LLMConnectionError(
                f"Failed to connect to Anthropic API: {str(e)}",
                details={"error": str(e)}
            ) from e

        except anthropic.BadRequestError as e:
            # Check for specific error types
            error_message = str(e)
            if "quota" in error_message.lower() or "billing" in error_message.lower():
                raise LLMQuotaExceededError(
                    f"Anthropic quota exceeded: {error_message}",
                    details={"error": error_message}
                ) from e
            elif "content" in error_message.lower() or "policy" in error_message.lower():
                raise LLMContentFilterError(
                    f"Content filtered by Anthropic: {error_message}",
                    details={"error": error_message}
                ) from e
            else:
                raise LLMError(
                    f"Anthropic API error: {error_message}",
                    details={"error": error_message}
                ) from e

        except anthropic.APIError as e:
            raise LLMError(
                f"Anthropic API error: {str(e)}",
                details={"error": str(e)}
            ) from e

        except Exception as e:
            raise LLMError(
                f"Unexpected error during Anthropic generation: {str(e)}",
                details={"error": str(e), "type": type(e).__name__}
            ) from e

    def _generate_streaming_impl(
        self,
        request: LLMRequest
    ) -> Iterator[StreamChunk]:
        """
        Provider-specific implementation of streaming generation.

        Args:
            request: Generation request

        Yields:
            Stream chunks

        Raises:
            LLMError: On generation failure
        """
        self._enforce_rate_limit()

        max_tokens = request.max_tokens or self.default_max_tokens
        max_tokens = min(max_tokens, CLAUDE_MODELS[self.model]["max_output"])

        messages = [{"role": "user", "content": request.prompt}]

        request_params = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": request.temperature,
            "stream": True,
        }

        if request.system_prompt:
            request_params["system"] = request.system_prompt

        if request.stop_sequences:
            request_params["stop_sequences"] = request.stop_sequences

        if request.top_p != 1.0:
            request_params["top_p"] = request.top_p

        if request.top_k is not None:
            request_params["top_k"] = request.top_k

        if request.tools:
            request_params["tools"] = self._convert_tools_to_anthropic_format(request.tools)

        try:
            start_time = time.time()
            first_token_time = None

            with self.client.messages.stream(**request_params) as stream:
                for text in stream.text_stream:
                    if first_token_time is None:
                        first_token_time = time.time()

                    yield StreamChunk(
                        type=StreamChunkType.CONTENT,
                        content=text,
                        metadata={
                            "time_to_first_token_ms": (first_token_time - start_time) * 1000
                                if first_token_time else None
                        }
                    )

            # Send completion chunk
            yield StreamChunk(
                type=StreamChunkType.DONE,
                content="",
                metadata={
                    "total_time_ms": (time.time() - start_time) * 1000
                }
            )

        except Exception as e:
            yield StreamChunk(
                type=StreamChunkType.ERROR,
                content=str(e),
                metadata={"error_type": type(e).__name__}
            )
            raise LLMError(
                f"Error during streaming generation: {str(e)}",
                details={"error": str(e)}
            ) from e

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Claude uses the same tokenizer across all models. This is an approximation
        based on the rule of thumb that 1 token ≈ 3.5 characters for English text.

        For exact token counts, you would need to use Anthropic's tokenizer API,
        but that requires an additional API call.

        Args:
            text: Text to count tokens for

        Returns:
            Approximate number of tokens
        """
        # Approximation: ~3.5 characters per token for English
        # This is a rough estimate; actual token count may vary
        return max(1, len(text) // 3 + (1 if len(text) % 3 else 0))

    def _extract_content(self, response: Message) -> str:
        """
        Extract text content from a Claude message response.

        Args:
            response: The Claude message response

        Returns:
            Extracted text content
        """
        content_parts = []

        for block in response.content:
            if isinstance(block, TextBlock):
                content_parts.append(block.text)
            elif hasattr(block, "text"):
                content_parts.append(block.text)

        return "".join(content_parts)

    def _extract_tool_calls(self, response: Message) -> Optional[List[Dict[str, Any]]]:
        """
        Extract tool calls from a Claude message response.

        Args:
            response: The Claude message response

        Returns:
            List of tool calls or None
        """
        tool_calls = []

        for block in response.content:
            if isinstance(block, ToolUseBlock):
                tool_calls.append({
                    "id": block.id,
                    "type": "function",
                    "function": {
                        "name": block.name,
                        "arguments": json.dumps(block.input)
                    }
                })

        return tool_calls if tool_calls else None

    def _convert_tools_to_anthropic_format(
        self,
        tools: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Convert standard tool format to Anthropic's tool format.

        Args:
            tools: List of tool definitions

        Returns:
            Anthropic-formatted tools
        """
        anthropic_tools = []

        for tool in tools:
            # Handle OpenAI-style function tools
            if tool.get("type") == "function" and "function" in tool:
                func = tool["function"]
                anthropic_tools.append({
                    "name": func["name"],
                    "description": func.get("description", ""),
                    "input_schema": func.get("parameters", {})
                })
            # Handle direct Anthropic-style tools
            elif "name" in tool and "input_schema" in tool:
                anthropic_tools.append(tool)

        return anthropic_tools

    def _enforce_rate_limit(self) -> None:
        """
        Enforce rate limiting by waiting if necessary.

        This ensures we don't exceed Anthropic's rate limits by spacing
        out requests appropriately.
        """
        current_time = time.time()
        time_since_last_request = current_time - self._last_request_time

        if time_since_last_request < self._min_request_interval:
            sleep_time = self._min_request_interval - time_since_last_request
            time.sleep(sleep_time)

        self._last_request_time = time.time()

    @staticmethod
    def list_available_models() -> List[str]:
        """
        List all available Claude models.

        Returns:
            List of model identifiers
        """
        return list(CLAUDE_MODELS.keys())

    @staticmethod
    def get_model_config(model: str) -> Dict[str, Any]:
        """
        Get configuration for a specific model.

        Args:
            model: Model identifier

        Returns:
            Model configuration dictionary

        Raises:
            LLMModelNotFoundError: If model is not found
        """
        if model not in CLAUDE_MODELS:
            raise LLMModelNotFoundError(
                f"Model '{model}' not found",
                details={"model": model}
            )
        return CLAUDE_MODELS[model].copy()

    def __repr__(self) -> str:
        """String representation of the provider."""
        return f"AnthropicProvider(model='{self.model}')"


# Convenience function for creating Anthropic provider
def create_anthropic_provider(
    model: str = DEFAULT_MODEL,
    api_key: Optional[str] = None,
    **kwargs
) -> AnthropicProvider:
    """
    Create an Anthropic provider instance.

    Args:
        model: Claude model to use
        api_key: API key (optional, reads from env if not provided)
        **kwargs: Additional provider arguments

    Returns:
        Configured AnthropicProvider instance

    Example:
        >>> provider = create_anthropic_provider("claude-3-5-sonnet-20241022")
        >>> response = provider.generate_text("Hello, Claude!")
    """
    return AnthropicProvider(model=model, api_key=api_key, **kwargs)
