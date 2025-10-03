import React, { useState } from 'react';
import {
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  IconButton,
  Box,
  Typography,
  Divider,
  Fab,
  Menu,
  MenuItem,
} from '@mui/material';
import {
  Add,
  Chat,
  Settings,
  Storage,
  MenuBook,
  Delete,
  Edit,
  MoreVert,
} from '@mui/icons-material';
import { useChatStore } from '@store/chatStore';
import { useUIStore } from '@store/uiStore';
import { formatRelativeTime } from '@utils/formatters';
import EndpointSelector from '../endpoint/EndpointSelector';

const DRAWER_WIDTH = 280;

const Sidebar: React.FC = () => {
  const [endpointSelectorOpen, setEndpointSelectorOpen] = useState(false);
  const [sessionMenuAnchor, setSessionMenuAnchor] = useState<{
    element: HTMLElement;
    sessionId: string;
  } | null>(null);

  const sessions = useChatStore(state => state.sessions);
  const currentSessionId = useChatStore(state => state.currentSessionId);
  const createSession = useChatStore(state => state.createSession);
  const setCurrentSession = useChatStore(state => state.setCurrentSession);
  const deleteSession = useChatStore(state => state.deleteSession);

  const sidebarOpen = useUIStore(state => state.sidebarOpen);
  const toggleOntologyBrowser = useUIStore(state => state.toggleOntologyBrowser);

  const handleNewSession = () => {
    setEndpointSelectorOpen(true);
  };

  const handleEndpointSelect = (endpoint: any) => {
    const title = `New Chat - ${endpoint.name}`;
    createSession(title, endpoint);
  };

  const handleDeleteSession = (sessionId: string) => {
    deleteSession(sessionId);
    setSessionMenuAnchor(null);
  };

  return (
    <>
      <Drawer
        variant="persistent"
        anchor="left"
        open={sidebarOpen}
        sx={{
          width: DRAWER_WIDTH,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: DRAWER_WIDTH,
            boxSizing: 'border-box',
          },
        }}
      >
        <Box sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
          {/* Header */}
          <Box mb={2}>
            <Typography variant="h6" gutterBottom>
              SPARQL Agent
            </Typography>
            <Fab
              color="primary"
              variant="extended"
              size="small"
              fullWidth
              onClick={handleNewSession}
            >
              <Add sx={{ mr: 1 }} />
              New Chat
            </Fab>
          </Box>

          <Divider sx={{ mb: 2 }} />

          {/* Sessions List */}
          <Box flex={1} overflow="auto">
            <Typography variant="caption" color="text.secondary" sx={{ pl: 2, mb: 1 }}>
              Recent Chats
            </Typography>
            <List dense>
              {sessions.map(session => (
                <ListItem
                  key={session.id}
                  disablePadding
                  secondaryAction={
                    <IconButton
                      size="small"
                      onClick={e => {
                        e.stopPropagation();
                        setSessionMenuAnchor({
                          element: e.currentTarget,
                          sessionId: session.id,
                        });
                      }}
                    >
                      <MoreVert fontSize="small" />
                    </IconButton>
                  }
                >
                  <ListItemButton
                    selected={currentSessionId === session.id}
                    onClick={() => setCurrentSession(session.id)}
                  >
                    <ListItemIcon>
                      <Chat />
                    </ListItemIcon>
                    <ListItemText
                      primary={session.title}
                      secondary={formatRelativeTime(session.updatedAt)}
                      primaryTypographyProps={{ noWrap: true }}
                      secondaryTypographyProps={{ variant: 'caption' }}
                    />
                  </ListItemButton>
                </ListItem>
              ))}
            </List>

            {sessions.length === 0 && (
              <Box textAlign="center" py={4}>
                <Typography variant="body2" color="text.secondary">
                  No chats yet. Create one to get started!
                </Typography>
              </Box>
            )}
          </Box>

          <Divider sx={{ my: 2 }} />

          {/* Bottom Actions */}
          <List dense>
            <ListItem disablePadding>
              <ListItemButton onClick={() => setEndpointSelectorOpen(true)}>
                <ListItemIcon>
                  <Storage />
                </ListItemIcon>
                <ListItemText primary="Endpoints" />
              </ListItemButton>
            </ListItem>

            <ListItem disablePadding>
              <ListItemButton onClick={toggleOntologyBrowser}>
                <ListItemIcon>
                  <MenuBook />
                </ListItemIcon>
                <ListItemText primary="Ontology" />
              </ListItemButton>
            </ListItem>

            <ListItem disablePadding>
              <ListItemButton>
                <ListItemIcon>
                  <Settings />
                </ListItemIcon>
                <ListItemText primary="Settings" />
              </ListItemButton>
            </ListItem>
          </List>
        </Box>
      </Drawer>

      {/* Session Context Menu */}
      <Menu
        anchorEl={sessionMenuAnchor?.element}
        open={Boolean(sessionMenuAnchor)}
        onClose={() => setSessionMenuAnchor(null)}
      >
        <MenuItem
          onClick={() => {
            if (sessionMenuAnchor) {
              // TODO: Implement rename
              setSessionMenuAnchor(null);
            }
          }}
        >
          <Edit fontSize="small" sx={{ mr: 1 }} />
          Rename
        </MenuItem>
        <MenuItem
          onClick={() => {
            if (sessionMenuAnchor) {
              handleDeleteSession(sessionMenuAnchor.sessionId);
            }
          }}
        >
          <Delete fontSize="small" sx={{ mr: 1 }} />
          Delete
        </MenuItem>
      </Menu>

      {/* Endpoint Selector Dialog */}
      <EndpointSelector
        open={endpointSelectorOpen}
        onClose={() => setEndpointSelectorOpen(false)}
        onSelect={handleEndpointSelect}
      />
    </>
  );
};

export default Sidebar;
