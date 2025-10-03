# SPARQL Agent Frontend - Quick Start Guide

## Get Started in 5 Minutes

### 1. Install Dependencies

```bash
cd /Users/david/git/sparql-agent/web/frontend
npm install
```

This will install all required packages (~200MB of node_modules).

### 2. Start Development Server

```bash
npm run dev
```

The app will be available at: **http://localhost:3000**

### 3. Configure Backend Connection (Optional)

Create `.env` file if your backend is not on `localhost:8000`:

```env
VITE_API_URL=http://your-backend-url:8000
VITE_WS_URL=ws://your-backend-url:8000/ws
```

Default proxy configuration (in `vite.config.ts`):
- API: `http://localhost:8000`
- WebSocket: `ws://localhost:8000/ws`

## First Steps in the App

### 1. Create a New Chat Session

1. Click the "New Chat" button in the sidebar
2. Select a SPARQL endpoint from the dialog
3. The chat interface will open

### 2. Ask a Question

Type a natural language question in the input box:
- "What are the human proteins?"
- "List all proteins related to cancer"
- "Show diseases associated with gene BRCA1"

Press Enter to submit.

### 3. View Results

Switch between different view modes:
- **Table**: Sortable, paginated data table
- **Graph**: Visual representation of RDF triples
- **Chart**: Bar, line, or pie charts
- **JSON**: Raw JSON output

### 4. Export Results

Click the download icon and select format:
- CSV, JSON, TSV for tabular data
- Turtle, RDF/XML, N-Triples for RDF data

## Key Features

### Keyboard Shortcuts

- `Ctrl+B` - Toggle sidebar
- `Ctrl+O` - Toggle ontology browser
- `Ctrl+K` - Focus input field
- `Enter` - Submit query
- `Shift+Enter` - New line in input
- `Escape` - Close dialogs

### Theme Switching

Click the theme icon in the header to cycle through:
1. Light mode
2. Dark mode
3. System (follows OS preference)

### Ontology Browser

1. Click "Ontology" in sidebar
2. Search for terms or browse the tree
3. Click a term to see details
4. Use terms in your queries

### Session Management

- All sessions are saved in localStorage
- Switch between sessions in the sidebar
- Right-click a session for more options (rename, delete)

## Development Commands

```bash
# Start dev server with hot reload
npm run dev

# Type check without building
npm run type-check

# Lint code
npm run lint

# Format code with Prettier
npm run format

# Build for production
npm run build

# Preview production build
npm run preview
```

## Project Structure Overview

```
src/
├── components/     # UI components
│   ├── chat/      # Chat interface
│   ├── results/   # Result displays
│   ├── endpoint/  # Endpoint selector
│   ├── ontology/  # Ontology browser
│   └── common/    # Shared components
├── hooks/         # Custom hooks
├── services/      # API & WebSocket
├── store/         # State management
├── types/         # TypeScript types
├── utils/         # Utilities
└── styles/        # Global styles
```

## Common Issues & Solutions

### Issue: Port 3000 already in use

**Solution:** Change port in `vite.config.ts`:
```typescript
server: {
  port: 3001, // or any available port
  // ...
}
```

### Issue: API calls failing

**Solution:** Check:
1. Backend is running on port 8000
2. CORS is enabled on backend
3. Proxy configuration in `vite.config.ts`

### Issue: WebSocket not connecting

**Solution:** Check:
1. Backend WebSocket endpoint is `/ws`
2. WebSocket URL in preferences
3. Browser console for connection errors

### Issue: Type errors

**Solution:** Run type check:
```bash
npm run type-check
```

## Next Steps

1. **Customize Endpoints**: Edit the endpoint list in your backend API
2. **Add Custom Themes**: Modify `ThemeProvider.tsx`
3. **Extend Components**: Add new features to existing components
4. **Add Tests**: Set up Jest or Vitest for testing
5. **Deploy**: Build and deploy to your hosting service

## API Integration

The frontend expects the following backend endpoints:

### Chat
- `POST /api/chat/message` - Send message
- `POST /api/chat/stream` - Stream response

### Query
- `POST /api/query/execute` - Execute SPARQL
- `POST /api/query/validate` - Validate query
- `POST /api/query/explain` - Explain query
- `POST /api/query/translate` - Natural language to SPARQL

### Endpoints
- `GET /api/endpoints` - List endpoints
- `GET /api/endpoints/:id` - Get endpoint
- `POST /api/endpoints/test` - Test endpoint

### Ontology
- `GET /api/ontology/:endpointId` - Get ontology
- `GET /api/ontology/:endpointId/search` - Search ontology

### Suggestions
- `GET /api/suggestions` - Get suggestions
- `GET /api/templates/:endpointId` - Get templates

### WebSocket
- `WS /ws` - WebSocket connection

See `src/services/api.ts` for complete API client implementation.

## Resources

- **React Docs**: https://react.dev
- **Material-UI**: https://mui.com
- **TanStack Query**: https://tanstack.com/query
- **Vite**: https://vitejs.dev
- **TypeScript**: https://www.typescriptlang.org

## Support

For issues or questions:
1. Check `IMPLEMENTATION_SUMMARY.md` for detailed documentation
2. Review `README.md` for comprehensive feature list
3. Check browser console for errors
4. Verify backend API is responding

## License

Part of the SPARQL Agent project.
