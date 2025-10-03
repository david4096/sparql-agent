import { format, formatDistance, formatRelative } from 'date-fns';
import type { QueryResults, ResultBinding } from '@types/index';

// Date formatting
export const formatTimestamp = (date: Date): string => {
  return format(date, 'PPpp');
};

export const formatRelativeTime = (date: Date): string => {
  return formatDistance(date, new Date(), { addSuffix: true });
};

export const formatRelativeDate = (date: Date): string => {
  return formatRelative(date, new Date());
};

// Number formatting
export const formatNumber = (num: number): string => {
  return new Intl.NumberFormat('en-US').format(num);
};

export const formatDuration = (ms: number): string => {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(2)}s`;
  const minutes = Math.floor(ms / 60000);
  const seconds = ((ms % 60000) / 1000).toFixed(0);
  return `${minutes}m ${seconds}s`;
};

export const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
};

// URI formatting
export const formatURI = (uri: string): string => {
  try {
    const url = new URL(uri);
    return url.pathname.split('/').pop() || uri;
  } catch {
    return uri.split('/').pop() || uri.split('#').pop() || uri;
  }
};

export const getPrefix = (uri: string): string => {
  const lastSlash = uri.lastIndexOf('/');
  const lastHash = uri.lastIndexOf('#');
  const splitPoint = Math.max(lastSlash, lastHash);
  return splitPoint > 0 ? uri.substring(0, splitPoint + 1) : uri;
};

// SPARQL result formatting
export const formatBindingValue = (binding: ResultBinding[string]): string => {
  if (!binding) return '';

  switch (binding.type) {
    case 'uri':
      return formatURI(binding.value);
    case 'literal':
      if (binding['xml:lang']) {
        return `${binding.value}@${binding['xml:lang']}`;
      }
      if (binding.datatype) {
        const type = formatURI(binding.datatype);
        if (type === 'dateTime' || type === 'date') {
          try {
            return format(new Date(binding.value), 'PPpp');
          } catch {
            return binding.value;
          }
        }
        return binding.value;
      }
      return binding.value;
    case 'bnode':
      return `_:${binding.value}`;
    default:
      return binding.value;
  }
};

// Results conversion
export const resultsToCSV = (results: QueryResults): string => {
  const headers = results.head.vars;
  const rows = results.results.bindings;

  const csvRows = [
    headers.join(','),
    ...rows.map(row =>
      headers.map(header => {
        const value = row[header] ? formatBindingValue(row[header]) : '';
        // Escape quotes and wrap in quotes if contains comma
        return value.includes(',') || value.includes('"')
          ? `"${value.replace(/"/g, '""')}"`
          : value;
      }).join(',')
    ),
  ];

  return csvRows.join('\n');
};

export const resultsToJSON = (results: QueryResults): string => {
  return JSON.stringify(results, null, 2);
};

export const resultsToTSV = (results: QueryResults): string => {
  const headers = results.head.vars;
  const rows = results.results.bindings;

  const tsvRows = [
    headers.join('\t'),
    ...rows.map(row =>
      headers.map(header => {
        return row[header] ? formatBindingValue(row[header]) : '';
      }).join('\t')
    ),
  ];

  return tsvRows.join('\n');
};

// SPARQL query formatting
export const formatSPARQL = (query: string): string => {
  // Basic formatting - could be enhanced with a proper SPARQL formatter
  return query
    .replace(/\s+/g, ' ')
    .replace(/\s*{\s*/g, ' {\n  ')
    .replace(/\s*}\s*/g, '\n}\n')
    .replace(/\s*\.\s*/g, ' .\n  ')
    .replace(/\s*;\s*/g, ' ;\n  ')
    .trim();
};

// Truncate text
export const truncate = (text: string, maxLength: number): string => {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength - 3) + '...';
};

// Highlight search terms
export const highlightText = (text: string, search: string): string => {
  if (!search) return text;
  const regex = new RegExp(`(${search})`, 'gi');
  return text.replace(regex, '<mark>$1</mark>');
};
