import React, { useState, useMemo } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  TableSortLabel,
  Paper,
  Link,
  Chip,
  Box,
} from '@mui/material';
import type { QueryResults } from '@types/index';
import { formatBindingValue } from '@utils/formatters';

interface TableViewProps {
  results: QueryResults;
}

type Order = 'asc' | 'desc';

const TableView: React.FC<TableViewProps> = ({ results }) => {
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(50);
  const [orderBy, setOrderBy] = useState<string>('');
  const [order, setOrder] = useState<Order>('asc');

  const vars = results.head.vars;
  const bindings = results.results.bindings;

  const sortedBindings = useMemo(() => {
    if (!orderBy) return bindings;

    return [...bindings].sort((a, b) => {
      const aVal = a[orderBy]?.value || '';
      const bVal = b[orderBy]?.value || '';

      if (order === 'asc') {
        return aVal.localeCompare(bVal);
      } else {
        return bVal.localeCompare(aVal);
      }
    });
  }, [bindings, orderBy, order]);

  const paginatedBindings = useMemo(() => {
    const start = page * rowsPerPage;
    return sortedBindings.slice(start, start + rowsPerPage);
  }, [sortedBindings, page, rowsPerPage]);

  const handleSort = (variable: string) => {
    const isAsc = orderBy === variable && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(variable);
  };

  const renderCell = (binding: any) => {
    if (!binding) return <TableCell>-</TableCell>;

    const value = formatBindingValue(binding);

    if (binding.type === 'uri') {
      return (
        <TableCell>
          <Link
            href={binding.value}
            target="_blank"
            rel="noopener noreferrer"
            sx={{ wordBreak: 'break-word' }}
          >
            {value}
          </Link>
        </TableCell>
      );
    }

    if (binding.type === 'bnode') {
      return (
        <TableCell>
          <Chip label={value} size="small" variant="outlined" />
        </TableCell>
      );
    }

    return (
      <TableCell sx={{ wordBreak: 'break-word' }}>
        {value}
      </TableCell>
    );
  };

  return (
    <Box>
      <TableContainer component={Paper} variant="outlined">
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              {vars.map(variable => (
                <TableCell key={variable}>
                  <TableSortLabel
                    active={orderBy === variable}
                    direction={orderBy === variable ? order : 'asc'}
                    onClick={() => handleSort(variable)}
                  >
                    <strong>?{variable}</strong>
                  </TableSortLabel>
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {paginatedBindings.map((binding, index) => (
              <TableRow
                key={index}
                hover
                sx={{ '&:nth-of-type(odd)': { bgcolor: 'action.hover' } }}
              >
                {vars.map(variable => (
                  <React.Fragment key={variable}>
                    {renderCell(binding[variable])}
                  </React.Fragment>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <TablePagination
        component="div"
        count={bindings.length}
        page={page}
        onPageChange={(_, newPage) => setPage(newPage)}
        rowsPerPage={rowsPerPage}
        onRowsPerPageChange={e => {
          setRowsPerPage(parseInt(e.target.value, 10));
          setPage(0);
        }}
        rowsPerPageOptions={[10, 25, 50, 100, 250]}
      />
    </Box>
  );
};

export default TableView;
