# SPARQL Agent Frontend

Modern React-based chat interface for the SPARQL Agent - an AI-powered SPARQL query assistant.

## Features

### Core Functionality
- **Natural Language to SPARQL**: Convert plain English questions into SPARQL queries
- **Multi-Endpoint Support**: Connect to various SPARQL endpoints (UniProt, Wikidata, DBpedia, etc.)
- **Interactive Chat Interface**: Conversational UI for querying knowledge graphs
- **Real-time Query Execution**: Execute and visualize SPARQL query results

### Advanced UI Features
- **Multiple Result Views**:
  - Table view with sorting and pagination
  - Graph visualization for RDF triples
  - Chart view (bar, line, pie charts)
  - Raw JSON view
- **Syntax Highlighting**: Beautiful SPARQL query display with Prism.js
- **Export Functionality**: Export results in CSV, JSON, TSV, Turtle, RDF/XML, N-Triples
- **Dark/Light Theme**: System-aware theme with manual toggle
- **Responsive Design**: Works on desktop, tablet, and mobile

### Developer Features
- **TypeScript**: Full type safety throughout the application
- **React Query**: Efficient data fetching and caching
- **Zustand**: Lightweight state management
- **WebSocket Support**: Real-time updates and typing indicators
- **PWA Support**: Installable as a progressive web app
- **Keyboard Shortcuts**: Power-user friendly navigation
- **Accessibility**: WCAG 2.1 compliant

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Material-UI v5** - Component library
- **TanStack Query** - Data fetching and caching
- **Zustand** - State management
- **Recharts** - Data visualization
- **React Syntax Highlighter** - Code highlighting
- **Axios** - HTTP client

## Getting Started

### Prerequisites

- Node.js >= 18.0.0
- npm >= 9.0.0

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Development Scripts

```bash
# Run linter
npm run lint

# Type check
npm run type-check

# Format code
npm run format
```

## Project Structure

```
src/
├── components/          # React components
│   ├── chat/           # Chat interface components
│   │   ├── ChatInterface.tsx
│   │   ├── MessageBubble.tsx
│   │   └── QueryInput.tsx
│   ├── results/        # Result display components
│   │   ├── ResultsDisplay.tsx
│   │   ├── TableView.tsx
│   │   ├── GraphView.tsx
│   │   ├── ChartView.tsx
│   │   └── JSONView.tsx
│   ├── endpoint/       # Endpoint selection
│   │   └── EndpointSelector.tsx
│   ├── ontology/       # Ontology browser
│   │   └── OntologyBrowser.tsx
│   └── common/         # Shared components
│       ├── Header.tsx
│       ├── Sidebar.tsx
│       └── ThemeProvider.tsx
├── hooks/              # Custom React hooks
│   ├── useWebSocket.ts
│   ├── useKeyboardShortcuts.ts
│   └── useDebounce.ts
├── services/           # API and WebSocket services
│   ├── api.ts
│   └── websocket.ts
├── store/              # State management (Zustand)
│   ├── chatStore.ts
│   └── uiStore.ts
├── types/              # TypeScript type definitions
│   └── index.ts
├── utils/              # Utility functions
│   ├── formatters.ts
│   └── export.ts
├── styles/             # Global styles
│   └── index.css
├── App.tsx             # Main application component
└── main.tsx            # Application entry point
```

## Configuration

### API Endpoint

The frontend expects the backend API to be available at `/api` (configured in `vite.config.ts`):

```typescript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true
    }
  }
}
```

Update this to match your backend server location.

### Environment Variables

Create a `.env` file for custom configuration:

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
```

## Features in Detail

### Chat Interface

- Session-based conversations
- Message history with timestamps
- Streaming responses (optional)
- Query validation and error handling
- Auto-suggestions based on ontology

### Query Input

- Auto-complete for SPARQL keywords
- Ontology term suggestions
- Template queries
- Multi-line input support
- Keyboard shortcuts (Enter to submit, Shift+Enter for new line)

### Results Display

**Table View**
- Sortable columns
- Pagination
- Link detection for URIs
- Cell formatting based on data type

**Graph View**
- Visual representation of RDF triples
- Subject-Predicate-Object relationships
- Interactive node display

**Chart View**
- Bar, line, and pie charts
- Configurable X and Y axes
- Automatic data parsing

**JSON View**
- Formatted JSON output
- Copy to clipboard
- Syntax highlighting

### Ontology Browser

- Tree view of ontology classes and properties
- Search functionality
- Term details panel
- URI information
- Domain and range display

### Keyboard Shortcuts

- `Ctrl+B` - Toggle sidebar
- `Ctrl+O` - Toggle ontology browser
- `Ctrl+K` - Focus input field
- `Enter` - Submit query (in input)
- `Shift+Enter` - New line (in input)
- `Escape` - Close dialogs/dropdowns

## Accessibility

- Semantic HTML elements
- ARIA labels and roles
- Keyboard navigation support
- Focus management
- Screen reader friendly
- High contrast support

## Performance Optimizations

- Code splitting and lazy loading
- Virtual scrolling for large result sets
- Debounced search inputs
- React Query caching
- Memoized expensive computations
- Service Worker for offline support

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)

## Contributing

1. Follow the existing code style
2. Write TypeScript with proper types
3. Add comments for complex logic
4. Test on multiple browsers
5. Ensure accessibility standards

## License

Part of the SPARQL Agent project.
