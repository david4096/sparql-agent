# Federated SPARQL Query System

Complete cross-dataset integration for biomedical research using federated SPARQL queries.

## Overview

The federated query system enables querying multiple SPARQL endpoints in a single query, combining data from heterogeneous sources like UniProt, PDB, Wikidata, ChEMBL, and others. This is essential for complex biomedical research questions that require integrating protein data, structures, disease information, chemical compounds, and more.

## Key Features

- **Federated Query Generation**: Build queries spanning multiple endpoints with SERVICE clauses
- **Query Optimization**: Minimize data transfer and optimize execution order
- **Error Handling**: Graceful degradation when endpoints fail
- **Result Merging**: Combine results from multiple queries
- **Real-World Examples**: Pre-built queries for common research scenarios
- **Performance Monitoring**: Track query costs and execution times

## Quick Start

```python
from sparql_agent.endpoints import (
    FederatedQueryBuilder,
    CrossDatasetExamples,
    BIOMEDICAL_ENDPOINTS
)

# Create builder
builder = FederatedQueryBuilder(enable_optimization=True)

# Use pre-built examples
examples = CrossDatasetExamples()
query = examples.protein_disease_associations("BRCA1", limit=20)

print(query)
```

## Architecture

### Components

1. **FederatedQueryBuilder**: Core query construction with SERVICE clauses
2. **CrossDatasetExamples**: Pre-built queries for common research scenarios
3. **ResultMerger**: Merge results from multiple queries
4. **ResilientFederatedExecutor**: Execute with error handling and retry logic
5. **QueryOptimizationHints**: Guide query optimization

### Supported Endpoints

The system includes pre-configured endpoints for:

| Endpoint | URL | Data Types | Best For |
|----------|-----|------------|----------|
| UniProt | https://sparql.uniprot.org/sparql | Proteins, genes, functions | Protein information |
| PDB | https://rdf.wwpdb.org/sparql | 3D structures | Structural biology |
| Wikidata | https://query.wikidata.org/sparql | General knowledge | Diseases, drugs |
| ChEMBL | https://www.ebi.ac.uk/rdf/services/chembl/sparql | Compounds, bioactivity | Drug discovery |
| DisGeNET | http://rdf.disgenet.org/sparql/ | Gene-disease associations | Disease genetics |

## Research Scenarios

### 1. Protein-Disease Associations

Find all diseases associated with a gene/protein.

```python
examples = CrossDatasetExamples()
query = examples.protein_disease_associations(
    gene_name="BRCA1",
    limit=20
)
```

**Integrates:**
- UniProt: Protein and disease annotations
- Wikidata: Additional disease context

**Use Cases:**
- Clinical genetics
- Disease mechanism research
- Biomarker discovery

### 2. Structure-Function Integration

Correlate protein domains with 3D structures.

```python
query = examples.protein_structure_function_integration(
    protein_id="P38398",  # BRCA1
    limit=10
)
```

**Integrates:**
- UniProt: Protein domains and functional annotations
- PDB: 3D structures and experimental details

**Use Cases:**
- Structural biology
- Drug design
- Structure-function analysis

### 3. Drug Target Discovery

Identify proteins that bind to a compound.

```python
query = examples.chemical_protein_interaction_network(
    compound_name="Imatinib",
    activity_threshold=100.0,  # nM
    limit=50
)
```

**Integrates:**
- ChEMBL: Compound bioactivity
- UniProt: Target information

**Use Cases:**
- Drug discovery
- Off-target effect prediction
- Polypharmacology

### 4. Precision Medicine Variants

Find genetic variants affecting drug metabolism.

```python
query = examples.precision_medicine_variant_drug_response(
    gene_symbol="CYP2D6",
    limit=30
)
```

**Integrates:**
- UniProt: Natural variants and effects

**Use Cases:**
- Pharmacogenomics
- Personalized medicine
- Clinical decision support

### 5. Systems Biology Pathways

Reconstruct biological pathways with all components.

```python
query = examples.systems_biology_pathway_integration(
    pathway_name="Apoptosis",
    organism="Homo sapiens",
    limit=100
)
```

**Integrates:**
- UniProt: Pathway annotations and interactions

**Use Cases:**
- Systems biology
- Network analysis
- Disease perturbation studies

## Advanced Usage

### Custom Federated Query

Build a custom federated query with optimization:

```python
from sparql_agent.endpoints import (
    FederatedQueryBuilder,
    QueryOptimizationHints,
    OptimizationStrategy
)

builder = FederatedQueryBuilder(enable_optimization=True)

# Define optimization hints
hints = QueryOptimizationHints(
    strategies=[
        OptimizationStrategy.MINIMIZE_TRANSFER,
        OptimizationStrategy.EARLY_FILTERING,
    ],
    estimated_selectivity={
        "https://sparql.uniprot.org/sparql": 0.1,  # Very selective
        "https://query.wikidata.org/sparql": 0.5,
    },
    use_optional_for={"https://query.wikidata.org/sparql"}
)

# Build query
query = builder.build_federated_query(
    select_vars=["?protein", "?name", "?disease"],
    services={
        "https://sparql.uniprot.org/sparql": [
            "?protein a up:Protein .",
            "?protein up:organism/up:taxon <http://purl.uniprot.org/taxonomy/9606> .",
            "?protein up:recommendedName/up:fullName ?name .",
        ],
        "https://query.wikidata.org/sparql": [
            "?disease wdt:P31 wd:Q12136 .",  # instance of disease
            "?disease rdfs:label ?diseaseLabel .",
        ]
    },
    optimization_hints=hints,
    limit=50
)
```

### Result Merging

Combine results from multiple queries:

```python
from sparql_agent.endpoints import ResultMerger

merger = ResultMerger()

# UNION merge (combine all)
merged = merger.merge_with_union([result1, result2], deduplicate=True)

# JOIN merge (combine on keys)
merged = merger.merge_with_join(
    [result1, result2],
    join_keys=["?protein"],
    join_type="inner"
)

# Handle missing optional data
merged = merger.handle_missing_optional_data(
    merged,
    optional_vars=["?pdbId"],
    default_value="N/A"
)
```

### Resilient Execution

Execute with error handling and fallback:

```python
from sparql_agent.endpoints import ResilientFederatedExecutor

executor = ResilientFederatedExecutor(
    max_retries=2,
    retry_delay=1.0,
    allow_partial_results=True
)

# Execute with fallback queries
result = executor.execute_with_fallback(
    primary_query,
    fallback_queries=[simpler_query]
)
```

## Query Optimization Best Practices

### 1. Minimize Data Transfer

Filter within each SERVICE clause before transferring data:

```sparql
SERVICE <endpoint> {
  ?s a :Class .
  FILTER(?s = <specific-uri>)  # Filter early
} LIMIT 100  # Limit results
```

### 2. Order Services by Selectivity

Execute most selective services first:

```python
hints = QueryOptimizationHints(
    estimated_selectivity={
        "endpoint1": 0.1,  # Very selective - execute first
        "endpoint2": 0.5,  # Less selective - execute second
    }
)
```

### 3. Use SERVICE SILENT for Non-Critical Data

Continue if optional endpoint fails:

```sparql
SERVICE SILENT <optional-endpoint> {
  ?s :enrichment ?data .
}
```

### 4. Leverage OPTIONAL Clauses Wisely

Place OPTIONAL blocks after required patterns:

```sparql
SERVICE <critical-endpoint> {
  ?s :required ?data .  # Required first
  OPTIONAL { ?s :optional ?extra . }  # Then optional
}
```

### 5. Use Specific Identifiers

Bind specific URIs when known:

```sparql
BIND(<http://purl.uniprot.org/uniprot/P38398> AS ?protein)
SERVICE <endpoint> { ?protein :data ?value }
```

### 6. Set Appropriate Timeouts

Federated queries need longer timeouts:

```python
builder = FederatedQueryBuilder(timeout=120)  # 2 minutes
```

## Performance Considerations

### Query Cost Estimation

Estimate query execution time:

```python
services = {
    "endpoint1": ["pattern1", "pattern2"],
    "endpoint2": ["pattern3"]
}

cost = builder.estimate_query_cost(services)
print(f"Estimated time: {cost['estimated_time_seconds']}s")
print(f"Complexity score: {cost['complexity_score']}/100")
print(f"Recommended timeout: {cost['recommended_timeout']}s")
```

### Typical Performance

| Query Type | Endpoints | Patterns | Est. Time | Complexity |
|------------|-----------|----------|-----------|------------|
| Simple | 1 | 3-5 | 2-5s | 20-30 |
| Moderate | 2 | 6-10 | 5-15s | 40-60 |
| Complex | 3+ | 10+ | 15-60s | 70-90 |

### Optimization Impact

| Strategy | Performance Gain |
|----------|------------------|
| Early filtering | 30-50% |
| Service ordering | 20-30% |
| Result limiting | 40-60% |
| Optional services | 10-20% |

## Error Handling

### Common Issues

1. **Endpoint Timeout**
   - Solution: Increase timeout, simplify query, add LIMIT
   - Mitigation: Use SERVICE SILENT, provide fallback

2. **Endpoint Unavailable**
   - Solution: Retry with exponential backoff
   - Mitigation: Use OPTIONAL, allow partial results

3. **Rate Limiting**
   - Solution: Reduce request frequency, batch queries
   - Mitigation: Implement client-side rate limiting

4. **Data Mismatch**
   - Solution: Validate result schema, handle missing fields
   - Mitigation: Use OPTIONAL, provide defaults

### Graceful Degradation

```python
# Query with multiple endpoints
SERVICE <critical-endpoint> { ... }      # Required
SERVICE SILENT <optional-endpoint> { ... }  # Optional - continues if fails

# Result handling
if result.row_count > 0:
    # Process partial results
    process(result)
else:
    # Fallback to alternative query
    result = execute_fallback()
```

## Testing

Run the test suite:

```bash
# All tests
pytest src/sparql_agent/endpoints/test_federated.py -v

# Specific test class
pytest src/sparql_agent/endpoints/test_federated.py::TestFederatedQueryBuilder -v

# With coverage
pytest src/sparql_agent/endpoints/test_federated.py --cov=sparql_agent.endpoints.federated
```

## Examples

Run example queries:

```bash
# All examples
python -m sparql_agent.endpoints.federated_examples

# Specific example
python -m sparql_agent.endpoints.federated_examples disease
python -m sparql_agent.endpoints.federated_examples structure
python -m sparql_agent.endpoints.federated_examples drug

# Show endpoint registry
python -m sparql_agent.endpoints.federated_examples endpoints
```

## API Reference

### FederatedQueryBuilder

**Constructor:**
```python
FederatedQueryBuilder(
    coordinator_endpoint: Optional[str] = None,
    enable_optimization: bool = True,
    cache_results: bool = True,
    timeout: int = 120
)
```

**Methods:**

- `build_service_clause()`: Build SERVICE clause
- `build_federated_query()`: Build complete federated query
- `estimate_query_cost()`: Estimate query execution cost
- `add_result_limit_per_service()`: Add limits to services

### CrossDatasetExamples

**Pre-built Queries:**

- `protein_disease_associations()`: Find disease associations
- `protein_structure_function_integration()`: Correlate structure and function
- `gene_ontology_protein_expression()`: GO terms and expression
- `taxonomic_phylogenetic_protein_families()`: Protein families across species
- `chemical_protein_interaction_network()`: Drug-target interactions
- `precision_medicine_variant_drug_response()`: Pharmacogenomic variants
- `systems_biology_pathway_integration()`: Pathway reconstruction

### ResultMerger

**Methods:**

- `merge_with_union()`: UNION merge (combine all)
- `merge_with_join()`: JOIN merge (combine on keys)
- `handle_missing_optional_data()`: Fill missing optional values

### ResilientFederatedExecutor

**Methods:**

- `execute_with_fallback()`: Execute with fallback queries
- `_try_execute()`: Execute with retry logic

## Contributing

### Adding New Endpoints

1. Add endpoint to `BIOMEDICAL_ENDPOINTS`:

```python
BIOMEDICAL_ENDPOINTS["new_endpoint"] = EndpointInfo(
    url="https://example.org/sparql",
    name="Example Endpoint",
    description="Description",
    timeout=60,
    metadata={
        "capabilities": EndpointCapabilities(...),
        "data_types": ["type1", "type2"],
    }
)
```

2. Add prefixes to `FEDERATED_PREFIXES`:

```python
FEDERATED_PREFIXES["ex"] = "http://example.org/ns#"
```

3. Create example query in `CrossDatasetExamples`:

```python
def example_new_integration(self, param: str) -> str:
    return get_federated_prefix_string() + f"""
    SELECT ... WHERE {{
        SERVICE <new-endpoint> {{ ... }}
    }}
    """
```

### Adding New Optimization Strategies

1. Add strategy to `OptimizationStrategy` enum
2. Implement in `FederatedQueryBuilder._optimize_service_order()`
3. Document performance impact
4. Add tests

## Troubleshooting

### Query Takes Too Long

**Problem:** Query exceeds timeout

**Solutions:**
1. Add `LIMIT` clauses
2. Filter early in each SERVICE
3. Use specific identifiers instead of broad searches
4. Check estimated cost and reduce complexity

### Endpoint Returns Empty Results

**Problem:** SERVICE returns no data

**Solutions:**
1. Test each SERVICE independently
2. Check endpoint availability
3. Verify data exists for query constraints
4. Review FILTER conditions

### Results Don't Match Expected Schema

**Problem:** Missing or unexpected fields

**Solutions:**
1. Use OPTIONAL for optional fields
2. Validate endpoint schema
3. Handle missing data with defaults
4. Check endpoint documentation

## References

### SPARQL 1.1 Federated Query

- Specification: https://www.w3.org/TR/sparql11-federated-query/
- Best practices: https://www.w3.org/wiki/SparqlEndpoints
- Performance guide: https://www.w3.org/2001/sw/wiki/SPARQL/Federation

### Biomedical Resources

- UniProt SPARQL: https://sparql.uniprot.org/
- PDB SPARQL: https://rdf.wwpdb.org/sparql
- Wikidata Query Service: https://query.wikidata.org/
- Bio2RDF: http://bio2rdf.org/
- EBI RDF Platform: https://www.ebi.ac.uk/rdf/

### Related Tools

- SPARQLWrapper: Python library for SPARQL queries
- RDFLib: Python library for RDF
- Apache Jena: Java framework for semantic web

## License

This module is part of the SPARQL-Agent project and is licensed under the same terms.

## Support

For issues, questions, or contributions:
- File an issue on the project repository
- Check the main documentation
- Review example queries for patterns

## Changelog

### Version 1.0.0 (2025-10-02)

Initial release with:
- FederatedQueryBuilder
- CrossDatasetExamples (7 scenarios)
- ResultMerger
- ResilientFederatedExecutor
- Query optimization
- Error handling
- Comprehensive documentation
- Test suite
- Example queries
