# SPARQL Agent Documentation

Comprehensive documentation for SPARQL Agent - an intelligent SPARQL query agent with OWL ontology support and LLM integration.

## Documentation Structure

### Getting Started

- **[Index](index.md)** - Project overview and introduction
- **[Installation](installation.md)** - Installation instructions for all platforms
- **[Quick Start](quickstart.md)** - Get started in 5 minutes
- **[Configuration](configuration.md)** - Configuration options and setup

### User Guides

- **[CLI Reference](cli.md)** - Complete command-line interface documentation
- **[Python API](api.md)** - Programmatic usage guide
- **[Web API](web-api.md)** - REST API reference with OpenAPI
- **[MCP Integration](mcp.md)** - Model Context Protocol for AI agents
- **[Batch Processing](batch-processing.md)** - Processing multiple queries

### Tutorials

Step-by-step guides for common workflows:

- **[Basic SPARQL Queries](tutorials/tutorial-basic.md)** - Learn fundamental querying
- **[Working with Ontologies](tutorials/tutorial-ontology.md)** - OWL and OLS4 integration
- **[Federation & Cross-Dataset Queries](tutorials/tutorial-federation.md)** - Query multiple endpoints
- **[Natural Language to SPARQL](tutorials/tutorial-llm.md)** - LLM-powered query generation

### Examples

- **[Jupyter Notebooks](examples/notebooks.md)** - Interactive notebooks
  - [Basic Usage](../examples/notebooks/basic_usage.ipynb)
  - Biomedical Queries
  - Advanced Federation
- **[Code Samples](examples/code-samples.md)** - Copy-paste examples
- **[Integration Examples](examples/integrations.md)** - Real-world integrations

### Developer Guide

- **[Architecture](architecture.md)** - System design and architecture
- **[Contributing](contributing.md)** - Contribution guidelines
- **[Testing](testing.md)** - Testing guide and best practices
- **[Deployment](deployment.md)** - Production deployment guide
- **[Troubleshooting](troubleshooting.md)** - Common issues and solutions

### API Reference

Detailed API documentation for each module:

- **[Core](api/core.md)** - Core abstractions and base classes
- **[Discovery](api/discovery.md)** - Schema discovery and analysis
- **[Schema](api/schema.md)** - Schema management (VoID, ShEx)
- **[Ontology](api/ontology.md)** - OWL parsing and OLS4 client
- **[LLM](api/llm.md)** - LLM provider integrations
- **[Query](api/query.md)** - Query generation and validation
- **[Execution](api/execution.md)** - Query execution engine
- **[Formatting](api/formatting.md)** - Result formatting
- **[MCP](api/mcp.md)** - MCP server implementation
- **[CLI](api/cli.md)** - CLI internals
- **[Web](api/web.md)** - Web API internals

### Best Practices

- **[Performance Optimization](best-practices/performance.md)** - Performance tuning
- **[Security](best-practices/security.md)** - Security guidelines
- **[Monitoring](best-practices/monitoring.md)** - Monitoring and observability
- **[Production Deployment](best-practices/production.md)** - Production best practices

### Additional Resources

- **[Release Notes](release-notes.md)** - Version history and changes
- **[License](license.md)** - MIT License
- **[Citation](citation.md)** - How to cite SPARQL Agent

## Building Documentation

### Local Development

```bash
# Install dependencies
uv sync
uv pip install --system mkdocs-material mkdocstrings

# Serve documentation locally
mkdocs serve

# Open browser to http://localhost:8000
```

### Build Static Site

```bash
# Build documentation
mkdocs build

# Output in site/ directory
```

### Generate API Documentation

```bash
# Using Sphinx
cd docs
sphinx-build -b html . _build/html

# Using pdoc
pdoc --html --output-dir api-docs src/sparql_agent
```

## Documentation Standards

### Markdown Files

- Use clear, descriptive headings
- Include code examples for all features
- Add links to related documentation
- Keep line length reasonable (100-120 chars)
- Use admonitions for notes, warnings, tips

### Code Examples

````markdown
```python
from sparql_agent import SPARQLAgent

agent = SPARQLAgent(endpoint="https://sparql.uniprot.org/sparql")
results = agent.query("Find proteins")
```
````

### Admonitions

```markdown
!!! note
    This is a note

!!! warning
    This is a warning

!!! tip
    This is a tip
```

## Contributing to Documentation

1. **Fork the repository**
2. **Create a branch**: `git checkout -b docs/my-improvement`
3. **Make changes** to documentation files
4. **Test locally**: `mkdocs serve`
5. **Submit PR** with clear description

### Documentation Checklist

- [ ] Clear, concise writing
- [ ] Code examples tested
- [ ] Links verified
- [ ] Screenshots/diagrams included where helpful
- [ ] Spelling and grammar checked
- [ ] Cross-references added
- [ ] Updated table of contents

## Documentation Features

### Search

Full-text search across all documentation using the search box.

### Dark Mode

Toggle between light and dark themes using the theme switcher.

### Code Copy

Copy code examples with one click using the copy button.

### Navigation

- Table of contents for each page
- Breadcrumb navigation
- Previous/next page links
- Site-wide navigation menu

### Versioning

Documentation is versioned alongside code releases:

- `latest` - Latest stable release
- `develop` - Development version
- `v0.1.0` - Specific version

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/david4096/sparql-agent/issues)
- **Discussions**: [GitHub Discussions](https://github.com/david4096/sparql-agent/discussions)
- **Email**: support@example.com
- **Discord**: [Join our community](#)

## Documentation Roadmap

### Planned Additions

- [ ] Video tutorials
- [ ] Interactive playground
- [ ] More real-world examples
- [ ] Performance benchmarks
- [ ] API migration guides
- [ ] Advanced architecture guides
- [ ] Case studies
- [ ] FAQ section

## License

Documentation is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

Code examples in documentation are licensed under MIT, same as the project.

## Acknowledgments

- MkDocs and Material theme
- Sphinx documentation generator
- Contributors to documentation
