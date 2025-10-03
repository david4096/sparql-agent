"""
Configuration management system for SPARQL Agent.

This module provides Pydantic-based settings with environment variable support,
runtime configuration updates, and integration with YAML configuration files.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import yaml


class OntologySettings(BaseSettings):
    """Configuration for ontology services (EBI OLS4)."""

    model_config = SettingsConfigDict(
        env_prefix="SPARQL_AGENT_ONTOLOGY_",
        case_sensitive=False,
        extra="allow"
    )

    # EBI OLS4 API configuration
    ols_api_base_url: str = Field(
        default="https://www.ebi.ac.uk/ols4/api",
        description="Base URL for EBI OLS4 API"
    )
    ols_timeout: int = Field(
        default=30,
        description="Timeout for OLS API requests in seconds"
    )
    ols_max_retries: int = Field(
        default=3,
        description="Maximum number of retries for OLS API requests"
    )

    # OWL ontology cache settings
    cache_enabled: bool = Field(
        default=True,
        description="Enable ontology caching"
    )
    cache_dir: Path = Field(
        default=Path.home() / ".cache" / "sparql_agent" / "ontologies",
        description="Directory for ontology cache"
    )
    cache_ttl: int = Field(
        default=86400,
        description="Cache time-to-live in seconds (default: 24 hours)"
    )
    cache_max_size_mb: int = Field(
        default=500,
        description="Maximum cache size in megabytes"
    )

    # Default ontologies to load
    default_ontologies: List[str] = Field(
        default=["efo", "mondo", "hp", "uberon", "go"],
        description="List of default ontology IDs to preload"
    )

    @field_validator("cache_dir")
    @classmethod
    def create_cache_dir(cls, v: Path) -> Path:
        """Ensure cache directory exists."""
        v.mkdir(parents=True, exist_ok=True)
        return v


class EndpointSettings(BaseSettings):
    """Configuration for SPARQL endpoints."""

    model_config = SettingsConfigDict(
        env_prefix="SPARQL_AGENT_ENDPOINT_",
        case_sensitive=False,
        extra="allow"
    )

    default_timeout: int = Field(
        default=60,
        description="Default timeout for SPARQL queries in seconds"
    )
    max_retries: int = Field(
        default=3,
        description="Maximum number of retries for failed queries"
    )
    retry_delay: float = Field(
        default=1.0,
        description="Delay between retries in seconds"
    )
    user_agent: str = Field(
        default="SPARQL-Agent/1.0",
        description="User agent string for HTTP requests"
    )

    # Rate limiting
    rate_limit_enabled: bool = Field(
        default=True,
        description="Enable rate limiting for SPARQL queries"
    )
    rate_limit_calls: int = Field(
        default=10,
        description="Maximum number of calls per period"
    )
    rate_limit_period: int = Field(
        default=60,
        description="Rate limit period in seconds"
    )


class LLMSettings(BaseSettings):
    """Configuration for LLM integration."""

    model_config = SettingsConfigDict(
        env_prefix="SPARQL_AGENT_LLM_",
        case_sensitive=False,
        extra="allow"
    )

    # Provider configuration
    provider: Optional[str] = Field(
        default=None,
        description="LLM provider (anthropic, openai, local)"
    )

    # Model configuration
    model_name: str = Field(
        default="gpt-4",
        description="LLM model name"
    )
    temperature: float = Field(
        default=0.1,
        ge=0.0,
        le=2.0,
        description="Temperature for LLM generation"
    )
    max_tokens: int = Field(
        default=2000,
        description="Maximum tokens for LLM response"
    )

    # API configuration
    api_key: Optional[str] = Field(
        default=None,
        description="API key for LLM service"
    )
    api_base_url: Optional[str] = Field(
        default=None,
        description="Base URL for LLM API"
    )

    # Prompt configuration
    use_few_shot: bool = Field(
        default=True,
        description="Enable few-shot examples in prompts"
    )
    max_examples: int = Field(
        default=5,
        description="Maximum number of few-shot examples"
    )


class LoggingSettings(BaseSettings):
    """Configuration for logging."""

    model_config = SettingsConfigDict(
        env_prefix="SPARQL_AGENT_LOG_",
        case_sensitive=False,
        extra="allow"
    )

    level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format"
    )
    file_enabled: bool = Field(
        default=False,
        description="Enable logging to file"
    )
    file_path: Optional[Path] = Field(
        default=None,
        description="Path to log file"
    )
    file_max_bytes: int = Field(
        default=10485760,
        description="Maximum log file size in bytes (default: 10MB)"
    )
    file_backup_count: int = Field(
        default=5,
        description="Number of backup log files to keep"
    )

    # Structured logging
    json_enabled: bool = Field(
        default=False,
        description="Enable JSON structured logging"
    )

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Validate logging level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v_upper


class SPARQLAgentSettings(BaseSettings):
    """Main configuration settings for SPARQL Agent."""

    model_config = SettingsConfigDict(
        env_prefix="SPARQL_AGENT_",
        case_sensitive=False,
        env_nested_delimiter="__",
        extra="allow"
    )

    # Sub-configurations
    ontology: OntologySettings = Field(default_factory=OntologySettings)
    endpoint: EndpointSettings = Field(default_factory=EndpointSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)

    # General settings
    config_dir: Path = Field(
        default=Path(__file__).parent,
        description="Configuration directory path"
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )

    # Loaded configurations from YAML files
    _endpoints_config: Dict[str, Any] = {}
    _ontologies_config: Dict[str, Any] = {}
    _prompts_config: Dict[str, Any] = {}

    def __init__(self, **kwargs):
        """Initialize settings and load YAML configurations."""
        super().__init__(**kwargs)
        self._load_yaml_configs()

    def _load_yaml_configs(self) -> None:
        """Load configuration from YAML files."""
        yaml_files = {
            "_endpoints_config": "endpoints.yaml",
            "_ontologies_config": "ontologies.yaml",
            "_prompts_config": "prompts.yaml"
        }

        for attr, filename in yaml_files.items():
            filepath = self.config_dir / filename
            if filepath.exists():
                try:
                    with open(filepath, 'r') as f:
                        config = yaml.safe_load(f)
                        setattr(self, attr, config or {})
                except Exception as e:
                    print(f"Warning: Failed to load {filename}: {e}")
                    setattr(self, attr, {})
            else:
                setattr(self, attr, {})

    def get_endpoint_config(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific SPARQL endpoint.

        Args:
            name: Endpoint name (e.g., 'uniprot', 'clinvar', 'rdfportal')

        Returns:
            Endpoint configuration dictionary or None if not found
        """
        return self._endpoints_config.get("endpoints", {}).get(name)

    def get_ontology_config(self, ontology_id: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific ontology.

        Args:
            ontology_id: Ontology identifier (e.g., 'efo', 'mondo', 'hp')

        Returns:
            Ontology configuration dictionary or None if not found
        """
        return self._ontologies_config.get("ontologies", {}).get(ontology_id)

    def get_prompt_template(self, name: str) -> Optional[str]:
        """
        Get a prompt template by name.

        Args:
            name: Prompt template name

        Returns:
            Prompt template string or None if not found
        """
        return self._prompts_config.get("prompts", {}).get(name, {}).get("template")

    def list_endpoints(self) -> List[str]:
        """List all configured SPARQL endpoints."""
        return list(self._endpoints_config.get("endpoints", {}).keys())

    def list_ontologies(self) -> List[str]:
        """List all configured ontologies."""
        return list(self._ontologies_config.get("ontologies", {}).keys())

    def list_prompts(self) -> List[str]:
        """List all configured prompt templates."""
        return list(self._prompts_config.get("prompts", {}).keys())

    def update_config(self, **kwargs) -> None:
        """
        Update configuration at runtime.

        Args:
            **kwargs: Configuration values to update
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def reload_yaml_configs(self) -> None:
        """Reload YAML configuration files."""
        self._load_yaml_configs()

    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary."""
        return {
            "ontology": self.ontology.model_dump(),
            "endpoint": self.endpoint.model_dump(),
            "llm": self.llm.model_dump(),
            "logging": self.logging.model_dump(),
            "debug": self.debug,
            "config_dir": str(self.config_dir)
        }


# Global settings instance
_settings: Optional[SPARQLAgentSettings] = None


def get_settings(reload: bool = False) -> SPARQLAgentSettings:
    """
    Get or create the global settings instance.

    Args:
        reload: Force reload of settings

    Returns:
        SPARQLAgentSettings instance
    """
    global _settings
    if _settings is None or reload:
        _settings = SPARQLAgentSettings()
    return _settings


def reset_settings() -> None:
    """Reset the global settings instance."""
    global _settings
    _settings = None
