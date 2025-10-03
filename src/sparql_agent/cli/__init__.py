"""
Command-line interface module.

This module provides the CLI for SPARQL Agent including:
- Query execution and generation
- Endpoint discovery and validation
- Batch processing capabilities
- Interactive shell
- Ontology search
- Configuration management
"""

from .main import cli, main

__all__ = ['cli', 'main']
