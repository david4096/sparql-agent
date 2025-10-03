import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  IconButton,
  Collapse,
  Chip,
  Stack,
  Tooltip,
} from '@mui/material';
import {
  ContentCopy,
  ExpandMore,
  ExpandLess,
  Person,
  SmartToy,
  CheckCircle,
  Error as ErrorIcon,
} from '@mui/icons-material';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { tomorrow } from 'react-syntax-highlighter/dist/esm/styles/prism';
import type { Message } from '@types/index';
import { formatRelativeTime } from '@utils/formatters';
import { copyToClipboard } from '@utils/export';
import ResultsDisplay from '../results/ResultsDisplay';
import toast from 'react-hot-toast';

interface MessageBubbleProps {
  message: Message;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const [showQuery, setShowQuery] = useState(false);
  const [showResults, setShowResults] = useState(true);

  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';

  const handleCopy = async (text: string) => {
    const success = await copyToClipboard(text);
    if (success) {
      toast.success('Copied to clipboard');
    } else {
      toast.error('Failed to copy');
    }
  };

  if (isSystem) {
    return (
      <Box display="flex" justifyContent="center" my={2}>
        <Chip
          label={message.content}
          size="small"
          sx={{ bgcolor: 'action.hover' }}
        />
      </Box>
    );
  }

  return (
    <Box
      display="flex"
      justifyContent={isUser ? 'flex-end' : 'flex-start'}
      gap={1}
    >
      {!isUser && (
        <Box
          sx={{
            width: 40,
            height: 40,
            borderRadius: '50%',
            bgcolor: 'primary.main',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          <SmartToy sx={{ color: 'white', fontSize: 24 }} />
        </Box>
      )}

      <Paper
        elevation={1}
        sx={{
          maxWidth: '75%',
          p: 2,
          bgcolor: isUser ? 'primary.light' : 'background.paper',
          color: isUser ? 'primary.contrastText' : 'text.primary',
        }}
      >
        <Stack spacing={1.5}>
          {/* Message Content */}
          <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
            {message.content}
          </Typography>

          {/* Query Section */}
          {message.query && (
            <Box>
              <Box display="flex" alignItems="center" gap={1} mb={1}>
                <Chip
                  label={message.query.status}
                  size="small"
                  color={
                    message.query.status === 'success'
                      ? 'success'
                      : message.query.status === 'error'
                      ? 'error'
                      : 'default'
                  }
                  icon={
                    message.query.status === 'success' ? (
                      <CheckCircle />
                    ) : message.query.status === 'error' ? (
                      <ErrorIcon />
                    ) : undefined
                  }
                />
                {message.query.duration && (
                  <Typography variant="caption" color="text.secondary">
                    {message.query.duration}ms
                  </Typography>
                )}
                <IconButton
                  size="small"
                  onClick={() => setShowQuery(!showQuery)}
                  sx={{ ml: 'auto' }}
                >
                  {showQuery ? <ExpandLess /> : <ExpandMore />}
                </IconButton>
              </Box>

              <Collapse in={showQuery}>
                <Box position="relative">
                  <Tooltip title="Copy query">
                    <IconButton
                      size="small"
                      onClick={() => handleCopy(message.query!.query)}
                      sx={{
                        position: 'absolute',
                        right: 8,
                        top: 8,
                        zIndex: 1,
                        bgcolor: 'background.paper',
                      }}
                    >
                      <ContentCopy fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  <SyntaxHighlighter
                    language="sparql"
                    style={tomorrow}
                    customStyle={{
                      margin: 0,
                      borderRadius: 4,
                      fontSize: '0.875rem',
                    }}
                  >
                    {message.query.query}
                  </SyntaxHighlighter>
                </Box>
              </Collapse>

              {message.query.explanation && (
                <Typography variant="caption" color="text.secondary" mt={1}>
                  {message.query.explanation}
                </Typography>
              )}
            </Box>
          )}

          {/* Results Section */}
          {message.results && (
            <Box>
              <Box display="flex" alignItems="center" gap={1} mb={1}>
                <Typography variant="subtitle2">
                  Results ({message.results.results.bindings.length} rows)
                </Typography>
                <IconButton
                  size="small"
                  onClick={() => setShowResults(!showResults)}
                  sx={{ ml: 'auto' }}
                >
                  {showResults ? <ExpandLess /> : <ExpandMore />}
                </IconButton>
              </Box>

              <Collapse in={showResults}>
                <ResultsDisplay results={message.results} />
              </Collapse>
            </Box>
          )}

          {/* Error Section */}
          {message.error && (
            <Paper
              sx={{
                p: 1.5,
                bgcolor: 'error.light',
                color: 'error.contrastText',
              }}
            >
              <Typography variant="body2">{message.error}</Typography>
            </Paper>
          )}

          {/* Timestamp */}
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
            {formatRelativeTime(message.timestamp)}
          </Typography>
        </Stack>
      </Paper>

      {isUser && (
        <Box
          sx={{
            width: 40,
            height: 40,
            borderRadius: '50%',
            bgcolor: 'secondary.main',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          <Person sx={{ color: 'white', fontSize: 24 }} />
        </Box>
      )}
    </Box>
  );
};

export default MessageBubble;
