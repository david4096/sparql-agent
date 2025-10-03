"""
Locust load testing for Web API endpoints.

Run with: locust -f locust_web.py --host=http://localhost:8000
"""

from locust import HttpUser, task, between, events, SequentialTaskSet
import random
import json
import time
from typing import Dict, Any, List


class WebAPIUser(HttpUser):
    """
    Simulated user interacting with the web API.
    """
    wait_time = between(1, 3)

    def on_start(self):
        """Initialize user session."""
        self.api_key = "test_api_key"
        self.session_token = None
        self.authenticate()

    def authenticate(self):
        """Authenticate with API."""
        payload = {
            "api_key": self.api_key,
            "client": "load_test"
        }

        with self.client.post(
            "/api/auth/login",
            json=payload,
            catch_response=True,
            name="API: Authentication"
        ) as response:
            if response.status_code == 200:
                result = response.json()
                self.session_token = result.get("token")
                response.success()
            else:
                response.failure("Authentication failed")

    def get_headers(self) -> Dict[str, str]:
        """Get headers with auth token."""
        return {
            "Authorization": f"Bearer {self.session_token}",
            "Content-Type": "application/json"
        }

    @task(10)
    def query_endpoint(self):
        """Execute SPARQL query via API."""
        payload = {
            "query": "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10",
            "endpoint": "http://example.org/sparql",
            "format": "json"
        }

        with self.client.post(
            "/api/query",
            json=payload,
            headers=self.get_headers(),
            catch_response=True,
            name="API: Execute Query"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Query failed: {response.status_code}")

    @task(8)
    def generate_query_endpoint(self):
        """Generate SPARQL query from natural language."""
        questions = [
            "Find all people",
            "List organizations in California",
            "Show publications from last year",
            "What proteins are involved in cancer?"
        ]

        payload = {
            "question": random.choice(questions),
            "provider": "anthropic",
            "include_explanation": True
        }

        with self.client.post(
            "/api/generate",
            json=payload,
            headers=self.get_headers(),
            catch_response=True,
            name="API: Generate Query"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Generation failed: {response.status_code}")

    @task(5)
    def discover_schema_endpoint(self):
        """Discover schema from endpoint."""
        payload = {
            "endpoint": "http://example.org/sparql",
            "sample_size": 100
        }

        with self.client.post(
            "/api/schema/discover",
            json=payload,
            headers=self.get_headers(),
            catch_response=True,
            name="API: Discover Schema"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Schema discovery failed: {response.status_code}")

    @task(3)
    def parse_ontology_endpoint(self):
        """Parse ontology file."""
        payload = {
            "ontology_url": "http://example.org/ontology.owl",
            "format": "owl"
        }

        with self.client.post(
            "/api/ontology/parse",
            json=payload,
            headers=self.get_headers(),
            catch_response=True,
            name="API: Parse Ontology"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Ontology parsing failed: {response.status_code}")

    @task(2)
    def get_query_history(self):
        """Get query history."""
        params = {
            "limit": 20,
            "offset": 0
        }

        with self.client.get(
            "/api/history",
            params=params,
            headers=self.get_headers(),
            catch_response=True,
            name="API: Query History"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure("History retrieval failed")

    @task(1)
    def get_statistics(self):
        """Get API statistics."""
        with self.client.get(
            "/api/stats",
            headers=self.get_headers(),
            catch_response=True,
            name="API: Statistics"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure("Stats retrieval failed")


class WebUIWorkflow(SequentialTaskSet):
    """
    Sequential workflow simulating typical user interaction.
    """

    @task
    def step1_home_page(self):
        """Load home page."""
        with self.client.get(
            "/",
            catch_response=True,
            name="Web UI: Home Page"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure("Home page failed")

    @task
    def step2_search_interface(self):
        """Load search interface."""
        with self.client.get(
            "/search",
            catch_response=True,
            name="Web UI: Search Interface"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure("Search interface failed")

    @task
    def step3_submit_query(self):
        """Submit search query."""
        payload = {
            "question": "Find all entities related to cancer research"
        }

        with self.client.post(
            "/search/submit",
            json=payload,
            catch_response=True,
            name="Web UI: Submit Query"
        ) as response:
            if response.status_code == 200:
                response.success()
                # Store query_id for next step
                result = response.json()
                self.query_id = result.get("query_id")
            else:
                response.failure("Query submission failed")

    @task
    def step4_view_results(self):
        """View query results."""
        if hasattr(self, 'query_id'):
            with self.client.get(
                f"/results/{self.query_id}",
                catch_response=True,
                name="Web UI: View Results"
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure("Results viewing failed")


class WebUIUser(HttpUser):
    """User simulating web UI interactions."""
    tasks = [WebUIWorkflow]
    wait_time = between(2, 5)


class RestAPIUser(HttpUser):
    """
    User testing REST API endpoints comprehensively.
    """
    wait_time = between(1, 4)

    @task(5)
    def get_endpoints_list(self):
        """Get list of SPARQL endpoints."""
        with self.client.get(
            "/api/endpoints",
            catch_response=True,
            name="REST: List Endpoints"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure("Endpoints list failed")

    @task(5)
    def get_endpoint_details(self):
        """Get details of specific endpoint."""
        endpoint_id = random.randint(1, 100)

        with self.client.get(
            f"/api/endpoints/{endpoint_id}",
            catch_response=True,
            name="REST: Endpoint Details"
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure("Endpoint details failed")

    @task(3)
    def create_saved_query(self):
        """Create saved query."""
        payload = {
            "name": f"Test Query {random.randint(1000, 9999)}",
            "query": "SELECT ?s ?p ?o WHERE { ?s ?p ?o }",
            "description": "Load test query"
        }

        with self.client.post(
            "/api/queries",
            json=payload,
            catch_response=True,
            name="REST: Create Query"
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure("Query creation failed")

    @task(4)
    def get_saved_queries(self):
        """Get list of saved queries."""
        params = {
            "limit": 50,
            "sort": "created_at"
        }

        with self.client.get(
            "/api/queries",
            params=params,
            catch_response=True,
            name="REST: List Queries"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure("Queries list failed")

    @task(2)
    def update_saved_query(self):
        """Update existing query."""
        query_id = random.randint(1, 100)
        payload = {
            "name": "Updated Query",
            "query": "SELECT * WHERE { ?s ?p ?o } LIMIT 20"
        }

        with self.client.put(
            f"/api/queries/{query_id}",
            json=payload,
            catch_response=True,
            name="REST: Update Query"
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure("Query update failed")

    @task(1)
    def delete_saved_query(self):
        """Delete saved query."""
        query_id = random.randint(1, 100)

        with self.client.delete(
            f"/api/queries/{query_id}",
            catch_response=True,
            name="REST: Delete Query"
        ) as response:
            if response.status_code in [200, 204, 404]:
                response.success()
            else:
                response.failure("Query deletion failed")


class APIVersioningUser(HttpUser):
    """
    Test API versioning and backward compatibility.
    """
    wait_time = between(2, 4)

    @task
    def test_v1_endpoint(self):
        """Test v1 API endpoint."""
        with self.client.get(
            "/api/v1/query",
            catch_response=True,
            name="API v1: Query"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure("v1 endpoint failed")

    @task
    def test_v2_endpoint(self):
        """Test v2 API endpoint (newer version)."""
        with self.client.get(
            "/api/v2/query",
            catch_response=True,
            name="API v2: Query"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure("v2 endpoint failed")


class WebhookUser(HttpUser):
    """
    Test webhook functionality.
    """
    wait_time = between(3, 6)

    @task
    def register_webhook(self):
        """Register webhook for query completion."""
        payload = {
            "url": "http://example.org/webhook",
            "events": ["query.completed", "query.failed"]
        }

        with self.client.post(
            "/api/webhooks",
            json=payload,
            catch_response=True,
            name="Webhooks: Register"
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure("Webhook registration failed")

    @task
    def list_webhooks(self):
        """List registered webhooks."""
        with self.client.get(
            "/api/webhooks",
            catch_response=True,
            name="Webhooks: List"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure("Webhook list failed")


class FileUploadUser(HttpUser):
    """
    Test file upload endpoints (ontologies, datasets).
    """
    wait_time = between(5, 10)

    @task
    def upload_ontology_file(self):
        """Upload ontology file."""
        files = {
            "file": ("test_ontology.owl", b"<owl:Ontology>test</owl:Ontology>", "application/rdf+xml")
        }
        data = {
            "name": "Test Ontology",
            "format": "owl"
        }

        with self.client.post(
            "/api/upload/ontology",
            files=files,
            data=data,
            catch_response=True,
            name="Upload: Ontology File"
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure("File upload failed")

    @task
    def upload_dataset_file(self):
        """Upload dataset file."""
        files = {
            "file": ("test_data.ttl", b"@prefix ex: <http://example.org/>.", "text/turtle")
        }

        with self.client.post(
            "/api/upload/dataset",
            files=files,
            catch_response=True,
            name="Upload: Dataset File"
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure("Dataset upload failed")


class StaticAssetsUser(HttpUser):
    """
    Test static asset loading performance.
    """
    wait_time = between(1, 2)

    @task(5)
    def load_css(self):
        """Load CSS files."""
        with self.client.get(
            "/static/css/main.css",
            catch_response=True,
            name="Static: CSS"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure("CSS loading failed")

    @task(5)
    def load_javascript(self):
        """Load JavaScript files."""
        with self.client.get(
            "/static/js/app.js",
            catch_response=True,
            name="Static: JavaScript"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure("JS loading failed")

    @task(2)
    def load_images(self):
        """Load image assets."""
        images = ["logo.png", "icon.svg", "background.jpg"]
        image = random.choice(images)

        with self.client.get(
            f"/static/images/{image}",
            catch_response=True,
            name="Static: Images"
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure("Image loading failed")


# Event handlers
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts."""
    print("Starting Web API load test...")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops."""
    print("Web API load test completed.")
    print(f"Total requests: {environment.stats.total.num_requests}")
    print(f"Total failures: {environment.stats.total.num_failures}")
    print(f"Average response time: {environment.stats.total.avg_response_time}ms")
    print(f"RPS: {environment.stats.total.total_rps}")
    print(f"50th percentile: {environment.stats.total.get_response_time_percentile(0.5)}ms")
    print(f"95th percentile: {environment.stats.total.get_response_time_percentile(0.95)}ms")
    print(f"99th percentile: {environment.stats.total.get_response_time_percentile(0.99)}ms")
