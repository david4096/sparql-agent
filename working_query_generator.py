#!/usr/bin/env python3
"""
Working SPARQL Query Generator with Endpoint-Specific Context

This module provides a practical, working implementation of natural language
to SPARQL conversion that actually produces useful queries for real endpoints.
"""

import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sparql_agent.llm import create_anthropic_provider
from sparql_agent.llm.client import LLMRequest


class WorkingSPARQLGenerator:
    """A practical SPARQL generator that produces working queries."""

    def __init__(self, api_key: str):
        self.llm_client = create_anthropic_provider(api_key=api_key)

        # Endpoint-specific templates and vocabularies
        self.endpoint_contexts = {
            "wikidata": {
                "base_url": "https://query.wikidata.org/sparql",
                "prefixes": {
                    "wd": "http://www.wikidata.org/entity/",
                    "wdt": "http://www.wikidata.org/prop/direct/",
                    "wikibase": "http://wikiba.se/ontology#",
                    "bd": "http://www.bigdata.com/rdf#"
                },
                "common_patterns": {
                    "human": "?person wdt:P31 wd:Q5",
                    "birthplace": "?person wdt:P19 ?place",
                    "occupation": "?person wdt:P106 ?occupation",
                    "birth_date": "?person wdt:P569 ?birthDate",
                    "death_date": "?person wdt:P570 ?deathDate",
                    "label_service": "SERVICE wikibase:label { bd:serviceParam wikibase:language \"en\". }"
                },
                "example_entities": {
                    "Paris": "wd:Q90",
                    "France": "wd:Q142",
                    "Nobel Prize": "wd:Q7191",
                    "physicist": "wd:Q169470",
                    "scientist": "wd:Q901"
                }
            },
            "uniprot": {
                "base_url": "https://sparql.uniprot.org/sparql",
                "prefixes": {
                    "up": "http://purl.uniprot.org/core/",
                    "uniprotkb": "http://purl.uniprot.org/uniprot/",
                    "taxon": "http://purl.uniprot.org/taxonomy/",
                    "rdfs": "http://www.w3.org/2000/01/rdf-schema#"
                },
                "common_patterns": {
                    "human_protein": "?protein a up:Protein ; up:organism taxon:9606 ; up:reviewed true",
                    "protein_name": "?protein up:recommendedName/up:fullName ?name",
                    "simple_query": "?protein a up:Protein ; up:organism taxon:9606",
                    "enzyme": "?protein up:enzyme ?ec",
                    "annotation": "?protein up:annotation/up:comment ?comment"
                },
                "example_queries": {
                    "human_proteins": "SELECT ?protein ?name WHERE { ?protein a up:Protein ; up:organism taxon:9606 ; up:recommendedName/up:fullName ?name } LIMIT 5"
                }
            },
            "rdfportal": {
                "base_url": "https://rdfportal.org/primary/sparql",
                "prefixes": {
                    "faldo": "http://biohackathon.org/resource/faldo#",
                    "obo": "http://purl.obolibrary.org/obo/",
                    "sio": "http://semanticscience.org/resource/",
                    "opentggates": "http://purl.jp/bio/101/opentggates/ontology/",
                    "rdfs": "http://www.w3.org/2000/01/rdf-schema#"
                },
                "common_patterns": {
                    "gene_expression": "?measurement a opentggates:NormalizedSignalIntensity",
                    "p_value": "?pval a opentggates:PValue",
                    "log_ratio": "?ratio a opentggates:Log2Ratio",
                    "genomic_position": "?pos a faldo:ExactPosition",
                    "pa_call": "?call a opentggates:CustomizedPACall"
                },
                "description": "OpenTGGATEs toxicogenomics database with gene expression, genomic positions, and statistical data"
            }
        }

    def detect_endpoint(self, endpoint_url: str) -> str:
        """Detect endpoint type from URL."""
        url_lower = endpoint_url.lower()
        if "wikidata" in url_lower:
            return "wikidata"
        elif "uniprot" in url_lower:
            return "uniprot"
        elif "rdfportal" in url_lower:
            return "rdfportal"
        else:
            return "generic"

    def generate_context_aware_query(self, natural_language: str, endpoint_url: str) -> str:
        """Generate SPARQL query with endpoint-specific context."""

        endpoint_type = self.detect_endpoint(endpoint_url)
        context = self.endpoint_contexts.get(endpoint_type, {})

        # Build endpoint-specific prompt
        prompt = f"""Generate a SPARQL query for this natural language request: "{natural_language}"

Target endpoint: {endpoint_url} ({endpoint_type})
"""

        if context:
            prompt += f"\nUse these prefixes:\n"
            for prefix, uri in context.get("prefixes", {}).items():
                prompt += f"PREFIX {prefix}: <{uri}>\n"

            prompt += f"\nCommon patterns for {endpoint_type}:\n"
            for pattern_name, pattern in context.get("common_patterns", {}).items():
                prompt += f"- {pattern_name}: {pattern}\n"

            if endpoint_type == "wikidata":
                prompt += f"\nKnown entity IDs:\n"
                for entity, qid in context.get("example_entities", {}).items():
                    prompt += f"- {entity}: {qid}\n"

        prompt += """
Requirements:
1. Return only the SPARQL query, no explanations
2. Include appropriate LIMIT clause (3-10 results for testing)
3. Use endpoint-specific vocabulary and patterns
4. Include helpful comments in the query
5. Make sure the query will return actual results

SPARQL Query:"""

        request = LLMRequest(prompt=prompt, max_tokens=1000)
        response = self.llm_client.generate(request)
        if hasattr(response, 'content'):
            query = response.content.strip()
            # Clean up the query
            if query.startswith('```sparql'):
                query = query[9:]
            if query.startswith('```'):
                query = query[3:]
            if query.endswith('```'):
                query = query[:-3]
            return query.strip()
        return ""


def test_working_generator():
    """Test the working generator with real endpoints."""
    import os

    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("Please set ANTHROPIC_API_KEY environment variable")
        return

    generator = WorkingSPARQLGenerator(api_key)

    # Test queries for different endpoints
    test_cases = [
        ("Find 3 people born in Paris", "https://query.wikidata.org/sparql"),
        ("Find 5 human proteins involved in DNA repair", "https://sparql.uniprot.org/sparql"),
        ("Show me genomic regions from chromosome 1", "https://rdfportal.org/primary/sparql")
    ]

    for query, endpoint in test_cases:
        print(f"\nTesting: {query}")
        print(f"Endpoint: {endpoint}")
        print("-" * 80)

        sparql = generator.generate_context_aware_query(query, endpoint)
        print(sparql)
        print("=" * 80)


if __name__ == "__main__":
    test_working_generator()