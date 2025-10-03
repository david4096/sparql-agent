# Anthropic Claude Provider for SPARQL Agent

Complete integration with Anthropic's Claude models for natural language to SPARQL query generation and semantic web tasks.

## Features

- **Full Claude 3 Family Support**: Claude 3.5 Sonnet, Opus, Sonnet, and Haiku
- **Streaming Responses**: Real-time token streaming for interactive applications
- **Function/Tool Calling**: Native support for Claude's tool use capabilities
- **Token Counting & Cost Estimation**: Accurate tracking of API usage and costs
- **Rate Limiting**: Built-in rate limiting to comply with Anthropic's limits
- **Automatic Retry Logic**: Configurable retry behavior with exponential backoff
- **Provider Fallback**: Seamless fallback to other providers through ProviderManager
- **Type Safety**: Full type hints for better IDE support and type checking

## Installation

```bash
# Install with Anthropic support
pip install "sparql-agent[anthropic]"

# Or install manually
pip install anthropic>=0.25.0
```

## Quick Start

### Basic Usage

```python
from sparql_agent.llm import AnthropicProvider, LLMRequest

# Create provider (API key from ANTHROPIC_API_KEY env var)
provider = AnthropicProvider(model="claude-3-5-sonnet-20241022")

# Create request
request = LLMRequest(
    prompt="What is SPARQL?",
    system_prompt="You are a semantic web expert.",
    temperature=0.7,
    max_tokens=500,
)

# Generate response
response = provider.generate(request)
print(response.content)
```

### Using the Convenience Function

```python
from sparql_agent.llm import create_anthropic_provider

# Quick provider creation
provider = create_anthropic_provider("claude-3-5-sonnet-20241022")
response = provider.generate_text("Explain RDF triples")
```

## Available Models

| Model | Context | Max Output | Input Price | Output Price | Best For |
|-------|---------|------------|-------------|--------------|----------|
| `claude-3-5-sonnet-20241022` | 200K | 8,192 | $3/1M | $15/1M | Complex reasoning, code |
| `claude-3-5-sonnet-20240620` | 200K | 8,192 | $3/1M | $15/1M | Balanced performance |
| `claude-3-opus-20240229` | 200K | 4,096 | $15/1M | $75/1M | Highest capability |
| `claude-3-sonnet-20240229` | 200K | 4,096 | $3/1M | $15/1M | General tasks |
| `claude-3-haiku-20240307` | 200K | 4,096 | $0.25/1M | $1.25/1M | Fast, simple tasks |

## Configuration

### Environment Variables

```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

### Initialization Options

```python
provider = AnthropicProvider(
    model="claude-3-5-sonnet-20241022",
    api_key="optional-explicit-key",
    timeout=60.0,
    default_max_tokens=4096,
    retry_config=RetryConfig(
        max_retries=3,
        initial_delay=1.0,
        exponential_base=2.0,
    )
)
```

## Advanced Usage

### Streaming Responses

```python
request = LLMRequest(
    prompt="Explain semantic web technologies",
    temperature=0.7,
)

for chunk in provider.generate_streaming(request):
    if chunk.type.value == "content":
        print(chunk.content, end="", flush=True)
    elif chunk.type.value == "done":
        print(f"\nTime: {chunk.metadata['total_time_ms']:.2f}ms")
```

### Function/Tool Calling

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "execute_sparql",
            "description": "Execute a SPARQL query",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "SPARQL query"}
                },
                "required": ["query"]
            }
        }
    }
]

request = LLMRequest(
    prompt="Find all people in the knowledge graph",
    tools=tools,
)

response = provider.generate(request)

if response.tool_calls:
    for call in response.tool_calls:
        function_name = call['function']['name']
        arguments = call['function']['arguments']
        print(f"Tool: {function_name}, Args: {arguments}")
```

### System Prompts for SPARQL Generation

```python
SPARQL_SYSTEM_PROMPT = """You are an expert in SPARQL and semantic web technologies.
When generating SPARQL queries:
1. Always include necessary PREFIX declarations
2. Use proper syntax and best practices
3. Optimize for performance when possible
4. Include comments explaining complex patterns
5. Validate URIs and property paths
"""

request = LLMRequest(
    prompt="Generate a query to find all proteins that interact with P12345",
    system_prompt=SPARQL_SYSTEM_PROMPT,
    temperature=0.3,  # Lower temperature for more deterministic code
)

response = provider.generate(request)
```

### Cost Tracking

```python
# Get estimated costs before generating
prompt_tokens = provider.count_tokens(request.prompt)
estimated_cost = provider.estimate_cost(prompt_tokens, 500)
print(f"Estimated cost: ${estimated_cost:.6f}")

# Get actual costs after generation
response = provider.generate(request)
actual_cost = provider.estimate_cost(
    response.usage.prompt_tokens,
    response.usage.completion_tokens
)
print(f"Actual cost: ${actual_cost:.6f}")

# Track cumulative metrics
metrics = provider.get_metrics()
print(f"Total requests: {metrics['request_count']}")
print(f"Total cost: ${metrics['total_cost_usd']:.4f}")
print(f"Average tokens per request: {metrics['avg_tokens_per_request']:.1f}")
```

### Provider Manager Integration

```python
from sparql_agent.llm import ProviderManager, get_provider_manager

# Get global manager
manager = get_provider_manager()

# Register Anthropic provider
anthropic_provider = AnthropicProvider("claude-3-5-sonnet-20241022")
manager.register_provider(
    name="claude-sonnet",
    client=anthropic_provider,
    priority=10,  # Higher priority
    set_as_default=True
)

# Register fallback provider
haiku_provider = AnthropicProvider("claude-3-haiku-20240307")
manager.register_provider(
    name="claude-haiku",
    client=haiku_provider,
    priority=5,  # Lower priority fallback
)

# Generate with automatic fallback
response = manager.generate_with_fallback(request)

# Load balancing across providers
response = manager.generate_with_load_balancing(
    request,
    strategy="lowest_cost"  # or "round_robin", "least_loaded"
)
```

### Error Handling

```python
from sparql_agent.core.exceptions import (
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMQuotaExceededError,
)

try:
    response = provider.generate(request)
except LLMAuthenticationError as e:
    print(f"Authentication failed: {e}")
except LLMRateLimitError as e:
    print(f"Rate limit exceeded: {e}")
    # Wait and retry
except LLMTimeoutError as e:
    print(f"Request timed out: {e}")
except LLMQuotaExceededError as e:
    print(f"Quota exceeded: {e}")
    # Switch to different provider
```

## Model Selection Guide

### For SPARQL Query Generation

**Recommended: Claude 3.5 Sonnet (20241022)**
- Best balance of quality and cost
- Excellent at structured output (code, queries)
- Fast enough for interactive use
- Good understanding of semantic web concepts

**Alternative: Claude 3 Haiku (for simple queries)**
- Much cheaper ($0.25/1M vs $3/1M input)
- Fast response times
- Good for simple SELECT queries
- May struggle with complex CONSTRUCT or federated queries

### For Query Explanation/Documentation

**Recommended: Claude 3.5 Sonnet**
- Clear, concise explanations
- Good at technical writing
- Can adapt tone to audience

### For Ontology Analysis

**Recommended: Claude 3 Opus (for complex ontologies)**
- Best reasoning capabilities
- Can handle large context windows
- Better at understanding complex relationships

**Alternative: Claude 3.5 Sonnet (for most ontologies)**
- Usually sufficient for standard ontologies
- Much more cost-effective
- Faster response times

## Performance Optimization

### Token Optimization

```python
# Use system prompts to reduce repeated context
SHARED_CONTEXT = """Available prefixes:
  @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
  @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>
  @prefix : <http://example.org/>
"""

request = LLMRequest(
    prompt="Generate query for...",
    system_prompt=SHARED_CONTEXT,  # Included in every request
)
```

### Caching Strategies

```python
# Cache common queries/responses
import functools

@functools.lru_cache(maxsize=128)
def generate_query(natural_language: str) -> str:
    request = LLMRequest(prompt=natural_language)
    response = provider.generate(request)
    return response.content
```

### Batch Processing

```python
# Process multiple queries efficiently
queries = ["query1", "query2", "query3"]

responses = []
for query in queries:
    request = LLMRequest(prompt=query)
    response = provider.generate(request)
    responses.append(response)

    # Rate limiting handled automatically
```

## Best Practices

### 1. Use Appropriate Temperature

```python
# For deterministic output (queries, code)
request = LLMRequest(prompt="...", temperature=0.3)

# For creative output (explanations, examples)
request = LLMRequest(prompt="...", temperature=0.7)
```

### 2. Set Token Limits

```python
# Prevent runaway costs
request = LLMRequest(
    prompt="...",
    max_tokens=500,  # Reasonable limit
)
```

### 3. Use System Prompts

```python
# Guide behavior consistently
SYSTEM_PROMPT = """You are a SPARQL expert.
- Always validate syntax
- Use standard prefixes
- Optimize for performance
- Explain your reasoning
"""
```

### 4. Monitor Costs

```python
# Regular metrics checks
if provider.get_metrics()['total_cost_usd'] > 10.0:
    print("Warning: High API costs!")
    # Switch to cheaper model
```

### 5. Handle Errors Gracefully

```python
# Use retry logic
from sparql_agent.llm import RetryConfig

provider = AnthropicProvider(
    model="...",
    retry_config=RetryConfig(
        max_retries=3,
        retry_on_rate_limit=True,
        retry_on_timeout=True,
    )
)
```

## Testing

### Mock Provider for Tests

```python
class MockAnthropicProvider(AnthropicProvider):
    def _generate_impl(self, request):
        return ClientLLMResponse(
            content="SELECT * WHERE { ?s ?p ?o }",
            model=self.model,
            provider="anthropic",
            finish_reason="stop",
            usage=TokenUsage(100, 50, 150),
            metrics=GenerationMetrics(latency_ms=100, tokens_per_second=50),
        )

# Use in tests
provider = MockAnthropicProvider(model="claude-3-5-sonnet-20241022")
```

## Troubleshooting

### API Key Issues

```python
# Check if API key is set
import os
if not os.environ.get("ANTHROPIC_API_KEY"):
    raise ValueError("ANTHROPIC_API_KEY not set")

# Test connection
if provider.test_connection():
    print("Connection successful")
else:
    print("Connection failed")
```

### Rate Limiting

```python
# Anthropic rate limits (as of 2024):
# - Tier 1: 50 requests/min, 40,000 tokens/min
# - Tier 2: 1,000 requests/min, 80,000 tokens/min
# - Tier 3: 2,000 requests/min, 160,000 tokens/min

# Provider automatically handles rate limiting
# Adjust if needed:
provider._min_request_interval = 0.1  # 100ms between requests
```

### Timeout Issues

```python
# Increase timeout for complex queries
provider = AnthropicProvider(
    model="...",
    timeout=120.0,  # 2 minutes
)
```

## Examples

See `example_anthropic.py` for complete working examples including:
- Basic generation
- SPARQL query generation
- Streaming responses
- Tool calling
- Multi-model comparison
- Provider information

Run with:
```bash
python -m sparql_agent.llm.example_anthropic
```

## API Reference

### AnthropicProvider

```python
class AnthropicProvider(LLMClient):
    def __init__(
        self,
        model: str = "claude-3-5-sonnet-20241022",
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        timeout: float = 60.0,
        retry_config: Optional[RetryConfig] = None,
        default_max_tokens: int = 4096,
    )

    def get_provider(self) -> LLMProvider
    def get_capabilities(self) -> ModelCapabilities
    def generate(self, request: LLMRequest) -> LLMResponse
    def generate_streaming(self, request: LLMRequest) -> Iterator[StreamChunk]
    def count_tokens(self, text: str) -> int
    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float
    def get_metrics(self) -> Dict[str, Any]

    @staticmethod
    def list_available_models() -> List[str]

    @staticmethod
    def get_model_config(model: str) -> Dict[str, Any]
```

### Helper Functions

```python
def create_anthropic_provider(
    model: str = "claude-3-5-sonnet-20241022",
    api_key: Optional[str] = None,
    **kwargs
) -> AnthropicProvider
```

## Resources

- [Anthropic API Documentation](https://docs.anthropic.com/)
- [Claude Model Specifications](https://www.anthropic.com/api)
- [SPARQL 1.1 Specification](https://www.w3.org/TR/sparql11-query/)
- [Semantic Web Standards](https://www.w3.org/standards/semanticweb/)

## License

MIT License - See LICENSE file for details
