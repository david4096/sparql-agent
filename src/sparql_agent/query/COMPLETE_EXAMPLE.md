# Complete End-to-End Example

This document demonstrates a complete workflow using the prompt engineering and template system.

## Scenario: Life Sciences Research Query

**Goal**: Generate a SPARQL query to find human proteins associated with cancer-related genes.

## Step 1: Setup

```python
from sparql_agent.core.types import (
    SchemaInfo,
    OntologyInfo,
    OWLClass,
    OWLProperty,
    OWLPropertyType
)
from sparql_agent.schema.ontology_mapper import OntologyMapper
from sparql_agent.query import create_prompt_engine, QueryScenario
```

## Step 2: Prepare Schema Information

```python
# Create schema info (typically from SchemaInferenceEngine)
schema_info = SchemaInfo()

# Add discovered classes
schema_info.classes.update([
    "http://purl.uniprot.org/core/Protein",
    "http://purl.uniprot.org/core/Gene",
    "http://purl.uniprot.org/core/Taxon",
    "http://purl.obolibrary.org/obo/MONDO_0000001",  # Disease
    "http://purl.obolibrary.org/obo/GO_0003674",     # Molecular Function
])

# Add discovered properties
schema_info.properties.update([
    "http://purl.uniprot.org/core/organism",
    "http://purl.uniprot.org/core/encodedBy",
    "http://purl.uniprot.org/core/classifiedWith",
    "http://purl.obolibrary.org/obo/RO_0002200",     # has_phenotype
    "http://purl.obolibrary.org/obo/RO_0002205",     # has_variant
])

# Add namespaces
schema_info.namespaces = {
    "up": "http://purl.uniprot.org/core/",
    "taxon": "http://purl.uniprot.org/taxonomy/",
    "obo": "http://purl.obolibrary.org/obo/",
    "mondo": "http://purl.obolibrary.org/obo/MONDO_",
    "go": "http://purl.obolibrary.org/obo/GO_",
}

# Add instance counts
schema_info.class_counts = {
    "http://purl.uniprot.org/core/Protein": 542000,
    "http://purl.uniprot.org/core/Gene": 20000,
    "http://purl.uniprot.org/core/Taxon": 2500000,
    "http://purl.obolibrary.org/obo/MONDO_0000001": 23000,
    "http://purl.obolibrary.org/obo/GO_0003674": 45000,
}

# Add property usage counts
schema_info.property_counts = {
    "http://purl.uniprot.org/core/organism": 542000,
    "http://purl.uniprot.org/core/encodedBy": 450000,
    "http://purl.uniprot.org/core/classifiedWith": 1200000,
    "http://purl.obolibrary.org/obo/RO_0002200": 50000,
    "http://purl.obolibrary.org/obo/RO_0002205": 120000,
}

# Add property domains and ranges
schema_info.property_domains = {
    "http://purl.uniprot.org/core/organism": {
        "http://purl.uniprot.org/core/Protein"
    },
    "http://purl.uniprot.org/core/encodedBy": {
        "http://purl.uniprot.org/core/Protein"
    }
}

schema_info.property_ranges = {
    "http://purl.uniprot.org/core/organism": {
        "http://purl.uniprot.org/core/Taxon"
    },
    "http://purl.uniprot.org/core/encodedBy": {
        "http://purl.uniprot.org/core/Gene"
    }
}
```

## Step 3: Prepare Ontology Information

```python
# Create ontology info (typically from OWLParser or OLSClient)
ontology_info = OntologyInfo(
    uri="http://purl.uniprot.org/core/",
    title="UniProt Core Ontology",
    description="Ontology for protein sequences and functional annotation",
    version="2024.1"
)

# Add OWL Classes
protein_class = OWLClass(
    uri="http://purl.uniprot.org/core/Protein",
    label=["Protein"],
    comment=[
        "A biological macromolecule composed of one or more chains of amino acids "
        "in a specific order determined by the nucleotide sequence of nucleic acids."
    ],
    instances_count=542000,
    properties=[
        "http://purl.uniprot.org/core/organism",
        "http://purl.uniprot.org/core/encodedBy",
        "http://purl.uniprot.org/core/classifiedWith"
    ]
)

gene_class = OWLClass(
    uri="http://purl.uniprot.org/core/Gene",
    label=["Gene"],
    comment=[
        "A region of DNA that encodes a particular protein or functional RNA molecule."
    ],
    instances_count=20000,
    properties=[
        "http://www.w3.org/2000/01/rdf-schema#label",
        "http://purl.obolibrary.org/obo/RO_0002205"
    ]
)

taxon_class = OWLClass(
    uri="http://purl.uniprot.org/core/Taxon",
    label=["Taxon", "Organism"],
    comment=["A group of organisms at any hierarchical level (species, genus, etc.)"],
    instances_count=2500000,
    properties=["http://purl.uniprot.org/core/scientificName"]
)

disease_class = OWLClass(
    uri="http://purl.obolibrary.org/obo/MONDO_0000001",
    label=["Disease"],
    comment=["A disease is a disposition to undergo pathological processes."],
    instances_count=23000,
    subclass_of=["http://purl.obolibrary.org/obo/BFO_0000016"]
)

# Add classes to ontology
ontology_info.classes[protein_class.uri] = protein_class
ontology_info.classes[gene_class.uri] = gene_class
ontology_info.classes[taxon_class.uri] = taxon_class
ontology_info.classes[disease_class.uri] = disease_class

# Add OWL Properties
organism_prop = OWLProperty(
    uri="http://purl.uniprot.org/core/organism",
    label=["organism"],
    comment=["Links a protein to the organism it comes from"],
    property_type=OWLPropertyType.OBJECT_PROPERTY,
    domain=["http://purl.uniprot.org/core/Protein"],
    range=["http://purl.uniprot.org/core/Taxon"],
    usage_count=542000
)

encoded_by_prop = OWLProperty(
    uri="http://purl.uniprot.org/core/encodedBy",
    label=["encodedBy", "encoded by"],
    comment=["Links a protein to the gene that encodes it"],
    property_type=OWLPropertyType.OBJECT_PROPERTY,
    domain=["http://purl.uniprot.org/core/Protein"],
    range=["http://purl.uniprot.org/core/Gene"],
    is_functional=True,
    usage_count=450000
)

has_phenotype_prop = OWLProperty(
    uri="http://purl.obolibrary.org/obo/RO_0002200",
    label=["has_phenotype"],
    comment=["A relationship between a biological entity and a phenotypic trait"],
    property_type=OWLPropertyType.OBJECT_PROPERTY,
    domain=["http://purl.uniprot.org/core/Gene"],
    range=["http://purl.obolibrary.org/obo/MONDO_0000001"],
    usage_count=50000
)

# Add properties to ontology
ontology_info.properties[organism_prop.uri] = organism_prop
ontology_info.properties[encoded_by_prop.uri] = encoded_by_prop
ontology_info.properties[has_phenotype_prop.uri] = has_phenotype_prop

# Add namespace prefixes
ontology_info.namespaces = {
    "up": "http://purl.uniprot.org/core/",
    "taxon": "http://purl.uniprot.org/taxonomy/",
    "obo": "http://purl.obolibrary.org/obo/",
}
```

## Step 4: Create Prompt Engine

```python
# Create engine with ontology mapper
mapper = OntologyMapper()
engine = create_prompt_engine(ontology_mapper=mapper)

print(f"Engine created with {len(engine.examples_db)} scenario types")
print(f"Total examples loaded: {sum(len(exs) for exs in engine.examples_db.values())}")
```

**Output**:
```
Engine created with 10 scenario types
Total examples loaded: 6
```

## Step 5: Generate Prompt

```python
# User's natural language query
user_query = "Find human proteins associated with cancer-related genes"

# Generate prompt with full context
prompt = engine.generate_prompt(
    user_query=user_query,
    schema_info=schema_info,
    ontology_info=ontology_info,
    use_examples=True,
    max_examples=3,
    constraints={
        "LIMIT": 100,
        "timeout": "30 seconds",
        "distinct": "required"
    }
)

print("=" * 80)
print("GENERATED PROMPT")
print("=" * 80)
print(prompt)
```

## Step 6: Generated Prompt Output

```
================================================================================
GENERATED PROMPT
================================================================================
You are a SPARQL query generation expert. Generate a SPARQL query that performs complex joins across multiple datasets.

## Question
Find human proteins associated with cancer-related genes

## Available Ontologies
Ontology: UniProt Core Ontology
Description: Ontology for protein sequences and functional annotation

Key Classes:
  - Protein: A biological macromolecule composed of one or more chains of amino acids...
  - Gene: A region of DNA that encodes a particular protein or functional RNA molecule.
  - Taxon: A group of organisms at any hierarchical level (species, genus, etc.)
  - Disease: A disease is a disposition to undergo pathological processes.

Key Properties:
  - organism: Links a protein to the organism it comes from
  - encodedBy: Links a protein to the gene that encodes it
  - has_phenotype: A relationship between a biological entity and a phenotypic trait

## Schema Information
Most Common Classes:
  - http://purl.uniprot.org/core/Taxon (2,500,000 instances)
  - http://purl.uniprot.org/core/Protein (542,000 instances)
  - http://purl.obolibrary.org/obo/GO_0003674 (45,000 instances)
  - http://purl.obolibrary.org/obo/MONDO_0000001 (23,000 instances)
  - http://purl.uniprot.org/core/Gene (20,000 instances)

Most Common Properties:
  - http://purl.uniprot.org/core/classifiedWith (1,200,000 uses)
  - http://purl.uniprot.org/core/organism (542,000 uses)
  - http://purl.uniprot.org/core/encodedBy (450,000 uses)
  - http://purl.obolibrary.org/obo/RO_0002205 (120,000 uses)
  - http://purl.obolibrary.org/obo/RO_0002200 (50,000 uses)

Property Domains and Ranges (sample):
  - http://purl.uniprot.org/core/organism
    Domain: http://purl.uniprot.org/core/Protein
    Range: http://purl.uniprot.org/core/Taxon
  - http://purl.uniprot.org/core/encodedBy
    Domain: http://purl.uniprot.org/core/Protein
    Range: http://purl.uniprot.org/core/Gene

## Available Prefixes
PREFIX go: <http://purl.obolibrary.org/obo/GO_>
PREFIX mondo: <http://purl.obolibrary.org/obo/MONDO_>
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX taxon: <http://purl.uniprot.org/taxonomy/>
PREFIX up: <http://purl.uniprot.org/core/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

## Examples of Complex Joins
Example 1:
Question: Find genes associated with diseases and their functions
SPARQL:
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?gene ?geneName ?disease ?diseaseName ?function
WHERE {
  # Gene to disease association
  ?gene a obo:SO_0000704 ;
        rdfs:label ?geneName ;
        obo:RO_0002200 ?disease .

  # Disease information
  ?disease a obo:MONDO_0000001 ;
           rdfs:label ?diseaseName .

  # Gene function (optional)
  OPTIONAL {
    ?gene obo:RO_0000085 ?function .
  }
}
LIMIT 100

## Instructions for Complex Joins
1. Identify the entities and relationships to join
2. Use appropriate join patterns (INNER, LEFT OUTER via OPTIONAL)
3. Consider using SERVICE for federated queries if joining across endpoints
4. Use FILTER to constrain join conditions
5. Pay attention to performance with large joins
6. Consider using DISTINCT if duplicates are a concern
7. Use property paths for transitive relationships if needed

## Join Patterns to Consider
- Basic Triple Pattern Join: ?s p1 ?o1 . ?o1 p2 ?o2
- Optional Join: ?s p1 ?o1 . OPTIONAL { ?o1 p2 ?o2 }
- Federated Join: SERVICE <endpoint> { ?s p1 ?o1 } . ?o1 p2 ?o2
- Property Path: ?s p1/p2/p3 ?o  # transitive path

## Constraints
- LIMIT: 100
- timeout: 30 seconds
- distinct: required

## Generated SPARQL Query
Please provide the SPARQL query with complex joins:
```

## Step 7: Alternative - Auto-Detect Scenario

```python
# Let the engine detect the scenario automatically
prompt_auto = engine.generate_prompt(
    user_query=user_query,
    schema_info=schema_info,
    ontology_info=ontology_info,
    # scenario auto-detected as COMPLEX_JOIN
)

# Check detected scenario
detected = engine.detect_scenario(user_query)
print(f"Auto-detected scenario: {detected.value}")
# Output: Auto-detected scenario: complex_join
```

## Step 8: Generate Multiple Scenarios

```python
# Generate prompts for multiple scenarios to create candidate queries
scenarios = [
    QueryScenario.BASIC,
    QueryScenario.COMPLEX_JOIN,
    QueryScenario.AGGREGATION
]

multi_prompts = engine.generate_multi_scenario_prompts(
    user_query=user_query,
    schema_info=schema_info,
    ontology_info=ontology_info,
    scenarios=scenarios,
    use_examples=True,
    max_examples=2
)

for scenario, prompt in multi_prompts.items():
    print(f"\n{'='*80}")
    print(f"Scenario: {scenario.value.upper()}")
    print(f"{'='*80}")
    print(prompt[:500] + "...")
```

## Step 9: Send to LLM (Example with OpenAI)

```python
import openai

# Send prompt to LLM
response = openai.chat.completions.create(
    model="gpt-4",
    messages=[
        {
            "role": "system",
            "content": "You are a SPARQL query generation expert. Generate valid SPARQL 1.1 queries."
        },
        {
            "role": "user",
            "content": prompt
        }
    ],
    temperature=0.1,
    max_tokens=1000
)

generated_sparql = response.choices[0].message.content
print("\n" + "="*80)
print("LLM-GENERATED SPARQL QUERY")
print("="*80)
print(generated_sparql)
```

## Step 10: Expected LLM Output

```sparql
PREFIX up: <http://purl.uniprot.org/core/>
PREFIX taxon: <http://purl.uniprot.org/taxonomy/>
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

# Find human proteins associated with cancer-related genes
SELECT DISTINCT ?protein ?proteinName ?gene ?geneName ?disease ?diseaseName
WHERE {
  # Find proteins from human organism (taxon:9606)
  ?protein a up:Protein ;
           up:organism taxon:9606 ;
           rdfs:label ?proteinName ;
           up:encodedBy ?gene .

  # Gene information
  ?gene rdfs:label ?geneName ;
        obo:RO_0002200 ?disease .

  # Disease must be a subclass of cancer (MONDO_0004992)
  ?disease a obo:MONDO_0000001 ;
           rdfs:label ?diseaseName ;
           rdfs:subClassOf* mondo:0004992 .

  # Filter for cancer-related terms in disease name
  FILTER(CONTAINS(LCASE(?diseaseName), "cancer") ||
         CONTAINS(LCASE(?diseaseName), "carcinoma") ||
         CONTAINS(LCASE(?diseaseName), "tumor"))
}
LIMIT 100
```

## Benefits of This Approach

1. **Rich Context**: The prompt includes schema statistics, ontology structure, and examples
2. **Ontology-Guided**: Uses actual OWL classes and properties from the ontology
3. **Few-Shot Learning**: Includes relevant examples for the detected scenario
4. **Constraint-Aware**: Respects user-defined constraints (LIMIT, timeout, etc.)
5. **Scenario-Specific**: Uses templates tailored to the query type
6. **Namespace-Aware**: Automatically includes all relevant prefixes

## Comparison: Without Ontology vs. With Ontology

### Without Ontology Context
```
User: "Find human proteins associated with cancer-related genes"
→ Generic prompt without domain knowledge
→ LLM must guess URIs and relationships
→ Lower quality results
```

### With Ontology Context
```
User: "Find human proteins associated with cancer-related genes"
→ Prompt includes:
   • Protein class definition
   • Gene class definition
   • Disease class definition
   • organism property (links Protein → Taxon)
   • encodedBy property (links Protein → Gene)
   • has_phenotype property (links Gene → Disease)
→ LLM knows exact URIs and relationships
→ Higher quality, accurate results
```

## Summary

This complete example demonstrates:

1. ✅ Schema information preparation with realistic data
2. ✅ Ontology information with OWL classes and properties
3. ✅ Prompt engine creation and configuration
4. ✅ Automatic scenario detection
5. ✅ Prompt generation with full context
6. ✅ Multi-scenario generation for candidate queries
7. ✅ Integration with LLM (OpenAI)
8. ✅ Expected high-quality SPARQL output

The generated prompt provides the LLM with all the context needed to produce accurate, ontology-aware SPARQL queries.
