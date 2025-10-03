import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  TextField,
  IconButton,
  Paper,
  List,
  ListItem,
  ListItemText,
  Popper,
  ClickAwayListener,
  Chip,
  Stack,
} from '@mui/material';
import { Send, AutoAwesome, History } from '@mui/icons-material';
import { useChatStore } from '@store/chatStore';
import { useUIStore } from '@store/uiStore';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@services/api';
import { useDebounce } from '@hooks/useDebounce';
import type { QuerySuggestion } from '@types/index';
import toast from 'react-hot-toast';

const QueryInput: React.FC = () => {
  const [input, setInput] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const anchorRef = useRef<HTMLDivElement>(null);

  const currentSession = useChatStore(state => state.getCurrentSession());
  const addMessage = useChatStore(state => state.addMessage);
  const updateMessage = useChatStore(state => state.updateMessage);
  const setIsTyping = useChatStore(state => state.setIsTyping);
  const autoExecuteQueries = useUIStore(state => state.autoExecuteQueries);

  const debouncedInput = useDebounce(input, 300);

  // Fetch suggestions
  const { data: suggestions = [] } = useQuery<QuerySuggestion[]>({
    queryKey: ['suggestions', debouncedInput, currentSession?.endpoint.id],
    queryFn: () =>
      apiClient.getSuggestions(
        debouncedInput,
        currentSession!.endpoint.id,
        inputRef.current?.selectionStart || 0
      ),
    enabled: !!currentSession && debouncedInput.length > 2,
  });

  useEffect(() => {
    setShowSuggestions(suggestions.length > 0 && document.activeElement === inputRef.current);
  }, [suggestions]);

  const handleSubmit = async () => {
    if (!input.trim() || !currentSession) return;

    const userMessage = input.trim();
    setInput('');
    setShowSuggestions(false);

    // Add user message
    addMessage(currentSession.id, {
      role: 'user',
      content: userMessage,
    });

    try {
      setIsTyping(true);

      // Translate natural language to SPARQL
      const query = await apiClient.translateToSPARQL(
        userMessage,
        currentSession.endpoint.id
      );

      // Add assistant message with query
      const messageId = Math.random().toString(36);
      addMessage(currentSession.id, {
        role: 'assistant',
        content: 'I generated this SPARQL query for you:',
        query: {
          ...query,
          status: 'pending',
        },
      });

      // Execute query if auto-execute is enabled
      if (autoExecuteQueries) {
        try {
          const results = await apiClient.executeQuery(
            query.query,
            currentSession.endpoint.url
          );

          updateMessage(currentSession.id, messageId, {
            query: {
              ...query,
              status: 'success',
            },
            results,
          });
        } catch (error: any) {
          updateMessage(currentSession.id, messageId, {
            query: {
              ...query,
              status: 'error',
            },
            error: error.message || 'Failed to execute query',
          });
        }
      }
    } catch (error: any) {
      addMessage(currentSession.id, {
        role: 'assistant',
        content: 'Sorry, I encountered an error generating the query.',
        error: error.message || 'Unknown error',
      });
      toast.error('Failed to generate query');
    } finally {
      setIsTyping(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (showSuggestions && suggestions[selectedIndex]) {
        applySuggestion(suggestions[selectedIndex]);
      } else {
        handleSubmit();
      }
    } else if (e.key === 'ArrowUp' && showSuggestions) {
      e.preventDefault();
      setSelectedIndex(prev => Math.max(0, prev - 1));
    } else if (e.key === 'ArrowDown' && showSuggestions) {
      e.preventDefault();
      setSelectedIndex(prev => Math.min(suggestions.length - 1, prev + 1));
    } else if (e.key === 'Escape' && showSuggestions) {
      setShowSuggestions(false);
    }
  };

  const applySuggestion = (suggestion: QuerySuggestion) => {
    if (suggestion.type === 'template') {
      setInput(suggestion.sparqlTemplate || suggestion.text);
    } else {
      const cursorPos = inputRef.current?.selectionStart || input.length;
      const before = input.slice(0, cursorPos);
      const after = input.slice(cursorPos);
      const lastWord = before.split(/\s/).pop() || '';
      const newInput = before.slice(0, -lastWord.length) + suggestion.text + after;
      setInput(newInput);
    }
    setShowSuggestions(false);
    inputRef.current?.focus();
  };

  return (
    <Box ref={anchorRef} p={2}>
      <Stack direction="row" spacing={1} alignItems="flex-end">
        <TextField
          inputRef={inputRef}
          fullWidth
          multiline
          maxRows={4}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question about the data..."
          variant="outlined"
          disabled={!currentSession}
          sx={{
            '& .MuiOutlinedInput-root': {
              borderRadius: 2,
            },
          }}
          InputProps={{
            startAdornment: currentSession?.endpoint && (
              <Chip
                label={currentSession.endpoint.name}
                size="small"
                sx={{ mr: 1 }}
              />
            ),
          }}
        />

        <IconButton
          color="primary"
          onClick={handleSubmit}
          disabled={!input.trim() || !currentSession}
          sx={{
            bgcolor: 'primary.main',
            color: 'white',
            '&:hover': {
              bgcolor: 'primary.dark',
            },
            '&:disabled': {
              bgcolor: 'action.disabledBackground',
            },
          }}
        >
          <Send />
        </IconButton>
      </Stack>

      {/* Suggestions Popper */}
      <Popper
        open={showSuggestions}
        anchorEl={anchorRef.current}
        placement="top-start"
        sx={{ zIndex: 1300, width: anchorRef.current?.offsetWidth }}
      >
        <ClickAwayListener onClickAway={() => setShowSuggestions(false)}>
          <Paper elevation={8} sx={{ maxHeight: 300, overflow: 'auto' }}>
            <List dense>
              {suggestions.map((suggestion, index) => (
                <ListItem
                  key={suggestion.id}
                  button
                  selected={index === selectedIndex}
                  onClick={() => applySuggestion(suggestion)}
                  sx={{
                    '&.Mui-selected': {
                      bgcolor: 'action.selected',
                    },
                  }}
                >
                  <Box mr={1}>
                    {suggestion.type === 'template' ? (
                      <AutoAwesome fontSize="small" />
                    ) : (
                      <History fontSize="small" />
                    )}
                  </Box>
                  <ListItemText
                    primary={suggestion.text}
                    secondary={
                      suggestion.type === 'term'
                        ? suggestion.ontologyTerm?.description
                        : null
                    }
                  />
                </ListItem>
              ))}
            </List>
          </Paper>
        </ClickAwayListener>
      </Popper>
    </Box>
  );
};

export default QueryInput;
