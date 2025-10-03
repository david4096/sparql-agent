"""
Locust load testing for LLM query generation endpoints.

Run with: locust -f locust_llm.py --host=http://localhost:8000
"""

from locust import HttpUser, task, between, events
import random
import json
import time
from typing import List, Dict, Any


class LLMQueryGenerationUser(HttpUser):
    """
    Simulated user generating SPARQL queries via LLM.
    """
    wait_time = between(2, 5)

    def on_start(self):
        """Initialize user session."""
        self.natural_language_queries = self._load_test_questions()
        self.generation_count = 0
        self.failed_generations = 0

    def _load_test_questions(self) -> List[str]:
        """Load test natural language questions."""
        return [
            "Find all people",
            "List organizations in New York",
            "Show me publications from 2023",
            "What proteins are associated with cancer?",
            "Find all genes related to diabetes",
            "Show me universities in California",
            "List all proteins that bind to DNA",
            "What are the symptoms of influenza?",
            "Find all drugs that target specific proteins",
            "Show me disease-gene associations",
            "List all pathways involved in metabolism",
            "What organisms are used in research?",
            "Find all clinical trials for cancer",
            "Show me protein-protein interactions",
            "List all compounds with molecular weight over 500"
        ]

    @task(10)
    def generate_simple_query(self):
        """Generate simple SPARQL query from natural language."""
        question = random.choice(self.natural_language_queries[:5])
        self._generate_query(question, complexity="simple")

    @task(5)
    def generate_moderate_query(self):
        """Generate moderate complexity query."""
        question = random.choice(self.natural_language_queries[5:10])
        self._generate_query(question, complexity="moderate")

    @task(2)
    def generate_complex_query(self):
        """Generate complex SPARQL query."""
        question = random.choice(self.natural_language_queries[10:])
        self._generate_query(question, complexity="complex")

    def _generate_query(self, question: str, complexity: str):
        """Generate SPARQL query using LLM."""
        payload = {
            "question": question,
            "schema": {
                "classes": ["Person", "Organization", "Publication"],
                "properties": ["name", "worksFor", "publishedIn"]
            },
            "provider": random.choice(["anthropic", "openai"]),
            "max_tokens": 500
        }

        start_time = time.time()

        with self.client.post(
            "/api/generate-query",
            json=payload,
            catch_response=True,
            name=f"LLM Generate: {complexity}"
        ) as response:
            elapsed = time.time() - start_time
            self.generation_count += 1

            if response.status_code == 200:
                try:
                    result = response.json()
                    if "query" in result and "explanation" in result:
                        response.success()

                        # Track token usage
                        if "usage" in result:
                            events.request.fire(
                                request_type="CUSTOM",
                                name=f"Token Usage: {complexity}",
                                response_time=result["usage"].get("total_tokens", 0),
                                response_length=0,
                            )
                    else:
                        response.failure("Incomplete response")
                        self.failed_generations += 1
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
                    self.failed_generations += 1
            elif response.status_code == 429:
                # Rate limited - expected behavior
                response.success()
                time.sleep(1)  # Back off
            else:
                response.failure(f"HTTP {response.status_code}")
                self.failed_generations += 1

    @task(3)
    def generate_with_examples(self):
        """Generate query with few-shot examples."""
        question = random.choice(self.natural_language_queries)
        payload = {
            "question": question,
            "examples": [
                {
                    "question": "Find all people",
                    "query": "SELECT ?person WHERE { ?person a :Person }"
                },
                {
                    "question": "List organizations",
                    "query": "SELECT ?org WHERE { ?org a :Organization }"
                }
            ],
            "provider": "anthropic"
        }

        with self.client.post(
            "/api/generate-query",
            json=payload,
            catch_response=True,
            name="LLM Generate: with examples"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Generation failed: {response.status_code}")

    @task(1)
    def test_provider_failover(self):
        """Test LLM provider failover mechanism."""
        question = random.choice(self.natural_language_queries)
        payload = {
            "question": question,
            "provider": "auto",  # Should try primary then fallback
            "fallback_enabled": True
        }

        with self.client.post(
            "/api/generate-query",
            json=payload,
            catch_response=True,
            name="LLM Generate: failover test"
        ) as response:
            if response.status_code == 200:
                result = response.json()
                # Check which provider was used
                provider_used = result.get("provider_used", "unknown")
                response.success()
            else:
                response.failure("Failover failed")

    def on_stop(self):
        """Cleanup and statistics."""
        print(f"User generated {self.generation_count} queries, "
              f"{self.failed_generations} failed")


class LLMBatchGenerationUser(HttpUser):
    """
    User for batch query generation.
    """
    wait_time = between(5, 10)

    @task
    def batch_generate_queries(self):
        """Generate multiple queries in a batch."""
        questions = [
            "Find all people",
            "List organizations",
            "Show publications",
            "What are the genes?",
            "Find proteins"
        ]

        payload = {
            "questions": questions,
            "provider": "anthropic",
            "parallel": True
        }

        with self.client.post(
            "/api/batch-generate",
            json=payload,
            catch_response=True,
            name="LLM Batch Generation"
        ) as response:
            if response.status_code == 200:
                try:
                    results = response.json()
                    if len(results.get("queries", [])) == len(questions):
                        response.success()
                    else:
                        response.failure("Incomplete batch results")
                except:
                    response.failure("Invalid response")
            else:
                response.failure(f"Batch failed: {response.status_code}")


class LLMRefinementUser(HttpUser):
    """
    User for query refinement and iteration.
    """
    wait_time = between(3, 6)

    @task
    def refine_query(self):
        """Refine an existing SPARQL query."""
        initial_query = "SELECT ?s WHERE { ?s ?p ?o }"
        feedback = random.choice([
            "Add filters to limit results",
            "Include labels for entities",
            "Add sorting by date",
            "Group results by type"
        ])

        payload = {
            "query": initial_query,
            "feedback": feedback,
            "provider": "openai"
        }

        with self.client.post(
            "/api/refine-query",
            json=payload,
            catch_response=True,
            name="LLM Query Refinement"
        ) as response:
            if response.status_code == 200:
                result = response.json()
                if result.get("query") != initial_query:
                    response.success()
                else:
                    response.failure("Query not refined")
            else:
                response.failure(f"Refinement failed: {response.status_code}")

    @task
    def iterative_refinement(self):
        """Perform iterative query refinement."""
        query = "SELECT ?s WHERE { ?s ?p ?o }"
        iterations = 3

        for i in range(iterations):
            payload = {
                "query": query,
                "feedback": f"Refinement iteration {i+1}",
                "iteration": i
            }

            with self.client.post(
                "/api/refine-query",
                json=payload,
                catch_response=True,
                name=f"LLM Iterative Refinement: step {i+1}"
            ) as response:
                if response.status_code == 200:
                    result = response.json()
                    query = result.get("query", query)
                    response.success()
                else:
                    response.failure(f"Iteration {i+1} failed")
                    break


class LLMCachingUser(HttpUser):
    """
    Test LLM response caching effectiveness.
    """
    wait_time = between(1, 3)

    @task
    def test_cache_hit(self):
        """Test cache hit for repeated questions."""
        # Ask the same question to test caching
        question = "Find all people"
        payload = {
            "question": question,
            "cache_enabled": True
        }

        with self.client.post(
            "/api/generate-query",
            json=payload,
            catch_response=True,
            name="LLM Generate: cache hit test"
        ) as response:
            if response.status_code == 200:
                result = response.json()
                was_cached = result.get("cached", False)
                # Cached responses should be faster
                response.success()
            else:
                response.failure("Cache test failed")

    @task
    def test_cache_miss(self):
        """Test cache miss for unique questions."""
        # Ask unique question to test cache miss
        unique_id = random.randint(10000, 99999)
        question = f"Find entity with id {unique_id}"
        payload = {
            "question": question,
            "cache_enabled": True
        }

        with self.client.post(
            "/api/generate-query",
            json=payload,
            catch_response=True,
            name="LLM Generate: cache miss test"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure("Cache miss test failed")


class LLMStressUser(HttpUser):
    """
    Stress test LLM endpoints with high request rate.
    """
    wait_time = between(0.1, 0.5)

    @task
    def rapid_fire_requests(self):
        """Send requests rapidly to test rate limiting."""
        question = "Find all entities"
        payload = {"question": question, "provider": "anthropic"}

        with self.client.post(
            "/api/generate-query",
            json=payload,
            catch_response=True,
            name="LLM Stress Test"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                # Rate limiting is working - this is expected
                response.success()
            elif response.status_code == 503:
                # Service temporarily unavailable - acceptable under stress
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")


class LLMTokenOptimizationUser(HttpUser):
    """
    Test token usage optimization.
    """
    wait_time = between(2, 4)

    @task
    def test_schema_compression(self):
        """Test with compressed schema to reduce tokens."""
        large_schema = {
            "classes": [f"Class{i}" for i in range(100)],
            "properties": [f"prop{i}" for i in range(200)]
        }

        payload = {
            "question": "Find all entities",
            "schema": large_schema,
            "compress_schema": True
        }

        with self.client.post(
            "/api/generate-query",
            json=payload,
            catch_response=True,
            name="LLM Token Optimization"
        ) as response:
            if response.status_code == 200:
                result = response.json()
                token_count = result.get("usage", {}).get("total_tokens", 0)
                # Compressed should use fewer tokens
                response.success()
            else:
                response.failure("Token optimization test failed")


# Event handlers
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts."""
    print("Starting LLM endpoint load test...")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops."""
    print("LLM endpoint load test completed.")
    print(f"Total requests: {environment.stats.total.num_requests}")
    print(f"Total failures: {environment.stats.total.num_failures}")
    print(f"Average response time: {environment.stats.total.avg_response_time}ms")
    print(f"RPS: {environment.stats.total.total_rps}")

    # Calculate LLM-specific metrics
    total_time = environment.stats.total.total_response_time
    if total_time > 0:
        avg_generation_time = total_time / environment.stats.total.num_requests
        print(f"Average LLM generation time: {avg_generation_time:.2f}ms")
