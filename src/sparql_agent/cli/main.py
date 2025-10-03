"""
SPARQL Agent CLI.

Command-line interface for the SPARQL Agent system with comprehensive
commands for querying, discovering, validating, formatting, and serving.
"""

import csv
import io
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

import click

from ..config.settings import get_settings, SPARQLAgentSettings
from ..core.exceptions import (
    SPARQLAgentError,
    QueryGenerationError,
    QueryValidationError,
    EndpointError,
)
from ..discovery.capabilities import CapabilitiesDetector
from ..execution.validator import QueryValidator
from ..execution.executor import QueryExecutor, execute_query_with_validation
from ..query.schema_tools import create_schema_tools
from ..formatting.structured import (
    JSONFormatter,
    CSVFormatter,
    DataFrameFormatter,
    OutputFormat,
)
from ..ontology.ols_client import OLSClient, list_common_ontologies
from ..query.generator import SPARQLGenerator, GenerationStrategy
from ..query.intent_parser import IntentParser
from ..llm.client import LLMClient
from ..core.types import SchemaInfo, OntologyInfo, EndpointInfo
from ..schema.void_parser import VoIDParser, VoIDExtractor
from ..schema.shex_parser import ShExParser
from ..query.smart_generator import create_smart_generator

# Initialize logger
logger = logging.getLogger(__name__)


# ============================================================================
# CLI Setup
# ============================================================================

@click.group()
@click.option(
    '--config',
    type=click.Path(exists=True, dir_okay=False),
    help='Path to configuration file',
    envvar='SPARQL_AGENT_CONFIG'
)
@click.option(
    '--verbose',
    '-v',
    count=True,
    help='Enable verbose output (-v: INFO, -vv: DEBUG)'
)
@click.option(
    '--debug',
    is_flag=True,
    help='Enable debug mode with stack traces'
)
@click.option(
    '--profile',
    type=str,
    help='Configuration profile to use',
    envvar='SPARQL_AGENT_PROFILE'
)
@click.pass_context
def cli(ctx, config: Optional[str], verbose: int, debug: bool, profile: Optional[str]):
    """
    SPARQL Agent - Natural Language to SPARQL Query System.

    A comprehensive tool for working with SPARQL endpoints using natural language,
    ontology mapping, and intelligent query generation.

    \b
    Common Usage:
        # Query a SPARQL endpoint with natural language
        uv run sparql-agent query "Find all proteins from human"

        # Discover endpoint capabilities
        uv run sparql-agent discover https://query.wikidata.org/sparql

        # Start interactive shell
        uv run sparql-agent interactive

        # Run API server
        uv run sparql-agent serve --port 8000

    \b
    Environment Variables:
        SPARQL_AGENT_CONFIG       - Path to configuration file
        SPARQL_AGENT_PROFILE      - Configuration profile name
        SPARQL_AGENT_*            - Override any setting (e.g., SPARQL_AGENT_LLM__MODEL_NAME)

    For detailed help on any command, use: uv run sparql-agent COMMAND --help
    """
    # Ensure context object exists
    ctx.ensure_object(dict)

    # Load settings
    settings = get_settings()

    # Update settings based on CLI options
    if debug:
        settings.debug = True
        settings.logging.level = "DEBUG"
        # Reconfigure logging for debug mode
        from ..utils.logging import setup_logging
        setup_logging(log_level="DEBUG")
    elif verbose >= 2:
        settings.logging.level = "DEBUG"
        from ..utils.logging import setup_logging
        setup_logging(log_level="DEBUG")
    elif verbose == 1:
        settings.logging.level = "INFO"
        from ..utils.logging import setup_logging
        setup_logging(log_level="INFO")

    # Store in context
    ctx.obj['settings'] = settings
    ctx.obj['verbose'] = verbose > 0
    ctx.obj['debug'] = debug
    ctx.obj['profile'] = profile


# ============================================================================
# Query Command
# ============================================================================

@cli.command()
@click.argument('query', type=str)
@click.option(
    '--endpoint',
    '-e',
    help='SPARQL endpoint URL',
    envvar='SPARQL_AGENT_ENDPOINT'
)
@click.option(
    '--ontology',
    '-o',
    help='Ontology to use for mapping (e.g., efo, mondo, hp)'
)
@click.option(
    '--format',
    '-f',
    type=click.Choice(['json', 'csv', 'tsv', 'table', 'sparql'], case_sensitive=False),
    default='table',
    help='Output format'
)
@click.option(
    '--output',
    type=click.Path(),
    help='Save output to file instead of stdout'
)
@click.option(
    '--limit',
    '-l',
    type=int,
    help='Maximum number of results'
)
@click.option(
    '--timeout',
    '-t',
    type=int,
    help='Query timeout in seconds'
)
@click.option(
    '--execute/--no-execute',
    default=True,
    help='Execute the generated query'
)
@click.option(
    '--show-sparql',
    is_flag=True,
    help='Show generated SPARQL query'
)
@click.option(
    '--strategy',
    type=click.Choice(['auto', 'template', 'llm', 'hybrid'], case_sensitive=False),
    default='auto',
    help='Query generation strategy'
)
@click.option(
    '--llm-provider',
    type=click.Choice(['anthropic', 'openai', 'local'], case_sensitive=False),
    help='LLM provider to use for query generation'
)
@click.option(
    '--schema',
    '-s',
    type=click.Path(exists=True, readable=True),
    help='Schema file (VOID, SHEX, or discovery JSON) to use for intelligent query generation'
)
@click.option(
    '--use-smart-generator',
    is_flag=True,
    help='Use the smart schema-driven query generator instead of basic generation'
)
@click.option(
    '--max-validation-retries',
    type=int,
    default=5,
    help='Maximum validation retry attempts for query fixes (default: 5)'
)
@click.option(
    '--max-execution-retries',
    type=int,
    default=3,
    help='Maximum execution retry attempts after endpoint errors (default: 3)'
)
@click.pass_context
def query(
    ctx,
    query: str,
    endpoint: Optional[str],
    ontology: Optional[str],
    format: str,
    output: Optional[str],
    limit: Optional[int],
    timeout: Optional[int],
    execute: bool,
    show_sparql: bool,
    strategy: str,
    llm_provider: Optional[str],
    schema: Optional[str],
    use_smart_generator: bool,
    max_validation_retries: int,
    max_execution_retries: int
):
    """
    Generate and execute a SPARQL query from natural language.

    QUERY can be either natural language or a direct SPARQL query. The tool
    will automatically detect and handle both formats.

    \b
    Examples:
        # Natural language query
        uv run sparql-agent query "Find all proteins from human"

        # Query with specific endpoint
        uv run sparql-agent query "Show diseases related to diabetes" \\
            --endpoint https://rdf.uniprot.org/sparql

        # Query with ontology mapping
        uv run sparql-agent query "List genes with GO term DNA binding" \\
            --ontology go --format csv

        # Use discovered schema for intelligent query generation
        uv run sparql-agent query "Find people born in Paris" \\
            --schema wikidata_discovery.json --use-smart-generator

        # Use VOID metadata for schema-driven queries
        uv run sparql-agent query "Show proteins involved in DNA repair" \\
            --schema uniprot_void.ttl

        # Generate SPARQL without execution
        uv run sparql-agent query "Find all classes" --no-execute

        # Save results to file
        uv run sparql-agent query "Find proteins" --output results.json
    """
    settings: SPARQLAgentSettings = ctx.obj['settings']
    verbose = ctx.obj['verbose']

    try:
        # Resolve endpoint
        if endpoint:
            endpoint_url = endpoint
        elif settings._endpoints_config.get("endpoints"):
            # Use first configured endpoint as default
            default_endpoint = list(settings._endpoints_config["endpoints"].values())[0]
            endpoint_url = default_endpoint.get("url")
            if not endpoint_url:
                click.echo("Error: No endpoint specified and no default configured", err=True)
                sys.exit(1)
        else:
            click.echo("Error: No endpoint specified. Use --endpoint or configure a default.", err=True)
            sys.exit(1)

        if verbose:
            click.echo(f"Using endpoint: {endpoint_url}")

        # Load ontology if specified
        ontology_info = None
        if ontology:
            if verbose:
                click.echo(f"Loading ontology: {ontology}")
            # TODO: Integrate ontology loading
            # For now, we'll just note it

        # Build constraints
        constraints = {}
        if limit:
            constraints['limit'] = limit
        if timeout:
            constraints['timeout'] = timeout

        # Initialize LLM client if available
        llm_client = None
        if verbose:
            click.echo("Attempting to initialize LLM client...", err=True)
        try:
            import os
            from ..llm.anthropic_provider import create_anthropic_provider
            from ..llm.openai_provider import create_openai_provider

            # Try to get API key from environment if not in settings
            env_anthropic = os.environ.get('ANTHROPIC_API_KEY')
            env_openai = os.environ.get('OPENAI_API_KEY')
            anthropic_key = settings.llm.api_key or env_anthropic
            openai_key = settings.llm.api_key or env_openai

            if verbose:
                click.echo(f"Settings API key: {bool(settings.llm.api_key)}", err=True)
                click.echo(f"Env ANTHROPIC_API_KEY: {bool(env_anthropic)}", err=True)
                click.echo(f"Env OPENAI_API_KEY: {bool(env_openai)}", err=True)
                click.echo(f"Final anthropic_key: {bool(anthropic_key)}", err=True)
                click.echo(f"Final openai_key: {bool(openai_key)}", err=True)
                click.echo(f"LLM provider: {llm_provider}", err=True)

            if llm_provider == 'anthropic' or (not llm_provider and (anthropic_key or settings.llm.provider == 'anthropic')):
                if anthropic_key:
                    model = settings.llm.model_name if 'claude' in settings.llm.model_name.lower() else "claude-3-5-sonnet-20241022"
                    llm_client = create_anthropic_provider(
                        api_key=anthropic_key,
                        model_name=model
                    )
                    if verbose:
                        click.echo(f"Using Anthropic LLM: {model}")
            elif llm_provider == 'openai' or (not llm_provider and (openai_key or settings.llm.provider == 'openai')):
                if openai_key:
                    llm_client = create_openai_provider(
                        api_key=openai_key,
                        model_name=settings.llm.model_name
                    )
                    if verbose:
                        click.echo(f"Using OpenAI LLM: {settings.llm.model_name}")
        except Exception as e:
            import traceback
            click.echo(f"Warning: LLM client not available: {e}", err=True)
            if verbose:
                click.echo(traceback.format_exc(), err=True)
            click.echo("Falling back to template-only generation (may fail without context)", err=True)

        # Load schema information if provided
        schema_info = None
        void_data = None
        shex_schemas = {}

        if schema:
            if verbose:
                click.echo(f"Loading schema from: {schema}")

            try:
                with open(schema, 'r') as f:
                    schema_content = f.read()

                # Determine schema type and parse
                if schema.endswith('.json'):
                    # Assume discovery JSON format
                    schema_data = json.loads(schema_content)
                    schema_info = SchemaInfo(
                        namespaces=schema_data.get('namespaces', {}),
                        classes=set(schema_data.get('classes', [])),
                        properties=set(schema_data.get('properties', []))
                    )
                elif schema.endswith(('.shex', '.shex')):
                    # Parse ShEx schema
                    parser = ShExParser()
                    shex_schema = parser.parse(schema_content)
                    shex_schemas['main'] = shex_schema
                elif schema.endswith(('.ttl', '.turtle', '.rdf')):
                    # Parse VOID data
                    void_parser = VoIDParser()
                    void_data = void_parser.parse(schema_content)

                if verbose:
                    click.echo(f"✓ Schema loaded successfully")

            except Exception as e:
                click.echo(f"Warning: Could not load schema: {e}", err=True)

        # Choose generator based on options
        if use_smart_generator or schema or (schema_info or void_data or shex_schemas):
            if verbose:
                click.echo("Using smart schema-driven generator...")

            if not llm_client:
                click.echo("Error: Smart generator requires LLM client but none is available", err=True)
                sys.exit(1)

            # Use smart generator with schema tools
            # Skip discovery if schema is provided
            skip_discovery = bool(schema)
            smart_generator = create_smart_generator(endpoint_url, llm_client, skip_discovery=skip_discovery)

            # Load schema data into the generator's tools
            if schema_info:
                # Load JSON schema info into tools
                smart_generator.schema_tools.available_prefixes.update(schema_info.namespaces)
                # Could add more schema_info loading here
            if void_data:
                smart_generator.schema_tools.load_void_data(void_data)
            if shex_schemas:
                for name, schema_obj in shex_schemas.items():
                    smart_generator.schema_tools.load_shex_schema(schema_obj.to_shex(), name)

            # Generate using smart generator
            result = smart_generator.generate_query(query)

            # Convert smart generator result to standard format
            class SmartResult:
                def __init__(self, smart_result):
                    self.query = smart_result.get('query', '')
                    self.confidence = smart_result.get('confidence', 0.0)
                    self.explanation = smart_result.get('reasoning', '')
                    self.validation_issues = smart_result.get('validation', {}).get('issues', [])
                    self.steps = smart_result.get('steps', [])

            result = SmartResult(result)

        else:
            # Use standard generator
            if verbose:
                click.echo(f"Using standard generator with {strategy} strategy...")

            generator = SPARQLGenerator(
                llm_client=llm_client,
                enable_validation=True,
                enable_optimization=True
            )

            # Map strategy
            strategy_map = {
                'auto': GenerationStrategy.AUTO,
                'template': GenerationStrategy.TEMPLATE,
                'llm': GenerationStrategy.LLM,
                'hybrid': GenerationStrategy.HYBRID,
            }

            # Pass schema_info if available
            generate_kwargs = {
                'natural_language': query,
                'strategy': strategy_map[strategy.lower()],
                'constraints': constraints
            }

            if schema_info:
                generate_kwargs['schema_info'] = schema_info

            result = generator.generate(**generate_kwargs)

        # Show SPARQL if requested
        if show_sparql or not execute:
            click.echo("\n" + "="*60)
            click.echo("Generated SPARQL Query:")
            click.echo("="*60)
            click.echo(result.query)
            click.echo("="*60 + "\n")

            if verbose:
                click.echo(f"Confidence: {result.confidence:.2%}")
                if result.explanation:
                    click.echo(f"Explanation: {result.explanation}")

        # Execute if requested
        if execute:
            if verbose:
                click.echo("Executing query with validation and retry logic...")

            # Create schema tools for validation (skip discovery for speed unless smart generator)
            schema_tools = None
            if use_smart_generator and schema:
                # Use schema tools if we have schema and are using smart generator
                try:
                    schema_tools = create_schema_tools(endpoint_url, skip_discovery=True)
                    if verbose:
                        click.echo("Using schema tools for validation")
                except Exception as e:
                    if verbose:
                        click.echo(f"Warning: Could not create schema tools: {e}")

            # Execute with validation and retry
            try:
                query_result, execution_metadata = execute_query_with_validation(
                    query=result.query,
                    endpoint=endpoint_url,
                    original_intent=query,
                    llm_client=llm_client,
                    schema_tools=schema_tools,
                    max_retries=max_validation_retries,
                    max_execution_retries=max_execution_retries,
                    timeout=timeout or 60
                )

                if verbose and execution_metadata:
                    if execution_metadata.get('pre_validation_attempts', 0) > 1:
                        click.echo(f"✓ Query validated after {execution_metadata['pre_validation_attempts']} attempt(s)")
                    if execution_metadata.get('execution_attempts', 0) > 1:
                        click.echo(f"✓ Query executed after {execution_metadata['execution_attempts']} attempt(s)")
                    if execution_metadata.get('final_query') != result.query:
                        click.echo("✓ Query was modified during validation/retry process")

            except Exception as e:
                click.echo(f"Error executing query: {e}", err=True)
                if verbose:
                    import traceback
                    click.echo(traceback.format_exc(), err=True)
                sys.exit(1)

            # Format output
            output_text = None

            if format == 'json':
                formatter = JSONFormatter(pretty=True, include_metadata=verbose)
                output_text = formatter.format(query_result)

            elif format == 'csv':
                formatter = CSVFormatter(delimiter=',')
                output_text = formatter.format(query_result)

            elif format == 'tsv':
                formatter = CSVFormatter(delimiter='\t')
                output_text = formatter.format(query_result)

            elif format == 'table':
                # Use DataFrame for table display
                try:
                    formatter = DataFrameFormatter()
                    df = formatter.format(query_result)
                    output_text = df.to_string()
                except ImportError:
                    click.echo("Error: pandas required for table format. Install with: uv add pandas", err=True)
                    sys.exit(1)

            elif format == 'sparql':
                # Just show the SPARQL query
                output_text = result.query

            # Write output
            if output:
                Path(output).write_text(output_text, encoding='utf-8')
                click.echo(f"Results saved to: {output}")
            else:
                click.echo(output_text)

            if verbose:
                click.echo(f"\nTotal results: {len(query_result.bindings)}")
                click.echo(f"Execution time: {query_result.execution_time:.3f}s")

    except QueryGenerationError as e:
        click.echo(f"Error generating query: {e}", err=True)
        if verbose and hasattr(e, 'details'):
            click.echo(f"Details: {e.details}", err=True)
        sys.exit(1)

    except EndpointError as e:
        click.echo(f"Endpoint error: {e}", err=True)
        sys.exit(1)

    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        if ctx.obj['debug']:
            raise
        sys.exit(1)


# ============================================================================
# Discover Command
# ============================================================================

@cli.command()
@click.argument('endpoint', type=str)
@click.option(
    '--timeout',
    '-t',
    type=int,
    default=30,
    help='Discovery timeout in seconds'
)
@click.option(
    '--output',
    '-o',
    type=click.Path(),
    help='Save discovery results to file'
)
@click.option(
    '--format',
    '-f',
    type=click.Choice(['json', 'yaml', 'text'], case_sensitive=False),
    default='text',
    help='Output format'
)
@click.option(
    '--fast',
    is_flag=True,
    help='Fast mode: skip expensive queries for quicker results'
)
@click.option(
    '--no-progressive-timeout',
    is_flag=True,
    help='Disable progressive timeout strategy'
)
@click.option(
    '--max-samples',
    type=int,
    default=1000,
    help='Maximum number of samples for discovery queries'
)
@click.option(
    '--analyze-schema',
    is_flag=True,
    help='Perform deep schema analysis (slower but more detailed)'
)
@click.option(
    '--quiet',
    is_flag=True,
    help='Suppress progress messages and noisy error details'
)
@click.option(
    '--verbose-namespaces',
    is_flag=True,
    help='Include all discovered namespaces in output (not truncated)'
)
@click.pass_context
def discover(
    ctx,
    endpoint: str,
    timeout: int,
    output: Optional[str],
    format: str,
    fast: bool,
    no_progressive_timeout: bool,
    max_samples: int,
    analyze_schema: bool,
    quiet: bool,
    verbose_namespaces: bool
):
    """
    Discover capabilities and metadata of a SPARQL endpoint.

    Analyzes the endpoint to detect:
    - SPARQL version and features
    - Available namespaces and prefixes
    - Named graphs
    - Dataset statistics
    - Supported functions
    - Class and property schema (with --analyze-schema)

    Uses progressive timeout strategy by default to handle large endpoints
    like Wikidata gracefully.

    \b
    Examples:
        # Discover endpoint capabilities (fast mode for large endpoints)
        uv run sparql-agent discover https://query.wikidata.org/sparql --fast

        # Full discovery with custom timeout
        uv run sparql-agent discover https://rdf.uniprot.org/sparql \\
            --timeout 60 --output uniprot-info.json

        # Quick check without progressive timeouts
        uv run sparql-agent discover http://localhost:3030/dataset \\
            --fast --no-progressive-timeout

        # Deep schema analysis (slow)
        uv run sparql-agent discover https://sparql.uniprot.org/sparql \\
            --analyze-schema --timeout 120
    """
    verbose = ctx.obj['verbose'] and not quiet

    try:
        # Set up logging to suppress noisy error responses during discovery
        if quiet:
            # Temporarily set discovery logger to WARNING level to suppress noise
            discovery_logger = logging.getLogger('sparql_agent.discovery')
            execution_logger = logging.getLogger('sparql_agent.execution')
            original_level = discovery_logger.level
            execution_original = execution_logger.level
            discovery_logger.setLevel(logging.ERROR)
            execution_logger.setLevel(logging.ERROR)

        if verbose:
            click.echo(f"Discovering capabilities for: {endpoint}")
            if fast:
                click.echo("Fast mode enabled - skipping expensive queries")
            if not no_progressive_timeout:
                click.echo("Using progressive timeout strategy")
            if quiet:
                click.echo("Quiet mode - suppressing query error details")

        # Initialize detector with new parameters
        detector = CapabilitiesDetector(
            endpoint,
            timeout=timeout,
            fast_mode=fast,
            progressive_timeout=not no_progressive_timeout,
            max_samples=max_samples
        )

        # Progress callback for verbose mode (suppressed if quiet)
        def progress_callback(current, total, message):
            if verbose and not quiet:
                click.echo(f"[{current}/{total}] {message}")

        # Run discovery
        capabilities = detector.detect_all_capabilities(
            progress_callback=progress_callback if verbose and not quiet else None
        )

        # Restore original logging levels
        if quiet:
            discovery_logger.setLevel(original_level)
            execution_logger.setLevel(execution_original)

        # Format output
        if format == 'json':
            output_text = json.dumps(capabilities, indent=2, default=str)

        elif format == 'yaml':
            try:
                import yaml
                output_text = yaml.dump(capabilities, default_flow_style=False)
            except ImportError:
                click.echo("Error: PyYAML required for YAML format. Install with: pip install pyyaml", err=True)
                sys.exit(1)

        elif format == 'text':
            # Human-readable text format
            lines = [
                f"SPARQL Endpoint Discovery Results",
                f"=" * 60,
                f"",
                f"Endpoint: {capabilities.get('endpoint_url', endpoint)}",
            ]

            # Discovery mode info
            if capabilities.get('discovery_mode'):
                lines.append(f"Discovery Mode: {capabilities['discovery_mode']}")

            if capabilities.get('sparql_version'):
                lines.append(f"SPARQL Version: {capabilities['sparql_version']}")

            lines.append("")

            # Named graphs
            if capabilities.get('named_graphs'):
                graph_count = len(capabilities['named_graphs']) if capabilities['named_graphs'] else 0
                lines.append(f"Named Graphs: {graph_count}")
                if graph_count > 0:
                    for graph in capabilities['named_graphs'][:5]:
                        lines.append(f"  - {graph}")
                    if graph_count > 5:
                        lines.append(f"  ... and {graph_count - 5} more")

            # Namespaces
            if capabilities.get('namespaces'):
                ns_count = len(capabilities['namespaces']) if isinstance(capabilities['namespaces'], (list, dict)) else 0
                lines.append(f"\nNamespaces ({ns_count}):")
                namespaces = capabilities['namespaces']
                if isinstance(namespaces, list):
                    for ns in namespaces[:10]:
                        lines.append(f"  - {ns}")
                    if ns_count > 10:
                        lines.append(f"  ... and {ns_count - 10} more")
                elif isinstance(namespaces, dict):
                    for prefix, uri in list(namespaces.items())[:10]:
                        lines.append(f"  {prefix}: {uri}")
                    if ns_count > 10:
                        lines.append(f"  ... and {ns_count - 10} more")

            # Features
            if capabilities.get('features'):
                lines.append(f"\nSupported Features:")
                for feature, supported in capabilities['features'].items():
                    status = "✓" if supported else "✗"
                    lines.append(f"  {status} {feature}")

            # Statistics
            if capabilities.get('statistics'):
                lines.append(f"\nDataset Statistics:")
                for key, value in capabilities['statistics'].items():
                    if not key.endswith('_note'):
                        lines.append(f"  {key}: {value}")
                # Show notes if any
                for key, value in capabilities['statistics'].items():
                    if key.endswith('_note'):
                        lines.append(f"  Note: {value}")

            # Metadata about discovery process
            if capabilities.get('_metadata'):
                metadata = capabilities['_metadata']
                if metadata.get('timed_out_queries') or metadata.get('failed_queries'):
                    lines.append(f"\nDiscovery Issues:")
                    if metadata.get('timed_out_queries'):
                        lines.append(f"  Timed out: {', '.join(metadata['timed_out_queries'])}")
                    if metadata.get('failed_queries'):
                        lines.append(f"  Failed: {', '.join(metadata['failed_queries'])}")

            output_text = "\n".join(lines)

        # Output or save
        if output:
            output_path = Path(output)
            output_path.write_text(output_text, encoding='utf-8')
            click.echo(f"Discovery results saved to: {output}")
        else:
            click.echo(output_text)

    except Exception as e:
        click.echo(f"Discovery failed: {e}", err=True)
        if ctx.obj['debug']:
            raise
        sys.exit(1)


# ============================================================================
# Validate Command
# ============================================================================

@cli.command()
@click.argument('query_file', type=click.Path(exists=True, dir_okay=False))
@click.option(
    '--strict',
    is_flag=True,
    help='Enable strict validation mode'
)
@click.option(
    '--format',
    '-f',
    type=click.Choice(['text', 'json'], case_sensitive=False),
    default='text',
    help='Output format'
)
@click.pass_context
def validate(ctx, query_file: str, strict: bool, format: str):
    """
    Validate a SPARQL query file for syntax and best practices.

    Checks for:
    - Syntax errors
    - Missing prefix declarations
    - Variable consistency
    - URI and literal validation
    - Best practice recommendations

    Examples:

        sparql-agent validate query.sparql

        sparql-agent validate query.rq --strict --format json
    """
    verbose = ctx.obj['verbose']

    try:
        # Read query file
        query_path = Path(query_file)
        query = query_path.read_text(encoding='utf-8')

        if verbose:
            click.echo(f"Validating query from: {query_file}")

        # Validate
        validator = QueryValidator(strict=strict)
        result = validator.validate(query)

        # Format output
        if format == 'json':
            output = {
                'is_valid': result.is_valid,
                'errors': [
                    {
                        'severity': issue.severity.value,
                        'message': issue.message,
                        'line': issue.line,
                        'column': issue.column,
                        'fragment': issue.query_fragment,
                        'suggestion': issue.suggestion,
                        'rule': issue.rule,
                    }
                    for issue in result.issues
                ],
                'metadata': result.metadata
            }
            click.echo(json.dumps(output, indent=2))

        elif format == 'text':
            click.echo(result.format_report())

        # Exit with error code if invalid
        if not result.is_valid:
            sys.exit(1)

    except Exception as e:
        click.echo(f"Validation failed: {e}", err=True)
        if ctx.obj['debug']:
            raise
        sys.exit(1)


# ============================================================================
# Format Command
# ============================================================================

@cli.command()
@click.argument('results_file', type=click.Path(exists=True, dir_okay=False))
@click.option(
    '--output-format',
    '-f',
    type=click.Choice(['json', 'csv', 'tsv', 'table', 'html'], case_sensitive=False),
    default='json',
    help='Output format'
)
@click.option(
    '--output',
    '-o',
    type=click.Path(),
    help='Output file (default: stdout)'
)
@click.option(
    '--pretty',
    is_flag=True,
    help='Pretty-print output (for JSON)'
)
@click.pass_context
def format(ctx, results_file: str, output_format: str, output: Optional[str], pretty: bool):
    """
    Format SPARQL query results into various output formats.

    Converts results from JSON format (standard SPARQL JSON results)
    into other formats like CSV, TSV, or HTML tables.

    Examples:

        sparql-agent format results.json --output-format csv -o results.csv

        sparql-agent format results.json --output-format table

        sparql-agent format results.json -f json --pretty
    """
    verbose = ctx.obj['verbose']

    try:
        # Read results file
        results_path = Path(results_file)
        results_data = json.loads(results_path.read_text(encoding='utf-8'))

        if verbose:
            click.echo(f"Formatting results from: {results_file}")

        # TODO: Parse results into QueryResult object
        # For now, just re-format the JSON

        if output_format == 'json':
            if pretty:
                output_text = json.dumps(results_data, indent=2)
            else:
                output_text = json.dumps(results_data)

        elif output_format in ['csv', 'tsv']:
            delimiter = ',' if output_format == 'csv' else '\t'

            # Extract bindings
            bindings = results_data.get('results', {}).get('bindings', [])
            if not bindings:
                click.echo("No results to format", err=True)
                sys.exit(1)

            # Get variables
            variables = results_data.get('head', {}).get('vars', [])

            # Format as CSV/TSV
            output_buffer = io.StringIO()
            writer = csv.DictWriter(output_buffer, fieldnames=variables, delimiter=delimiter)
            writer.writeheader()

            for binding in bindings:
                row = {var: binding.get(var, {}).get('value', '') for var in variables}
                writer.writerow(row)

            output_text = output_buffer.getvalue()

        elif output_format == 'table':
            try:
                import pandas as pd

                # Extract bindings
                bindings = results_data.get('results', {}).get('bindings', [])
                variables = results_data.get('head', {}).get('vars', [])

                # Convert to DataFrame
                data = []
                for binding in bindings:
                    row = {var: binding.get(var, {}).get('value', '') for var in variables}
                    data.append(row)

                df = pd.DataFrame(data)
                output_text = df.to_string()

            except ImportError:
                click.echo("Error: pandas required for table format. Install with: pip install pandas", err=True)
                sys.exit(1)

        elif output_format == 'html':
            try:
                import pandas as pd

                # Extract bindings
                bindings = results_data.get('results', {}).get('bindings', [])
                variables = results_data.get('head', {}).get('vars', [])

                # Convert to DataFrame
                data = []
                for binding in bindings:
                    row = {var: binding.get(var, {}).get('value', '') for var in variables}
                    data.append(row)

                df = pd.DataFrame(data)
                output_text = df.to_html()

            except ImportError:
                click.echo("Error: pandas required for HTML format. Install with: pip install pandas", err=True)
                sys.exit(1)

        # Output
        if output:
            output_path = Path(output)
            output_path.write_text(output_text, encoding='utf-8')
            click.echo(f"Formatted results saved to: {output}")
        else:
            click.echo(output_text)

    except Exception as e:
        click.echo(f"Formatting failed: {e}", err=True)
        if ctx.obj['debug']:
            raise
        sys.exit(1)


# ============================================================================
# Ontology Commands
# ============================================================================

@cli.group()
def ontology():
    """
    Ontology search and management commands.

    Work with biomedical ontologies using the EBI Ontology Lookup Service.
    """
    pass


@ontology.command('search')
@click.argument('term', type=str)
@click.option(
    '--ontology',
    '-o',
    help='Filter by specific ontology (e.g., efo, mondo, hp)'
)
@click.option(
    '--exact',
    is_flag=True,
    help='Require exact match'
)
@click.option(
    '--limit',
    '-l',
    type=int,
    default=10,
    help='Maximum number of results'
)
@click.option(
    '--format',
    '-f',
    type=click.Choice(['text', 'json', 'csv'], case_sensitive=False),
    default='text',
    help='Output format'
)
@click.pass_context
def ontology_search(ctx, term: str, ontology: Optional[str], exact: bool, limit: int, format: str):
    """
    Search for ontology terms across biomedical ontologies.

    Searches the EBI Ontology Lookup Service for matching terms.

    Examples:

        sparql-agent ontology search "diabetes"

        sparql-agent ontology search "DNA binding" --ontology go --limit 5

        sparql-agent ontology search "heart" --exact --format json
    """
    verbose = ctx.obj['verbose']

    try:
        settings: SPARQLAgentSettings = ctx.obj['settings']

        if verbose:
            click.echo(f"Searching ontologies for: {term}")

        # Initialize OLS client
        client = OLSClient(base_url=settings.ontology.ols_api_base_url)

        # Search
        results = client.search(
            query=term,
            ontology=ontology,
            exact=exact,
            limit=limit
        )

        # Format output
        if format == 'json':
            click.echo(json.dumps(results, indent=2))

        elif format == 'csv':
            if results:
                import csv
                import sys

                writer = csv.DictWriter(
                    sys.stdout,
                    fieldnames=['id', 'label', 'ontology', 'description']
                )
                writer.writeheader()
                for result in results:
                    writer.writerow({
                        'id': result.get('id', ''),
                        'label': result.get('label', ''),
                        'ontology': result.get('ontology', ''),
                        'description': (result.get('description', '') or '')[:100]
                    })

        elif format == 'text':
            if not results:
                click.echo("No results found.")
            else:
                click.echo(f"Found {len(results)} results:\n")
                for i, result in enumerate(results, 1):
                    click.echo(f"{i}. {result['label']} [{result['id']}]")
                    if result.get('ontology'):
                        click.echo(f"   Ontology: {result['ontology']}")
                    if result.get('description'):
                        desc = result['description'][:150]
                        click.echo(f"   {desc}{'...' if len(result['description']) > 150 else ''}")
                    click.echo()

    except Exception as e:
        click.echo(f"Ontology search failed: {e}", err=True)
        if ctx.obj['debug']:
            raise
        sys.exit(1)


@ontology.command('list')
@click.option(
    '--limit',
    '-l',
    type=int,
    default=20,
    help='Maximum number of ontologies to list'
)
@click.option(
    '--format',
    '-f',
    type=click.Choice(['text', 'json'], case_sensitive=False),
    default='text',
    help='Output format'
)
@click.pass_context
def ontology_list(ctx, limit: int, format: str):
    """
    List available ontologies from OLS.

    Shows commonly used biomedical ontologies.

    Examples:

        sparql-agent ontology list

        sparql-agent ontology list --limit 50 --format json
    """
    verbose = ctx.obj['verbose']

    try:
        settings: SPARQLAgentSettings = ctx.obj['settings']

        # Get common ontologies
        ontologies = list_common_ontologies()

        # Format output
        if format == 'json':
            click.echo(json.dumps(ontologies, indent=2))

        elif format == 'text':
            click.echo(f"Common Biomedical Ontologies:\n")
            for onto in ontologies[:limit]:
                click.echo(f"• {onto['name']} [{onto['id'].upper()}]")
                if onto.get('description'):
                    desc = onto['description'][:100]
                    click.echo(f"  {desc}{'...' if len(onto['description']) > 100 else ''}")
                click.echo()

    except Exception as e:
        click.echo(f"Failed to list ontologies: {e}", err=True)
        if ctx.obj['debug']:
            raise
        sys.exit(1)


@ontology.command('info')
@click.argument('ontology_id', type=str)
@click.option(
    '--format',
    '-f',
    type=click.Choice(['text', 'json'], case_sensitive=False),
    default='text',
    help='Output format'
)
@click.pass_context
def ontology_info(ctx, ontology_id: str, format: str):
    """
    Get information about a specific ontology.

    Examples:

        sparql-agent ontology info efo

        sparql-agent ontology info mondo --format json
    """
    verbose = ctx.obj['verbose']

    try:
        settings: SPARQLAgentSettings = ctx.obj['settings']

        # Initialize OLS client
        client = OLSClient(base_url=settings.ontology.ols_api_base_url)

        # Get ontology info
        info = client.get_ontology(ontology_id)

        # Format output
        if format == 'json':
            click.echo(json.dumps(info, indent=2, default=str))

        elif format == 'text':
            click.echo(f"Ontology Information: {ontology_id.upper()}\n")
            click.echo("="*60)
            click.echo(f"Title: {info.get('title', 'N/A')}")
            click.echo(f"ID: {info.get('id', 'N/A')}")
            if info.get('description'):
                click.echo(f"\nDescription:\n{info['description']}")
            click.echo(f"\nVersion: {info.get('version', 'N/A')}")
            click.echo(f"Status: {info.get('status', 'N/A')}")
            click.echo(f"Number of terms: {info.get('num_terms', 'N/A')}")
            if info.get('namespace'):
                click.echo(f"Namespace: {info['namespace']}")
            if info.get('homepage'):
                click.echo(f"Homepage: {info['homepage']}")

    except Exception as e:
        click.echo(f"Failed to get ontology info: {e}", err=True)
        if ctx.obj['debug']:
            raise
        sys.exit(1)


# ============================================================================
# Serve Command
# ============================================================================

@cli.command()
@click.option(
    '--port',
    '-p',
    type=int,
    default=8000,
    help='Port to run the server on'
)
@click.option(
    '--host',
    '-h',
    default='127.0.0.1',
    help='Host to bind to'
)
@click.option(
    '--reload',
    is_flag=True,
    help='Enable auto-reload on code changes'
)
@click.pass_context
def serve(ctx, port: int, host: str, reload: bool):
    """
    Start the SPARQL Agent API server.

    Runs a FastAPI server providing REST API endpoints for
    query generation, execution, and ontology services.

    Examples:

        sparql-agent serve

        sparql-agent serve --port 8080 --host 0.0.0.0

        sparql-agent serve --reload  # Development mode with auto-reload
    """
    verbose = ctx.obj['verbose']

    try:
        # Import FastAPI dependencies
        try:
            import uvicorn
        except ImportError:
            click.echo(
                "Error: uvicorn required for server. Install with: pip install uvicorn[standard]",
                err=True
            )
            sys.exit(1)

        if verbose:
            click.echo(f"Starting SPARQL Agent server on {host}:{port}")

        # Run the server
        uvicorn.run(
            "sparql_agent.web:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info" if verbose else "warning"
        )

    except Exception as e:
        click.echo(f"Server failed to start: {e}", err=True)
        if ctx.obj['debug']:
            raise
        sys.exit(1)


# ============================================================================
# Config Commands
# ============================================================================

@cli.group()
def config():
    """
    Configuration management commands.

    View and manage SPARQL Agent configuration.
    """
    pass


@config.command('show')
@click.option(
    '--format',
    '-f',
    type=click.Choice(['text', 'json', 'yaml'], case_sensitive=False),
    default='text',
    help='Output format'
)
@click.pass_context
def config_show(ctx, format: str):
    """
    Show current configuration.

    Examples:

        sparql-agent config show

        sparql-agent config show --format json
    """
    settings: SPARQLAgentSettings = ctx.obj['settings']

    try:
        if format == 'json':
            config_dict = settings.to_dict()
            click.echo(json.dumps(config_dict, indent=2, default=str))

        elif format == 'yaml':
            try:
                import yaml
                config_dict = settings.to_dict()
                click.echo(yaml.dump(config_dict, default_flow_style=False))
            except ImportError:
                click.echo("Error: PyYAML required for YAML format. Install with: pip install pyyaml", err=True)
                sys.exit(1)

        elif format == 'text':
            click.echo("SPARQL Agent Configuration\n")
            click.echo("="*60)

            # General settings
            click.echo(f"\nGeneral:")
            click.echo(f"  Debug Mode: {settings.debug}")
            click.echo(f"  Config Dir: {settings.config_dir}")

            # Ontology settings
            click.echo(f"\nOntology:")
            click.echo(f"  OLS API URL: {settings.ontology.ols_api_base_url}")
            click.echo(f"  Cache Enabled: {settings.ontology.cache_enabled}")
            click.echo(f"  Cache Directory: {settings.ontology.cache_dir}")
            click.echo(f"  Default Ontologies: {', '.join(settings.ontology.default_ontologies)}")

            # Endpoint settings
            click.echo(f"\nEndpoint:")
            click.echo(f"  Default Timeout: {settings.endpoint.default_timeout}s")
            click.echo(f"  Max Retries: {settings.endpoint.max_retries}")
            click.echo(f"  Rate Limiting: {settings.endpoint.rate_limit_enabled}")

            # LLM settings
            click.echo(f"\nLLM:")
            click.echo(f"  Model: {settings.llm.model_name}")
            click.echo(f"  Temperature: {settings.llm.temperature}")
            click.echo(f"  Max Tokens: {settings.llm.max_tokens}")

            # Logging settings
            click.echo(f"\nLogging:")
            click.echo(f"  Level: {settings.logging.level}")
            click.echo(f"  JSON Format: {settings.logging.json_enabled}")

            # Configured endpoints
            endpoints = settings.list_endpoints()
            if endpoints:
                click.echo(f"\nConfigured Endpoints ({len(endpoints)}):")
                for ep in endpoints[:5]:
                    click.echo(f"  • {ep}")
                if len(endpoints) > 5:
                    click.echo(f"  ... and {len(endpoints) - 5} more")

            # Configured ontologies
            ontologies = settings.list_ontologies()
            if ontologies:
                click.echo(f"\nConfigured Ontologies ({len(ontologies)}):")
                for onto in ontologies[:5]:
                    click.echo(f"  • {onto}")
                if len(ontologies) > 5:
                    click.echo(f"  ... and {len(ontologies) - 5} more")

    except Exception as e:
        click.echo(f"Failed to show configuration: {e}", err=True)
        if ctx.obj['debug']:
            raise
        sys.exit(1)


@config.command('list-endpoints')
@click.pass_context
def config_list_endpoints(ctx):
    """
    List all configured SPARQL endpoints.
    """
    settings: SPARQLAgentSettings = ctx.obj['settings']

    try:
        endpoints = settings._endpoints_config.get("endpoints", {})

        if not endpoints:
            click.echo("No endpoints configured.")
        else:
            click.echo(f"Configured SPARQL Endpoints ({len(endpoints)}):\n")
            for name, config in endpoints.items():
                click.echo(f"• {name}")
                click.echo(f"  URL: {config.get('url', 'N/A')}")
                if config.get('description'):
                    click.echo(f"  Description: {config['description']}")
                click.echo()

    except Exception as e:
        click.echo(f"Failed to list endpoints: {e}", err=True)
        sys.exit(1)


# ============================================================================
# Interactive Command
# ============================================================================

@cli.command()
@click.pass_context
def interactive(ctx):
    """
    Start interactive query builder shell.

    Provides a rich, interactive terminal interface with:
    - Syntax highlighting and auto-completion
    - Multi-line query editing
    - Query history management
    - Beautiful result formatting
    - Schema exploration
    - Ontology search

    Examples:

        sparql-agent interactive

        # Then in the shell:
        sparql> .connect https://query.wikidata.org/sparql
        sparql> SELECT * WHERE { ?s ?p ?o } LIMIT 10
        sparql> .ontology diabetes
        sparql> .help
    """
    try:
        from .interactive import InteractiveShell
    except ImportError as e:
        click.echo(
            "Error: Interactive mode requires additional dependencies.",
            err=True
        )
        click.echo("Install with: pip install rich prompt-toolkit pygments", err=True)
        sys.exit(1)

    try:
        shell = InteractiveShell()
        shell.run()
    except KeyboardInterrupt:
        click.echo("\nInterrupted by user", err=True)
        sys.exit(130)
    except Exception as e:
        click.echo(f"Interactive shell error: {e}", err=True)
        if ctx.obj['debug']:
            raise
        sys.exit(1)


# ============================================================================
# VOID Commands
# ============================================================================

@cli.command()
@click.argument('endpoint_url')
@click.option(
    '--output', '-o',
    help='Output file (default: stdout)'
)
@click.option(
    '--format', '-f',
    type=click.Choice(['turtle', 'json', 'yaml']),
    default='turtle',
    help='Output format'
)
@click.option(
    '--include-stats/--no-stats',
    default=True,
    help='Include dataset statistics'
)
@click.option(
    '--include-classes/--no-classes',
    default=True,
    help='Include class partitions'
)
@click.option(
    '--include-properties/--no-properties',
    default=True,
    help='Include property partitions'
)
@click.pass_context
def void(ctx, endpoint_url: str, output: Optional[str], format: str, include_stats: bool, include_classes: bool, include_properties: bool):
    """Extract VoID (Vocabulary of Interlinked Datasets) metadata from a SPARQL endpoint.

    VoID describes RDF datasets with metadata like statistics, vocabularies,
    and structural information. This command queries the endpoint to extract
    and generate VoID descriptions.

    Examples:
        # Extract VoID metadata from Wikidata
        uv run sparql-agent void https://query.wikidata.org/sparql

        # Save VoID as JSON
        uv run sparql-agent void https://sparql.uniprot.org/sparql -f json -o uniprot_void.json

        # Extract only basic metadata without stats
        uv run sparql-agent void https://rdfportal.org/primary/sparql --no-stats
    """
    try:
        click.echo(f"Extracting VoID metadata from: {endpoint_url}")

        extractor = VoIDExtractor(endpoint_url)

        # Configure what to extract (if the extractor has these attributes)
        if hasattr(extractor, 'include_statistics'):
            extractor.include_statistics = include_stats
        if hasattr(extractor, 'include_class_partitions'):
            extractor.include_class_partitions = include_classes
        if hasattr(extractor, 'include_property_partitions'):
            extractor.include_property_partitions = include_properties

        # Extract VoID data
        void_datasets = extractor.extract()

        # Format output
        if format == 'turtle':
            output_content = extractor.export_to_rdf(void_datasets, format='turtle')
        elif format == 'json':
            import json
            datasets_dict = [dataset.to_dict() for dataset in void_datasets]
            output_content = json.dumps(datasets_dict, indent=2, default=str)
        elif format == 'yaml':
            import yaml
            datasets_dict = [dataset.to_dict() for dataset in void_datasets]
            output_content = yaml.dump(datasets_dict, default_flow_style=False)

        # Write to file or stdout
        if output:
            with open(output, 'w') as f:
                f.write(output_content)
            click.echo(f"VoID metadata saved to: {output}")
        else:
            click.echo(output_content)

    except Exception as e:
        ctx.fail(f"VoID extraction failed: {str(e)}")


# ============================================================================
# ShEx Commands
# ============================================================================

@cli.command()
@click.argument('schema_file')
@click.option(
    '--data', '-d',
    help='RDF data file to validate against the schema'
)
@click.option(
    '--shape', '-s',
    help='Specific shape to validate (default: validate all)'
)
@click.option(
    '--format', '-f',
    type=click.Choice(['turtle', 'json', 'summary']),
    default='summary',
    help='Output format'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Verbose validation output'
)
@click.pass_context
def shex(ctx, schema_file: str, data: Optional[str], shape: Optional[str], format: str, verbose: bool):
    """Parse and validate ShEx (Shape Expressions) schemas.

    ShEx schemas define constraints on RDF data structures. This command can parse
    ShEx files, validate RDF data against shapes, and provide detailed reports.

    Examples:
        # Parse a ShEx schema file
        uv run sparql-agent shex schema.shex

        # Validate RDF data against a schema
        uv run sparql-agent shex schema.shex --data data.ttl

        # Validate specific shape with verbose output
        uv run sparql-agent shex protein.shex -d proteins.ttl -s ProteinShape -v

        # Output as JSON
        uv run sparql-agent shex schema.shex -f json
    """
    try:
        parser = ShExParser()

        # Parse the schema
        click.echo(f"Parsing ShEx schema: {schema_file}")
        with open(schema_file, 'r') as f:
            schema_content = f.read()

        schema = parser.parse(schema_content)

        if not data:
            # Just show schema information
            if format == 'json':
                click.echo(json.dumps(schema.to_dict(), indent=2))
            elif format == 'turtle':
                click.echo(schema.to_shex())
            else:
                click.echo(f"ShEx Schema: {schema_file}")
                click.echo(f"Shapes: {len(schema.shapes)}")
                for shape_name, shape in schema.shapes.items():
                    click.echo(f"  - {shape_name}: {len(shape.triple_constraints)} constraints")
                    if verbose:
                        for tc in shape.triple_constraints:
                            click.echo(f"    • {tc.predicate} {tc.value_expr} {tc.cardinality.value}")
        else:
            # Validate data against schema
            click.echo(f"Validating RDF data: {data}")

            # Load RDF data
            from rdflib import Graph
            g = Graph()
            g.parse(data)

            # Perform validation
            results = parser.validate_graph(g, schema, target_shape=shape)

            if format == 'json':
                click.echo(json.dumps([r.to_dict() for r in results], indent=2))
            else:
                click.echo(f"Validation Results:")
                for result in results:
                    status = "✓ PASS" if result.conforms else "✗ FAIL"
                    click.echo(f"  {status} {result.focus_node} : {result.shape}")
                    if verbose and result.reasons:
                        for reason in result.reasons:
                            click.echo(f"    Reason: {reason}")

    except FileNotFoundError:
        ctx.fail(f"File not found: {schema_file}")
    except Exception as e:
        ctx.fail(f"ShEx processing failed: {str(e)}")


# ============================================================================
# Version Command
# ============================================================================

@cli.command()
@click.option(
    '--verbose',
    '-v',
    is_flag=True,
    help='Show detailed version information'
)
def version(verbose: bool):
    """Show SPARQL Agent version information."""
    try:
        from .. import __version__, __author__, __license__
        version_str = __version__
    except:
        version_str = "unknown"
        __author__ = "Unknown"
        __license__ = "Unknown"

    click.echo(f"SPARQL Agent version {version_str}")

    if verbose:
        click.echo(f"Author: {__author__}")
        click.echo(f"License: {__license__}")
        click.echo(f"Python: {sys.version.split()[0]}")

        # Show key dependencies
        try:
            import rdflib
            import anthropic
            import click as click_lib
            click.echo(f"\nKey Dependencies:")
            click.echo(f"  - rdflib: {rdflib.__version__}")
            click.echo(f"  - anthropic: {anthropic.__version__}")
            click.echo(f"  - click: {click_lib.__version__}")
        except:
            pass

    click.echo("\nhttps://github.com/david4096/sparql-agent")
    click.echo("Report issues: https://github.com/david4096/sparql-agent/issues")


# ============================================================================
# Batch Processing Commands
# ============================================================================

# Import and register batch commands
try:
    from .batch import batch_cli
    cli.add_command(batch_cli, name='batch')
except ImportError as e:
    logger.warning(f"Batch processing commands not available: {e}")


# ============================================================================
# Entry Point
# ============================================================================

def main():
    """Main entry point for the CLI."""
    try:
        cli(obj={})
    except KeyboardInterrupt:
        click.echo("\nInterrupted by user", err=True)
        sys.exit(130)
    except Exception as e:
        click.echo(f"Fatal error: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
