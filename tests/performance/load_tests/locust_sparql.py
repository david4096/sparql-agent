"""
Locust load testing for SPARQL endpoints.

Run with: locust -f locust_sparql.py --host=http://localhost:8000
"""

from locust import HttpUser, task, between, events
import random
import json
import time
from typing import Dict, Any


class SPARQLQueryUser(HttpUser):
    """
    Simulated user executing SPARQL queries against endpoints.
    """
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    def on_start(self):
        """Initialize user session."""
        self.queries = self._load_test_queries()
        self.query_count = 0
        self.failed_queries = 0

    def _load_test_queries(self) -> Dict[str, str]:
        """Load test SPARQL queries of various complexity."""
        return {
            "simple": """
                SELECT ?s ?p ?o
                WHERE {
                    ?s ?p ?o
                }
                LIMIT 10
            """,
            "filtered": """
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                SELECT ?entity ?label
                WHERE {
                    ?entity rdf:type ?type .
                    ?entity rdfs:label ?label .
                    FILTER (lang(?label) = "en")
                }
                LIMIT 50
            """,
            "join": """
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                SELECT ?person ?name ?org ?orgName
                WHERE {
                    ?person rdf:type :Person .
                    ?person :name ?name .
                    ?person :worksFor ?org .
                    ?org :name ?orgName .
                }
                LIMIT 100
            """,
            "aggregation": """
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                SELECT ?type (COUNT(?entity) as ?count)
                WHERE {
                    ?entity rdf:type ?type .
                }
                GROUP BY ?type
                ORDER BY DESC(?count)
                LIMIT 20
            """,
            "complex": """
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                SELECT DISTINCT ?entity ?label ?type ?relatedCount
                WHERE {
                    ?entity rdf:type ?type .
                    ?entity rdfs:label ?label .
                    {
                        SELECT ?entity (COUNT(?related) as ?relatedCount)
                        WHERE {
                            ?entity ?p ?related .
                        }
                        GROUP BY ?entity
                    }
                    FILTER (lang(?label) = "en")
                    FILTER (?relatedCount > 5)
                }
                ORDER BY DESC(?relatedCount)
                LIMIT 50
            """
        }

    @task(10)
    def execute_simple_query(self):
        """Execute simple SPARQL query (most common)."""
        self._execute_query("simple")

    @task(5)
    def execute_filtered_query(self):
        """Execute filtered SPARQL query."""
        self._execute_query("filtered")

    @task(3)
    def execute_join_query(self):
        """Execute query with joins."""
        self._execute_query("join")

    @task(2)
    def execute_aggregation_query(self):
        """Execute aggregation query."""
        self._execute_query("aggregation")

    @task(1)
    def execute_complex_query(self):
        """Execute complex query (least common, most expensive)."""
        self._execute_query("complex")

    def _execute_query(self, query_type: str):
        """Execute a SPARQL query and track metrics."""
        query = self.queries[query_type]

        headers = {
            "Content-Type": "application/sparql-query",
            "Accept": "application/sparql-results+json"
        }

        start_time = time.time()

        with self.client.post(
            "/sparql",
            data=query,
            headers=headers,
            catch_response=True,
            name=f"SPARQL Query: {query_type}"
        ) as response:
            elapsed = time.time() - start_time
            self.query_count += 1

            if response.status_code == 200:
                try:
                    results = response.json()
                    result_count = len(results.get("results", {}).get("bindings", []))
                    response.success()

                    # Track custom metrics
                    events.request.fire(
                        request_type="CUSTOM",
                        name=f"Result Count: {query_type}",
                        response_time=result_count,
                        response_length=0,
                    )
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
                    self.failed_queries += 1
            else:
                response.failure(f"HTTP {response.status_code}")
                self.failed_queries += 1

    @task(1)
    def test_query_timeout(self):
        """Test handling of slow/timeout queries."""
        slow_query = """
            SELECT ?s ?p ?o ?x ?y ?z
            WHERE {
                ?s ?p ?o .
                ?x ?y ?z .
                FILTER NOT EXISTS { ?s ?p ?x }
            }
            LIMIT 1000
        """

        with self.client.post(
            "/sparql",
            data=slow_query,
            headers={"Content-Type": "application/sparql-query"},
            catch_response=True,
            name="SPARQL Query: timeout_test",
            timeout=5.0  # 5 second timeout
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 504:  # Gateway timeout
                response.success()  # Expected behavior
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    def on_stop(self):
        """Cleanup and final statistics."""
        print(f"User completed {self.query_count} queries, {self.failed_queries} failed")


class SPARQLUpdateUser(HttpUser):
    """
    Simulated user performing SPARQL updates (INSERT/DELETE).
    """
    wait_time = between(2, 5)

    @task
    def execute_insert(self):
        """Execute SPARQL INSERT operation."""
        entity_id = random.randint(1000, 9999)
        update_query = f"""
            PREFIX ex: <http://example.org/>
            INSERT DATA {{
                ex:entity{entity_id} ex:property "value" .
                ex:entity{entity_id} ex:timestamp "{time.time()}" .
            }}
        """

        with self.client.post(
            "/sparql-update",
            data=update_query,
            headers={"Content-Type": "application/sparql-update"},
            catch_response=True,
            name="SPARQL Update: INSERT"
        ) as response:
            if response.status_code in [200, 204]:
                response.success()
            else:
                response.failure(f"Insert failed: {response.status_code}")

    @task
    def execute_delete(self):
        """Execute SPARQL DELETE operation."""
        entity_id = random.randint(1000, 9999)
        update_query = f"""
            PREFIX ex: <http://example.org/>
            DELETE WHERE {{
                ex:entity{entity_id} ?p ?o .
            }}
        """

        with self.client.post(
            "/sparql-update",
            data=update_query,
            headers={"Content-Type": "application/sparql-update"},
            catch_response=True,
            name="SPARQL Update: DELETE"
        ) as response:
            if response.status_code in [200, 204]:
                response.success()
            else:
                response.failure(f"Delete failed: {response.status_code}")


class SPARQLBatchUser(HttpUser):
    """
    User that executes batch queries for performance testing.
    """
    wait_time = between(5, 10)

    @task
    def execute_batch_queries(self):
        """Execute multiple queries in a batch."""
        queries = [
            f"SELECT ?s ?p ?o WHERE {{ ?s ?p ?o }} LIMIT {i*10}"
            for i in range(1, 6)
        ]

        batch_payload = {
            "queries": queries,
            "format": "json"
        }

        with self.client.post(
            "/sparql/batch",
            json=batch_payload,
            catch_response=True,
            name="SPARQL Batch Query"
        ) as response:
            if response.status_code == 200:
                try:
                    results = response.json()
                    if len(results) == len(queries):
                        response.success()
                    else:
                        response.failure("Incomplete batch results")
                except:
                    response.failure("Invalid batch response")
            else:
                response.failure(f"Batch failed: {response.status_code}")


class SPARQLStressUser(HttpUser):
    """
    User for stress testing with heavy queries.
    """
    wait_time = between(0.5, 2)

    @task
    def stress_test_query(self):
        """Execute queries rapidly for stress testing."""
        query = f"""
            SELECT ?s ?p ?o
            WHERE {{
                ?s ?p ?o
            }}
            LIMIT {random.randint(10, 100)}
        """

        with self.client.post(
            "/sparql",
            data=query,
            headers={"Content-Type": "application/sparql-query"},
            catch_response=True,
            name="SPARQL Stress Test"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:  # Rate limited
                response.success()  # Expected under stress
            else:
                response.failure(f"Stress test failed: {response.status_code}")


# Event handlers for custom metrics
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts."""
    print("Starting SPARQL endpoint load test...")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops."""
    print("SPARQL endpoint load test completed.")
    print(f"Total requests: {environment.stats.total.num_requests}")
    print(f"Total failures: {environment.stats.total.num_failures}")
    print(f"Average response time: {environment.stats.total.avg_response_time}ms")
    print(f"RPS: {environment.stats.total.total_rps}")
