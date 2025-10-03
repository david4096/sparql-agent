// Core types for SPARQL Agent Frontend

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  query?: SPARQLQuery;
  results?: QueryResults;
  error?: string;
  isStreaming?: boolean;
}

export interface SPARQLQuery {
  id: string;
  query: string;
  endpoint: string;
  naturalLanguage: string;
  generatedAt: Date;
  executedAt?: Date;
  duration?: number;
  status: 'pending' | 'executing' | 'success' | 'error';
  validated?: boolean;
  explanation?: string;
}

export interface QueryResults {
  head: {
    vars: string[];
  };
  results: {
    bindings: ResultBinding[];
  };
  metadata?: {
    rowCount: number;
    executionTime: number;
    endpoint: string;
  };
}

export interface ResultBinding {
  [variable: string]: {
    type: 'uri' | 'literal' | 'bnode';
    value: string;
    datatype?: string;
    'xml:lang'?: string;
  };
}

export interface SPARQLEndpoint {
  id: string;
  name: string;
  url: string;
  description?: string;
  icon?: string;
  category?: string;
  examples?: string[];
  requiresAuth?: boolean;
  ontologyUrl?: string;
}

export interface OntologyTerm {
  uri: string;
  label: string;
  description?: string;
  type: 'class' | 'property' | 'individual';
  parentClass?: string;
  domain?: string;
  range?: string;
  examples?: string[];
}

export interface OntologyNode {
  id: string;
  label: string;
  uri: string;
  type: 'class' | 'property';
  children?: OntologyNode[];
  expanded?: boolean;
}

export interface QuerySuggestion {
  id: string;
  text: string;
  type: 'keyword' | 'term' | 'template' | 'history';
  ontologyTerm?: OntologyTerm;
  sparqlTemplate?: string;
  score?: number;
}

export interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  endpoint: SPARQLEndpoint;
  createdAt: Date;
  updatedAt: Date;
}

export interface UserPreferences {
  theme: 'light' | 'dark' | 'system';
  defaultEndpoint?: string;
  autoExecuteQueries: boolean;
  showQueryExplanations: boolean;
  maxResultsPerPage: number;
  syntaxHighlightTheme: string;
  enableNotifications: boolean;
  enableWebSocket: boolean;
}

export interface ExportFormat {
  format: 'csv' | 'json' | 'tsv' | 'turtle' | 'rdf-xml' | 'n-triples';
  filename: string;
}

export interface VisualizationConfig {
  type: 'table' | 'graph' | 'chart' | 'json';
  options?: {
    chartType?: 'bar' | 'line' | 'pie' | 'scatter';
    graphLayout?: 'force' | 'hierarchical' | 'circular';
    pageSize?: number;
    sortBy?: string;
    sortOrder?: 'asc' | 'desc';
  };
}

export interface QueryHistory {
  id: string;
  query: SPARQLQuery;
  results?: QueryResults;
  favorite: boolean;
  tags: string[];
  notes?: string;
}

export interface WebSocketMessage {
  type: 'query_start' | 'query_progress' | 'query_complete' | 'query_error' | 'typing' | 'validation';
  data: any;
  timestamp: Date;
}

export interface ValidationResult {
  valid: boolean;
  errors?: ValidationError[];
  warnings?: ValidationWarning[];
  suggestions?: string[];
}

export interface ValidationError {
  message: string;
  line?: number;
  column?: number;
  severity: 'error';
}

export interface ValidationWarning {
  message: string;
  line?: number;
  column?: number;
  severity: 'warning';
}

export interface KeyboardShortcut {
  key: string;
  ctrlKey?: boolean;
  shiftKey?: boolean;
  altKey?: boolean;
  metaKey?: boolean;
  description: string;
  action: () => void;
}

export interface APIError {
  message: string;
  code?: string;
  details?: any;
  timestamp: Date;
}
