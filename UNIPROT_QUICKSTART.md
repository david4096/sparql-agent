# UniProt SPARQL Endpoint - Quick Start Guide

Get started with the UniProt SPARQL endpoint in 5 minutes!

## Installation Check

```python
import sys
sys.path.insert(0, 'src')

# Verify the module loads
from sparql_agent.endpoints.uniprot import (
    UNIPROT_ENDPOINT,
    UniProtExampleQueries,
)

print(f"✓ Connected to: {UNIPROT_ENDPOINT.url}")
```

## Example 1: Find a Protein by ID (30 seconds)

```python
from sparql_agent.endpoints.uniprot import UniProtExampleQueries

# Get basic info for human BRCA1 protein
query = UniProtExampleQueries.get_protein_basic_info("P38398")
print(query)

# Execute with SPARQLClient:
# from sparql_agent.core.client import SPARQLClient
# client = SPARQLClient(UNIPROT_ENDPOINT)
# result = client.execute_query(query)
```

**What you get:**
- Protein name
- Organism
- Sequence length and mass

## Example 2: Search by Gene Name (1 minute)

```python
# Find all human proteins for the TP53 gene
query = UniProtExampleQueries.get_human_proteins_by_gene("TP53")
```

**Use case:** Clinical genetics, variant interpretation

## Example 3: Find Disease-Associated Proteins (2 minutes)

```python
# Step 1: Find protein
query1 = UniProtExampleQueries.get_human_proteins_by_gene("BRCA1")

# Step 2: Get disease associations (using P38398)
query2 = UniProtExampleQueries.get_protein_disease_associations("P38398")

# Step 3: Get function
query3 = UniProtExampleQueries.get_protein_function("P38398")
```

**Use case:** Understanding disease mechanisms, drug target identification

## Example 4: Find Proteins with 3D Structures (1 minute)

```python
# Get proteins that have PDB structures
query = UniProtExampleQueries.get_proteins_with_pdb_structure(limit=20)
```

**Use case:** Structural biology, drug design

## Example 5: Build Custom Query (3 minutes)

```python
from sparql_agent.endpoints.uniprot import (
    UniProtQueryHelper,
    get_prefix_string,
)

helper = UniProtQueryHelper()

# Build a query for human membrane kinases
query = get_prefix_string() + f"""
SELECT ?protein ?name WHERE {{
    # Filter for human proteins
    ?protein up:organism/up:taxon <http://purl.uniprot.org/taxonomy/9606> .

    # Reviewed entries only (faster!)
    ?protein up:reviewed true .

    # Get name
    ?protein up:recommendedName/up:fullName ?name .

    # Filter for kinases
    FILTER(CONTAINS(LCASE(?name), "kinase"))
}}
LIMIT 50
"""
```

**Pro tip:** Always filter by taxonomy and reviewed status first!

## Common Use Cases - One-Liners

```python
# Get protein sequence
UniProtExampleQueries.get_protein_sequence("P12345")

# Find proteins by GO term (protein binding)
UniProtExampleQueries.get_proteins_by_go_term("GO:0005515", limit=50)

# Find proteins by keyword (membrane proteins)
UniProtExampleQueries.get_proteins_by_keyword("Membrane", limit=50)

# Find enzymes by EC number (alcohol dehydrogenase)
UniProtExampleQueries.get_enzyme_by_ec_number("1.1.1.1")

# Get protein domains
UniProtExampleQueries.get_protein_domains("P12345")

# Get cross-references (links to other databases)
UniProtExampleQueries.get_protein_cross_references("P12345")

# Get subcellular location
UniProtExampleQueries.get_protein_subcellular_location("P12345")

# Find proteins by mass range (50-60 kDa)
UniProtExampleQueries.get_proteins_by_mass_range(50000, 60000, limit=50)
```

## Performance Tips (The Golden Rules)

### 1. Always Use LIMIT
```python
LIMIT 100  # Start small!
```

### 2. Filter by Organism First
```python
?protein up:organism/up:taxon <http://purl.uniprot.org/taxonomy/9606> .  # Human
```

### 3. Use Reviewed Entries Only
```python
?protein up:reviewed true .  # SwissProt only (much faster)
```

### 4. Common Taxonomy IDs
```python
Human: 9606
Mouse: 10090
Fruit fly: 7227
C. elegans: 6239
Yeast: 559292
```

## Next Steps

### Read More Documentation
- **Quick Reference:** `UNIPROT_QUICK_REFERENCE.md` - One-page cheat sheet
- **Usage Examples:** `UNIPROT_USAGE_EXAMPLES.md` - Comprehensive guide
- **Implementation:** `UNIPROT_IMPLEMENTATION_SUMMARY.md` - Technical details

### Run Tests
```bash
python3 test_uniprot_endpoint.py
```

### Try Examples
```bash
python3 example_uniprot_usage.py
```

## Getting Help

### Check Available Methods
```python
from sparql_agent.endpoints.uniprot import UniProtExampleQueries

# List all example query methods
methods = [m for m in dir(UniProtExampleQueries) if not m.startswith('_')]
for method in methods:
    print(method)
```

### Use Helper Functions
```python
from sparql_agent.endpoints.uniprot import UniProtQueryHelper

helper = UniProtQueryHelper()

# Resolve IDs
helper.resolve_protein_id("P12345")
helper.resolve_taxon_id("9606")

# Build patterns
helper.build_go_term_pattern("GO:0005515")
helper.build_keyword_pattern("Kinase")
```

## Common Patterns

### Pattern 1: Protein Lookup
```python
# By ID
UniProtExampleQueries.get_protein_basic_info("P38398")

# By gene name
UniProtExampleQueries.get_human_proteins_by_gene("BRCA1")

# By name search
UniProtExampleQueries.search_proteins_by_name("insulin", limit=10)
```

### Pattern 2: Functional Analysis
```python
# Function
UniProtExampleQueries.get_protein_function("P38398")

# GO terms
UniProtExampleQueries.get_proteins_by_go_term("GO:0005515", limit=50)

# Pathways and interactions
UniProtExampleQueries.get_protein_interactions("P38398")
```

### Pattern 3: Structural Analysis
```python
# Domains
UniProtExampleQueries.get_protein_domains("P38398")

# PDB structures
UniProtExampleQueries.get_proteins_with_pdb_structure(limit=20)

# Sequence
UniProtExampleQueries.get_protein_sequence("P38398")
```

### Pattern 4: Disease Research
```python
# Disease associations
UniProtExampleQueries.get_protein_disease_associations("P38398")

# Cross-references (OMIM, etc.)
UniProtExampleQueries.get_protein_cross_references("P38398")
```

## Troubleshooting

### Query Times Out
**Solution:** Add more filters, use LIMIT, filter by taxonomy

### Too Many Results
**Solution:** Reduce LIMIT, add more specific filters

### No Results
**Solution:** Check protein ID is correct, try without OPTIONAL blocks

### Slow Performance
**Solution:** Apply the Golden Rules (see above)

## Resources

- **Endpoint:** https://sparql.uniprot.org/sparql
- **Documentation:** https://www.uniprot.org/help/sparql
- **Examples:** https://sparql.uniprot.org/.well-known/sparql-examples/

## Summary

You now know how to:
- ✅ Import the UniProt endpoint
- ✅ Use 19 pre-built example queries
- ✅ Build custom queries with helpers
- ✅ Optimize query performance
- ✅ Troubleshoot common issues

**Next:** Try running the examples and explore the full documentation!

---

**Happy querying!** 🧬
