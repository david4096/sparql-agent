import React from 'react';
import {
  AppBar,
  Toolbar,
  IconButton,
  Typography,
  Box,
  Tooltip,
  Switch,
  Chip,
} from '@mui/material';
import {
  Menu as MenuIcon,
  DarkMode,
  LightMode,
  Brightness4,
  Storage,
} from '@mui/icons-material';
import { useUIStore } from '@store/uiStore';
import { useChatStore } from '@store/chatStore';

const Header: React.FC = () => {
  const theme = useUIStore(state => state.theme);
  const setTheme = useUIStore(state => state.setTheme);
  const toggleSidebar = useUIStore(state => state.toggleSidebar);
  const wsConnected = useUIStore(state => state.wsConnected);
  const currentEndpoint = useChatStore(state => state.currentEndpoint);

  const handleThemeToggle = () => {
    if (theme === 'light') setTheme('dark');
    else if (theme === 'dark') setTheme('system');
    else setTheme('light');
  };

  const getThemeIcon = () => {
    switch (theme) {
      case 'light':
        return <LightMode />;
      case 'dark':
        return <DarkMode />;
      case 'system':
        return <Brightness4 />;
    }
  };

  return (
    <AppBar position="static" elevation={1}>
      <Toolbar>
        <IconButton
          edge="start"
          color="inherit"
          onClick={toggleSidebar}
          sx={{ mr: 2 }}
        >
          <MenuIcon />
        </IconButton>

        <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
          SPARQL Agent
        </Typography>

        {currentEndpoint && (
          <Chip
            icon={<Storage />}
            label={currentEndpoint.name}
            size="small"
            sx={{ mr: 2 }}
            color="default"
            variant="outlined"
          />
        )}

        {wsConnected && (
          <Chip
            label="Live"
            size="small"
            color="success"
            sx={{ mr: 2 }}
          />
        )}

        <Tooltip title={`Theme: ${theme}`}>
          <IconButton color="inherit" onClick={handleThemeToggle}>
            {getThemeIcon()}
          </IconButton>
        </Tooltip>
      </Toolbar>
    </AppBar>
  );
};

export default Header;
