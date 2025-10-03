# Tutorial: Federation & Cross-Dataset Queries

Learn how to query multiple SPARQL endpoints and integrate data from different sources.

## Introduction

Federation allows you to:
- Query multiple endpoints in one query
- Combine data from different knowledge graphs
- Perform cross-dataset analysis
- Build integrated knowledge systems

## Part 1: Basic Federation

### Simple Federated Query

```python
from sparql_agent import SPARQLAgent

agent = SPARQLAgent()

# Query combines UniProt and Wikidata
federated_query = """
PREFIX up: <http://purl.uniprot.org/core/>
PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>

SELECT ?protein ?name ?disease
WHERE {
    SERVICE <https://sparql.uniprot.org/sparql> {
        ?protein a up:Protein ;
                 rdfs:label ?name .
        FILTER(CONTAINS(?name, "BRCA1"))
    }

    SERVICE <https://query.wikidata.org/sparql> {
        ?disease wdt:P2293 ?geneId ;
                 rdfs:label ?diseaseName .
    }
}
LIMIT 10
"""

results = agent.execute_sparql(federated_query)
```

### Natural Language Federation

```python
agent = SPARQLAgent(llm_provider="anthropic")

# Agent automatically generates federated query
results = agent.query("""
    Find proteins from UniProt and their associated
    diseases from Wikidata for gene BRCA1
""")
```

## Part 2: Common Federation Patterns

### Pattern 1: Protein-Disease Links

```python
# Link UniProt proteins to diseases
query = """
SELECT ?protein ?proteinName ?disease ?diseaseName
WHERE {
    SERVICE <https://sparql.uniprot.org/sparql> {
        ?protein a up:Protein ;
                 rdfs:label ?proteinName ;
                 up:encodedBy ?gene .
    }

    SERVICE <https://query.wikidata.org/sparql> {
        ?disease wdt:P2293 ?gene ;
                 rdfs:label ?diseaseName .
        FILTER(LANG(?diseaseName) = "en")
    }
}
LIMIT 100
"""
```

### Pattern 2: Drug-Target Integration

```python
# Combine ChEMBL drugs with UniProt targets
query = """
SELECT ?drug ?drugName ?target ?targetName
WHERE {
    SERVICE <https://chembl.lbl.gov/sparql> {
        ?drug a :Drug ;
              rdfs:label ?drugName ;
              :targets ?target .
    }

    SERVICE <https://sparql.uniprot.org/sparql> {
        ?target a up:Protein ;
                rdfs:label ?targetName .
    }
}
LIMIT 100
"""
```

### Pattern 3: Pathway Integration

```python
# Combine Reactome pathways with UniProt proteins
query = """
SELECT ?pathway ?pathwayName ?protein ?proteinName
WHERE {
    SERVICE <https://reactome.org/ContentService/sparql> {
        ?pathway a :Pathway ;
                 rdfs:label ?pathwayName ;
                 :hasComponent ?protein .
    }

    SERVICE <https://sparql.uniprot.org/sparql> {
        ?protein a up:Protein ;
                 rdfs:label ?proteinName .
    }
}
"""
```

## Part 3: Multi-Endpoint Queries

### Query Multiple Endpoints

```python
from sparql_agent import SPARQLAgent

class FederatedAgent:
    def __init__(self):
        self.endpoints = {
            'uniprot': SPARQLAgent(endpoint="https://sparql.uniprot.org/sparql"),
            'wikidata': SPARQLAgent(endpoint="https://query.wikidata.org/sparql"),
            'dbpedia': SPARQLAgent(endpoint="https://dbpedia.org/sparql")
        }

    def query_all(self, query_template):
        results = {}
        for name, agent in self.endpoints.items():
            try:
                results[name] = agent.query(query_template)
            except Exception as e:
                print(f"Error querying {name}: {e}")
        return results

# Use federated agent
fed_agent = FederatedAgent()
all_results = fed_agent.query_all("Find information about insulin")

for endpoint, results in all_results.items():
    print(f"\n{endpoint}: {len(results)} results")
```

## Part 4: Data Integration

### Merge Results

```python
def merge_results(results1, results2, key_field):
    """Merge results from two endpoints"""
    merged = {}

    for r1 in results1:
        key = r1.get(key_field)
        if key:
            merged[key] = r1

    for r2 in results2:
        key = r2.get(key_field)
        if key and key in merged:
            merged[key].update(r2)

    return list(merged.values())

# Query two endpoints
uniprot_results = uniprot_agent.query("Find proteins for gene TP53")
wikidata_results = wikidata_agent.query("Find information about TP53")

# Merge results
combined = merge_results(uniprot_results, wikidata_results, 'gene')
```

### Cross-Reference Resolution

```python
from sparql_agent import SPARQLAgent

def resolve_cross_refs(entity_id, source='uniprot'):
    """Find entity in multiple databases"""
    agent = SPARQLAgent(endpoint="https://sparql.uniprot.org/sparql")

    query = f"""
    SELECT ?database ?id
    WHERE {{
        <{entity_id}> rdfs:seeAlso ?xref .
        ?xref up:database ?database ;
              up:id ?id .
    }}
    """

    return agent.execute_sparql(query)

# Get cross-references
xrefs = resolve_cross_refs("http://purl.uniprot.org/uniprot/P04637")
for xref in xrefs:
    print(f"{xref['database']}: {xref['id']}")
```

## Part 5: Performance Optimization

### Optimize Federation

```python
# Bad: Queries remote endpoint multiple times
query_bad = """
SELECT ?protein ?disease
WHERE {
    SERVICE <https://sparql.uniprot.org/sparql> {
        ?protein a up:Protein .
        ?protein rdfs:label ?name .  # Multiple SERVICE calls
    }
}
"""

# Good: Single SERVICE call
query_good = """
SELECT ?protein ?disease
WHERE {
    SERVICE <https://sparql.uniprot.org/sparql> {
        ?protein a up:Protein ;
                 rdfs:label ?name .
    }
}
"""
```

### Use BIND for Filtering

```python
query = """
SELECT ?protein ?info
WHERE {
    SERVICE <https://sparql.uniprot.org/sparql> {
        ?protein a up:Protein ;
                 rdfs:label ?name .
        FILTER(CONTAINS(?name, "kinase"))
    }
    BIND(?name AS ?info)
}
"""
```

### Parallel Queries

```python
from concurrent.futures import ThreadPoolExecutor

def query_endpoint(endpoint, query):
    agent = SPARQLAgent(endpoint=endpoint)
    return agent.query(query)

# Query endpoints in parallel
with ThreadPoolExecutor(max_workers=3) as executor:
    futures = {
        'uniprot': executor.submit(
            query_endpoint,
            "https://sparql.uniprot.org/sparql",
            "Find proteins"
        ),
        'wikidata': executor.submit(
            query_endpoint,
            "https://query.wikidata.org/sparql",
            "Find genes"
        )
    }

    results = {name: future.result() for name, future in futures.items()}
```

## Part 6: Real-World Examples

### Example 1: Comprehensive Protein Report

```python
def get_protein_report(protein_name):
    """Get comprehensive protein information from multiple sources"""

    # UniProt: Basic info
    uniprot = SPARQLAgent(endpoint="https://sparql.uniprot.org/sparql")
    basic_info = uniprot.query(f"Find protein {protein_name} with sequence and function")

    # Wikidata: Additional context
    wikidata = SPARQLAgent(endpoint="https://query.wikidata.org/sparql")
    wiki_info = wikidata.query(f"Find information about protein {protein_name}")

    # Combine results
    report = {
        'name': protein_name,
        'uniprot': basic_info[0] if basic_info else {},
        'wikidata': wiki_info[0] if wiki_info else {},
    }

    return report

report = get_protein_report("BRCA1")
print(report)
```

### Example 2: Drug Discovery Pipeline

```python
def find_drug_targets(disease_name):
    """Find potential drug targets for a disease"""

    # 1. Find disease in ontology
    ols = OLSClient()
    disease = ols.search(disease_name, ontology="mondo")[0]

    # 2. Find associated proteins from UniProt
    uniprot = SPARQLAgent(endpoint="https://sparql.uniprot.org/sparql")
    proteins = uniprot.query(f"Find proteins associated with disease {disease['iri']}")

    # 3. Find existing drugs from ChEMBL
    chembl = SPARQLAgent(endpoint="https://chembl.lbl.gov/sparql")
    drugs = chembl.query(f"Find drugs targeting these proteins")

    # 4. Combine results
    targets = {
        'disease': disease_name,
        'proteins': proteins,
        'existing_drugs': drugs
    }

    return targets
```

### Example 3: Knowledge Graph Integration

```python
class KnowledgeGraphIntegrator:
    def __init__(self):
        self.agents = {
            'uniprot': SPARQLAgent(endpoint="https://sparql.uniprot.org/sparql"),
            'wikidata': SPARQLAgent(endpoint="https://query.wikidata.org/sparql"),
            'dbpedia': SPARQLAgent(endpoint="https://dbpedia.org/sparql")
        }

    def integrate(self, entity, entity_type='protein'):
        """Integrate information about an entity from multiple sources"""
        results = {}

        for name, agent in self.agents.items():
            try:
                query = f"Find all information about {entity_type} {entity}"
                results[name] = agent.query(query)
            except Exception as e:
                print(f"Error with {name}: {e}")

        return self.merge_results(results)

    def merge_results(self, results):
        """Merge results from multiple sources"""
        merged = {}
        for source, data in results.items():
            for item in data:
                key = item.get('uri') or item.get('id')
                if key:
                    if key not in merged:
                        merged[key] = {'sources': []}
                    merged[key].update(item)
                    merged[key]['sources'].append(source)
        return merged

# Use integrator
integrator = KnowledgeGraphIntegrator()
integrated_data = integrator.integrate("BRCA1", "protein")
```

## Best Practices

1. **Minimize SERVICE Calls**: Group operations in single SERVICE block
2. **Filter Early**: Apply filters within SERVICE blocks
3. **Use OPTIONAL Carefully**: Optional federated queries can be slow
4. **Handle Timeouts**: Set appropriate timeouts for federated queries
5. **Cache Results**: Cache federated query results
6. **Parallel Processing**: Query independent endpoints in parallel

## Troubleshooting

### Timeout Issues

```python
# Increase timeout for federated queries
agent = SPARQLAgent(timeout=120)  # 2 minutes
```

### Endpoint Unavailable

```python
# Graceful fallback
try:
    results = agent.execute_sparql(federated_query)
except EndpointError:
    # Fall back to single endpoint
    results = single_endpoint_query()
```

## Exercises

1. Create a federated query combining UniProt and Wikidata
2. Build a function to query 3+ endpoints in parallel
3. Integrate protein data from multiple sources
4. Create a drug-target discovery pipeline
5. Build a knowledge graph visualizer with federated data

## Next Steps

- [Tutorial: LLM Integration](tutorial-llm.md)
- [Examples: Integration Examples](../examples/integrations.md)
- [Best Practices: Performance](../best-practices/performance.md)
