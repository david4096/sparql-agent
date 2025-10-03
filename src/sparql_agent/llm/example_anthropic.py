"""
Example usage of the Anthropic Claude provider.

This example demonstrates how to use the AnthropicProvider for
SPARQL query generation and other LLM tasks.
"""

import os
from anthropic_provider import (
    AnthropicProvider,
    create_anthropic_provider,
    CLAUDE_MODELS,
)
from client import LLMRequest


def basic_generation_example():
    """Basic text generation example."""
    print("=" * 80)
    print("Basic Generation Example")
    print("=" * 80)

    # Create provider
    provider = create_anthropic_provider(
        model="claude-3-5-sonnet-20241022",
        # API key read from ANTHROPIC_API_KEY env var
    )

    # Create request
    request = LLMRequest(
        prompt="What is SPARQL and how is it used in semantic web applications?",
        system_prompt="You are a semantic web expert. Provide concise, technical answers.",
        temperature=0.7,
        max_tokens=500,
    )

    # Generate response
    response = provider.generate(request)

    # Display results
    print(f"\nModel: {response.model}")
    print(f"Provider: {response.provider}")
    print(f"Tokens: {response.usage.total_tokens} "
          f"({response.usage.prompt_tokens} prompt + {response.usage.completion_tokens} completion)")
    print(f"Latency: {response.metrics.latency_ms:.2f}ms")
    print(f"Tokens/sec: {response.metrics.tokens_per_second:.2f}")
    print(f"\nResponse:\n{response.content}")
    print()


def sparql_query_generation_example():
    """Example of generating SPARQL queries."""
    print("=" * 80)
    print("SPARQL Query Generation Example")
    print("=" * 80)

    provider = AnthropicProvider(model="claude-3-5-sonnet-20241022")

    # Request SPARQL query generation
    request = LLMRequest(
        prompt="""
        Generate a SPARQL query to find all proteins that interact with the protein P12345.
        The data uses the following schema:
        - Proteins are instances of :Protein
        - Interactions use the :interactsWith property
        - Protein IDs use the :hasID property
        """,
        system_prompt="""You are a SPARQL expert. Generate valid, optimized SPARQL queries.
        Always include prefixes and use best practices.""",
        temperature=0.3,  # Lower temperature for more deterministic output
        max_tokens=1000,
    )

    response = provider.generate(request)

    print(f"\nGenerated Query:\n{response.content}")
    print(f"\nCost: ${provider.estimate_cost(response.usage.prompt_tokens, response.usage.completion_tokens):.6f}")
    print()


def streaming_example():
    """Example of streaming responses."""
    print("=" * 80)
    print("Streaming Example")
    print("=" * 80)

    provider = AnthropicProvider(model="claude-3-haiku-20240307")  # Use faster model

    request = LLMRequest(
        prompt="Explain the difference between RDF, RDFS, and OWL in semantic web technologies.",
        system_prompt="You are a semantic web expert.",
        temperature=0.7,
        max_tokens=800,
    )

    print("\nStreaming response:")
    print("-" * 80)

    # Stream the response
    for chunk in provider.generate_streaming(request):
        if chunk.type.value == "content":
            print(chunk.content, end="", flush=True)
        elif chunk.type.value == "done":
            print("\n" + "-" * 80)
            print(f"Total time: {chunk.metadata.get('total_time_ms', 0):.2f}ms")

    print()


def multi_model_comparison():
    """Compare responses from different Claude models."""
    print("=" * 80)
    print("Multi-Model Comparison")
    print("=" * 80)

    models = [
        "claude-3-haiku-20240307",
        "claude-3-sonnet-20240229",
        "claude-3-5-sonnet-20241022",
    ]

    question = "What are the key benefits of using ontologies in knowledge graphs?"

    for model in models:
        print(f"\n{'=' * 40}")
        print(f"Model: {model}")
        print('=' * 40)

        provider = AnthropicProvider(model=model)

        request = LLMRequest(
            prompt=question,
            temperature=0.5,
            max_tokens=300,
        )

        response = provider.generate(request)

        caps = provider.get_capabilities()

        print(f"Response: {response.content[:200]}...")
        print(f"\nMetrics:")
        print(f"  - Latency: {response.metrics.latency_ms:.2f}ms")
        print(f"  - Tokens: {response.usage.total_tokens}")
        print(f"  - Cost: ${provider.estimate_cost(response.usage.prompt_tokens, response.usage.completion_tokens):.6f}")
        print(f"  - Speed: {response.metrics.tokens_per_second:.2f} tokens/sec")


def tool_calling_example():
    """Example of using Claude's tool calling capabilities."""
    print("=" * 80)
    print("Tool Calling Example")
    print("=" * 80)

    provider = AnthropicProvider(model="claude-3-5-sonnet-20241022")

    # Define tools
    tools = [
        {
            "type": "function",
            "function": {
                "name": "execute_sparql_query",
                "description": "Execute a SPARQL query against a knowledge graph",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The SPARQL query to execute"
                        },
                        "endpoint": {
                            "type": "string",
                            "description": "The SPARQL endpoint URL"
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    ]

    request = LLMRequest(
        prompt="Find all people who work at Google in the knowledge graph.",
        system_prompt="You are a helpful assistant that can query knowledge graphs using SPARQL.",
        tools=tools,
        temperature=0.5,
        max_tokens=1000,
    )

    response = provider.generate(request)

    print(f"\nResponse: {response.content}")

    if response.tool_calls:
        print(f"\nTool Calls:")
        for tool_call in response.tool_calls:
            print(f"  - {tool_call['function']['name']}")
            print(f"    Arguments: {tool_call['function']['arguments']}")

    print()


def provider_info_example():
    """Display provider and model information."""
    print("=" * 80)
    print("Provider Information")
    print("=" * 80)

    print(f"\nAvailable Models:")
    for model in AnthropicProvider.list_available_models():
        print(f"  - {model}")

    print(f"\nModel Details:")
    for model_name in ["claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"]:
        config = AnthropicProvider.get_model_config(model_name)
        print(f"\n  {model_name}:")
        print(f"    Context Window: {config['context_window']:,} tokens")
        print(f"    Max Output: {config['max_output']:,} tokens")
        print(f"    Input Price: ${config['input_price']}/1M tokens")
        print(f"    Output Price: ${config['output_price']}/1M tokens")
        print(f"    Vision Support: {config['supports_vision']}")
        print(f"    Tool Support: {config['supports_tools']}")
        print(f"    Description: {config['description']}")

    # Show capabilities for a specific instance
    provider = AnthropicProvider(model="claude-3-5-sonnet-20241022")
    caps = provider.get_capabilities()

    print(f"\n  Capabilities for {provider.model}:")
    print(f"    Streaming: {caps.supports_streaming}")
    print(f"    Function Calling: {caps.supports_function_calling}")
    print(f"    Vision: {caps.supports_vision}")
    print(f"    JSON Mode: {caps.supports_json_mode}")
    print(f"    System Messages: {caps.supports_system_message}")

    # Show metrics
    print(f"\n  Provider Metrics:")
    metrics = provider.get_metrics()
    print(f"    Requests: {metrics['request_count']}")
    print(f"    Total Tokens: {metrics['total_tokens']}")
    print(f"    Total Cost: ${metrics['total_cost_usd']:.6f}")
    print(f"    Errors: {metrics['error_count']}")

    print()


def main():
    """Run all examples."""
    # Check if API key is set
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY environment variable not set")
        print("Set it with: export ANTHROPIC_API_KEY='your-api-key'")
        return

    try:
        # Run examples
        provider_info_example()
        basic_generation_example()
        sparql_query_generation_example()
        streaming_example()
        tool_calling_example()
        multi_model_comparison()

        print("=" * 80)
        print("All examples completed successfully!")
        print("=" * 80)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
