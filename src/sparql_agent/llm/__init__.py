"""
LLM integration module.

This module provides integrations with various LLM providers for
natural language to SPARQL query translation.

Provides:
- LLMClient: Abstract base class for all LLM providers
- ProviderManager: Manages multiple providers with load balancing and fallback
- Provider implementations: OpenAI, Anthropic, Local models, etc.
- Unified interfaces for generation, streaming, token counting, and cost tracking
"""

from .client import (
    # Core classes
    LLMClient,
    ProviderManager,

    # Request/Response types
    LLMRequest,
    LLMResponse,
    StreamChunk,

    # Configuration types
    TokenUsage,
    GenerationMetrics,
    ModelCapabilities,
    RetryConfig,

    # Enums
    LLMProvider,
    StreamChunkType,

    # Global functions
    get_provider_manager,
    reset_provider_manager,
)

# Optional provider imports - only available if dependencies are installed
_OPENAI_AVAILABLE = False
_ANTHROPIC_AVAILABLE = False

try:
    from .openai_provider import (
        OpenAIProvider,
        LocalProvider,
        create_openai_provider,
        create_ollama_provider,
        create_lmstudio_provider,
        create_custom_provider,
    )
    _OPENAI_AVAILABLE = True
except ImportError:
    pass

try:
    from .anthropic_provider import (
        AnthropicProvider,
        create_anthropic_provider,
    )
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    pass

# Base exports (always available)
__all__ = [
    # Core classes
    "LLMClient",
    "ProviderManager",

    # Request/Response types
    "LLMRequest",
    "LLMResponse",
    "StreamChunk",

    # Configuration types
    "TokenUsage",
    "GenerationMetrics",
    "ModelCapabilities",
    "RetryConfig",

    # Enums
    "LLMProvider",
    "StreamChunkType",

    # Global functions
    "get_provider_manager",
    "reset_provider_manager",
]

# Add optional providers to exports if available
if _OPENAI_AVAILABLE:
    __all__.extend([
        "OpenAIProvider",
        "LocalProvider",
        "create_openai_provider",
        "create_ollama_provider",
        "create_lmstudio_provider",
        "create_custom_provider",
    ])

if _ANTHROPIC_AVAILABLE:
    __all__.extend([
        "AnthropicProvider",
        "create_anthropic_provider",
    ])
