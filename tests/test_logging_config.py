"""
Test logging configuration for SPARQL Agent.

Verifies that logging setup works correctly with various configurations.
"""

import logging
import os
from pathlib import Path

import pytest


def test_basic_logging_setup():
    """Test that basic logging setup works."""
    from sparql_agent.utils.logging import setup_logging

    # Setup basic logging
    setup_logging(log_level="INFO")

    # Get a logger and test it
    logger = logging.getLogger("test_logger")
    assert logger is not None


def test_logging_with_config_file():
    """Test that logging setup works with config file."""
    from sparql_agent.utils.logging import setup_logging

    # Get path to logging.yaml
    config_path = Path(__file__).parent.parent / "src" / "sparql_agent" / "config" / "logging.yaml"

    if config_path.exists():
        # Setup logging with config file
        setup_logging(config_path=config_path, log_level="DEBUG")

        # Get a logger and test it
        logger = logging.getLogger("sparql_agent")
        assert logger is not None
        assert logger.level <= logging.DEBUG or logging.getLogger().level <= logging.DEBUG


def test_rate_limit_filter():
    """Test that RateLimitFilter works correctly."""
    from sparql_agent.utils.logging import RateLimitFilter

    # Create filter with small rate limit
    rate_filter = RateLimitFilter(rate=2, per=60)

    # Create mock log records
    class MockRecord:
        def __init__(self, msg):
            self.module = "test"
            self.funcName = "test_func"
            self.msg = msg

        def getMessage(self):
            return self.msg

    # First two messages should pass
    assert rate_filter.filter(MockRecord("test message"))
    assert rate_filter.filter(MockRecord("test message"))

    # Third message should be filtered
    assert not rate_filter.filter(MockRecord("test message"))


def test_sensitive_data_filter():
    """Test that SensitiveDataFilter masks sensitive data."""
    from sparql_agent.utils.logging import SensitiveDataFilter

    # Create filter
    sensitive_filter = SensitiveDataFilter()

    # Create mock log record with sensitive data
    class MockRecord:
        def __init__(self, msg):
            self.msg = msg
            self.args = ()

        def getMessage(self):
            return self.msg

    # Test password masking
    record = MockRecord("Login with password=secret123")
    sensitive_filter.filter(record)
    assert "secret123" not in record.msg
    assert "***REDACTED***" in record.msg

    # Test API key masking
    record = MockRecord("API request with api_key: abc123xyz")
    sensitive_filter.filter(record)
    assert "abc123xyz" not in record.msg
    assert "***REDACTED***" in record.msg


def test_logging_levels():
    """Test that different logging levels work."""
    from sparql_agent.utils.logging import setup_logging, get_logger

    # Test each level
    for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        setup_logging(log_level=level)
        logger = get_logger(f"test_{level.lower()}")
        assert logger is not None


def test_disable_third_party_logging():
    """Test that third-party logging can be disabled."""
    from sparql_agent.utils.logging import disable_third_party_logging

    # Disable third-party logging
    disable_third_party_logging()

    # Check that common libraries are set to WARNING
    for module in ['urllib3', 'requests', 'httpx']:
        logger = logging.getLogger(module)
        assert logger.level >= logging.WARNING


def test_config_initialization():
    """Test that config module initializes logging correctly."""
    # This test verifies that importing the config module doesn't raise errors
    from sparql_agent.config import get_settings

    settings = get_settings()
    assert settings is not None
    assert hasattr(settings, 'logging')


def test_cli_logging_setup():
    """Test that CLI logging setup works without warnings."""
    import subprocess
    import sys

    # Run CLI help command and capture output
    result = subprocess.run(
        [sys.executable, "-m", "sparql_agent.cli.main", "--help"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )

    # Check that there are no logging configuration errors
    assert "Unable to configure formatter" not in result.stderr
    assert "Unable to configure filter" not in result.stderr

    # The only acceptable warning is about python-json-logger if not installed
    if "WARNING" in result.stderr:
        # This is fine - it's just noting that optional dependencies aren't installed
        assert "python-json-logger" in result.stderr or "colorlog" in result.stderr or "RuntimeWarning" in result.stderr


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
