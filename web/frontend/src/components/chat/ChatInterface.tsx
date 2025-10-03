import React, { useRef, useEffect } from 'react';
import { Box, Paper, CircularProgress, Typography } from '@mui/material';
import { useChatStore } from '@store/chatStore';
import MessageBubble from './MessageBubble';
import QueryInput from './QueryInput';

const ChatInterface: React.FC = () => {
  const currentSession = useChatStore(state => state.getCurrentSession());
  const isTyping = useChatStore(state => state.isTyping);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [currentSession?.messages]);

  if (!currentSession) {
    return (
      <Box
        display="flex"
        alignItems="center"
        justifyContent="center"
        height="100%"
        p={4}
      >
        <Typography variant="h6" color="text.secondary">
          Select or create a session to start chatting
        </Typography>
      </Box>
    );
  }

  return (
    <Box
      display="flex"
      flexDirection="column"
      height="100%"
      sx={{ bgcolor: 'background.default' }}
    >
      {/* Messages Area */}
      <Box
        flex={1}
        overflow="auto"
        p={2}
        sx={{
          '&::-webkit-scrollbar': {
            width: '8px',
          },
          '&::-webkit-scrollbar-track': {
            background: 'transparent',
          },
          '&::-webkit-scrollbar-thumb': {
            background: 'rgba(0,0,0,0.2)',
            borderRadius: '4px',
          },
          '&::-webkit-scrollbar-thumb:hover': {
            background: 'rgba(0,0,0,0.3)',
          },
        }}
      >
        {currentSession.messages.length === 0 ? (
          <Box
            display="flex"
            flexDirection="column"
            alignItems="center"
            justifyContent="center"
            height="100%"
            gap={2}
          >
            <Typography variant="h5" color="text.secondary">
              Start a conversation
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Ask a question about {currentSession.endpoint.name}
            </Typography>
          </Box>
        ) : (
          <Box display="flex" flexDirection="column" gap={2}>
            {currentSession.messages.map(message => (
              <MessageBubble key={message.id} message={message} />
            ))}
            {isTyping && (
              <Box display="flex" gap={1} alignItems="center" pl={2}>
                <CircularProgress size={16} />
                <Typography variant="body2" color="text.secondary">
                  AI is thinking...
                </Typography>
              </Box>
            )}
            <div ref={messagesEndRef} />
          </Box>
        )}
      </Box>

      {/* Input Area */}
      <Paper
        elevation={3}
        sx={{
          borderRadius: 0,
          borderTop: 1,
          borderColor: 'divider',
        }}
      >
        <QueryInput />
      </Paper>
    </Box>
  );
};

export default ChatInterface;
