"""
Test script for OpenAI and Local providers.

This script validates that providers are correctly configured and can
generate responses. Run this to verify your setup.
"""

import sys
import time
from typing import Optional

try:
    from .openai_provider import (
        OpenAIProvider,
        LocalProvider,
        create_ollama_provider,
        create_lmstudio_provider,
    )
except ImportError:
    # Handle direct execution
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
    from sparql_agent.llm.openai_provider import (
        OpenAIProvider,
        LocalProvider,
        create_ollama_provider,
        create_lmstudio_provider,
    )


class ProviderTester:
    """Test harness for LLM providers."""

    def __init__(self):
        self.results = []

    def test_provider(self, name: str, provider, skip_if_failed: bool = True) -> bool:
        """
        Test a provider with a simple prompt.

        Args:
            name: Provider name for display
            provider: Provider instance to test
            skip_if_failed: Skip if connection fails

        Returns:
            True if test passed, False otherwise
        """
        print(f"\n{'='*60}")
        print(f"Testing: {name}")
        print(f"{'='*60}")

        # Test connection
        print("1. Testing connection...")
        try:
            if not provider.test_connection():
                print("   ✗ Connection test failed")
                if skip_if_failed:
                    print("   ⊘ Skipping (provider not available)")
                    self.results.append((name, "skipped"))
                    return False
        except Exception as e:
            print(f"   ✗ Connection error: {e}")
            if skip_if_failed:
                print("   ⊘ Skipping (provider not available)")
                self.results.append((name, "skipped"))
                return False

        print("   ✓ Connection successful")

        # Test model info
        print("\n2. Getting model info...")
        try:
            info = provider.get_model_info()
            print(f"   Model: {info.get('model')}")
            print(f"   Provider: {info.get('provider')}")
            print(f"   Context length: {info.get('context_length')}")
            print(f"   Supports functions: {info.get('supports_functions')}")
        except Exception as e:
            print(f"   ⚠ Warning: {e}")

        # Test generation
        print("\n3. Testing generation...")
        test_prompt = "What is SPARQL? Answer in one sentence."

        try:
            start_time = time.time()
            response = provider.generate(
                prompt=test_prompt,
                max_tokens=100,
                temperature=0.1
            )
            duration = time.time() - start_time

            print(f"   ✓ Generation successful")
            print(f"   Response: {response.content[:100]}...")
            print(f"   Latency: {duration:.2f}s")

            if response.tokens_used:
                print(f"   Tokens: {response.tokens_used}")
            if response.cost:
                print(f"   Cost: ${response.cost:.6f}")

            self.results.append((name, "passed"))
            return True

        except Exception as e:
            print(f"   ✗ Generation failed: {e}")
            self.results.append((name, "failed"))
            return False

    def test_token_counting(self, provider) -> bool:
        """Test token counting functionality."""
        print("\n4. Testing token counting...")
        try:
            texts = [
                "Hello",
                "SELECT ?s ?p ?o WHERE { ?s ?p ?o }",
            ]

            for text in texts:
                count = provider.count_tokens(text)
                print(f"   '{text[:30]}...' -> {count} tokens")

            print("   ✓ Token counting works")
            return True
        except Exception as e:
            print(f"   ⚠ Token counting failed: {e}")
            return False

    def test_cost_estimation(self, provider) -> bool:
        """Test cost estimation."""
        print("\n5. Testing cost estimation...")
        try:
            cost = provider.estimate_cost(100, 50)
            print(f"   100 prompt + 50 completion tokens = ${cost:.6f}")
            print("   ✓ Cost estimation works")
            return True
        except Exception as e:
            print(f"   ⚠ Cost estimation failed: {e}")
            return False

    def print_summary(self):
        """Print test summary."""
        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print(f"{'='*60}")

        passed = sum(1 for _, status in self.results if status == "passed")
        failed = sum(1 for _, status in self.results if status == "failed")
        skipped = sum(1 for _, status in self.results if status == "skipped")

        for name, status in self.results:
            symbol = {
                "passed": "✓",
                "failed": "✗",
                "skipped": "⊘"
            }.get(status, "?")
            print(f"{symbol} {name}: {status}")

        print(f"\nTotal: {len(self.results)} tests")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Skipped: {skipped}")


def main():
    """Run all provider tests."""
    print("OpenAI and Local Provider Test Suite")
    print("="*60)

    tester = ProviderTester()

    # Test OpenAI (if API key available)
    print("\n\nChecking OpenAI availability...")
    import os
    if os.getenv("OPENAI_API_KEY"):
        print("✓ OPENAI_API_KEY found")
        try:
            provider = OpenAIProvider(model="gpt-3.5-turbo")
            if tester.test_provider("OpenAI GPT-3.5", provider):
                tester.test_token_counting(provider)
                tester.test_cost_estimation(provider)
        except Exception as e:
            print(f"✗ OpenAI setup failed: {e}")
    else:
        print("⊘ OPENAI_API_KEY not set, skipping OpenAI tests")
        print("  Set with: export OPENAI_API_KEY='sk-...'")

    # Test Ollama (if running)
    print("\n\nChecking Ollama availability...")
    try:
        provider = create_ollama_provider(model="llama2")
        if tester.test_provider("Ollama (llama2)", provider):
            tester.test_token_counting(provider)
    except Exception as e:
        print(f"⊘ Ollama not available: {e}")

    # Test LM Studio (if running)
    print("\n\nChecking LM Studio availability...")
    try:
        provider = create_lmstudio_provider()
        tester.test_provider("LM Studio", provider)
    except Exception as e:
        print(f"⊘ LM Studio not available: {e}")

    # Print summary
    tester.print_summary()

    # Setup instructions
    print("\n" + "="*60)
    print("SETUP INSTRUCTIONS")
    print("="*60)

    if not os.getenv("OPENAI_API_KEY"):
        print("\nOpenAI Setup:")
        print("  1. Get API key: https://platform.openai.com/api-keys")
        print("  2. Set environment: export OPENAI_API_KEY='sk-...'")

    print("\nOllama Setup:")
    print("  1. Install: https://ollama.ai")
    print("  2. Start: ollama serve")
    print("  3. Pull model: ollama pull llama2")

    print("\nLM Studio Setup:")
    print("  1. Download: https://lmstudio.ai")
    print("  2. Load a model in the UI")
    print("  3. Enable local server (Settings → Local Server)")


if __name__ == "__main__":
    main()
