import React, { useEffect } from 'react';
import { Box } from '@mui/material';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { Toaster } from 'react-hot-toast';
import ThemeProvider from './components/common/ThemeProvider';
import Header from './components/common/Header';
import Sidebar from './components/common/Sidebar';
import ChatInterface from './components/chat/ChatInterface';
import OntologyBrowser from './components/ontology/OntologyBrowser';
import { useWebSocket } from './hooks/useWebSocket';
import { useUIStore } from './store/uiStore';
import { useChatStore } from './store/chatStore';
import { useKeyboardShortcuts, createShortcut } from './hooks/useKeyboardShortcuts';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

const AppContent: React.FC = () => {
  const sidebarOpen = useUIStore(state => state.sidebarOpen);
  const toggleSidebar = useUIStore(state => state.toggleSidebar);
  const toggleOntologyBrowser = useUIStore(state => state.toggleOntologyBrowser);
  const setWSConnected = useUIStore(state => state.setWSConnected);
  const setIsTyping = useChatStore(state => state.setIsTyping);

  // WebSocket connection
  const { connected } = useWebSocket(message => {
    if (message.type === 'typing') {
      setIsTyping(message.data.isTyping);
    }
    // Handle other message types as needed
  });

  useEffect(() => {
    setWSConnected(connected);
  }, [connected, setWSConnected]);

  // Keyboard shortcuts
  useKeyboardShortcuts([
    createShortcut('b', toggleSidebar, 'Toggle sidebar', { ctrl: true }),
    createShortcut('o', toggleOntologyBrowser, 'Toggle ontology browser', { ctrl: true }),
    createShortcut('k', () => {
      // Focus search/input
      document.querySelector<HTMLInputElement>('input[type="text"]')?.focus();
    }, 'Focus input', { ctrl: true }),
  ]);

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      <Header />

      <Box sx={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <Sidebar />

        <Box
          component="main"
          sx={{
            flexGrow: 1,
            transition: theme =>
              theme.transitions.create(['margin', 'width'], {
                easing: theme.transitions.easing.sharp,
                duration: theme.transitions.duration.leavingScreen,
              }),
            marginLeft: sidebarOpen ? 0 : '-280px',
          }}
        >
          <ChatInterface />
        </Box>

        <OntologyBrowser />
      </Box>

      {/* Toast notifications */}
      <Toaster
        position="bottom-right"
        toastOptions={{
          duration: 3000,
          style: {
            background: '#363636',
            color: '#fff',
          },
          success: {
            duration: 2000,
            iconTheme: {
              primary: '#4caf50',
              secondary: '#fff',
            },
          },
          error: {
            duration: 4000,
            iconTheme: {
              primary: '#f44336',
              secondary: '#fff',
            },
          },
        }}
      />
    </Box>
  );
};

const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AppContent />
        <ReactQueryDevtools initialIsOpen={false} />
      </ThemeProvider>
    </QueryClientProvider>
  );
};

export default App;
