"""
Comprehensive ontology search quality testing script.

Tests OLS4 integration with various biomedical terms, chemicals, processes,
anatomical terms, and evaluates search quality, response times, and error handling.
"""

import time
import json
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, asdict
from sparql_agent.ontology import OLSClient

@dataclass
class SearchResult:
    """Represents a search test result."""
    query: str
    ontology: str
    duration: float
    num_results: int
    top_result_label: str
    top_result_id: str
    relevance_score: float
    errors: List[str]

@dataclass
class TestSummary:
    """Overall test summary."""
    total_searches: int
    successful: int
    failed: int
    avg_response_time: float
    max_response_time: float
    min_response_time: float
    avg_results_per_query: float
    avg_relevance_score: float


class OntologySearchTester:
    """Comprehensive ontology search testing."""

    def __init__(self):
        self.client = OLSClient()
        self.results: List[SearchResult] = []

    def test_biomedical_terms(self) -> List[SearchResult]:
        """Test search with biomedical terms."""
        test_cases = [
            ("diabetes", "efo", 10),
            ("protein kinase", "go", 10),
            ("cancer", "mondo", 10),
            ("apoptosis", "go", 10),
            ("immunology", "efo", 10),
            ("cell differentiation", "go", 10),
            ("inflammation", "go", 10),
            ("metabolism", "go", 10),
        ]

        results = []
        print("\n" + "="*80)
        print("TESTING BIOMEDICAL TERMS")
        print("="*80)

        for query, ontology, limit in test_cases:
            result = self._test_search(query, ontology, limit)
            results.append(result)
            self._print_result(result)
            time.sleep(0.3)  # Rate limiting

        return results

    def test_chemical_terms(self) -> List[SearchResult]:
        """Test search with chemical terms."""
        test_cases = [
            ("glucose", "chebi", 10),
            ("ethanol", "chebi", 10),
            ("aspirin", "chebi", 10),
            ("caffeine", "chebi", 10),
            ("dopamine", "chebi", 10),
            ("penicillin", "chebi", 10),
        ]

        results = []
        print("\n" + "="*80)
        print("TESTING CHEMICAL TERMS")
        print("="*80)

        for query, ontology, limit in test_cases:
            result = self._test_search(query, ontology, limit)
            results.append(result)
            self._print_result(result)
            time.sleep(0.3)

        return results

    def test_biological_process_terms(self) -> List[SearchResult]:
        """Test search with biological process terms."""
        test_cases = [
            ("transcription", "go", 10),
            ("translation", "go", 10),
            ("signal transduction", "go", 10),
            ("DNA replication", "go", 10),
            ("cell cycle", "go", 10),
            ("mitosis", "go", 10),
        ]

        results = []
        print("\n" + "="*80)
        print("TESTING BIOLOGICAL PROCESS TERMS")
        print("="*80)

        for query, ontology, limit in test_cases:
            result = self._test_search(query, ontology, limit)
            results.append(result)
            self._print_result(result)
            time.sleep(0.3)

        return results

    def test_anatomical_terms(self) -> List[SearchResult]:
        """Test search with anatomical terms."""
        test_cases = [
            ("brain", "uberon", 10),
            ("heart", "uberon", 10),
            ("liver", "uberon", 10),
            ("kidney", "uberon", 10),
            ("lung", "uberon", 10),
        ]

        results = []
        print("\n" + "="*80)
        print("TESTING ANATOMICAL TERMS")
        print("="*80)

        for query, ontology, limit in test_cases:
            result = self._test_search(query, ontology, limit)
            results.append(result)
            self._print_result(result)
            time.sleep(0.3)

        return results

    def test_phenotype_terms(self) -> List[SearchResult]:
        """Test search with phenotype terms."""
        test_cases = [
            ("seizure", "hp", 10),
            ("fever", "hp", 10),
            ("intellectual disability", "hp", 10),
            ("short stature", "hp", 10),
        ]

        results = []
        print("\n" + "="*80)
        print("TESTING PHENOTYPE TERMS")
        print("="*80)

        for query, ontology, limit in test_cases:
            result = self._test_search(query, ontology, limit)
            results.append(result)
            self._print_result(result)
            time.sleep(0.3)

        return results

    def test_misspellings(self) -> List[SearchResult]:
        """Test search with misspellings and partial matches."""
        test_cases = [
            ("protien", None, 10),  # misspelled protein
            ("diabet", None, 10),   # partial diabetes
            ("kinas", "go", 10),    # partial kinase
            ("neuro", None, 10),    # partial neurological
        ]

        results = []
        print("\n" + "="*80)
        print("TESTING MISSPELLINGS AND PARTIAL MATCHES")
        print("="*80)

        for query, ontology, limit in test_cases:
            result = self._test_search(query, ontology, limit)
            results.append(result)
            self._print_result(result)
            time.sleep(0.3)

        return results

    def test_pagination(self) -> List[SearchResult]:
        """Test pagination with different result limits."""
        query = "protein"

        results = []
        print("\n" + "="*80)
        print("TESTING PAGINATION")
        print("="*80)

        for limit in [5, 10, 20, 50]:
            result = self._test_search(query, None, limit)
            results.append(result)
            print(f"  Limit {limit}: Got {result.num_results} results in {result.duration:.3f}s")
            time.sleep(0.3)

        return results

    def _test_search(self, query: str, ontology: str, limit: int) -> SearchResult:
        """Execute a single search test."""
        errors = []
        duration = 0
        num_results = 0
        top_label = ""
        top_id = ""
        relevance = 0.0

        try:
            start = time.time()
            results = self.client.search(query, ontology=ontology, limit=limit)
            duration = time.time() - start

            num_results = len(results)

            if results:
                top_label = results[0].get("label", "")
                top_id = results[0].get("id", "")

                # Calculate relevance score (simple: check if query terms in result)
                query_lower = query.lower()
                label_lower = top_label.lower()

                if query_lower == label_lower:
                    relevance = 1.0
                elif query_lower in label_lower or label_lower in query_lower:
                    relevance = 0.8
                elif any(word in label_lower for word in query_lower.split()):
                    relevance = 0.6
                else:
                    relevance = 0.4

        except Exception as e:
            errors.append(str(e))
            relevance = 0.0

        return SearchResult(
            query=query,
            ontology=ontology or "all",
            duration=duration,
            num_results=num_results,
            top_result_label=top_label,
            top_result_id=top_id,
            relevance_score=relevance,
            errors=errors
        )

    def _print_result(self, result: SearchResult):
        """Print a search result."""
        status = "OK" if not result.errors else "FAILED"
        print(f"  [{status}] {result.query:30s} | {result.ontology:10s} | "
              f"{result.num_results:3d} results | {result.duration:.3f}s | "
              f"Rel: {result.relevance_score:.1f}")
        if result.num_results > 0:
            print(f"       Top: {result.top_result_label} ({result.top_result_id})")
        if result.errors:
            print(f"       Error: {result.errors[0]}")

    def generate_summary(self, all_results: List[SearchResult]) -> TestSummary:
        """Generate test summary statistics."""
        successful = [r for r in all_results if not r.errors]
        failed = [r for r in all_results if r.errors]

        if not successful:
            return TestSummary(
                total_searches=len(all_results),
                successful=0,
                failed=len(failed),
                avg_response_time=0.0,
                max_response_time=0.0,
                min_response_time=0.0,
                avg_results_per_query=0.0,
                avg_relevance_score=0.0
            )

        durations = [r.duration for r in successful]

        return TestSummary(
            total_searches=len(all_results),
            successful=len(successful),
            failed=len(failed),
            avg_response_time=sum(durations) / len(durations),
            max_response_time=max(durations),
            min_response_time=min(durations),
            avg_results_per_query=sum(r.num_results for r in successful) / len(successful),
            avg_relevance_score=sum(r.relevance_score for r in successful) / len(successful)
        )

    def run_all_tests(self) -> Tuple[List[SearchResult], TestSummary]:
        """Run all test categories."""
        print("\n" + "="*80)
        print("COMPREHENSIVE ONTOLOGY SEARCH QUALITY TESTING")
        print("="*80)

        all_results = []

        # Run all test categories
        all_results.extend(self.test_biomedical_terms())
        all_results.extend(self.test_chemical_terms())
        all_results.extend(self.test_biological_process_terms())
        all_results.extend(self.test_anatomical_terms())
        all_results.extend(self.test_phenotype_terms())
        all_results.extend(self.test_misspellings())
        all_results.extend(self.test_pagination())

        # Generate summary
        summary = self.generate_summary(all_results)

        # Print summary
        self._print_summary(summary)

        return all_results, summary

    def _print_summary(self, summary: TestSummary):
        """Print test summary."""
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"Total Searches:        {summary.total_searches}")
        print(f"Successful:            {summary.successful}")
        print(f"Failed:                {summary.failed}")
        print(f"Success Rate:          {(summary.successful/summary.total_searches*100):.1f}%")
        print()
        print(f"Avg Response Time:     {summary.avg_response_time:.3f}s")
        print(f"Max Response Time:     {summary.max_response_time:.3f}s")
        print(f"Min Response Time:     {summary.min_response_time:.3f}s")
        print()
        print(f"Avg Results/Query:     {summary.avg_results_per_query:.1f}")
        print(f"Avg Relevance Score:   {summary.avg_relevance_score:.2f}")
        print("="*80)

    def save_results(self, results: List[SearchResult], summary: TestSummary, filename: str):
        """Save results to JSON file."""
        output = {
            "summary": asdict(summary),
            "results": [asdict(r) for r in results]
        }

        with open(filename, 'w') as f:
            json.dump(output, f, indent=2)

        print(f"\nResults saved to {filename}")


def main():
    """Main test execution."""
    tester = OntologySearchTester()

    try:
        results, summary = tester.run_all_tests()

        # Save results
        tester.save_results(results, summary, "ontology_search_quality_results.json")

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
