# UniProt SPARQL Endpoint - Usage Examples

This document provides comprehensive examples of using the UniProt SPARQL endpoint configuration in the SPARQL Agent.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Basic Protein Queries](#basic-protein-queries)
3. [Sequence Analysis](#sequence-analysis)
4. [Functional Annotations](#functional-annotations)
5. [Disease Research](#disease-research)
6. [Taxonomy Queries](#taxonomy-queries)
7. [Cross-Database Integration](#cross-database-integration)
8. [Advanced Patterns](#advanced-patterns)
9. [Performance Optimization](#performance-optimization)
10. [Real-World Research Workflows](#real-world-research-workflows)

## Getting Started

```python
from sparql_agent.endpoints.uniprot import (
    UNIPROT_ENDPOINT,
    UniProtQueryHelper,
    UniProtExampleQueries,
    get_prefix_string,
)

# The endpoint is pre-configured and ready to use
print(UNIPROT_ENDPOINT.url)
# Output: https://sparql.uniprot.org/sparql
```

## Basic Protein Queries

### 1. Get Basic Information for a Specific Protein

```python
# Example: Get information about Amyloid-beta precursor protein (APP)
query = UniProtExampleQueries.get_protein_basic_info("P05067")

# The query retrieves:
# - Protein mnemonic (entry name)
# - Organism
# - Sequence length and mass
# - Recommended name
```

**Use Case:** Quick lookup of protein characteristics for literature review or experimental planning.

### 2. Search Proteins by Name

```python
# Find all proteins with "insulin" in their name
query = UniProtExampleQueries.search_proteins_by_name("insulin", limit=10)

# Results include:
# - UniProt accession
# - Protein mnemonic
# - Full protein name
# - Source organism
```

**Use Case:** Exploring protein families or finding orthologs across species.

### 3. Find Human Proteins by Gene Name

```python
# Get proteins encoded by the BRCA1 gene
query = UniProtExampleQueries.get_human_proteins_by_gene("BRCA1")

# Returns:
# - All protein isoforms
# - Gene names and synonyms
# - Protein names
```

**Use Case:** Clinical genetics research, variant interpretation.

## Sequence Analysis

### 4. Retrieve Protein Sequence

```python
# Get the amino acid sequence for a protein
query = UniProtExampleQueries.get_protein_sequence("P12345")

# Returns:
# - Complete amino acid sequence
# - Sequence length
# - Molecular mass
# - CRC64 checksum for verification
```

**Use Case:** Input for sequence alignment, structural modeling, or functional analysis.

### 5. Find Proteins by Mass Range

```python
# Find proteins between 50-60 kDa
query = UniProtExampleQueries.get_proteins_by_mass_range(
    min_mass=50000,
    max_mass=60000,
    limit=50
)
```

**Use Case:** Interpreting mass spectrometry results, identifying proteins in proteomics experiments.

### 6. Analyze Protein Domains

```python
# Get domain and region information
query = UniProtExampleQueries.get_protein_domains("P12345")

# Returns:
# - Domain types and names
# - Sequence positions (begin/end)
# - Domain descriptions
# - Ordered by position
```

**Use Case:** Understanding protein structure-function relationships, designing domain deletion constructs.

## Functional Annotations

### 7. Get Protein Function

```python
# Retrieve functional annotations
query = UniProtExampleQueries.get_protein_function("P12345")

# Returns:
# - Curated function annotations
# - Gene Ontology (GO) terms
# - GO labels and descriptions
```

**Use Case:** Hypothesis generation, pathway analysis, functional genomics.

### 8. Find Proteins by GO Term

```python
# Find all proteins with "protein binding" GO term
query = UniProtExampleQueries.get_proteins_by_go_term("GO:0005515", limit=50)

# Key GO terms:
# - GO:0005515: Protein binding
# - GO:0003824: Catalytic activity
# - GO:0005634: Nucleus
# - GO:0016020: Membrane
```

**Use Case:** Gene set enrichment analysis, systems biology, network analysis.

### 9. Find Proteins by Keyword

```python
# Find membrane proteins
query = UniProtExampleQueries.get_proteins_by_keyword("Membrane", limit=50)

# Common keywords:
# - "Signal" (signal peptides)
# - "Transmembrane" (membrane proteins)
# - "Glycoprotein" (glycosylated proteins)
# - "Kinase" (kinases)
# - "Receptor" (receptors)
```

**Use Case:** Targeted proteomics, drug target discovery.

### 10. Get Subcellular Location

```python
# Find where a protein is located in the cell
query = UniProtExampleQueries.get_protein_subcellular_location("P12345")

# Returns:
# - Cellular compartments
# - Membrane topology
# - Localization signals
```

**Use Case:** Cell biology experiments, protein trafficking studies.

## Disease Research

### 11. Get Disease Associations

```python
# Find diseases associated with a protein
query = UniProtExampleQueries.get_protein_disease_associations("P12345")

# Returns:
# - Disease names
# - Disease descriptions
# - Mutation information
# - Links to disease databases (OMIM, OrphaNet)
```

**Use Case:** Clinical genetics, precision medicine, drug target identification.

### 12. Find Proteins by Taxonomy (e.g., Human Proteins)

```python
# Get human proteins (NCBI taxonomy ID: 9606)
query = UniProtExampleQueries.get_proteins_by_taxonomy("9606", limit=100)

# Common taxonomy IDs:
# - 9606: Homo sapiens (Human)
# - 10090: Mus musculus (Mouse)
# - 7227: Drosophila melanogaster (Fruit fly)
# - 6239: Caenorhabditis elegans (Nematode)
# - 559292: Saccharomyces cerevisiae (Baker's yeast)
```

**Use Case:** Comparative genomics, model organism research.

## Cross-Database Integration

### 13. Get Cross-References

```python
# Get all cross-references for a protein
query = UniProtExampleQueries.get_protein_cross_references("P12345")

# Links to:
# - PDB (3D structures)
# - RefSeq (genomic sequences)
# - Ensembl (genome browser)
# - KEGG (pathways)
# - STRING (protein interactions)
# - DrugBank (drug targets)
```

**Use Case:** Integrating data from multiple databases, comprehensive protein characterization.

### 14. Find Proteins with PDB Structures

```python
# Get proteins that have 3D structures
query = UniProtExampleQueries.get_proteins_with_pdb_structure(limit=100)

# Returns:
# - Protein accession
# - PDB IDs
# - Protein names
```

**Use Case:** Structural biology, drug design, molecular modeling.

### 15. Get Enzymes by EC Number

```python
# Find alcohol dehydrogenases (EC 1.1.1.1)
query = UniProtExampleQueries.get_enzyme_by_ec_number("1.1.1.1")

# Common EC classes:
# - 1.-.-.-: Oxidoreductases
# - 2.-.-.-: Transferases
# - 3.-.-.-: Hydrolases
# - 4.-.-.-: Lyases
# - 5.-.-.-: Isomerases
# - 6.-.-.-: Ligases
```

**Use Case:** Enzyme engineering, metabolic pathway analysis.

## Advanced Patterns

### 16. Get Protein-Protein Interactions

```python
# Find interaction partners
query = UniProtExampleQueries.get_protein_interactions("P12345")

# Returns:
# - Interaction types
# - Interacting proteins
# - Interaction descriptions
```

**Use Case:** Protein network analysis, co-immunoprecipitation experiment design.

### 17. Get Taxonomy Lineage

```python
# Get the complete taxonomic lineage for humans
query = UniProtExampleQueries.get_taxonomy_lineage("9606")

# Returns complete path from species to root:
# Homo sapiens → Hominidae → Primates → Mammalia → Chordata → Eukaryota
```

**Use Case:** Phylogenetic analysis, evolutionary studies.

### 18. Count Proteins by Organism

```python
# Get protein counts for top organisms
query = UniProtExampleQueries.count_proteins_by_organism(limit=20)

# Useful for:
# - Understanding database composition
# - Selecting model organisms
# - Comparative proteomics
```

**Use Case:** Database statistics, research resource planning.

### 19. Get Protein Publications

```python
# Find publications about a protein
query = UniProtExampleQueries.get_protein_publications("P12345")

# Returns:
# - Publication titles
# - PubMed IDs
# - DOIs
```

**Use Case:** Literature review, citation discovery.

## Performance Optimization

### Best Practices for Fast Queries

```python
from sparql_agent.endpoints.uniprot import PERFORMANCE_TIPS

# Print all optimization tips
print(PERFORMANCE_TIPS)
```

**Key Tips:**

1. **Always use LIMIT** for exploratory queries
2. **Filter early** - apply taxonomy/organism filters first
3. **Use reviewed entries** - `?protein up:reviewed true` (SwissProt only)
4. **Avoid broad text searches** - combine REGEX with other filters
5. **Optimize OPTIONAL blocks** - place after required patterns

### Example of Well-Optimized Query

```sparql
PREFIX up: <http://purl.uniprot.org/core/>
PREFIX uptaxon: <http://purl.uniprot.org/taxonomy/>

SELECT ?protein ?name WHERE {
    # 1. Filter by organism FIRST (reduces search space)
    ?protein up:organism/up:taxon uptaxon:9606 .

    # 2. Get only reviewed entries (SwissProt)
    ?protein up:reviewed true .

    # 3. Then retrieve other properties
    ?protein a up:Protein ;
             up:recommendedName/up:fullName ?name .

    # 4. Apply text filter AFTER other constraints
    FILTER(CONTAINS(LCASE(?name), "kinase"))
}
LIMIT 100
```

## Real-World Research Workflows

### Workflow 1: Identifying Drug Targets

```python
# Step 1: Find human membrane proteins (potential drug targets)
query1 = UniProtExampleQueries.get_proteins_by_keyword("Transmembrane", limit=1000)

# Step 2: Filter for disease-associated proteins
query2 = UniProtExampleQueries.get_protein_disease_associations("PROTEIN_ID")

# Step 3: Check for known structures
query3 = UniProtExampleQueries.get_proteins_with_pdb_structure()

# Step 4: Get drug interactions from DrugBank
# Use cross-references to link to DrugBank
```

### Workflow 2: Comparative Proteomics

```python
# Step 1: Get all proteins for organism 1
query1 = UniProtExampleQueries.get_proteins_by_taxonomy("9606", limit=5000)

# Step 2: Get all proteins for organism 2
query2 = UniProtExampleQueries.get_proteins_by_taxonomy("10090", limit=5000)

# Step 3: Compare sequences using CRC64 checksums
# Step 4: Analyze functional annotations with GO terms
```

### Workflow 3: Pathway Analysis

```python
# Step 1: Get all proteins in a pathway (using keyword)
query1 = UniProtExampleQueries.get_proteins_by_keyword("Glycolysis", limit=100)

# Step 2: Get enzyme classifications
query2 = UniProtExampleQueries.get_enzyme_by_ec_number("EC_NUMBER")

# Step 3: Get interaction networks
query3 = UniProtExampleQueries.get_protein_interactions("PROTEIN_ID")

# Step 4: Cross-reference with KEGG pathways
```

### Workflow 4: Structural Biology

```python
# Step 1: Find proteins with PDB structures
query1 = UniProtExampleQueries.get_proteins_with_pdb_structure(limit=1000)

# Step 2: Get domain information
query2 = UniProtExampleQueries.get_protein_domains("PROTEIN_ID")

# Step 3: Get sequence for modeling
query3 = UniProtExampleQueries.get_protein_sequence("PROTEIN_ID")

# Step 4: Find similar proteins for comparison
# Use sequence similarity tools
```

### Workflow 5: Clinical Genetics

```python
# Step 1: Find protein by gene name
query1 = UniProtExampleQueries.get_human_proteins_by_gene("GENE_NAME")

# Step 2: Get disease associations
query2 = UniProtExampleQueries.get_protein_disease_associations("PROTEIN_ID")

# Step 3: Get protein function
query3 = UniProtExampleQueries.get_protein_function("PROTEIN_ID")

# Step 4: Cross-reference with OMIM
# Use cross-references for clinical data
```

## Using Helper Functions

```python
from sparql_agent.endpoints.uniprot import UniProtQueryHelper

helper = UniProtQueryHelper()

# Build custom queries with helper functions

# 1. Resolve identifiers
protein_uri = helper.resolve_protein_id("P12345")
taxon_uri = helper.resolve_taxon_id("9606")

# 2. Build query patterns
go_pattern = helper.build_go_term_pattern("GO:0005515")
tax_pattern = helper.build_taxonomy_hierarchy_pattern("9606")
keyword_pattern = helper.build_keyword_pattern("Kinase")
xref_pattern = helper.build_cross_reference_pattern("PDB", "1HHO")

# 3. Build filters
text_filter = helper.build_text_search_filter("insulin", "?name")
reviewed_filter = helper.build_reviewed_only_filter()

# 4. Combine into custom query
custom_query = get_prefix_string() + f"""
SELECT ?protein ?name WHERE {{
    # Use helper-generated patterns
    {tax_pattern}
    {reviewed_filter}
    {go_pattern}

    ?protein up:recommendedName/up:fullName ?name .
    {text_filter}
}}
LIMIT 100
"""
```

## Integration with SPARQL Agent

```python
from sparql_agent.core.client import SPARQLClient
from sparql_agent.endpoints.uniprot import UNIPROT_ENDPOINT, UniProtExampleQueries

# Create client
client = SPARQLClient(UNIPROT_ENDPOINT)

# Execute query
query = UniProtExampleQueries.get_human_proteins_by_gene("BRCA1")
result = client.execute_query(query)

# Process results
if result.is_success:
    for binding in result.bindings:
        protein = binding.get('protein')
        mnemonic = binding.get('mnemonic')
        name = binding.get('proteinName')
        print(f"{protein} ({mnemonic}): {name}")
else:
    print(f"Query failed: {result.error_message}")
```

## Resources

- **UniProt Website:** https://www.uniprot.org/
- **SPARQL Endpoint:** https://sparql.uniprot.org/sparql
- **Documentation:** https://www.uniprot.org/help/sparql
- **Example Queries:** https://sparql.uniprot.org/.well-known/sparql-examples/
- **VoID Description:** https://sparql.uniprot.org/.well-known/void

## Common Issues and Solutions

### Issue 1: Query Timeout

**Solution:** Add LIMIT clauses, filter by taxonomy early, use reviewed entries only.

```python
# Bad: No LIMIT, no filters
query = "SELECT * WHERE { ?s ?p ?o }"

# Good: Limited, filtered query
query = UniProtExampleQueries.get_proteins_by_taxonomy("9606", limit=100)
```

### Issue 2: Too Many Results

**Solution:** Use more specific filters, combine multiple constraints.

```python
helper = UniProtQueryHelper()

# Add multiple filters
query = get_prefix_string() + f"""
SELECT ?protein ?name WHERE {{
    ?protein up:organism/up:taxon <http://purl.uniprot.org/taxonomy/9606> .
    ?protein up:reviewed true .
    ?protein up:classifiedWith <http://purl.obolibrary.org/obo/GO_0005515> .
    ?protein up:recommendedName/up:fullName ?name .
    FILTER(CONTAINS(LCASE(?name), "kinase"))
}}
LIMIT 50
"""
```

### Issue 3: Missing Data

**Solution:** Use OPTIONAL blocks for non-essential data.

```python
query = get_prefix_string() + """
SELECT ?protein ?name ?pdbId WHERE {
    ?protein a up:Protein .
    ?protein up:mnemonic ?mnemonic .

    # Required data
    ?protein up:recommendedName/up:fullName ?name .

    # Optional data (might not exist for all proteins)
    OPTIONAL {
        ?protein rdfs:seeAlso ?xref .
        ?xref up:database <http://purl.uniprot.org/database/PDB> .
        ?xref up:id ?pdbId .
    }
}
LIMIT 100
"""
```

## Summary

The UniProt SPARQL endpoint configuration provides:

- ✅ **29 namespace prefixes** for comprehensive coverage
- ✅ **18 core classes** covering all major protein data types
- ✅ **38 protein properties** for detailed characterization
- ✅ **15 annotation types** for functional information
- ✅ **18 cross-reference databases** for data integration
- ✅ **19 example query methods** for common use cases
- ✅ **8 helper functions** for building custom queries
- ✅ **Performance optimization tips** for efficient queries
- ✅ **Real-world workflows** for research applications

This makes the UniProt endpoint ready for production use in protein research, drug discovery, clinical genetics, and systems biology applications.
