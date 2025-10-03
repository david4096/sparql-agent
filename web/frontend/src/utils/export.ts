import { saveAs } from 'file-saver';
import type { QueryResults, ExportFormat } from '@types/index';
import { resultsToCSV, resultsToJSON, resultsToTSV } from './formatters';

export const exportResults = (results: QueryResults, format: ExportFormat): void => {
  let content: string;
  let mimeType: string;

  switch (format.format) {
    case 'csv':
      content = resultsToCSV(results);
      mimeType = 'text/csv;charset=utf-8';
      break;

    case 'json':
      content = resultsToJSON(results);
      mimeType = 'application/json;charset=utf-8';
      break;

    case 'tsv':
      content = resultsToTSV(results);
      mimeType = 'text/tab-separated-values;charset=utf-8';
      break;

    case 'turtle':
      content = convertToTurtle(results);
      mimeType = 'text/turtle;charset=utf-8';
      break;

    case 'rdf-xml':
      content = convertToRDFXML(results);
      mimeType = 'application/rdf+xml;charset=utf-8';
      break;

    case 'n-triples':
      content = convertToNTriples(results);
      mimeType = 'application/n-triples;charset=utf-8';
      break;

    default:
      throw new Error(`Unsupported export format: ${format.format}`);
  }

  const blob = new Blob([content], { type: mimeType });
  saveAs(blob, format.filename);
};

// Convert SPARQL results to Turtle format
const convertToTurtle = (results: QueryResults): string => {
  const lines: string[] = ['@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .', ''];

  results.results.bindings.forEach(binding => {
    const vars = results.head.vars;
    if (vars.length >= 3) {
      const subject = formatTurtleValue(binding[vars[0]]);
      const predicate = formatTurtleValue(binding[vars[1]]);
      const object = formatTurtleValue(binding[vars[2]]);
      lines.push(`${subject} ${predicate} ${object} .`);
    }
  });

  return lines.join('\n');
};

// Convert SPARQL results to RDF/XML format
const convertToRDFXML = (results: QueryResults): string => {
  const lines: string[] = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">',
  ];

  results.results.bindings.forEach(binding => {
    const vars = results.head.vars;
    if (vars.length >= 3) {
      const subject = binding[vars[0]];
      const predicate = binding[vars[1]];
      const object = binding[vars[2]];

      lines.push(`  <rdf:Description rdf:about="${subject?.value || ''}">`);
      if (predicate && object) {
        const tag = formatXMLTag(predicate.value);
        if (object.type === 'uri') {
          lines.push(`    <${tag} rdf:resource="${object.value}"/>`);
        } else {
          const attrs = [];
          if (object.datatype) attrs.push(`rdf:datatype="${object.datatype}"`);
          if (object['xml:lang']) attrs.push(`xml:lang="${object['xml:lang']}"`);
          lines.push(`    <${tag}${attrs.length ? ' ' + attrs.join(' ') : ''}>${escapeXML(object.value)}</${tag}>`);
        }
      }
      lines.push('  </rdf:Description>');
    }
  });

  lines.push('</rdf:RDF>');
  return lines.join('\n');
};

// Convert SPARQL results to N-Triples format
const convertToNTriples = (results: QueryResults): string => {
  const lines: string[] = [];

  results.results.bindings.forEach(binding => {
    const vars = results.head.vars;
    if (vars.length >= 3) {
      const subject = formatNTriplesValue(binding[vars[0]]);
      const predicate = formatNTriplesValue(binding[vars[1]]);
      const object = formatNTriplesValue(binding[vars[2]]);
      lines.push(`${subject} ${predicate} ${object} .`);
    }
  });

  return lines.join('\n');
};

// Helper functions
const formatTurtleValue = (binding: any): string => {
  if (!binding) return '""';

  switch (binding.type) {
    case 'uri':
      return `<${binding.value}>`;
    case 'literal':
      const value = `"${binding.value.replace(/"/g, '\\"')}"`;
      if (binding['xml:lang']) return `${value}@${binding['xml:lang']}`;
      if (binding.datatype) return `${value}^^<${binding.datatype}>`;
      return value;
    case 'bnode':
      return `_:${binding.value}`;
    default:
      return `"${binding.value}"`;
  }
};

const formatNTriplesValue = (binding: any): string => {
  if (!binding) return '""';

  switch (binding.type) {
    case 'uri':
      return `<${binding.value}>`;
    case 'literal':
      const value = `"${binding.value.replace(/\\/g, '\\\\').replace(/"/g, '\\"').replace(/\n/g, '\\n')}"`;
      if (binding['xml:lang']) return `${value}@${binding['xml:lang']}`;
      if (binding.datatype) return `${value}^^<${binding.datatype}>`;
      return value;
    case 'bnode':
      return `_:${binding.value}`;
    default:
      return `"${binding.value}"`;
  }
};

const formatXMLTag = (uri: string): string => {
  const parts = uri.split(/[/#]/);
  return parts[parts.length - 1] || 'property';
};

const escapeXML = (text: string): string => {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
};

// Export query text
export const exportQuery = (query: string, filename: string): void => {
  const blob = new Blob([query], { type: 'text/plain;charset=utf-8' });
  saveAs(blob, filename);
};

// Copy to clipboard
export const copyToClipboard = async (text: string): Promise<boolean> => {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (error) {
    console.error('Failed to copy to clipboard:', error);
    return false;
  }
};
