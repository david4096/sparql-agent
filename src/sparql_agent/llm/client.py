"""
LLM Client Abstraction Layer.

This module provides a provider-agnostic interface for interacting with various
LLM services (OpenAI, Anthropic, local models, etc.) with unified error handling,
token counting, cost tracking, streaming support, and automatic fallback mechanisms.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (
    Any, AsyncIterator, Callable, Dict, Iterator, List, Optional,
    Protocol, Set, Union
)
import asyncio
import logging
import time
from collections import defaultdict
from functools import wraps

from ..core.exceptions import (
    LLMError,
    LLMConnectionError,
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMResponseError,
    LLMModelNotFoundError,
    LLMQuotaExceededError,
    LLMContentFilterError,
)


logger = logging.getLogger(__name__)


# ============================================================================
# Core Types and Enums
# ============================================================================


class LLMProvider(Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"
    GOOGLE = "google"
    COHERE = "cohere"
    HUGGINGFACE = "huggingface"
    LOCAL = "local"
    CUSTOM = "custom"


class StreamChunkType(Enum):
    """Types of streaming chunks."""
    CONTENT = "content"
    FUNCTION_CALL = "function_call"
    TOOL_USE = "tool_use"
    METADATA = "metadata"
    ERROR = "error"
    DONE = "done"


@dataclass
class StreamChunk:
    """A chunk from a streaming response."""
    type: StreamChunkType
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class TokenUsage:
    """Token usage information."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    @property
    def cached_tokens(self) -> int:
        """Number of cached tokens (if supported by provider)."""
        return 0


@dataclass
class GenerationMetrics:
    """Metrics for a generation request."""
    latency_ms: float
    tokens_per_second: float
    time_to_first_token_ms: Optional[float] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class LLMRequest:
    """
    Unified request format for LLM generation.

    Attributes:
        prompt: The input prompt/message
        system_prompt: Optional system message
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature (0.0-2.0)
        top_p: Nucleus sampling parameter
        top_k: Top-k sampling parameter
        stop_sequences: List of sequences that stop generation
        frequency_penalty: Frequency penalty for repetition
        presence_penalty: Presence penalty for repetition
        seed: Random seed for reproducibility
        stream: Whether to stream the response
        tools: Tool/function definitions for function calling
        response_format: Desired response format (json, text, etc.)
        metadata: Additional request metadata
    """
    prompt: str
    system_prompt: Optional[str] = None
    max_tokens: int = 2000
    temperature: float = 0.7
    top_p: float = 1.0
    top_k: Optional[int] = None
    stop_sequences: List[str] = field(default_factory=list)
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    seed: Optional[int] = None
    stream: bool = False
    tools: Optional[List[Dict[str, Any]]] = None
    response_format: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    """
    Unified response format from LLM providers.

    Attributes:
        content: Generated text content
        model: Model identifier used
        provider: Provider identifier
        finish_reason: Reason generation stopped (stop, length, content_filter, etc.)
        usage: Token usage information
        metrics: Performance metrics
        tool_calls: Tool/function calls (if applicable)
        raw_response: Original provider response
        cached: Whether response was served from cache
        metadata: Additional response metadata
    """
    content: str
    model: str
    provider: str
    finish_reason: str
    usage: TokenUsage
    metrics: GenerationMetrics
    tool_calls: Optional[List[Dict[str, Any]]] = None
    raw_response: Optional[Any] = None
    cached: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelCapabilities:
    """Capabilities of an LLM model."""
    supports_streaming: bool = True
    supports_function_calling: bool = False
    supports_vision: bool = False
    supports_json_mode: bool = False
    max_context_length: int = 4096
    max_output_tokens: int = 4096
    supports_system_message: bool = True
    cost_per_1k_prompt_tokens: float = 0.0
    cost_per_1k_completion_tokens: float = 0.0


@dataclass
class RetryConfig:
    """Configuration for retry logic."""
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retry_on_timeout: bool = True
    retry_on_rate_limit: bool = True
    retry_on_server_error: bool = True


# ============================================================================
# Abstract Base Classes
# ============================================================================


class LLMClient(ABC):
    """
    Abstract base class for all LLM providers.

    Provides unified interface for text generation, streaming, token counting,
    cost estimation, and error handling across different providers.
    """

    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        timeout: float = 60.0,
        retry_config: Optional[RetryConfig] = None,
        **kwargs
    ):
        """
        Initialize LLM client.

        Args:
            model: Model identifier
            api_key: API key for authentication
            api_base: Base URL for API
            timeout: Request timeout in seconds
            retry_config: Retry configuration
            **kwargs: Additional provider-specific parameters
        """
        self.model = model
        self.api_key = api_key
        self.api_base = api_base
        self.timeout = timeout
        self.retry_config = retry_config or RetryConfig()
        self.extra_params = kwargs

        # Metrics tracking
        self._request_count = 0
        self._total_tokens = 0
        self._total_cost = 0.0
        self._error_count = 0
        self._cache_hits = 0

    @abstractmethod
    def get_provider(self) -> LLMProvider:
        """Return the provider type."""
        pass

    @abstractmethod
    def get_capabilities(self) -> ModelCapabilities:
        """Return model capabilities."""
        pass

    @abstractmethod
    def _generate_impl(self, request: LLMRequest) -> LLMResponse:
        """
        Provider-specific implementation of text generation.

        Args:
            request: Generation request

        Returns:
            LLM response

        Raises:
            LLMError: On generation failure
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        pass

    def generate_text(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate text from prompt (high-level interface).

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional parameters

        Returns:
            LLM response
        """
        request = LLMRequest(
            prompt=prompt,
            max_tokens=max_tokens or 2000,
            temperature=temperature if temperature is not None else 0.7,
            **kwargs
        )
        return self.generate(request)

    def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate response with retry logic and error handling.

        Args:
            request: Generation request

        Returns:
            LLM response

        Raises:
            LLMError: On generation failure after retries
        """
        last_error = None
        retry_count = 0

        while retry_count <= self.retry_config.max_retries:
            try:
                start_time = time.time()
                response = self._generate_impl(request)

                # Update metrics
                self._request_count += 1
                self._total_tokens += response.usage.total_tokens
                cost = self.estimate_cost(
                    response.usage.prompt_tokens,
                    response.usage.completion_tokens
                )
                self._total_cost += cost

                return response

            except (LLMTimeoutError, LLMRateLimitError, LLMConnectionError) as e:
                last_error = e
                self._error_count += 1

                if not self._should_retry(e, retry_count):
                    raise

                delay = self._calculate_retry_delay(retry_count)
                logger.warning(
                    f"Request failed (attempt {retry_count + 1}/{self.retry_config.max_retries + 1}), "
                    f"retrying in {delay:.2f}s: {e}"
                )
                time.sleep(delay)
                retry_count += 1

            except LLMError:
                self._error_count += 1
                raise

        # All retries exhausted
        raise last_error

    def generate_streaming(
        self,
        request: LLMRequest,
        callback: Optional[Callable[[StreamChunk], None]] = None
    ) -> Iterator[StreamChunk]:
        """
        Generate streaming response with callback support.

        Args:
            request: Generation request
            callback: Optional callback for each chunk

        Yields:
            Stream chunks

        Raises:
            LLMError: On generation failure
        """
        request.stream = True

        if not self.get_capabilities().supports_streaming:
            raise LLMError(
                f"Streaming not supported by {self.get_provider().value}",
                details={"model": self.model}
            )

        try:
            for chunk in self._generate_streaming_impl(request):
                if callback:
                    callback(chunk)
                yield chunk
        except Exception as e:
            self._error_count += 1
            if isinstance(e, LLMError):
                raise
            raise LLMError(f"Streaming generation failed: {e}")

    def estimate_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int
    ) -> float:
        """
        Estimate cost for token usage.

        Args:
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens

        Returns:
            Estimated cost in USD
        """
        caps = self.get_capabilities()
        prompt_cost = (prompt_tokens / 1000) * caps.cost_per_1k_prompt_tokens
        completion_cost = (completion_tokens / 1000) * caps.cost_per_1k_completion_tokens
        return prompt_cost + completion_cost

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get client metrics.

        Returns:
            Dictionary of metrics
        """
        return {
            "request_count": self._request_count,
            "total_tokens": self._total_tokens,
            "total_cost_usd": self._total_cost,
            "error_count": self._error_count,
            "cache_hits": self._cache_hits,
            "error_rate": self._error_count / max(self._request_count, 1),
            "avg_tokens_per_request": self._total_tokens / max(self._request_count, 1),
            "avg_cost_per_request": self._total_cost / max(self._request_count, 1),
        }

    def reset_metrics(self) -> None:
        """Reset all metrics counters."""
        self._request_count = 0
        self._total_tokens = 0
        self._total_cost = 0.0
        self._error_count = 0
        self._cache_hits = 0

    def _should_retry(self, error: Exception, retry_count: int) -> bool:
        """Determine if request should be retried."""
        if retry_count >= self.retry_config.max_retries:
            return False

        if isinstance(error, LLMTimeoutError):
            return self.retry_config.retry_on_timeout
        elif isinstance(error, LLMRateLimitError):
            return self.retry_config.retry_on_rate_limit
        elif isinstance(error, LLMConnectionError):
            return self.retry_config.retry_on_server_error

        return False

    def _calculate_retry_delay(self, retry_count: int) -> float:
        """Calculate delay before next retry with exponential backoff."""
        delay = min(
            self.retry_config.initial_delay * (
                self.retry_config.exponential_base ** retry_count
            ),
            self.retry_config.max_delay
        )

        if self.retry_config.jitter:
            import random
            delay = delay * (0.5 + random.random() * 0.5)

        return delay


# ============================================================================
# Provider Manager
# ============================================================================


class ProviderManager:
    """
    Manages multiple LLM providers with load balancing and fallback.

    Features:
    - Provider registration and discovery
    - Automatic fallback on failure
    - Load balancing across providers
    - Provider health tracking
    - Cost optimization
    """

    def __init__(self):
        """Initialize provider manager."""
        self._providers: Dict[str, LLMClient] = {}
        self._provider_priorities: Dict[str, int] = {}
        self._provider_health: Dict[str, float] = {}
        self._provider_registry: Dict[LLMProvider, type] = {}
        self._default_provider: Optional[str] = None

    def register_provider_class(
        self,
        provider_type: LLMProvider,
        provider_class: type
    ) -> None:
        """
        Register a provider class for dynamic instantiation.

        Args:
            provider_type: Provider type enum
            provider_class: Provider class (must inherit from LLMClient)
        """
        if not issubclass(provider_class, LLMClient):
            raise ValueError(f"Provider class must inherit from LLMClient")

        self._provider_registry[provider_type] = provider_class
        logger.info(f"Registered provider class: {provider_type.value}")

    def register_provider(
        self,
        name: str,
        client: LLMClient,
        priority: int = 0,
        set_as_default: bool = False
    ) -> None:
        """
        Register an LLM provider instance.

        Args:
            name: Unique provider name
            client: LLM client instance
            priority: Priority level (higher = preferred)
            set_as_default: Set as default provider
        """
        self._providers[name] = client
        self._provider_priorities[name] = priority
        self._provider_health[name] = 1.0  # Initial health score

        if set_as_default or self._default_provider is None:
            self._default_provider = name

        logger.info(
            f"Registered provider '{name}' "
            f"({client.get_provider().value}, model: {client.model})"
        )

    def unregister_provider(self, name: str) -> None:
        """
        Unregister a provider.

        Args:
            name: Provider name to unregister
        """
        if name in self._providers:
            del self._providers[name]
            del self._provider_priorities[name]
            del self._provider_health[name]

            if self._default_provider == name:
                self._default_provider = next(iter(self._providers), None)

            logger.info(f"Unregistered provider: {name}")

    def get_provider(self, name: Optional[str] = None) -> LLMClient:
        """
        Get a provider by name or default.

        Args:
            name: Provider name (uses default if None)

        Returns:
            LLM client instance

        Raises:
            LLMError: If provider not found
        """
        if name is None:
            name = self._default_provider

        if name is None or name not in self._providers:
            raise LLMError(
                f"Provider '{name}' not found",
                details={"available_providers": list(self._providers.keys())}
            )

        return self._providers[name]

    def list_providers(self) -> List[Dict[str, Any]]:
        """
        List all registered providers.

        Returns:
            List of provider information
        """
        return [
            {
                "name": name,
                "provider": client.get_provider().value,
                "model": client.model,
                "priority": self._provider_priorities[name],
                "health": self._provider_health[name],
                "is_default": name == self._default_provider,
                "metrics": client.get_metrics(),
            }
            for name, client in self._providers.items()
        ]

    def generate_with_fallback(
        self,
        request: LLMRequest,
        provider_names: Optional[List[str]] = None,
        fallback_on_error: bool = True
    ) -> LLMResponse:
        """
        Generate with automatic fallback to other providers.

        Args:
            request: Generation request
            provider_names: Ordered list of providers to try (None = all by priority)
            fallback_on_error: Enable fallback on errors

        Returns:
            LLM response

        Raises:
            LLMError: If all providers fail
        """
        if provider_names is None:
            # Use all providers sorted by priority and health
            provider_names = self._get_sorted_providers()

        if not provider_names:
            raise LLMError("No providers available")

        last_error = None

        for provider_name in provider_names:
            try:
                client = self.get_provider(provider_name)
                response = client.generate(request)

                # Update health score on success
                self._update_health(provider_name, success=True)

                return response

            except LLMError as e:
                last_error = e
                self._update_health(provider_name, success=False)

                logger.warning(
                    f"Provider '{provider_name}' failed: {e}. "
                    f"{'Trying fallback...' if fallback_on_error else 'No fallback.'}"
                )

                if not fallback_on_error:
                    raise

        # All providers failed
        raise LLMError(
            "All providers failed",
            details={
                "providers_tried": provider_names,
                "last_error": str(last_error)
            }
        )

    def generate_with_load_balancing(
        self,
        request: LLMRequest,
        strategy: str = "round_robin"
    ) -> LLMResponse:
        """
        Generate with load balancing across providers.

        Args:
            request: Generation request
            strategy: Load balancing strategy (round_robin, least_loaded, lowest_cost)

        Returns:
            LLM response
        """
        provider_name = self._select_provider_for_load_balancing(strategy)
        client = self.get_provider(provider_name)
        return client.generate(request)

    def _get_sorted_providers(self) -> List[str]:
        """Get providers sorted by priority and health."""
        return sorted(
            self._providers.keys(),
            key=lambda name: (
                self._provider_priorities[name],
                self._provider_health[name]
            ),
            reverse=True
        )

    def _select_provider_for_load_balancing(self, strategy: str) -> str:
        """Select provider based on load balancing strategy."""
        if strategy == "round_robin":
            # Simple rotation
            providers = list(self._providers.keys())
            if not hasattr(self, "_round_robin_index"):
                self._round_robin_index = 0

            provider = providers[self._round_robin_index % len(providers)]
            self._round_robin_index += 1
            return provider

        elif strategy == "least_loaded":
            # Select provider with fewest requests
            return min(
                self._providers.keys(),
                key=lambda name: self._providers[name]._request_count
            )

        elif strategy == "lowest_cost":
            # Select cheapest provider
            return min(
                self._providers.keys(),
                key=lambda name: (
                    self._providers[name].get_capabilities().cost_per_1k_prompt_tokens +
                    self._providers[name].get_capabilities().cost_per_1k_completion_tokens
                )
            )

        else:
            raise ValueError(f"Unknown load balancing strategy: {strategy}")

    def _update_health(self, provider_name: str, success: bool) -> None:
        """Update provider health score based on success/failure."""
        current_health = self._provider_health[provider_name]

        if success:
            # Slowly increase health on success
            self._provider_health[provider_name] = min(1.0, current_health + 0.1)
        else:
            # Rapidly decrease health on failure
            self._provider_health[provider_name] = max(0.0, current_health - 0.3)

    def get_aggregated_metrics(self) -> Dict[str, Any]:
        """
        Get aggregated metrics across all providers.

        Returns:
            Dictionary of aggregated metrics
        """
        total_requests = sum(c._request_count for c in self._providers.values())
        total_tokens = sum(c._total_tokens for c in self._providers.values())
        total_cost = sum(c._total_cost for c in self._providers.values())
        total_errors = sum(c._error_count for c in self._providers.values())

        return {
            "total_providers": len(self._providers),
            "total_requests": total_requests,
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost,
            "total_errors": total_errors,
            "avg_tokens_per_request": total_tokens / max(total_requests, 1),
            "avg_cost_per_request": total_cost / max(total_requests, 1),
            "error_rate": total_errors / max(total_requests, 1),
            "providers": {
                name: client.get_metrics()
                for name, client in self._providers.items()
            }
        }

    def reset_all_metrics(self) -> None:
        """Reset metrics for all providers."""
        for client in self._providers.values():
            client.reset_metrics()


# ============================================================================
# Global Provider Manager Instance
# ============================================================================


_global_provider_manager: Optional[ProviderManager] = None


def get_provider_manager() -> ProviderManager:
    """
    Get or create the global provider manager instance.

    Returns:
        Global ProviderManager instance
    """
    global _global_provider_manager
    if _global_provider_manager is None:
        _global_provider_manager = ProviderManager()
    return _global_provider_manager


def reset_provider_manager() -> None:
    """Reset the global provider manager instance."""
    global _global_provider_manager
    _global_provider_manager = None
