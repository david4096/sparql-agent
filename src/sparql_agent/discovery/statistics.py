"""
Dataset Statistics and Introspection Module

Provides efficient collection and analysis of SPARQL dataset statistics,
including triple counts, class distributions, property usage, and pattern detection.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from datetime import datetime
import time
from collections import defaultdict

from SPARQLWrapper import SPARQLWrapper, JSON
from SPARQLWrapper.SPARQLExceptions import SPARQLWrapperException


logger = logging.getLogger(__name__)


@dataclass
class DatasetStatistics:
    """Container for dataset statistics."""

    # Basic counts
    total_triples: int = 0
    distinct_subjects: int = 0
    distinct_predicates: int = 0
    distinct_objects: int = 0

    # Class statistics
    total_classes: int = 0
    top_classes: List[Tuple[str, int]] = field(default_factory=list)

    # Property statistics
    total_properties: int = 0
    top_properties: List[Tuple[str, int]] = field(default_factory=list)

    # Type statistics
    typed_resources: int = 0
    untyped_resources: int = 0

    # Literal statistics
    total_literals: int = 0
    datatype_distribution: Dict[str, int] = field(default_factory=dict)
    language_distribution: Dict[str, int] = field(default_factory=dict)

    # Graph statistics
    named_graphs: List[str] = field(default_factory=list)
    graph_sizes: Dict[str, int] = field(default_factory=dict)

    # Namespace statistics
    namespace_usage: Dict[str, int] = field(default_factory=dict)

    # Patterns
    detected_patterns: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    endpoint_url: str = ""
    collection_time: str = ""
    collection_duration_seconds: float = 0.0
    query_timeout_seconds: int = 30

    def to_dict(self) -> Dict[str, Any]:
        """Convert statistics to dictionary."""
        return {
            'basic_counts': {
                'total_triples': self.total_triples,
                'distinct_subjects': self.distinct_subjects,
                'distinct_predicates': self.distinct_predicates,
                'distinct_objects': self.distinct_objects,
            },
            'classes': {
                'total_classes': self.total_classes,
                'top_classes': self.top_classes,
            },
            'properties': {
                'total_properties': self.total_properties,
                'top_properties': self.top_properties,
            },
            'types': {
                'typed_resources': self.typed_resources,
                'untyped_resources': self.untyped_resources,
            },
            'literals': {
                'total_literals': self.total_literals,
                'datatype_distribution': self.datatype_distribution,
                'language_distribution': self.language_distribution,
            },
            'graphs': {
                'named_graphs': self.named_graphs,
                'graph_sizes': self.graph_sizes,
            },
            'namespaces': self.namespace_usage,
            'patterns': self.detected_patterns,
            'metadata': {
                'endpoint_url': self.endpoint_url,
                'collection_time': self.collection_time,
                'collection_duration_seconds': self.collection_duration_seconds,
                'query_timeout_seconds': self.query_timeout_seconds,
            }
        }

    def summary(self) -> str:
        """Generate a human-readable summary."""
        lines = [
            "=" * 60,
            "SPARQL Dataset Statistics Summary",
            "=" * 60,
            f"Endpoint: {self.endpoint_url}",
            f"Collected: {self.collection_time}",
            f"Duration: {self.collection_duration_seconds:.2f}s",
            "",
            "Basic Counts:",
            f"  Total Triples: {self.total_triples:,}",
            f"  Distinct Subjects: {self.distinct_subjects:,}",
            f"  Distinct Predicates: {self.distinct_predicates:,}",
            f"  Distinct Objects: {self.distinct_objects:,}",
            "",
        ]

        if self.top_classes:
            lines.extend([
                f"Top {len(self.top_classes)} Classes:",
                *[f"  {i+1}. {cls} ({count:,} instances)"
                  for i, (cls, count) in enumerate(self.top_classes[:10])],
                "",
            ])

        if self.top_properties:
            lines.extend([
                f"Top {len(self.top_properties)} Properties:",
                *[f"  {i+1}. {prop} ({count:,} uses)"
                  for i, (prop, count) in enumerate(self.top_properties[:10])],
                "",
            ])

        if self.typed_resources or self.untyped_resources:
            lines.extend([
                "Type Information:",
                f"  Typed Resources: {self.typed_resources:,}",
                f"  Untyped Resources: {self.untyped_resources:,}",
                "",
            ])

        if self.total_literals:
            lines.extend([
                "Literal Statistics:",
                f"  Total Literals: {self.total_literals:,}",
            ])
            if self.datatype_distribution:
                lines.append("  Datatype Distribution:")
                for dtype, count in sorted(self.datatype_distribution.items(),
                                          key=lambda x: x[1], reverse=True)[:5]:
                    lines.append(f"    {dtype}: {count:,}")
            if self.language_distribution:
                lines.append("  Language Distribution:")
                for lang, count in sorted(self.language_distribution.items(),
                                         key=lambda x: x[1], reverse=True)[:5]:
                    lines.append(f"    {lang}: {count:,}")
            lines.append("")

        if self.named_graphs:
            lines.extend([
                f"Named Graphs: {len(self.named_graphs)}",
                *[f"  {graph}: {self.graph_sizes.get(graph, 0):,} triples"
                  for graph in self.named_graphs[:5]],
                "",
            ])

        if self.namespace_usage:
            lines.extend([
                "Top Namespaces:",
                *[f"  {ns}: {count:,} uses"
                  for ns, count in sorted(self.namespace_usage.items(),
                                        key=lambda x: x[1], reverse=True)[:10]],
                "",
            ])

        if self.detected_patterns:
            lines.extend([
                "Detected Patterns:",
                *[f"  {pattern}: {value}"
                  for pattern, value in self.detected_patterns.items()],
                "",
            ])

        lines.append("=" * 60)
        return "\n".join(lines)


class StatisticsCollector:
    """
    Efficient collector for SPARQL dataset statistics.

    Provides methods to gather comprehensive statistics about a SPARQL endpoint
    including counts, distributions, and pattern detection with caching and
    progress reporting.
    """

    def __init__(
        self,
        endpoint_url: str,
        timeout: int = 30,
        max_retries: int = 3,
        cache_results: bool = True,
        progress_callback: Optional[callable] = None
    ):
        """
        Initialize the statistics collector.

        Args:
            endpoint_url: SPARQL endpoint URL
            timeout: Query timeout in seconds
            max_retries: Maximum number of retries for failed queries
            cache_results: Whether to cache query results
            progress_callback: Optional callback for progress reporting
        """
        self.endpoint_url = endpoint_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.cache_results = cache_results
        self.progress_callback = progress_callback

        self.sparql = SPARQLWrapper(endpoint_url)
        self.sparql.setTimeout(timeout)
        self.sparql.setReturnFormat(JSON)

        self._cache: Dict[str, Any] = {}
        self._query_count = 0
        self._failed_queries: List[str] = []

    def _report_progress(self, message: str, current: int = 0, total: int = 0):
        """Report progress to callback if available."""
        if self.progress_callback:
            self.progress_callback(message, current, total)
        else:
            if total > 0:
                logger.info(f"{message} ({current}/{total})")
            else:
                logger.info(message)

    def _execute_query(
        self,
        query: str,
        cache_key: Optional[str] = None,
        retry_count: int = 0
    ) -> Optional[Dict]:
        """
        Execute a SPARQL query with caching and retry logic.

        Args:
            query: SPARQL query string
            cache_key: Optional key for caching results
            retry_count: Current retry attempt

        Returns:
            Query results as dictionary or None if failed
        """
        # Check cache
        if cache_key and self.cache_results and cache_key in self._cache:
            logger.debug(f"Using cached result for: {cache_key}")
            return self._cache[cache_key]

        try:
            self._query_count += 1
            logger.debug(f"Executing query #{self._query_count}: {query[:100]}...")

            self.sparql.setQuery(query)
            results = self.sparql.queryAndConvert()

            # Cache results
            if cache_key and self.cache_results:
                self._cache[cache_key] = results

            return results

        except SPARQLWrapperException as e:
            logger.warning(f"Query failed (attempt {retry_count + 1}): {str(e)[:200]}")

            if retry_count < self.max_retries:
                time.sleep(2 ** retry_count)  # Exponential backoff
                return self._execute_query(query, cache_key, retry_count + 1)
            else:
                self._failed_queries.append(query[:200])
                logger.error(f"Query failed after {self.max_retries} retries")
                return None

        except Exception as e:
            logger.error(f"Unexpected error executing query: {str(e)}")
            self._failed_queries.append(query[:200])
            return None

    def _extract_single_value(self, results: Optional[Dict], var_name: str) -> int:
        """Extract a single integer value from query results."""
        if not results or 'results' not in results:
            return 0

        bindings = results['results']['bindings']
        if not bindings or var_name not in bindings[0]:
            return 0

        try:
            return int(bindings[0][var_name]['value'])
        except (ValueError, KeyError, IndexError):
            return 0

    def _extract_counts(
        self,
        results: Optional[Dict],
        key_var: str,
        count_var: str
    ) -> List[Tuple[str, int]]:
        """Extract key-count pairs from query results."""
        if not results or 'results' not in results:
            return []

        items = []
        for binding in results['results']['bindings']:
            try:
                key = binding[key_var]['value']
                count = int(binding[count_var]['value'])
                items.append((key, count))
            except (ValueError, KeyError):
                continue

        return items

    def count_total_triples(self) -> int:
        """
        Count total triples in the dataset efficiently.

        Returns:
            Total number of triples
        """
        self._report_progress("Counting total triples...")

        query = "SELECT (COUNT(*) AS ?triples) WHERE { ?s ?p ?o }"
        results = self._execute_query(query, cache_key="total_triples")

        count = self._extract_single_value(results, "triples")
        logger.info(f"Total triples: {count:,}")
        return count

    def count_distinct_subjects(self) -> int:
        """Count distinct subjects in the dataset."""
        self._report_progress("Counting distinct subjects...")

        query = "SELECT (COUNT(DISTINCT ?s) AS ?count) WHERE { ?s ?p ?o }"
        results = self._execute_query(query, cache_key="distinct_subjects")

        count = self._extract_single_value(results, "count")
        logger.info(f"Distinct subjects: {count:,}")
        return count

    def count_distinct_predicates(self) -> int:
        """Count distinct predicates in the dataset."""
        self._report_progress("Counting distinct predicates...")

        query = "SELECT (COUNT(DISTINCT ?p) AS ?count) WHERE { ?s ?p ?o }"
        results = self._execute_query(query, cache_key="distinct_predicates")

        count = self._extract_single_value(results, "count")
        logger.info(f"Distinct predicates: {count:,}")
        return count

    def count_distinct_objects(self) -> int:
        """Count distinct objects in the dataset."""
        self._report_progress("Counting distinct objects...")

        query = "SELECT (COUNT(DISTINCT ?o) AS ?count) WHERE { ?s ?p ?o }"
        results = self._execute_query(query, cache_key="distinct_objects")

        count = self._extract_single_value(results, "count")
        logger.info(f"Distinct objects: {count:,}")
        return count

    def get_top_classes(self, limit: int = 20) -> List[Tuple[str, int]]:
        """
        Find the most common classes in the dataset.

        Args:
            limit: Maximum number of classes to return

        Returns:
            List of (class_uri, instance_count) tuples
        """
        self._report_progress(f"Finding top {limit} classes...")

        query = f"""
        SELECT ?class (COUNT(?s) AS ?count)
        WHERE {{
            ?s a ?class
        }}
        GROUP BY ?class
        ORDER BY DESC(?count)
        LIMIT {limit}
        """

        results = self._execute_query(query, cache_key=f"top_classes_{limit}")
        classes = self._extract_counts(results, "class", "count")

        logger.info(f"Found {len(classes)} top classes")
        return classes

    def get_top_properties(self, limit: int = 20) -> List[Tuple[str, int]]:
        """
        Find the most frequently used properties in the dataset.

        Args:
            limit: Maximum number of properties to return

        Returns:
            List of (property_uri, usage_count) tuples
        """
        self._report_progress(f"Finding top {limit} properties...")

        query = f"""
        SELECT ?property (COUNT(*) AS ?count)
        WHERE {{
            ?s ?property ?o
        }}
        GROUP BY ?property
        ORDER BY DESC(?count)
        LIMIT {limit}
        """

        results = self._execute_query(query, cache_key=f"top_properties_{limit}")
        properties = self._extract_counts(results, "property", "count")

        logger.info(f"Found {len(properties)} top properties")
        return properties

    def count_typed_resources(self) -> int:
        """Count resources that have at least one rdf:type."""
        self._report_progress("Counting typed resources...")

        query = "SELECT (COUNT(DISTINCT ?s) AS ?count) WHERE { ?s a ?type }"
        results = self._execute_query(query, cache_key="typed_resources")

        count = self._extract_single_value(results, "count")
        logger.info(f"Typed resources: {count:,}")
        return count

    def count_untyped_resources(self) -> int:
        """Count resources that have no rdf:type (approximation)."""
        self._report_progress("Counting untyped resources...")

        # This is an approximation - count subjects not appearing with rdf:type
        query = """
        SELECT (COUNT(DISTINCT ?s) AS ?count)
        WHERE {
            ?s ?p ?o
            FILTER NOT EXISTS { ?s a ?type }
        }
        """

        results = self._execute_query(query, cache_key="untyped_resources")

        count = self._extract_single_value(results, "count")
        logger.info(f"Untyped resources: {count:,}")
        return count

    def count_literals(self) -> int:
        """Count total number of literals in the dataset."""
        self._report_progress("Counting literals...")

        query = """
        SELECT (COUNT(*) AS ?count)
        WHERE {
            ?s ?p ?o
            FILTER(isLiteral(?o))
        }
        """

        results = self._execute_query(query, cache_key="total_literals")

        count = self._extract_single_value(results, "count")
        logger.info(f"Total literals: {count:,}")
        return count

    def get_datatype_distribution(self, limit: int = 20) -> Dict[str, int]:
        """
        Get distribution of literal datatypes.

        Args:
            limit: Maximum number of datatypes to return

        Returns:
            Dictionary mapping datatype URI to count
        """
        self._report_progress("Analyzing datatype distribution...")

        query = f"""
        SELECT ?datatype (COUNT(*) AS ?count)
        WHERE {{
            ?s ?p ?o
            FILTER(isLiteral(?o))
            BIND(DATATYPE(?o) AS ?datatype)
        }}
        GROUP BY ?datatype
        ORDER BY DESC(?count)
        LIMIT {limit}
        """

        results = self._execute_query(query, cache_key=f"datatype_dist_{limit}")

        distribution = {}
        if results and 'results' in results:
            for binding in results['results']['bindings']:
                try:
                    datatype = binding.get('datatype', {}).get('value', 'unknown')
                    count = int(binding['count']['value'])
                    distribution[datatype] = count
                except (ValueError, KeyError):
                    continue

        logger.info(f"Found {len(distribution)} datatypes")
        return distribution

    def get_language_distribution(self, limit: int = 20) -> Dict[str, int]:
        """
        Get distribution of language tags in literals.

        Args:
            limit: Maximum number of languages to return

        Returns:
            Dictionary mapping language tag to count
        """
        self._report_progress("Analyzing language distribution...")

        query = f"""
        SELECT ?lang (COUNT(*) AS ?count)
        WHERE {{
            ?s ?p ?o
            FILTER(isLiteral(?o))
            BIND(LANG(?o) AS ?lang)
            FILTER(?lang != "")
        }}
        GROUP BY ?lang
        ORDER BY DESC(?count)
        LIMIT {limit}
        """

        results = self._execute_query(query, cache_key=f"language_dist_{limit}")

        distribution = {}
        if results and 'results' in results:
            for binding in results['results']['bindings']:
                try:
                    lang = binding['lang']['value']
                    count = int(binding['count']['value'])
                    distribution[lang] = count
                except (ValueError, KeyError):
                    continue

        logger.info(f"Found {len(distribution)} languages")
        return distribution

    def get_named_graphs(self) -> List[str]:
        """
        Get list of named graphs in the dataset.

        Returns:
            List of named graph URIs
        """
        self._report_progress("Finding named graphs...")

        query = "SELECT DISTINCT ?g WHERE { GRAPH ?g { ?s ?p ?o } }"
        results = self._execute_query(query, cache_key="named_graphs")

        graphs = []
        if results and 'results' in results:
            for binding in results['results']['bindings']:
                try:
                    graph = binding['g']['value']
                    graphs.append(graph)
                except KeyError:
                    continue

        logger.info(f"Found {len(graphs)} named graphs")
        return graphs

    def get_graph_sizes(self, graphs: List[str]) -> Dict[str, int]:
        """
        Get triple counts for named graphs.

        Args:
            graphs: List of graph URIs to measure

        Returns:
            Dictionary mapping graph URI to triple count
        """
        sizes = {}
        total = len(graphs)

        for i, graph in enumerate(graphs):
            self._report_progress(f"Measuring graph size: {graph}", i + 1, total)

            query = f"""
            SELECT (COUNT(*) AS ?count)
            WHERE {{
                GRAPH <{graph}> {{ ?s ?p ?o }}
            }}
            """

            results = self._execute_query(query, cache_key=f"graph_size_{graph}")
            count = self._extract_single_value(results, "count")
            sizes[graph] = count

        return sizes

    def analyze_namespace_usage(self) -> Dict[str, int]:
        """
        Analyze namespace usage across all predicates.

        Returns:
            Dictionary mapping namespace to usage count
        """
        self._report_progress("Analyzing namespace usage...")

        # Get all predicates and their counts
        query = """
        SELECT ?p (COUNT(*) AS ?count)
        WHERE { ?s ?p ?o }
        GROUP BY ?p
        """

        results = self._execute_query(query, cache_key="all_predicates")

        namespace_counts = defaultdict(int)

        if results and 'results' in results:
            for binding in results['results']['bindings']:
                try:
                    predicate = binding['p']['value']
                    count = int(binding['count']['value'])

                    # Extract namespace (everything before # or last /)
                    if '#' in predicate:
                        namespace = predicate.rsplit('#', 1)[0] + '#'
                    else:
                        namespace = predicate.rsplit('/', 1)[0] + '/'

                    namespace_counts[namespace] += count

                except (ValueError, KeyError):
                    continue

        logger.info(f"Found {len(namespace_counts)} namespaces")
        return dict(namespace_counts)

    def detect_patterns(self) -> Dict[str, Any]:
        """
        Detect common patterns in the dataset.

        Returns:
            Dictionary of detected patterns and their characteristics
        """
        self._report_progress("Detecting patterns...")

        patterns = {}

        # Check for OWL ontology patterns
        query = """
        SELECT (COUNT(*) AS ?count)
        WHERE {
            { ?s a <http://www.w3.org/2002/07/owl#Class> }
            UNION
            { ?s a <http://www.w3.org/2002/07/owl#ObjectProperty> }
            UNION
            { ?s a <http://www.w3.org/2002/07/owl#DatatypeProperty> }
        }
        """
        results = self._execute_query(query, cache_key="owl_patterns")
        owl_count = self._extract_single_value(results, "count")
        if owl_count > 0:
            patterns['has_owl_ontology'] = True
            patterns['owl_entity_count'] = owl_count

        # Check for SKOS patterns
        query = """
        SELECT (COUNT(*) AS ?count)
        WHERE {
            { ?s a <http://www.w3.org/2004/02/skos/core#Concept> }
            UNION
            { ?s <http://www.w3.org/2004/02/skos/core#broader> ?o }
            UNION
            { ?s <http://www.w3.org/2004/02/skos/core#narrower> ?o }
        }
        """
        results = self._execute_query(query, cache_key="skos_patterns")
        skos_count = self._extract_single_value(results, "count")
        if skos_count > 0:
            patterns['has_skos_vocabulary'] = True
            patterns['skos_usage_count'] = skos_count

        # Check for FOAF patterns
        query = """
        SELECT (COUNT(*) AS ?count)
        WHERE {
            { ?s a <http://xmlns.com/foaf/0.1/Person> }
            UNION
            { ?s a <http://xmlns.com/foaf/0.1/Organization> }
        }
        """
        results = self._execute_query(query, cache_key="foaf_patterns")
        foaf_count = self._extract_single_value(results, "count")
        if foaf_count > 0:
            patterns['has_foaf_data'] = True
            patterns['foaf_entity_count'] = foaf_count

        # Check for Dublin Core metadata
        query = """
        SELECT (COUNT(*) AS ?count)
        WHERE {
            { ?s <http://purl.org/dc/terms/title> ?o }
            UNION
            { ?s <http://purl.org/dc/terms/creator> ?o }
            UNION
            { ?s <http://purl.org/dc/elements/1.1/title> ?o }
        }
        """
        results = self._execute_query(query, cache_key="dc_patterns")
        dc_count = self._extract_single_value(results, "count")
        if dc_count > 0:
            patterns['has_dublin_core_metadata'] = True
            patterns['dc_usage_count'] = dc_count

        logger.info(f"Detected {len(patterns)} patterns")
        return patterns

    def collect_all_statistics(
        self,
        include_graphs: bool = False,
        class_limit: int = 20,
        property_limit: int = 20
    ) -> DatasetStatistics:
        """
        Collect comprehensive dataset statistics.

        Args:
            include_graphs: Whether to analyze named graphs (can be slow)
            class_limit: Maximum number of top classes to collect
            property_limit: Maximum number of top properties to collect

        Returns:
            DatasetStatistics object with all collected statistics
        """
        start_time = time.time()

        logger.info(f"Starting statistics collection for {self.endpoint_url}")
        self._report_progress("Collecting dataset statistics...")

        stats = DatasetStatistics(
            endpoint_url=self.endpoint_url,
            collection_time=datetime.now().isoformat(),
            query_timeout_seconds=self.timeout
        )

        # Basic counts (parallel concepts, sequential execution for simplicity)
        stats.total_triples = self.count_total_triples()
        stats.distinct_subjects = self.count_distinct_subjects()
        stats.distinct_predicates = self.count_distinct_predicates()
        stats.distinct_objects = self.count_distinct_objects()

        # Class statistics
        stats.top_classes = self.get_top_classes(class_limit)
        stats.total_classes = len(stats.top_classes)

        # Property statistics
        stats.top_properties = self.get_top_properties(property_limit)
        stats.total_properties = len(stats.top_properties)

        # Type statistics
        stats.typed_resources = self.count_typed_resources()
        stats.untyped_resources = self.count_untyped_resources()

        # Literal statistics
        stats.total_literals = self.count_literals()
        stats.datatype_distribution = self.get_datatype_distribution()
        stats.language_distribution = self.get_language_distribution()

        # Graph statistics (optional, can be slow)
        if include_graphs:
            stats.named_graphs = self.get_named_graphs()
            if stats.named_graphs:
                stats.graph_sizes = self.get_graph_sizes(stats.named_graphs)

        # Namespace analysis
        stats.namespace_usage = self.analyze_namespace_usage()

        # Pattern detection
        stats.detected_patterns = self.detect_patterns()

        # Finalize
        stats.collection_duration_seconds = time.time() - start_time

        logger.info(f"Statistics collection completed in {stats.collection_duration_seconds:.2f}s")
        logger.info(f"Executed {self._query_count} queries")

        if self._failed_queries:
            logger.warning(f"{len(self._failed_queries)} queries failed")

        self._report_progress("Statistics collection complete!")

        return stats

    def clear_cache(self):
        """Clear the query result cache."""
        self._cache.clear()
        logger.info("Cache cleared")

    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about the cache."""
        return {
            'cache_size': len(self._cache),
            'cache_keys': list(self._cache.keys()),
            'query_count': self._query_count,
            'failed_queries': len(self._failed_queries)
        }


def collect_statistics(
    endpoint_url: str,
    timeout: int = 30,
    include_graphs: bool = False,
    class_limit: int = 20,
    property_limit: int = 20,
    progress_callback: Optional[callable] = None
) -> DatasetStatistics:
    """
    Convenience function to collect dataset statistics.

    Args:
        endpoint_url: SPARQL endpoint URL
        timeout: Query timeout in seconds
        include_graphs: Whether to analyze named graphs
        class_limit: Maximum number of top classes to collect
        property_limit: Maximum number of top properties to collect
        progress_callback: Optional callback for progress reporting

    Returns:
        DatasetStatistics object
    """
    collector = StatisticsCollector(
        endpoint_url=endpoint_url,
        timeout=timeout,
        progress_callback=progress_callback
    )

    return collector.collect_all_statistics(
        include_graphs=include_graphs,
        class_limit=class_limit,
        property_limit=property_limit
    )


if __name__ == "__main__":
    # Example usage
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if len(sys.argv) < 2:
        print("Usage: python statistics.py <endpoint_url>")
        sys.exit(1)

    endpoint = sys.argv[1]

    def progress_callback(message: str, current: int = 0, total: int = 0):
        if total > 0:
            print(f"[{current}/{total}] {message}")
        else:
            print(f"[*] {message}")

    stats = collect_statistics(
        endpoint_url=endpoint,
        timeout=60,
        include_graphs=True,
        progress_callback=progress_callback
    )

    print("\n" + stats.summary())

    # Optionally save to JSON
    import json
    output_file = "dataset_statistics.json"
    with open(output_file, 'w') as f:
        json.dump(stats.to_dict(), f, indent=2)
    print(f"\nStatistics saved to {output_file}")
