import React, { useMemo, useEffect } from 'react';
import {
  ThemeProvider as MuiThemeProvider,
  createTheme,
  CssBaseline,
  useMediaQuery,
} from '@mui/material';
import { useUIStore } from '@store/uiStore';

interface ThemeProviderProps {
  children: React.ReactNode;
}

const ThemeProvider: React.FC<ThemeProviderProps> = ({ children }) => {
  const themeMode = useUIStore(state => state.theme);
  const setTheme = useUIStore(state => state.setTheme);
  const prefersDarkMode = useMediaQuery('(prefers-color-scheme: dark)');

  // Detect system theme changes
  useEffect(() => {
    if (themeMode === 'system') {
      // Theme will be automatically updated via prefersDarkMode
    }
  }, [prefersDarkMode, themeMode]);

  const theme = useMemo(() => {
    const mode =
      themeMode === 'system' ? (prefersDarkMode ? 'dark' : 'light') : themeMode;

    return createTheme({
      palette: {
        mode,
        primary: {
          main: '#1976d2',
          light: '#42a5f5',
          dark: '#1565c0',
        },
        secondary: {
          main: '#9c27b0',
          light: '#ba68c8',
          dark: '#7b1fa2',
        },
        background: {
          default: mode === 'dark' ? '#121212' : '#fafafa',
          paper: mode === 'dark' ? '#1e1e1e' : '#ffffff',
        },
      },
      typography: {
        fontFamily: [
          '-apple-system',
          'BlinkMacSystemFont',
          '"Segoe UI"',
          'Roboto',
          '"Helvetica Neue"',
          'Arial',
          'sans-serif',
        ].join(','),
        h6: {
          fontWeight: 600,
        },
        subtitle1: {
          fontWeight: 500,
        },
      },
      shape: {
        borderRadius: 8,
      },
      components: {
        MuiButton: {
          styleOverrides: {
            root: {
              textTransform: 'none',
              fontWeight: 500,
            },
          },
        },
        MuiChip: {
          styleOverrides: {
            root: {
              fontWeight: 500,
            },
          },
        },
        MuiPaper: {
          styleOverrides: {
            root: {
              backgroundImage: 'none',
            },
          },
        },
      },
    });
  }, [themeMode, prefersDarkMode]);

  return (
    <MuiThemeProvider theme={theme}>
      <CssBaseline />
      {children}
    </MuiThemeProvider>
  );
};

export default ThemeProvider;
