# Test Data

This directory contains sample data files used in the sparql-agent test suite.

## Files

### sample_queries.sparql
Collection of SPARQL query patterns used for testing query parsing, validation, and execution.

Includes:
- Simple SELECT queries
- Queries with FILTER clauses
- ASK, CONSTRUCT, and DESCRIBE queries
- Aggregation queries
- Queries with OPTIONAL and UNION
- Complex queries with property paths

### sample_ontology.ttl
Comprehensive OWL ontology for testing ontology-guided query generation.

Contains:
- Class hierarchy (Agent, Person, Organization, etc.)
- Object properties (worksFor, collaboratesWith, etc.)
- Data properties (name, email, age, etc.)
- Sample instances for testing

## Usage in Tests

These files are automatically loaded by test fixtures defined in `conftest.py`:

- `sample_sparql_queries` fixture loads sample_queries.sparql
- `sample_owl_file` fixture loads sample_ontology.ttl

## Adding New Test Data

When adding new test data:

1. Place the file in this directory
2. Add a fixture in `conftest.py` to load it
3. Document the file purpose in this README
4. Use appropriate RDF/SPARQL syntax
5. Include comments explaining the test cases covered
