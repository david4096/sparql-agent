"""
Examples for OpenAI and Local LLM providers.

This module demonstrates various usage patterns for:
1. OpenAI API (GPT-4, GPT-3.5)
2. Ollama local models
3. LM Studio local models
4. Custom OpenAI-compatible endpoints
"""

from typing import Optional
import os

from .openai_provider import (
    OpenAIProvider,
    LocalProvider,
    create_openai_provider,
    create_ollama_provider,
    create_lmstudio_provider,
    create_custom_provider,
)


# ============================================================================
# OpenAI Examples
# ============================================================================

def example_openai_basic():
    """Basic OpenAI usage with GPT-4."""
    print("=== OpenAI Basic Example ===\n")

    # Option 1: Using environment variable OPENAI_API_KEY
    provider = OpenAIProvider(model="gpt-4")

    # Option 2: Explicitly providing API key
    # provider = OpenAIProvider(model="gpt-4", api_key="sk-...")

    # Generate a response
    response = provider.generate(
        prompt="Translate this to SPARQL: Find all proteins that interact with TP53",
        system_prompt="You are a SPARQL query expert. Generate valid SPARQL queries.",
        temperature=0.1
    )

    print(f"Model: {response.model}")
    print(f"Response: {response.content}")
    print(f"Tokens: {response.tokens_used}")
    print(f"Cost: ${response.cost:.4f}")
    print(f"Latency: {response.latency:.2f}s")
    print()


def example_openai_function_calling():
    """OpenAI with function calling for structured output."""
    print("=== OpenAI Function Calling Example ===\n")

    provider = OpenAIProvider(model="gpt-4")

    # Define function schema
    functions = [{
        "name": "generate_sparql",
        "description": "Generate a SPARQL query from natural language",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The SPARQL query"
                },
                "explanation": {
                    "type": "string",
                    "description": "Explanation of the query"
                },
                "prefixes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Required SPARQL prefixes"
                }
            },
            "required": ["query", "explanation"]
        }
    }]

    response = provider.generate(
        prompt="Find all diseases associated with BRCA1 gene",
        system_prompt="You are a SPARQL expert for biomedical data.",
        functions=functions,
        function_call={"name": "generate_sparql"},
        temperature=0.1
    )

    print(f"Response:\n{response.content}")
    print()


def example_openai_json_schema():
    """OpenAI with JSON schema validation."""
    print("=== OpenAI JSON Schema Example ===\n")

    provider = OpenAIProvider(model="gpt-4")

    # Define JSON schema
    json_schema = {
        "type": "object",
        "properties": {
            "classes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Ontology classes mentioned"
            },
            "properties": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Ontology properties mentioned"
            },
            "query_type": {
                "type": "string",
                "enum": ["SELECT", "ASK", "CONSTRUCT", "DESCRIBE"],
                "description": "Type of SPARQL query"
            }
        },
        "required": ["query_type"]
    }

    response = provider.generate_with_json_schema(
        prompt="I want to find all proteins and their functions",
        json_schema=json_schema,
        system_prompt="Extract semantic information from the query.",
        temperature=0.1
    )

    print(f"Structured Response:\n{response.content}")
    print()


def example_openai_different_models():
    """Compare different OpenAI models."""
    print("=== OpenAI Model Comparison ===\n")

    models = ["gpt-4", "gpt-3.5-turbo"]
    prompt = "Generate SPARQL: Find proteins in humans"

    for model_name in models:
        provider = OpenAIProvider(model=model_name)

        response = provider.generate(
            prompt=prompt,
            temperature=0.1,
            max_tokens=200
        )

        print(f"Model: {model_name}")
        print(f"Tokens: {response.tokens_used}")
        print(f"Cost: ${response.cost:.6f}")
        print(f"Latency: {response.latency:.2f}s")
        print(f"Response: {response.content[:100]}...")
        print()


# ============================================================================
# Ollama Examples
# ============================================================================

def example_ollama_basic():
    """Basic Ollama usage with local models."""
    print("=== Ollama Basic Example ===\n")

    # Prerequisites:
    # 1. Install Ollama: https://ollama.ai
    # 2. Start Ollama: ollama serve
    # 3. Pull a model: ollama pull llama2

    provider = create_ollama_provider(model="llama2")

    # Test connection
    if not provider.test_connection():
        print("Error: Cannot connect to Ollama. Make sure it's running!")
        print("Start with: ollama serve")
        return

    response = provider.generate(
        prompt="Generate SPARQL query to find all proteins",
        system_prompt="You are a SPARQL expert.",
        temperature=0.1
    )

    print(f"Model: {response.model}")
    print(f"Response: {response.content}")
    print(f"Cost: ${response.cost} (free!)")
    print(f"Latency: {response.latency:.2f}s")
    print()


def example_ollama_different_models():
    """Try different Ollama models."""
    print("=== Ollama Different Models ===\n")

    # Popular models for code/SPARQL generation:
    # - llama2: General purpose
    # - codellama: Code generation
    # - mistral: Fast and capable
    # - mixtral: Large, very capable

    models = ["llama2", "codellama", "mistral"]

    for model_name in models:
        print(f"Trying {model_name}...")
        provider = create_ollama_provider(model=model_name)

        try:
            response = provider.generate(
                prompt="What is SPARQL?",
                max_tokens=100
            )
            print(f"  Success! Latency: {response.latency:.2f}s")
        except Exception as e:
            print(f"  Failed: {e}")
            print(f"  (Try: ollama pull {model_name})")

        print()


def example_ollama_custom_config():
    """Ollama with custom configuration."""
    print("=== Ollama Custom Configuration ===\n")

    provider = LocalProvider(
        model="llama2",
        api_base="http://localhost:11434/v1",
        temperature=0.2,
        max_tokens=1000,
        timeout=180,  # Longer timeout for complex queries
        context_length=8192
    )

    response = provider.generate(
        prompt="Explain SPARQL PREFIX declarations",
        system_prompt="You are a semantic web expert."
    )

    print(f"Response: {response.content[:200]}...")
    print()


# ============================================================================
# LM Studio Examples
# ============================================================================

def example_lmstudio_basic():
    """Basic LM Studio usage."""
    print("=== LM Studio Basic Example ===\n")

    # Prerequisites:
    # 1. Download LM Studio: https://lmstudio.ai
    # 2. Load a model in LM Studio
    # 3. Enable local server in settings (default port 1234)

    provider = create_lmstudio_provider(model="local-model")

    # Test connection
    if not provider.test_connection():
        print("Error: Cannot connect to LM Studio!")
        print("1. Open LM Studio")
        print("2. Load a model")
        print("3. Start local server (Settings -> Local Server)")
        return

    response = provider.generate(
        prompt="Generate a SPARQL query to find all diseases",
        temperature=0.1
    )

    print(f"Response: {response.content}")
    print(f"Latency: {response.latency:.2f}s")
    print()


# ============================================================================
# Custom Endpoint Examples
# ============================================================================

def example_custom_endpoint():
    """Custom OpenAI-compatible endpoint."""
    print("=== Custom Endpoint Example ===\n")

    # Example: Self-hosted vLLM, FastChat, or other OpenAI-compatible server
    provider = create_custom_provider(
        model="custom-llama",
        api_base="http://my-server:8000/v1",
        api_key="optional-api-key",  # If required
        temperature=0.1
    )

    response = provider.generate(
        prompt="What is RDF?",
        max_tokens=150
    )

    print(f"Response: {response.content}")
    print()


def example_custom_with_auth():
    """Custom endpoint with authentication."""
    print("=== Custom Endpoint with Auth ===\n")

    provider = LocalProvider(
        model="protected-model",
        api_base="https://my-secure-server.com/v1",
        api_key="your-api-key-here",
        verify_ssl=True,  # Verify SSL certificates
        timeout=60
    )

    response = provider.generate(
        prompt="Hello, world!",
        max_tokens=50
    )

    print(f"Response: {response.content}")
    print()


# ============================================================================
# Comparison Examples
# ============================================================================

def example_compare_providers():
    """Compare OpenAI vs Local model performance."""
    print("=== Provider Comparison ===\n")

    prompt = "Generate SPARQL: Find all genes associated with cancer"

    # OpenAI
    print("1. OpenAI GPT-4:")
    openai_provider = OpenAIProvider(model="gpt-4")
    openai_response = openai_provider.generate(prompt, temperature=0.1)
    print(f"   Latency: {openai_response.latency:.2f}s")
    print(f"   Cost: ${openai_response.cost:.4f}")
    print(f"   Response length: {len(openai_response.content)} chars")
    print()

    # Ollama
    print("2. Ollama (Local):")
    try:
        ollama_provider = create_ollama_provider(model="llama2")
        ollama_response = ollama_provider.generate(prompt, temperature=0.1)
        print(f"   Latency: {ollama_response.latency:.2f}s")
        print(f"   Cost: ${ollama_response.cost:.4f}")
        print(f"   Response length: {len(ollama_response.content)} chars")
    except Exception as e:
        print(f"   Error: {e}")

    print()


def example_fallback_pattern():
    """Implement fallback from OpenAI to local model."""
    print("=== Fallback Pattern Example ===\n")

    def generate_with_fallback(prompt: str) -> str:
        """Try OpenAI first, fall back to Ollama."""

        # Try OpenAI
        try:
            print("Trying OpenAI...")
            provider = OpenAIProvider(model="gpt-4")
            response = provider.generate(prompt, temperature=0.1, max_tokens=500)
            print("✓ OpenAI succeeded")
            return response.content
        except Exception as e:
            print(f"✗ OpenAI failed: {e}")

        # Fall back to Ollama
        try:
            print("Falling back to Ollama...")
            provider = create_ollama_provider(model="llama2")
            response = provider.generate(prompt, temperature=0.1, max_tokens=500)
            print("✓ Ollama succeeded")
            return response.content
        except Exception as e:
            print(f"✗ Ollama failed: {e}")
            return "Error: All providers failed"

    result = generate_with_fallback("What is SPARQL?")
    print(f"\nResult: {result[:100]}...")
    print()


# ============================================================================
# Utility Examples
# ============================================================================

def example_token_counting():
    """Demonstrate token counting."""
    print("=== Token Counting Example ===\n")

    provider = OpenAIProvider(model="gpt-4")

    texts = [
        "Hello world",
        "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10",
        "Generate a SPARQL query to find all proteins that interact with TP53 gene"
    ]

    for text in texts:
        token_count = provider.count_tokens(text)
        print(f"Text: {text[:50]}...")
        print(f"Tokens: {token_count}")
        print()


def example_cost_estimation():
    """Demonstrate cost estimation."""
    print("=== Cost Estimation Example ===\n")

    provider = OpenAIProvider(model="gpt-4")

    # Simulate token usage
    scenarios = [
        ("Simple query", 100, 50),
        ("Complex query", 500, 300),
        ("Large context", 2000, 1000),
    ]

    for name, prompt_tokens, completion_tokens in scenarios:
        cost = provider.estimate_cost(prompt_tokens, completion_tokens)
        print(f"{name}:")
        print(f"  Prompt tokens: {prompt_tokens}")
        print(f"  Completion tokens: {completion_tokens}")
        print(f"  Total cost: ${cost:.4f}")
        print()


def example_model_info():
    """Get model information."""
    print("=== Model Information ===\n")

    providers = [
        ("OpenAI GPT-4", OpenAIProvider(model="gpt-4")),
        ("OpenAI GPT-3.5", OpenAIProvider(model="gpt-3.5-turbo")),
        ("Ollama Llama2", create_ollama_provider(model="llama2")),
    ]

    for name, provider in providers:
        info = provider.get_model_info()
        print(f"{name}:")
        for key, value in info.items():
            print(f"  {key}: {value}")
        print()


# ============================================================================
# Main
# ============================================================================

def main():
    """Run all examples."""
    print("=" * 70)
    print("OpenAI and Local LLM Provider Examples")
    print("=" * 70)
    print()

    # OpenAI Examples
    # Uncomment if you have OPENAI_API_KEY set
    # example_openai_basic()
    # example_openai_function_calling()
    # example_openai_json_schema()
    # example_openai_different_models()

    # Ollama Examples
    # Uncomment if you have Ollama running
    # example_ollama_basic()
    # example_ollama_different_models()
    # example_ollama_custom_config()

    # LM Studio Examples
    # Uncomment if you have LM Studio running
    # example_lmstudio_basic()

    # Custom Endpoint Examples
    # example_custom_endpoint()

    # Comparison Examples
    # example_compare_providers()
    # example_fallback_pattern()

    # Utility Examples
    example_token_counting()
    example_cost_estimation()
    example_model_info()


if __name__ == "__main__":
    main()
