#!/usr/bin/env python3
"""
Example usage of the SPARQL Agent configuration system.

This script demonstrates how to use the configuration management system
including loading settings, accessing configurations, and runtime updates.
"""

from pathlib import Path
from sparql_agent.config import (
    get_settings,
    print_configuration,
    validate_configuration,
    export_configuration,
)


def basic_usage():
    """Demonstrate basic configuration usage."""
    print("=" * 80)
    print("BASIC USAGE")
    print("=" * 80)

    # Get global settings instance
    settings = get_settings()

    # Access general settings
    print(f"\nDebug mode: {settings.debug}")
    print(f"Config directory: {settings.config_dir}")

    # Access ontology settings
    print(f"\nOntology cache enabled: {settings.ontology.cache_enabled}")
    print(f"Ontology cache directory: {settings.ontology.cache_dir}")
    print(f"OLS API URL: {settings.ontology.ols_api_base_url}")

    # Access endpoint settings
    print(f"\nEndpoint timeout: {settings.endpoint.default_timeout}s")
    print(f"Max retries: {settings.endpoint.max_retries}")
    print(f"Rate limiting: {settings.endpoint.rate_limit_enabled}")

    # Access LLM settings
    print(f"\nLLM model: {settings.llm.model_name}")
    print(f"Temperature: {settings.llm.temperature}")
    print(f"Max tokens: {settings.llm.max_tokens}")

    # Access logging settings
    print(f"\nLog level: {settings.logging.level}")
    print(f"File logging: {settings.logging.file_enabled}")


def endpoint_configurations():
    """Demonstrate endpoint configuration access."""
    print("\n" + "=" * 80)
    print("ENDPOINT CONFIGURATIONS")
    print("=" * 80)

    settings = get_settings()

    # List all available endpoints
    endpoints = settings.list_endpoints()
    print(f"\nAvailable endpoints: {', '.join(endpoints)}")

    # Get specific endpoint configuration
    uniprot = settings.get_endpoint_config('uniprot')
    if uniprot:
        print(f"\nUniProt Configuration:")
        print(f"  Name: {uniprot.get('name')}")
        print(f"  URL: {uniprot.get('url')}")
        print(f"  Description: {uniprot.get('description')}")
        print(f"  Timeout: {uniprot.get('timeout')}s")

        # Access prefixes
        prefixes = uniprot.get('prefixes', {})
        print(f"  Prefixes: {len(prefixes)} defined")
        for prefix, uri in list(prefixes.items())[:3]:
            print(f"    {prefix}: {uri}")

        # Access features
        features = uniprot.get('features', [])
        print(f"  Features: {', '.join(features)}")

    # Get ClinVar configuration
    clinvar = settings.get_endpoint_config('clinvar')
    if clinvar:
        print(f"\nClinVar Configuration:")
        print(f"  Name: {clinvar.get('name')}")
        print(f"  URL: {clinvar.get('url')}")


def ontology_configurations():
    """Demonstrate ontology configuration access."""
    print("\n" + "=" * 80)
    print("ONTOLOGY CONFIGURATIONS")
    print("=" * 80)

    settings = get_settings()

    # List all available ontologies
    ontologies = settings.list_ontologies()
    print(f"\nAvailable ontologies: {', '.join(ontologies)}")

    # Get specific ontology configuration
    efo = settings.get_ontology_config('efo')
    if efo:
        print(f"\nEFO (Experimental Factor Ontology):")
        print(f"  Name: {efo.get('name')}")
        print(f"  Namespace: {efo.get('namespace')}")
        print(f"  Prefix: {efo.get('prefix')}")
        print(f"  Description: {efo.get('description')}")
        print(f"  Homepage: {efo.get('homepage')}")
        print(f"  Cache enabled: {efo.get('cache_enabled')}")
        print(f"  Preload: {efo.get('preload')}")

        # Access categories
        categories = efo.get('categories', [])
        print(f"  Categories: {', '.join(categories)}")

        # Access use cases
        use_cases = efo.get('use_cases', [])
        print(f"  Use cases:")
        for use_case in use_cases:
            print(f"    - {use_case}")

    # Get MONDO configuration
    mondo = settings.get_ontology_config('mondo')
    if mondo:
        print(f"\nMONDO (Mondo Disease Ontology):")
        print(f"  Name: {mondo.get('name')}")
        print(f"  Prefix: {mondo.get('prefix')}")
        print(f"  Categories: {', '.join(mondo.get('categories', []))}")


def prompt_templates():
    """Demonstrate prompt template access."""
    print("\n" + "=" * 80)
    print("PROMPT TEMPLATES")
    print("=" * 80)

    settings = get_settings()

    # List all available prompts
    prompts = settings.list_prompts()
    print(f"\nAvailable prompts: {', '.join(prompts)}")

    # Get specific prompt template
    nl_to_sparql = settings.get_prompt_template('nl_to_sparql')
    if nl_to_sparql:
        print(f"\nNatural Language to SPARQL Prompt:")
        print(f"  Length: {len(nl_to_sparql)} characters")
        print(f"  Preview: {nl_to_sparql[:200]}...")

    # Get query refinement prompt
    refinement = settings.get_prompt_template('query_refinement')
    if refinement:
        print(f"\nQuery Refinement Prompt:")
        print(f"  Length: {len(refinement)} characters")


def runtime_updates():
    """Demonstrate runtime configuration updates."""
    print("\n" + "=" * 80)
    print("RUNTIME CONFIGURATION UPDATES")
    print("=" * 80)

    settings = get_settings()

    # Show original values
    print(f"\nOriginal values:")
    print(f"  Debug: {settings.debug}")
    print(f"  LLM Temperature: {settings.llm.temperature}")
    print(f"  Cache enabled: {settings.ontology.cache_enabled}")

    # Update configuration
    print(f"\nUpdating configuration...")
    settings.update_config(debug=True)
    settings.llm.temperature = 0.5
    settings.ontology.cache_enabled = False

    # Show updated values
    print(f"\nUpdated values:")
    print(f"  Debug: {settings.debug}")
    print(f"  LLM Temperature: {settings.llm.temperature}")
    print(f"  Cache enabled: {settings.ontology.cache_enabled}")

    # Reset for other examples
    settings.update_config(debug=False)
    settings.llm.temperature = 0.1
    settings.ontology.cache_enabled = True


def configuration_validation():
    """Demonstrate configuration validation."""
    print("\n" + "=" * 80)
    print("CONFIGURATION VALIDATION")
    print("=" * 80)

    is_valid, errors = validate_configuration()

    print(f"\nConfiguration valid: {is_valid}")

    if not is_valid:
        print(f"\nErrors found:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("\nNo configuration errors detected.")


def configuration_export():
    """Demonstrate configuration export."""
    print("\n" + "=" * 80)
    print("CONFIGURATION EXPORT")
    print("=" * 80)

    # Export as JSON
    print("\nExporting configuration as JSON...")
    json_config = export_configuration(format="json")
    print(f"JSON export length: {len(json_config)} characters")
    print(f"JSON preview:\n{json_config[:300]}...\n")

    # Export as YAML
    print("\nExporting configuration as YAML...")
    yaml_config = export_configuration(format="yaml")
    print(f"YAML export length: {len(yaml_config)} characters")
    print(f"YAML preview:\n{yaml_config[:300]}...\n")


def full_configuration_display():
    """Display the full configuration."""
    print("\n" + "=" * 80)
    print("FULL CONFIGURATION DISPLAY")
    print("=" * 80)
    print()

    # Print basic configuration
    print_configuration(verbose=False)

    # Ask if user wants verbose output
    print("\nFor verbose output with all YAML configs, use:")
    print("  print_configuration(verbose=True)")


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("SPARQL AGENT CONFIGURATION SYSTEM - USAGE EXAMPLES")
    print("=" * 80)

    try:
        # Run all example functions
        basic_usage()
        endpoint_configurations()
        ontology_configurations()
        prompt_templates()
        runtime_updates()
        configuration_validation()
        configuration_export()
        full_configuration_display()

        print("\n" + "=" * 80)
        print("ALL EXAMPLES COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print()

    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
