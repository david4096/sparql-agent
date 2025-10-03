#!/usr/bin/env python3
"""Debug ShEx parsing."""

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
schema = parser.parse(shex_text)

print("Parsed shapes:")
for shape_id, shape in schema.shapes.items():
    print(f"  Shape ID: '{shape_id}'")
    print(f"    ID length: {len(shape_id)}")
    print(f"    ID bytes: {shape_id.encode('utf-8')}")
    print(f"    Constraints: {len(shape.expression)}")

print("\nLooking for: '<ProteinShape>'")
print(f"Found: {'<ProteinShape>' in schema.shapes}")

# Check prefixes too
print("\nPrefixes:")
for prefix, iri in schema.prefixes.items():
    print(f"  {prefix}: <{iri}>")
