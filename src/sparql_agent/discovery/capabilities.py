"""
SPARQL Endpoint Capabilities Detection and Prefix Extraction.

This module provides tools for discovering SPARQL endpoint features,
supported functions, available namespaces, and prefix mappings.
"""

import logging
import re
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

from SPARQLWrapper import SPARQLWrapper, JSON, SPARQLExceptions


logger = logging.getLogger(__name__)


class CapabilitiesDetector:
    """
    Detects SPARQL endpoint capabilities through introspection queries.

    Discovers:
    - Supported SPARQL features
    - Available prefixes/namespaces
    - SPARQL version
    - Named graphs
    - Supported functions
    """

    def __init__(
        self,
        endpoint_url: str,
        timeout: int = 30,
        fast_mode: bool = False,
        progressive_timeout: bool = True,
        max_samples: int = 1000
    ):
        """
        Initialize the capabilities detector.

        Args:
            endpoint_url: SPARQL endpoint URL
            timeout: Query timeout in seconds
            fast_mode: Skip expensive queries for faster discovery
            progressive_timeout: Use progressive timeout strategy
            max_samples: Maximum number of samples for discovery queries
        """
        self.endpoint_url = endpoint_url
        self.timeout = timeout
        self.fast_mode = fast_mode
        self.progressive_timeout = progressive_timeout
        self.max_samples = max_samples
        self.sparql = SPARQLWrapper(endpoint_url)
        self.sparql.setTimeout(timeout)
        self.sparql.setReturnFormat(JSON)

        # Cache for detected capabilities
        self._capabilities_cache: Optional[Dict] = None

        # Track failed queries
        self._failed_queries: List[str] = []
        self._timed_out_queries: List[str] = []

    def detect_all_capabilities(self, progress_callback=None) -> Dict:
        """
        Run all capability detection queries and return comprehensive results.

        Uses progressive timeout strategy to handle large endpoints gracefully.

        Args:
            progress_callback: Optional callback function(step, total, message)

        Returns:
            Dictionary with all detected capabilities
        """
        if self._capabilities_cache is not None:
            return self._capabilities_cache

        logger.info(f"Detecting capabilities for endpoint: {self.endpoint_url}")

        # Define discovery phases with different timeout requirements
        phases = []

        # Phase 1: Quick tests (use short timeout)
        phases.append({
            'name': 'Quick Tests',
            'timeout': min(5, self.timeout),
            'tasks': [
                ('sparql_version', self.detect_sparql_version, {}),
            ]
        })

        # Phase 2: Feature detection (medium timeout)
        phases.append({
            'name': 'Feature Detection',
            'timeout': min(10, self.timeout),
            'tasks': [
                ('features', self.detect_features, {}),
            ]
        })

        if not self.fast_mode:
            # Phase 3: Data sampling (longer timeout)
            phases.append({
                'name': 'Data Sampling',
                'timeout': min(20, self.timeout),
                'tasks': [
                    ('named_graphs', self.find_named_graphs, {'limit': 50}),
                    ('namespaces', self.discover_namespaces, {'limit': self.max_samples}),
                ]
            })

            # Phase 4: Function support (can be slow on some endpoints)
            phases.append({
                'name': 'Function Support',
                'timeout': min(30, self.timeout),
                'tasks': [
                    ('supported_functions', self.detect_supported_functions, {}),
                ]
            })

            # Phase 5: Statistics (potentially expensive)
            phases.append({
                'name': 'Statistics',
                'timeout': self.timeout,
                'tasks': [
                    ('statistics', self.get_endpoint_statistics, {}),
                ]
            })

        capabilities = {
            'endpoint_url': self.endpoint_url,
            'discovery_mode': 'fast' if self.fast_mode else 'full',
            'progressive_timeout': self.progressive_timeout,
        }

        total_tasks = sum(len(phase['tasks']) for phase in phases)
        current_task = 0

        # Execute phases with progressive timeouts
        for phase in phases:
            phase_name = phase['name']
            phase_timeout = phase['timeout']

            logger.info(f"Starting phase: {phase_name} (timeout: {phase_timeout}s)")

            if self.progressive_timeout:
                # Temporarily adjust timeout for this phase
                original_timeout = self.sparql.timeout
                self.sparql.setTimeout(phase_timeout)

            for key, func, kwargs in phase['tasks']:
                current_task += 1

                if progress_callback:
                    progress_callback(current_task, total_tasks, f"Running: {key}")

                try:
                    logger.info(f"Executing discovery task: {key}")
                    result = func(**kwargs)
                    capabilities[key] = result
                    logger.debug(f"Task {key} completed successfully")

                except TimeoutError as e:
                    logger.warning(f"Task {key} timed out after {phase_timeout}s: {e}")
                    self._timed_out_queries.append(key)
                    capabilities[key] = None
                    capabilities[f'{key}_error'] = f"Timeout after {phase_timeout}s"

                except Exception as e:
                    logger.warning(f"Task {key} failed: {e}")
                    self._failed_queries.append(key)
                    capabilities[key] = None
                    capabilities[f'{key}_error'] = str(e)

            if self.progressive_timeout:
                # Restore original timeout
                self.sparql.setTimeout(original_timeout)

        # Add metadata about the discovery process
        capabilities['_metadata'] = {
            'failed_queries': self._failed_queries,
            'timed_out_queries': self._timed_out_queries,
            'fast_mode': self.fast_mode,
            'max_samples': self.max_samples,
            'timeout': self.timeout,
        }

        self._capabilities_cache = capabilities
        return capabilities

    def detect_sparql_version(self) -> str:
        """
        Detect SPARQL version by testing version-specific features.

        Returns:
            SPARQL version string (e.g., "1.1", "1.0")
        """
        # Test SPARQL 1.1 features
        sparql_11_features = [
            # Test BIND
            "SELECT * WHERE { BIND(1 AS ?x) } LIMIT 1",
            # Test EXISTS
            "SELECT * WHERE { FILTER EXISTS { ?s ?p ?o } } LIMIT 1",
            # Test MINUS
            "SELECT * WHERE { ?s ?p ?o MINUS { ?s a ?type } } LIMIT 1"
        ]

        for query in sparql_11_features:
            try:
                self._execute_query(query)
                logger.info("Detected SPARQL 1.1 support")
                return "1.1"
            except Exception as e:
                logger.debug(f"SPARQL 1.1 feature test failed: {e}")
                continue

        # Fallback to 1.0
        logger.info("Detected SPARQL 1.0 support")
        return "1.0"

    def find_named_graphs(self, limit: int = 100) -> List[str]:
        """
        Discover named graphs in the endpoint.

        Args:
            limit: Maximum number of graphs to return

        Returns:
            List of named graph URIs
        """
        query = f"""
        SELECT DISTINCT ?g
        WHERE {{
            GRAPH ?g {{ ?s ?p ?o }}
        }}
        LIMIT {limit}
        """

        try:
            results = self._execute_query(query)
            graphs = [row['g']['value'] for row in results.get('results', {}).get('bindings', [])]
            logger.info(f"Found {len(graphs)} named graphs")
            return graphs
        except Exception as e:
            logger.warning(f"Could not detect named graphs: {e}")
            return []

    def discover_namespaces(self, limit: int = 1000) -> List[str]:
        """
        Discover common namespaces used in the endpoint.

        Uses multiple strategies for different endpoint sizes:
        1. Sample predicates (fast, usually sufficient)
        2. If needed, sample subjects and objects

        Args:
            limit: Number of triples to sample

        Returns:
            List of discovered namespace URIs
        """
        namespaces = set()

        # Strategy 1: Get namespaces from predicates (fast and effective)
        # Predicates are typically from well-defined vocabularies
        try:
            logger.debug("Discovering namespaces from predicates...")
            predicate_query = f"""
            SELECT DISTINCT ?p
            WHERE {{
                ?s ?p ?o .
            }}
            LIMIT {min(limit, 1000)}
            """

            results = self._execute_query(predicate_query)

            for row in results.get('results', {}).get('bindings', []):
                if 'p' in row and row['p'].get('type') == 'uri':
                    uri = row['p']['value']
                    namespace = self._extract_namespace(uri)
                    if namespace:
                        namespaces.add(namespace)

            logger.info(f"Discovered {len(namespaces)} namespaces from predicates")

        except TimeoutError:
            logger.warning("Predicate query timed out, trying simpler approach")

        except Exception as e:
            logger.warning(f"Could not discover namespaces from predicates: {e}")

        # Strategy 2: If we have few namespaces, try sampling subjects/objects
        # (but with a smaller limit to avoid timeouts on large endpoints)
        if len(namespaces) < 10 and not self.fast_mode:
            try:
                logger.debug("Discovering additional namespaces from subjects/objects...")
                sample_query = f"""
                SELECT DISTINCT ?s ?o
                WHERE {{
                    ?s ?p ?o .
                    FILTER(isIRI(?s) || isIRI(?o))
                }}
                LIMIT {min(limit // 2, 500)}
                """

                results = self._execute_query(sample_query)

                for row in results.get('results', {}).get('bindings', []):
                    for var in ['s', 'o']:
                        if var in row and row[var].get('type') == 'uri':
                            uri = row[var]['value']
                            namespace = self._extract_namespace(uri)
                            if namespace:
                                namespaces.add(namespace)

                logger.info(f"Total namespaces discovered: {len(namespaces)}")

            except TimeoutError:
                logger.warning("Subject/object sampling timed out")

            except Exception as e:
                logger.warning(f"Could not discover additional namespaces: {e}")

        namespace_list = sorted(list(namespaces))
        logger.info(f"Final namespace count: {len(namespace_list)}")
        return namespace_list

    def detect_supported_functions(self) -> Dict[str, bool]:
        """
        Test for supported SPARQL functions and extensions.

        Returns:
            Dictionary mapping function names to availability
        """
        functions_to_test = {
            # String functions
            'STRLEN': 'SELECT (STRLEN("test") AS ?result) WHERE {}',
            'SUBSTR': 'SELECT (SUBSTR("test", 1, 2) AS ?result) WHERE {}',
            'UCASE': 'SELECT (UCASE("test") AS ?result) WHERE {}',
            'LCASE': 'SELECT (LCASE("TEST") AS ?result) WHERE {}',
            'STRSTARTS': 'SELECT (STRSTARTS("test", "te") AS ?result) WHERE {}',
            'STRENDS': 'SELECT (STRENDS("test", "st") AS ?result) WHERE {}',
            'CONTAINS': 'SELECT (CONTAINS("test", "es") AS ?result) WHERE {}',
            'CONCAT': 'SELECT (CONCAT("a", "b") AS ?result) WHERE {}',
            'REPLACE': 'SELECT (REPLACE("test", "e", "a") AS ?result) WHERE {}',
            'REGEX': 'SELECT (REGEX("test", "t.*t") AS ?result) WHERE {}',

            # Numeric functions
            'ABS': 'SELECT (ABS(-5) AS ?result) WHERE {}',
            'CEIL': 'SELECT (CEIL(4.3) AS ?result) WHERE {}',
            'FLOOR': 'SELECT (FLOOR(4.8) AS ?result) WHERE {}',
            'ROUND': 'SELECT (ROUND(4.5) AS ?result) WHERE {}',
            'RAND': 'SELECT (RAND() AS ?result) WHERE {}',

            # Date/Time functions
            'NOW': 'SELECT (NOW() AS ?result) WHERE {}',
            'YEAR': 'SELECT (YEAR(NOW()) AS ?result) WHERE {}',
            'MONTH': 'SELECT (MONTH(NOW()) AS ?result) WHERE {}',
            'DAY': 'SELECT (DAY(NOW()) AS ?result) WHERE {}',

            # Hash functions
            'MD5': 'SELECT (MD5("test") AS ?result) WHERE {}',
            'SHA1': 'SELECT (SHA1("test") AS ?result) WHERE {}',
            'SHA256': 'SELECT (SHA256("test") AS ?result) WHERE {}',

            # Aggregate functions
            'COUNT': 'SELECT (COUNT(*) AS ?result) WHERE { VALUES ?x { 1 2 3 } }',
            'SUM': 'SELECT (SUM(?x) AS ?result) WHERE { VALUES ?x { 1 2 3 } }',
            'AVG': 'SELECT (AVG(?x) AS ?result) WHERE { VALUES ?x { 1 2 3 } }',
            'MIN': 'SELECT (MIN(?x) AS ?result) WHERE { VALUES ?x { 1 2 3 } }',
            'MAX': 'SELECT (MAX(?x) AS ?result) WHERE { VALUES ?x { 1 2 3 } }',
            'GROUP_CONCAT': 'SELECT (GROUP_CONCAT(?x) AS ?result) WHERE { VALUES ?x { "a" "b" } }',

            # Other functions
            'BOUND': 'SELECT * WHERE { OPTIONAL { ?s ?p ?o } FILTER(BOUND(?s)) } LIMIT 1',
            'IF': 'SELECT (IF(1=1, "yes", "no") AS ?result) WHERE {}',
            'COALESCE': 'SELECT (COALESCE(?unbound, "default") AS ?result) WHERE {}',
            'UUID': 'SELECT (UUID() AS ?result) WHERE {}',
            'STRUUID': 'SELECT (STRUUID() AS ?result) WHERE {}',
        }

        supported = {}
        for func_name, query in functions_to_test.items():
            try:
                self._execute_query(query)
                supported[func_name] = True
                logger.debug(f"Function {func_name} is supported")
            except Exception:
                supported[func_name] = False
                logger.debug(f"Function {func_name} is not supported")

        supported_count = sum(1 for v in supported.values() if v)
        logger.info(f"Detected {supported_count}/{len(supported)} supported functions")
        return supported

    def detect_features(self) -> Dict[str, bool]:
        """
        Detect SPARQL 1.1 features support.

        Returns:
            Dictionary mapping feature names to availability
        """
        features = {
            'BIND': self._test_feature('SELECT * WHERE { BIND(1 AS ?x) } LIMIT 1'),
            'EXISTS': self._test_feature('SELECT * WHERE { FILTER EXISTS { ?s ?p ?o } } LIMIT 1'),
            'NOT_EXISTS': self._test_feature('SELECT * WHERE { FILTER NOT EXISTS { ?s ?p ?o } } LIMIT 1'),
            'MINUS': self._test_feature('SELECT * WHERE { ?s ?p ?o MINUS { ?s a ?type } } LIMIT 1'),
            'SERVICE': self._test_feature('SELECT * WHERE { SERVICE <http://example.org/sparql> { ?s ?p ?o } } LIMIT 1'),
            'SUBQUERY': self._test_feature('SELECT * WHERE { { SELECT * WHERE { ?s ?p ?o } LIMIT 1 } } LIMIT 1'),
            'VALUES': self._test_feature('SELECT * WHERE { VALUES ?x { 1 2 3 } } LIMIT 1'),
            'PROPERTY_PATHS': self._test_feature('SELECT * WHERE { ?s ?p+ ?o } LIMIT 1'),
            'NAMED_GRAPHS': len(self.find_named_graphs(limit=1)) > 0,
        }

        supported_count = sum(1 for v in features.values() if v)
        logger.info(f"Detected {supported_count}/{len(features)} SPARQL features")
        return features

    def get_endpoint_statistics(self) -> Dict:
        """
        Get basic statistics about the endpoint content.

        Uses lightweight queries suitable for large endpoints.
        Falls back gracefully if queries timeout.

        Returns:
            Dictionary with statistics
        """
        stats = {}

        # Strategy: Try progressively simpler queries if complex ones fail

        # Try to count triples (but this may timeout on huge endpoints)
        if not self.fast_mode:
            try:
                # Use sampling approach for large endpoints
                count_query = """
                SELECT (COUNT(*) AS ?count)
                WHERE {
                    ?s ?p ?o .
                }
                LIMIT 100000
                """
                result = self._execute_query(count_query)
                bindings = result.get('results', {}).get('bindings', [])
                if bindings:
                    count = int(bindings[0]['count']['value'])
                    # If we hit the limit, indicate it's approximate
                    if count >= 100000:
                        stats['approximate_triple_count'] = f"{count}+"
                        stats['triple_count_note'] = "Endpoint has >100K triples (exact count unavailable)"
                    else:
                        stats['approximate_triple_count'] = count
                    logger.info(f"Approximate triple count: {stats['approximate_triple_count']}")
            except TimeoutError:
                logger.warning("Triple count query timed out")
                stats['approximate_triple_count'] = "Unknown (query timeout)"
            except Exception as e:
                logger.warning(f"Could not count triples: {e}")
                stats['approximate_triple_count'] = None

        # Count distinct predicates (usually much faster than counting all triples)
        try:
            predicate_query = "SELECT (COUNT(DISTINCT ?p) AS ?count) WHERE { ?s ?p ?o }"
            result = self._execute_query(predicate_query)
            bindings = result.get('results', {}).get('bindings', [])
            if bindings:
                stats['distinct_predicates'] = int(bindings[0]['count']['value'])
                logger.info(f"Distinct predicates: {stats['distinct_predicates']}")
        except TimeoutError:
            logger.warning("Predicate count timed out, trying alternative approach")
            # Try just listing some predicates instead
            try:
                alt_query = "SELECT DISTINCT ?p WHERE { ?s ?p ?o } LIMIT 1000"
                result = self._execute_query(alt_query)
                bindings = result.get('results', {}).get('bindings', [])
                stats['distinct_predicates'] = f"{len(bindings)}+" if len(bindings) >= 1000 else len(bindings)
                stats['predicate_count_note'] = "Approximate (sampled)"
            except Exception:
                stats['distinct_predicates'] = None
        except Exception as e:
            logger.warning(f"Could not count predicates: {e}")
            stats['distinct_predicates'] = None

        # Count classes (useful and usually fast)
        try:
            class_query = "SELECT (COUNT(DISTINCT ?class) AS ?count) WHERE { ?s a ?class }"
            result = self._execute_query(class_query)
            bindings = result.get('results', {}).get('bindings', [])
            if bindings:
                stats['distinct_classes'] = int(bindings[0]['count']['value'])
                logger.info(f"Distinct classes: {stats['distinct_classes']}")
        except TimeoutError:
            logger.warning("Class count timed out")
            stats['distinct_classes'] = None
        except Exception as e:
            logger.warning(f"Could not count classes: {e}")
            stats['distinct_classes'] = None

        # Only try subject count in non-fast mode (can be very slow)
        if not self.fast_mode:
            try:
                # Use a limit to avoid extremely long queries
                subject_query = """
                SELECT (COUNT(DISTINCT ?s) AS ?count)
                WHERE {
                    ?s ?p ?o .
                }
                """
                result = self._execute_query(subject_query)
                bindings = result.get('results', {}).get('bindings', [])
                if bindings:
                    stats['distinct_subjects'] = int(bindings[0]['count']['value'])
                    logger.info(f"Distinct subjects: {stats['distinct_subjects']}")
            except TimeoutError:
                logger.warning("Subject count timed out (expected for large endpoints)")
                stats['distinct_subjects'] = "Unknown (query timeout)"
            except Exception as e:
                logger.warning(f"Could not count subjects: {e}")
                stats['distinct_subjects'] = None

        return stats

    def _execute_query(self, query: str, retry_count: int = 0, max_retries: int = 2) -> Dict:
        """
        Execute SPARQL query and return results with retry logic.

        Args:
            query: SPARQL query string
            retry_count: Current retry attempt
            max_retries: Maximum number of retries

        Returns:
            Query results as dictionary

        Raises:
            TimeoutError: If query times out after all retries
            SPARQLExceptions: If query fails with SPARQL error
        """
        try:
            self.sparql.setQuery(query)
            result = self.sparql.query().convert()
            return result

        except SPARQLExceptions.EndPointNotFound as e:
            logger.error(f"Endpoint not found: {self.endpoint_url}")
            raise

        except SPARQLExceptions.QueryBadFormed as e:
            logger.error(f"Malformed query: {e}")
            raise

        except SPARQLExceptions.EndPointInternalError as e:
            # Server error - might be worth retrying
            if retry_count < max_retries:
                logger.warning(f"Server error, retrying ({retry_count + 1}/{max_retries}): {e}")
                import time
                time.sleep(2 ** retry_count)  # Exponential backoff
                return self._execute_query(query, retry_count + 1, max_retries)
            else:
                logger.error(f"Server error after {max_retries} retries: {e}")
                raise

        except SPARQLExceptions.Unauthorized as e:
            logger.error(f"Authentication required for endpoint: {self.endpoint_url}")
            raise

        except SPARQLExceptions.URITooLong as e:
            logger.error(f"Query URI too long: {e}")
            raise

        except Exception as e:
            # Check if it's a timeout-related error
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in ['timeout', 'timed out', 'time out']):
                logger.warning(f"Query timeout: {e}")
                raise TimeoutError(f"Query timed out: {e}") from e

            # Generic error - might be worth retrying
            if retry_count < max_retries:
                logger.warning(f"Query failed, retrying ({retry_count + 1}/{max_retries}): {e}")
                import time
                time.sleep(2 ** retry_count)  # Exponential backoff
                return self._execute_query(query, retry_count + 1, max_retries)
            else:
                logger.error(f"Query failed after {max_retries} retries: {e}")
                raise

    def _test_feature(self, query: str) -> bool:
        """Test if a feature is supported by executing a query."""
        try:
            self._execute_query(query)
            return True
        except Exception:
            return False

    def _extract_namespace(self, uri: str) -> Optional[str]:
        """
        Extract namespace from a URI.

        Args:
            uri: Full URI

        Returns:
            Namespace portion of the URI
        """
        # Try splitting on # first
        if '#' in uri:
            return uri.rsplit('#', 1)[0] + '#'

        # Try splitting on last /
        if '/' in uri:
            parts = uri.rsplit('/', 1)
            # Only return if it looks like a namespace (not just a path)
            if len(parts[0]) > 8:  # Minimum "http://x"
                return parts[0] + '/'

        return None


class PrefixExtractor:
    """
    Extracts and manages SPARQL prefix mappings.

    Handles:
    - Parsing common prefixes from various sources
    - Building prefix mappings
    - Resolving conflicts
    - Generating prefix declarations
    """

    # Common well-known prefixes
    COMMON_PREFIXES = {
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
        'owl': 'http://www.w3.org/2002/07/owl#',
        'xsd': 'http://www.w3.org/2001/XMLSchema#',
        'skos': 'http://www.w3.org/2004/02/skos/core#',
        'dc': 'http://purl.org/dc/elements/1.1/',
        'dcterms': 'http://purl.org/dc/terms/',
        'foaf': 'http://xmlns.com/foaf/0.1/',
        'schema': 'http://schema.org/',
        'dbo': 'http://dbpedia.org/ontology/',
        'dbr': 'http://dbpedia.org/resource/',
        'dbp': 'http://dbpedia.org/property/',
        'geo': 'http://www.w3.org/2003/01/geo/wgs84_pos#',
        'prov': 'http://www.w3.org/ns/prov#',
        'void': 'http://rdfs.org/ns/void#',
        'dcat': 'http://www.w3.org/ns/dcat#',
        'vcard': 'http://www.w3.org/2006/vcard/ns#',
        'time': 'http://www.w3.org/2006/time#',
        'org': 'http://www.w3.org/ns/org#',
        'qb': 'http://purl.org/linked-data/cube#',
    }

    def __init__(self):
        """Initialize the prefix extractor."""
        self.prefix_mappings: Dict[str, str] = {}
        self.namespace_to_prefix: Dict[str, str] = {}

        # Start with common prefixes
        self._load_common_prefixes()

    def _load_common_prefixes(self):
        """Load well-known common prefixes."""
        for prefix, namespace in self.COMMON_PREFIXES.items():
            self.add_prefix(prefix, namespace)

    def add_prefix(self, prefix: str, namespace: str, overwrite: bool = False):
        """
        Add a prefix mapping.

        Args:
            prefix: Prefix name
            namespace: Full namespace URI
            overwrite: Whether to overwrite existing mappings
        """
        # Normalize prefix (remove trailing colon if present)
        prefix = prefix.rstrip(':')

        # Check for conflicts
        if prefix in self.prefix_mappings and not overwrite:
            if self.prefix_mappings[prefix] != namespace:
                logger.warning(
                    f"Prefix conflict: '{prefix}' already maps to "
                    f"'{self.prefix_mappings[prefix]}', not adding '{namespace}'"
                )
                return

        self.prefix_mappings[prefix] = namespace
        self.namespace_to_prefix[namespace] = prefix
        logger.debug(f"Added prefix mapping: {prefix} -> {namespace}")

    def extract_from_query(self, query: str) -> Dict[str, str]:
        """
        Extract prefix declarations from a SPARQL query.

        Args:
            query: SPARQL query string

        Returns:
            Dictionary of extracted prefix mappings
        """
        prefix_pattern = r'PREFIX\s+(\w+):\s*<([^>]+)>'
        matches = re.findall(prefix_pattern, query, re.IGNORECASE)

        extracted = {}
        for prefix, namespace in matches:
            extracted[prefix] = namespace
            self.add_prefix(prefix, namespace)

        logger.info(f"Extracted {len(extracted)} prefixes from query")
        return extracted

    def extract_from_namespaces(self, namespaces: List[str]) -> Dict[str, str]:
        """
        Generate prefix mappings for discovered namespaces.

        Args:
            namespaces: List of namespace URIs

        Returns:
            Dictionary of generated prefix mappings
        """
        generated = {}

        for namespace in namespaces:
            # Check if we already have this namespace
            if namespace in self.namespace_to_prefix:
                continue

            # Try to generate a sensible prefix
            prefix = self._generate_prefix(namespace)
            if prefix:
                self.add_prefix(prefix, namespace)
                generated[prefix] = namespace

        logger.info(f"Generated {len(generated)} new prefix mappings")
        return generated

    def _generate_prefix(self, namespace: str) -> Optional[str]:
        """
        Generate a prefix name from a namespace URI.

        Args:
            namespace: Namespace URI

        Returns:
            Generated prefix name
        """
        # Parse the URL
        parsed = urlparse(namespace)

        # Try to extract from path
        path = parsed.path.strip('/')
        if path:
            # Use the last path component
            parts = path.split('/')
            candidate = parts[-1]

            # Clean up common suffixes
            candidate = candidate.replace('.owl', '').replace('.rdf', '')
            candidate = candidate.rstrip('#')

            # Make it a valid prefix (alphanumeric + underscore)
            candidate = re.sub(r'[^a-zA-Z0-9_]', '', candidate)

            if candidate and not candidate[0].isdigit():
                # Check if this prefix is already used
                if candidate not in self.prefix_mappings:
                    return candidate

                # Try with number suffix
                for i in range(2, 100):
                    numbered = f"{candidate}{i}"
                    if numbered not in self.prefix_mappings:
                        return numbered

        # Fallback: use domain name
        if parsed.netloc:
            domain = parsed.netloc.replace('.', '_').replace('-', '_')
            domain = re.sub(r'[^a-zA-Z0-9_]', '', domain)

            if domain and not domain[0].isdigit():
                if domain not in self.prefix_mappings:
                    return domain

                for i in range(2, 100):
                    numbered = f"{domain}{i}"
                    if numbered not in self.prefix_mappings:
                        return numbered

        return None

    def get_prefix_declarations(self, namespaces: Optional[List[str]] = None) -> str:
        """
        Generate PREFIX declarations for SPARQL queries.

        Args:
            namespaces: Optional list of specific namespaces to include

        Returns:
            String with PREFIX declarations
        """
        if namespaces:
            # Only include specified namespaces
            relevant_mappings = {
                prefix: ns for prefix, ns in self.prefix_mappings.items()
                if ns in namespaces
            }
        else:
            # Include all mappings
            relevant_mappings = self.prefix_mappings

        declarations = []
        for prefix, namespace in sorted(relevant_mappings.items()):
            declarations.append(f"PREFIX {prefix}: <{namespace}>")

        return '\n'.join(declarations)

    def shorten_uri(self, uri: str) -> str:
        """
        Shorten a URI using known prefixes.

        Args:
            uri: Full URI

        Returns:
            Shortened URI (prefix:local) or original if no prefix found
        """
        for namespace, prefix in self.namespace_to_prefix.items():
            if uri.startswith(namespace):
                local_part = uri[len(namespace):]
                return f"{prefix}:{local_part}"

        return uri

    def expand_uri(self, prefixed_uri: str) -> str:
        """
        Expand a prefixed URI to full form.

        Args:
            prefixed_uri: Prefixed URI (e.g., "rdf:type")

        Returns:
            Full URI or original if prefix not found
        """
        if ':' not in prefixed_uri:
            return prefixed_uri

        prefix, local_part = prefixed_uri.split(':', 1)
        if prefix in self.prefix_mappings:
            return self.prefix_mappings[prefix] + local_part

        return prefixed_uri

    def merge_mappings(self, other_mappings: Dict[str, str], strategy: str = 'keep_existing'):
        """
        Merge another set of prefix mappings.

        Args:
            other_mappings: Dictionary of prefix -> namespace mappings
            strategy: Conflict resolution strategy ('keep_existing', 'overwrite', 'rename')
        """
        for prefix, namespace in other_mappings.items():
            if prefix in self.prefix_mappings:
                if self.prefix_mappings[prefix] == namespace:
                    continue  # Same mapping, no conflict

                if strategy == 'keep_existing':
                    logger.debug(f"Keeping existing mapping for {prefix}")
                    continue
                elif strategy == 'overwrite':
                    logger.debug(f"Overwriting mapping for {prefix}")
                    self.add_prefix(prefix, namespace, overwrite=True)
                elif strategy == 'rename':
                    # Find a new prefix name
                    for i in range(2, 100):
                        new_prefix = f"{prefix}{i}"
                        if new_prefix not in self.prefix_mappings:
                            logger.debug(f"Renaming {prefix} to {new_prefix}")
                            self.add_prefix(new_prefix, namespace)
                            break
            else:
                self.add_prefix(prefix, namespace)

    def get_mapping_summary(self) -> Dict:
        """
        Get a summary of current prefix mappings.

        Returns:
            Dictionary with mapping statistics
        """
        return {
            'total_prefixes': len(self.prefix_mappings),
            'prefixes': list(self.prefix_mappings.keys()),
            'namespaces': list(self.namespace_to_prefix.keys()),
            'mappings': self.prefix_mappings.copy()
        }
