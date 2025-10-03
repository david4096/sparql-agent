"""
Abstract base classes for the SPARQL-LLM system.

This module defines the core abstractions and interfaces that all implementations
must follow. These abstract base classes ensure consistent behavior across different
implementations and make the system extensible.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set

from .types import (
    EndpointInfo,
    FormattedResult,
    GeneratedQuery,
    LLMResponse,
    OntologyInfo,
    QueryResult,
    SchemaInfo,
)


class SPARQLEndpoint(ABC):
    """
    Abstract base class for SPARQL endpoint implementations.

    This class defines the interface for interacting with SPARQL endpoints,
    including query execution, updates, and endpoint management.
    """

    @abstractmethod
    def __init__(self, endpoint_info: EndpointInfo, **kwargs):
        """
        Initialize the SPARQL endpoint.

        Args:
            endpoint_info: Information about the endpoint
            **kwargs: Additional implementation-specific arguments
        """
        self.endpoint_info = endpoint_info

    @abstractmethod
    def query(self, sparql_query: str, timeout: Optional[int] = None) -> QueryResult:
        """
        Execute a SPARQL SELECT or ASK query.

        Args:
            sparql_query: The SPARQL query to execute
            timeout: Optional timeout in seconds (overrides endpoint default)

        Returns:
            QueryResult containing the query results

        Raises:
            QuerySyntaxError: If the query has syntax errors
            QueryExecutionError: If query execution fails
            EndpointConnectionError: If connection to endpoint fails
        """
        pass

    @abstractmethod
    def update(self, sparql_update: str, timeout: Optional[int] = None) -> bool:
        """
        Execute a SPARQL UPDATE operation.

        Args:
            sparql_update: The SPARQL UPDATE query to execute
            timeout: Optional timeout in seconds (overrides endpoint default)

        Returns:
            True if update was successful

        Raises:
            QuerySyntaxError: If the update has syntax errors
            QueryExecutionError: If update execution fails
            EndpointConnectionError: If connection to endpoint fails
        """
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test the connection to the SPARQL endpoint.

        Returns:
            True if connection is successful, False otherwise
        """
        pass

    @abstractmethod
    def get_endpoint_info(self) -> EndpointInfo:
        """
        Get information about the endpoint.

        Returns:
            EndpointInfo object with endpoint details
        """
        pass

    @abstractmethod
    def set_authentication(self, username: str, password: str) -> None:
        """
        Set authentication credentials for the endpoint.

        Args:
            username: Username for authentication
            password: Password for authentication
        """
        pass

    @abstractmethod
    def clear_authentication(self) -> None:
        """Clear authentication credentials."""
        pass

    def close(self) -> None:
        """
        Close the endpoint connection and clean up resources.

        Override this method if your implementation needs cleanup.
        """
        pass


class OntologyProvider(ABC):
    """
    Abstract base class for ontology providers.

    This class defines the interface for loading, parsing, and querying ontologies
    to support ontology-guided query generation and schema understanding.
    """

    @abstractmethod
    def __init__(self, **kwargs):
        """
        Initialize the ontology provider.

        Args:
            **kwargs: Implementation-specific arguments
        """
        pass

    @abstractmethod
    def load_ontology(self, source: str, format: Optional[str] = None) -> OntologyInfo:
        """
        Load an ontology from a source.

        Args:
            source: Path, URL, or identifier of the ontology
            format: Optional format specification (e.g., 'rdf/xml', 'turtle', 'n3')

        Returns:
            OntologyInfo object containing the parsed ontology

        Raises:
            OntologyLoadError: If loading fails
            OntologyParseError: If parsing fails
        """
        pass

    @abstractmethod
    def load_from_endpoint(self, endpoint: SPARQLEndpoint) -> OntologyInfo:
        """
        Load ontology information from a SPARQL endpoint.

        Args:
            endpoint: The SPARQL endpoint to load from

        Returns:
            OntologyInfo object containing the discovered ontology

        Raises:
            OntologyLoadError: If loading fails
            EndpointError: If endpoint access fails
        """
        pass

    @abstractmethod
    def get_class(self, class_uri: str) -> Optional[Any]:
        """
        Get an OWL class by its URI.

        Args:
            class_uri: The URI of the class

        Returns:
            OWLClass object or None if not found
        """
        pass

    @abstractmethod
    def get_property(self, property_uri: str) -> Optional[Any]:
        """
        Get an OWL property by its URI.

        Args:
            property_uri: The URI of the property

        Returns:
            OWLProperty object or None if not found
        """
        pass

    @abstractmethod
    def find_classes_by_label(self, label: str, fuzzy: bool = False) -> List[str]:
        """
        Find classes by their label.

        Args:
            label: The label to search for
            fuzzy: Whether to use fuzzy matching

        Returns:
            List of class URIs matching the label
        """
        pass

    @abstractmethod
    def find_properties_by_label(self, label: str, fuzzy: bool = False) -> List[str]:
        """
        Find properties by their label.

        Args:
            label: The label to search for
            fuzzy: Whether to use fuzzy matching

        Returns:
            List of property URIs matching the label
        """
        pass

    @abstractmethod
    def get_class_hierarchy(self, class_uri: str, max_depth: int = -1) -> Dict[str, Any]:
        """
        Get the class hierarchy for a given class.

        Args:
            class_uri: The URI of the class
            max_depth: Maximum depth to traverse (-1 for unlimited)

        Returns:
            Dictionary representing the class hierarchy
        """
        pass

    @abstractmethod
    def get_property_hierarchy(self, property_uri: str, max_depth: int = -1) -> Dict[str, Any]:
        """
        Get the property hierarchy for a given property.

        Args:
            property_uri: The URI of the property
            max_depth: Maximum depth to traverse (-1 for unlimited)

        Returns:
            Dictionary representing the property hierarchy
        """
        pass

    @abstractmethod
    def validate_ontology(self) -> List[str]:
        """
        Validate the ontology for consistency and completeness.

        Returns:
            List of validation warnings/errors (empty if valid)
        """
        pass


class SchemaDiscoverer(ABC):
    """
    Abstract base class for schema discovery implementations.

    This class defines the interface for discovering schema information from
    SPARQL endpoints, with support for ontology-aware discovery.
    """

    @abstractmethod
    def __init__(self, endpoint: SPARQLEndpoint, ontology_provider: Optional[OntologyProvider] = None, **kwargs):
        """
        Initialize the schema discoverer.

        Args:
            endpoint: The SPARQL endpoint to discover schema from
            ontology_provider: Optional ontology provider for ontology-guided discovery
            **kwargs: Additional implementation-specific arguments
        """
        self.endpoint = endpoint
        self.ontology_provider = ontology_provider

    @abstractmethod
    def discover_schema(self, use_ontology: bool = True, sample_size: int = 100) -> SchemaInfo:
        """
        Discover schema information from the endpoint.

        Args:
            use_ontology: Whether to use ontology information for discovery
            sample_size: Number of samples to collect for each class

        Returns:
            SchemaInfo object containing discovered schema

        Raises:
            SchemaDiscoveryError: If discovery fails
            EndpointError: If endpoint access fails
        """
        pass

    @abstractmethod
    def discover_classes(self) -> Set[str]:
        """
        Discover all classes in the dataset.

        Returns:
            Set of class URIs

        Raises:
            SchemaDiscoveryError: If discovery fails
        """
        pass

    @abstractmethod
    def discover_properties(self) -> Set[str]:
        """
        Discover all properties in the dataset.

        Returns:
            Set of property URIs

        Raises:
            SchemaDiscoveryError: If discovery fails
        """
        pass

    @abstractmethod
    def discover_namespaces(self) -> Dict[str, str]:
        """
        Discover namespaces used in the dataset.

        Returns:
            Dictionary mapping prefixes to namespace URIs

        Raises:
            SchemaDiscoveryError: If discovery fails
        """
        pass

    @abstractmethod
    def get_class_count(self, class_uri: str) -> int:
        """
        Get the number of instances of a class.

        Args:
            class_uri: The URI of the class

        Returns:
            Count of instances

        Raises:
            QueryExecutionError: If count query fails
        """
        pass

    @abstractmethod
    def get_property_count(self, property_uri: str) -> int:
        """
        Get the number of triples using a property.

        Args:
            property_uri: The URI of the property

        Returns:
            Count of triples

        Raises:
            QueryExecutionError: If count query fails
        """
        pass

    @abstractmethod
    def get_sample_instances(self, class_uri: str, limit: int = 10) -> List[str]:
        """
        Get sample instances of a class.

        Args:
            class_uri: The URI of the class
            limit: Maximum number of samples to return

        Returns:
            List of instance URIs

        Raises:
            QueryExecutionError: If sample query fails
        """
        pass

    @abstractmethod
    def infer_property_domain(self, property_uri: str) -> Set[str]:
        """
        Infer the domain (subject classes) of a property.

        Args:
            property_uri: The URI of the property

        Returns:
            Set of class URIs that use this property

        Raises:
            QueryExecutionError: If inference query fails
        """
        pass

    @abstractmethod
    def infer_property_range(self, property_uri: str) -> Set[str]:
        """
        Infer the range (object classes/datatypes) of a property.

        Args:
            property_uri: The URI of the property

        Returns:
            Set of class/datatype URIs that appear as values

        Raises:
            QueryExecutionError: If inference query fails
        """
        pass


class QueryGenerator(ABC):
    """
    Abstract base class for SPARQL query generation from natural language.

    This class defines the interface for generating SPARQL queries from natural
    language questions, with support for ontology-guided generation.
    """

    @abstractmethod
    def __init__(
        self,
        llm_provider: 'LLMProvider',
        schema_info: SchemaInfo,
        ontology_provider: Optional[OntologyProvider] = None,
        **kwargs
    ):
        """
        Initialize the query generator.

        Args:
            llm_provider: The LLM provider to use for generation
            schema_info: Schema information from the target endpoint
            ontology_provider: Optional ontology provider for ontology-guided generation
            **kwargs: Additional implementation-specific arguments
        """
        self.llm_provider = llm_provider
        self.schema_info = schema_info
        self.ontology_provider = ontology_provider

    @abstractmethod
    def generate(
        self,
        natural_language_query: str,
        use_ontology: bool = True,
        optimize: bool = True
    ) -> GeneratedQuery:
        """
        Generate a SPARQL query from a natural language question.

        Args:
            natural_language_query: The natural language question
            use_ontology: Whether to use ontology information for generation
            optimize: Whether to optimize the generated query

        Returns:
            GeneratedQuery object containing the query and metadata

        Raises:
            QueryGenerationError: If generation fails
            LLMError: If LLM interaction fails
        """
        pass

    @abstractmethod
    def generate_multiple(
        self,
        natural_language_query: str,
        count: int = 3,
        use_ontology: bool = True
    ) -> List[GeneratedQuery]:
        """
        Generate multiple alternative SPARQL queries.

        Args:
            natural_language_query: The natural language question
            count: Number of alternatives to generate
            use_ontology: Whether to use ontology information

        Returns:
            List of GeneratedQuery objects

        Raises:
            QueryGenerationError: If generation fails
            LLMError: If LLM interaction fails
        """
        pass

    @abstractmethod
    def validate_query(self, sparql_query: str) -> List[str]:
        """
        Validate a SPARQL query.

        Args:
            sparql_query: The SPARQL query to validate

        Returns:
            List of validation errors (empty if valid)
        """
        pass

    @abstractmethod
    def optimize_query(self, sparql_query: str) -> str:
        """
        Optimize a SPARQL query.

        Args:
            sparql_query: The SPARQL query to optimize

        Returns:
            Optimized SPARQL query

        Raises:
            QueryOptimizationError: If optimization fails
        """
        pass

    @abstractmethod
    def explain_query(self, sparql_query: str) -> str:
        """
        Generate a natural language explanation of a SPARQL query.

        Args:
            sparql_query: The SPARQL query to explain

        Returns:
            Natural language explanation

        Raises:
            LLMError: If explanation generation fails
        """
        pass


class LLMProvider(ABC):
    """
    Abstract base class for LLM provider implementations.

    This class defines the interface for interacting with Large Language Models
    for query generation, explanation, and other NLP tasks.
    """

    @abstractmethod
    def __init__(self, model: str, api_key: Optional[str] = None, **kwargs):
        """
        Initialize the LLM provider.

        Args:
            model: The model identifier to use
            api_key: Optional API key for authentication
            **kwargs: Additional implementation-specific arguments
        """
        self.model = model
        self.api_key = api_key

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response from the LLM.

        Args:
            prompt: The prompt to send to the LLM
            system_prompt: Optional system prompt to set context
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific arguments

        Returns:
            LLMResponse containing the generated content and metadata

        Raises:
            LLMError: If generation fails
            LLMAuthenticationError: If authentication fails
            LLMRateLimitError: If rate limit is exceeded
        """
        pass

    @abstractmethod
    def generate_with_json_schema(
        self,
        prompt: str,
        json_schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response conforming to a JSON schema.

        Args:
            prompt: The prompt to send to the LLM
            json_schema: JSON schema that the response should conform to
            system_prompt: Optional system prompt to set context
            temperature: Sampling temperature (0-1)
            **kwargs: Additional provider-specific arguments

        Returns:
            LLMResponse with content as valid JSON conforming to schema

        Raises:
            LLMError: If generation fails
            LLMResponseError: If response doesn't conform to schema
        """
        pass

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in a text.

        Args:
            text: The text to count tokens for

        Returns:
            Number of tokens

        Raises:
            LLMError: If token counting fails
        """
        pass

    @abstractmethod
    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Estimate the cost of a request.

        Args:
            prompt_tokens: Number of tokens in the prompt
            completion_tokens: Number of tokens in the completion

        Returns:
            Estimated cost in USD
        """
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model.

        Returns:
            Dictionary containing model information (context length, capabilities, etc.)
        """
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test the connection to the LLM provider.

        Returns:
            True if connection is successful, False otherwise
        """
        pass


class ResultFormatter(ABC):
    """
    Abstract base class for query result formatting.

    This class defines the interface for formatting query results in various
    formats (table, JSON, markdown, etc.) and generating human-readable summaries.
    """

    @abstractmethod
    def __init__(self, llm_provider: Optional['LLMProvider'] = None, **kwargs):
        """
        Initialize the result formatter.

        Args:
            llm_provider: Optional LLM provider for generating summaries
            **kwargs: Additional implementation-specific arguments
        """
        self.llm_provider = llm_provider

    @abstractmethod
    def format(
        self,
        result: QueryResult,
        format_type: str = "table",
        include_summary: bool = False,
        **kwargs
    ) -> FormattedResult:
        """
        Format a query result.

        Args:
            result: The QueryResult to format
            format_type: Type of formatting (table, json, markdown, csv, etc.)
            include_summary: Whether to include a human-readable summary
            **kwargs: Additional formatting options

        Returns:
            FormattedResult object containing formatted content

        Raises:
            FormattingError: If formatting fails
            InvalidFormatError: If format_type is not supported
        """
        pass

    @abstractmethod
    def format_to_table(self, result: QueryResult, **kwargs) -> str:
        """
        Format result as a table.

        Args:
            result: The QueryResult to format
            **kwargs: Additional table formatting options

        Returns:
            Formatted table as string

        Raises:
            FormattingError: If formatting fails
        """
        pass

    @abstractmethod
    def format_to_json(self, result: QueryResult, pretty: bool = True, **kwargs) -> str:
        """
        Format result as JSON.

        Args:
            result: The QueryResult to format
            pretty: Whether to pretty-print the JSON
            **kwargs: Additional JSON formatting options

        Returns:
            Formatted JSON as string

        Raises:
            FormattingError: If formatting fails
        """
        pass

    @abstractmethod
    def format_to_markdown(self, result: QueryResult, **kwargs) -> str:
        """
        Format result as Markdown.

        Args:
            result: The QueryResult to format
            **kwargs: Additional Markdown formatting options

        Returns:
            Formatted Markdown as string

        Raises:
            FormattingError: If formatting fails
        """
        pass

    @abstractmethod
    def format_to_csv(self, result: QueryResult, **kwargs) -> str:
        """
        Format result as CSV.

        Args:
            result: The QueryResult to format
            **kwargs: Additional CSV formatting options

        Returns:
            Formatted CSV as string

        Raises:
            FormattingError: If formatting fails
        """
        pass

    @abstractmethod
    def generate_summary(self, result: QueryResult, natural_language_query: Optional[str] = None) -> str:
        """
        Generate a human-readable summary of the results.

        Args:
            result: The QueryResult to summarize
            natural_language_query: Optional original natural language query

        Returns:
            Human-readable summary

        Raises:
            FormattingError: If summary generation fails
            LLMError: If LLM-based summary generation fails
        """
        pass

    @abstractmethod
    def suggest_visualizations(self, result: QueryResult) -> List[Dict[str, Any]]:
        """
        Suggest appropriate visualizations for the results.

        Args:
            result: The QueryResult to analyze

        Returns:
            List of visualization suggestions with metadata

        Raises:
            FormattingError: If suggestion generation fails
        """
        pass

    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """
        Get list of supported format types.

        Returns:
            List of supported format type strings
        """
        pass
