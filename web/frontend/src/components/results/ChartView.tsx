import React, { useState, useMemo } from 'react';
import {
  Box,
  Paper,
  Typography,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Stack,
} from '@mui/material';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import type { QueryResults } from '@types/index';
import { formatBindingValue } from '@utils/formatters';

interface ChartViewProps {
  results: QueryResults;
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82ca9d'];

const ChartView: React.FC<ChartViewProps> = ({ results }) => {
  const vars = results.head.vars;
  const [chartType, setChartType] = useState<'bar' | 'line' | 'pie'>('bar');
  const [xAxis, setXAxis] = useState(vars[0] || '');
  const [yAxis, setYAxis] = useState(vars[1] || '');

  const chartData = useMemo(() => {
    if (!xAxis || !yAxis) return [];

    return results.results.bindings.map(binding => {
      const xValue = binding[xAxis] ? formatBindingValue(binding[xAxis]) : '';
      const yValue = binding[yAxis] ? binding[yAxis].value : '0';

      // Try to parse as number
      const numericY = parseFloat(yValue);

      return {
        name: xValue,
        value: isNaN(numericY) ? 0 : numericY,
        label: xValue,
      };
    });
  }, [results, xAxis, yAxis]);

  if (vars.length < 2) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <Typography color="text.secondary">
          Chart view requires at least 2 variables in the result set.
        </Typography>
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 2 }}>
      <Stack spacing={2}>
        {/* Chart Controls */}
        <Box display="flex" gap={2}>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Chart Type</InputLabel>
            <Select
              value={chartType}
              label="Chart Type"
              onChange={e => setChartType(e.target.value as any)}
            >
              <MenuItem value="bar">Bar Chart</MenuItem>
              <MenuItem value="line">Line Chart</MenuItem>
              <MenuItem value="pie">Pie Chart</MenuItem>
            </Select>
          </FormControl>

          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>X-Axis</InputLabel>
            <Select value={xAxis} label="X-Axis" onChange={e => setXAxis(e.target.value)}>
              {vars.map(v => (
                <MenuItem key={v} value={v}>
                  {v}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Y-Axis</InputLabel>
            <Select value={yAxis} label="Y-Axis" onChange={e => setYAxis(e.target.value)}>
              {vars.map(v => (
                <MenuItem key={v} value={v}>
                  {v}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>

        {/* Chart Display */}
        <Box sx={{ width: '100%', height: 400 }}>
          <ResponsiveContainer>
            {chartType === 'bar' && (
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="value" fill="#1976d2" />
              </BarChart>
            )}

            {chartType === 'line' && (
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="value" stroke="#1976d2" />
              </LineChart>
            )}

            {chartType === 'pie' && (
              <PieChart>
                <Pie
                  data={chartData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={entry => entry.name}
                  outerRadius={120}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {chartData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            )}
          </ResponsiveContainer>
        </Box>

        <Typography variant="caption" color="text.secondary">
          Showing {chartData.length} data points
        </Typography>
      </Stack>
    </Paper>
  );
};

export default ChartView;
