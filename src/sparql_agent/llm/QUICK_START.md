# OpenAI/Local Provider Quick Start

Get started with OpenAI, Ollama, or LM Studio in 5 minutes.

## Installation

```bash
# Install OpenAI library (required)
pip install openai>=1.0.0

# Optional: Install Ollama
# macOS/Linux: curl https://ollama.ai/install.sh | sh
# Or visit: https://ollama.ai
```

## Option 1: OpenAI (Cloud)

### Setup
```bash
export OPENAI_API_KEY="sk-..."
```

### Code
```python
from sparql_agent.llm import OpenAIProvider

provider = OpenAIProvider(model="gpt-4", temperature=0.1)

response = provider.generate(
    prompt="Generate SPARQL: Find all proteins",
    system_prompt="You are a SPARQL expert"
)

print(response.content)
print(f"Cost: ${response.cost:.4f}")
```

## Option 2: Ollama (Local/Free)

### Setup
```bash
# Start Ollama
ollama serve

# Pull a model (in another terminal)
ollama pull llama2
```

### Code
```python
from sparql_agent.llm import create_ollama_provider

provider = create_ollama_provider(model="llama2")

response = provider.generate(
    prompt="Generate SPARQL: Find all proteins",
    system_prompt="You are a SPARQL expert",
    temperature=0.1
)

print(response.content)
print(f"Cost: ${response.cost} (FREE!)")
```

## Option 3: LM Studio (Local/Free)

### Setup
1. Download LM Studio: https://lmstudio.ai
2. Load a model in the UI
3. Start local server (Settings → Local Server)

### Code
```python
from sparql_agent.llm import create_lmstudio_provider

provider = create_lmstudio_provider()

response = provider.generate(
    prompt="Generate SPARQL: Find all proteins"
)

print(response.content)
```

## Option 4: Custom Endpoint

```python
from sparql_agent.llm import create_custom_provider

provider = create_custom_provider(
    model="custom-model",
    api_base="http://your-server:8000/v1",
    api_key="optional-key"
)

response = provider.generate(prompt="Hello!")
print(response.content)
```

## Complete Example

```python
from sparql_agent.llm import OpenAIProvider, create_ollama_provider

def generate_sparql(question: str, use_local: bool = False):
    """Generate SPARQL query from natural language."""

    # Choose provider
    if use_local:
        provider = create_ollama_provider(model="llama2")
    else:
        provider = OpenAIProvider(model="gpt-4")

    # Generate query
    response = provider.generate(
        prompt=f"Generate SPARQL query: {question}",
        system_prompt="""You are a SPARQL expert.
        Generate valid SPARQL queries with proper prefixes.""",
        temperature=0.1,
        max_tokens=500
    )

    return response.content

# Usage
query = generate_sparql("Find all proteins that interact with TP53")
print(query)
```

## Next Steps

1. **Read the full guide**: `OPENAI_LOCAL_GUIDE.md`
2. **Try examples**: `openai_examples.py`
3. **Explore features**: Function calling, JSON schema, streaming
4. **Optimize**: Caching, fallbacks, cost management

## Troubleshooting

### OpenAI
```bash
# Check API key
echo $OPENAI_API_KEY

# Set API key
export OPENAI_API_KEY="sk-..."
```

### Ollama
```bash
# Check if running
curl http://localhost:11434/api/tags

# List models
ollama list

# Pull model
ollama pull llama2
```

### LM Studio
1. Open LM Studio
2. Load a model
3. Go to Settings → Local Server
4. Click "Start Server"

## Common Patterns

### Fallback Pattern
```python
from sparql_agent.llm import OpenAIProvider, create_ollama_provider

try:
    provider = OpenAIProvider(model="gpt-4")
    response = provider.generate(prompt)
except:
    provider = create_ollama_provider(model="llama2")
    response = provider.generate(prompt)
```

### Cost Optimization
```python
# Use GPT-3.5 for simple tasks
simple_provider = OpenAIProvider(model="gpt-3.5-turbo")

# Use GPT-4 only when needed
complex_provider = OpenAIProvider(model="gpt-4")
```

### Connection Testing
```python
provider = create_ollama_provider(model="llama2")

if not provider.test_connection():
    print("Error: Ollama not running!")
    exit(1)
```

## Support

- **Full Guide**: `OPENAI_LOCAL_GUIDE.md`
- **Examples**: `openai_examples.py`
- **OpenAI Docs**: https://platform.openai.com/docs
- **Ollama Docs**: https://ollama.ai
