import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { UserPreferences, VisualizationConfig } from '@types/index';

interface UIState extends UserPreferences {
  // UI State
  sidebarOpen: boolean;
  ontologyBrowserOpen: boolean;
  queryHistoryOpen: boolean;
  visualizationConfig: VisualizationConfig;
  wsConnected: boolean;

  // Actions
  setTheme: (theme: 'light' | 'dark' | 'system') => void;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  toggleOntologyBrowser: () => void;
  toggleQueryHistory: () => void;
  setVisualizationConfig: (config: VisualizationConfig) => void;
  updatePreferences: (preferences: Partial<UserPreferences>) => void;
  setWSConnected: (connected: boolean) => void;
  resetToDefaults: () => void;
}

const defaultPreferences: UserPreferences = {
  theme: 'system',
  autoExecuteQueries: false,
  showQueryExplanations: true,
  maxResultsPerPage: 50,
  syntaxHighlightTheme: 'tomorrow',
  enableNotifications: true,
  enableWebSocket: true,
};

const defaultVisualizationConfig: VisualizationConfig = {
  type: 'table',
  options: {
    pageSize: 50,
    sortOrder: 'asc',
  },
};

export const useUIStore = create<UIState>()(
  persist(
    set => ({
      // Default preferences
      ...defaultPreferences,

      // UI state
      sidebarOpen: true,
      ontologyBrowserOpen: false,
      queryHistoryOpen: false,
      visualizationConfig: defaultVisualizationConfig,
      wsConnected: false,

      // Actions
      setTheme: theme => set({ theme }),

      toggleSidebar: () => set(state => ({ sidebarOpen: !state.sidebarOpen })),

      setSidebarOpen: open => set({ sidebarOpen: open }),

      toggleOntologyBrowser: () =>
        set(state => ({ ontologyBrowserOpen: !state.ontologyBrowserOpen })),

      toggleQueryHistory: () =>
        set(state => ({ queryHistoryOpen: !state.queryHistoryOpen })),

      setVisualizationConfig: config => set({ visualizationConfig: config }),

      updatePreferences: preferences => set(state => ({ ...state, ...preferences })),

      setWSConnected: connected => set({ wsConnected: connected }),

      resetToDefaults: () => set({ ...defaultPreferences, visualizationConfig: defaultVisualizationConfig }),
    }),
    {
      name: 'sparql-agent-ui',
    }
  )
);
