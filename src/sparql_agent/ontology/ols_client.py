"""
OLS (Ontology Lookup Service) Client.

This module provides integration with the EMBL-EBI Ontology Lookup Service (OLS4)
for searching and retrieving ontology information.
"""

import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin

import requests


class OLSClient:
    """
    Client for interacting with the EMBL-EBI Ontology Lookup Service (OLS4).
    
    The OLS provides a unified API for accessing biomedical ontologies including
    GO, EFO, MONDO, HP, and many others.
    """

    def __init__(self, base_url: str = "https://www.ebi.ac.uk/ols4/api/"):
        """
        Initialize the OLS client.
        
        Args:
            base_url: Base URL for the OLS API (default: OLS4 production)
        """
        self.base_url = base_url.rstrip("/") + "/"
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "SPARQL-Agent/0.1.0"
        })

    def _request(
        self, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make a request to the OLS API.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            JSON response as dictionary
            
        Raises:
            requests.RequestException: On request failure
        """
        url = urljoin(self.base_url, endpoint)
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def search(
        self,
        query: str,
        ontology: Optional[str] = None,
        exact: bool = False,
        limit: int = 10,
        field_list: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for terms across ontologies.
        
        Args:
            query: Search query string
            ontology: Filter by specific ontology (e.g., "efo", "go", "mondo")
            exact: Require exact match
            limit: Maximum number of results to return
            field_list: Specific fields to return
            
        Returns:
            List of matching terms with metadata
        """
        params: Dict[str, Any] = {
            "q": query,
            "rows": limit,
        }
        
        if ontology:
            params["ontology"] = ontology
        if exact:
            params["exact"] = "true"
        if field_list:
            params["fieldList"] = ",".join(field_list)
            
        response = self._request("search", params)
        
        # Extract terms from response
        docs = response.get("response", {}).get("docs", [])
        return [self._format_term(doc) for doc in docs]

    def get_term(
        self, 
        ontology: str, 
        term_id: str,
        iri: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get detailed information about a specific term.
        
        Args:
            ontology: Ontology ID (e.g., "efo", "go")
            term_id: Term ID (e.g., "EFO_0000400")
            iri: Alternative IRI-based lookup
            
        Returns:
            Term details including labels, descriptions, and relationships
        """
        if iri:
            # Use IRI-based lookup
            params = {"iri": iri}
            response = self._request(f"ontologies/{ontology}/terms", params)
        else:
            # Use term ID lookup
            endpoint = f"ontologies/{ontology}/terms/{term_id}"
            response = self._request(endpoint)
            
        return self._format_term(response)

    def get_ontology(self, ontology_id: str) -> Dict[str, Any]:
        """
        Get information about a specific ontology.
        
        Args:
            ontology_id: Ontology identifier (e.g., "efo", "go", "mondo")
            
        Returns:
            Ontology metadata including title, description, and version
        """
        response = self._request(f"ontologies/{ontology_id}")
        return {
            "id": response.get("ontologyId"),
            "title": response.get("config", {}).get("title"),
            "description": response.get("config", {}).get("description"),
            "version": response.get("config", {}).get("version"),
            "namespace": response.get("config", {}).get("namespace"),
            "homepage": response.get("config", {}).get("homepage"),
            "num_terms": response.get("numberOfTerms"),
            "num_properties": response.get("numberOfProperties"),
            "num_individuals": response.get("numberOfIndividuals"),
            "status": response.get("status"),
        }

    def list_ontologies(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        List all available ontologies.
        
        Args:
            limit: Maximum number of ontologies to return
            
        Returns:
            List of ontology metadata
        """
        params = {"size": limit}
        response = self._request("ontologies", params)
        
        ontologies = response.get("_embedded", {}).get("ontologies", [])
        return [
            {
                "id": ont.get("ontologyId"),
                "title": ont.get("config", {}).get("title"),
                "description": ont.get("config", {}).get("description"),
                "num_terms": ont.get("numberOfTerms"),
            }
            for ont in ontologies
        ]

    def get_term_parents(
        self, 
        ontology: str, 
        term_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get parent terms for a given term.
        
        Args:
            ontology: Ontology ID
            term_id: Term ID
            
        Returns:
            List of parent terms
        """
        endpoint = f"ontologies/{ontology}/terms/{term_id}/parents"
        response = self._request(endpoint)
        
        terms = response.get("_embedded", {}).get("terms", [])
        return [self._format_term(term) for term in terms]

    def get_term_children(
        self, 
        ontology: str, 
        term_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get child terms for a given term.
        
        Args:
            ontology: Ontology ID
            term_id: Term ID
            
        Returns:
            List of child terms
        """
        endpoint = f"ontologies/{ontology}/terms/{term_id}/children"
        response = self._request(endpoint)
        
        terms = response.get("_embedded", {}).get("terms", [])
        return [self._format_term(term) for term in terms]

    def get_term_ancestors(
        self, 
        ontology: str, 
        term_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all ancestor terms (transitive parents).
        
        Args:
            ontology: Ontology ID
            term_id: Term ID
            
        Returns:
            List of ancestor terms
        """
        endpoint = f"ontologies/{ontology}/terms/{term_id}/ancestors"
        response = self._request(endpoint)
        
        terms = response.get("_embedded", {}).get("terms", [])
        return [self._format_term(term) for term in terms]

    def get_term_descendants(
        self, 
        ontology: str, 
        term_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all descendant terms (transitive children).
        
        Args:
            ontology: Ontology ID
            term_id: Term ID
            
        Returns:
            List of descendant terms
        """
        endpoint = f"ontologies/{ontology}/terms/{term_id}/descendants"
        response = self._request(endpoint)
        
        terms = response.get("_embedded", {}).get("terms", [])
        return [self._format_term(term) for term in terms]

    @staticmethod
    def _format_term(term_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format term data into a consistent structure.
        
        Args:
            term_data: Raw term data from OLS API
            
        Returns:
            Formatted term dictionary
        """
        return {
            "id": term_data.get("obo_id") or term_data.get("short_form"),
            "iri": term_data.get("iri"),
            "label": term_data.get("label"),
            "description": term_data.get("description", [None])[0] if term_data.get("description") else None,
            "ontology": term_data.get("ontology_name"),
            "synonyms": term_data.get("synonym", []),
            "type": term_data.get("type"),
            "is_defining_ontology": term_data.get("is_defining_ontology"),
            "is_obsolete": term_data.get("is_obsolete", False),
        }

    def download_ontology(
        self,
        ontology_id: str,
        output_path: Optional[Union[str, Path]] = None,
        format: str = "owl"
    ) -> Path:
        """
        Download an ontology file from OLS4.

        Args:
            ontology_id: Ontology identifier (e.g., "go", "chebi", "efo")
            output_path: Path to save the ontology file (defaults to temp file)
            format: Format to download (owl, obo, owl.xml, obo.owl)

        Returns:
            Path to the downloaded ontology file

        Raises:
            requests.RequestException: On download failure
        """
        # Get ontology metadata first to check if it exists
        ontology_info = self.get_ontology(ontology_id)

        # Try to get download link from config
        ontology_config = self._request(f"ontologies/{ontology_id}")
        config = ontology_config.get("config", {})

        # Try common download URLs
        download_url = None
        file_location = config.get("fileLocation")

        if file_location:
            # Use the fileLocation from OLS
            download_url = file_location
        else:
            # Construct common OWL download URLs
            namespace = config.get("namespace", "")
            preferred_prefix = config.get("preferredPrefix", ontology_id.lower())

            # Try common patterns
            potential_urls = [
                f"http://purl.obolibrary.org/obo/{preferred_prefix}.owl",
                f"http://purl.obolibrary.org/obo/{preferred_prefix}.obo",
                f"https://github.com/obophenotype/{preferred_prefix}-ontology/raw/master/{preferred_prefix}.owl",
            ]

            # Test each URL
            for url in potential_urls:
                try:
                    response = requests.head(url, timeout=10, allow_redirects=True)
                    if response.status_code == 200:
                        download_url = url
                        break
                except:
                    continue

        if not download_url:
            raise ValueError(
                f"Could not find download URL for ontology '{ontology_id}'. "
                f"Please specify the URL manually or check if the ontology is available."
            )

        # Download the file
        response = requests.get(download_url, stream=True, timeout=300)
        response.raise_for_status()

        # Determine output path
        if output_path is None:
            suffix = f".{format}" if not format.startswith(".") else format
            temp_file = tempfile.NamedTemporaryFile(
                suffix=suffix,
                prefix=f"{ontology_id}_",
                delete=False
            )
            output_path = Path(temp_file.name)
            temp_file.close()
        else:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write content to file
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return output_path

    def get_download_url(self, ontology_id: str) -> Optional[str]:
        """
        Get the download URL for an ontology.

        Args:
            ontology_id: Ontology identifier

        Returns:
            Download URL if available, None otherwise
        """
        try:
            ontology_config = self._request(f"ontologies/{ontology_id}")
            config = ontology_config.get("config", {})
            return config.get("fileLocation")
        except:
            return None

    def suggest_ontology(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Suggest ontologies based on a search query.

        Args:
            query: Search query (e.g., "gene", "protein", "disease")
            limit: Maximum number of suggestions

        Returns:
            List of relevant ontologies with metadata
        """
        params = {
            "q": query,
            "size": limit
        }

        response = self._request("ontologies", params)
        ontologies = response.get("_embedded", {}).get("ontologies", [])

        return [
            {
                "id": ont.get("ontologyId"),
                "title": ont.get("config", {}).get("title"),
                "description": ont.get("config", {}).get("description"),
                "num_terms": ont.get("numberOfTerms"),
                "namespace": ont.get("config", {}).get("namespace"),
                "preferred_prefix": ont.get("config", {}).get("preferredPrefix"),
            }
            for ont in ontologies
        ]

    def __repr__(self) -> str:
        """String representation of the OLS client."""
        return f"OLSClient(base_url={self.base_url})"


# ============================================================================
# Common Life Science Ontologies
# ============================================================================

# Well-known ontology configurations
COMMON_ONTOLOGIES = {
    "GO": {
        "id": "go",
        "name": "Gene Ontology",
        "description": "The Gene Ontology (GO) provides a framework for describing gene function",
        "url": "http://purl.obolibrary.org/obo/go.owl",
        "homepage": "http://geneontology.org/",
        "namespace": "http://purl.obolibrary.org/obo/GO_",
    },
    "CHEBI": {
        "id": "chebi",
        "name": "Chemical Entities of Biological Interest",
        "description": "A structured classification of molecular entities of biological interest",
        "url": "http://purl.obolibrary.org/obo/chebi.owl",
        "homepage": "https://www.ebi.ac.uk/chebi/",
        "namespace": "http://purl.obolibrary.org/obo/CHEBI_",
    },
    "PRO": {
        "id": "pr",
        "name": "Protein Ontology",
        "description": "An ontology for protein entities",
        "url": "http://purl.obolibrary.org/obo/pr.owl",
        "homepage": "https://proconsortium.org/",
        "namespace": "http://purl.obolibrary.org/obo/PR_",
    },
    "HPO": {
        "id": "hp",
        "name": "Human Phenotype Ontology",
        "description": "A standardized vocabulary of phenotypic abnormalities encountered in human disease",
        "url": "http://purl.obolibrary.org/obo/hp.owl",
        "homepage": "https://hpo.jax.org/",
        "namespace": "http://purl.obolibrary.org/obo/HP_",
    },
    "MONDO": {
        "id": "mondo",
        "name": "Monarch Disease Ontology",
        "description": "A semi-automatically constructed ontology that merges multiple disease ontologies",
        "url": "http://purl.obolibrary.org/obo/mondo.owl",
        "homepage": "https://mondo.monarchinitiative.org/",
        "namespace": "http://purl.obolibrary.org/obo/MONDO_",
    },
    "UBERON": {
        "id": "uberon",
        "name": "Uber Anatomy Ontology",
        "description": "An integrated cross-species anatomy ontology",
        "url": "http://purl.obolibrary.org/obo/uberon.owl",
        "homepage": "http://uberon.org/",
        "namespace": "http://purl.obolibrary.org/obo/UBERON_",
    },
    "CL": {
        "id": "cl",
        "name": "Cell Ontology",
        "description": "A structured controlled vocabulary for cell types",
        "url": "http://purl.obolibrary.org/obo/cl.owl",
        "homepage": "http://obophenotype.github.io/cell-ontology/",
        "namespace": "http://purl.obolibrary.org/obo/CL_",
    },
    "SO": {
        "id": "so",
        "name": "Sequence Ontology",
        "description": "A structured controlled vocabulary for genomic features",
        "url": "http://purl.obolibrary.org/obo/so.owl",
        "homepage": "http://www.sequenceontology.org/",
        "namespace": "http://purl.obolibrary.org/obo/SO_",
    },
    "EFO": {
        "id": "efo",
        "name": "Experimental Factor Ontology",
        "description": "An application ontology for experimental variables in studies",
        "url": "https://github.com/EBISPOT/efo/raw/main/efo.owl",
        "homepage": "https://www.ebi.ac.uk/efo/",
        "namespace": "http://www.ebi.ac.uk/efo/EFO_",
    },
    "DOID": {
        "id": "doid",
        "name": "Human Disease Ontology",
        "description": "An ontology for describing human diseases",
        "url": "http://purl.obolibrary.org/obo/doid.owl",
        "homepage": "https://disease-ontology.org/",
        "namespace": "http://purl.obolibrary.org/obo/DOID_",
    },
}


def get_ontology_config(ontology_key: str) -> Optional[Dict[str, Any]]:
    """
    Get configuration for a common ontology.

    Args:
        ontology_key: Ontology key (e.g., "GO", "CHEBI", "PRO", "HPO")

    Returns:
        Ontology configuration dictionary or None if not found
    """
    return COMMON_ONTOLOGIES.get(ontology_key.upper())


def list_common_ontologies() -> List[Dict[str, Any]]:
    """
    Get list of all configured common ontologies.

    Returns:
        List of ontology configurations
    """
    return list(COMMON_ONTOLOGIES.values())
