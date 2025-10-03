import axios, { AxiosInstance } from 'axios';
import type {
  Message,
  SPARQLQuery,
  QueryResults,
  SPARQLEndpoint,
  OntologyTerm,
  QuerySuggestion,
  ValidationResult,
} from '@types/index';

class APIClient {
  private client: AxiosInstance;

  constructor(baseURL: string = '/api') {
    this.client = axios.create({
      baseURL,
      timeout: 60000, // 60 seconds
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor
    this.client.interceptors.request.use(
      config => {
        // Add auth token if available
        const token = localStorage.getItem('auth_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      error => Promise.reject(error)
    );

    // Response interceptor
    this.client.interceptors.response.use(
      response => response,
      error => {
        if (error.response?.status === 401) {
          // Handle unauthorized
          localStorage.removeItem('auth_token');
          window.dispatchEvent(new Event('unauthorized'));
        }
        return Promise.reject(error);
      }
    );
  }

  // Chat endpoints
  async sendMessage(message: string, sessionId?: string): Promise<Message> {
    const response = await this.client.post('/chat/message', {
      message,
      sessionId,
    });
    return response.data;
  }

  async streamMessage(
    message: string,
    sessionId: string,
    onChunk: (chunk: string) => void
  ): Promise<void> {
    const response = await fetch(`/api/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, sessionId }),
    });

    if (!response.body) throw new Error('No response body');

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value);
      onChunk(chunk);
    }
  }

  // Query endpoints
  async executeQuery(query: string, endpoint: string): Promise<QueryResults> {
    const response = await this.client.post('/query/execute', {
      query,
      endpoint,
    });
    return response.data;
  }

  async validateQuery(query: string): Promise<ValidationResult> {
    const response = await this.client.post('/query/validate', { query });
    return response.data;
  }

  async explainQuery(query: string): Promise<{ explanation: string }> {
    const response = await this.client.post('/query/explain', { query });
    return response.data;
  }

  async translateToSPARQL(naturalLanguage: string, endpoint: string): Promise<SPARQLQuery> {
    const response = await this.client.post('/query/translate', {
      naturalLanguage,
      endpoint,
    });
    return response.data;
  }

  // Endpoint endpoints
  async getEndpoints(): Promise<SPARQLEndpoint[]> {
    const response = await this.client.get('/endpoints');
    return response.data;
  }

  async getEndpoint(id: string): Promise<SPARQLEndpoint> {
    const response = await this.client.get(`/endpoints/${id}`);
    return response.data;
  }

  async testEndpoint(url: string): Promise<{ available: boolean; latency?: number }> {
    const response = await this.client.post('/endpoints/test', { url });
    return response.data;
  }

  // Ontology endpoints
  async getOntology(endpointId: string): Promise<OntologyTerm[]> {
    const response = await this.client.get(`/ontology/${endpointId}`);
    return response.data;
  }

  async searchOntology(query: string, endpointId: string): Promise<OntologyTerm[]> {
    const response = await this.client.get(`/ontology/${endpointId}/search`, {
      params: { q: query },
    });
    return response.data;
  }

  async getOntologyTerm(uri: string, endpointId: string): Promise<OntologyTerm> {
    const response = await this.client.get(`/ontology/${endpointId}/term`, {
      params: { uri },
    });
    return response.data;
  }

  // Suggestion endpoints
  async getSuggestions(
    input: string,
    endpointId: string,
    cursor: number
  ): Promise<QuerySuggestion[]> {
    const response = await this.client.get('/suggestions', {
      params: { input, endpointId, cursor },
    });
    return response.data;
  }

  async getQueryTemplates(endpointId: string): Promise<QuerySuggestion[]> {
    const response = await this.client.get(`/templates/${endpointId}`);
    return response.data;
  }

  // History endpoints
  async getQueryHistory(limit: number = 50): Promise<SPARQLQuery[]> {
    const response = await this.client.get('/history', {
      params: { limit },
    });
    return response.data;
  }

  async saveQuery(query: SPARQLQuery): Promise<void> {
    await this.client.post('/history', query);
  }

  async deleteQuery(queryId: string): Promise<void> {
    await this.client.delete(`/history/${queryId}`);
  }

  // Session endpoints
  async createSession(title: string, endpointId: string): Promise<{ id: string }> {
    const response = await this.client.post('/sessions', {
      title,
      endpointId,
    });
    return response.data;
  }

  async getSessions(): Promise<Array<{ id: string; title: string; updatedAt: Date }>> {
    const response = await this.client.get('/sessions');
    return response.data;
  }

  async getSession(sessionId: string): Promise<{ messages: Message[] }> {
    const response = await this.client.get(`/sessions/${sessionId}`);
    return response.data;
  }

  async deleteSession(sessionId: string): Promise<void> {
    await this.client.delete(`/sessions/${sessionId}`);
  }

  // Export endpoints
  async exportResults(results: QueryResults, format: string): Promise<Blob> {
    const response = await this.client.post(
      '/export',
      { results, format },
      { responseType: 'blob' }
    );
    return response.data;
  }
}

// Singleton instance
export const apiClient = new APIClient();

export default apiClient;
