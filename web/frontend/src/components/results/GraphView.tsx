import React, { useMemo } from 'react';
import { Box, Typography, Paper } from '@mui/material';
import type { QueryResults } from '@types/index';
import { formatBindingValue } from '@utils/formatters';

interface GraphViewProps {
  results: QueryResults;
}

interface Node {
  id: string;
  label: string;
  type: 'uri' | 'literal' | 'bnode';
}

interface Edge {
  source: string;
  target: string;
  label: string;
}

const GraphView: React.FC<GraphViewProps> = ({ results }) => {
  const { nodes, edges } = useMemo(() => {
    const nodeMap = new Map<string, Node>();
    const edgeList: Edge[] = [];

    const vars = results.head.vars;
    const bindings = results.results.bindings;

    // Assume triple pattern: subject, predicate, object
    if (vars.length >= 3) {
      bindings.forEach(binding => {
        const subject = binding[vars[0]];
        const predicate = binding[vars[1]];
        const object = binding[vars[2]];

        if (subject) {
          const subjectId = subject.value;
          if (!nodeMap.has(subjectId)) {
            nodeMap.set(subjectId, {
              id: subjectId,
              label: formatBindingValue(subject),
              type: subject.type,
            });
          }
        }

        if (object) {
          const objectId = object.value;
          if (!nodeMap.has(objectId)) {
            nodeMap.set(objectId, {
              id: objectId,
              label: formatBindingValue(object),
              type: object.type,
            });
          }
        }

        if (subject && predicate && object) {
          edgeList.push({
            source: subject.value,
            target: object.value,
            label: formatBindingValue(predicate),
          });
        }
      });
    }

    return {
      nodes: Array.from(nodeMap.values()),
      edges: edgeList,
    };
  }, [results]);

  // Simple SVG-based graph visualization
  const svgWidth = 800;
  const svgHeight = 600;
  const nodeRadius = 30;

  // Simple force-directed layout (circular for now)
  const layoutNodes = useMemo(() => {
    const centerX = svgWidth / 2;
    const centerY = svgHeight / 2;
    const radius = Math.min(svgWidth, svgHeight) / 3;

    return nodes.map((node, index) => {
      const angle = (2 * Math.PI * index) / nodes.length;
      return {
        ...node,
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle),
      };
    });
  }, [nodes]);

  if (nodes.length === 0) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <Typography color="text.secondary">
          No graph data to display. Graph view requires subject-predicate-object patterns.
        </Typography>
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 2, overflow: 'auto' }}>
      <svg width={svgWidth} height={svgHeight}>
        {/* Draw edges */}
        {edges.map((edge, index) => {
          const sourceNode = layoutNodes.find(n => n.id === edge.source);
          const targetNode = layoutNodes.find(n => n.id === edge.target);

          if (!sourceNode || !targetNode) return null;

          return (
            <g key={`edge-${index}`}>
              <line
                x1={sourceNode.x}
                y1={sourceNode.y}
                x2={targetNode.x}
                y2={targetNode.y}
                stroke="#999"
                strokeWidth={2}
                markerEnd="url(#arrowhead)"
              />
              <text
                x={(sourceNode.x + targetNode.x) / 2}
                y={(sourceNode.y + targetNode.y) / 2}
                fontSize="10"
                fill="#666"
                textAnchor="middle"
              >
                {edge.label}
              </text>
            </g>
          );
        })}

        {/* Draw nodes */}
        {layoutNodes.map((node, index) => (
          <g key={`node-${index}`}>
            <circle
              cx={node.x}
              cy={node.y}
              r={nodeRadius}
              fill={node.type === 'uri' ? '#1976d2' : node.type === 'literal' ? '#2e7d32' : '#9c27b0'}
              stroke="#fff"
              strokeWidth={2}
            />
            <text
              x={node.x}
              y={node.y + nodeRadius + 15}
              fontSize="12"
              fill="#000"
              textAnchor="middle"
              style={{ maxWidth: '100px' }}
            >
              {node.label.length > 20 ? node.label.slice(0, 20) + '...' : node.label}
            </text>
          </g>
        ))}

        {/* Arrow marker */}
        <defs>
          <marker
            id="arrowhead"
            markerWidth="10"
            markerHeight="10"
            refX="9"
            refY="3"
            orient="auto"
          >
            <polygon points="0 0, 10 3, 0 6" fill="#999" />
          </marker>
        </defs>
      </svg>

      <Box mt={2}>
        <Typography variant="caption" color="text.secondary">
          Nodes: {nodes.length} | Edges: {edges.length}
        </Typography>
      </Box>
    </Paper>
  );
};

export default GraphView;
