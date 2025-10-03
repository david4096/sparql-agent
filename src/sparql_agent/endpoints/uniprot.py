"""
UniProt SPARQL Endpoint Configuration and Utilities.

This module provides comprehensive support for querying the UniProt SPARQL endpoint,
including endpoint configuration, common prefixes, schema information, helper functions,
and example queries for protein data retrieval and analysis.

UniProt (Universal Protein Resource) is the world's most comprehensive catalog of
protein sequence and functional information. The SPARQL endpoint provides access to:
- Protein sequences and structures
- Functional annotations
- Taxonomic information
- Gene ontology terms
- Cross-references to other databases
- Publications and citations

Official Documentation: https://sparql.uniprot.org/
SPARQL Editor: https://sparql.uniprot.org/sparql
API Documentation: https://www.uniprot.org/help/api_queries
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from ..core.types import EndpointInfo, SchemaInfo


# =============================================================================
# ENDPOINT CONFIGURATION
# =============================================================================

UNIPROT_ENDPOINT = EndpointInfo(
    url="https://sparql.uniprot.org/sparql",
    name="UniProt SPARQL Endpoint",
    description=(
        "The UniProt SPARQL endpoint provides programmatic access to UniProt protein "
        "data using the SPARQL query language. It includes comprehensive protein sequence, "
        "function, taxonomy, and cross-reference information."
    ),
    graph_uri=None,  # Uses default graph
    supports_update=False,
    timeout=60,  # UniProt queries can be complex
    rate_limit=5.0,  # Be respectful of the public service
    authentication_required=False,
    version="1.1",
    metadata={
        "provider": "European Bioinformatics Institute (EBI) and Swiss Institute of Bioinformatics (SIB)",
        "license": "Creative Commons Attribution 4.0 International (CC BY 4.0)",
        "data_version": "UniProtKB",
        "update_frequency": "Every 8 weeks (following UniProt releases)",
        "documentation": "https://www.uniprot.org/help/sparql",
        "examples": "https://sparql.uniprot.org/.well-known/sparql-examples/",
        "void_description": "https://sparql.uniprot.org/.well-known/void",
        "data_size": "~250 million proteins (SwissProt + TrEMBL)",
        "performance_tips": [
            "Use LIMIT clauses for exploratory queries",
            "Filter by taxonomy early in queries",
            "Use specific UniProt accessions when known",
            "Avoid broad text searches without filters",
            "Use federated queries carefully (can be slow)"
        ]
    }
)


# =============================================================================
# COMMON PREFIXES AND NAMESPACES
# =============================================================================

UNIPROT_PREFIXES = {
    # Core UniProt namespaces
    "up": "http://purl.uniprot.org/core/",
    "uniprotkb": "http://purl.uniprot.org/uniprot/",
    "uptaxon": "http://purl.uniprot.org/taxonomy/",
    "updb": "http://purl.uniprot.org/database/",
    "upkw": "http://purl.uniprot.org/keywords/",
    "upcit": "http://purl.uniprot.org/citations/",
    "uploc": "http://purl.uniprot.org/locations/",
    "upfam": "http://purl.uniprot.org/pfam/",
    "upenzyme": "http://purl.uniprot.org/enzyme/",
    "updis": "http://purl.uniprot.org/diseases/",

    # Standard ontology namespaces
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "dc": "http://purl.org/dc/terms/",
    "dcterms": "http://purl.org/dc/terms/",
    "foaf": "http://xmlns.com/foaf/0.1/",

    # External biological databases
    "obo": "http://purl.obolibrary.org/obo/",
    "go": "http://purl.obolibrary.org/obo/GO_",
    "eco": "http://purl.obolibrary.org/obo/ECO_",
    "so": "http://purl.obolibrary.org/obo/SO_",

    # Protein/sequence specific
    "faldo": "http://biohackathon.org/resource/faldo#",
    "bibo": "http://purl.org/ontology/bibo/",
    "pav": "http://purl.org/pav/",

    # External cross-references
    "ensembl": "http://identifiers.org/ensembl/",
    "refseq": "http://identifiers.org/refseq/",
    "pdb": "http://identifiers.org/pdb/",
    "interpro": "http://identifiers.org/interpro/",
}


def get_prefix_string() -> str:
    """
    Generate SPARQL PREFIX declarations for UniProt queries.

    Returns:
        String containing all PREFIX declarations

    Example:
        >>> prefixes = get_prefix_string()
        >>> query = prefixes + '''
        ... SELECT ?protein WHERE {
        ...     ?protein a up:Protein .
        ... } LIMIT 10
        ... '''
    """
    return "\n".join(
        f"PREFIX {prefix}: <{uri}>"
        for prefix, uri in UNIPROT_PREFIXES.items()
    ) + "\n\n"


# =============================================================================
# SCHEMA INFORMATION
# =============================================================================

@dataclass
class UniProtSchema:
    """
    Schema information for the UniProt SPARQL endpoint.

    This class provides comprehensive information about the UniProt data model,
    including core classes, properties, and their relationships.
    """

    # Core UniProt classes
    CORE_CLASSES = {
        "up:Protein": "A protein entity",
        "up:Taxon": "A taxonomic classification",
        "up:Organism": "An organism",
        "up:Gene": "A gene encoding a protein",
        "up:Proteome": "A complete set of proteins in an organism",
        "up:Annotation": "An annotation describing protein features",
        "up:Disease": "A disease associated with a protein",
        "up:Pathway": "A biological pathway",
        "up:Enzyme": "An enzyme with catalytic activity",
        "up:Sequence": "A protein sequence",
        "up:Structure": "A 3D protein structure",
        "up:Citation": "A scientific publication",
        "up:Database": "An external database reference",
        "up:Subcellular_Location": "A cellular compartment",
        "up:Tissue": "A tissue type where protein is expressed",
        "up:Domain": "A protein domain or region",
        "up:Family": "A protein family",
        "up:Keyword": "A controlled vocabulary keyword",
    }

    # Key properties for protein information
    PROTEIN_PROPERTIES = {
        # Identity and naming
        "up:mnemonic": "UniProt mnemonic (entry name)",
        "up:recommendedName": "Recommended protein name",
        "up:alternativeName": "Alternative protein names",
        "up:submittedName": "Submitted protein name",
        "up:alias": "Protein name alias",

        # Sequence information
        "up:sequence": "Links to sequence information",
        "up:sequenceFor": "Inverse of sequence",
        "rdf:value": "Sequence string value",
        "up:mass": "Molecular mass in Daltons",
        "up:length": "Sequence length in amino acids",
        "up:crc64": "CRC64 checksum",
        "up:md5": "MD5 checksum",

        # Classification and organization
        "up:organism": "Source organism",
        "up:proteome": "Proteome membership",
        "up:encodedBy": "Gene encoding the protein",
        "up:annotation": "Annotations (function, disease, etc.)",
        "up:classifiedWith": "Classification keywords",

        # Function and activity
        "up:enzyme": "Enzyme classification",
        "up:activity": "Catalytic activity",
        "up:catalyticActivity": "Detailed catalytic activity",
        "up:cofactor": "Required cofactors",
        "up:pathway": "Biological pathways",

        # Location and expression
        "up:locatedIn": "Subcellular location",
        "up:tissueSpecificity": "Tissue specificity",
        "up:developmentalStage": "Developmental stage expression",

        # Disease and phenotype
        "up:associatedWith": "Associated diseases",
        "up:causedBy": "Causal mutations",

        # Structure and domains
        "up:domain": "Protein domains",
        "up:region": "Sequence regions",
        "up:site": "Important sites",
        "up:structure": "3D structures",

        # Cross-references
        "rdfs:seeAlso": "Cross-references to other databases",
        "up:database": "External database links",

        # Evidence and provenance
        "up:reviewed": "Review status (SwissProt vs TrEMBL)",
        "up:created": "Creation date",
        "up:modified": "Last modification date",
        "up:version": "Entry version",
        "up:attribution": "Data attribution",
    }

    # Taxonomy-related properties
    TAXONOMY_PROPERTIES = {
        "up:scientificName": "Scientific name",
        "up:commonName": "Common name",
        "up:synonym": "Taxonomic synonym",
        "up:rank": "Taxonomic rank",
        "rdfs:subClassOf": "Parent taxon",
        "up:strain": "Organism strain",
        "up:isolate": "Organism isolate",
    }

    # Gene-related properties
    GENE_PROPERTIES = {
        "up:name": "Gene name",
        "up:orfName": "ORF name",
        "up:locusName": "Locus name",
        "skos:prefLabel": "Preferred gene label",
        "skos:altLabel": "Alternative gene label",
    }

    # Annotation types
    ANNOTATION_TYPES = {
        "up:Function_Annotation": "Protein function",
        "up:Catalytic_Activity_Annotation": "Catalytic activity",
        "up:Cofactor_Annotation": "Cofactor requirements",
        "up:Enzyme_Regulation_Annotation": "Enzyme regulation",
        "up:Biophysicochemical_Properties_Annotation": "Physical/chemical properties",
        "up:Subunit_Annotation": "Subunit structure",
        "up:Subcellular_Location_Annotation": "Cellular location",
        "up:Tissue_Specificity_Annotation": "Tissue expression",
        "up:PTM_Annotation": "Post-translational modification",
        "up:Disease_Annotation": "Disease involvement",
        "up:Pathway_Annotation": "Pathway membership",
        "up:Interaction_Annotation": "Protein interactions",
        "up:Domain_Annotation": "Domain information",
        "up:Sequence_Caution_Annotation": "Sequence issues",
        "up:Alternative_Products_Annotation": "Isoforms and variants",
    }

    # External database cross-references
    CROSS_REFERENCE_DBS = {
        "PDB": "Protein Data Bank (3D structures)",
        "EMBL": "EMBL nucleotide sequence database",
        "RefSeq": "NCBI Reference Sequence database",
        "Ensembl": "Ensembl genome database",
        "InterPro": "Protein family and domain database",
        "Pfam": "Protein families database",
        "PROSITE": "Protein domains and families",
        "GO": "Gene Ontology",
        "KEGG": "KEGG pathways",
        "Reactome": "Reactome pathways",
        "STRING": "Protein interaction networks",
        "IntAct": "Molecular interaction database",
        "DrugBank": "Drug and drug target database",
        "ChEMBL": "Bioactive molecules database",
        "OMIM": "Online Mendelian Inheritance in Man",
        "OrphaNet": "Rare diseases database",
        "GeneCards": "Human genes database",
        "HGNC": "HUGO Gene Nomenclature Committee",
    }


UNIPROT_SCHEMA_INFO = SchemaInfo(
    classes=set(UniProtSchema.CORE_CLASSES.keys()),
    properties=set(UniProtSchema.PROTEIN_PROPERTIES.keys()) |
               set(UniProtSchema.TAXONOMY_PROPERTIES.keys()) |
               set(UniProtSchema.GENE_PROPERTIES.keys()),
    namespaces=UNIPROT_PREFIXES,
    endpoint_info=UNIPROT_ENDPOINT,
)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

class UniProtQueryHelper:
    """
    Helper class providing utility methods for constructing UniProt SPARQL queries.
    """

    @staticmethod
    def resolve_protein_id(protein_id: str) -> str:
        """
        Resolve a protein identifier to a full UniProt URI.

        Args:
            protein_id: Protein identifier (accession, mnemonic, or full URI)

        Returns:
            Full UniProt URI

        Example:
            >>> helper = UniProtQueryHelper()
            >>> uri = helper.resolve_protein_id("P12345")
            >>> print(uri)
            <http://purl.uniprot.org/uniprot/P12345>
        """
        if protein_id.startswith("http"):
            return f"<{protein_id}>"
        else:
            return f"<http://purl.uniprot.org/uniprot/{protein_id}>"

    @staticmethod
    def resolve_taxon_id(taxon_id: str) -> str:
        """
        Resolve a taxonomy identifier to a full UniProt taxonomy URI.

        Args:
            taxon_id: NCBI taxonomy ID (with or without prefix)

        Returns:
            Full UniProt taxonomy URI

        Example:
            >>> helper = UniProtQueryHelper()
            >>> uri = helper.resolve_taxon_id("9606")
            >>> print(uri)
            <http://purl.uniprot.org/taxonomy/9606>
        """
        # Remove "taxon:" prefix if present
        if taxon_id.startswith("taxon:"):
            taxon_id = taxon_id[6:]
        if taxon_id.startswith("http"):
            return f"<{taxon_id}>"
        else:
            return f"<http://purl.uniprot.org/taxonomy/{taxon_id}>"

    @staticmethod
    def build_text_search_filter(text: str, field: str = "?label") -> str:
        """
        Build a FILTER clause for text search.

        Args:
            text: Text to search for
            field: Variable to search in

        Returns:
            SPARQL FILTER clause

        Example:
            >>> helper = UniProtQueryHelper()
            >>> filter_clause = helper.build_text_search_filter("insulin", "?proteinName")
            >>> print(filter_clause)
            FILTER(REGEX(?proteinName, "insulin", "i"))
        """
        return f'FILTER(REGEX({field}, "{text}", "i"))'

    @staticmethod
    def build_taxonomy_hierarchy_pattern(taxon_id: str, variable: str = "?protein") -> str:
        """
        Build a pattern to match proteins from a taxon and its descendants.

        Args:
            taxon_id: Root taxonomy ID
            variable: Variable representing the protein

        Returns:
            SPARQL pattern for taxonomy hierarchy

        Example:
            >>> helper = UniProtQueryHelper()
            >>> pattern = helper.build_taxonomy_hierarchy_pattern("9606", "?protein")
        """
        taxon_uri = UniProtQueryHelper.resolve_taxon_id(taxon_id)
        return f"""
    {variable} up:organism/up:taxon ?taxon .
    ?taxon rdfs:subClassOf* {taxon_uri} .
"""

    @staticmethod
    def build_go_term_pattern(go_id: str, variable: str = "?protein") -> str:
        """
        Build a pattern to match proteins annotated with a GO term.

        Args:
            go_id: Gene Ontology ID (e.g., "GO:0005515")
            variable: Variable representing the protein

        Returns:
            SPARQL pattern for GO term annotation

        Example:
            >>> helper = UniProtQueryHelper()
            >>> pattern = helper.build_go_term_pattern("GO:0005515", "?protein")
        """
        # Remove "GO:" prefix if present
        if go_id.startswith("GO:"):
            go_id = go_id.replace("GO:", "GO_")
        elif not go_id.startswith("GO_"):
            go_id = f"GO_{go_id}"

        return f"""
    {variable} up:classifiedWith <http://purl.obolibrary.org/obo/{go_id}> .
"""

    @staticmethod
    def build_keyword_pattern(keyword: str, variable: str = "?protein") -> str:
        """
        Build a pattern to match proteins with a specific keyword.

        Args:
            keyword: UniProt keyword
            variable: Variable representing the protein

        Returns:
            SPARQL pattern for keyword search

        Example:
            >>> helper = UniProtQueryHelper()
            >>> pattern = helper.build_keyword_pattern("Signal", "?protein")
        """
        return f"""
    {variable} up:classifiedWith ?keyword .
    ?keyword a up:Keyword .
    ?keyword skos:prefLabel ?keywordLabel .
    FILTER(REGEX(?keywordLabel, "{keyword}", "i"))
"""

    @staticmethod
    def build_reviewed_only_filter() -> str:
        """
        Build a filter to restrict results to reviewed (SwissProt) entries only.

        Returns:
            SPARQL pattern for reviewed entries

        Example:
            >>> helper = UniProtQueryHelper()
            >>> pattern = helper.build_reviewed_only_filter()
        """
        return """
    ?protein up:reviewed true .
"""

    @staticmethod
    def build_cross_reference_pattern(
        database: str,
        db_id: Optional[str] = None,
        variable: str = "?protein"
    ) -> str:
        """
        Build a pattern to find proteins with cross-references to external databases.

        Args:
            database: Database name (e.g., "PDB", "Ensembl", "RefSeq")
            db_id: Optional specific database identifier
            variable: Variable representing the protein

        Returns:
            SPARQL pattern for cross-references

        Example:
            >>> helper = UniProtQueryHelper()
            >>> pattern = helper.build_cross_reference_pattern("PDB", "1HHO", "?protein")
        """
        pattern = f"""
    {variable} rdfs:seeAlso ?xref .
    ?xref up:database <http://purl.uniprot.org/database/{database}> .
"""
        if db_id:
            pattern += f'    ?xref up:id "{db_id}" .\n'
        else:
            pattern += '    ?xref up:id ?xrefId .\n'

        return pattern


# =============================================================================
# EXAMPLE QUERIES
# =============================================================================

class UniProtExampleQueries:
    """
    Collection of example SPARQL queries for the UniProt endpoint.

    These examples demonstrate common query patterns and best practices
    for retrieving protein information from UniProt.
    """

    @staticmethod
    def get_protein_basic_info(protein_id: str = "P12345") -> str:
        """
        Get basic information about a specific protein.

        Args:
            protein_id: UniProt accession number

        Returns:
            SPARQL query string
        """
        return get_prefix_string() + f"""
SELECT ?protein ?mnemonic ?name ?organism ?length ?mass
WHERE {{
    BIND({UniProtQueryHelper.resolve_protein_id(protein_id)} AS ?protein)

    ?protein a up:Protein .
    ?protein up:mnemonic ?mnemonic .
    ?protein up:organism ?organism_node .
    ?organism_node up:scientificName ?organism .

    OPTIONAL {{ ?protein up:recommendedName ?recName .
               ?recName up:fullName ?name . }}

    OPTIONAL {{ ?protein up:sequence ?seq .
               ?seq rdf:value ?sequence ;
                    up:length ?length ;
                    up:mass ?mass . }}
}}
"""

    @staticmethod
    def search_proteins_by_name(name: str, limit: int = 10) -> str:
        """
        Search for proteins by name (case-insensitive).

        Args:
            name: Protein name or partial name
            limit: Maximum number of results

        Returns:
            SPARQL query string
        """
        return get_prefix_string() + f"""
SELECT ?protein ?mnemonic ?fullName ?organism
WHERE {{
    ?protein a up:Protein .
    ?protein up:mnemonic ?mnemonic .
    ?protein up:recommendedName ?recName .
    ?recName up:fullName ?fullName .
    ?protein up:organism ?organism_node .
    ?organism_node up:scientificName ?organism .

    FILTER(REGEX(?fullName, "{name}", "i"))
}}
LIMIT {limit}
"""

    @staticmethod
    def get_human_proteins_by_gene(gene_name: str) -> str:
        """
        Find human proteins encoded by a specific gene.

        Args:
            gene_name: Gene name (e.g., "BRCA1", "TP53")

        Returns:
            SPARQL query string
        """
        return get_prefix_string() + f"""
SELECT ?protein ?mnemonic ?proteinName ?geneName
WHERE {{
    ?protein a up:Protein .
    ?protein up:mnemonic ?mnemonic .
    ?protein up:organism ?organism .
    ?organism up:scientificName "Homo sapiens" .

    ?protein up:encodedBy ?gene .
    ?gene skos:prefLabel ?geneName .
    FILTER(REGEX(?geneName, "^{gene_name}$", "i"))

    OPTIONAL {{
        ?protein up:recommendedName ?recName .
        ?recName up:fullName ?proteinName .
    }}
}}
"""

    @staticmethod
    def get_proteins_by_taxonomy(taxon_id: str = "9606", limit: int = 100) -> str:
        """
        Get proteins from a specific organism (by NCBI taxonomy ID).

        Args:
            taxon_id: NCBI taxonomy ID (e.g., "9606" for human)
            limit: Maximum number of results

        Returns:
            SPARQL query string
        """
        return get_prefix_string() + f"""
SELECT ?protein ?mnemonic ?name ?geneName
WHERE {{
    ?protein a up:Protein .
    ?protein up:mnemonic ?mnemonic .
    ?protein up:organism/up:taxon {UniProtQueryHelper.resolve_taxon_id(taxon_id)} .
    ?protein up:reviewed true .  # Reviewed entries only

    OPTIONAL {{
        ?protein up:recommendedName ?recName .
        ?recName up:fullName ?name .
    }}

    OPTIONAL {{
        ?protein up:encodedBy ?gene .
        ?gene skos:prefLabel ?geneName .
    }}
}}
LIMIT {limit}
"""

    @staticmethod
    def get_protein_sequence(protein_id: str = "P12345") -> str:
        """
        Retrieve the amino acid sequence for a protein.

        Args:
            protein_id: UniProt accession number

        Returns:
            SPARQL query string
        """
        return get_prefix_string() + f"""
SELECT ?protein ?sequence ?length ?mass ?crc64
WHERE {{
    BIND({UniProtQueryHelper.resolve_protein_id(protein_id)} AS ?protein)

    ?protein up:sequence ?seq .
    ?seq rdf:value ?sequence ;
         up:length ?length ;
         up:mass ?mass ;
         up:crc64 ?crc64 .
}}
"""

    @staticmethod
    def get_protein_function(protein_id: str = "P12345") -> str:
        """
        Get functional annotations for a protein.

        Args:
            protein_id: UniProt accession number

        Returns:
            SPARQL query string
        """
        return get_prefix_string() + f"""
SELECT ?protein ?functionText ?goTerm ?goLabel
WHERE {{
    BIND({UniProtQueryHelper.resolve_protein_id(protein_id)} AS ?protein)

    # Function annotation
    OPTIONAL {{
        ?protein up:annotation ?functionAnnotation .
        ?functionAnnotation a up:Function_Annotation ;
                           rdfs:comment ?functionText .
    }}

    # GO annotations
    OPTIONAL {{
        ?protein up:classifiedWith ?goTerm .
        ?goTerm rdfs:label ?goLabel .
        FILTER(STRSTARTS(STR(?goTerm), "http://purl.obolibrary.org/obo/GO_"))
    }}
}}
"""

    @staticmethod
    def get_protein_disease_associations(protein_id: str = "P12345") -> str:
        """
        Get disease associations for a protein.

        Args:
            protein_id: UniProt accession number

        Returns:
            SPARQL query string
        """
        return get_prefix_string() + f"""
SELECT ?protein ?disease ?diseaseLabel ?diseaseComment
WHERE {{
    BIND({UniProtQueryHelper.resolve_protein_id(protein_id)} AS ?protein)

    ?protein up:annotation ?diseaseAnnotation .
    ?diseaseAnnotation a up:Disease_Annotation ;
                      up:disease ?disease .

    OPTIONAL {{ ?disease skos:prefLabel ?diseaseLabel . }}
    OPTIONAL {{ ?diseaseAnnotation rdfs:comment ?diseaseComment . }}
}}
"""

    @staticmethod
    def get_protein_subcellular_location(protein_id: str = "P12345") -> str:
        """
        Get subcellular location information for a protein.

        Args:
            protein_id: UniProt accession number

        Returns:
            SPARQL query string
        """
        return get_prefix_string() + f"""
SELECT ?protein ?location ?locationLabel ?topology
WHERE {{
    BIND({UniProtQueryHelper.resolve_protein_id(protein_id)} AS ?protein)

    ?protein up:annotation ?locAnnotation .
    ?locAnnotation a up:Subcellular_Location_Annotation .

    OPTIONAL {{
        ?locAnnotation up:locatedIn ?location .
        ?location skos:prefLabel ?locationLabel .
    }}

    OPTIONAL {{
        ?locAnnotation up:topology ?topologyNode .
        ?topologyNode skos:prefLabel ?topology .
    }}
}}
"""

    @staticmethod
    def get_protein_domains(protein_id: str = "P12345") -> str:
        """
        Get domain and region information for a protein.

        Args:
            protein_id: UniProt accession number

        Returns:
            SPARQL query string
        """
        return get_prefix_string() + f"""
SELECT ?protein ?domainType ?domainLabel ?begin ?end ?description
WHERE {{
    BIND({UniProtQueryHelper.resolve_protein_id(protein_id)} AS ?protein)

    ?protein up:annotation ?domainAnnotation .
    ?domainAnnotation a ?domainType ;
                     rdfs:comment ?description .

    FILTER(?domainType IN (up:Domain_Annotation, up:Region_Annotation))

    OPTIONAL {{
        ?domainAnnotation up:range ?range .
        ?range faldo:begin/faldo:position ?begin ;
               faldo:end/faldo:position ?end .
    }}

    OPTIONAL {{ ?domainAnnotation rdfs:label ?domainLabel . }}
}}
ORDER BY ?begin
"""

    @staticmethod
    def get_protein_cross_references(protein_id: str = "P12345") -> str:
        """
        Get cross-references to external databases.

        Args:
            protein_id: UniProt accession number

        Returns:
            SPARQL query string
        """
        return get_prefix_string() + f"""
SELECT ?protein ?database ?databaseName ?xrefId
WHERE {{
    BIND({UniProtQueryHelper.resolve_protein_id(protein_id)} AS ?protein)

    ?protein rdfs:seeAlso ?xref .
    ?xref up:database ?database ;
          up:id ?xrefId .

    ?database skos:prefLabel ?databaseName .
}}
ORDER BY ?databaseName ?xrefId
"""

    @staticmethod
    def get_proteins_by_go_term(go_id: str = "GO:0005515", limit: int = 50) -> str:
        """
        Find proteins annotated with a specific Gene Ontology term.

        Args:
            go_id: Gene Ontology ID (e.g., "GO:0005515" for protein binding)
            limit: Maximum number of results

        Returns:
            SPARQL query string
        """
        # Normalize GO ID format
        go_id_normalized = go_id.replace("GO:", "GO_")

        return get_prefix_string() + f"""
SELECT ?protein ?mnemonic ?name ?organism ?goLabel
WHERE {{
    ?protein a up:Protein ;
             up:mnemonic ?mnemonic ;
             up:organism ?organism_node .

    ?organism_node up:scientificName ?organism .

    # GO term annotation
    ?protein up:classifiedWith <http://purl.obolibrary.org/obo/{go_id_normalized}> .

    OPTIONAL {{
        <http://purl.obolibrary.org/obo/{go_id_normalized}> rdfs:label ?goLabel .
    }}

    OPTIONAL {{
        ?protein up:recommendedName ?recName .
        ?recName up:fullName ?name .
    }}
}}
LIMIT {limit}
"""

    @staticmethod
    def get_proteins_by_keyword(keyword: str = "Membrane", limit: int = 50) -> str:
        """
        Find proteins with a specific UniProt keyword.

        Args:
            keyword: UniProt keyword (e.g., "Membrane", "Signal", "Kinase")
            limit: Maximum number of results

        Returns:
            SPARQL query string
        """
        return get_prefix_string() + f"""
SELECT ?protein ?mnemonic ?name ?keywordLabel
WHERE {{
    ?protein a up:Protein ;
             up:mnemonic ?mnemonic ;
             up:classifiedWith ?keyword .

    ?keyword a up:Keyword ;
             skos:prefLabel ?keywordLabel .

    FILTER(REGEX(?keywordLabel, "{keyword}", "i"))

    OPTIONAL {{
        ?protein up:recommendedName ?recName .
        ?recName up:fullName ?name .
    }}
}}
LIMIT {limit}
"""

    @staticmethod
    def get_enzyme_by_ec_number(ec_number: str = "1.1.1.1") -> str:
        """
        Find enzymes by EC (Enzyme Commission) number.

        Args:
            ec_number: EC number (e.g., "1.1.1.1" for alcohol dehydrogenase)

        Returns:
            SPARQL query string
        """
        return get_prefix_string() + f"""
SELECT ?protein ?mnemonic ?name ?organism ?ecNumber
WHERE {{
    ?protein a up:Protein ;
             up:mnemonic ?mnemonic ;
             up:enzyme ?enzyme ;
             up:organism ?organism_node .

    ?enzyme skos:prefLabel ?ecNumber .
    FILTER(?ecNumber = "{ec_number}")

    ?organism_node up:scientificName ?organism .

    OPTIONAL {{
        ?protein up:recommendedName ?recName .
        ?recName up:fullName ?name .
    }}
}}
"""

    @staticmethod
    def get_proteins_with_pdb_structure(limit: int = 100) -> str:
        """
        Find proteins that have 3D structures in the Protein Data Bank.

        Args:
            limit: Maximum number of results

        Returns:
            SPARQL query string
        """
        return get_prefix_string() + f"""
SELECT ?protein ?mnemonic ?name ?pdbId
WHERE {{
    ?protein a up:Protein ;
             up:mnemonic ?mnemonic ;
             rdfs:seeAlso ?pdb .

    ?pdb up:database <http://purl.uniprot.org/database/PDB> ;
         up:id ?pdbId .

    OPTIONAL {{
        ?protein up:recommendedName ?recName .
        ?recName up:fullName ?name .
    }}
}}
LIMIT {limit}
"""

    @staticmethod
    def get_protein_interactions(protein_id: str = "P12345") -> str:
        """
        Get protein-protein interaction information.

        Args:
            protein_id: UniProt accession number

        Returns:
            SPARQL query string
        """
        return get_prefix_string() + f"""
SELECT ?protein ?interactionType ?interactant ?interactantName
WHERE {{
    BIND({UniProtQueryHelper.resolve_protein_id(protein_id)} AS ?protein)

    ?protein up:annotation ?interaction .
    ?interaction a up:Interaction_Annotation ;
                rdfs:comment ?interactionType .

    OPTIONAL {{
        ?interaction up:interactant ?interactant .
        ?interactant up:mnemonic ?interactantName .
    }}
}}
"""

    @staticmethod
    def get_proteins_by_mass_range(
        min_mass: float = 50000,
        max_mass: float = 60000,
        limit: int = 50
    ) -> str:
        """
        Find proteins within a specific molecular mass range.

        Args:
            min_mass: Minimum mass in Daltons
            max_mass: Maximum mass in Daltons
            limit: Maximum number of results

        Returns:
            SPARQL query string
        """
        return get_prefix_string() + f"""
SELECT ?protein ?mnemonic ?name ?mass ?length
WHERE {{
    ?protein a up:Protein ;
             up:mnemonic ?mnemonic ;
             up:sequence ?seq .

    ?seq up:mass ?mass ;
         up:length ?length .

    FILTER(?mass >= {min_mass} && ?mass <= {max_mass})

    OPTIONAL {{
        ?protein up:recommendedName ?recName .
        ?recName up:fullName ?name .
    }}
}}
ORDER BY ?mass
LIMIT {limit}
"""

    @staticmethod
    def get_taxonomy_lineage(taxon_id: str = "9606") -> str:
        """
        Get the complete taxonomic lineage for an organism.

        Args:
            taxon_id: NCBI taxonomy ID

        Returns:
            SPARQL query string
        """
        return get_prefix_string() + f"""
SELECT ?taxon ?scientificName ?rank ?parent
WHERE {{
    BIND({UniProtQueryHelper.resolve_taxon_id(taxon_id)} AS ?startTaxon)

    ?startTaxon rdfs:subClassOf* ?taxon .

    ?taxon up:scientificName ?scientificName .

    OPTIONAL {{ ?taxon up:rank ?rank . }}
    OPTIONAL {{
        ?taxon rdfs:subClassOf ?parent .
        FILTER(?parent != <http://purl.uniprot.org/core/Taxon>)
    }}
}}
ORDER BY DESC(?rank)
"""

    @staticmethod
    def count_proteins_by_organism(limit: int = 20) -> str:
        """
        Count proteins grouped by organism (most common organisms).

        Args:
            limit: Number of organisms to return

        Returns:
            SPARQL query string
        """
        return get_prefix_string() + f"""
SELECT ?organism (COUNT(?protein) AS ?proteinCount)
WHERE {{
    ?protein a up:Protein ;
             up:organism ?organism_node .

    ?organism_node up:scientificName ?organism .
}}
GROUP BY ?organism
ORDER BY DESC(?proteinCount)
LIMIT {limit}
"""

    @staticmethod
    def get_protein_publications(protein_id: str = "P12345") -> str:
        """
        Get publications (citations) associated with a protein.

        Args:
            protein_id: UniProt accession number

        Returns:
            SPARQL query string
        """
        return get_prefix_string() + f"""
SELECT ?protein ?citation ?title ?pubMedId ?doi
WHERE {{
    BIND({UniProtQueryHelper.resolve_protein_id(protein_id)} AS ?protein)

    ?protein up:citation ?citation .

    OPTIONAL {{ ?citation dc:title ?title . }}
    OPTIONAL {{ ?citation up:pubMedId ?pubMedId . }}
    OPTIONAL {{ ?citation up:doi ?doi . }}
}}
"""


# =============================================================================
# PERFORMANCE OPTIMIZATION TIPS
# =============================================================================

PERFORMANCE_TIPS = """
Performance Optimization Tips for UniProt SPARQL Queries
=========================================================

1. FILTER EARLY
   - Apply filters as early as possible in the query
   - Filter by taxonomy before retrieving annotations
   - Use FILTER clauses right after the relevant triple pattern

2. USE LIMIT CLAUSES
   - Always use LIMIT for exploratory queries
   - Start with small limits (10-100) for testing
   - Increase gradually as needed

3. SPECIFY REVIEWED ENTRIES
   - Add "?protein up:reviewed true" to get only SwissProt entries
   - SwissProt is smaller and higher quality than TrEMBL
   - This dramatically reduces result set size

4. AVOID BROAD TEXT SEARCHES
   - Text searches with REGEX are expensive
   - Combine text searches with other filters
   - Use specific identifiers when known

5. USE OPTIONAL WISELY
   - OPTIONAL blocks can slow down queries
   - Place OPTIONAL blocks after required patterns
   - Consider whether data is truly optional

6. OPTIMIZE TAXONOMY QUERIES
   - Use specific taxonomy IDs when possible
   - Be cautious with rdfs:subClassOf* (transitive)
   - Filter by taxonomy before complex patterns

7. MINIMIZE CROSS-REFERENCES
   - Cross-reference retrieval can be slow
   - Request only needed databases
   - Use specific database filters

8. USE BIND FOR CONSTANTS
   - Use BIND to set constant values
   - Improves query clarity and performance
   - Example: BIND(<http://purl.uniprot.org/uniprot/P12345> AS ?protein)

9. AVOID REDUNDANT PATTERNS
   - Don't retrieve the same data multiple ways
   - Check if data is already available in previous patterns
   - Combine related patterns efficiently

10. FEDERATED QUERIES
    - Be very careful with SERVICE (federated queries)
    - Federated queries can be extremely slow
    - Use only when absolutely necessary
    - Add LIMIT to federated sub-queries

Example of a well-optimized query:
-----------------------------------
PREFIX up: <http://purl.uniprot.org/core/>
PREFIX uptaxon: <http://purl.uniprot.org/taxonomy/>

SELECT ?protein ?name WHERE {
    # Filter by organism FIRST (reduces search space)
    ?protein up:organism/up:taxon uptaxon:9606 .

    # Get only reviewed entries (SwissProt)
    ?protein up:reviewed true .

    # Then retrieve other properties
    ?protein a up:Protein ;
             up:recommendedName/up:fullName ?name .

    # Apply text filter after other constraints
    FILTER(CONTAINS(LCASE(?name), "kinase"))
}
LIMIT 100
"""


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    "UNIPROT_ENDPOINT",
    "UNIPROT_PREFIXES",
    "UNIPROT_SCHEMA_INFO",
    "UniProtSchema",
    "UniProtQueryHelper",
    "UniProtExampleQueries",
    "PERFORMANCE_TIPS",
    "get_prefix_string",
]
