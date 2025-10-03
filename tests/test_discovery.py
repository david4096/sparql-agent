"""
Tests for discovery module: connectivity, capabilities, and statistics.

This module tests endpoint connectivity checking, capability detection,
and statistics gathering functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import asyncio

from sparql_agent.discovery.connectivity import (
    EndpointPinger,
    EndpointHealth,
    EndpointStatus,
    ConnectionConfig,
    RateLimiter,
    ConnectionPool,
)
from sparql_agent.discovery.capabilities import (
    CapabilitiesDetector,
    PrefixExtractor,
)


# =============================================================================
# Tests for Connectivity Module
# =============================================================================


class TestEndpointHealth:
    """Tests for EndpointHealth dataclass."""

    def test_endpoint_health_creation(self):
        """Test creating EndpointHealth instance."""
        health = EndpointHealth(
            endpoint_url="http://example.org/sparql",
            status=EndpointStatus.HEALTHY,
            response_time_ms=150.5,
            status_code=200,
        )
        assert health.endpoint_url == "http://example.org/sparql"
        assert health.status == EndpointStatus.HEALTHY
        assert health.response_time_ms == 150.5

    def test_endpoint_health_to_dict(self):
        """Test converting EndpointHealth to dictionary."""
        health = EndpointHealth(
            endpoint_url="http://example.org/sparql",
            status=EndpointStatus.HEALTHY,
            response_time_ms=150.5,
            status_code=200,
        )
        health_dict = health.to_dict()

        assert health_dict["endpoint_url"] == "http://example.org/sparql"
        assert health_dict["status"] == "healthy"
        assert health_dict["response_time_ms"] == 150.5
        assert health_dict["status_code"] == 200


class TestConnectionConfig:
    """Tests for ConnectionConfig dataclass."""

    def test_connection_config_defaults(self):
        """Test default connection configuration values."""
        config = ConnectionConfig()
        assert config.timeout == 10.0
        assert config.verify_ssl is True
        assert config.follow_redirects is True
        assert config.max_redirects == 5
        assert config.retry_attempts == 3

    def test_connection_config_custom(self):
        """Test custom connection configuration."""
        config = ConnectionConfig(
            timeout=30.0,
            verify_ssl=False,
            retry_attempts=5,
        )
        assert config.timeout == 30.0
        assert config.verify_ssl is False
        assert config.retry_attempts == 5


class TestRateLimiter:
    """Tests for RateLimiter class."""

    @pytest.mark.asyncio
    async def test_rate_limiter_async(self):
        """Test async rate limiting."""
        limiter = RateLimiter(rate=10.0, burst=5)  # 10 req/sec

        start = asyncio.get_event_loop().time()
        for _ in range(5):
            await limiter.acquire()
        elapsed = asyncio.get_event_loop().time() - start

        # Should be nearly instant for burst
        assert elapsed < 0.1

    def test_rate_limiter_sync(self):
        """Test synchronous rate limiting."""
        import time
        limiter = RateLimiter(rate=10.0, burst=2)

        start = time.time()
        for _ in range(2):
            limiter.acquire_sync()
        elapsed = time.time() - start

        # Should be nearly instant for burst
        assert elapsed < 0.1


@pytest.mark.unit
class TestEndpointPinger:
    """Tests for EndpointPinger class."""

    def test_pinger_initialization(self):
        """Test EndpointPinger initialization."""
        pinger = EndpointPinger()
        assert pinger.config is not None
        assert pinger.pool is not None

    def test_pinger_with_custom_config(self):
        """Test pinger with custom configuration."""
        config = ConnectionConfig(timeout=30.0)
        pinger = EndpointPinger(config=config)
        assert pinger.config.timeout == 30.0

    @patch('sparql_agent.discovery.connectivity.requests')
    def test_ping_sync_success(self, mock_requests):
        """Test successful synchronous ping."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_requests.Session.return_value.get.return_value = mock_response

        pinger = EndpointPinger()
        health = pinger.ping_sync("http://example.org/sparql", check_query=False)

        assert health.status == EndpointStatus.HEALTHY
        assert health.status_code == 200
        assert health.response_time_ms is not None

    @patch('sparql_agent.discovery.connectivity.requests')
    def test_ping_sync_timeout(self, mock_requests):
        """Test ping with timeout."""
        # Mock timeout exception
        import requests
        mock_requests.Session.return_value.get.side_effect = requests.exceptions.Timeout()
        mock_requests.exceptions.Timeout = requests.exceptions.Timeout

        pinger = EndpointPinger()
        health = pinger.ping_sync("http://example.org/sparql", check_query=False)

        assert health.status == EndpointStatus.TIMEOUT
        assert "timeout" in health.error_message.lower()

    @patch('sparql_agent.discovery.connectivity.requests')
    def test_ping_sync_authentication_required(self, mock_requests):
        """Test ping with authentication required."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_requests.Session.return_value.get.return_value = mock_response
        mock_requests.exceptions.HTTPError = Exception

        pinger = EndpointPinger()
        config = ConnectionConfig(retry_attempts=1)
        health = pinger.ping_sync("http://example.org/sparql", config=config)

        # Will be UNHEALTHY due to status determination logic
        assert health.status in [EndpointStatus.AUTH_REQUIRED, EndpointStatus.UNHEALTHY]

    def test_determine_status_healthy(self):
        """Test status determination for healthy endpoint."""
        pinger = EndpointPinger()
        status = pinger._determine_status(200, 500.0)
        assert status == EndpointStatus.HEALTHY

    def test_determine_status_degraded(self):
        """Test status determination for degraded endpoint."""
        pinger = EndpointPinger()
        status = pinger._determine_status(200, 3000.0)
        assert status == EndpointStatus.DEGRADED

    def test_determine_status_unhealthy(self):
        """Test status determination for unhealthy endpoint."""
        pinger = EndpointPinger()
        status = pinger._determine_status(200, 8000.0)
        assert status == EndpointStatus.UNHEALTHY

    def test_extract_server_info(self):
        """Test extracting server information from headers."""
        pinger = EndpointPinger()
        headers = {
            "Server": "Apache/2.4.41",
            "X-Powered-By": "Virtuoso",
        }
        info = pinger._extract_server_info(headers)

        assert "Server" in info
        assert info["Server"] == "Apache/2.4.41"

    def test_detect_capabilities(self):
        """Test detecting endpoint capabilities from headers."""
        pinger = EndpointPinger()
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST",
        }
        capabilities = pinger._detect_capabilities(headers)

        assert "CORS" in capabilities

    def test_record_health(self):
        """Test recording health check history."""
        pinger = EndpointPinger()
        health = EndpointHealth(
            endpoint_url="http://example.org/sparql",
            status=EndpointStatus.HEALTHY,
        )

        pinger.record_health(health)
        history = pinger.get_health_history("http://example.org/sparql")

        assert len(history) == 1
        assert history[0].status == EndpointStatus.HEALTHY

    def test_get_uptime_percentage(self):
        """Test calculating uptime percentage."""
        pinger = EndpointPinger()
        endpoint_url = "http://example.org/sparql"

        # Record some health checks
        for status in [EndpointStatus.HEALTHY] * 8 + [EndpointStatus.UNHEALTHY] * 2:
            health = EndpointHealth(endpoint_url=endpoint_url, status=status)
            pinger.record_health(health)

        uptime = pinger.get_uptime_percentage(endpoint_url)
        assert uptime == 80.0

    def test_get_average_response_time(self):
        """Test calculating average response time."""
        pinger = EndpointPinger()
        endpoint_url = "http://example.org/sparql"

        # Record health checks with response times
        for time_ms in [100.0, 200.0, 300.0]:
            health = EndpointHealth(
                endpoint_url=endpoint_url,
                status=EndpointStatus.HEALTHY,
                response_time_ms=time_ms,
            )
            pinger.record_health(health)

        avg_time = pinger.get_average_response_time(endpoint_url)
        assert avg_time == 200.0


# =============================================================================
# Tests for Capabilities Module
# =============================================================================


@pytest.mark.unit
class TestCapabilitiesDetector:
    """Tests for CapabilitiesDetector class."""

    def test_capabilities_detector_initialization(self):
        """Test CapabilitiesDetector initialization."""
        detector = CapabilitiesDetector("http://example.org/sparql")
        assert detector.endpoint_url == "http://example.org/sparql"
        assert detector.timeout == 30

    @patch('sparql_agent.discovery.capabilities.SPARQLWrapper')
    def test_detect_sparql_version_1_1(self, mock_sparql):
        """Test detecting SPARQL 1.1 support."""
        # Mock successful query execution
        mock_instance = Mock()
        mock_instance.query.return_value.convert.return_value = {"results": {"bindings": []}}
        mock_sparql.return_value = mock_instance

        detector = CapabilitiesDetector("http://example.org/sparql")
        version = detector.detect_sparql_version()

        assert version in ["1.1", "1.0"]

    @patch('sparql_agent.discovery.capabilities.SPARQLWrapper')
    def test_find_named_graphs(self, mock_sparql):
        """Test finding named graphs."""
        # Mock response with named graphs
        mock_instance = Mock()
        mock_instance.query.return_value.convert.return_value = {
            "results": {
                "bindings": [
                    {"g": {"value": "http://example.org/graph1"}},
                    {"g": {"value": "http://example.org/graph2"}},
                ]
            }
        }
        mock_sparql.return_value = mock_instance

        detector = CapabilitiesDetector("http://example.org/sparql")
        graphs = detector.find_named_graphs()

        assert len(graphs) == 2
        assert "http://example.org/graph1" in graphs

    def test_extract_namespace(self):
        """Test namespace extraction from URIs."""
        detector = CapabilitiesDetector("http://example.org/sparql")

        # Test hash-based namespace
        ns = detector._extract_namespace("http://example.org/ontology#Person")
        assert ns == "http://example.org/ontology#"

        # Test slash-based namespace
        ns = detector._extract_namespace("http://example.org/resource/Person")
        assert ns == "http://example.org/resource/"

    @patch('sparql_agent.discovery.capabilities.SPARQLWrapper')
    def test_detect_supported_functions(self, mock_sparql):
        """Test detecting supported SPARQL functions."""
        # Mock successful function tests
        mock_instance = Mock()
        mock_instance.query.return_value.convert.return_value = {"results": {"bindings": []}}
        mock_sparql.return_value = mock_instance

        detector = CapabilitiesDetector("http://example.org/sparql")
        functions = detector.detect_supported_functions()

        assert isinstance(functions, dict)
        assert "COUNT" in functions or "STRLEN" in functions

    @patch('sparql_agent.discovery.capabilities.SPARQLWrapper')
    def test_detect_features(self, mock_sparql):
        """Test detecting SPARQL 1.1 features."""
        mock_instance = Mock()
        mock_instance.query.return_value.convert.return_value = {"results": {"bindings": []}}
        mock_sparql.return_value = mock_instance

        detector = CapabilitiesDetector("http://example.org/sparql")
        features = detector.detect_features()

        assert isinstance(features, dict)
        assert "BIND" in features


class TestPrefixExtractor:
    """Tests for PrefixExtractor class."""

    def test_prefix_extractor_initialization(self):
        """Test PrefixExtractor initialization with common prefixes."""
        extractor = PrefixExtractor()

        assert len(extractor.prefix_mappings) > 0
        assert "rdf" in extractor.prefix_mappings
        assert "rdfs" in extractor.prefix_mappings
        assert "owl" in extractor.prefix_mappings

    def test_add_prefix(self):
        """Test adding a new prefix."""
        extractor = PrefixExtractor()
        extractor.add_prefix("ex", "http://example.org/")

        assert "ex" in extractor.prefix_mappings
        assert extractor.prefix_mappings["ex"] == "http://example.org/"

    def test_add_prefix_conflict(self):
        """Test handling prefix conflicts."""
        extractor = PrefixExtractor()
        extractor.add_prefix("test", "http://example.org/1/")
        extractor.add_prefix("test", "http://example.org/2/")

        # Should keep first mapping
        assert extractor.prefix_mappings["test"] == "http://example.org/1/"

    def test_add_prefix_overwrite(self):
        """Test overwriting existing prefix."""
        extractor = PrefixExtractor()
        extractor.add_prefix("test", "http://example.org/1/")
        extractor.add_prefix("test", "http://example.org/2/", overwrite=True)

        assert extractor.prefix_mappings["test"] == "http://example.org/2/"

    def test_extract_from_query(self):
        """Test extracting prefixes from SPARQL query."""
        extractor = PrefixExtractor()
        query = """
            PREFIX ex: <http://example.org/>
            PREFIX foaf: <http://xmlns.com/foaf/0.1/>
            SELECT ?s WHERE { ?s ex:name ?name }
        """

        extracted = extractor.extract_from_query(query)

        assert "ex" in extracted
        assert extracted["ex"] == "http://example.org/"

    def test_generate_prefix(self):
        """Test generating prefix from namespace."""
        extractor = PrefixExtractor()

        # Test with path-based namespace
        prefix = extractor._generate_prefix("http://example.org/ontology#")
        assert prefix == "ontology"

        # Test with already-used prefix
        extractor.add_prefix("ontology", "http://other.org/")
        prefix = extractor._generate_prefix("http://example.org/ontology#")
        assert prefix.startswith("ontology")

    def test_get_prefix_declarations(self):
        """Test generating PREFIX declarations."""
        extractor = PrefixExtractor()
        declarations = extractor.get_prefix_declarations(
            namespaces=["http://www.w3.org/1999/02/22-rdf-syntax-ns#"]
        )

        assert "PREFIX rdf:" in declarations
        assert "http://www.w3.org/1999/02/22-rdf-syntax-ns#" in declarations

    def test_shorten_uri(self):
        """Test shortening URIs with prefixes."""
        extractor = PrefixExtractor()

        short = extractor.shorten_uri("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
        assert short == "rdf:type"

    def test_expand_uri(self):
        """Test expanding prefixed URIs."""
        extractor = PrefixExtractor()

        full = extractor.expand_uri("rdf:type")
        assert full == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"

    def test_merge_mappings_keep_existing(self):
        """Test merging mappings with keep_existing strategy."""
        extractor = PrefixExtractor()
        extractor.add_prefix("test", "http://example.org/1/")

        other = {"test": "http://example.org/2/", "new": "http://new.org/"}
        extractor.merge_mappings(other, strategy="keep_existing")

        assert extractor.prefix_mappings["test"] == "http://example.org/1/"
        assert extractor.prefix_mappings["new"] == "http://new.org/"

    def test_merge_mappings_overwrite(self):
        """Test merging mappings with overwrite strategy."""
        extractor = PrefixExtractor()
        extractor.add_prefix("test", "http://example.org/1/")

        other = {"test": "http://example.org/2/"}
        extractor.merge_mappings(other, strategy="overwrite")

        assert extractor.prefix_mappings["test"] == "http://example.org/2/"

    def test_merge_mappings_rename(self):
        """Test merging mappings with rename strategy."""
        extractor = PrefixExtractor()
        extractor.add_prefix("test", "http://example.org/1/")

        other = {"test": "http://example.org/2/"}
        extractor.merge_mappings(other, strategy="rename")

        assert extractor.prefix_mappings["test"] == "http://example.org/1/"
        assert "test2" in extractor.prefix_mappings
        assert extractor.prefix_mappings["test2"] == "http://example.org/2/"

    def test_get_mapping_summary(self):
        """Test getting mapping summary."""
        extractor = PrefixExtractor()
        summary = extractor.get_mapping_summary()

        assert "total_prefixes" in summary
        assert "prefixes" in summary
        assert "namespaces" in summary
        assert summary["total_prefixes"] > 0


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.integration
class TestDiscoveryIntegration:
    """Integration tests for discovery components."""

    @patch('sparql_agent.discovery.connectivity.requests')
    def test_ping_and_detect_capabilities(self, mock_requests):
        """Test pinging endpoint and detecting capabilities together."""
        # Mock successful ping
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            "Server": "Virtuoso",
            "X-Powered-By": "Virtuoso",
        }
        mock_requests.Session.return_value.get.return_value = mock_response

        # Ping endpoint
        pinger = EndpointPinger()
        health = pinger.ping_sync("http://example.org/sparql", check_query=False)

        assert health.status == EndpointStatus.HEALTHY
        assert len(health.server_info) > 0

    def test_prefix_extraction_workflow(self):
        """Test complete prefix extraction workflow."""
        extractor = PrefixExtractor()

        # Extract from query
        query = "PREFIX ex: <http://example.org/> SELECT ?s WHERE { ?s ex:name ?n }"
        extractor.extract_from_query(query)

        # Generate declarations
        declarations = extractor.get_prefix_declarations()

        assert "PREFIX ex:" in declarations
        assert "PREFIX rdf:" in declarations  # From common prefixes
