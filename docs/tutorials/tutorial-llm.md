# Tutorial: Natural Language to SPARQL with LLMs

Learn how to use Large Language Models to generate SPARQL queries from natural language.

## Prerequisites

```bash
uv add sparql-agent
export ANTHROPIC_API_KEY="your-key"  # or OPENAI_API_KEY
```

## Part 1: Basic LLM Query Generation

### Using Anthropic Claude

```python
from sparql_agent import SPARQLAgent

agent = SPARQLAgent(
    endpoint="https://sparql.uniprot.org/sparql",
    llm_provider="anthropic",
    api_key="your-api-key"  # or uses ANTHROPIC_API_KEY env var
)

# Natural language query
results = agent.query("Find all human proteins involved in DNA repair")

for result in results[:5]:
    print(result)
```

### Using OpenAI GPT

```python
agent = SPARQLAgent(
    endpoint="https://sparql.uniprot.org/sparql",
    llm_provider="openai",
    api_key="your-api-key"  # or uses OPENAI_API_KEY env var
)

results = agent.query("Show me proteins from mouse that are kinases")
```

### Local LLM Support

```python
agent = SPARQLAgent(
    endpoint="https://sparql.uniprot.org/sparql",
    llm_provider="local",
    llm_base_url="http://localhost:1234/v1",
    llm_model="local-model"
)

results = agent.query("Find proteins")
```

## Part 2: Query Generation Strategies

### Auto Strategy (Default)

```python
# Automatically chooses best strategy
results = agent.query("Find proteins", strategy="auto")
```

### Template Strategy

```python
# Uses predefined templates (fast, no LLM)
results = agent.query("Find proteins", strategy="template")
```

### LLM Strategy

```python
# Always uses LLM (flexible, slower)
results = agent.query(
    "Find all membrane proteins from human that interact with insulin receptor",
    strategy="llm"
)
```

### Hybrid Strategy

```python
# Combines templates and LLM
results = agent.query("Find proteins", strategy="hybrid")
```

## Part 3: Improving Query Quality

### Provide Context

```python
# Add schema context
from sparql_agent.discovery import SchemaInference

inference = SchemaInference("https://sparql.uniprot.org/sparql")
schema = inference.infer_schema()

agent = SPARQLAgent(
    endpoint="https://sparql.uniprot.org/sparql",
    llm_provider="anthropic",
    schema=schema  # Provides context to LLM
)

results = agent.query("Find proteins in the nucleus")
```

### Add Ontology Context

```python
# Use ontology for better term mapping
results = agent.query(
    "Find proteins with GO term DNA binding",
    ontology="go"
)
```

### Use Examples

```python
from sparql_agent.query import PromptEngine

engine = PromptEngine()

# Add example queries
engine.add_example(
    natural="Find proteins from human",
    sparql="""
    SELECT ?protein WHERE {
        ?protein a up:Protein ;
                 up:organism taxon:9606 .
    }
    """
)

# LLM learns from examples
agent = SPARQLAgent(
    endpoint="https://sparql.uniprot.org/sparql",
    llm_provider="anthropic",
    prompt_engine=engine
)

results = agent.query("Find proteins from mouse")
```

## Part 4: Complex Natural Language Queries

### Multi-Constraint Queries

```python
results = agent.query("""
    Find human proteins that:
    - Are membrane proteins
    - Have molecular weight greater than 50 kDa
    - Are involved in signal transduction
    - Have known disease associations
""")
```

### Aggregation Queries

```python
results = agent.query("""
    Count proteins by organism
    Show top 10 organisms
    Order by protein count descending
""")
```

### Relationship Queries

```python
results = agent.query("""
    Find proteins that interact with BRCA1
    Include the interaction type
    Show only experimentally verified interactions
""")
```

## Part 5: Query Refinement

### Iterative Refinement

```python
# First query
results1 = agent.query("Find cancer-related proteins")

# Refine based on results
results2 = agent.query("""
    From the previous results, show only proteins
    that are kinases and located in the nucleus
""")
```

### Error Correction

```python
from sparql_agent.query import QueryValidator

validator = QueryValidator()

query = "Find proteins from mars"  # Intentionally weird

# LLM generates query
sparql = agent.generate_query(query)

# Validate
is_valid, errors = validator.validate(sparql)

if not is_valid:
    # Ask LLM to fix
    fixed_sparql = agent.generate_query(
        query,
        previous_query=sparql,
        previous_errors=errors
    )
```

## Part 6: Prompt Engineering

### Custom System Prompts

```python
from sparql_agent.query import PromptEngine

engine = PromptEngine()

# Customize system prompt
engine.set_system_prompt("""
You are an expert in biomedical SPARQL queries.
Always include proper prefixes and use UniProt ontology.
Optimize queries for performance.
""")

agent = SPARQLAgent(
    endpoint="https://sparql.uniprot.org/sparql",
    llm_provider="anthropic",
    prompt_engine=engine
)
```

### Domain-Specific Prompts

```python
# Biomedical domain
biomedical_prompt = """
Focus on biomedical entities: proteins, genes, diseases, drugs.
Use standard biomedical ontologies: GO, MONDO, EFO, HP.
Include cross-references to standard databases.
"""

engine.set_domain_prompt(biomedical_prompt)
```

### Few-Shot Learning

```python
# Provide domain examples
examples = [
    {
        "natural": "Find proteins from human",
        "sparql": "SELECT ?p WHERE { ?p a up:Protein ; up:organism taxon:9606 }"
    },
    {
        "natural": "Count proteins by organism",
        "sparql": "SELECT ?org (COUNT(?p) as ?count) WHERE { ?p up:organism ?org } GROUP BY ?org"
    }
]

engine.set_examples(examples)
```

## Part 7: LLM Configuration

### Model Selection

```python
# Use different Claude models
agent = SPARQLAgent(
    llm_provider="anthropic",
    llm_model="claude-3-5-sonnet-20241022"  # Latest
)

# Or use GPT-4
agent = SPARQLAgent(
    llm_provider="openai",
    llm_model="gpt-4"
)
```

### Temperature Control

```python
# Lower temperature = more deterministic
agent = SPARQLAgent(
    llm_provider="anthropic",
    llm_temperature=0.0  # Most deterministic
)

# Higher temperature = more creative
agent = SPARQLAgent(
    llm_provider="anthropic",
    llm_temperature=0.7  # More varied
)
```

### Token Limits

```python
agent = SPARQLAgent(
    llm_provider="anthropic",
    llm_max_tokens=4096  # Maximum response length
)
```

## Part 8: Batch Processing with LLM

```python
# Process multiple natural language queries
queries = [
    "Find proteins involved in cancer",
    "What drugs target EGFR?",
    "Show pathways related to diabetes"
]

# Batch process
results = agent.query_batch(queries)

for query, result in zip(queries, results):
    print(f"\nQuery: {query}")
    print(f"Results: {len(result)}")
```

## Part 9: Cost Optimization

### Cache LLM Responses

```python
from sparql_agent.cache import QueryCache

cache = QueryCache(ttl=86400)  # 24 hours

agent = SPARQLAgent(
    llm_provider="anthropic",
    cache=cache
)

# First call - uses LLM
results1 = agent.query("Find proteins")  # Costs $

# Second call - uses cache
results2 = agent.query("Find proteins")  # Free!
```

### Use Templates When Possible

```python
# Simple queries don't need LLM
agent.query("Find proteins", strategy="template")  # Free

# Complex queries use LLM
agent.query(
    "Complex multi-constraint query...",
    strategy="llm"  # Costs $
)
```

### Fallback to Templates

```python
from sparql_agent import SPARQLAgent
from sparql_agent.core import LLMError

try:
    results = agent.query("Find proteins", strategy="llm")
except LLMError:
    # Fallback to template
    results = agent.query("Find proteins", strategy="template")
```

## Part 10: Advanced Techniques

### Chain of Thought

```python
engine = PromptEngine()
engine.enable_chain_of_thought()

# LLM explains reasoning
sparql, reasoning = agent.generate_query_with_reasoning(
    "Find membrane proteins involved in cancer"
)

print("Reasoning:", reasoning)
print("Query:", sparql)
```

### Query Explanation

```python
results = agent.query("Find proteins")

# Get explanation
explanation = agent.explain_last_query()
print(explanation)
```

### Self-Validation

```python
# LLM validates its own query
sparql = agent.generate_query("Find proteins")

# Ask LLM to validate
is_valid = agent.validate_query_with_llm(sparql)

if not is_valid:
    # Regenerate
    sparql = agent.generate_query("Find proteins", retry=True)
```

## Best Practices

1. **Cache Results**: Cache LLM-generated queries
2. **Provide Context**: Include schema and ontology information
3. **Use Examples**: Provide few-shot examples for better results
4. **Start Simple**: Test with simple queries first
5. **Monitor Costs**: Track API usage and costs
6. **Fallback Strategy**: Have template fallbacks for common queries
7. **Validate Output**: Always validate generated SPARQL

## Exercises

1. Generate SPARQL for 5 different natural language queries
2. Compare Claude vs GPT-4 for query generation quality
3. Create a custom prompt for your domain
4. Implement cost tracking for LLM API calls
5. Build a query refinement loop with user feedback

## Next Steps

- [Tutorial: Advanced Queries](tutorial-advanced.md)
- [Examples: Code Samples](../examples/code-samples.md)
- [Best Practices: Performance](../best-practices/performance.md)
