#!/usr/bin/env python3
"""
Test suite for SPARQL Agent configuration system.

Run with: python -m pytest test_config.py
Or directly: python test_config.py
"""

import os
import tempfile
from pathlib import Path
import pytest

# Note: This test file assumes the configuration module is importable
# Adjust import paths as needed based on your project structure


def test_settings_import():
    """Test that settings can be imported."""
    try:
        from sparql_agent.config import (
            get_settings,
            SPARQLAgentSettings,
            OntologySettings,
            EndpointSettings,
            LLMSettings,
            LoggingSettings,
        )
        assert True
    except ImportError as e:
        pytest.skip(f"Configuration module not in path: {e}")


def test_get_settings():
    """Test getting settings instance."""
    try:
        from sparql_agent.config import get_settings

        settings = get_settings()
        assert settings is not None
        assert hasattr(settings, 'ontology')
        assert hasattr(settings, 'endpoint')
        assert hasattr(settings, 'llm')
        assert hasattr(settings, 'logging')
    except ImportError:
        pytest.skip("Configuration module not in path")


def test_ontology_settings():
    """Test ontology settings."""
    try:
        from sparql_agent.config import get_settings

        settings = get_settings()
        assert settings.ontology.ols_api_base_url is not None
        assert settings.ontology.cache_enabled is not None
        assert settings.ontology.cache_ttl > 0
        assert isinstance(settings.ontology.default_ontologies, list)
    except ImportError:
        pytest.skip("Configuration module not in path")


def test_endpoint_settings():
    """Test endpoint settings."""
    try:
        from sparql_agent.config import get_settings

        settings = get_settings()
        assert settings.endpoint.default_timeout > 0
        assert settings.endpoint.max_retries >= 0
        assert settings.endpoint.user_agent is not None
    except ImportError:
        pytest.skip("Configuration module not in path")


def test_llm_settings():
    """Test LLM settings."""
    try:
        from sparql_agent.config import get_settings

        settings = get_settings()
        assert settings.llm.model_name is not None
        assert 0.0 <= settings.llm.temperature <= 2.0
        assert settings.llm.max_tokens > 0
    except ImportError:
        pytest.skip("Configuration module not in path")


def test_logging_settings():
    """Test logging settings."""
    try:
        from sparql_agent.config import get_settings

        settings = get_settings()
        assert settings.logging.level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        assert settings.logging.format is not None
    except ImportError:
        pytest.skip("Configuration module not in path")


def test_endpoint_config_access():
    """Test accessing endpoint configurations."""
    try:
        from sparql_agent.config import get_settings

        settings = get_settings()

        # List endpoints
        endpoints = settings.list_endpoints()
        assert isinstance(endpoints, list)

        if endpoints:
            # Test accessing first endpoint
            endpoint_config = settings.get_endpoint_config(endpoints[0])
            assert endpoint_config is not None
            assert 'url' in endpoint_config or 'name' in endpoint_config
    except ImportError:
        pytest.skip("Configuration module not in path")


def test_ontology_config_access():
    """Test accessing ontology configurations."""
    try:
        from sparql_agent.config import get_settings

        settings = get_settings()

        # List ontologies
        ontologies = settings.list_ontologies()
        assert isinstance(ontologies, list)

        if ontologies:
            # Test accessing first ontology
            ontology_config = settings.get_ontology_config(ontologies[0])
            assert ontology_config is not None
            assert 'id' in ontology_config or 'name' in ontology_config
    except ImportError:
        pytest.skip("Configuration module not in path")


def test_prompt_template_access():
    """Test accessing prompt templates."""
    try:
        from sparql_agent.config import get_settings

        settings = get_settings()

        # List prompts
        prompts = settings.list_prompts()
        assert isinstance(prompts, list)

        if prompts:
            # Test accessing first prompt
            prompt = settings.get_prompt_template(prompts[0])
            assert prompt is not None
            assert isinstance(prompt, str)
    except ImportError:
        pytest.skip("Configuration module not in path")


def test_runtime_updates():
    """Test runtime configuration updates."""
    try:
        from sparql_agent.config import get_settings

        settings = get_settings()

        # Store original value
        original_debug = settings.debug

        # Update
        settings.update_config(debug=not original_debug)
        assert settings.debug == (not original_debug)

        # Restore
        settings.update_config(debug=original_debug)
        assert settings.debug == original_debug
    except ImportError:
        pytest.skip("Configuration module not in path")


def test_environment_variable_override():
    """Test environment variable override."""
    try:
        from sparql_agent.config import reset_settings, get_settings

        # Set environment variable
        os.environ['SPARQL_AGENT_DEBUG'] = 'true'

        # Reset and get new settings
        reset_settings()
        settings = get_settings()

        assert settings.debug is True

        # Clean up
        del os.environ['SPARQL_AGENT_DEBUG']
        reset_settings()
    except ImportError:
        pytest.skip("Configuration module not in path")


def test_configuration_validation():
    """Test configuration validation."""
    try:
        from sparql_agent.config import validate_configuration

        is_valid, errors = validate_configuration()
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)
    except ImportError:
        pytest.skip("Configuration module not in path")


def test_configuration_export_json():
    """Test configuration export to JSON."""
    try:
        from sparql_agent.config import export_configuration
        import json

        json_config = export_configuration(format="json")
        assert json_config is not None

        # Verify it's valid JSON
        parsed = json.loads(json_config)
        assert isinstance(parsed, dict)
    except ImportError:
        pytest.skip("Configuration module not in path")


def test_configuration_export_yaml():
    """Test configuration export to YAML."""
    try:
        from sparql_agent.config import export_configuration
        import yaml

        yaml_config = export_configuration(format="yaml")
        assert yaml_config is not None

        # Verify it's valid YAML
        parsed = yaml.safe_load(yaml_config)
        assert isinstance(parsed, dict)
    except ImportError:
        pytest.skip("Configuration module not in path")


def test_to_dict():
    """Test settings to_dict conversion."""
    try:
        from sparql_agent.config import get_settings

        settings = get_settings()
        config_dict = settings.to_dict()

        assert isinstance(config_dict, dict)
        assert 'ontology' in config_dict
        assert 'endpoint' in config_dict
        assert 'llm' in config_dict
        assert 'logging' in config_dict
    except ImportError:
        pytest.skip("Configuration module not in path")


def test_cache_directory_creation():
    """Test that cache directory is created."""
    try:
        from sparql_agent.config import get_settings

        settings = get_settings()
        cache_dir = settings.ontology.cache_dir

        # Cache directory should be created by validator
        assert cache_dir.exists()
        assert cache_dir.is_dir()
    except ImportError:
        pytest.skip("Configuration module not in path")


# Manual test runner if not using pytest
def run_manual_tests():
    """Run tests manually without pytest."""
    import sys

    tests = [
        test_settings_import,
        test_get_settings,
        test_ontology_settings,
        test_endpoint_settings,
        test_llm_settings,
        test_logging_settings,
        test_endpoint_config_access,
        test_ontology_config_access,
        test_prompt_template_access,
        test_runtime_updates,
        test_environment_variable_override,
        test_configuration_validation,
        test_configuration_export_json,
        test_configuration_export_yaml,
        test_to_dict,
        test_cache_directory_creation,
    ]

    passed = 0
    failed = 0
    skipped = 0

    print("Running configuration tests...\n")

    for test in tests:
        test_name = test.__name__
        try:
            test()
            print(f"✓ {test_name}")
            passed += 1
        except pytest.skip.Exception as e:
            print(f"⊝ {test_name} (skipped: {e})")
            skipped += 1
        except AssertionError as e:
            print(f"✗ {test_name} (failed: {e})")
            failed += 1
        except Exception as e:
            print(f"✗ {test_name} (error: {e})")
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"Results: {passed} passed, {failed} failed, {skipped} skipped")
    print(f"{'=' * 60}")

    return failed == 0


if __name__ == "__main__":
    success = run_manual_tests()
    exit(0 if success else 1)
