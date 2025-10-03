"""
SPARQL Query Execution and Result Handling Module.

This module provides comprehensive SPARQL query execution capabilities including:
- Query execution against multiple endpoints
- Multiple result format support (JSON, XML, CSV, Turtle)
- Streaming for large result sets
- Connection pooling and reuse
- Federation support across multiple endpoints
- Performance monitoring and metrics
- Result processing and standardization
- Lazy loading for memory efficiency
- Retry logic and error recovery
- Timeout management

Example:
    >>> from sparql_agent.execution import QueryExecutor
    >>> from sparql_agent.core.types import EndpointInfo
    >>>
    >>> executor = QueryExecutor()
    >>> endpoint = EndpointInfo(url="https://sparql.uniprot.org/sparql")
    >>> result = executor.execute(
    ...     query="SELECT * WHERE { ?s ?p ?o } LIMIT 10",
    ...     endpoint=endpoint
    ... )
    >>> for binding in result.bindings:
    ...     print(binding)
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (
    Any, AsyncIterator, Dict, Iterator, List, Optional, Set, Tuple, Union
)
from urllib.parse import urlparse
import json
import csv
import io
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from SPARQLWrapper import SPARQLWrapper, JSON, XML, CSV as CSV_FORMAT, TURTLE
from SPARQLWrapper.SPARQLExceptions import SPARQLWrapperException

from ..core.types import (
    QueryResult,
    QueryStatus,
    EndpointInfo,
    SchemaInfo,
)
from ..core.exceptions import (
    QueryExecutionError,
    QueryTimeoutError,
    QueryResultError,
    EndpointConnectionError,
    EndpointTimeoutError,
    EndpointAuthenticationError,
    EndpointRateLimitError,
    EndpointUnavailableError,
)


logger = logging.getLogger(__name__)


class ResultFormat(Enum):
    """Supported SPARQL result formats."""
    JSON = "json"
    XML = "xml"
    CSV = "csv"
    TSV = "tsv"
    TURTLE = "turtle"
    N_TRIPLES = "n-triples"
    RDF_XML = "rdf-xml"


class BindingType(Enum):
    """Types of SPARQL result bindings."""
    URI = "uri"
    LITERAL = "literal"
    BNODE = "bnode"
    TYPED_LITERAL = "typed-literal"


@dataclass
class Binding:
    """
    Represents a single variable binding in a SPARQL result.

    Attributes:
        variable: Variable name
        value: Binding value
        binding_type: Type of binding (URI, literal, bnode)
        datatype: Datatype URI for typed literals
        language: Language tag for literals
        raw: Raw binding data from endpoint
    """
    variable: str
    value: Any
    binding_type: BindingType = BindingType.LITERAL
    datatype: Optional[str] = None
    language: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None

    def is_uri(self) -> bool:
        """Check if binding is a URI."""
        return self.binding_type == BindingType.URI

    def is_literal(self) -> bool:
        """Check if binding is a literal."""
        return self.binding_type in [BindingType.LITERAL, BindingType.TYPED_LITERAL]

    def is_bnode(self) -> bool:
        """Check if binding is a blank node."""
        return self.binding_type == BindingType.BNODE

    def to_dict(self) -> Dict[str, Any]:
        """Convert binding to dictionary."""
        return {
            "variable": self.variable,
            "value": self.value,
            "type": self.binding_type.value,
            "datatype": self.datatype,
            "language": self.language,
        }


@dataclass
class ExecutionMetrics:
    """
    Performance metrics for query execution.

    Attributes:
        start_time: Query start timestamp
        end_time: Query end timestamp
        execution_time: Total execution time in seconds
        network_time: Network/transfer time in seconds
        parse_time: Result parsing time in seconds
        result_count: Number of results returned
        bytes_transferred: Approximate bytes transferred
        retry_count: Number of retries attempted
        endpoint_url: Endpoint URL
        query_hash: Hash of the query
        cache_hit: Whether result was from cache
    """
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    execution_time: float = 0.0
    network_time: float = 0.0
    parse_time: float = 0.0
    result_count: int = 0
    bytes_transferred: int = 0
    retry_count: int = 0
    endpoint_url: str = ""
    query_hash: str = ""
    cache_hit: bool = False

    def finalize(self):
        """Finalize metrics after execution."""
        self.end_time = datetime.now()
        if self.start_time and self.end_time:
            self.execution_time = (self.end_time - self.start_time).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "execution_time": self.execution_time,
            "network_time": self.network_time,
            "parse_time": self.parse_time,
            "result_count": self.result_count,
            "bytes_transferred": self.bytes_transferred,
            "retry_count": self.retry_count,
            "endpoint_url": self.endpoint_url,
            "cache_hit": self.cache_hit,
        }


@dataclass
class FederatedQuery:
    """
    Configuration for federated query execution.

    Attributes:
        endpoints: List of endpoint configurations
        merge_strategy: How to merge results (union, intersection, etc.)
        parallel: Execute queries in parallel
        fail_on_error: Fail entire query if one endpoint fails
        timeout_per_endpoint: Timeout for each endpoint
    """
    endpoints: List[EndpointInfo]
    merge_strategy: str = "union"  # union, intersection, sequential
    parallel: bool = True
    fail_on_error: bool = False
    timeout_per_endpoint: Optional[int] = None


class ConnectionPool:
    """
    Connection pool for SPARQL endpoints with reuse and timeout management.
    """

    def __init__(
        self,
        pool_size: int = 10,
        max_retries: int = 3,
        backoff_factor: float = 0.3,
        timeout: int = 30,
    ):
        """
        Initialize connection pool.

        Args:
            pool_size: Maximum number of connections per host
            max_retries: Maximum number of retry attempts
            backoff_factor: Backoff factor for retries
            timeout: Default timeout in seconds
        """
        self.pool_size = pool_size
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.timeout = timeout

        # Connection pools per endpoint
        self._sessions: Dict[str, requests.Session] = {}
        self._sparql_wrappers: Dict[str, SPARQLWrapper] = {}

        # Statistics
        self.stats = {
            "connections_created": 0,
            "connections_reused": 0,
            "requests_sent": 0,
            "requests_failed": 0,
        }

    def get_session(self, endpoint_url: str) -> requests.Session:
        """
        Get or create a requests session for an endpoint.

        Args:
            endpoint_url: Endpoint URL

        Returns:
            Configured requests session
        """
        if endpoint_url not in self._sessions:
            session = requests.Session()

            # Configure retry strategy
            retry_strategy = Retry(
                total=self.max_retries,
                backoff_factor=self.backoff_factor,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
            )

            adapter = HTTPAdapter(
                pool_connections=self.pool_size,
                pool_maxsize=self.pool_size,
                max_retries=retry_strategy
            )

            session.mount("http://", adapter)
            session.mount("https://", adapter)

            self._sessions[endpoint_url] = session
            self.stats["connections_created"] += 1
            logger.debug(f"Created new session for {endpoint_url}")
        else:
            self.stats["connections_reused"] += 1

        return self._sessions[endpoint_url]

    def get_sparql_wrapper(
        self,
        endpoint_url: str,
        return_format: ResultFormat = ResultFormat.JSON,
        timeout: Optional[int] = None,
    ) -> SPARQLWrapper:
        """
        Get or create a SPARQLWrapper for an endpoint.

        Args:
            endpoint_url: Endpoint URL
            return_format: Desired return format
            timeout: Query timeout in seconds

        Returns:
            Configured SPARQLWrapper
        """
        cache_key = f"{endpoint_url}:{return_format.value}"

        if cache_key not in self._sparql_wrappers:
            wrapper = SPARQLWrapper(endpoint_url)

            # Set return format
            if return_format == ResultFormat.JSON:
                wrapper.setReturnFormat(JSON)
            elif return_format == ResultFormat.XML:
                wrapper.setReturnFormat(XML)
            elif return_format == ResultFormat.CSV:
                wrapper.setReturnFormat(CSV_FORMAT)
            elif return_format == ResultFormat.TURTLE:
                wrapper.setReturnFormat(TURTLE)

            # Set timeout
            wrapper.setTimeout(timeout or self.timeout)

            self._sparql_wrappers[cache_key] = wrapper
            logger.debug(f"Created new SPARQLWrapper for {endpoint_url}")

        wrapper = self._sparql_wrappers[cache_key]

        # Update timeout if specified
        if timeout is not None:
            wrapper.setTimeout(timeout)

        return wrapper

    def close_all(self):
        """Close all connections in the pool."""
        for session in self._sessions.values():
            session.close()
        self._sessions.clear()
        self._sparql_wrappers.clear()
        logger.info("Closed all connections in pool")

    def get_statistics(self) -> Dict[str, int]:
        """Get connection pool statistics."""
        return dict(self.stats)


class ResultParser:
    """
    Parses SPARQL results from different formats into standardized structure.
    """

    @staticmethod
    def parse_json(data: Union[str, dict]) -> List[Dict[str, Binding]]:
        """
        Parse SPARQL JSON results.

        Args:
            data: JSON string or dictionary

        Returns:
            List of binding dictionaries
        """
        if isinstance(data, str):
            data = json.loads(data)

        results = []

        # Handle SELECT/ASK results
        if "results" in data and "bindings" in data["results"]:
            for binding_set in data["results"]["bindings"]:
                parsed_binding = {}
                for var, binding in binding_set.items():
                    parsed_binding[var] = ResultParser._parse_json_binding(var, binding)
                results.append(parsed_binding)

        # Handle ASK results
        elif "boolean" in data:
            results.append({"result": Binding(
                variable="result",
                value=data["boolean"],
                binding_type=BindingType.LITERAL
            )})

        return results

    @staticmethod
    def _parse_json_binding(variable: str, binding: Dict[str, Any]) -> Binding:
        """Parse a single JSON binding."""
        binding_type_str = binding.get("type", "literal")
        value = binding.get("value", "")

        # Determine binding type
        if binding_type_str == "uri":
            binding_type = BindingType.URI
        elif binding_type_str == "bnode":
            binding_type = BindingType.BNODE
        elif binding_type_str == "literal":
            if "datatype" in binding:
                binding_type = BindingType.TYPED_LITERAL
            else:
                binding_type = BindingType.LITERAL
        else:
            binding_type = BindingType.LITERAL

        return Binding(
            variable=variable,
            value=value,
            binding_type=binding_type,
            datatype=binding.get("datatype"),
            language=binding.get("xml:lang"),
            raw=binding
        )

    @staticmethod
    def parse_csv(data: str) -> List[Dict[str, Binding]]:
        """
        Parse SPARQL CSV results.

        Args:
            data: CSV string

        Returns:
            List of binding dictionaries
        """
        results = []
        reader = csv.DictReader(io.StringIO(data))

        for row in reader:
            parsed_binding = {}
            for var, value in row.items():
                if value:  # Skip empty values
                    parsed_binding[var] = Binding(
                        variable=var,
                        value=value,
                        binding_type=BindingType.LITERAL
                    )
            if parsed_binding:
                results.append(parsed_binding)

        return results

    @staticmethod
    def parse_xml(data: str) -> List[Dict[str, Binding]]:
        """
        Parse SPARQL XML results.

        Args:
            data: XML string

        Returns:
            List of binding dictionaries
        """
        # Basic XML parsing (could be enhanced with lxml)
        import xml.etree.ElementTree as ET

        results = []
        root = ET.fromstring(data)

        # Define namespaces
        ns = {
            'sparql': 'http://www.w3.org/2005/sparql-results#'
        }

        # Find all result elements
        for result in root.findall('.//sparql:result', ns):
            parsed_binding = {}

            for binding in result.findall('sparql:binding', ns):
                var = binding.get('name')

                # Check for URI
                uri_elem = binding.find('sparql:uri', ns)
                if uri_elem is not None:
                    parsed_binding[var] = Binding(
                        variable=var,
                        value=uri_elem.text,
                        binding_type=BindingType.URI
                    )
                    continue

                # Check for literal
                literal_elem = binding.find('sparql:literal', ns)
                if literal_elem is not None:
                    datatype = literal_elem.get('datatype')
                    language = literal_elem.get('{http://www.w3.org/XML/1998/namespace}lang')

                    parsed_binding[var] = Binding(
                        variable=var,
                        value=literal_elem.text or "",
                        binding_type=BindingType.TYPED_LITERAL if datatype else BindingType.LITERAL,
                        datatype=datatype,
                        language=language
                    )
                    continue

                # Check for blank node
                bnode_elem = binding.find('sparql:bnode', ns)
                if bnode_elem is not None:
                    parsed_binding[var] = Binding(
                        variable=var,
                        value=bnode_elem.text,
                        binding_type=BindingType.BNODE
                    )

            if parsed_binding:
                results.append(parsed_binding)

        return results


class StreamingResultIterator:
    """
    Iterator for streaming large SPARQL results with lazy loading.
    """

    def __init__(
        self,
        response: requests.Response,
        format: ResultFormat = ResultFormat.JSON,
        chunk_size: int = 1024,
    ):
        """
        Initialize streaming iterator.

        Args:
            response: HTTP response object
            format: Result format
            chunk_size: Size of chunks to read
        """
        self.response = response
        self.format = format
        self.chunk_size = chunk_size
        self._buffer = ""
        self._iterator = None
        self._exhausted = False

    def __iter__(self) -> Iterator[Dict[str, Binding]]:
        """Return iterator."""
        return self

    def __next__(self) -> Dict[str, Binding]:
        """Get next result binding."""
        if self._exhausted:
            raise StopIteration

        # For JSON streaming, we need to parse line by line or in chunks
        if self.format == ResultFormat.JSON:
            return self._next_json()
        else:
            raise NotImplementedError(f"Streaming not implemented for {self.format}")

    def _next_json(self) -> Dict[str, Binding]:
        """Get next JSON result."""
        # This is a simplified implementation
        # A production version would use ijson or similar for true streaming
        if self._iterator is None:
            # Load all data (for now)
            data = self.response.json()
            if "results" in data and "bindings" in data["results"]:
                self._iterator = iter(data["results"]["bindings"])
            else:
                self._exhausted = True
                raise StopIteration

        try:
            binding_set = next(self._iterator)
            parsed_binding = {}
            for var, binding in binding_set.items():
                parsed_binding[var] = ResultParser._parse_json_binding(var, binding)
            return parsed_binding
        except StopIteration:
            self._exhausted = True
            raise


class QueryExecutor:
    """
    Main query executor with support for multiple endpoints, formats, and execution modes.

    Features:
    - Execute queries against SPARQL endpoints
    - Multiple result format support (JSON, XML, CSV, Turtle)
    - Streaming for large result sets
    - Connection pooling and reuse
    - Federation support across multiple endpoints
    - Performance monitoring and metrics
    - Retry logic and error recovery
    - Timeout management

    Example:
        >>> executor = QueryExecutor(timeout=60, enable_metrics=True)
        >>> result = executor.execute(
        ...     query="SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10",
        ...     endpoint=EndpointInfo(url="https://sparql.uniprot.org/sparql")
        ... )
        >>> print(f"Found {result.row_count} results")
        >>> for binding in result.bindings:
        ...     print(binding)
    """

    def __init__(
        self,
        timeout: int = 60,
        max_retries: int = 3,
        pool_size: int = 10,
        enable_streaming: bool = False,
        enable_metrics: bool = True,
        user_agent: str = "SPARQL-Agent/1.0",
    ):
        """
        Initialize query executor.

        Args:
            timeout: Default timeout for queries in seconds
            max_retries: Maximum number of retry attempts
            pool_size: Connection pool size
            enable_streaming: Enable streaming for large results
            enable_metrics: Enable performance metrics collection
            user_agent: User agent string for requests
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.enable_streaming = enable_streaming
        self.enable_metrics = enable_metrics
        self.user_agent = user_agent

        # Initialize connection pool
        self.pool = ConnectionPool(
            pool_size=pool_size,
            max_retries=max_retries,
            timeout=timeout
        )

        # Execution statistics
        self.stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "total_results": 0,
            "total_execution_time": 0.0,
            "average_execution_time": 0.0,
            "queries_by_endpoint": defaultdict(int),
            "errors_by_type": defaultdict(int),
        }

        # Active executions for monitoring
        self._active_executions: Dict[str, ExecutionMetrics] = {}

    def execute(
        self,
        query: str,
        endpoint: Union[EndpointInfo, str],
        format: ResultFormat = ResultFormat.JSON,
        timeout: Optional[int] = None,
        stream: Optional[bool] = None,
        credentials: Optional[Dict[str, str]] = None,
        custom_headers: Optional[Dict[str, str]] = None,
    ) -> QueryResult:
        """
        Execute a SPARQL query against an endpoint.

        Args:
            query: SPARQL query string
            endpoint: Endpoint info or URL
            format: Desired result format
            timeout: Query timeout (uses default if None)
            stream: Enable streaming (uses default if None)
            credentials: Authentication credentials (username, password)
            custom_headers: Custom HTTP headers

        Returns:
            QueryResult with execution results and metadata

        Raises:
            QueryExecutionError: If query execution fails
            QueryTimeoutError: If query times out
            EndpointConnectionError: If connection fails
        """
        # Normalize endpoint
        if isinstance(endpoint, str):
            endpoint = EndpointInfo(url=endpoint)

        # Initialize metrics
        metrics = ExecutionMetrics(endpoint_url=endpoint.url)
        query_hash = str(hash(query))
        metrics.query_hash = query_hash

        if self.enable_metrics:
            self._active_executions[query_hash] = metrics

        # Use provided timeout or defaults
        actual_timeout = timeout or endpoint.timeout or self.timeout
        actual_stream = stream if stream is not None else self.enable_streaming

        self.stats["total_queries"] += 1
        self.stats["queries_by_endpoint"][endpoint.url] += 1

        try:
            logger.info(f"Executing query on {endpoint.url} (timeout: {actual_timeout}s)")
            logger.debug(f"Query: {query[:200]}...")

            # Execute query
            start_time = time.time()

            if actual_stream:
                result = self._execute_streaming(
                    query, endpoint, format, actual_timeout, credentials, custom_headers
                )
            else:
                result = self._execute_standard(
                    query, endpoint, format, actual_timeout, credentials, custom_headers
                )

            # Update metrics
            metrics.finalize()
            metrics.result_count = result.row_count

            # Update statistics
            self.stats["successful_queries"] += 1
            self.stats["total_results"] += result.row_count
            self.stats["total_execution_time"] += metrics.execution_time
            self.stats["average_execution_time"] = (
                self.stats["total_execution_time"] / self.stats["successful_queries"]
            )

            # Add metrics to result
            if self.enable_metrics:
                result.metadata["metrics"] = metrics.to_dict()

            logger.info(
                f"Query executed successfully: {result.row_count} results in "
                f"{metrics.execution_time:.2f}s"
            )

            return result

        except Exception as e:
            # Update error statistics
            self.stats["failed_queries"] += 1
            self.stats["errors_by_type"][type(e).__name__] += 1

            # Finalize metrics
            metrics.finalize()

            # Convert to appropriate exception
            error = self._convert_exception(e, endpoint)
            logger.error(f"Query execution failed: {error}")

            # Return failed result
            return QueryResult(
                status=QueryStatus.FAILED,
                query=query,
                error_message=str(error),
                execution_time=metrics.execution_time,
                metadata={"metrics": metrics.to_dict()} if self.enable_metrics else {}
            )

        finally:
            # Clean up active execution
            if query_hash in self._active_executions:
                del self._active_executions[query_hash]

    def _execute_standard(
        self,
        query: str,
        endpoint: EndpointInfo,
        format: ResultFormat,
        timeout: int,
        credentials: Optional[Dict[str, str]],
        custom_headers: Optional[Dict[str, str]],
    ) -> QueryResult:
        """Execute query in standard (non-streaming) mode."""
        start_network = time.time()

        # Get SPARQLWrapper from pool
        wrapper = self.pool.get_sparql_wrapper(endpoint.url, format, timeout)
        wrapper.setQuery(query)

        # Set custom user agent
        wrapper.addCustomHttpHeader("User-Agent", self.user_agent)

        # Add credentials if provided
        if credentials:
            wrapper.setCredentials(credentials.get("username"), credentials.get("password"))
        elif endpoint.authentication_required and endpoint.metadata.get("credentials"):
            creds = endpoint.metadata["credentials"]
            wrapper.setCredentials(creds.get("username"), creds.get("password"))

        # Add custom headers
        if custom_headers:
            for key, value in custom_headers.items():
                wrapper.addCustomHttpHeader(key, value)

        # Execute query
        try:
            raw_results = wrapper.query()
            network_time = time.time() - start_network

            # Convert results based on format
            start_parse = time.time()

            if format == ResultFormat.JSON:
                data = raw_results.convert()
                bindings = ResultParser.parse_json(data)
            elif format == ResultFormat.XML:
                data = raw_results.convert()
                bindings = ResultParser.parse_xml(data)
            elif format == ResultFormat.CSV:
                data = raw_results.convert()
                bindings = ResultParser.parse_csv(data)
            else:
                # For RDF formats, return raw data
                data = raw_results.convert()
                bindings = []

            parse_time = time.time() - start_parse

            # Build result
            variables = list(bindings[0].keys()) if bindings else []

            # Convert bindings to standard format
            standard_bindings = []
            for binding_dict in bindings:
                standard_binding = {}
                for var, binding in binding_dict.items():
                    standard_binding[var] = binding.value
                standard_bindings.append(standard_binding)

            result = QueryResult(
                status=QueryStatus.SUCCESS,
                query=query,
                bindings=standard_bindings,
                row_count=len(bindings),
                variables=variables,
                execution_time=network_time + parse_time,
                metadata={
                    "format": format.value,
                    "endpoint": endpoint.url,
                    "network_time": network_time,
                    "parse_time": parse_time,
                }
            )

            return result

        except SPARQLWrapperException as e:
            raise QueryExecutionError(
                f"SPARQL execution failed: {e}",
                details={"endpoint": endpoint.url, "query": query[:100]}
            )

    def _execute_streaming(
        self,
        query: str,
        endpoint: EndpointInfo,
        format: ResultFormat,
        timeout: int,
        credentials: Optional[Dict[str, str]],
        custom_headers: Optional[Dict[str, str]],
    ) -> QueryResult:
        """Execute query in streaming mode."""
        # Build request
        session = self.pool.get_session(endpoint.url)

        headers = {
            "User-Agent": self.user_agent,
            "Accept": self._get_accept_header(format),
        }

        if custom_headers:
            headers.update(custom_headers)

        # Add authentication
        auth = None
        if credentials:
            auth = (credentials.get("username"), credentials.get("password"))
        elif endpoint.authentication_required and endpoint.metadata.get("credentials"):
            creds = endpoint.metadata["credentials"]
            auth = (creds.get("username"), creds.get("password"))

        # Execute request
        start_time = time.time()

        try:
            response = session.post(
                endpoint.url,
                data={"query": query},
                headers=headers,
                auth=auth,
                timeout=timeout,
                stream=True
            )
            response.raise_for_status()

            # Create streaming iterator
            iterator = StreamingResultIterator(response, format)

            # Collect results (in streaming mode, could yield)
            bindings = []
            for binding in iterator:
                standard_binding = {var: b.value for var, b in binding.items()}
                bindings.append(standard_binding)

            execution_time = time.time() - start_time
            variables = list(bindings[0].keys()) if bindings else []

            result = QueryResult(
                status=QueryStatus.SUCCESS,
                query=query,
                bindings=bindings,
                row_count=len(bindings),
                variables=variables,
                execution_time=execution_time,
                metadata={
                    "format": format.value,
                    "endpoint": endpoint.url,
                    "streaming": True,
                }
            )

            return result

        except requests.exceptions.Timeout:
            raise QueryTimeoutError(
                f"Query timed out after {timeout}s",
                details={"endpoint": endpoint.url, "timeout": timeout}
            )
        except requests.exceptions.RequestException as e:
            raise EndpointConnectionError(
                f"Connection failed: {e}",
                details={"endpoint": endpoint.url}
            )

    def execute_federated(
        self,
        query: str,
        config: FederatedQuery,
        timeout: Optional[int] = None,
    ) -> QueryResult:
        """
        Execute a federated query across multiple endpoints.

        Args:
            query: SPARQL query string
            config: Federation configuration
            timeout: Overall timeout for all queries

        Returns:
            Merged QueryResult from all endpoints

        Raises:
            QueryExecutionError: If federation fails
        """
        logger.info(f"Executing federated query across {len(config.endpoints)} endpoints")

        if config.parallel:
            return self._execute_federated_parallel(query, config, timeout)
        else:
            return self._execute_federated_sequential(query, config, timeout)

    def _execute_federated_parallel(
        self,
        query: str,
        config: FederatedQuery,
        timeout: Optional[int],
    ) -> QueryResult:
        """Execute federated query in parallel."""
        results = []
        errors = []

        with ThreadPoolExecutor(max_workers=len(config.endpoints)) as executor:
            # Submit all queries
            futures = {
                executor.submit(
                    self.execute,
                    query,
                    endpoint,
                    timeout=config.timeout_per_endpoint or timeout
                ): endpoint
                for endpoint in config.endpoints
            }

            # Collect results
            for future in as_completed(futures):
                endpoint = futures[future]
                try:
                    result = future.result()
                    if result.is_success:
                        results.append(result)
                    else:
                        errors.append((endpoint, result.error_message))
                except Exception as e:
                    errors.append((endpoint, str(e)))
                    if config.fail_on_error:
                        raise QueryExecutionError(
                            f"Federated query failed at {endpoint.url}: {e}",
                            details={"endpoint": endpoint.url}
                        )

        # Merge results
        return self._merge_results(results, config.merge_strategy, errors)

    def _execute_federated_sequential(
        self,
        query: str,
        config: FederatedQuery,
        timeout: Optional[int],
    ) -> QueryResult:
        """Execute federated query sequentially."""
        results = []
        errors = []

        for endpoint in config.endpoints:
            try:
                result = self.execute(
                    query,
                    endpoint,
                    timeout=config.timeout_per_endpoint or timeout
                )
                if result.is_success:
                    results.append(result)
                else:
                    errors.append((endpoint, result.error_message))
                    if config.fail_on_error:
                        raise QueryExecutionError(
                            f"Federated query failed at {endpoint.url}: {result.error_message}",
                            details={"endpoint": endpoint.url}
                        )
            except Exception as e:
                errors.append((endpoint, str(e)))
                if config.fail_on_error:
                    raise

        # Merge results
        return self._merge_results(results, config.merge_strategy, errors)

    def _merge_results(
        self,
        results: List[QueryResult],
        strategy: str,
        errors: List[Tuple[EndpointInfo, str]],
    ) -> QueryResult:
        """
        Merge results from multiple endpoints.

        Args:
            results: List of query results
            strategy: Merge strategy (union, intersection, etc.)
            errors: List of errors from failed endpoints

        Returns:
            Merged QueryResult
        """
        if not results:
            return QueryResult(
                status=QueryStatus.FAILED,
                error_message=f"All endpoints failed: {errors}",
                row_count=0,
                metadata={"errors": errors}
            )

        if strategy == "union":
            # Union: combine all results
            merged_bindings = []
            all_variables = set()

            for result in results:
                merged_bindings.extend(result.bindings)
                all_variables.update(result.variables)

            return QueryResult(
                status=QueryStatus.SUCCESS,
                bindings=merged_bindings,
                row_count=len(merged_bindings),
                variables=list(all_variables),
                execution_time=max(r.execution_time for r in results),
                metadata={
                    "merge_strategy": strategy,
                    "endpoints_count": len(results),
                    "errors": errors if errors else None,
                }
            )

        elif strategy == "intersection":
            # Intersection: only common results
            if not results:
                return QueryResult(status=QueryStatus.SUCCESS, row_count=0)

            # Convert to sets for intersection
            binding_sets = [
                set(tuple(sorted(b.items())) for b in r.bindings)
                for r in results
            ]

            common = binding_sets[0]
            for bs in binding_sets[1:]:
                common = common.intersection(bs)

            # Convert back to list of dicts
            merged_bindings = [dict(b) for b in common]

            return QueryResult(
                status=QueryStatus.SUCCESS,
                bindings=merged_bindings,
                row_count=len(merged_bindings),
                variables=results[0].variables if results else [],
                execution_time=max(r.execution_time for r in results),
                metadata={
                    "merge_strategy": strategy,
                    "endpoints_count": len(results),
                }
            )

        else:  # sequential
            # Sequential: results from first successful endpoint
            return results[0]

    def _get_accept_header(self, format: ResultFormat) -> str:
        """Get Accept header for result format."""
        format_headers = {
            ResultFormat.JSON: "application/sparql-results+json",
            ResultFormat.XML: "application/sparql-results+xml",
            ResultFormat.CSV: "text/csv",
            ResultFormat.TSV: "text/tab-separated-values",
            ResultFormat.TURTLE: "text/turtle",
            ResultFormat.N_TRIPLES: "application/n-triples",
            ResultFormat.RDF_XML: "application/rdf+xml",
        }
        return format_headers.get(format, "application/sparql-results+json")

    def _convert_exception(self, error: Exception, endpoint: EndpointInfo) -> Exception:
        """Convert generic exceptions to specific SPARQL exceptions."""
        if isinstance(error, (QueryExecutionError, QueryTimeoutError)):
            return error

        error_str = str(error).lower()

        if "timeout" in error_str:
            return QueryTimeoutError(
                f"Query timed out: {error}",
                details={"endpoint": endpoint.url}
            )
        elif "401" in error_str or "unauthorized" in error_str:
            return EndpointAuthenticationError(
                f"Authentication failed: {error}",
                details={"endpoint": endpoint.url}
            )
        elif "429" in error_str or "rate limit" in error_str:
            return EndpointRateLimitError(
                f"Rate limit exceeded: {error}",
                details={"endpoint": endpoint.url}
            )
        elif "503" in error_str or "unavailable" in error_str:
            return EndpointUnavailableError(
                f"Endpoint unavailable: {error}",
                details={"endpoint": endpoint.url}
            )
        elif "connection" in error_str or "network" in error_str:
            return EndpointConnectionError(
                f"Connection failed: {error}",
                details={"endpoint": endpoint.url}
            )
        else:
            return QueryExecutionError(
                f"Query execution failed: {error}",
                details={"endpoint": endpoint.url}
            )

    def get_statistics(self) -> Dict[str, Any]:
        """Get executor statistics."""
        stats = dict(self.stats)
        stats["pool_stats"] = self.pool.get_statistics()
        stats["active_executions"] = len(self._active_executions)
        return stats

    def get_active_executions(self) -> Dict[str, Dict[str, Any]]:
        """Get currently active executions."""
        return {
            query_hash: metrics.to_dict()
            for query_hash, metrics in self._active_executions.items()
        }

    def close(self):
        """Close executor and all connections."""
        self.pool.close_all()
        logger.info("Query executor closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Utility functions

def execute_query(
    query: str,
    endpoint: Union[EndpointInfo, str],
    timeout: int = 60,
) -> QueryResult:
    """
    Quick utility to execute a SPARQL query.

    Args:
        query: SPARQL query string
        endpoint: Endpoint info or URL
        timeout: Query timeout in seconds

    Returns:
        QueryResult
    """
    with QueryExecutor(timeout=timeout) as executor:
        return executor.execute(query, endpoint)


def execute_query_with_validation(
    query: str,
    endpoint: Union[EndpointInfo, str],
    original_intent: str = "",
    llm_client=None,
    schema_tools=None,
    max_retries: int = 5,
    max_execution_retries: int = 3,
    timeout: int = 60,
) -> Tuple[QueryResult, Dict[str, Any]]:
    """
    Execute a SPARQL query with pre-execution validation and post-execution retry logic.

    This function:
    1. Validates the query against SPARQL syntax and schema constraints
    2. Attempts to fix issues through LLM refinement before execution
    3. Executes the query against the endpoint
    4. If execution fails, analyzes the error and regenerates a better query
    5. Retries execution with the improved query

    Args:
        query: SPARQL query string
        endpoint: Endpoint info or URL
        original_intent: Original natural language intent for the query
        llm_client: LLM client for query refinement
        schema_tools: Schema validation tools
        max_retries: Maximum retry attempts for pre-execution validation failures
        max_execution_retries: Maximum retry attempts for post-execution failures
        timeout: Query timeout in seconds

    Returns:
        Tuple of (QueryResult, validation_info)
    """
    from ..query.validation_retry import validate_before_execution, QueryValidationRetry

    endpoint_url = endpoint if isinstance(endpoint, str) else endpoint.url

    # Step 1: Pre-execution validation with retry logic
    if llm_client and original_intent:
        print(f"🔍 Pre-execution validation for endpoint: {endpoint_url}")

        validation_result = validate_before_execution(
            query=query,
            original_intent=original_intent,
            llm_client=llm_client,
            schema_tools=schema_tools,
            endpoint_url=endpoint_url,
            max_retries=max_retries
        )

        if not validation_result.is_valid and validation_result.gave_up:
            # Query validation failed after all retries
            error_msg = f"Query validation failed after {validation_result.attempts_made} attempts"
            if validation_result.final_validation.issues:
                issues = [issue.message for issue in validation_result.final_validation.issues]
                error_msg += f": {'; '.join(issues)}"

            raise QueryExecutionError(error_msg)

        final_query = validation_result.final_query
        validation_info = {
            'pre_validation_performed': True,
            'pre_validation_attempts': validation_result.attempts_made,
            'original_query': query,
            'pre_validated_query': final_query,
            'validation_passed': validation_result.is_valid,
            'schema_compliance': validation_result.schema_compliance
        }

        print(f"✅ Query pre-validated successfully after {validation_result.attempts_made} attempts")

    else:
        # No pre-validation, use original query
        final_query = query
        validation_info = {
            'pre_validation_performed': False,
            'original_query': query,
            'pre_validated_query': final_query,
            'validation_passed': True,
            'reason': 'No LLM client or intent provided for validation'
        }

    # Step 2: Execute query with post-execution retry logic
    execution_attempts = 0
    execution_errors = []
    last_error = None

    for execution_attempt in range(max_execution_retries + 1):  # +1 for initial attempt
        execution_attempts += 1

        try:
            print(f"🚀 Executing query (attempt {execution_attempt + 1}/{max_execution_retries + 1})")

            with QueryExecutor(timeout=timeout) as executor:
                result = executor.execute(final_query, endpoint)

            # Success! Update validation info and return
            validation_info.update({
                'execution_successful': True,
                'execution_attempts': execution_attempts,
                'execution_errors': execution_errors,
                'final_query': final_query
            })

            print(f"✅ Query executed successfully on attempt {execution_attempt + 1}")
            return result, validation_info

        except Exception as e:
            last_error = e
            error_message = str(e)
            execution_errors.append(error_message)

            print(f"❌ Execution attempt {execution_attempt + 1} failed: {error_message[:100]}...")

            # If this was the last attempt or we don't have LLM capabilities, give up
            if execution_attempt >= max_execution_retries or not llm_client or not original_intent:
                break

            # Attempt to generate a better query based on the execution error
            print(f"🔄 Analyzing execution error and generating better query...")

            validator = QueryValidationRetry(
                llm_client=llm_client,
                schema_tools=schema_tools,
                max_retries=2,  # Fewer retries for execution error fixes
                strict_validation=False
            )

            try:
                # Generate new query based on execution error
                retry_result = validator.retry_after_execution_error(
                    failed_query=final_query,
                    original_intent=original_intent,
                    execution_error=error_message,
                    endpoint_url=endpoint_url,
                    attempt_number=execution_attempt + 1
                )

                if retry_result.is_valid and not retry_result.gave_up:
                    final_query = retry_result.final_query
                    print(f"🔧 Generated new query based on execution error")
                else:
                    print(f"⚠️  Could not generate better query, will retry with same query")

            except Exception as fix_error:
                print(f"⚠️  Error generating fix for execution failure: {fix_error}")

    # All execution attempts failed
    validation_info.update({
        'execution_successful': False,
        'execution_attempts': execution_attempts,
        'execution_errors': execution_errors,
        'final_query': final_query,
        'final_error': str(last_error)
    })

    error_msg = f"Query execution failed after {execution_attempts} attempts"
    if execution_errors:
        error_msg += f". Last error: {execution_errors[-1]}"

    raise QueryExecutionError(error_msg)


def execute_federated_query(
    query: str,
    endpoints: List[Union[EndpointInfo, str]],
    parallel: bool = True,
) -> QueryResult:
    """
    Quick utility to execute a federated query.

    Args:
        query: SPARQL query string
        endpoints: List of endpoints
        parallel: Execute in parallel

    Returns:
        Merged QueryResult
    """
    # Normalize endpoints
    endpoint_infos = [
        e if isinstance(e, EndpointInfo) else EndpointInfo(url=e)
        for e in endpoints
    ]

    config = FederatedQuery(
        endpoints=endpoint_infos,
        parallel=parallel
    )

    with QueryExecutor() as executor:
        return executor.execute_federated(query, config)
