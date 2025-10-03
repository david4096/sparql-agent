"""
OpenAI and Local LLM Provider implementations.

This module provides LLM provider implementations for:
1. OpenAI API (GPT-4, GPT-3.5-turbo)
2. OpenAI-compatible APIs (Ollama, LMStudio, etc.)
3. Local models with custom endpoints

Supports function calling, streaming, and flexible configuration.
"""

import json
import time
from typing import Any, Dict, List, Optional, Union
import logging

try:
    from openai import OpenAI, OpenAIError, APIError, APIConnectionError, RateLimitError
except ImportError:
    raise ImportError(
        "OpenAI library is required. Install with: pip install openai>=1.0.0"
    )

from ..core.base import LLMProvider
from ..core.types import LLMResponse
from ..core.exceptions import (
    LLMError,
    LLMAuthenticationError,
    LLMRateLimitError,
)


logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """
    OpenAI API provider for GPT models with function calling support.

    Supports:
    - GPT-4, GPT-4-turbo, GPT-3.5-turbo models
    - Function calling for structured outputs
    - Streaming responses
    - Token counting and cost estimation

    Example:
        ```python
        provider = OpenAIProvider(
            model="gpt-4",
            api_key="sk-...",
            temperature=0.1
        )

        response = provider.generate(
            prompt="Translate to SPARQL: Find all proteins",
            system_prompt="You are a SPARQL expert"
        )
        ```
    """

    # Model pricing (per 1K tokens) - Updated as of 2024
    MODEL_PRICING = {
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-4-turbo-preview": {"input": 0.01, "output": 0.03},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        "gpt-3.5-turbo-16k": {"input": 0.003, "output": 0.004},
    }

    # Model context lengths
    MODEL_CONTEXT_LENGTHS = {
        "gpt-4": 8192,
        "gpt-4-32k": 32768,
        "gpt-4-turbo": 128000,
        "gpt-4-turbo-preview": 128000,
        "gpt-3.5-turbo": 4096,
        "gpt-3.5-turbo-16k": 16384,
    }

    def __init__(
        self,
        model: str = "gpt-4",
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        organization: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        top_p: float = 1.0,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        timeout: int = 60,
        max_retries: int = 3,
        **kwargs
    ):
        """
        Initialize OpenAI provider.

        Args:
            model: Model name (e.g., 'gpt-4', 'gpt-3.5-turbo')
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)
            api_base: Optional base URL for API (for proxies)
            organization: Optional organization ID
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            frequency_penalty: Frequency penalty (-2.0 to 2.0)
            presence_penalty: Presence penalty (-2.0 to 2.0)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries
            **kwargs: Additional OpenAI client arguments
        """
        super().__init__(model=model, api_key=api_key, **kwargs)

        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.frequency_penalty = frequency_penalty
        self.presence_penalty = presence_penalty
        self.timeout = timeout
        self.max_retries = max_retries

        # Initialize OpenAI client
        client_kwargs = {
            "api_key": api_key,
            "timeout": timeout,
            "max_retries": max_retries,
        }

        if api_base:
            client_kwargs["base_url"] = api_base
        if organization:
            client_kwargs["organization"] = organization

        try:
            self.client = OpenAI(**client_kwargs)
        except Exception as e:
            raise LLMError(f"Failed to initialize OpenAI client: {e}")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        functions: Optional[List[Dict[str, Any]]] = None,
        function_call: Optional[Union[str, Dict[str, str]]] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response from OpenAI.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt for context
            temperature: Override default temperature
            max_tokens: Override default max tokens
            stream: Enable streaming (not fully implemented)
            functions: List of function definitions for function calling
            function_call: Control function calling ("auto", "none", or {"name": "function_name"})
            **kwargs: Additional OpenAI API parameters

        Returns:
            LLMResponse with generated content and metadata

        Raises:
            LLMError: If generation fails
            LLMAuthenticationError: If authentication fails
            LLMRateLimitError: If rate limit is exceeded
        """
        start_time = time.time()

        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Prepare API call parameters
        api_params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
        }

        if max_tokens is not None or self.max_tokens is not None:
            api_params["max_tokens"] = max_tokens or self.max_tokens

        if functions:
            api_params["functions"] = functions
        if function_call:
            api_params["function_call"] = function_call

        # Add any additional kwargs
        api_params.update(kwargs)

        try:
            # Make API call
            response = self.client.chat.completions.create(**api_params)

            # Extract response data
            choice = response.choices[0]
            message = choice.message

            # Handle function calling response
            if hasattr(message, 'function_call') and message.function_call:
                content = json.dumps({
                    "function_call": {
                        "name": message.function_call.name,
                        "arguments": message.function_call.arguments
                    }
                })
            else:
                content = message.content or ""

            # Calculate latency
            latency = time.time() - start_time

            # Extract token usage
            usage = response.usage
            prompt_tokens = usage.prompt_tokens if usage else None
            completion_tokens = usage.completion_tokens if usage else None
            total_tokens = usage.total_tokens if usage else None

            # Estimate cost
            cost = self.estimate_cost(
                prompt_tokens or 0,
                completion_tokens or 0
            )

            return LLMResponse(
                content=content,
                model=self.model,
                prompt=prompt,
                tokens_used=total_tokens,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                finish_reason=choice.finish_reason,
                cost=cost,
                latency=latency,
                metadata={
                    "system_prompt": system_prompt,
                    "temperature": api_params["temperature"],
                    "response_id": response.id,
                    "has_function_call": hasattr(message, 'function_call') and message.function_call is not None,
                }
            )

        except RateLimitError as e:
            logger.error(f"OpenAI rate limit exceeded: {e}")
            raise LLMRateLimitError(f"Rate limit exceeded: {e}")
        except APIConnectionError as e:
            logger.error(f"OpenAI connection error: {e}")
            raise LLMError(f"Connection error: {e}")
        except APIError as e:
            if e.status_code == 401:
                raise LLMAuthenticationError(f"Authentication failed: {e}")
            logger.error(f"OpenAI API error: {e}")
            raise LLMError(f"API error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in OpenAI generation: {e}")
            raise LLMError(f"Generation failed: {e}")

    def generate_with_json_schema(
        self,
        prompt: str,
        json_schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response conforming to a JSON schema using function calling.

        Args:
            prompt: User prompt
            json_schema: JSON schema for the response
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            **kwargs: Additional parameters

        Returns:
            LLMResponse with JSON content conforming to schema
        """
        # Convert JSON schema to function definition
        function_def = {
            "name": "structured_response",
            "description": "Generate a structured response",
            "parameters": json_schema
        }

        # Add instruction to system prompt
        schema_prompt = system_prompt or ""
        schema_prompt += "\n\nRespond using the structured_response function with the required schema."

        response = self.generate(
            prompt=prompt,
            system_prompt=schema_prompt,
            temperature=temperature,
            functions=[function_def],
            function_call={"name": "structured_response"},
            **kwargs
        )

        # Parse function call response
        try:
            response_data = json.loads(response.content)
            if "function_call" in response_data:
                arguments = response_data["function_call"]["arguments"]
                # Ensure arguments is parsed JSON
                if isinstance(arguments, str):
                    arguments = json.loads(arguments)
                response.content = json.dumps(arguments, indent=2)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON schema response: {e}")

        return response

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text (approximate).

        For accurate counting, use tiktoken library.
        This provides a rough estimate: ~4 chars per token for English.

        Args:
            text: Text to count tokens for

        Returns:
            Approximate token count
        """
        try:
            import tiktoken
            encoding = tiktoken.encoding_for_model(self.model)
            return len(encoding.encode(text))
        except ImportError:
            # Fallback: rough approximation
            return len(text) // 4
        except Exception:
            # If model not found, use cl100k_base (GPT-4 default)
            try:
                import tiktoken
                encoding = tiktoken.get_encoding("cl100k_base")
                return len(encoding.encode(text))
            except:
                return len(text) // 4

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Estimate cost of API call.

        Args:
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens

        Returns:
            Estimated cost in USD
        """
        # Find matching model pricing
        model_key = self.model
        for key in self.MODEL_PRICING.keys():
            if key in self.model:
                model_key = key
                break

        if model_key not in self.MODEL_PRICING:
            logger.warning(f"Unknown model for pricing: {self.model}")
            return 0.0

        pricing = self.MODEL_PRICING[model_key]
        input_cost = (prompt_tokens / 1000) * pricing["input"]
        output_cost = (completion_tokens / 1000) * pricing["output"]

        return input_cost + output_cost

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model.

        Returns:
            Dictionary with model information
        """
        context_length = self.MODEL_CONTEXT_LENGTHS.get(
            self.model,
            8192  # default
        )

        return {
            "model": self.model,
            "provider": "openai",
            "context_length": context_length,
            "supports_functions": True,
            "supports_streaming": True,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

    def test_connection(self) -> bool:
        """
        Test connection to OpenAI API.

        Returns:
            True if connection successful
        """
        try:
            response = self.generate(
                prompt="Hello",
                max_tokens=5
            )
            return response.content is not None
        except Exception as e:
            logger.error(f"OpenAI connection test failed: {e}")
            return False


class LocalProvider(LLMProvider):
    """
    Provider for local and OpenAI-compatible LLM endpoints.

    Supports:
    - Ollama (http://localhost:11434)
    - LMStudio (http://localhost:1234)
    - Any OpenAI-compatible API
    - Custom local models

    Features:
    - No API key required for local models
    - Custom endpoint configuration
    - Model parameter customization
    - Compatible with OpenAI function calling (if supported by endpoint)

    Example with Ollama:
        ```python
        provider = LocalProvider(
            model="llama2",
            api_base="http://localhost:11434/v1",
            temperature=0.1
        )

        response = provider.generate(
            prompt="Translate to SPARQL: Find all proteins"
        )
        ```

    Example with LMStudio:
        ```python
        provider = LocalProvider(
            model="local-model",
            api_base="http://localhost:1234/v1",
        )
        ```
    """

    def __init__(
        self,
        model: str,
        api_base: str = "http://localhost:11434/v1",
        api_key: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        top_p: float = 1.0,
        timeout: int = 120,
        max_retries: int = 3,
        context_length: int = 4096,
        verify_ssl: bool = True,
        **kwargs
    ):
        """
        Initialize local/OpenAI-compatible provider.

        Args:
            model: Model name (e.g., 'llama2', 'mistral', 'local-model')
            api_base: Base URL for the API endpoint
            api_key: Optional API key (not needed for most local setups)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            timeout: Request timeout in seconds (longer for local models)
            max_retries: Maximum number of retries
            context_length: Model context length
            verify_ssl: Whether to verify SSL certificates
            **kwargs: Additional client arguments
        """
        super().__init__(model=model, api_key=api_key, **kwargs)

        self.api_base = api_base
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.timeout = timeout
        self.max_retries = max_retries
        self.context_length = context_length
        self.verify_ssl = verify_ssl

        # Initialize OpenAI client with custom base URL
        # For local models, use a dummy API key if none provided
        client_kwargs = {
            "api_key": api_key or "not-needed",
            "base_url": api_base,
            "timeout": timeout,
            "max_retries": max_retries,
        }

        try:
            self.client = OpenAI(**client_kwargs)
            logger.info(f"Initialized local provider: {api_base} (model: {model})")
        except Exception as e:
            raise LLMError(f"Failed to initialize local provider: {e}")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        functions: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response from local model.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Override default temperature
            max_tokens: Override default max tokens
            stream: Enable streaming (not fully implemented)
            functions: Optional function definitions (if supported)
            **kwargs: Additional API parameters

        Returns:
            LLMResponse with generated content

        Raises:
            LLMError: If generation fails
        """
        start_time = time.time()

        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Prepare API parameters
        api_params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "top_p": self.top_p,
        }

        if max_tokens is not None or self.max_tokens is not None:
            api_params["max_tokens"] = max_tokens or self.max_tokens

        # Add functions if provided and supported
        if functions:
            api_params["functions"] = functions

        # Add additional kwargs
        api_params.update(kwargs)

        try:
            # Make API call
            response = self.client.chat.completions.create(**api_params)

            # Extract response
            choice = response.choices[0]
            message = choice.message
            content = message.content or ""

            # Calculate latency
            latency = time.time() - start_time

            # Extract token usage (may not be available from all endpoints)
            usage = getattr(response, 'usage', None)
            prompt_tokens = getattr(usage, 'prompt_tokens', None) if usage else None
            completion_tokens = getattr(usage, 'completion_tokens', None) if usage else None
            total_tokens = getattr(usage, 'total_tokens', None) if usage else None

            # Local models have no cost
            cost = 0.0

            return LLMResponse(
                content=content,
                model=self.model,
                prompt=prompt,
                tokens_used=total_tokens,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                finish_reason=choice.finish_reason,
                cost=cost,
                latency=latency,
                metadata={
                    "system_prompt": system_prompt,
                    "temperature": api_params["temperature"],
                    "api_base": self.api_base,
                    "provider": "local",
                }
            )

        except APIConnectionError as e:
            logger.error(f"Local model connection error: {e}")
            raise LLMError(
                f"Failed to connect to {self.api_base}. "
                f"Make sure your local model server is running. Error: {e}"
            )
        except APIError as e:
            logger.error(f"Local model API error: {e}")
            raise LLMError(f"Local model API error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in local model generation: {e}")
            raise LLMError(f"Generation failed: {e}")

    def generate_with_json_schema(
        self,
        prompt: str,
        json_schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """
        Generate response conforming to JSON schema.

        Note: This uses prompt engineering for local models that don't
        support function calling. May be less reliable than OpenAI's
        native function calling.

        Args:
            prompt: User prompt
            json_schema: JSON schema for response
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            **kwargs: Additional parameters

        Returns:
            LLMResponse with JSON content
        """
        # Enhance prompt with schema instructions
        schema_instruction = (
            f"\n\nRespond ONLY with valid JSON matching this schema:\n"
            f"```json\n{json.dumps(json_schema, indent=2)}\n```\n"
            f"Do not include any explanatory text, only the JSON object."
        )

        enhanced_prompt = prompt + schema_instruction
        enhanced_system = (system_prompt or "") + "\nYou always respond with valid JSON."

        response = self.generate(
            prompt=enhanced_prompt,
            system_prompt=enhanced_system,
            temperature=temperature,
            **kwargs
        )

        # Try to extract and validate JSON
        try:
            # Look for JSON in response
            content = response.content.strip()

            # Try to find JSON block
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                content = content[start:end].strip()
            elif "```" in content:
                start = content.find("```") + 3
                end = content.find("```", start)
                content = content[start:end].strip()

            # Validate JSON
            parsed = json.loads(content)
            response.content = json.dumps(parsed, indent=2)

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from local model: {e}")
            # Return as-is, let caller handle

        return response

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text (approximate).

        Uses simple heuristic since tiktoken may not support local models.

        Args:
            text: Text to count

        Returns:
            Approximate token count
        """
        # Simple approximation: ~4 chars per token for English
        # For more accurate counting, implement model-specific tokenizer
        return len(text) // 4

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Estimate cost (always 0.0 for local models).

        Args:
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens

        Returns:
            0.0 (local models are free)
        """
        return 0.0

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the local model.

        Returns:
            Dictionary with model information
        """
        return {
            "model": self.model,
            "provider": "local",
            "api_base": self.api_base,
            "context_length": self.context_length,
            "supports_functions": False,  # Most local models don't support this
            "supports_streaming": True,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "cost": 0.0,
        }

    def test_connection(self) -> bool:
        """
        Test connection to local model endpoint.

        Returns:
            True if connection successful
        """
        try:
            response = self.generate(
                prompt="Hello",
                max_tokens=5
            )
            return response.content is not None
        except Exception as e:
            logger.error(f"Local model connection test failed: {e}")
            return False


# Convenience functions for common configurations

def create_openai_provider(
    model: str = "gpt-4",
    api_key: Optional[str] = None,
    **kwargs
) -> OpenAIProvider:
    """
    Create OpenAI provider with default settings.

    Args:
        model: Model name
        api_key: API key (or use OPENAI_API_KEY env var)
        **kwargs: Additional provider arguments

    Returns:
        Configured OpenAIProvider instance
    """
    return OpenAIProvider(model=model, api_key=api_key, **kwargs)


def create_ollama_provider(
    model: str = "llama2",
    host: str = "localhost",
    port: int = 11434,
    **kwargs
) -> LocalProvider:
    """
    Create provider for Ollama local models.

    Args:
        model: Ollama model name (e.g., 'llama2', 'mistral', 'codellama')
        host: Ollama server host
        port: Ollama server port
        **kwargs: Additional provider arguments

    Returns:
        Configured LocalProvider for Ollama

    Example:
        ```python
        # Start Ollama: ollama serve
        # Pull model: ollama pull llama2
        provider = create_ollama_provider(model="llama2")
        ```
    """
    api_base = f"http://{host}:{port}/v1"
    return LocalProvider(
        model=model,
        api_base=api_base,
        timeout=120,  # Ollama can be slower
        **kwargs
    )


def create_lmstudio_provider(
    model: str = "local-model",
    host: str = "localhost",
    port: int = 1234,
    **kwargs
) -> LocalProvider:
    """
    Create provider for LM Studio local models.

    Args:
        model: Model name (use 'local-model' or check LM Studio UI)
        host: LM Studio server host
        port: LM Studio server port
        **kwargs: Additional provider arguments

    Returns:
        Configured LocalProvider for LM Studio

    Example:
        ```python
        # Start LM Studio and load a model
        # Enable local server in LM Studio settings
        provider = create_lmstudio_provider()
        ```
    """
    api_base = f"http://{host}:{port}/v1"
    return LocalProvider(
        model=model,
        api_base=api_base,
        timeout=120,
        **kwargs
    )


def create_custom_provider(
    model: str,
    api_base: str,
    api_key: Optional[str] = None,
    **kwargs
) -> LocalProvider:
    """
    Create provider for custom OpenAI-compatible endpoint.

    Args:
        model: Model name
        api_base: Base URL for the API
        api_key: Optional API key
        **kwargs: Additional provider arguments

    Returns:
        Configured LocalProvider

    Example:
        ```python
        provider = create_custom_provider(
            model="custom-model",
            api_base="http://my-server:8000/v1",
            api_key="optional-key"
        )
        ```
    """
    return LocalProvider(
        model=model,
        api_base=api_base,
        api_key=api_key,
        **kwargs
    )
