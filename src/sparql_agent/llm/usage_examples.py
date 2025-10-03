"""
Usage Examples for LLM Client Abstraction Layer.

This module demonstrates how to use the LLM client abstraction layer
with various providers, including setup, basic usage, streaming,
provider management, and error handling.
"""

import logging
from typing import List

from .client import (
    LLMClient,
    LLMRequest,
    LLMResponse,
    ProviderManager,
    RetryConfig,
    get_provider_manager,
)
from .example_provider import OpenAIClient, MockLLMClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Example 1: Basic Usage with Single Provider
# ============================================================================


def example_basic_usage():
    """Basic usage with a single LLM provider."""
    print("\n" + "=" * 80)
    print("Example 1: Basic Usage")
    print("=" * 80)

    # Initialize client
    client = MockLLMClient(
        model="mock-gpt-4",
        default_response="SPARQL is a query language for RDF data.",
    )

    # Simple text generation
    response = client.generate_text(
        prompt="What is SPARQL?",
        max_tokens=100,
        temperature=0.7
    )

    print(f"\nPrompt: What is SPARQL?")
    print(f"Response: {response.content}")
    print(f"Tokens used: {response.usage.total_tokens}")
    print(f"Latency: {response.metrics.latency_ms:.2f}ms")
    print(f"Cost: ${client.estimate_cost(response.usage.prompt_tokens, response.usage.completion_tokens):.4f}")


# ============================================================================
# Example 2: Advanced Request Configuration
# ============================================================================


def example_advanced_request():
    """Using LLMRequest for advanced configuration."""
    print("\n" + "=" * 80)
    print("Example 2: Advanced Request Configuration")
    print("=" * 80)

    client = MockLLMClient(
        default_response="SELECT ?subject ?predicate ?object WHERE { ?subject ?predicate ?object } LIMIT 10"
    )

    # Create detailed request
    request = LLMRequest(
        prompt="Generate a simple SPARQL query to get 10 triples",
        system_prompt="You are a SPARQL expert. Generate syntactically correct queries.",
        max_tokens=500,
        temperature=0.2,  # Low temperature for deterministic output
        stop_sequences=["```", "---"],
        frequency_penalty=0.5,
        presence_penalty=0.3,
        metadata={
            "user_id": "user_123",
            "session_id": "session_456",
        }
    )

    response = client.generate(request)

    print(f"\nGenerated Query:\n{response.content}")
    print(f"\nModel: {response.model}")
    print(f"Provider: {response.provider}")
    print(f"Finish reason: {response.finish_reason}")


# ============================================================================
# Example 3: Streaming Responses
# ============================================================================


def example_streaming():
    """Streaming text generation with callback."""
    print("\n" + "=" * 80)
    print("Example 3: Streaming Responses")
    print("=" * 80)

    client = MockLLMClient(
        default_response="Streaming allows real-time response generation. "
                        "Each token is returned as it's generated. "
                        "This provides better user experience for long responses."
    )

    request = LLMRequest(
        prompt="Explain streaming in LLM APIs",
        max_tokens=200,
        stream=True
    )

    print("\nStreaming response:")
    print("-" * 40)

    # Stream with callback
    full_response = []

    def on_chunk(chunk):
        """Callback for each chunk."""
        if chunk.content:
            print(chunk.content, end="", flush=True)
            full_response.append(chunk.content)

    for chunk in client.generate_streaming(request, callback=on_chunk):
        pass  # Callback handles printing

    print("\n" + "-" * 40)
    print(f"\nTotal response length: {len(''.join(full_response))} characters")


# ============================================================================
# Example 4: Provider Manager with Multiple Providers
# ============================================================================


def example_provider_manager():
    """Using ProviderManager for multiple providers."""
    print("\n" + "=" * 80)
    print("Example 4: Provider Manager")
    print("=" * 80)

    # Create provider manager
    manager = ProviderManager()

    # Register multiple providers
    manager.register_provider(
        name="primary",
        client=MockLLMClient(
            model="mock-gpt-4",
            default_response="Response from primary provider"
        ),
        priority=10,
        set_as_default=True
    )

    manager.register_provider(
        name="backup",
        client=MockLLMClient(
            model="mock-gpt-3.5",
            default_response="Response from backup provider"
        ),
        priority=5
    )

    manager.register_provider(
        name="cheap",
        client=MockLLMClient(
            model="mock-claude",
            default_response="Response from cheap provider"
        ),
        priority=3
    )

    # List all providers
    print("\nRegistered providers:")
    for provider_info in manager.list_providers():
        print(f"  - {provider_info['name']}: {provider_info['model']} "
              f"(priority: {provider_info['priority']}, "
              f"default: {provider_info['is_default']})")

    # Use default provider
    default_client = manager.get_provider()
    response = default_client.generate_text("Test prompt")
    print(f"\nDefault provider response: {response.content}")

    # Use specific provider
    cheap_client = manager.get_provider("cheap")
    response = cheap_client.generate_text("Test prompt")
    print(f"Cheap provider response: {response.content}")


# ============================================================================
# Example 5: Automatic Fallback
# ============================================================================


def example_fallback():
    """Automatic fallback when providers fail."""
    print("\n" + "=" * 80)
    print("Example 5: Automatic Fallback")
    print("=" * 80)

    manager = ProviderManager()

    # Register providers with different priorities
    manager.register_provider(
        name="primary",
        client=MockLLMClient(
            model="primary-model",
            default_response="Primary response"
        ),
        priority=10
    )

    manager.register_provider(
        name="fallback",
        client=MockLLMClient(
            model="fallback-model",
            default_response="Fallback response"
        ),
        priority=5
    )

    request = LLMRequest(prompt="Test prompt")

    # Try generation with automatic fallback
    try:
        response = manager.generate_with_fallback(
            request=request,
            fallback_on_error=True
        )
        print(f"\nSuccessful response: {response.content}")
        print(f"Provider used: {response.provider}")
        print(f"Model used: {response.model}")
    except Exception as e:
        print(f"\nAll providers failed: {e}")


# ============================================================================
# Example 6: Load Balancing
# ============================================================================


def example_load_balancing():
    """Load balancing across multiple providers."""
    print("\n" + "=" * 80)
    print("Example 6: Load Balancing")
    print("=" * 80)

    manager = ProviderManager()

    # Register multiple providers
    for i in range(3):
        manager.register_provider(
            name=f"provider_{i}",
            client=MockLLMClient(
                model=f"model-{i}",
                default_response=f"Response from provider {i}"
            ),
            priority=5
        )

    # Generate multiple requests with round-robin load balancing
    print("\nRound-robin load balancing:")
    for i in range(5):
        response = manager.generate_with_load_balancing(
            request=LLMRequest(prompt=f"Request {i}"),
            strategy="round_robin"
        )
        print(f"  Request {i}: {response.model} -> {response.content}")


# ============================================================================
# Example 7: Token Counting and Cost Estimation
# ============================================================================


def example_cost_tracking():
    """Token counting and cost estimation."""
    print("\n" + "=" * 80)
    print("Example 7: Token Counting and Cost Estimation")
    print("=" * 80)

    # Create client with realistic costs
    client = MockLLMClient(model="mock-gpt-4")

    # Simulate multiple requests
    prompts = [
        "What is SPARQL?",
        "Explain RDF triples",
        "How do I query a SPARQL endpoint?",
        "What are named graphs?",
    ]

    print("\nProcessing multiple requests:")
    for prompt in prompts:
        response = client.generate_text(prompt, max_tokens=150)

        cost = client.estimate_cost(
            response.usage.prompt_tokens,
            response.usage.completion_tokens
        )

        print(f"\n  Prompt: {prompt}")
        print(f"  Tokens: {response.usage.prompt_tokens} + "
              f"{response.usage.completion_tokens} = "
              f"{response.usage.total_tokens}")
        print(f"  Estimated cost: ${cost:.6f}")

    # Get aggregate metrics
    metrics = client.get_metrics()
    print("\n" + "-" * 40)
    print("Aggregate Metrics:")
    print(f"  Total requests: {metrics['request_count']}")
    print(f"  Total tokens: {metrics['total_tokens']}")
    print(f"  Total cost: ${metrics['total_cost_usd']:.6f}")
    print(f"  Avg tokens/request: {metrics['avg_tokens_per_request']:.2f}")
    print(f"  Error rate: {metrics['error_rate']:.2%}")


# ============================================================================
# Example 8: Error Handling and Retries
# ============================================================================


def example_error_handling():
    """Error handling with automatic retries."""
    print("\n" + "=" * 80)
    print("Example 8: Error Handling and Retries")
    print("=" * 80)

    # Configure retry behavior
    retry_config = RetryConfig(
        max_retries=3,
        initial_delay=1.0,
        max_delay=10.0,
        exponential_base=2.0,
        jitter=True,
        retry_on_timeout=True,
        retry_on_rate_limit=True,
    )

    client = MockLLMClient(
        model="mock-model",
        retry_config=retry_config
    )

    print("\nRetry configuration:")
    print(f"  Max retries: {retry_config.max_retries}")
    print(f"  Initial delay: {retry_config.initial_delay}s")
    print(f"  Max delay: {retry_config.max_delay}s")
    print(f"  Exponential base: {retry_config.exponential_base}")
    print(f"  Jitter enabled: {retry_config.jitter}")

    try:
        response = client.generate_text("Test prompt with retries")
        print(f"\nSuccessful response: {response.content}")
    except Exception as e:
        print(f"\nFailed after retries: {e}")


# ============================================================================
# Example 9: Global Provider Manager
# ============================================================================


def example_global_manager():
    """Using the global provider manager instance."""
    print("\n" + "=" * 80)
    print("Example 9: Global Provider Manager")
    print("=" * 80)

    # Get global manager
    manager = get_provider_manager()

    # Register a provider
    manager.register_provider(
        name="global_provider",
        client=MockLLMClient(
            model="global-model",
            default_response="Response from global provider"
        ),
        set_as_default=True
    )

    # Use from anywhere in the application
    client = manager.get_provider()
    response = client.generate_text("Test with global manager")

    print(f"\nGlobal provider response: {response.content}")
    print(f"Provider count: {len(manager.list_providers())}")

    # Get aggregated metrics
    agg_metrics = manager.get_aggregated_metrics()
    print(f"\nAggregated metrics:")
    print(f"  Total providers: {agg_metrics['total_providers']}")
    print(f"  Total requests: {agg_metrics['total_requests']}")
    print(f"  Total tokens: {agg_metrics['total_tokens']}")


# ============================================================================
# Example 10: Custom Provider Implementation
# ============================================================================


def example_custom_provider():
    """Implementing a custom provider."""
    print("\n" + "=" * 80)
    print("Example 10: Custom Provider Implementation")
    print("=" * 80)

    from .client import LLMProvider, ModelCapabilities
    from typing import Iterator

    class CustomLLMClient(LLMClient):
        """Custom LLM implementation."""

        def get_provider(self) -> LLMProvider:
            return LLMProvider.CUSTOM

        def get_capabilities(self) -> ModelCapabilities:
            return ModelCapabilities(
                supports_streaming=True,
                max_context_length=8192,
                cost_per_1k_prompt_tokens=0.001,
                cost_per_1k_completion_tokens=0.002,
            )

        def _generate_impl(self, request: LLMRequest) -> LLMResponse:
            # Custom implementation
            from .client import TokenUsage, GenerationMetrics
            import time

            content = f"Custom response to: {request.prompt[:50]}..."

            usage = TokenUsage(
                prompt_tokens=len(request.prompt.split()),
                completion_tokens=len(content.split()),
                total_tokens=len(request.prompt.split()) + len(content.split()),
            )

            metrics = GenerationMetrics(
                latency_ms=50.0,
                tokens_per_second=100.0,
                provider="custom",
                model=self.model,
            )

            from .client import LLMResponse
            return LLMResponse(
                content=content,
                model=self.model,
                provider="custom",
                finish_reason="stop",
                usage=usage,
                metrics=metrics,
            )

        def _generate_streaming_impl(self, request: LLMRequest) -> Iterator:
            from .client import StreamChunk, StreamChunkType
            yield StreamChunk(
                type=StreamChunkType.CONTENT,
                content="Custom streaming response"
            )
            yield StreamChunk(type=StreamChunkType.DONE, content="")

        def count_tokens(self, text: str) -> int:
            return len(text.split())

    # Use custom provider
    custom_client = CustomLLMClient(model="custom-model-v1")
    response = custom_client.generate_text("Test custom provider")

    print(f"\nCustom provider response: {response.content}")
    print(f"Provider: {response.provider}")
    print(f"Model: {response.model}")


# ============================================================================
# Run All Examples
# ============================================================================


def run_all_examples():
    """Run all usage examples."""
    examples = [
        example_basic_usage,
        example_advanced_request,
        example_streaming,
        example_provider_manager,
        example_fallback,
        example_load_balancing,
        example_cost_tracking,
        example_error_handling,
        example_global_manager,
        example_custom_provider,
    ]

    print("\n" + "=" * 80)
    print("LLM Client Abstraction Layer - Usage Examples")
    print("=" * 80)

    for i, example_func in enumerate(examples, 1):
        try:
            example_func()
        except Exception as e:
            print(f"\n[ERROR in Example {i}] {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 80)
    print("All examples completed!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    run_all_examples()
