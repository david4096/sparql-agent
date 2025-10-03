import React, { useState } from 'react';
import {
  Drawer,
  Box,
  TextField,
  Typography,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Collapse,
  IconButton,
  InputAdornment,
  Chip,
  Divider,
  Tooltip,
  CircularProgress,
} from '@mui/material';
import {
  ExpandMore,
  ChevronRight,
  Search,
  Close,
  Info,
  Class as ClassIcon,
  Link as LinkIcon,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@services/api';
import { useChatStore } from '@store/chatStore';
import { useUIStore } from '@store/uiStore';
import type { OntologyTerm, OntologyNode } from '@types/index';
import { useDebounce } from '@hooks/useDebounce';

const OntologyBrowser: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());
  const [selectedTerm, setSelectedTerm] = useState<OntologyTerm | null>(null);

  const currentEndpoint = useChatStore(state => state.currentEndpoint);
  const ontologyBrowserOpen = useUIStore(state => state.ontologyBrowserOpen);
  const toggleOntologyBrowser = useUIStore(state => state.toggleOntologyBrowser);

  const debouncedSearch = useDebounce(searchQuery, 300);

  // Fetch ontology
  const { data: ontologyTerms = [], isLoading } = useQuery<OntologyTerm[]>({
    queryKey: ['ontology', currentEndpoint?.id],
    queryFn: () => apiClient.getOntology(currentEndpoint!.id),
    enabled: !!currentEndpoint && ontologyBrowserOpen,
    staleTime: 10 * 60 * 1000, // 10 minutes
  });

  // Search ontology
  const { data: searchResults = [] } = useQuery<OntologyTerm[]>({
    queryKey: ['ontology-search', debouncedSearch, currentEndpoint?.id],
    queryFn: () => apiClient.searchOntology(debouncedSearch, currentEndpoint!.id),
    enabled: !!currentEndpoint && debouncedSearch.length > 2,
  });

  const handleToggleNode = (nodeId: string) => {
    setExpandedNodes(prev => {
      const next = new Set(prev);
      if (next.has(nodeId)) {
        next.delete(nodeId);
      } else {
        next.add(nodeId);
      }
      return next;
    });
  };

  const handleTermClick = (term: OntologyTerm) => {
    setSelectedTerm(term);
  };

  const renderOntologyTree = (terms: OntologyTerm[], level = 0) => {
    // Group by parent class for tree structure
    const classes = terms.filter(t => t.type === 'class');
    const properties = terms.filter(t => t.type === 'property');

    return (
      <List dense disablePadding>
        {classes.map(term => {
          const isExpanded = expandedNodes.has(term.uri);
          return (
            <Box key={term.uri}>
              <ListItem disablePadding sx={{ pl: level * 2 }}>
                <ListItemButton onClick={() => handleTermClick(term)}>
                  <IconButton
                    size="small"
                    onClick={e => {
                      e.stopPropagation();
                      handleToggleNode(term.uri);
                    }}
                  >
                    {isExpanded ? <ExpandMore /> : <ChevronRight />}
                  </IconButton>
                  <ClassIcon fontSize="small" sx={{ mr: 1, color: 'primary.main' }} />
                  <ListItemText
                    primary={term.label}
                    secondary={term.description}
                    primaryTypographyProps={{ variant: 'body2' }}
                    secondaryTypographyProps={{ variant: 'caption', noWrap: true }}
                  />
                </ListItemButton>
              </ListItem>
              <Collapse in={isExpanded}>
                {/* Render child properties */}
                {properties
                  .filter(p => p.domain === term.uri)
                  .map(prop => (
                    <ListItem key={prop.uri} disablePadding sx={{ pl: (level + 1) * 2 }}>
                      <ListItemButton onClick={() => handleTermClick(prop)}>
                        <LinkIcon fontSize="small" sx={{ mr: 1, color: 'secondary.main' }} />
                        <ListItemText
                          primary={prop.label}
                          primaryTypographyProps={{ variant: 'body2' }}
                        />
                      </ListItemButton>
                    </ListItem>
                  ))}
              </Collapse>
            </Box>
          );
        })}
      </List>
    );
  };

  return (
    <Drawer
      anchor="right"
      open={ontologyBrowserOpen}
      onClose={toggleOntologyBrowser}
      sx={{
        '& .MuiDrawer-paper': {
          width: 400,
          maxWidth: '100%',
        },
      }}
    >
      <Box p={2}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h6">Ontology Browser</Typography>
          <IconButton onClick={toggleOntologyBrowser} size="small">
            <Close />
          </IconButton>
        </Box>

        {currentEndpoint && (
          <Chip label={currentEndpoint.name} size="small" sx={{ mb: 2 }} />
        )}

        <TextField
          fullWidth
          size="small"
          placeholder="Search ontology..."
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          sx={{ mb: 2 }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <Search />
              </InputAdornment>
            ),
          }}
        />

        <Divider sx={{ mb: 2 }} />

        {isLoading ? (
          <Box display="flex" justifyContent="center" py={4}>
            <CircularProgress />
          </Box>
        ) : !currentEndpoint ? (
          <Box textAlign="center" py={4}>
            <Typography color="text.secondary">
              Select an endpoint to browse its ontology
            </Typography>
          </Box>
        ) : searchQuery.length > 2 ? (
          <List>
            {searchResults.map(term => (
              <ListItem key={term.uri} disablePadding>
                <ListItemButton onClick={() => handleTermClick(term)}>
                  {term.type === 'class' ? (
                    <ClassIcon fontSize="small" sx={{ mr: 1, color: 'primary.main' }} />
                  ) : (
                    <LinkIcon fontSize="small" sx={{ mr: 1, color: 'secondary.main' }} />
                  )}
                  <ListItemText
                    primary={term.label}
                    secondary={term.description}
                    primaryTypographyProps={{ variant: 'body2' }}
                    secondaryTypographyProps={{ variant: 'caption', noWrap: true }}
                  />
                </ListItemButton>
              </ListItem>
            ))}
          </List>
        ) : (
          renderOntologyTree(ontologyTerms)
        )}
      </Box>

      {/* Term Details Panel */}
      {selectedTerm && (
        <Box
          sx={{
            position: 'absolute',
            bottom: 0,
            left: 0,
            right: 0,
            bgcolor: 'background.paper',
            borderTop: 1,
            borderColor: 'divider',
            p: 2,
            maxHeight: '40%',
            overflow: 'auto',
          }}
        >
          <Box display="flex" justifyContent="space-between" alignItems="start" mb={1}>
            <Typography variant="subtitle2">{selectedTerm.label}</Typography>
            <IconButton size="small" onClick={() => setSelectedTerm(null)}>
              <Close fontSize="small" />
            </IconButton>
          </Box>

          <Chip
            label={selectedTerm.type}
            size="small"
            color={selectedTerm.type === 'class' ? 'primary' : 'secondary'}
            sx={{ mb: 1 }}
          />

          {selectedTerm.description && (
            <Typography variant="body2" color="text.secondary" paragraph>
              {selectedTerm.description}
            </Typography>
          )}

          <Typography variant="caption" color="text.secondary" sx={{ wordBreak: 'break-all' }}>
            URI: {selectedTerm.uri}
          </Typography>

          {selectedTerm.domain && (
            <Typography variant="caption" color="text.secondary" display="block">
              Domain: {selectedTerm.domain}
            </Typography>
          )}

          {selectedTerm.range && (
            <Typography variant="caption" color="text.secondary" display="block">
              Range: {selectedTerm.range}
            </Typography>
          )}
        </Box>
      )}
    </Drawer>
  );
};

export default OntologyBrowser;
