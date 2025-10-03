import React, { useState } from 'react';
import {
  Box,
  ToggleButtonGroup,
  ToggleButton,
  IconButton,
  Menu,
  MenuItem,
  Tooltip,
} from '@mui/material';
import {
  TableChart,
  AccountTree,
  BarChart,
  Code,
  Download,
} from '@mui/icons-material';
import type { QueryResults, ExportFormat } from '@types/index';
import { exportResults } from '@utils/export';
import TableView from './TableView';
import GraphView from './GraphView';
import ChartView from './ChartView';
import JSONView from './JSONView';
import toast from 'react-hot-toast';

interface ResultsDisplayProps {
  results: QueryResults;
}

const ResultsDisplay: React.FC<ResultsDisplayProps> = ({ results }) => {
  const [viewMode, setViewMode] = useState<'table' | 'graph' | 'chart' | 'json'>('table');
  const [exportAnchor, setExportAnchor] = useState<null | HTMLElement>(null);

  const handleExport = (format: ExportFormat['format']) => {
    try {
      const filename = `results_${Date.now()}.${format}`;
      exportResults(results, { format, filename });
      toast.success(`Exported as ${format.toUpperCase()}`);
    } catch (error: any) {
      toast.error(`Export failed: ${error.message}`);
    }
    setExportAnchor(null);
  };

  return (
    <Box>
      {/* Toolbar */}
      <Box
        display="flex"
        justifyContent="space-between"
        alignItems="center"
        mb={2}
        pb={1}
        borderBottom={1}
        borderColor="divider"
      >
        <ToggleButtonGroup
          size="small"
          value={viewMode}
          exclusive
          onChange={(_, value) => value && setViewMode(value)}
        >
          <ToggleButton value="table">
            <Tooltip title="Table View">
              <TableChart fontSize="small" />
            </Tooltip>
          </ToggleButton>
          <ToggleButton value="graph">
            <Tooltip title="Graph View">
              <AccountTree fontSize="small" />
            </Tooltip>
          </ToggleButton>
          <ToggleButton value="chart">
            <Tooltip title="Chart View">
              <BarChart fontSize="small" />
            </Tooltip>
          </ToggleButton>
          <ToggleButton value="json">
            <Tooltip title="JSON View">
              <Code fontSize="small" />
            </Tooltip>
          </ToggleButton>
        </ToggleButtonGroup>

        <Tooltip title="Export Results">
          <IconButton
            size="small"
            onClick={e => setExportAnchor(e.currentTarget)}
          >
            <Download />
          </IconButton>
        </Tooltip>

        <Menu
          anchorEl={exportAnchor}
          open={Boolean(exportAnchor)}
          onClose={() => setExportAnchor(null)}
        >
          <MenuItem onClick={() => handleExport('csv')}>Export as CSV</MenuItem>
          <MenuItem onClick={() => handleExport('json')}>Export as JSON</MenuItem>
          <MenuItem onClick={() => handleExport('tsv')}>Export as TSV</MenuItem>
          <MenuItem onClick={() => handleExport('turtle')}>Export as Turtle</MenuItem>
          <MenuItem onClick={() => handleExport('rdf-xml')}>Export as RDF/XML</MenuItem>
          <MenuItem onClick={() => handleExport('n-triples')}>Export as N-Triples</MenuItem>
        </Menu>
      </Box>

      {/* View Content */}
      <Box>
        {viewMode === 'table' && <TableView results={results} />}
        {viewMode === 'graph' && <GraphView results={results} />}
        {viewMode === 'chart' && <ChartView results={results} />}
        {viewMode === 'json' && <JSONView results={results} />}
      </Box>
    </Box>
  );
};

export default ResultsDisplay;
