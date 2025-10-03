"""
Logging utilities for SPARQL Agent.

Provides custom filters, formatters, and helper functions for logging configuration.
"""

import logging
import logging.config
import re
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml


class RateLimitFilter(logging.Filter):
    """
    Filter that rate-limits log messages to prevent log flooding.

    Limits the number of log messages that can be emitted within a time window.

    Args:
        rate: Maximum number of messages per time window
        per: Time window in seconds
        name: Optional filter name
    """

    def __init__(self, rate: int = 10, per: int = 60, name: str = ""):
        super().__init__(name)
        self.rate = rate
        self.per = per
        self.message_counts: Dict[str, List[float]] = defaultdict(list)

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter log records based on rate limiting.

        Args:
            record: The log record to filter

        Returns:
            True if the record should be logged, False otherwise
        """
        # Create a unique key for this message
        key = f"{record.module}:{record.funcName}:{record.getMessage()}"

        # Get current time
        now = time.time()

        # Remove timestamps outside our time window
        self.message_counts[key] = [
            timestamp for timestamp in self.message_counts[key]
            if now - timestamp < self.per
        ]

        # Check if we're under the rate limit
        if len(self.message_counts[key]) < self.rate:
            self.message_counts[key].append(now)
            return True

        return False


class SensitiveDataFilter(logging.Filter):
    """
    Filter that removes or masks sensitive data from log messages.

    Searches for patterns like passwords, API keys, tokens, etc. and replaces them
    with a masked value.

    Args:
        patterns: List of sensitive field names to filter (e.g., 'password', 'api_key')
        mask: String to use for masking sensitive data
        name: Optional filter name
    """

    def __init__(
        self,
        patterns: Optional[List[str]] = None,
        mask: str = "***REDACTED***",
        name: str = ""
    ):
        super().__init__(name)
        self.patterns = patterns or ["password", "api_key", "secret", "token"]
        self.mask = mask

        # Compile regex patterns for each sensitive field
        self.regex_patterns = []
        for pattern in self.patterns:
            # Match patterns like: password="value", password: value, password='value'
            escaped_pattern = re.escape(pattern)
            regex = re.compile(
                r'(' + escaped_pattern + r'[\s]*[=:]+[\s]*["\']?)([^"\'}\s,]+)(["\'}},\s]?)',
                re.IGNORECASE
            )
            self.regex_patterns.append(regex)

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter log records to remove sensitive data.

        Args:
            record: The log record to filter

        Returns:
            Always True (we modify the record but don't suppress it)
        """
        # Get the message
        msg = record.getMessage()

        # Replace sensitive data in the message
        for regex in self.regex_patterns:
            msg = regex.sub(rf'\1{self.mask}\3', msg)

        # Update the record's message
        record.msg = msg
        record.args = ()

        return True


def setup_logging(
    config_path: Optional[Path] = None,
    log_level: Optional[str] = None,
    enable_file_logging: bool = False,
    enable_json_logging: bool = False,
    log_dir: Optional[Path] = None,
) -> None:
    """
    Setup logging configuration for SPARQL Agent.

    Args:
        config_path: Path to logging YAML configuration file
        log_level: Override log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_file_logging: Enable file-based logging
        enable_json_logging: Enable JSON format logging
        log_dir: Directory for log files (default: ./logs)
    """
    # Set default log directory
    if log_dir is None:
        log_dir = Path("logs")

    # Create log directory if needed
    if enable_file_logging:
        log_dir.mkdir(exist_ok=True)

    # If config path provided, try to load it
    if config_path and config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)

            # Remove handlers that require missing dependencies
            if 'formatters' in config:
                formatters_to_remove = []

                # Check for JSON formatter dependency
                if 'json' in config['formatters']:
                    try:
                        import pythonjsonlogger.jsonlogger  # noqa: F401
                    except ImportError:
                        formatters_to_remove.append('json')
                        # Only log at debug level - this is optional
                        if enable_json_logging:
                            logging.info(
                                "python-json-logger not installed. JSON logging disabled. "
                                "Install with: pip install python-json-logger"
                            )

                # Check for colored formatter dependency
                if 'colored' in config['formatters']:
                    try:
                        import colorlog  # noqa: F401
                    except ImportError:
                        formatters_to_remove.append('colored')
                        # Fall back to standard formatter for console
                        if 'handlers' in config and 'console' in config['handlers']:
                            config['handlers']['console']['formatter'] = 'standard'

                # Remove formatters that can't be used
                for formatter in formatters_to_remove:
                    del config['formatters'][formatter]

                # Remove handlers that use missing formatters
                if 'handlers' in config:
                    handlers_to_remove = []
                    for handler_name, handler_config in config['handlers'].items():
                        if handler_config.get('formatter') in formatters_to_remove:
                            if enable_file_logging and 'file' in handler_name:
                                # Fall back to detailed formatter for file handlers
                                handler_config['formatter'] = 'detailed'
                            else:
                                # Remove handlers that can't work without their formatter
                                handlers_to_remove.append(handler_name)

                    for handler in handlers_to_remove:
                        del config['handlers'][handler]

                    # Update loggers to remove missing handlers
                    if 'loggers' in config:
                        for logger_config in config['loggers'].values():
                            if 'handlers' in logger_config:
                                logger_config['handlers'] = [
                                    h for h in logger_config['handlers']
                                    if h not in handlers_to_remove
                                ]

                    # Update root logger
                    if 'root' in config and 'handlers' in config['root']:
                        config['root']['handlers'] = [
                            h for h in config['root']['handlers']
                            if h not in handlers_to_remove
                        ]

            # Disable file logging if not requested
            if not enable_file_logging and 'handlers' in config:
                file_handlers = [
                    name for name in config['handlers'].keys()
                    if name and 'file' in name.lower()
                ]
                for handler in file_handlers:
                    del config['handlers'][handler]

                # Remove file handlers from loggers
                if 'loggers' in config:
                    for logger_config in config['loggers'].values():
                        if 'handlers' in logger_config:
                            logger_config['handlers'] = [
                                h for h in logger_config['handlers']
                                if h not in file_handlers
                            ]

                # Remove file handlers from root
                if 'root' in config and 'handlers' in config['root']:
                    config['root']['handlers'] = [
                        h for h in config['root']['handlers']
                        if h not in file_handlers
                    ]

            # Override log level if specified
            if log_level:
                level_str = log_level.upper() if log_level else 'INFO'
                if 'root' in config:
                    config['root']['level'] = level_str
                if 'loggers' in config:
                    for logger_config in config['loggers'].values():
                        if isinstance(logger_config, dict) and 'level' in logger_config:
                            logger_config['level'] = level_str

            # Clean up any None or invalid values from handler lists
            if 'loggers' in config:
                for logger_config in config['loggers'].values():
                    if isinstance(logger_config, dict) and 'handlers' in logger_config:
                        logger_config['handlers'] = [
                            h for h in logger_config['handlers']
                            if h is not None and h != ''
                        ]

            if 'root' in config and 'handlers' in config['root']:
                config['root']['handlers'] = [
                    h for h in config['root']['handlers']
                    if h is not None and h != ''
                ]

            # Clean up None keys from handlers dictionary
            if 'handlers' in config:
                config['handlers'] = {
                    k: v for k, v in config['handlers'].items()
                    if k is not None and k != ''
                }

            # Apply the configuration
            logging.config.dictConfig(config)
            return

        except Exception as e:
            import traceback
            logging.warning(
                f"Failed to load logging configuration from {config_path}: {e}\n"
                f"Traceback: {traceback.format_exc()}"
            )

    # Fallback to basic configuration
    level_str = log_level.upper() if log_level else 'INFO'
    logging.basicConfig(
        level=getattr(logging, level_str),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    Args:
        name: Name for the logger (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def configure_module_logging(
    module_name: str,
    level: Optional[str] = None,
    handlers: Optional[List[str]] = None,
) -> None:
    """
    Configure logging for a specific module.

    Args:
        module_name: Name of the module to configure
        level: Log level for this module
        handlers: List of handler names to use
    """
    logger = logging.getLogger(module_name)

    if level:
        logger.setLevel(getattr(logging, level.upper()))

    if handlers:
        # Remove existing handlers
        logger.handlers.clear()

        # Add new handlers
        root_logger = logging.getLogger()
        for handler_name in handlers:
            for handler in root_logger.handlers:
                if handler.get_name() == handler_name:
                    logger.addHandler(handler)


def disable_third_party_logging(modules: Optional[List[str]] = None) -> None:
    """
    Disable or reduce logging from third-party libraries.

    Args:
        modules: List of module names to configure (default: common noisy libraries)
    """
    if modules is None:
        modules = [
            'urllib3',
            'requests',
            'SPARQLWrapper',
            'httpx',
            'httpcore',
            'asyncio',
            'aiohttp',
        ]

    for module in modules:
        logging.getLogger(module).setLevel(logging.WARNING)
