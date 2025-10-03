# OpenAI and Local LLM Provider Guide

Complete guide for using OpenAI, Ollama, LM Studio, and custom LLM providers with SPARQL Agent.

## Table of Contents

1. [OpenAI Setup](#openai-setup)
2. [Ollama Setup](#ollama-setup)
3. [LM Studio Setup](#lm-studio-setup)
4. [Custom Endpoints](#custom-endpoints)
5. [Configuration Examples](#configuration-examples)
6. [Feature Comparison](#feature-comparison)
7. [Best Practices](#best-practices)

---

## OpenAI Setup

### Installation

```bash
pip install openai>=1.0.0
```

### Configuration

#### Option 1: Environment Variable (Recommended)

```bash
export OPENAI_API_KEY="sk-..."
```

#### Option 2: Direct API Key

```python
from sparql_agent.llm import OpenAIProvider

provider = OpenAIProvider(
    model="gpt-4",
    api_key="sk-...",
    temperature=0.1
)
```

### Supported Models

| Model | Context | Best For | Cost (per 1K tokens) |
|-------|---------|----------|---------------------|
| gpt-4 | 8K | High accuracy | $0.03 input / $0.06 output |
| gpt-4-turbo | 128K | Long context | $0.01 input / $0.03 output |
| gpt-3.5-turbo | 4K | Speed/cost | $0.0005 input / $0.0015 output |

### Basic Usage

```python
from sparql_agent.llm import OpenAIProvider

# Initialize provider
provider = OpenAIProvider(
    model="gpt-4",
    temperature=0.1,
    max_tokens=2000
)

# Generate response
response = provider.generate(
    prompt="Generate SPARQL: Find all proteins",
    system_prompt="You are a SPARQL expert"
)

print(f"Response: {response.content}")
print(f"Cost: ${response.cost:.4f}")
print(f"Tokens: {response.tokens_used}")
```

### Advanced Features

#### Function Calling

```python
functions = [{
    "name": "generate_sparql",
    "description": "Generate SPARQL query",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "explanation": {"type": "string"}
        },
        "required": ["query"]
    }
}]

response = provider.generate(
    prompt="Find all diseases",
    functions=functions,
    function_call={"name": "generate_sparql"}
)
```

#### JSON Schema Validation

```python
schema = {
    "type": "object",
    "properties": {
        "classes": {"type": "array"},
        "properties": {"type": "array"}
    }
}

response = provider.generate_with_json_schema(
    prompt="Extract ontology terms",
    json_schema=schema
)
```

---

## Ollama Setup

### Installation

1. **Install Ollama:**
   - macOS/Linux: `curl https://ollama.ai/install.sh | sh`
   - Or download from: https://ollama.ai

2. **Start Ollama server:**
   ```bash
   ollama serve
   ```

3. **Pull a model:**
   ```bash
   ollama pull llama2
   ollama pull codellama
   ollama pull mistral
   ```

### Configuration

```python
from sparql_agent.llm import create_ollama_provider

# Default: localhost:11434
provider = create_ollama_provider(model="llama2")

# Custom host/port
provider = create_ollama_provider(
    model="llama2",
    host="192.168.1.100",
    port=11434,
    temperature=0.1
)
```

### Recommended Models

| Model | Size | Best For | Speed |
|-------|------|----------|-------|
| llama2 | 7B | General purpose | Fast |
| codellama | 7B-34B | Code generation | Fast-Medium |
| mistral | 7B | Reasoning | Fast |
| mixtral | 8x7B | Complex tasks | Slow |

### Usage Examples

#### Basic Generation

```python
provider = create_ollama_provider(model="llama2")

response = provider.generate(
    prompt="What is SPARQL?",
    temperature=0.1,
    max_tokens=500
)

print(response.content)
print(f"Latency: {response.latency:.2f}s")
print(f"Cost: ${response.cost} (FREE!)")
```

#### Custom Configuration

```python
from sparql_agent.llm import LocalProvider

provider = LocalProvider(
    model="llama2",
    api_base="http://localhost:11434/v1",
    temperature=0.2,
    max_tokens=2000,
    timeout=180,  # Longer timeout for local models
    context_length=8192
)
```

### Ollama Management

```bash
# List downloaded models
ollama list

# Pull new model
ollama pull codellama

# Remove model
ollama rm llama2

# Update model
ollama pull llama2

# Show model info
ollama show llama2
```

---

## LM Studio Setup

### Installation

1. **Download LM Studio:**
   - https://lmstudio.ai

2. **Load a Model:**
   - Open LM Studio
   - Browse and download a model (e.g., Llama 2, Mistral)
   - Load the model

3. **Enable Local Server:**
   - Go to Settings → Local Server
   - Start server (default port: 1234)

### Configuration

```python
from sparql_agent.llm import create_lmstudio_provider

# Default: localhost:1234
provider = create_lmstudio_provider(model="local-model")

# Custom configuration
provider = create_lmstudio_provider(
    model="local-model",
    host="localhost",
    port=1234,
    temperature=0.1
)
```

### Usage

```python
provider = create_lmstudio_provider()

# Test connection
if not provider.test_connection():
    print("Error: LM Studio not running!")
    exit(1)

# Generate response
response = provider.generate(
    prompt="Generate SPARQL query",
    max_tokens=1000
)

print(response.content)
```

### LM Studio Tips

- **GPU Acceleration**: Enable in settings for faster inference
- **Model Selection**: Choose models based on your RAM/VRAM
- **Context Length**: Adjust in UI before loading model
- **Temperature**: Control randomness (0.0 = deterministic)

---

## Custom Endpoints

### OpenAI-Compatible APIs

Any API that implements the OpenAI API specification:

- **vLLM**: High-performance inference server
- **FastChat**: Multi-model serving
- **Text Generation WebUI**: Popular UI with API
- **LocalAI**: Self-hosted alternative
- **Jan**: Privacy-focused local AI

### Configuration

```python
from sparql_agent.llm import create_custom_provider

provider = create_custom_provider(
    model="custom-model",
    api_base="http://your-server:8000/v1",
    api_key="optional-key",  # If required
    temperature=0.1,
    timeout=60
)
```

### Advanced Configuration

```python
from sparql_agent.llm import LocalProvider

provider = LocalProvider(
    model="custom-llama",
    api_base="https://api.example.com/v1",
    api_key="your-api-key",
    temperature=0.2,
    max_tokens=2000,
    top_p=0.95,
    timeout=90,
    max_retries=3,
    context_length=16384,
    verify_ssl=True  # For HTTPS endpoints
)
```

### With Authentication

```python
provider = LocalProvider(
    model="protected-model",
    api_base="https://secure-api.com/v1",
    api_key="Bearer your-token",
    verify_ssl=True,
    timeout=60
)
```

---

## Configuration Examples

### Environment-Based Configuration

```python
import os
from sparql_agent.llm import OpenAIProvider, create_ollama_provider

def get_provider():
    """Get provider based on environment."""
    provider_type = os.getenv("LLM_PROVIDER", "openai")

    if provider_type == "openai":
        return OpenAIProvider(
            model=os.getenv("OPENAI_MODEL", "gpt-4"),
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.1"))
        )

    elif provider_type == "ollama":
        return create_ollama_provider(
            model=os.getenv("OLLAMA_MODEL", "llama2"),
            host=os.getenv("OLLAMA_HOST", "localhost"),
            port=int(os.getenv("OLLAMA_PORT", "11434"))
        )

    else:
        raise ValueError(f"Unknown provider: {provider_type}")

# Usage
provider = get_provider()
```

### Fallback Pattern

```python
from sparql_agent.llm import OpenAIProvider, create_ollama_provider

class FallbackProvider:
    """Try OpenAI first, fall back to local."""

    def __init__(self):
        self.primary = OpenAIProvider(model="gpt-4")
        self.fallback = create_ollama_provider(model="llama2")

    def generate(self, prompt: str, **kwargs):
        try:
            return self.primary.generate(prompt, **kwargs)
        except Exception as e:
            print(f"Primary failed ({e}), using fallback...")
            return self.fallback.generate(prompt, **kwargs)

# Usage
provider = FallbackProvider()
response = provider.generate("What is SPARQL?")
```

### Multi-Provider Ensemble

```python
from sparql_agent.llm import OpenAIProvider, create_ollama_provider

def generate_with_voting(prompt: str) -> str:
    """Generate with multiple providers and vote."""
    providers = [
        OpenAIProvider(model="gpt-4"),
        OpenAIProvider(model="gpt-3.5-turbo"),
        create_ollama_provider(model="llama2"),
    ]

    responses = []
    for provider in providers:
        try:
            response = provider.generate(prompt, temperature=0.1)
            responses.append(response.content)
        except Exception as e:
            print(f"Provider {provider.model} failed: {e}")

    # Simple voting: return most common response
    from collections import Counter
    return Counter(responses).most_common(1)[0][0]
```

---

## Feature Comparison

| Feature | OpenAI | Ollama | LM Studio | Custom |
|---------|--------|--------|-----------|--------|
| **Cost** | Paid | Free | Free | Varies |
| **Privacy** | Cloud | Local | Local | Varies |
| **Speed** | Fast | Medium | Medium | Varies |
| **Quality** | Excellent | Good | Good | Varies |
| **Function Calling** | ✅ | ❌ | ❌ | Varies |
| **Streaming** | ✅ | ✅ | ✅ | ✅ |
| **Context Length** | Up to 128K | 2K-32K | Varies | Varies |
| **Setup Difficulty** | Easy | Easy | Easy | Medium |
| **Internet Required** | ✅ | ❌ | ❌ | Varies |

---

## Best Practices

### 1. Model Selection

**For Production:**
- Use OpenAI GPT-4 for best quality
- Use GPT-3.5-turbo for cost/speed balance

**For Development:**
- Use Ollama for offline development
- Use LM Studio for testing

**For Privacy:**
- Use Ollama or LM Studio
- Use self-hosted custom endpoint

### 2. Temperature Settings

```python
# Deterministic (SPARQL generation)
temperature=0.0  # or 0.1

# Balanced (explanations)
temperature=0.7

# Creative (alternatives)
temperature=1.0
```

### 3. Token Management

```python
provider = OpenAIProvider(model="gpt-4")

# Estimate tokens before calling
prompt_tokens = provider.count_tokens(prompt)
if prompt_tokens > 6000:
    print("Warning: Prompt too long!")

# Limit output tokens
response = provider.generate(
    prompt=prompt,
    max_tokens=500  # Limit response length
)
```

### 4. Error Handling

```python
from sparql_agent.core.exceptions import (
    LLMError,
    LLMAuthenticationError,
    LLMRateLimitError
)

try:
    response = provider.generate(prompt)
except LLMAuthenticationError:
    print("Invalid API key!")
except LLMRateLimitError:
    print("Rate limit exceeded, waiting...")
    time.sleep(60)
except LLMError as e:
    print(f"LLM error: {e}")
```

### 5. Connection Testing

```python
provider = create_ollama_provider(model="llama2")

if not provider.test_connection():
    print("Error: Cannot connect to Ollama")
    print("1. Check if Ollama is running: ollama serve")
    print("2. Check if model is available: ollama list")
    print("3. Pull model if needed: ollama pull llama2")
    exit(1)
```

### 6. Cost Optimization

```python
# Use cheaper model for simple tasks
simple_provider = OpenAIProvider(model="gpt-3.5-turbo")

# Use expensive model only for complex tasks
complex_provider = OpenAIProvider(model="gpt-4")

def smart_generate(prompt: str, complexity: str = "simple"):
    provider = complex_provider if complexity == "complex" else simple_provider
    return provider.generate(prompt)
```

### 7. Caching Results

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_generate(prompt: str) -> str:
    """Cache LLM responses to avoid redundant calls."""
    provider = OpenAIProvider(model="gpt-4")
    response = provider.generate(prompt, temperature=0.0)
    return response.content

# First call: hits API
result1 = cached_generate("What is SPARQL?")

# Second call: returns cached result
result2 = cached_generate("What is SPARQL?")
```

---

## Troubleshooting

### OpenAI Issues

**Authentication Failed:**
```bash
# Check API key
echo $OPENAI_API_KEY

# Set API key
export OPENAI_API_KEY="sk-..."
```

**Rate Limit Exceeded:**
```python
# Implement retry with backoff
import time

def generate_with_retry(provider, prompt, max_retries=3):
    for i in range(max_retries):
        try:
            return provider.generate(prompt)
        except LLMRateLimitError:
            if i < max_retries - 1:
                wait_time = 2 ** i
                print(f"Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
    raise Exception("Max retries exceeded")
```

### Ollama Issues

**Cannot Connect:**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve
```

**Model Not Found:**
```bash
# List available models
ollama list

# Pull missing model
ollama pull llama2
```

**Slow Performance:**
- Use smaller models (7B instead of 13B/70B)
- Reduce max_tokens
- Increase timeout value

### LM Studio Issues

**Connection Failed:**
1. Open LM Studio
2. Load a model
3. Go to Settings → Local Server
4. Click "Start Server"
5. Verify port (default: 1234)

**Model Not Loading:**
- Check available RAM/VRAM
- Try quantized models (Q4, Q5)
- Reduce context length

---

## Integration with SPARQL Agent

### Complete Example

```python
from sparql_agent.llm import create_ollama_provider
from sparql_agent.core.types import LLMResponse

# Initialize provider
provider = create_ollama_provider(model="llama2")

# Generate SPARQL query
response = provider.generate(
    prompt="Find all proteins that interact with TP53",
    system_prompt="""You are a SPARQL expert for biomedical data.
    Generate valid SPARQL queries using proper prefixes and syntax.""",
    temperature=0.1,
    max_tokens=500
)

print("Generated SPARQL:")
print(response.content)
print(f"\nLatency: {response.latency:.2f}s")
print(f"Cost: ${response.cost:.4f}")
```

---

## Additional Resources

- **OpenAI API Docs**: https://platform.openai.com/docs
- **Ollama**: https://ollama.ai
- **LM Studio**: https://lmstudio.ai
- **Model Comparison**: https://artificialanalysis.ai

---

## Support

For issues or questions:
1. Check this guide
2. Review examples in `openai_examples.py`
3. Check provider documentation
4. File an issue on GitHub
