# UniProt SPARQL Endpoint - Quick Reference Card

## Import

```python
from sparql_agent.endpoints.uniprot import (
    UNIPROT_ENDPOINT,          # Endpoint configuration
    UNIPROT_PREFIXES,          # Namespace prefixes dictionary
    UniProtQueryHelper,        # Helper functions
    UniProtExampleQueries,     # Pre-built example queries
    get_prefix_string,         # Generate PREFIX declarations
)
```

## Endpoint Configuration

```python
UNIPROT_ENDPOINT.url                    # https://sparql.uniprot.org/sparql
UNIPROT_ENDPOINT.timeout                # 60 seconds
UNIPROT_ENDPOINT.rate_limit             # 5.0 requests/second
```

## Common Taxonomy IDs

| Organism | Taxonomy ID |
|----------|-------------|
| Human | 9606 |
| Mouse | 10090 |
| Rat | 10116 |
| Zebrafish | 7955 |
| Fruit fly | 7227 |
| C. elegans | 6239 |
| S. cerevisiae | 559292 |
| E. coli K-12 | 83333 |
| A. thaliana | 3702 |

## Common GO Terms

| GO Term | Description |
|---------|-------------|
| GO:0005515 | Protein binding |
| GO:0003824 | Catalytic activity |
| GO:0005634 | Nucleus |
| GO:0005737 | Cytoplasm |
| GO:0016020 | Membrane |
| GO:0005886 | Plasma membrane |
| GO:0006810 | Transport |
| GO:0006355 | Regulation of transcription |

## Common Keywords

| Keyword | Use Case |
|---------|----------|
| Signal | Signal peptides |
| Transmembrane | Membrane proteins |
| Glycoprotein | Glycosylated proteins |
| Kinase | Protein kinases |
| Receptor | Receptors |
| Membrane | All membrane-associated |
| Nucleus | Nuclear proteins |
| Secreted | Secreted proteins |

## Example Queries - Quick Access

### 1. Basic Protein Info
```python
UniProtExampleQueries.get_protein_basic_info("P05067")
```

### 2. Search by Name
```python
UniProtExampleQueries.search_proteins_by_name("insulin", limit=10)
```

### 3. Human Gene Lookup
```python
UniProtExampleQueries.get_human_proteins_by_gene("BRCA1")
```

### 4. Get Sequence
```python
UniProtExampleQueries.get_protein_sequence("P12345")
```

### 5. Protein Function
```python
UniProtExampleQueries.get_protein_function("P12345")
```

### 6. Disease Associations
```python
UniProtExampleQueries.get_protein_disease_associations("P12345")
```

### 7. Subcellular Location
```python
UniProtExampleQueries.get_protein_subcellular_location("P12345")
```

### 8. Protein Domains
```python
UniProtExampleQueries.get_protein_domains("P12345")
```

### 9. Cross-References
```python
UniProtExampleQueries.get_protein_cross_references("P12345")
```

### 10. By Taxonomy
```python
UniProtExampleQueries.get_proteins_by_taxonomy("9606", limit=100)
```

### 11. By GO Term
```python
UniProtExampleQueries.get_proteins_by_go_term("GO:0005515", limit=50)
```

### 12. By Keyword
```python
UniProtExampleQueries.get_proteins_by_keyword("Membrane", limit=50)
```

### 13. Enzyme by EC Number
```python
UniProtExampleQueries.get_enzyme_by_ec_number("1.1.1.1")
```

### 14. With PDB Structures
```python
UniProtExampleQueries.get_proteins_with_pdb_structure(limit=100)
```

### 15. Protein Interactions
```python
UniProtExampleQueries.get_protein_interactions("P12345")
```

### 16. By Mass Range
```python
UniProtExampleQueries.get_proteins_by_mass_range(50000, 60000, limit=50)
```

### 17. Taxonomy Lineage
```python
UniProtExampleQueries.get_taxonomy_lineage("9606")
```

### 18. Count by Organism
```python
UniProtExampleQueries.count_proteins_by_organism(limit=20)
```

### 19. Publications
```python
UniProtExampleQueries.get_protein_publications("P12345")
```

## Helper Functions

### Resolve IDs
```python
helper = UniProtQueryHelper()
helper.resolve_protein_id("P12345")           # → <http://purl.uniprot.org/uniprot/P12345>
helper.resolve_taxon_id("9606")               # → <http://purl.uniprot.org/taxonomy/9606>
```

### Build Patterns
```python
helper.build_text_search_filter("insulin", "?name")
helper.build_taxonomy_hierarchy_pattern("9606", "?protein")
helper.build_go_term_pattern("GO:0005515", "?protein")
helper.build_keyword_pattern("Kinase", "?protein")
helper.build_reviewed_only_filter()
helper.build_cross_reference_pattern("PDB", "1HHO", "?protein")
```

## Performance Tips (The Big 5)

### 1. Always Use LIMIT
```sparql
LIMIT 100  # Start small, increase as needed
```

### 2. Filter by Taxonomy Early
```sparql
?protein up:organism/up:taxon uptaxon:9606 .  # Put this FIRST
```

### 3. Use Reviewed Entries Only
```sparql
?protein up:reviewed true .  # SwissProt only (higher quality, faster)
```

### 4. Combine Filters
```sparql
# Bad: Just text search
FILTER(REGEX(?name, "kinase", "i"))

# Good: Text search + other filters
?protein up:organism/up:taxon uptaxon:9606 .
?protein up:reviewed true .
FILTER(REGEX(?name, "kinase", "i"))
```

### 5. Use BIND for Constants
```sparql
BIND(<http://purl.uniprot.org/uniprot/P12345> AS ?protein)
```

## Well-Optimized Query Template

```sparql
PREFIX up: <http://purl.uniprot.org/core/>
PREFIX uptaxon: <http://purl.uniprot.org/taxonomy/>

SELECT ?protein ?name WHERE {
    # 1. Filter by organism FIRST
    ?protein up:organism/up:taxon uptaxon:9606 .

    # 2. Get only reviewed entries
    ?protein up:reviewed true .

    # 3. Required patterns
    ?protein a up:Protein ;
             up:recommendedName/up:fullName ?name .

    # 4. Text filters LAST
    FILTER(CONTAINS(LCASE(?name), "kinase"))
}
LIMIT 100
```

## Common Prefixes

```sparql
PREFIX up: <http://purl.uniprot.org/core/>
PREFIX uniprotkb: <http://purl.uniprot.org/uniprot/>
PREFIX uptaxon: <http://purl.uniprot.org/taxonomy/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX go: <http://purl.obolibrary.org/obo/GO_>
```

## Key Properties Cheat Sheet

### Identity
- `up:mnemonic` - Entry name
- `up:recommendedName` - Recommended name
- `up:alternativeName` - Alternative names

### Sequence
- `up:sequence` - Sequence node
- `rdf:value` - Sequence string
- `up:length` - Length (amino acids)
- `up:mass` - Mass (Daltons)

### Classification
- `up:organism` - Source organism
- `up:encodedBy` - Gene
- `up:classifiedWith` - Keywords/GO terms
- `up:reviewed` - SwissProt vs TrEMBL

### Function
- `up:annotation` - Annotations
- `up:enzyme` - EC number
- `up:pathway` - Pathways

### Location
- `up:locatedIn` - Subcellular location
- `up:tissueSpecificity` - Tissue expression

### Disease
- `up:associatedWith` - Associated diseases

### Structure
- `up:domain` - Domains
- `up:structure` - 3D structures

### Cross-References
- `rdfs:seeAlso` - External database links
- `up:database` - Database type
- `up:id` - External ID

## External Database Names

- `PDB` - Protein Data Bank
- `RefSeq` - NCBI Reference Sequences
- `Ensembl` - Ensembl genome browser
- `KEGG` - KEGG pathways
- `InterPro` - Protein families/domains
- `Pfam` - Protein families
- `STRING` - Protein interactions
- `DrugBank` - Drug targets
- `OMIM` - Genetic disorders
- `OrphaNet` - Rare diseases

## Error Handling

### Query Timeout
- Add `LIMIT` clause
- Filter by taxonomy
- Use `up:reviewed true`

### Too Many Results
- Reduce `LIMIT`
- Add more filters
- Use reviewed entries only

### Missing Data
- Use `OPTIONAL` blocks
- Check if property exists for protein type
- Try alternative properties

### Slow Performance
- Filter early (taxonomy, reviewed status)
- Avoid broad text searches
- Minimize OPTIONAL blocks
- Use BIND for constants

## Quick Test

```python
# Verify installation
import sys
sys.path.insert(0, 'src')
from sparql_agent.endpoints.uniprot import *

print(f"✓ Endpoint: {UNIPROT_ENDPOINT.url}")
print(f"✓ Prefixes: {len(UNIPROT_PREFIXES)}")
print(f"✓ Example queries: {len([m for m in dir(UniProtExampleQueries) if not m.startswith('_')])}")
```

## Resources

- **SPARQL Endpoint:** https://sparql.uniprot.org/sparql
- **Documentation:** https://www.uniprot.org/help/sparql
- **Examples:** https://sparql.uniprot.org/.well-known/sparql-examples/

---

**Pro Tip:** Start with example queries and modify them incrementally. Always test with small LIMIT values first!
