"""
SPARQL Agent Configuration Module

This module provides comprehensive configuration management for the SPARQL Agent,
including settings for endpoints, ontologies, prompts, and logging.

Usage:
    from sparql_agent.config import get_settings, SPARQLAgentSettings

    # Get global settings instance
    settings = get_settings()

    # Access endpoint configuration
    uniprot_config = settings.get_endpoint_config('uniprot')

    # Access ontology configuration
    efo_config = settings.get_ontology_config('efo')

    # Get prompt template
    nl_to_sparql_prompt = settings.get_prompt_template('nl_to_sparql')

    # Update configuration at runtime
    settings.update_config(debug=True)

    # Reload YAML configurations
    settings.reload_yaml_configs()

Environment Variables:
    All settings can be overridden using environment variables with the
    SPARQL_AGENT_ prefix. For nested settings, use double underscores (__).

    Examples:
        SPARQL_AGENT_DEBUG=true
        SPARQL_AGENT_ONTOLOGY__CACHE_ENABLED=false
        SPARQL_AGENT_ENDPOINT__DEFAULT_TIMEOUT=120
        SPARQL_AGENT_LLM__MODEL_NAME=gpt-4-turbo
        SPARQL_AGENT_LOG__LEVEL=DEBUG
"""

from .settings import (
    SPARQLAgentSettings,
    OntologySettings,
    EndpointSettings,
    LLMSettings,
    LoggingSettings,
    get_settings,
    reset_settings,
)

__all__ = [
    # Main settings class
    "SPARQLAgentSettings",

    # Sub-configuration classes
    "OntologySettings",
    "EndpointSettings",
    "LLMSettings",
    "LoggingSettings",

    # Utility functions
    "get_settings",
    "reset_settings",
]

# Version information
__version__ = "1.0.0"
__author__ = "SPARQL Agent Team"
__license__ = "MIT"

# Configuration file names
CONFIG_FILES = [
    "endpoints.yaml",
    "ontologies.yaml",
    "prompts.yaml",
    "logging.yaml",
]

# Default configuration values
DEFAULTS = {
    "endpoints": {
        "default": "uniprot",
        "timeout": 60,
        "max_retries": 3,
    },
    "ontologies": {
        "ols_api_base_url": "https://www.ebi.ac.uk/ols4/api",
        "cache_enabled": True,
        "cache_ttl": 86400,
    },
    "llm": {
        "model_name": "gpt-4",
        "temperature": 0.1,
        "max_tokens": 2000,
    },
    "logging": {
        "level": "INFO",
        "file_enabled": False,
        "json_enabled": False,
    },
}


def load_configuration(config_dir=None, reload=False):
    """
    Load or reload the global configuration.

    Args:
        config_dir: Optional configuration directory path
        reload: Force reload of configuration

    Returns:
        SPARQLAgentSettings: The loaded settings instance
    """
    if config_dir:
        reset_settings()
        return SPARQLAgentSettings(config_dir=config_dir)
    return get_settings(reload=reload)


def validate_configuration(settings=None):
    """
    Validate the current configuration.

    Args:
        settings: Optional settings instance to validate (uses global if None)

    Returns:
        tuple: (is_valid: bool, errors: list)
    """
    if settings is None:
        settings = get_settings()

    errors = []

    # Validate ontology settings
    if not settings.ontology.ols_api_base_url:
        errors.append("OLS API base URL is not configured")

    if settings.ontology.cache_enabled and not settings.ontology.cache_dir:
        errors.append("Cache is enabled but cache directory is not configured")

    # Validate endpoint settings
    if settings.endpoint.default_timeout <= 0:
        errors.append("Endpoint timeout must be positive")

    if settings.endpoint.max_retries < 0:
        errors.append("Max retries must be non-negative")

    # Validate LLM settings
    if not (0.0 <= settings.llm.temperature <= 2.0):
        errors.append("LLM temperature must be between 0.0 and 2.0")

    if settings.llm.max_tokens <= 0:
        errors.append("LLM max tokens must be positive")

    # Validate logging settings
    valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if settings.logging.level not in valid_log_levels:
        errors.append(f"Invalid log level: {settings.logging.level}")

    # Validate loaded configurations
    if not settings._endpoints_config:
        errors.append("No endpoint configurations loaded")

    if not settings._ontologies_config:
        errors.append("No ontology configurations loaded")

    if not settings._prompts_config:
        errors.append("No prompt templates loaded")

    return len(errors) == 0, errors


def print_configuration(settings=None, verbose=False):
    """
    Print the current configuration.

    Args:
        settings: Optional settings instance to print (uses global if None)
        verbose: Include all details including YAML configs
    """
    if settings is None:
        settings = get_settings()

    print("=" * 80)
    print("SPARQL Agent Configuration")
    print("=" * 80)

    print("\nGeneral Settings:")
    print(f"  Debug Mode: {settings.debug}")
    print(f"  Config Directory: {settings.config_dir}")

    print("\nOntology Settings:")
    print(f"  OLS API Base URL: {settings.ontology.ols_api_base_url}")
    print(f"  Cache Enabled: {settings.ontology.cache_enabled}")
    print(f"  Cache Directory: {settings.ontology.cache_dir}")
    print(f"  Cache TTL: {settings.ontology.cache_ttl}s")
    print(f"  Default Ontologies: {', '.join(settings.ontology.default_ontologies)}")

    print("\nEndpoint Settings:")
    print(f"  Default Timeout: {settings.endpoint.default_timeout}s")
    print(f"  Max Retries: {settings.endpoint.max_retries}")
    print(f"  Rate Limiting: {settings.endpoint.rate_limit_enabled}")
    print(f"  User Agent: {settings.endpoint.user_agent}")

    print("\nLLM Settings:")
    print(f"  Model: {settings.llm.model_name}")
    print(f"  Temperature: {settings.llm.temperature}")
    print(f"  Max Tokens: {settings.llm.max_tokens}")
    print(f"  Few-shot Examples: {settings.llm.use_few_shot}")

    print("\nLogging Settings:")
    print(f"  Level: {settings.logging.level}")
    print(f"  File Logging: {settings.logging.file_enabled}")
    print(f"  JSON Logging: {settings.logging.json_enabled}")

    if verbose:
        print(f"\nConfigured Endpoints: {', '.join(settings.list_endpoints())}")
        print(f"Configured Ontologies: {', '.join(settings.list_ontologies())}")
        print(f"Available Prompts: {', '.join(settings.list_prompts())}")

    print("=" * 80)


def export_configuration(settings=None, format="json"):
    """
    Export configuration to a file or string.

    Args:
        settings: Optional settings instance to export (uses global if None)
        format: Export format ('json' or 'yaml')

    Returns:
        str: Serialized configuration
    """
    if settings is None:
        settings = get_settings()

    config_dict = settings.to_dict()

    if format == "json":
        import json
        return json.dumps(config_dict, indent=2, default=str)
    elif format == "yaml":
        import yaml
        return yaml.dump(config_dict, default_flow_style=False)
    else:
        raise ValueError(f"Unsupported format: {format}")


# Initialize logging when module is imported
def _setup_logging():
    """Setup logging based on configuration."""
    import logging
    from pathlib import Path
    from ..utils.logging import setup_logging

    try:
        settings = get_settings()
        logging_config_path = settings.config_dir / "logging.yaml"

        # Use the utils.logging setup function which handles missing dependencies gracefully
        setup_logging(
            config_path=logging_config_path if logging_config_path.exists() else None,
            log_level=settings.logging.level,
            enable_file_logging=settings.logging.file_enabled,
            enable_json_logging=settings.logging.json_enabled,
        )
    except Exception as e:
        # Fallback to basic logging if configuration fails
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        )
        # Don't show warning during import - it's noisy
        # Only show if verbose/debug mode is enabled


# Setup logging on import (can be disabled by setting environment variable)
import os
if os.getenv("SPARQL_AGENT_DISABLE_AUTO_LOGGING") != "true":
    try:
        _setup_logging()
    except Exception:
        pass  # Silently fail if settings cannot be loaded yet
