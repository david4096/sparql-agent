#!/usr/bin/env python3
"""
SPARQL Agent Chat UI Web Interface

A Flask-based web interface for the SPARQL Agent system that allows users
to input natural language queries and get SPARQL results with visualization.
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

import flask
from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from sparql_agent.llm import create_anthropic_provider
    from sparql_agent.query import quick_generate, create_prompt_engine
    from sparql_agent.execution import execute_query, execute_query_with_validation, QueryExecutor
    from sparql_agent.query.validation_retry import validate_before_execution
    from sparql_agent.query.schema_tools import create_schema_tools
    from sparql_agent.discovery import EndpointPinger, EndpointStatus
    from sparql_agent.formatting.visualizer import VisualizationSelector
except ImportError as e:
    print(f"Error importing SPARQL Agent modules: {e}")
    print("Please ensure the SPARQL Agent is properly installed.")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask app setup
app = Flask(__name__,
           template_folder='templates',
           static_folder='static')
app.secret_key = os.urandom(24)
CORS(app)

# Common SPARQL endpoints
ENDPOINTS = {
    "Wikidata": "https://query.wikidata.org/sparql",
    "DBpedia": "https://dbpedia.org/sparql",
    "EBI OLS4": "https://www.ebi.ac.uk/ols4/api/sparql",
    "UniProt": "https://sparql.uniprot.org/sparql",
    "RDF Portal (FAIR)": "https://rdfportal.org/sparql",
    "RDF Portal (Biomedical)": "https://rdfportal.org/biomedical/sparql",
}

class ChatSession:
    """Manages a chat session with conversation history."""

    def __init__(self):
        self.history: List[Dict[str, Any]] = []
        self.created_at = datetime.now()

    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add a message to the conversation history."""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        self.history.append(message)

    def get_context(self, limit: int = 10) -> str:
        """Get recent conversation context for the LLM."""
        recent = self.history[-limit:]
        context = []
        for msg in recent:
            if msg["role"] == "user":
                context.append(f"User: {msg['content']}")
            elif msg["role"] == "assistant":
                context.append(f"Assistant: {msg['content']}")
        return "\n".join(context)

def get_session() -> ChatSession:
    """Get or create a chat session."""
    if 'session_id' not in session:
        session['session_id'] = os.urandom(16).hex()
        session['chat_history'] = []
        session['session_created'] = datetime.now().isoformat()

    # Create ChatSession object from session data
    chat_session = ChatSession()
    chat_session.history = session.get('chat_history', [])
    if 'session_created' in session:
        chat_session.created_at = datetime.fromisoformat(session['session_created'])

    return chat_session

def save_session(chat_session: ChatSession):
    """Save chat session back to Flask session."""
    session['chat_history'] = chat_session.history
    session['session_created'] = chat_session.created_at.isoformat()

@app.route('/')
def index():
    """Main chat interface."""
    return render_template('index.html', endpoints=ENDPOINTS)

@app.route('/api/query', methods=['POST'])
def query():
    """Process natural language query and return SPARQL results."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        nl_query = data.get('query', '').strip()
        endpoint_url = data.get('endpoint', ENDPOINTS['Wikidata'])

        if not nl_query:
            return jsonify({"error": "No query provided"}), 400

        # Get API key
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            return jsonify({
                "error": "ANTHROPIC_API_KEY not configured. Please set your API key."
            }), 500

        chat_session = get_session()
        chat_session.add_message("user", nl_query)
        save_session(chat_session)

        logger.info(f"Processing query: {nl_query}")
        logger.info(f"Using endpoint: {endpoint_url}")

        # Step 1: Generate SPARQL query using quick_generate
        try:
            llm_client = create_anthropic_provider(api_key=api_key)
            sparql_query = quick_generate(nl_query, llm_client=llm_client)
            logger.info(f"Generated initial SPARQL: {sparql_query}")
        except Exception as e:
            error_msg = f"Failed to generate SPARQL query: {str(e)}"
            logger.error(error_msg)
            chat_session.add_message("assistant", error_msg, {"error": True})
            save_session(chat_session)
            return jsonify({"error": error_msg}), 500

        # Step 2: Execute SPARQL query with validation and retry
        try:
            # Create schema tools for the endpoint (with discovery skip for faster response)
            schema_tools = create_schema_tools(endpoint_url, skip_discovery=True)

            # Execute with validation and retry logic
            result, execution_metadata = execute_query_with_validation(
                query=sparql_query,
                endpoint=endpoint_url,
                original_intent=nl_query,
                llm_client=llm_client,
                schema_tools=schema_tools,
                max_retries=5,
                max_execution_retries=3,
                timeout=60
            )

            logger.info(f"Query executed with validation, {len(result.bindings)} results")
            logger.info(f"Validation metadata: {execution_metadata}")

            # Extract final query used (may be different from original if retries occurred)
            final_sparql_query = execution_metadata.get('final_query', sparql_query)

        except Exception as e:
            error_msg = f"Query execution error: {str(e)}"
            logger.error(error_msg)
            chat_session.add_message("assistant", error_msg, {"error": True})
            save_session(chat_session)
            return jsonify({
                "error": error_msg,
                "sparql_query": sparql_query
            }), 500

        # Step 3: Format results
        try:
            # Convert bindings to simple format
            formatted_results = []
            for binding in result.bindings:
                formatted_binding = {}
                for var, value in binding.items():
                    formatted_binding[var] = str(value)
                formatted_results.append(formatted_binding)

            # Try to generate visualization suggestion
            visualization = None
            try:
                viz_type = VisualizationSelector.recommend_visualization(result)
                if viz_type:
                    visualization = {
                        "type": viz_type.value,
                        "config": {}
                    }
            except Exception as viz_error:
                logger.warning(f"Visualization suggestion failed: {viz_error}")

            # Step 4: Generate natural language explanation (if requested)
            nl_explanation = None
            try:
                # Generate a natural language explanation of the results
                explanation_prompt = f"""
Given the original question: "{nl_query}"
And the SPARQL query: {final_sparql_query}
And the results showing {len(formatted_results)} items:

{json.dumps(formatted_results[:3], indent=2) if formatted_results else "No results"}

Please provide a clear, concise explanation in plain English of what was found and what it means.
Focus on answering the original question and summarizing the key insights from the data.
"""

                from sparql_agent.llm.client import LLMRequest
                llm_request = LLMRequest(prompt=explanation_prompt, max_tokens=500)
                explanation_response = llm_client.generate(llm_request)
                if explanation_response and hasattr(explanation_response, 'content'):
                    nl_explanation = explanation_response.content.strip()

            except Exception as exp_error:
                logger.warning(f"Natural language explanation generation failed: {exp_error}")

            response_data = {
                "success": True,
                "query": nl_query,
                "sparql_query": final_sparql_query,
                "original_query": sparql_query if final_sparql_query != sparql_query else None,
                "endpoint": endpoint_url,
                "results": formatted_results,
                "result_count": len(formatted_results),
                "execution_time": getattr(result, 'execution_time', 0),
                "visualization": visualization,
                "explanation": nl_explanation,
                "validation_metadata": execution_metadata
            }

            success_msg = f"Found {len(formatted_results)} results"
            chat_session.add_message("assistant", success_msg, {
                "sparql_query": final_sparql_query,
                "original_query": sparql_query if final_sparql_query != sparql_query else None,
                "result_count": len(formatted_results),
                "validation_attempts": execution_metadata.get('validation_attempts', 0),
                "execution_attempts": execution_metadata.get('execution_attempts', 1)
            })
            save_session(chat_session)

            return jsonify(response_data)

        except Exception as e:
            error_msg = f"Result formatting error: {str(e)}"
            logger.error(error_msg)
            return jsonify({
                "error": error_msg,
                "sparql_query": final_sparql_query if 'final_sparql_query' in locals() else sparql_query
            }), 500

    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg)
        return jsonify({"error": error_msg}), 500

@app.route('/api/endpoints/test', methods=['POST'])
def test_endpoint():
    """Test endpoint connectivity."""
    try:
        data = request.get_json()
        endpoint_url = data.get('endpoint')

        if not endpoint_url:
            return jsonify({"error": "No endpoint provided"}), 400

        pinger = EndpointPinger()
        health = pinger.ping_sync(endpoint_url)

        return jsonify({
            "endpoint": endpoint_url,
            "status": health.status.value,
            "response_time": health.response_time_ms,
            "accessible": health.status in [EndpointStatus.HEALTHY, EndpointStatus.DEGRADED],
            "error": health.error_message if health.error_message else None
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/history')
def get_history():
    """Get conversation history."""
    try:
        chat_session = get_session()
        return jsonify({
            "history": chat_session.history,
            "session_created": chat_session.created_at.isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/clear', methods=['POST'])
def clear_session():
    """Clear conversation history."""
    try:
        session.pop('session_id', None)
        session.pop('chat_history', None)
        session.pop('session_created', None)
        return jsonify({"success": True, "message": "Session cleared"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Check for API key
    if not os.getenv('ANTHROPIC_API_KEY'):
        print("⚠️  Warning: ANTHROPIC_API_KEY not set!")
        print("   Please set your Anthropic API key:")
        print("   export ANTHROPIC_API_KEY='your-key-here'")
        print()

    print("🚀 Starting SPARQL Agent Chat UI...")
    print("📱 Open http://localhost:5001 in your browser")
    print("💡 Use Ctrl+C to stop the server")

    # Run Flask development server
    app.run(
        host='0.0.0.0',
        port=5001,
        debug=True,
        threaded=True
    )