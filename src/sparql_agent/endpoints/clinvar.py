"""
ClinVar SPARQL Endpoint Configuration and Utilities.

This module provides comprehensive support for querying ClinVar genetic variant data
via SPARQL endpoints, including endpoint configuration, common prefixes, schema information,
helper functions, and example queries for clinical genetics research.

ClinVar is a freely accessible, public archive of reports of human variation and their
relationships to phenotypes, with supporting evidence. ClinVar facilitates access to and
communication about the relationships asserted between human variation and observed health
status, and the history of that interpretation. It provides access to:
- Genetic variant data (SNPs, CNVs, indels, etc.)
- Clinical significance classifications (pathogenic, benign, VUS, etc.)
- Gene-disease associations
- Phenotype mappings (HPO, OMIM, etc.)
- Allele frequencies and population data
- Evidence and provenance information

Data Access:
ClinVar data can be accessed via SPARQL through Bio2RDF (https://bio2rdf.org) and
GT2RDF (Genetic Testing to RDF) semantic frameworks, which provide RDF representations
of ClinVar data integrated with other biomedical resources.

Official Resources:
- ClinVar Homepage: https://www.ncbi.nlm.nih.gov/clinvar/
- ClinVar Documentation: https://www.ncbi.nlm.nih.gov/clinvar/docs/
- Bio2RDF SPARQL Endpoint: http://bio2rdf.org/sparql
- GT2RDF Project: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5333271/
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from ..core.types import EndpointInfo, SchemaInfo


# =============================================================================
# ENDPOINT CONFIGURATION
# =============================================================================

CLINVAR_ENDPOINT = EndpointInfo(
    url="http://bio2rdf.org/sparql",
    name="ClinVar SPARQL Endpoint (Bio2RDF)",
    description=(
        "The ClinVar SPARQL endpoint via Bio2RDF provides programmatic access to ClinVar "
        "genetic variant data using the SPARQL query language. It includes comprehensive "
        "variant annotations, clinical significance assessments, gene-disease associations, "
        "phenotype mappings, and population frequency data in RDF format."
    ),
    graph_uri="http://bio2rdf.org/clinvar:",
    supports_update=False,
    timeout=90,  # Clinical queries can be complex
    rate_limit=2.0,  # Be respectful of the public service
    authentication_required=False,
    version="1.1",
    metadata={
        "provider": "Bio2RDF / National Center for Biotechnology Information (NCBI)",
        "license": "Public Domain (ClinVar data)",
        "data_version": "ClinVar",
        "update_frequency": "Monthly (following ClinVar releases)",
        "documentation": "https://www.ncbi.nlm.nih.gov/clinvar/docs/",
        "bio2rdf_documentation": "https://bio2rdf.org/",
        "data_size": "~2.5 million variant records",
        "clinical_use_notice": [
            "For research and educational purposes only",
            "Not for clinical diagnostic use without proper validation",
            "Always verify critical information with primary sources",
            "Follow appropriate clinical guidelines and regulations",
            "Respect patient privacy and data protection laws"
        ],
        "performance_tips": [
            "Use specific variant or gene identifiers when known",
            "Filter by clinical significance early in queries",
            "Limit result sets for exploratory queries",
            "Use specific genomic coordinates when available",
            "Combine filters to reduce search space"
        ],
        "related_resources": [
            "dbSNP: https://www.ncbi.nlm.nih.gov/snp/",
            "dbVar: https://www.ncbi.nlm.nih.gov/dbvar/",
            "GTEx: https://gtexportal.org/",
            "gnomAD: https://gnomad.broadinstitute.org/",
            "OMIM: https://www.omim.org/",
            "HPO: https://hpo.jax.org/"
        ]
    }
)


# Alternative endpoint for GT2RDF semantic representation
GT2RDF_ENDPOINT = EndpointInfo(
    url="http://gt2rdf.ncbo.io/sparql",
    name="GT2RDF SPARQL Endpoint (Genetic Testing to RDF)",
    description=(
        "GT2RDF provides a semantic representation of genetic testing data including "
        "ClinVar, integrating information about disease, gene, phenotype, genetic tests, "
        "and drugs from multiple sources into a unified RDF resource."
    ),
    graph_uri=None,
    supports_update=False,
    timeout=90,
    rate_limit=2.0,
    authentication_required=False,
    version="1.1",
    metadata={
        "provider": "GT2RDF Project / NCBO BioPortal",
        "license": "Varies by source database",
        "data_version": "GT2RDF",
        "documentation": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5333271/",
        "integrated_sources": [
            "ClinVar", "OMIM", "HPO", "PharmGKB", "GTR", "UniProt"
        ]
    }
)


# =============================================================================
# COMMON PREFIXES AND NAMESPACES
# =============================================================================

CLINVAR_PREFIXES = {
    # Bio2RDF ClinVar namespaces
    "clinvar": "http://bio2rdf.org/clinvar:",
    "clinvar_vocabulary": "http://bio2rdf.org/clinvar_vocabulary:",
    "clinvar_resource": "http://bio2rdf.org/clinvar_resource:",

    # NCBI namespaces
    "ncbi": "http://bio2rdf.org/ncbi:",
    "ncbigene": "http://bio2rdf.org/ncbigene:",
    "dbsnp": "http://bio2rdf.org/dbsnp:",
    "pubmed": "http://bio2rdf.org/pubmed:",

    # Genetic variant and genomic namespaces
    "hgvs": "http://purl.obolibrary.org/obo/GENO_",
    "geno": "http://purl.obolibrary.org/obo/GENO_",
    "so": "http://purl.obolibrary.org/obo/SO_",
    "vario": "http://purl.obolibrary.org/obo/VARIO_",
    "seqont": "http://purl.obolibrary.org/obo/SEQONT_",

    # Clinical and phenotype ontologies
    "hpo": "http://purl.obolibrary.org/obo/HP_",
    "omim": "http://bio2rdf.org/omim:",
    "orphanet": "http://bio2rdf.org/orphanet:",
    "mondo": "http://purl.obolibrary.org/obo/MONDO_",
    "doid": "http://purl.obolibrary.org/obo/DOID_",

    # Medical terminologies
    "snomed": "http://purl.bioontology.org/ontology/SNOMEDCT/",
    "loinc": "http://purl.bioontology.org/ontology/LNC/",
    "rxnorm": "http://purl.bioontology.org/ontology/RXNORM/",
    "icd10": "http://purl.bioontology.org/ontology/ICD10/",
    "icd11": "http://purl.bioontology.org/ontology/ICD11/",

    # Genomic coordinates and references
    "grch37": "http://rdf.ebi.ac.uk/resource/ensembl.grch37/",
    "grch38": "http://rdf.ebi.ac.uk/resource/ensembl/",
    "faldo": "http://biohackathon.org/resource/faldo#",

    # Pharmacogenomics
    "pharmgkb": "http://bio2rdf.org/pharmgkb:",
    "drugbank": "http://bio2rdf.org/drugbank:",
    "chebi": "http://purl.obolibrary.org/obo/CHEBI_",

    # Gene and protein resources
    "hgnc": "http://bio2rdf.org/hgnc:",
    "uniprot": "http://purl.uniprot.org/uniprot/",
    "ensembl": "http://identifiers.org/ensembl/",

    # Standard ontology namespaces
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "dc": "http://purl.org/dc/terms/",
    "dcterms": "http://purl.org/dc/terms/",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "prov": "http://www.w3.org/ns/prov#",

    # Evidence and citations
    "eco": "http://purl.obolibrary.org/obo/ECO_",
    "cito": "http://purl.org/spar/cito/",

    # Bio2RDF core vocabulary
    "bio2rdf": "http://bio2rdf.org/bio2rdf_vocabulary:",
}


def get_prefix_string() -> str:
    """
    Generate SPARQL PREFIX declarations for ClinVar queries.

    Returns:
        String containing all PREFIX declarations

    Example:
        >>> prefixes = get_prefix_string()
        >>> query = prefixes + '''
        ... SELECT ?variant ?gene WHERE {
        ...     ?variant a clinvar_vocabulary:Variant .
        ... } LIMIT 10
        ... '''
    """
    return "\n".join(
        f"PREFIX {prefix}: <{uri}>"
        for prefix, uri in CLINVAR_PREFIXES.items()
    ) + "\n\n"


# =============================================================================
# SCHEMA INFORMATION
# =============================================================================

@dataclass
class ClinVarSchema:
    """
    Schema information for the ClinVar SPARQL endpoint.

    This class provides comprehensive information about the ClinVar data model,
    including core classes, properties, and their relationships for genetic
    variant data and clinical annotations.
    """

    # Core ClinVar classes
    CORE_CLASSES = {
        "clinvar_vocabulary:Variant": "A genetic variant (SNP, CNV, indel, etc.)",
        "clinvar_vocabulary:VariantInterpretation": "Clinical interpretation of a variant",
        "clinvar_vocabulary:Allele": "An allele at a specific genomic location",
        "clinvar_vocabulary:Haplotype": "A group of alleles inherited together",
        "clinvar_vocabulary:Genotype": "A specific combination of alleles",
        "clinvar_vocabulary:Gene": "A gene associated with variants",
        "clinvar_vocabulary:Phenotype": "A phenotype associated with variants",
        "clinvar_vocabulary:Disease": "A disease associated with variants",
        "clinvar_vocabulary:ClinicalSignificance": "Clinical significance classification",
        "clinvar_vocabulary:SubmissionRecord": "A submitter's assertion",
        "clinvar_vocabulary:Evidence": "Evidence supporting an interpretation",
        "clinvar_vocabulary:Population": "Population frequency information",
        "clinvar_vocabulary:FunctionalConsequence": "Predicted functional impact",
        "clinvar_vocabulary:MolecularConsequence": "Molecular-level consequence",
        "clinvar_vocabulary:GenomicLocation": "Genomic coordinates of variant",
    }

    # Variant properties
    VARIANT_PROPERTIES = {
        # Identity and naming
        "clinvar_vocabulary:id": "ClinVar variant ID (VCV or RCV)",
        "clinvar_vocabulary:variantId": "ClinVar Variation ID",
        "clinvar_vocabulary:alleleId": "ClinVar Allele ID",
        "clinvar_vocabulary:name": "Variant name or label",
        "clinvar_vocabulary:title": "Variant title",

        # HGVS nomenclature
        "clinvar_vocabulary:hgvsGenomic": "HGVS genomic description",
        "clinvar_vocabulary:hgvsCoding": "HGVS coding sequence description",
        "clinvar_vocabulary:hgvsProtein": "HGVS protein description",
        "clinvar_vocabulary:hgvsNonCoding": "HGVS non-coding RNA description",

        # Genomic location
        "clinvar_vocabulary:chromosome": "Chromosome location",
        "clinvar_vocabulary:position": "Genomic position",
        "clinvar_vocabulary:startPosition": "Start position",
        "clinvar_vocabulary:endPosition": "End position",
        "clinvar_vocabulary:assembly": "Reference assembly (GRCh37/GRCh38)",
        "clinvar_vocabulary:referenceAllele": "Reference allele",
        "clinvar_vocabulary:alternateAllele": "Alternate allele",

        # Variant type and consequence
        "clinvar_vocabulary:variantType": "Type of variant (SNV, deletion, insertion, etc.)",
        "clinvar_vocabulary:molecularConsequence": "Molecular consequence",
        "clinvar_vocabulary:functionalConsequence": "Functional consequence",
        "clinvar_vocabulary:sequenceOntology": "Sequence Ontology term",

        # Gene associations
        "clinvar_vocabulary:hasGene": "Associated gene",
        "clinvar_vocabulary:geneSymbol": "Gene symbol",
        "clinvar_vocabulary:geneId": "Gene identifier (NCBI Gene ID, HGNC, etc.)",
        "clinvar_vocabulary:transcriptId": "Transcript identifier",

        # Clinical significance
        "clinvar_vocabulary:clinicalSignificance": "Clinical significance classification",
        "clinvar_vocabulary:reviewStatus": "Review status",
        "clinvar_vocabulary:interpretation": "Clinical interpretation",
        "clinvar_vocabulary:assertionCriteria": "Guidelines used for interpretation",

        # Phenotype and disease associations
        "clinvar_vocabulary:hasPhenotype": "Associated phenotype",
        "clinvar_vocabulary:hasDisease": "Associated disease",
        "clinvar_vocabulary:phenotypeName": "Phenotype name",
        "clinvar_vocabulary:diseaseName": "Disease name",
        "clinvar_vocabulary:modeOfInheritance": "Mode of inheritance",

        # Population data
        "clinvar_vocabulary:alleleFrequency": "Allele frequency",
        "clinvar_vocabulary:populationData": "Population frequency data",
        "clinvar_vocabulary:minorAlleleFrequency": "Minor allele frequency (MAF)",

        # Evidence and provenance
        "clinvar_vocabulary:hasEvidence": "Supporting evidence",
        "clinvar_vocabulary:evidenceLevel": "Level of evidence",
        "clinvar_vocabulary:submitter": "Submitter organization",
        "clinvar_vocabulary:dateCreated": "Creation date",
        "clinvar_vocabulary:dateUpdated": "Last update date",
        "clinvar_vocabulary:hasAssertion": "Clinical assertion",

        # Cross-references
        "clinvar_vocabulary:dbSNP": "dbSNP reference SNP (rs) number",
        "clinvar_vocabulary:dbVar": "dbVar reference",
        "clinvar_vocabulary:omim": "OMIM reference",
        "clinvar_vocabulary:pubmed": "PubMed citation",
        "rdfs:seeAlso": "Cross-references to other databases",
    }

    # Clinical significance categories
    CLINICAL_SIGNIFICANCE_CATEGORIES = {
        "Pathogenic": "Variant is pathogenic for a disease",
        "Likely pathogenic": "Variant is likely pathogenic",
        "Uncertain significance": "Variant of uncertain significance (VUS)",
        "Likely benign": "Variant is likely benign",
        "Benign": "Variant is benign",
        "Conflicting interpretations": "Different submitters have conflicting interpretations",
        "Risk factor": "Variant is a risk factor for disease",
        "Association": "Variant is associated with a trait or disease",
        "Protective": "Variant is protective against disease",
        "Affects": "Variant affects gene product or clinical outcome",
        "Drug response": "Variant affects drug response (pharmacogenomics)",
        "Not provided": "No interpretation provided",
    }

    # Review status levels
    REVIEW_STATUS_LEVELS = {
        "practice guideline": "Interpretation in professional guideline",
        "reviewed by expert panel": "Reviewed by expert panel",
        "criteria provided, multiple submitters, no conflicts": "Multiple submitters agree",
        "criteria provided, single submitter": "Single submitter with criteria",
        "criteria provided, conflicting interpretations": "Multiple submitters disagree",
        "no assertion criteria provided": "No criteria specified",
        "no assertion provided": "No interpretation provided",
    }

    # Variant types
    VARIANT_TYPES = {
        "single nucleotide variant": "SNV - Single nucleotide substitution",
        "deletion": "Deletion of nucleotides",
        "insertion": "Insertion of nucleotides",
        "duplication": "Duplication of sequence",
        "indel": "Insertion-deletion",
        "copy number gain": "Copy number increase",
        "copy number loss": "Copy number decrease",
        "inversion": "Sequence inversion",
        "translocation": "Chromosomal translocation",
        "complex": "Complex structural variant",
        "microsatellite": "Microsatellite repeat variation",
    }

    # Molecular consequence terms (Sequence Ontology)
    MOLECULAR_CONSEQUENCES = {
        "missense_variant": "Amino acid substitution",
        "nonsense_variant": "Premature stop codon",
        "frameshift_variant": "Frameshift mutation",
        "splice_site_variant": "Affects splicing",
        "splice_donor_variant": "Affects splice donor site",
        "splice_acceptor_variant": "Affects splice acceptor site",
        "stop_gained": "Creates stop codon",
        "stop_lost": "Removes stop codon",
        "start_lost": "Affects start codon",
        "inframe_insertion": "In-frame insertion",
        "inframe_deletion": "In-frame deletion",
        "synonymous_variant": "Silent mutation",
        "5_prime_UTR_variant": "In 5' untranslated region",
        "3_prime_UTR_variant": "In 3' untranslated region",
        "intron_variant": "In intron",
        "regulatory_region_variant": "In regulatory region",
    }

    # Mode of inheritance
    INHERITANCE_MODES = {
        "Autosomal dominant": "Autosomal dominant inheritance",
        "Autosomal recessive": "Autosomal recessive inheritance",
        "X-linked dominant": "X-linked dominant inheritance",
        "X-linked recessive": "X-linked recessive inheritance",
        "Y-linked": "Y-linked inheritance",
        "Mitochondrial": "Mitochondrial inheritance",
        "Somatic": "Somatic mutation (non-inherited)",
        "De novo": "New mutation not inherited from parents",
        "Multifactorial": "Multifactorial inheritance",
        "Codominant": "Codominant inheritance",
    }

    # External ontologies and vocabularies
    EXTERNAL_ONTOLOGIES = {
        "HPO": "Human Phenotype Ontology - phenotypic abnormalities",
        "OMIM": "Online Mendelian Inheritance in Man",
        "MONDO": "Monarch Disease Ontology",
        "DOID": "Disease Ontology",
        "Orphanet": "Rare diseases database",
        "SNOMED CT": "Systematized Nomenclature of Medicine Clinical Terms",
        "LOINC": "Logical Observation Identifiers Names and Codes",
        "ICD-10": "International Classification of Diseases, 10th Revision",
        "ICD-11": "International Classification of Diseases, 11th Revision",
        "SO": "Sequence Ontology - sequence feature terms",
        "GENO": "Genotype Ontology",
        "ECO": "Evidence and Conclusion Ontology",
    }


CLINVAR_SCHEMA_INFO = SchemaInfo(
    classes=set(ClinVarSchema.CORE_CLASSES.keys()),
    properties=set(ClinVarSchema.VARIANT_PROPERTIES.keys()),
    namespaces=CLINVAR_PREFIXES,
    endpoint_info=CLINVAR_ENDPOINT,
)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

class ClinVarQueryHelper:
    """
    Helper class providing utility methods for constructing ClinVar SPARQL queries.
    """

    @staticmethod
    def resolve_variant_id(variant_id: str) -> str:
        """
        Resolve a variant identifier to a full ClinVar URI.

        Args:
            variant_id: Variant identifier (VCV, RCV, or numeric ID)

        Returns:
            Full ClinVar URI

        Example:
            >>> helper = ClinVarQueryHelper()
            >>> uri = helper.resolve_variant_id("VCV000012345")
            >>> print(uri)
            <http://bio2rdf.org/clinvar:VCV000012345>
        """
        if variant_id.startswith("http"):
            return f"<{variant_id}>"
        else:
            return f"<http://bio2rdf.org/clinvar:{variant_id}>"

    @staticmethod
    def resolve_gene_id(gene_id: str) -> str:
        """
        Resolve a gene identifier to a full NCBI Gene URI.

        Args:
            gene_id: Gene identifier (NCBI Gene ID, HGNC symbol, etc.)

        Returns:
            Full gene URI

        Example:
            >>> helper = ClinVarQueryHelper()
            >>> uri = helper.resolve_gene_id("672")  # BRCA1 gene ID
            >>> print(uri)
            <http://bio2rdf.org/ncbigene:672>
        """
        if gene_id.startswith("http"):
            return f"<{gene_id}>"
        elif gene_id.isdigit():
            return f"<http://bio2rdf.org/ncbigene:{gene_id}>"
        else:
            # Assume HGNC symbol, may need additional resolution
            return f"<http://bio2rdf.org/hgnc:{gene_id}>"

    @staticmethod
    def build_clinical_significance_filter(significance: str, variable: str = "?significance") -> str:
        """
        Build a FILTER clause for clinical significance.

        Args:
            significance: Clinical significance category
            variable: Variable to filter

        Returns:
            SPARQL FILTER clause

        Example:
            >>> helper = ClinVarQueryHelper()
            >>> filter_clause = helper.build_clinical_significance_filter("Pathogenic")
            >>> print(filter_clause)
            FILTER(REGEX(?significance, "Pathogenic", "i"))
        """
        return f'FILTER(REGEX({variable}, "{significance}", "i"))'

    @staticmethod
    def build_gene_pattern(gene_symbol: str, variable: str = "?variant") -> str:
        """
        Build a pattern to match variants in a specific gene.

        Args:
            gene_symbol: Gene symbol (e.g., "BRCA1", "TP53")
            variable: Variable representing the variant

        Returns:
            SPARQL pattern for gene filtering

        Example:
            >>> helper = ClinVarQueryHelper()
            >>> pattern = helper.build_gene_pattern("BRCA1", "?variant")
        """
        return f"""
    {variable} clinvar_vocabulary:hasGene ?gene .
    ?gene clinvar_vocabulary:geneSymbol "{gene_symbol}" .
"""

    @staticmethod
    def build_genomic_location_pattern(
        chromosome: str,
        start: int,
        end: int,
        assembly: str = "GRCh38",
        variable: str = "?variant"
    ) -> str:
        """
        Build a pattern to find variants in a genomic region.

        Args:
            chromosome: Chromosome (e.g., "1", "X", "MT")
            start: Start position
            end: End position
            assembly: Reference assembly (GRCh37 or GRCh38)
            variable: Variable representing the variant

        Returns:
            SPARQL pattern for genomic location

        Example:
            >>> helper = ClinVarQueryHelper()
            >>> pattern = helper.build_genomic_location_pattern("17", 43000000, 43100000)
        """
        return f"""
    {variable} clinvar_vocabulary:chromosome "{chromosome}" ;
              clinvar_vocabulary:assembly "{assembly}" ;
              clinvar_vocabulary:position ?pos .
    FILTER(?pos >= {start} && ?pos <= {end})
"""

    @staticmethod
    def build_phenotype_pattern(phenotype: str, variable: str = "?variant") -> str:
        """
        Build a pattern to match variants associated with a phenotype.

        Args:
            phenotype: Phenotype or disease name
            variable: Variable representing the variant

        Returns:
            SPARQL pattern for phenotype association

        Example:
            >>> helper = ClinVarQueryHelper()
            >>> pattern = helper.build_phenotype_pattern("breast cancer", "?variant")
        """
        return f"""
    {variable} clinvar_vocabulary:hasPhenotype ?phenotype .
    ?phenotype rdfs:label ?phenotypeLabel .
    FILTER(REGEX(?phenotypeLabel, "{phenotype}", "i"))
"""

    @staticmethod
    def build_hgvs_pattern(hgvs_notation: str, variable: str = "?variant") -> str:
        """
        Build a pattern to find variants by HGVS notation.

        Args:
            hgvs_notation: HGVS notation (genomic, coding, or protein)
            variable: Variable representing the variant

        Returns:
            SPARQL pattern for HGVS lookup

        Example:
            >>> helper = ClinVarQueryHelper()
            >>> pattern = helper.build_hgvs_pattern("NM_000059.3:c.68_69del")
        """
        return f"""
    {{
        {variable} clinvar_vocabulary:hgvsGenomic "{hgvs_notation}" .
    }} UNION {{
        {variable} clinvar_vocabulary:hgvsCoding "{hgvs_notation}" .
    }} UNION {{
        {variable} clinvar_vocabulary:hgvsProtein "{hgvs_notation}" .
    }}
"""

    @staticmethod
    def build_review_status_filter(min_stars: int = 1) -> str:
        """
        Build a filter for minimum review status (star rating).

        Args:
            min_stars: Minimum number of stars (0-4)

        Returns:
            SPARQL pattern for review status filtering

        Example:
            >>> helper = ClinVarQueryHelper()
            >>> pattern = helper.build_review_status_filter(2)
        """
        review_statuses = {
            0: "no assertion provided",
            1: "no assertion criteria provided",
            2: "criteria provided, single submitter",
            3: "criteria provided, multiple submitters",
            4: "reviewed by expert panel|practice guideline"
        }

        if min_stars >= 4:
            return '''
    ?variant clinvar_vocabulary:reviewStatus ?reviewStatus .
    FILTER(REGEX(?reviewStatus, "reviewed by expert panel|practice guideline", "i"))
'''
        elif min_stars >= 3:
            return '''
    ?variant clinvar_vocabulary:reviewStatus ?reviewStatus .
    FILTER(REGEX(?reviewStatus, "multiple submitters", "i"))
'''
        elif min_stars >= 2:
            return '''
    ?variant clinvar_vocabulary:reviewStatus ?reviewStatus .
    FILTER(REGEX(?reviewStatus, "criteria provided", "i"))
'''
        else:
            return ""


# =============================================================================
# EXAMPLE QUERIES
# =============================================================================

class ClinVarExampleQueries:
    """
    Collection of example SPARQL queries for the ClinVar endpoint.

    These examples demonstrate common query patterns and best practices
    for retrieving genetic variant information from ClinVar.
    """

    @staticmethod
    def get_variant_by_id(variant_id: str = "VCV000012345") -> str:
        """
        Get detailed information about a specific variant by ClinVar ID.

        Args:
            variant_id: ClinVar Variation ID (VCV or RCV)

        Returns:
            SPARQL query string
        """
        return get_prefix_string() + f"""
SELECT DISTINCT ?variant ?name ?gene ?geneSymbol ?significance ?reviewStatus
WHERE {{
    BIND({ClinVarQueryHelper.resolve_variant_id(variant_id)} AS ?variant)

    ?variant a clinvar_vocabulary:Variant .

    OPTIONAL {{ ?variant clinvar_vocabulary:name ?name . }}
    OPTIONAL {{
        ?variant clinvar_vocabulary:hasGene ?gene .
        ?gene clinvar_vocabulary:geneSymbol ?geneSymbol .
    }}
    OPTIONAL {{ ?variant clinvar_vocabulary:clinicalSignificance ?significance . }}
    OPTIONAL {{ ?variant clinvar_vocabulary:reviewStatus ?reviewStatus . }}
}}
"""

    @staticmethod
    def find_pathogenic_variants_in_gene(gene_symbol: str = "BRCA1", limit: int = 50) -> str:
        """
        Find pathogenic variants in a specific gene.

        Args:
            gene_symbol: Gene symbol (e.g., "BRCA1", "TP53", "CFTR")
            limit: Maximum number of results

        Returns:
            SPARQL query string
        """
        return get_prefix_string() + f"""
SELECT DISTINCT ?variant ?variantName ?hgvs ?significance ?phenotype
WHERE {{
    ?variant a clinvar_vocabulary:Variant ;
            clinvar_vocabulary:hasGene ?gene ;
            clinvar_vocabulary:clinicalSignificance ?significance .

    ?gene clinvar_vocabulary:geneSymbol "{gene_symbol}" .

    FILTER(REGEX(?significance, "Pathogenic", "i"))
    FILTER(!REGEX(?significance, "Benign", "i"))

    OPTIONAL {{ ?variant clinvar_vocabulary:name ?variantName . }}
    OPTIONAL {{ ?variant clinvar_vocabulary:hgvsCoding ?hgvs . }}
    OPTIONAL {{
        ?variant clinvar_vocabulary:hasPhenotype ?phenotypeNode .
        ?phenotypeNode rdfs:label ?phenotype .
    }}
}}
LIMIT {limit}
"""

    @staticmethod
    def search_variants_by_phenotype(phenotype: str = "breast cancer", limit: int = 100) -> str:
        """
        Search for variants associated with a specific phenotype or disease.

        Args:
            phenotype: Phenotype or disease name
            limit: Maximum number of results

        Returns:
            SPARQL query string
        """
        return get_prefix_string() + f"""
SELECT DISTINCT ?variant ?gene ?geneSymbol ?significance ?phenotypeName
WHERE {{
    ?variant a clinvar_vocabulary:Variant ;
            clinvar_vocabulary:hasPhenotype ?phenotype ;
            clinvar_vocabulary:clinicalSignificance ?significance .

    ?phenotype rdfs:label ?phenotypeName .
    FILTER(REGEX(?phenotypeName, "{phenotype}", "i"))

    OPTIONAL {{
        ?variant clinvar_vocabulary:hasGene ?gene .
        ?gene clinvar_vocabulary:geneSymbol ?geneSymbol .
    }}
}}
LIMIT {limit}
"""

    @staticmethod
    def get_variants_in_genomic_region(
        chromosome: str = "17",
        start: int = 43000000,
        end: int = 43100000,
        assembly: str = "GRCh38",
        limit: int = 100
    ) -> str:
        """
        Find variants within a genomic region.

        Args:
            chromosome: Chromosome number or name
            start: Start position (0-based or 1-based depending on source)
            end: End position
            assembly: Reference genome assembly
            limit: Maximum number of results

        Returns:
            SPARQL query string
        """
        return get_prefix_string() + f"""
SELECT DISTINCT ?variant ?position ?ref ?alt ?gene ?significance
WHERE {{
    ?variant a clinvar_vocabulary:Variant ;
            clinvar_vocabulary:chromosome "{chromosome}" ;
            clinvar_vocabulary:assembly "{assembly}" ;
            clinvar_vocabulary:position ?position .

    FILTER(?position >= {start} && ?position <= {end})

    OPTIONAL {{ ?variant clinvar_vocabulary:referenceAllele ?ref . }}
    OPTIONAL {{ ?variant clinvar_vocabulary:alternateAllele ?alt . }}
    OPTIONAL {{
        ?variant clinvar_vocabulary:hasGene ?geneNode .
        ?geneNode clinvar_vocabulary:geneSymbol ?gene .
    }}
    OPTIONAL {{ ?variant clinvar_vocabulary:clinicalSignificance ?significance . }}
}}
ORDER BY ?position
LIMIT {limit}
"""

    @staticmethod
    def get_pharmacogenomic_variants(drug: str = "warfarin", limit: int = 50) -> str:
        """
        Find variants affecting drug response (pharmacogenomics).

        Args:
            drug: Drug name
            limit: Maximum number of results

        Returns:
            SPARQL query string
        """
        return get_prefix_string() + f"""
SELECT DISTINCT ?variant ?gene ?geneSymbol ?significance ?drugResponse ?phenotype
WHERE {{
    ?variant a clinvar_vocabulary:Variant ;
            clinvar_vocabulary:clinicalSignificance ?significance .

    FILTER(REGEX(?significance, "drug response|pharmacogenomic", "i"))

    ?variant clinvar_vocabulary:hasPhenotype ?phenotypeNode .
    ?phenotypeNode rdfs:label ?phenotype .
    FILTER(REGEX(?phenotype, "{drug}", "i"))

    OPTIONAL {{
        ?variant clinvar_vocabulary:hasGene ?gene .
        ?gene clinvar_vocabulary:geneSymbol ?geneSymbol .
    }}

    OPTIONAL {{ ?variant clinvar_vocabulary:interpretation ?drugResponse . }}
}}
LIMIT {limit}
"""

    @staticmethod
    def find_variants_by_clinical_significance(
        significance: str = "Pathogenic",
        min_review_stars: int = 2,
        limit: int = 100
    ) -> str:
        """
        Find variants by clinical significance with minimum review status.

        Args:
            significance: Clinical significance category
            min_review_stars: Minimum review status (0-4 stars)
            limit: Maximum number of results

        Returns:
            SPARQL query string
        """
        return get_prefix_string() + f"""
SELECT DISTINCT ?variant ?gene ?geneSymbol ?significance ?reviewStatus ?phenotype
WHERE {{
    ?variant a clinvar_vocabulary:Variant ;
            clinvar_vocabulary:clinicalSignificance ?significance ;
            clinvar_vocabulary:reviewStatus ?reviewStatus .

    FILTER(REGEX(?significance, "{significance}", "i"))

    {ClinVarQueryHelper.build_review_status_filter(min_review_stars)}

    OPTIONAL {{
        ?variant clinvar_vocabulary:hasGene ?gene .
        ?gene clinvar_vocabulary:geneSymbol ?geneSymbol .
    }}

    OPTIONAL {{
        ?variant clinvar_vocabulary:hasPhenotype ?phenotypeNode .
        ?phenotypeNode rdfs:label ?phenotype .
    }}
}}
LIMIT {limit}
"""

    @staticmethod
    def get_variant_by_hgvs(hgvs: str = "NM_000059.3:c.68_69del") -> str:
        """
        Look up a variant by HGVS nomenclature.

        Args:
            hgvs: HGVS notation (genomic, coding, or protein)

        Returns:
            SPARQL query string
        """
        return get_prefix_string() + f"""
SELECT DISTINCT ?variant ?variantId ?gene ?geneSymbol ?significance ?phenotype
WHERE {{
    ?variant a clinvar_vocabulary:Variant .

    {{
        ?variant clinvar_vocabulary:hgvsGenomic "{hgvs}" .
    }} UNION {{
        ?variant clinvar_vocabulary:hgvsCoding "{hgvs}" .
    }} UNION {{
        ?variant clinvar_vocabulary:hgvsProtein "{hgvs}" .
    }}

    OPTIONAL {{ ?variant clinvar_vocabulary:variantId ?variantId . }}
    OPTIONAL {{
        ?variant clinvar_vocabulary:hasGene ?gene .
        ?gene clinvar_vocabulary:geneSymbol ?geneSymbol .
    }}
    OPTIONAL {{ ?variant clinvar_vocabulary:clinicalSignificance ?significance . }}
    OPTIONAL {{
        ?variant clinvar_vocabulary:hasPhenotype ?phenotypeNode .
        ?phenotypeNode rdfs:label ?phenotype .
    }}
}}
"""

    @staticmethod
    def find_variants_with_conflicting_interpretations(limit: int = 50) -> str:
        """
        Find variants with conflicting clinical interpretations.

        Args:
            limit: Maximum number of results

        Returns:
            SPARQL query string
        """
        return get_prefix_string() + f"""
SELECT DISTINCT ?variant ?gene ?geneSymbol ?significance ?reviewStatus ?phenotype
WHERE {{
    ?variant a clinvar_vocabulary:Variant ;
            clinvar_vocabulary:clinicalSignificance ?significance ;
            clinvar_vocabulary:reviewStatus ?reviewStatus .

    FILTER(REGEX(?significance, "conflicting", "i") ||
           REGEX(?reviewStatus, "conflicting", "i"))

    OPTIONAL {{
        ?variant clinvar_vocabulary:hasGene ?gene .
        ?gene clinvar_vocabulary:geneSymbol ?geneSymbol .
    }}

    OPTIONAL {{
        ?variant clinvar_vocabulary:hasPhenotype ?phenotypeNode .
        ?phenotypeNode rdfs:label ?phenotype .
    }}
}}
LIMIT {limit}
"""

    @staticmethod
    def get_variants_by_molecular_consequence(
        consequence: str = "missense_variant",
        limit: int = 100
    ) -> str:
        """
        Find variants with a specific molecular consequence.

        Args:
            consequence: Molecular consequence (SO term)
            limit: Maximum number of results

        Returns:
            SPARQL query string
        """
        return get_prefix_string() + f"""
SELECT DISTINCT ?variant ?gene ?geneSymbol ?consequence ?significance ?hgvs
WHERE {{
    ?variant a clinvar_vocabulary:Variant ;
            clinvar_vocabulary:molecularConsequence ?consequence .

    FILTER(REGEX(?consequence, "{consequence}", "i"))

    OPTIONAL {{
        ?variant clinvar_vocabulary:hasGene ?gene .
        ?gene clinvar_vocabulary:geneSymbol ?geneSymbol .
    }}
    OPTIONAL {{ ?variant clinvar_vocabulary:clinicalSignificance ?significance . }}
    OPTIONAL {{ ?variant clinvar_vocabulary:hgvsCoding ?hgvs . }}
}}
LIMIT {limit}
"""

    @staticmethod
    def get_variants_by_inheritance_mode(
        mode: str = "Autosomal dominant",
        limit: int = 100
    ) -> str:
        """
        Find variants with a specific mode of inheritance.

        Args:
            mode: Mode of inheritance
            limit: Maximum number of results

        Returns:
            SPARQL query string
        """
        return get_prefix_string() + f"""
SELECT DISTINCT ?variant ?gene ?geneSymbol ?inheritance ?phenotype ?significance
WHERE {{
    ?variant a clinvar_vocabulary:Variant ;
            clinvar_vocabulary:modeOfInheritance ?inheritance .

    FILTER(REGEX(?inheritance, "{mode}", "i"))

    OPTIONAL {{
        ?variant clinvar_vocabulary:hasGene ?gene .
        ?gene clinvar_vocabulary:geneSymbol ?geneSymbol .
    }}
    OPTIONAL {{
        ?variant clinvar_vocabulary:hasPhenotype ?phenotypeNode .
        ?phenotypeNode rdfs:label ?phenotype .
    }}
    OPTIONAL {{ ?variant clinvar_vocabulary:clinicalSignificance ?significance . }}
}}
LIMIT {limit}
"""

    @staticmethod
    def get_cancer_related_variants(
        cancer_type: str = "breast",
        significance: str = "Pathogenic",
        limit: int = 100
    ) -> str:
        """
        Find cancer-related variants with specific clinical significance.

        Args:
            cancer_type: Type of cancer
            significance: Clinical significance
            limit: Maximum number of results

        Returns:
            SPARQL query string
        """
        return get_prefix_string() + f"""
SELECT DISTINCT ?variant ?gene ?geneSymbol ?phenotype ?significance ?hgvs
WHERE {{
    ?variant a clinvar_vocabulary:Variant ;
            clinvar_vocabulary:hasPhenotype ?phenotypeNode ;
            clinvar_vocabulary:clinicalSignificance ?significance .

    ?phenotypeNode rdfs:label ?phenotype .

    FILTER(REGEX(?phenotype, "{cancer_type}", "i") &&
           REGEX(?phenotype, "cancer|carcinoma|tumor", "i"))
    FILTER(REGEX(?significance, "{significance}", "i"))

    OPTIONAL {{
        ?variant clinvar_vocabulary:hasGene ?gene .
        ?gene clinvar_vocabulary:geneSymbol ?geneSymbol .
    }}
    OPTIONAL {{ ?variant clinvar_vocabulary:hgvsCoding ?hgvs . }}
}}
LIMIT {limit}
"""

    @staticmethod
    def get_variants_with_population_frequency(
        max_frequency: float = 0.01,
        significance: str = "Pathogenic",
        limit: int = 50
    ) -> str:
        """
        Find rare pathogenic variants based on population frequency.

        Args:
            max_frequency: Maximum allele frequency (e.g., 0.01 = 1%)
            significance: Clinical significance
            limit: Maximum number of results

        Returns:
            SPARQL query string
        """
        return get_prefix_string() + f"""
SELECT DISTINCT ?variant ?gene ?geneSymbol ?frequency ?significance ?phenotype
WHERE {{
    ?variant a clinvar_vocabulary:Variant ;
            clinvar_vocabulary:alleleFrequency ?frequency ;
            clinvar_vocabulary:clinicalSignificance ?significance .

    FILTER(?frequency <= {max_frequency})
    FILTER(REGEX(?significance, "{significance}", "i"))

    OPTIONAL {{
        ?variant clinvar_vocabulary:hasGene ?gene .
        ?gene clinvar_vocabulary:geneSymbol ?geneSymbol .
    }}
    OPTIONAL {{
        ?variant clinvar_vocabulary:hasPhenotype ?phenotypeNode .
        ?phenotypeNode rdfs:label ?phenotype .
    }}
}}
ORDER BY ?frequency
LIMIT {limit}
"""

    @staticmethod
    def get_gene_disease_associations(gene_symbol: str = "BRCA1") -> str:
        """
        Get all disease associations for a specific gene.

        Args:
            gene_symbol: Gene symbol

        Returns:
            SPARQL query string
        """
        return get_prefix_string() + f"""
SELECT DISTINCT ?gene ?geneSymbol ?phenotype ?variantCount ?pathogenicCount
WHERE {{
    ?gene clinvar_vocabulary:geneSymbol "{gene_symbol}" .

    ?variant clinvar_vocabulary:hasGene ?gene ;
            clinvar_vocabulary:hasPhenotype ?phenotypeNode .

    ?phenotypeNode rdfs:label ?phenotype .

    OPTIONAL {{
        ?gene clinvar_vocabulary:geneSymbol ?geneSymbol .
    }}
}}
GROUP BY ?gene ?geneSymbol ?phenotype
ORDER BY DESC(?variantCount)
"""

    @staticmethod
    def get_variants_with_evidence(
        gene_symbol: str = "TP53",
        min_publications: int = 1,
        limit: int = 50
    ) -> str:
        """
        Find variants with supporting evidence and publications.

        Args:
            gene_symbol: Gene symbol
            min_publications: Minimum number of PubMed citations
            limit: Maximum number of results

        Returns:
            SPARQL query string
        """
        return get_prefix_string() + f"""
SELECT DISTINCT ?variant ?gene ?significance ?reviewStatus ?pubmedId ?evidenceLevel
WHERE {{
    ?variant a clinvar_vocabulary:Variant ;
            clinvar_vocabulary:hasGene ?gene ;
            clinvar_vocabulary:clinicalSignificance ?significance .

    ?gene clinvar_vocabulary:geneSymbol "{gene_symbol}" .

    OPTIONAL {{ ?variant clinvar_vocabulary:reviewStatus ?reviewStatus . }}
    OPTIONAL {{ ?variant clinvar_vocabulary:pubmed ?pubmedId . }}
    OPTIONAL {{ ?variant clinvar_vocabulary:evidenceLevel ?evidenceLevel . }}
}}
LIMIT {limit}
"""

    @staticmethod
    def get_somatic_vs_germline_variants(
        gene_symbol: str = "EGFR",
        variant_origin: str = "somatic",
        limit: int = 100
    ) -> str:
        """
        Find somatic or germline variants in a gene.

        Args:
            gene_symbol: Gene symbol
            variant_origin: "somatic" or "germline"
            limit: Maximum number of results

        Returns:
            SPARQL query string
        """
        return get_prefix_string() + f"""
SELECT DISTINCT ?variant ?origin ?phenotype ?significance ?molecularConsequence
WHERE {{
    ?variant a clinvar_vocabulary:Variant ;
            clinvar_vocabulary:hasGene ?gene ;
            clinvar_vocabulary:variantOrigin ?origin .

    ?gene clinvar_vocabulary:geneSymbol "{gene_symbol}" .

    FILTER(REGEX(?origin, "{variant_origin}", "i"))

    OPTIONAL {{
        ?variant clinvar_vocabulary:hasPhenotype ?phenotypeNode .
        ?phenotypeNode rdfs:label ?phenotype .
    }}
    OPTIONAL {{ ?variant clinvar_vocabulary:clinicalSignificance ?significance . }}
    OPTIONAL {{ ?variant clinvar_vocabulary:molecularConsequence ?molecularConsequence . }}
}}
LIMIT {limit}
"""

    @staticmethod
    def count_variants_by_significance(gene_symbol: Optional[str] = None) -> str:
        """
        Count variants grouped by clinical significance.

        Args:
            gene_symbol: Optional gene symbol to filter

        Returns:
            SPARQL query string
        """
        gene_filter = ""
        if gene_symbol:
            gene_filter = f'''
    ?variant clinvar_vocabulary:hasGene ?gene .
    ?gene clinvar_vocabulary:geneSymbol "{gene_symbol}" .
'''

        return get_prefix_string() + f"""
SELECT ?significance (COUNT(DISTINCT ?variant) AS ?count)
WHERE {{
    ?variant a clinvar_vocabulary:Variant ;
            clinvar_vocabulary:clinicalSignificance ?significance .
    {gene_filter}
}}
GROUP BY ?significance
ORDER BY DESC(?count)
"""


# =============================================================================
# CLINICAL RESEARCH WORKFLOWS
# =============================================================================

CLINICAL_WORKFLOWS = """
Clinical Research Workflows with ClinVar SPARQL Queries
========================================================

1. GENETIC TESTING INTERPRETATION
----------------------------------
Workflow: Interpret variants found in clinical genetic testing

a) Look up variants by genomic coordinates or HGVS notation
b) Check clinical significance and review status
c) Assess allele frequency in populations
d) Review associated phenotypes and inheritance patterns
e) Check for conflicting interpretations
f) Review supporting evidence and publications

Example Genes: BRCA1, BRCA2, TP53, MLH1, MSH2, PTEN, APC, CFTR


2. CANCER GENOMICS RESEARCH
---------------------------
Workflow: Identify actionable cancer variants

a) Find somatic variants in cancer-related genes
b) Filter by pathogenic/likely pathogenic significance
c) Check for drug response associations (pharmacogenomics)
d) Identify variants in specific cancer types
e) Assess molecular consequences (missense, nonsense, etc.)
f) Cross-reference with treatment guidelines

Key Cancer Genes: TP53, EGFR, KRAS, BRAF, PIK3CA, PTEN, BRCA1/2


3. RARE DISEASE DIAGNOSIS
-------------------------
Workflow: Identify causative variants in rare diseases

a) Search variants by rare disease phenotypes
b) Filter by autosomal recessive inheritance
c) Check for compound heterozygotes
d) Assess variant pathogenicity
e) Review HPO phenotype matches
f) Check for de novo variants

Resources: Orphanet, OMIM, HPO, MONDO


4. PHARMACOGENOMICS
------------------
Workflow: Identify variants affecting drug response

a) Search for drug response variants
b) Filter by specific medications
c) Check clinical guidelines (CPIC, PharmGKB)
d) Assess allele frequencies by population
e) Review evidence levels
f) Identify gene-drug pairs

Key Genes: CYP2D6, CYP2C19, CYP3A4, TPMT, DPYD, VKORC1, SLCO1B1


5. CARDIOVASCULAR GENETICS
--------------------------
Workflow: Assess inherited cardiovascular disease risk

a) Find variants in cardiomyopathy genes
b) Check for long QT syndrome variants
c) Assess familial hypercholesterolemia variants
d) Review sudden cardiac death risk
e) Check mode of inheritance
f) Assess penetrance and expressivity

Key Genes: MYH7, MYBPC3, KCNQ1, KCNH2, SCN5A, LDLR, APOB, PCSK9


6. POPULATION GENETICS
---------------------
Workflow: Study variant frequencies across populations

a) Query variants with population frequency data
b) Compare frequencies across ancestries
c) Identify founder mutations
d) Assess pathogenic variant burden
e) Study allelic heterogeneity
f) Analyze geographic distribution


7. VARIANT RECLASSIFICATION
---------------------------
Workflow: Track changes in variant interpretation

a) Find variants with conflicting interpretations
b) Check review status and evidence levels
c) Compare assertions from multiple submitters
d) Track date of last update
e) Review assertion criteria (ACMG guidelines)
f) Identify variants needing reassessment


8. PRENATAL AND CARRIER SCREENING
---------------------------------
Workflow: Assess reproductive genetic risks

a) Identify common carrier screening variants
b) Check for recessive disease variants
c) Assess population-specific risks
d) Review allele frequencies
e) Check for consanguinity-related risks
f) Identify compound heterozygotes

Common Conditions: Cystic fibrosis, Sickle cell disease, Tay-Sachs,
                   Spinal muscular atrophy, Fragile X syndrome
"""


# =============================================================================
# CLINICAL SIGNIFICANCE INTERPRETATION GUIDE
# =============================================================================

CLINICAL_INTERPRETATION_GUIDE = """
ClinVar Clinical Significance Interpretation Guide
===================================================

PATHOGENIC
----------
Definition: Variant is disease-causing
Clinical Action: Typically warrants clinical intervention or genetic counseling
Evidence: Strong evidence from multiple sources
Examples: Known disease-causing mutations, null variants in haploinsufficient genes

LIKELY PATHOGENIC
-----------------
Definition: >90% certainty that variant is disease-causing
Clinical Action: May warrant clinical intervention with appropriate caution
Evidence: Strong but not definitive evidence
Examples: Novel missense in critical domain, de novo in dominant condition

UNCERTAIN SIGNIFICANCE (VUS)
----------------------------
Definition: Insufficient evidence to classify as pathogenic or benign
Clinical Action: Do not use for clinical decision-making
Evidence: Conflicting evidence or lack of data
Note: VUS may be reclassified as more evidence becomes available

LIKELY BENIGN
-------------
Definition: >90% certainty that variant is benign
Clinical Action: Unlikely to be clinically significant
Evidence: Multiple lines of evidence supporting benign impact
Examples: High population frequency, in silico predictions favor benign

BENIGN
------
Definition: Variant is not disease-causing
Clinical Action: No clinical significance
Evidence: Strong evidence of no pathogenic effect
Examples: Common polymorphisms, synonymous variants with no impact

CONFLICTING INTERPRETATIONS
---------------------------
Definition: Different submitters have provided conflicting assessments
Clinical Action: Requires expert review and additional evidence
Note: Often reflects evolving understanding or case-specific factors

DRUG RESPONSE
-------------
Definition: Variant affects drug metabolism, efficacy, or toxicity
Clinical Action: May guide medication selection or dosing
Resources: PharmGKB, CPIC guidelines, FDA labels

RISK FACTOR
-----------
Definition: Variant increases disease risk but is not causative
Clinical Action: Consider in context of other risk factors
Examples: APOE ε4 for Alzheimer's, Factor V Leiden for thrombosis

ASSOCIATION
-----------
Definition: Variant statistically associated with a trait or condition
Clinical Action: Limited clinical utility, research finding
Evidence: GWAS or association studies

PROTECTIVE
----------
Definition: Variant provides protection against disease
Clinical Action: Generally no action needed
Examples: CCR5-Δ32 for HIV resistance


REVIEW STATUS (STAR RATING)
============================

4 STARS: Practice guideline
   - Expert panel consensus
   - Published in professional guidelines
   - Highest level of confidence

3 STARS: Reviewed by expert panel
   - Curated by expert panel (e.g., ClinGen)
   - No conflicts among submissions
   - High confidence

2 STARS: Criteria provided, multiple submitters, no conflicts
   - Multiple independent submissions agreeing
   - All use recognized interpretation criteria
   - Moderate-high confidence

1 STAR: Criteria provided, single submitter OR conflicting
   - Single submission with criteria, or
   - Multiple submissions with conflicts
   - Lower confidence, may need additional review

0 STARS: No assertion criteria provided
   - No interpretation criteria specified
   - Lowest confidence
   - Should not be used for clinical decisions


ACMG/AMP CLASSIFICATION CRITERIA
=================================

Pathogenic/Likely Pathogenic Evidence:
- PVS1: Null variant in haploinsufficient gene
- PS1-4: Strong evidence (functional, segregation, de novo, etc.)
- PM1-6: Moderate evidence (location, allele frequency, predictions, etc.)
- PP1-5: Supporting evidence (cosegregation, computational, phenotype, etc.)

Benign/Likely Benign Evidence:
- BA1: High allele frequency in population
- BS1-4: Strong evidence against pathogenicity
- BP1-7: Supporting evidence for benign impact

Classification Rules:
- Pathogenic: 1 Very Strong + 1 Strong, OR 2 Strong, OR 1 Strong + 3+ Moderate
- Likely Pathogenic: 1 Strong + 1-2 Moderate, OR 3+ Moderate, OR combinations
- Benign: 1 Stand-alone, OR 2+ Strong
- Likely Benign: 1 Strong + 1 Supporting, OR 2+ Supporting


IMPORTANT CLINICAL NOTES
=========================

1. Always verify critical findings with primary literature and databases
2. Consider ethnicity and population-specific allele frequencies
3. Check date of last update - interpretations may change over time
4. Review evidence sources and submitter credentials
5. Consider phenotypic overlap and variable expressivity
6. Assess penetrance and age of onset for genetic counseling
7. Use multi-gene panel results in appropriate clinical context
8. Follow institutional protocols and clinical guidelines
9. Obtain appropriate informed consent for genetic testing
10. Maintain patient privacy and confidentiality (HIPAA, GDPR, etc.)

DISCLAIMER
==========
This information is for research and educational purposes only.
All clinical decisions must be made by qualified healthcare professionals
with appropriate training and credentials. Genetic test results should be
interpreted in the context of personal and family history, clinical findings,
and current medical guidelines.
"""


# =============================================================================
# PERFORMANCE OPTIMIZATION TIPS
# =============================================================================

PERFORMANCE_TIPS = """
Performance Optimization Tips for ClinVar SPARQL Queries
=========================================================

1. USE SPECIFIC IDENTIFIERS
   - Start with gene symbols or variant IDs when known
   - Use genomic coordinates for region queries
   - Specify exact HGVS notation when available
   - Filter by ClinVar IDs (VCV, RCV) for direct lookup

2. FILTER BY CLINICAL SIGNIFICANCE EARLY
   - Apply significance filters at the beginning
   - Focus on Pathogenic/Likely Pathogenic for clinical queries
   - Exclude Benign variants when not needed
   - Use review status filters to improve confidence

3. LIMIT GENOMIC REGIONS
   - Keep genomic region queries under 1 Mb when possible
   - Use gene-based queries instead of large regions
   - Specify exact assembly (GRCh37 vs GRCh38)
   - Consider chromosome-specific queries

4. USE APPROPRIATE LIMITS
   - Always use LIMIT for exploratory queries
   - Start with LIMIT 10-50 for testing
   - Increase gradually based on needs
   - Use pagination for large result sets

5. OPTIMIZE PHENOTYPE QUERIES
   - Use specific disease names rather than broad terms
   - Filter by gene when searching phenotypes
   - Combine with clinical significance filters
   - Use OMIM or HPO IDs when available

6. MINIMIZE OPTIONAL BLOCKS
   - Request only needed data fields
   - Place OPTIONAL patterns after required ones
   - Group related OPTIONAL blocks
   - Consider running separate queries for detailed info

7. USE UNION EFFICIENTLY
   - UNION blocks can be expensive
   - Limit number of UNION alternatives
   - Place filters outside UNION when possible
   - Consider separate queries instead of complex UNIONs

8. LEVERAGE REVIEW STATUS
   - Filter for higher star ratings (2+ stars recommended)
   - Exclude "no assertion" entries when appropriate
   - Focus on expert panel reviews for clinical use
   - Consider "multiple submitters" for confidence

9. POPULATION FREQUENCY FILTERS
   - Apply frequency filters early in query
   - Use appropriate thresholds (e.g., <0.01 for rare)
   - Combine with pathogenicity filters
   - Consider population-specific frequencies

10. AGGREGATE QUERIES CAREFULLY
    - Use COUNT with DISTINCT when needed
    - Group by specific fields to avoid large groupings
    - Consider sampling instead of full aggregation
    - Be cautious with nested aggregations

Example of a well-optimized query:
-----------------------------------
PREFIX clinvar_vocabulary: <http://bio2rdf.org/clinvar_vocabulary:>

SELECT ?variant ?gene ?significance ?hgvs WHERE {
    # Filter by gene first (reduces search space)
    ?variant clinvar_vocabulary:hasGene ?geneNode .
    ?geneNode clinvar_vocabulary:geneSymbol "BRCA1" .

    # Filter by clinical significance early
    ?variant clinvar_vocabulary:clinicalSignificance ?significance .
    FILTER(REGEX(?significance, "Pathogenic", "i"))
    FILTER(!REGEX(?significance, "Benign", "i"))

    # Filter by review status for confidence
    ?variant clinvar_vocabulary:reviewStatus ?reviewStatus .
    FILTER(REGEX(?reviewStatus, "criteria provided", "i"))

    # Then retrieve other properties
    ?variant a clinvar_vocabulary:Variant .

    # Optional fields last
    OPTIONAL { ?variant clinvar_vocabulary:hgvsCoding ?hgvs . }
    OPTIONAL { ?variant clinvar_vocabulary:hasGene ?gene . }
}
LIMIT 50
"""


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    "CLINVAR_ENDPOINT",
    "GT2RDF_ENDPOINT",
    "CLINVAR_PREFIXES",
    "CLINVAR_SCHEMA_INFO",
    "ClinVarSchema",
    "ClinVarQueryHelper",
    "ClinVarExampleQueries",
    "CLINICAL_WORKFLOWS",
    "CLINICAL_INTERPRETATION_GUIDE",
    "PERFORMANCE_TIPS",
    "get_prefix_string",
]
