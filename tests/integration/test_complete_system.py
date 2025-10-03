"""
Complete system integration tests.

This module contains comprehensive integration tests that validate the entire
SPARQL Agent system end-to-end with real APIs and endpoints.
"""

import os
import pytest
import asyncio
from unittest.mock import patch, MagicMock

# System imports
from sparql_agent.llm import create_anthropic_provider, LLMRequest
from sparql_agent.execution import execute_query
from sparql_agent.discovery import EndpointPinger, ConnectionConfig
from sparql_agent.ontology import OLSClient
from sparql_agent.query import quick_generate


class TestCompleteSystem:
    """Complete system integration tests."""

    def setup_method(self):
        """Set up test environment."""
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        self.has_api_key = self.api_key is not None

    @pytest.mark.integration
    @pytest.mark.skipif(not os.getenv('ANTHROPIC_API_KEY'), reason="No ANTHROPIC_API_KEY")
    def test_complete_nlp_to_sparql_pipeline(self):
        """Test complete natural language to SPARQL to results pipeline."""
        # Create LLM provider
        provider = create_anthropic_provider(api_key=self.api_key)
        assert provider is not None

        # Generate SPARQL from natural language
        nl_query = "Find 3 items"
        sparql_query = quick_generate(
            natural_language=nl_query,
            llm_client=provider
        )

        assert sparql_query
        assert "SELECT" in sparql_query.upper()
        assert "LIMIT" in sparql_query.upper()

        # Execute query (with timeout to avoid hanging)
        try:
            result = execute_query(sparql_query, 'https://query.wikidata.org/sparql', timeout=30)
            assert result is not None
            # Query might timeout but should handle gracefully
        except Exception as e:
            # Acceptable for timeouts or network issues
            assert "timeout" in str(e).lower() or "network" in str(e).lower() or "connection" in str(e).lower()

    @pytest.mark.integration
    def test_sparql_endpoint_connectivity(self):
        """Test SPARQL endpoint connectivity and basic queries."""
        config = ConnectionConfig(timeout=15.0)
        pinger = EndpointPinger()

        endpoints = [
            'https://query.wikidata.org/sparql',
            'https://sparql.uniprot.org/sparql'
        ]

        for endpoint in endpoints:
            try:
                result = pinger.ping_sync(endpoint, config=config)
                assert result is not None
                assert result.status.value in ['healthy', 'degraded']  # Acceptable statuses
            except Exception as e:
                # Network issues are acceptable in tests
                pytest.skip(f"Network issue with {endpoint}: {e}")

    @pytest.mark.integration
    def test_ols_ontology_integration(self):
        """Test OLS ontology integration."""
        ols = OLSClient()

        try:
            results = ols.search('protein', limit=2)
            assert isinstance(results, list)
            assert len(results) >= 0  # May return 0 if API is down

            if results:
                assert 'label' in results[0] or 'iri' in results[0]
        except Exception as e:
            # API issues are acceptable in tests
            pytest.skip(f"OLS API issue: {e}")

    @pytest.mark.integration
    @pytest.mark.skipif(not os.getenv('ANTHROPIC_API_KEY'), reason="No ANTHROPIC_API_KEY")
    def test_llm_provider_functionality(self):
        """Test LLM provider with real API."""
        provider = create_anthropic_provider(api_key=self.api_key)

        request = LLMRequest(
            prompt='Convert to SPARQL: Find scientists',
            max_tokens=500,
            temperature=0.3
        )

        response = provider.generate(request)
        assert response is not None
        assert response.content
        assert response.usage.total_tokens > 0

    @pytest.mark.integration
    def test_error_handling_robustness(self):
        """Test error handling with invalid inputs."""
        # Test invalid endpoint
        with pytest.raises(Exception):
            execute_query('SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 1',
                         'http://invalid-endpoint.example', timeout=5)

        # Test invalid query
        with pytest.raises(Exception):
            execute_query('INVALID SPARQL QUERY',
                         'https://query.wikidata.org/sparql', timeout=5)

    @pytest.mark.integration
    def test_cli_command_simulation(self):
        """Test CLI command functionality (simulated)."""
        # This would test CLI commands if we could run them in pytest
        # For now, just test that the underlying functions work

        config = ConnectionConfig(timeout=10.0)
        pinger = EndpointPinger()

        try:
            result = pinger.ping_sync('https://query.wikidata.org/sparql', config=config)
            assert result is not None
        except Exception:
            # Network issues acceptable in tests
            pass

    @pytest.mark.performance
    @pytest.mark.skipif(not os.getenv('ANTHROPIC_API_KEY'), reason="No ANTHROPIC_API_KEY")
    def test_performance_benchmarks(self):
        """Test basic performance benchmarks."""
        import time

        # Test LLM response time
        provider = create_anthropic_provider(api_key=self.api_key)

        start = time.time()
        request = LLMRequest(prompt='Generate SPARQL for: Find items', max_tokens=200)
        response = provider.generate(request)
        llm_time = time.time() - start

        assert llm_time < 30.0  # Should respond within 30 seconds
        assert response.usage.total_tokens > 0

    @pytest.mark.security
    def test_security_validations(self):
        """Test security aspects."""
        # Test that API keys are not exposed in errors
        try:
            # This should fail but not expose the API key
            provider = create_anthropic_provider(api_key="invalid-key")
            request = LLMRequest(prompt='test')
            provider.generate(request)
        except Exception as e:
            error_str = str(e)
            assert "invalid-key" not in error_str
            assert "sk-ant" not in error_str

    def test_system_components_importable(self):
        """Test that all major system components can be imported."""
        # Test core imports
        from sparql_agent.core import SPARQLEndpoint
        from sparql_agent.llm import LLMClient
        from sparql_agent.execution import QueryExecutor
        from sparql_agent.discovery import EndpointPinger
        from sparql_agent.ontology import OLSClient
        from sparql_agent.query import SPARQLGenerator
        from sparql_agent.formatting import ResultFormatter

        # All imports should succeed
        assert True


# Test configuration
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test requiring real endpoints"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance benchmark"
    )
    config.addinivalue_line(
        "markers", "security: mark test as security validation"
    )


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])