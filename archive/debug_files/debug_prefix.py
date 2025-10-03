#!/usr/bin/env python3
"""Debug prefix parsing."""

import sys
import importlib.util

# Load the module directly
spec = importlib.util.spec_from_file_location(
    "shex_parser",
    "/Users/david/git/sparql-agent/src/sparql_agent/schema/shex_parser.py"
)
shex_parser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shex_parser)

ShExParser = shex_parser.ShExParser

shex_text = """
PREFIX up: <http://purl.uniprot.org/core/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

<ProteinShape> {
  up:name xsd:string+,
  up:organism IRI,
  up:sequence xsd:string?
}
"""

parser = ShExParser()

# Before parsing
print("Text to parse:")
print(repr(shex_text))

# Parse
schema = parser.parse(shex_text)

print("\nParsed prefixes:")
for prefix, iri in schema.prefixes.items():
    print(f"  {prefix}: <{iri}>")

print(f"\nHas 'xsd' prefix: {'xsd' in schema.prefixes}")

# Check what's in the cleaned text
print("\nCleaned text:")
print(repr(parser.text[:200]))
