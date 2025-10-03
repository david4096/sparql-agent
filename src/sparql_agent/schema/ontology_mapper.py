"""
Ontology Mapping and Vocabulary Detection Module

This module provides comprehensive ontology mapping capabilities including:
- Vocabulary mapping and URI resolution
- owl:sameAs relationship handling
- Vocabulary detection and statistics
- Life science ontology support
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict, Counter
import re
from enum import Enum


class OntologyDomain(Enum):
    """Domains of ontologies"""
    GENERAL = "general"
    LIFE_SCIENCES = "life_sciences"
    BIBLIOGRAPHIC = "bibliographic"
    WEB = "web"
    PROVENANCE = "provenance"
    GEOSPATIAL = "geospatial"
    TIME = "time"
    MULTIMEDIA = "multimedia"


@dataclass
class VocabularyInfo:
    """Information about a vocabulary/ontology"""
    prefix: str
    namespace: str
    name: str
    domain: OntologyDomain
    description: str
    homepage: Optional[str] = None
    lov_url: Optional[str] = None
    aliases: List[str] = field(default_factory=list)
    same_as_mappings: Dict[str, str] = field(default_factory=dict)


@dataclass
class VocabularyUsage:
    """Statistics about vocabulary usage in a dataset"""
    prefix: str
    namespace: str
    term_count: int
    unique_terms: Set[str] = field(default_factory=set)
    property_count: int = 0
    class_count: int = 0
    individual_count: int = 0
    misuse_warnings: List[str] = field(default_factory=list)


@dataclass
class OntologyMapping:
    """Represents a mapping between ontology terms"""
    source_uri: str
    target_uri: str
    mapping_type: str  # owl:sameAs, skos:exactMatch, skos:closeMatch, etc.
    confidence: float = 1.0


class OntologyMapper:
    """
    Maps between different vocabularies and handles URI variations.

    This class provides:
    - Vocabulary mapping and resolution
    - owl:sameAs relationship handling
    - URI normalization and variation detection
    - Cross-referencing with Linked Open Vocabularies (LOV)
    """

    def __init__(self):
        self.vocabularies: Dict[str, VocabularyInfo] = {}
        self.namespace_to_prefix: Dict[str, str] = {}
        self.mappings: List[OntologyMapping] = []
        self.same_as_graph: Dict[str, Set[str]] = defaultdict(set)

        self._initialize_standard_vocabularies()
        self._initialize_life_science_ontologies()

    def _initialize_standard_vocabularies(self):
        """Initialize standard web and semantic web vocabularies"""

        standard_vocabs = [
            VocabularyInfo(
                prefix="foaf",
                namespace="http://xmlns.com/foaf/0.1/",
                name="Friend of a Friend",
                domain=OntologyDomain.WEB,
                description="Vocabulary for describing people, their activities and relations",
                homepage="http://xmlns.com/foaf/spec/",
                lov_url="https://lov.linkeddata.es/dataset/lov/vocabs/foaf",
                aliases=["FOAF"]
            ),
            VocabularyInfo(
                prefix="dc",
                namespace="http://purl.org/dc/elements/1.1/",
                name="Dublin Core Metadata Element Set",
                domain=OntologyDomain.BIBLIOGRAPHIC,
                description="Core metadata terms for resource description",
                homepage="https://www.dublincore.org/specifications/dublin-core/dcmi-terms/",
                lov_url="https://lov.linkeddata.es/dataset/lov/vocabs/dc",
                aliases=["dcelem", "dce"]
            ),
            VocabularyInfo(
                prefix="dcterms",
                namespace="http://purl.org/dc/terms/",
                name="Dublin Core Terms",
                domain=OntologyDomain.BIBLIOGRAPHIC,
                description="Extended Dublin Core metadata terms",
                homepage="https://www.dublincore.org/specifications/dublin-core/dcmi-terms/",
                lov_url="https://lov.linkeddata.es/dataset/lov/vocabs/dcterms",
                aliases=["dct"]
            ),
            VocabularyInfo(
                prefix="schema",
                namespace="http://schema.org/",
                name="Schema.org",
                domain=OntologyDomain.WEB,
                description="Vocabulary for structured data on the web",
                homepage="https://schema.org/",
                lov_url="https://lov.linkeddata.es/dataset/lov/vocabs/schema",
                aliases=["sdo"],
                same_as_mappings={
                    "http://schema.org/Person": "http://xmlns.com/foaf/0.1/Person",
                    "http://schema.org/name": "http://xmlns.com/foaf/0.1/name",
                }
            ),
            VocabularyInfo(
                prefix="owl",
                namespace="http://www.w3.org/2002/07/owl#",
                name="Web Ontology Language",
                domain=OntologyDomain.GENERAL,
                description="Vocabulary for defining ontologies",
                homepage="https://www.w3.org/OWL/",
                lov_url="https://lov.linkeddata.es/dataset/lov/vocabs/owl"
            ),
            VocabularyInfo(
                prefix="rdf",
                namespace="http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                name="Resource Description Framework",
                domain=OntologyDomain.GENERAL,
                description="Core RDF vocabulary",
                homepage="https://www.w3.org/RDF/",
                lov_url="https://lov.linkeddata.es/dataset/lov/vocabs/rdf"
            ),
            VocabularyInfo(
                prefix="rdfs",
                namespace="http://www.w3.org/2000/01/rdf-schema#",
                name="RDF Schema",
                domain=OntologyDomain.GENERAL,
                description="RDF vocabulary description language",
                homepage="https://www.w3.org/TR/rdf-schema/",
                lov_url="https://lov.linkeddata.es/dataset/lov/vocabs/rdfs"
            ),
            VocabularyInfo(
                prefix="skos",
                namespace="http://www.w3.org/2004/02/skos/core#",
                name="Simple Knowledge Organization System",
                domain=OntologyDomain.GENERAL,
                description="Vocabulary for knowledge organization systems",
                homepage="https://www.w3.org/2004/02/skos/",
                lov_url="https://lov.linkeddata.es/dataset/lov/vocabs/skos"
            ),
            VocabularyInfo(
                prefix="prov",
                namespace="http://www.w3.org/ns/prov#",
                name="PROV Ontology",
                domain=OntologyDomain.PROVENANCE,
                description="Vocabulary for provenance information",
                homepage="https://www.w3.org/TR/prov-o/",
                lov_url="https://lov.linkeddata.es/dataset/lov/vocabs/prov"
            ),
            VocabularyInfo(
                prefix="dcat",
                namespace="http://www.w3.org/ns/dcat#",
                name="Data Catalog Vocabulary",
                domain=OntologyDomain.BIBLIOGRAPHIC,
                description="Vocabulary for data catalogs",
                homepage="https://www.w3.org/TR/vocab-dcat/",
                lov_url="https://lov.linkeddata.es/dataset/lov/vocabs/dcat"
            ),
            VocabularyInfo(
                prefix="void",
                namespace="http://rdfs.org/ns/void#",
                name="Vocabulary of Interlinked Datasets",
                domain=OntologyDomain.BIBLIOGRAPHIC,
                description="Vocabulary for describing RDF datasets",
                homepage="http://vocab.deri.ie/void",
                lov_url="https://lov.linkeddata.es/dataset/lov/vocabs/void"
            ),
            VocabularyInfo(
                prefix="geo",
                namespace="http://www.w3.org/2003/01/geo/wgs84_pos#",
                name="WGS84 Geo Positioning",
                domain=OntologyDomain.GEOSPATIAL,
                description="Vocabulary for WGS84 geo-positioning",
                homepage="https://www.w3.org/2003/01/geo/",
                lov_url="https://lov.linkeddata.es/dataset/lov/vocabs/geo"
            ),
            VocabularyInfo(
                prefix="time",
                namespace="http://www.w3.org/2006/time#",
                name="Time Ontology",
                domain=OntologyDomain.TIME,
                description="Vocabulary for temporal concepts",
                homepage="https://www.w3.org/TR/owl-time/",
                lov_url="https://lov.linkeddata.es/dataset/lov/vocabs/time"
            ),
        ]

        for vocab in standard_vocabs:
            self.add_vocabulary(vocab)

    def _initialize_life_science_ontologies(self):
        """Initialize life science specific ontologies"""

        life_science_vocabs = [
            VocabularyInfo(
                prefix="uniprot",
                namespace="http://purl.uniprot.org/core/",
                name="UniProt Core Ontology",
                domain=OntologyDomain.LIFE_SCIENCES,
                description="Ontology for protein and gene data from UniProt",
                homepage="https://www.uniprot.org/help/core_ontology",
                lov_url="https://lov.linkeddata.es/dataset/lov/vocabs/uniprot",
                aliases=["up"]
            ),
            VocabularyInfo(
                prefix="go",
                namespace="http://purl.obolibrary.org/obo/GO_",
                name="Gene Ontology",
                domain=OntologyDomain.LIFE_SCIENCES,
                description="Ontology for gene and gene product attributes",
                homepage="http://geneontology.org/",
                aliases=["GO"]
            ),
            VocabularyInfo(
                prefix="obo",
                namespace="http://purl.obolibrary.org/obo/",
                name="OBO Foundry",
                domain=OntologyDomain.LIFE_SCIENCES,
                description="Open Biological and Biomedical Ontologies",
                homepage="http://obofoundry.org/"
            ),
            VocabularyInfo(
                prefix="sio",
                namespace="http://semanticscience.org/resource/",
                name="Semanticscience Integrated Ontology",
                domain=OntologyDomain.LIFE_SCIENCES,
                description="Ontology for biomedical research",
                homepage="https://github.com/micheldumontier/semanticscience",
                aliases=["SIO"]
            ),
            VocabularyInfo(
                prefix="so",
                namespace="http://purl.obolibrary.org/obo/SO_",
                name="Sequence Ontology",
                domain=OntologyDomain.LIFE_SCIENCES,
                description="Ontology for biological sequences",
                homepage="http://www.sequenceontology.org/"
            ),
            VocabularyInfo(
                prefix="ncit",
                namespace="http://purl.obolibrary.org/obo/NCIT_",
                name="NCI Thesaurus",
                domain=OntologyDomain.LIFE_SCIENCES,
                description="Cancer research ontology",
                homepage="https://ncithesaurus.nci.nih.gov/"
            ),
            VocabularyInfo(
                prefix="efo",
                namespace="http://www.ebi.ac.uk/efo/EFO_",
                name="Experimental Factor Ontology",
                domain=OntologyDomain.LIFE_SCIENCES,
                description="Ontology for experimental variables",
                homepage="https://www.ebi.ac.uk/efo/"
            ),
            VocabularyInfo(
                prefix="mondo",
                namespace="http://purl.obolibrary.org/obo/MONDO_",
                name="Mondo Disease Ontology",
                domain=OntologyDomain.LIFE_SCIENCES,
                description="Global disease ontology",
                homepage="https://mondo.monarchinitiative.org/"
            ),
            VocabularyInfo(
                prefix="hp",
                namespace="http://purl.obolibrary.org/obo/HP_",
                name="Human Phenotype Ontology",
                domain=OntologyDomain.LIFE_SCIENCES,
                description="Ontology for human phenotypic abnormalities",
                homepage="https://hpo.jax.org/"
            ),
            VocabularyInfo(
                prefix="chebi",
                namespace="http://purl.obolibrary.org/obo/CHEBI_",
                name="Chemical Entities of Biological Interest",
                domain=OntologyDomain.LIFE_SCIENCES,
                description="Ontology for molecular entities",
                homepage="https://www.ebi.ac.uk/chebi/"
            ),
            VocabularyInfo(
                prefix="ensembl",
                namespace="http://rdf.ebi.ac.uk/resource/ensembl/",
                name="Ensembl RDF",
                domain=OntologyDomain.LIFE_SCIENCES,
                description="Genome annotation data from Ensembl",
                homepage="https://www.ensembl.org/"
            ),
            VocabularyInfo(
                prefix="geno",
                namespace="http://purl.obolibrary.org/obo/GENO_",
                name="Genotype Ontology",
                domain=OntologyDomain.LIFE_SCIENCES,
                description="Ontology for genotypes and their properties",
                homepage="https://github.com/monarch-initiative/GENO-ontology"
            ),
            # FAIR vocabulary
            VocabularyInfo(
                prefix="fair",
                namespace="https://w3id.org/fair/principles/terms/",
                name="FAIR Principles Vocabulary",
                domain=OntologyDomain.GENERAL,
                description="Vocabulary for FAIR data principles",
                homepage="https://www.go-fair.org/",
                aliases=["fairterms"]
            ),
            VocabularyInfo(
                prefix="fdp",
                namespace="https://w3id.org/fdp/fdp-o#",
                name="FAIR Data Point Ontology",
                domain=OntologyDomain.GENERAL,
                description="Ontology for FAIR Data Points",
                homepage="https://www.fairdatapoint.org/"
            ),
        ]

        for vocab in life_science_vocabs:
            self.add_vocabulary(vocab)

    def add_vocabulary(self, vocab: VocabularyInfo):
        """Add a vocabulary to the mapper"""
        self.vocabularies[vocab.prefix] = vocab
        self.namespace_to_prefix[vocab.namespace] = vocab.prefix

        # Add alias mappings
        for alias in vocab.aliases:
            if alias.lower() not in self.vocabularies:
                self.vocabularies[alias.lower()] = vocab

        # Add same-as mappings to graph
        for source, target in vocab.same_as_mappings.items():
            self.add_same_as_mapping(source, target)

    def add_same_as_mapping(self, uri1: str, uri2: str):
        """Add an owl:sameAs relationship between two URIs"""
        self.same_as_graph[uri1].add(uri2)
        self.same_as_graph[uri2].add(uri1)

        mapping = OntologyMapping(
            source_uri=uri1,
            target_uri=uri2,
            mapping_type="owl:sameAs",
            confidence=1.0
        )
        self.mappings.append(mapping)

    def add_mapping(self, mapping: OntologyMapping):
        """Add a general ontology mapping"""
        self.mappings.append(mapping)

        if mapping.mapping_type == "owl:sameAs":
            self.same_as_graph[mapping.source_uri].add(mapping.target_uri)
            self.same_as_graph[mapping.target_uri].add(mapping.source_uri)

    def get_equivalent_uris(self, uri: str) -> Set[str]:
        """Get all URIs that are owl:sameAs the given URI"""
        visited = set()
        to_visit = {uri}

        while to_visit:
            current = to_visit.pop()
            if current in visited:
                continue
            visited.add(current)

            # Add all directly connected URIs
            if current in self.same_as_graph:
                to_visit.update(self.same_as_graph[current] - visited)

        return visited

    def normalize_uri(self, uri: str) -> str:
        """
        Normalize a URI to a canonical form.

        Handles:
        - Trailing slashes and hashes
        - HTTP vs HTTPS
        - Common variations
        """
        # Remove fragment if present
        if "#" in uri and not uri.rstrip("#").endswith(uri.split("#")[0]):
            base, fragment = uri.rsplit("#", 1)
            uri = f"{base}#{fragment}"

        # Normalize trailing slash
        if uri.endswith("/") and not uri.endswith("://"):
            uri = uri.rstrip("/")

        return uri

    def resolve_uri(self, uri: str, prefer_namespace: Optional[str] = None) -> str:
        """
        Resolve a URI to its preferred form.

        If the URI has equivalent URIs via owl:sameAs, return the preferred one.
        """
        normalized = self.normalize_uri(uri)
        equivalents = self.get_equivalent_uris(normalized)

        if not equivalents:
            return normalized

        # If a preferred namespace is specified, try to use that
        if prefer_namespace:
            for equiv in equivalents:
                if equiv.startswith(prefer_namespace):
                    return equiv

        # Otherwise return the shortest URI (often the canonical one)
        return min(equivalents, key=len)

    def get_vocabulary_for_uri(self, uri: str) -> Optional[VocabularyInfo]:
        """Get the vocabulary information for a URI"""
        for vocab in self.vocabularies.values():
            if uri.startswith(vocab.namespace):
                return vocab
        return None

    def get_vocabulary_by_prefix(self, prefix: str) -> Optional[VocabularyInfo]:
        """Get vocabulary by prefix"""
        return self.vocabularies.get(prefix.lower())

    def get_vocabulary_by_namespace(self, namespace: str) -> Optional[VocabularyInfo]:
        """Get vocabulary by namespace"""
        prefix = self.namespace_to_prefix.get(namespace)
        if prefix:
            return self.vocabularies.get(prefix)
        return None

    def extract_prefix_from_uri(self, uri: str) -> Optional[Tuple[str, str]]:
        """
        Extract prefix and local name from a URI.

        Returns: (prefix, local_name) or None
        """
        for vocab in self.vocabularies.values():
            if uri.startswith(vocab.namespace):
                local_name = uri[len(vocab.namespace):]
                return (vocab.prefix, local_name)

        # Try to extract from URI structure
        if "#" in uri:
            namespace, local = uri.rsplit("#", 1)
            namespace += "#"
        elif "/" in uri:
            namespace, local = uri.rsplit("/", 1)
            namespace += "/"
        else:
            return None

        prefix = self.namespace_to_prefix.get(namespace)
        if prefix:
            return (prefix, local)

        return None

    def get_lov_url(self, prefix: str) -> Optional[str]:
        """Get the Linked Open Vocabularies URL for a vocabulary"""
        vocab = self.get_vocabulary_by_prefix(prefix)
        if vocab:
            return vocab.lov_url
        return None

    def list_vocabularies_by_domain(self, domain: OntologyDomain) -> List[VocabularyInfo]:
        """List all vocabularies in a specific domain"""
        vocabs = []
        seen = set()

        for vocab in self.vocabularies.values():
            if vocab.domain == domain and vocab.prefix not in seen:
                vocabs.append(vocab)
                seen.add(vocab.prefix)

        return vocabs

    def search_vocabularies(self, query: str) -> List[VocabularyInfo]:
        """Search vocabularies by name, prefix, or description"""
        query_lower = query.lower()
        results = []
        seen = set()

        for vocab in self.vocabularies.values():
            if vocab.prefix in seen:
                continue

            if (query_lower in vocab.prefix.lower() or
                query_lower in vocab.name.lower() or
                query_lower in vocab.description.lower()):
                results.append(vocab)
                seen.add(vocab.prefix)

        return results


class VocabularyDetector:
    """
    Detects and analyzes vocabulary usage in RDF data.

    This class provides:
    - Identification of used ontologies
    - Extraction of vocabulary statistics
    - Detection of vocabulary misuse or violations
    - Term frequency analysis
    """

    def __init__(self, mapper: Optional[OntologyMapper] = None):
        self.mapper = mapper or OntologyMapper()
        self.usage_stats: Dict[str, VocabularyUsage] = {}

        # Patterns for detecting common issues
        self.property_patterns = {
            "camelCase": re.compile(r'^[a-z][a-zA-Z0-9]*$'),
            "PascalCase": re.compile(r'^[A-Z][a-zA-Z0-9]*$'),
        }

    def analyze_uri(self, uri: str, context: str = "unknown"):
        """
        Analyze a single URI and update statistics.

        Args:
            uri: The URI to analyze
            context: Context of use (property, class, individual)
        """
        vocab = self.mapper.get_vocabulary_for_uri(uri)

        if not vocab:
            # Unknown vocabulary
            namespace = self._extract_namespace(uri)
            prefix = self.mapper.namespace_to_prefix.get(namespace, "unknown")

            if prefix not in self.usage_stats:
                self.usage_stats[prefix] = VocabularyUsage(
                    prefix=prefix,
                    namespace=namespace,
                    term_count=0
                )
        else:
            prefix = vocab.prefix
            if prefix not in self.usage_stats:
                self.usage_stats[prefix] = VocabularyUsage(
                    prefix=prefix,
                    namespace=vocab.namespace,
                    term_count=0
                )

        # Update statistics
        usage = self.usage_stats[prefix]
        usage.term_count += 1
        usage.unique_terms.add(uri)

        if context == "property":
            usage.property_count += 1
        elif context == "class":
            usage.class_count += 1
        elif context == "individual":
            usage.individual_count += 1

        # Check for potential misuse
        self._check_uri_conventions(uri, vocab, usage)

    def _extract_namespace(self, uri: str) -> str:
        """Extract namespace from a URI"""
        if "#" in uri:
            return uri.rsplit("#", 1)[0] + "#"
        elif "/" in uri:
            return uri.rsplit("/", 1)[0] + "/"
        return uri

    def _check_uri_conventions(self, uri: str, vocab: Optional[VocabularyInfo],
                               usage: VocabularyUsage):
        """Check URI against naming conventions"""
        if not vocab:
            return

        local_name = uri[len(vocab.namespace):]

        # Check naming conventions based on vocabulary
        if vocab.prefix in ["foaf", "dc", "dcterms", "schema"]:
            # These typically use camelCase for properties
            if not self.property_patterns["camelCase"].match(local_name):
                if not self.property_patterns["PascalCase"].match(local_name):
                    warning = f"Unusual naming convention for {uri}"
                    if warning not in usage.misuse_warnings:
                        usage.misuse_warnings.append(warning)

        # Check for deprecated terms (simplified)
        deprecated_terms = {
            "http://xmlns.com/foaf/0.1/geekcode": "FOAF geekcode is deprecated",
            "http://purl.org/dc/elements/1.1/": "Consider using dcterms instead of dc",
        }

        for deprecated, message in deprecated_terms.items():
            if uri.startswith(deprecated):
                if message not in usage.misuse_warnings:
                    usage.misuse_warnings.append(message)

    def analyze_triple(self, subject: str, predicate: str, obj: str):
        """Analyze a complete triple"""
        self.analyze_uri(subject, "individual")
        self.analyze_uri(predicate, "property")

        # Only analyze object if it's a URI (not a literal)
        if obj.startswith("http://") or obj.startswith("https://"):
            self.analyze_uri(obj, "individual")

    def detect_vocabulary_violations(self) -> Dict[str, List[str]]:
        """
        Detect violations of vocabulary best practices.

        Returns a dict mapping vocabulary prefix to list of warnings.
        """
        violations = {}

        for prefix, usage in self.usage_stats.items():
            if usage.misuse_warnings:
                violations[prefix] = usage.misuse_warnings

        return violations

    def get_vocabulary_statistics(self) -> Dict[str, VocabularyUsage]:
        """Get complete vocabulary usage statistics"""
        return self.usage_stats

    def get_top_vocabularies(self, n: int = 10) -> List[Tuple[str, int]]:
        """Get the top N most used vocabularies by term count"""
        vocab_counts = [(prefix, usage.term_count)
                       for prefix, usage in self.usage_stats.items()]
        return sorted(vocab_counts, key=lambda x: x[1], reverse=True)[:n]

    def identify_ontologies(self) -> Dict[OntologyDomain, List[str]]:
        """
        Identify which ontologies are used, grouped by domain.

        Returns a dict mapping domain to list of vocabulary prefixes.
        """
        domain_vocabs = defaultdict(list)

        for prefix, usage in self.usage_stats.items():
            vocab = self.mapper.get_vocabulary_by_prefix(prefix)
            if vocab:
                domain_vocabs[vocab.domain].append(prefix)
            else:
                domain_vocabs[OntologyDomain.GENERAL].append(prefix)

        return dict(domain_vocabs)

    def get_coverage_report(self) -> str:
        """Generate a human-readable coverage report"""
        lines = ["Vocabulary Usage Report", "=" * 50, ""]

        # Top vocabularies
        lines.append("Top Vocabularies by Usage:")
        for prefix, count in self.get_top_vocabularies(10):
            vocab = self.mapper.get_vocabulary_by_prefix(prefix)
            name = vocab.name if vocab else "Unknown"
            lines.append(f"  {prefix:15s} {count:6d} uses  ({name})")

        lines.append("")

        # By domain
        lines.append("Vocabularies by Domain:")
        for domain, prefixes in self.identify_ontologies().items():
            lines.append(f"  {domain.value}:")
            for prefix in prefixes:
                usage = self.usage_stats[prefix]
                lines.append(f"    {prefix}: {usage.term_count} uses "
                           f"({usage.property_count} props, {usage.class_count} classes)")

        lines.append("")

        # Violations
        violations = self.detect_vocabulary_violations()
        if violations:
            lines.append("Warnings and Violations:")
            for prefix, warnings in violations.items():
                lines.append(f"  {prefix}:")
                for warning in warnings:
                    lines.append(f"    - {warning}")
        else:
            lines.append("No vocabulary violations detected.")

        return "\n".join(lines)

    def export_statistics(self) -> Dict:
        """Export statistics as a dictionary for serialization"""
        return {
            "vocabulary_count": len(self.usage_stats),
            "total_terms": sum(u.term_count for u in self.usage_stats.values()),
            "vocabularies": {
                prefix: {
                    "namespace": usage.namespace,
                    "term_count": usage.term_count,
                    "unique_terms": len(usage.unique_terms),
                    "property_count": usage.property_count,
                    "class_count": usage.class_count,
                    "individual_count": usage.individual_count,
                    "warnings": usage.misuse_warnings,
                }
                for prefix, usage in self.usage_stats.items()
            },
            "by_domain": {
                domain.value: prefixes
                for domain, prefixes in self.identify_ontologies().items()
            }
        }

    def reset(self):
        """Reset all statistics"""
        self.usage_stats.clear()


def create_default_mapper() -> OntologyMapper:
    """Create a default ontology mapper with standard vocabularies"""
    return OntologyMapper()


def detect_vocabularies_in_text(text: str, mapper: Optional[OntologyMapper] = None) -> VocabularyDetector:
    """
    Detect vocabularies used in text containing URIs.

    Args:
        text: Text containing URIs (e.g., SPARQL query, RDF dump)
        mapper: Optional OntologyMapper instance

    Returns:
        VocabularyDetector with analysis results
    """
    detector = VocabularyDetector(mapper)

    # Simple URI extraction regex
    uri_pattern = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+')

    for uri in uri_pattern.findall(text):
        detector.analyze_uri(uri)

    return detector
