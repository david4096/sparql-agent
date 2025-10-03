import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  ListItemIcon,
  TextField,
  Box,
  Chip,
  Typography,
  CircularProgress,
  IconButton,
  InputAdornment,
} from '@mui/material';
import { Storage, Search, CheckCircle, Close } from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@services/api';
import { useChatStore } from '@store/chatStore';
import type { SPARQLEndpoint } from '@types/index';
import toast from 'react-hot-toast';

interface EndpointSelectorProps {
  open: boolean;
  onClose: () => void;
  onSelect: (endpoint: SPARQLEndpoint) => void;
}

const EndpointSelector: React.FC<EndpointSelectorProps> = ({ open, onClose, onSelect }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const currentEndpoint = useChatStore(state => state.currentEndpoint);

  const { data: endpoints = [], isLoading } = useQuery<SPARQLEndpoint[]>({
    queryKey: ['endpoints'],
    queryFn: () => apiClient.getEndpoints(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  const filteredEndpoints = endpoints.filter(
    endpoint =>
      endpoint.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      endpoint.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      endpoint.category?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleSelect = (endpoint: SPARQLEndpoint) => {
    onSelect(endpoint);
    onClose();
    toast.success(`Selected ${endpoint.name}`);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h6">Select SPARQL Endpoint</Typography>
          <IconButton onClick={onClose} size="small">
            <Close />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent>
        <Box mb={2}>
          <TextField
            fullWidth
            size="small"
            placeholder="Search endpoints..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Search />
                </InputAdornment>
              ),
            }}
          />
        </Box>

        {isLoading ? (
          <Box display="flex" justifyContent="center" py={4}>
            <CircularProgress />
          </Box>
        ) : (
          <List>
            {filteredEndpoints.map(endpoint => (
              <ListItem key={endpoint.id} disablePadding>
                <ListItemButton
                  onClick={() => handleSelect(endpoint)}
                  selected={currentEndpoint?.id === endpoint.id}
                >
                  <ListItemIcon>
                    {currentEndpoint?.id === endpoint.id ? (
                      <CheckCircle color="primary" />
                    ) : (
                      <Storage />
                    )}
                  </ListItemIcon>
                  <ListItemText
                    primary={
                      <Box display="flex" alignItems="center" gap={1}>
                        <Typography variant="subtitle1">{endpoint.name}</Typography>
                        {endpoint.category && (
                          <Chip label={endpoint.category} size="small" />
                        )}
                      </Box>
                    }
                    secondary={
                      <Box>
                        <Typography variant="body2" color="text.secondary">
                          {endpoint.description}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {endpoint.url}
                        </Typography>
                      </Box>
                    }
                  />
                </ListItemButton>
              </ListItem>
            ))}

            {filteredEndpoints.length === 0 && (
              <Box textAlign="center" py={4}>
                <Typography color="text.secondary">
                  No endpoints found matching your search
                </Typography>
              </Box>
            )}
          </List>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default EndpointSelector;
