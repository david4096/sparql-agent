# SPARQL Agent Frontend - Component Tree

## Visual Component Hierarchy

```
App (main entry point)
│
├─ QueryClientProvider (TanStack Query)
│  │
│  └─ ThemeProvider (MUI + Custom)
│     │
│     ├─ CssBaseline (MUI)
│     │
│     ├─ AppContent
│     │  │
│     │  ├─ Header
│     │  │  ├─ AppBar
│     │  │  ├─ MenuIcon Button (toggle sidebar)
│     │  │  ├─ Title
│     │  │  ├─ Endpoint Chip (current endpoint)
│     │  │  ├─ WebSocket Status Chip
│     │  │  └─ Theme Toggle Button
│     │  │
│     │  ├─ Sidebar (Drawer)
│     │  │  ├─ Header
│     │  │  │  ├─ Logo/Title
│     │  │  │  └─ New Chat Button
│     │  │  │
│     │  │  ├─ Sessions List
│     │  │  │  └─ Session Items (map)
│     │  │  │     ├─ Chat Icon
│     │  │  │     ├─ Session Title
│     │  │  │     ├─ Timestamp
│     │  │  │     └─ More Menu Button
│     │  │  │
│     │  │  └─ Bottom Actions
│     │  │     ├─ Endpoints Button
│     │  │     ├─ Ontology Button
│     │  │     └─ Settings Button
│     │  │
│     │  ├─ Main Content Area
│     │  │  │
│     │  │  └─ ChatInterface
│     │  │     │
│     │  │     ├─ Messages Area (scrollable)
│     │  │     │  ├─ Empty State (conditional)
│     │  │     │  │
│     │  │     │  ├─ Message List
│     │  │     │  │  └─ MessageBubble (map)
│     │  │     │  │     ├─ Avatar (User/AI icon)
│     │  │     │  │     ├─ Message Paper
│     │  │     │  │     │  ├─ Content (text)
│     │  │     │  │     │  ├─ Query Section (conditional)
│     │  │     │  │     │  │  ├─ Status Chip
│     │  │     │  │     │  │  ├─ Duration
│     │  │     │  │     │  │  ├─ Expand/Collapse Button
│     │  │     │  │     │  │  ├─ Query Display (Collapse)
│     │  │     │  │     │  │  │  ├─ Copy Button
│     │  │     │  │     │  │  │  └─ SyntaxHighlighter (SPARQL)
│     │  │     │  │     │  │  └─ Explanation Text
│     │  │     │  │     │  │
│     │  │     │  │     │  ├─ Results Section (conditional)
│     │  │     │  │     │  │  ├─ Results Header
│     │  │     │  │     │  │  │  ├─ Row Count
│     │  │     │  │     │  │  │  └─ Expand/Collapse Button
│     │  │     │  │     │  │  └─ ResultsDisplay (Collapse)
│     │  │     │  │     │  │
│     │  │     │  │     │  ├─ Error Section (conditional)
│     │  │     │  │     │  │  └─ Error Paper
│     │  │     │  │     │  │
│     │  │     │  │     │  └─ Timestamp
│     │  │     │  │     │
│     │  │     │  │     └─ Avatar (if user message)
│     │  │     │  │
│     │  │     │  └─ Typing Indicator (conditional)
│     │  │     │
│     │  │     └─ Input Area (Paper)
│     │  │        │
│     │  │        └─ QueryInput
│     │  │           ├─ TextField (multi-line)
│     │  │           │  ├─ Endpoint Chip (start adornment)
│     │  │           │  └─ Input field
│     │  │           │
│     │  │           ├─ Send Button (IconButton)
│     │  │           │
│     │  │           └─ Suggestions Popper (conditional)
│     │  │              └─ Paper
│     │  │                 └─ List
│     │  │                    └─ Suggestion Items (map)
│     │  │                       ├─ Icon (template/history)
│     │  │                       └─ Text (primary/secondary)
│     │  │
│     │  └─ OntologyBrowser (Drawer - right)
│     │     ├─ Header
│     │     │  ├─ Title
│     │     │  └─ Close Button
│     │     │
│     │     ├─ Endpoint Chip
│     │     │
│     │     ├─ Search Field
│     │     │
│     │     ├─ Content Area
│     │     │  ├─ Loading State (conditional)
│     │     │  │
│     │     │  ├─ Empty State (conditional)
│     │     │  │
│     │     │  ├─ Search Results (conditional)
│     │     │  │  └─ Result List
│     │     │  │     └─ Term Items (map)
│     │     │  │
│     │     │  └─ Ontology Tree (conditional)
│     │     │     └─ Tree Nodes (recursive)
│     │     │        ├─ Expand/Collapse Button
│     │     │        ├─ Icon (class/property)
│     │     │        ├─ Label
│     │     │        └─ Children (Collapse)
│     │     │
│     │     └─ Term Details Panel (conditional, bottom)
│     │        ├─ Header
│     │        │  ├─ Term Label
│     │        │  └─ Close Button
│     │        │
│     │        ├─ Type Chip
│     │        ├─ Description
│     │        ├─ URI
│     │        ├─ Domain (if property)
│     │        └─ Range (if property)
│     │
│     └─ Toaster (notifications)
│
└─ ReactQueryDevtools (development only)
```

## Results Display Component Tree

```
ResultsDisplay
│
├─ Toolbar
│  ├─ View Toggle Group
│  │  ├─ Table Button
│  │  ├─ Graph Button
│  │  ├─ Chart Button
│  │  └─ JSON Button
│  │
│  └─ Export Button
│     └─ Export Menu (Popper)
│        ├─ CSV MenuItem
│        ├─ JSON MenuItem
│        ├─ TSV MenuItem
│        ├─ Turtle MenuItem
│        ├─ RDF/XML MenuItem
│        └─ N-Triples MenuItem
│
└─ View Content (conditional based on mode)
   │
   ├─ TableView
   │  ├─ TableContainer
   │  │  └─ Table
   │  │     ├─ TableHead
   │  │     │  └─ TableRow
   │  │     │     └─ TableCell (map variables)
   │  │     │        └─ TableSortLabel
   │  │     │
   │  │     └─ TableBody
   │  │        └─ TableRow (map bindings)
   │  │           └─ TableCell (map variables)
   │  │              ├─ Link (if URI)
   │  │              ├─ Chip (if bnode)
   │  │              └─ Text (if literal)
   │  │
   │  └─ TablePagination
   │
   ├─ GraphView
   │  ├─ SVG Container
   │  │  ├─ Edges Group
   │  │  │  └─ Edge (map edges)
   │  │  │     ├─ Line
   │  │  │     └─ Label Text
   │  │  │
   │  │  ├─ Nodes Group
   │  │  │  └─ Node (map nodes)
   │  │  │     ├─ Circle
   │  │  │     └─ Label Text
   │  │  │
   │  │  └─ Defs (arrow marker)
   │  │
   │  └─ Stats Text
   │
   ├─ ChartView
   │  ├─ Controls Stack
   │  │  ├─ Chart Type Select
   │  │  ├─ X-Axis Select
   │  │  └─ Y-Axis Select
   │  │
   │  ├─ Chart Container (ResponsiveContainer)
   │  │  ├─ BarChart (conditional)
   │  │  │  ├─ CartesianGrid
   │  │  │  ├─ XAxis
   │  │  │  ├─ YAxis
   │  │  │  ├─ Tooltip
   │  │  │  ├─ Legend
   │  │  │  └─ Bar
   │  │  │
   │  │  ├─ LineChart (conditional)
   │  │  │  ├─ CartesianGrid
   │  │  │  ├─ XAxis
   │  │  │  ├─ YAxis
   │  │  │  ├─ Tooltip
   │  │  │  ├─ Legend
   │  │  │  └─ Line
   │  │  │
   │  │  └─ PieChart (conditional)
   │  │     └─ Pie
   │  │        ├─ Tooltip
   │  │        └─ Cell (map data)
   │  │
   │  └─ Data Count Text
   │
   └─ JSONView
      ├─ Copy Button (absolute positioned)
      └─ SyntaxHighlighter (JSON)
```

## Endpoint Selector Component Tree

```
EndpointSelector (Dialog)
│
├─ DialogTitle
│  ├─ Title Text
│  └─ Close Button
│
└─ DialogContent
   ├─ Search Field
   │
   ├─ Loading State (conditional)
   │  └─ CircularProgress
   │
   └─ Endpoint List
      └─ ListItem (map endpoints)
         └─ ListItemButton
            ├─ ListItemIcon
            │  ├─ CheckCircle (if selected)
            │  └─ Storage (if not selected)
            │
            └─ ListItemText
               ├─ Primary
               │  ├─ Name
               │  └─ Category Chip
               │
               └─ Secondary
                  ├─ Description
                  └─ URL
```

## Data Flow Diagram

```
User Input
   │
   ├─ QueryInput Component
   │  │
   │  ├─ Debounced Search (300ms)
   │  │  └─ TanStack Query
   │  │     └─ API: getSuggestions()
   │  │        └─ Suggestions Display
   │  │
   │  └─ Submit (Enter key)
   │     │
   │     ├─ Add User Message (chatStore)
   │     │
   │     ├─ Set Typing Indicator (chatStore)
   │     │
   │     ├─ API: translateToSPARQL()
   │     │  │
   │     │  ├─ Success
   │     │  │  ├─ Add Assistant Message with Query
   │     │  │  │
   │     │  │  └─ Auto-Execute (if enabled)
   │     │  │     └─ API: executeQuery()
   │     │  │        │
   │     │  │        ├─ Success
   │     │  │        │  └─ Update Message with Results
   │     │  │        │
   │     │  │        └─ Error
   │     │  │           └─ Update Message with Error
   │     │  │
   │     │  └─ Error
   │     │     └─ Add Assistant Message with Error
   │     │
   │     └─ Clear Typing Indicator (chatStore)
   │
   └─ Display in ChatInterface
      └─ MessageBubble
         └─ ResultsDisplay
            └─ View Components
```

## State Flow Diagram

```
User Actions
   │
   ├─ Chat Actions
   │  │
   │  ├─ Create Session
   │  │  └─ chatStore.createSession()
   │  │     ├─ Generate UUID
   │  │     ├─ Create Session Object
   │  │     ├─ Add to sessions[]
   │  │     ├─ Set as currentSessionId
   │  │     └─ Persist to localStorage
   │  │
   │  ├─ Send Message
   │  │  └─ chatStore.addMessage()
   │  │     ├─ Generate Message ID
   │  │     ├─ Add timestamp
   │  │     ├─ Add to session.messages[]
   │  │     └─ Update session.updatedAt
   │  │
   │  └─ Switch Session
   │     └─ chatStore.setCurrentSession()
   │        ├─ Update currentSessionId
   │        └─ Update currentEndpoint
   │
   ├─ UI Actions
   │  │
   │  ├─ Toggle Theme
   │  │  └─ uiStore.setTheme()
   │  │     ├─ Update theme state
   │  │     └─ Persist to localStorage
   │  │
   │  ├─ Toggle Sidebar
   │  │  └─ uiStore.toggleSidebar()
   │  │     └─ Update sidebarOpen
   │  │
   │  └─ Toggle Ontology Browser
   │     └─ uiStore.toggleOntologyBrowser()
   │        └─ Update ontologyBrowserOpen
   │
   └─ API Queries
      │
      ├─ TanStack Query
      │  ├─ Cache Management (5 min stale time)
      │  ├─ Loading States
      │  ├─ Error Handling
      │  └─ Auto Refetch
      │
      └─ WebSocket
         ├─ Connection Management
         ├─ Auto Reconnect (exponential backoff)
         ├─ Message Handlers
         └─ Status Updates
```

## Component Communication Patterns

### Parent → Child (Props)
```
ChatInterface → MessageBubble
   ├─ message: Message
   └─ (MessageBubble renders based on props)

ResultsDisplay → TableView
   ├─ results: QueryResults
   └─ (TableView renders table)
```

### Child → Parent (Callbacks)
```
QueryInput → ChatInterface
   ├─ onSubmit callback
   └─ (triggered on Enter key)

EndpointSelector → Sidebar
   ├─ onSelect callback
   └─ (triggered on endpoint selection)
```

### Sibling Communication (Shared State)
```
Header ←→ chatStore ←→ Sidebar
   ├─ Header displays currentEndpoint
   └─ Sidebar updates currentEndpoint

QueryInput ←→ chatStore ←→ MessageBubble
   ├─ QueryInput adds messages
   └─ MessageBubble displays messages
```

### Global State (Zustand Stores)
```
Any Component → chatStore
   ├─ Read: sessions, currentSessionId, currentEndpoint
   └─ Write: createSession, addMessage, updateMessage

Any Component → uiStore
   ├─ Read: theme, sidebarOpen, wsConnected
   └─ Write: setTheme, toggleSidebar, updatePreferences
```

### Server State (TanStack Query)
```
Component → useQuery
   ├─ queryKey: ['endpoints']
   ├─ queryFn: apiClient.getEndpoints()
   ├─ Cache: 5 minutes
   └─ Returns: { data, isLoading, error }

Component → useQuery
   ├─ queryKey: ['suggestions', input, endpointId]
   ├─ queryFn: apiClient.getSuggestions()
   ├─ Enabled: input.length > 2
   └─ Returns: { data, isLoading }
```

## Event Flow Diagram

```
User Types in QueryInput
   ↓
onChange event
   ↓
setInput(value)
   ↓
useDebounce (300ms) ← Wait
   ↓
debouncedInput changes
   ↓
useQuery triggers
   ↓
API: getSuggestions()
   ↓
Results cached by TanStack Query
   ↓
suggestions state updates
   ↓
Suggestions Popper shows
   ↓
User selects suggestion (click/enter)
   ↓
applySuggestion()
   ↓
Update input with suggestion
   ↓
User presses Enter
   ↓
handleSubmit()
   ↓
Add user message to chatStore
   ↓
API: translateToSPARQL()
   ↓
Add assistant message with query
   ↓
API: executeQuery() (if auto-execute)
   ↓
Update message with results
   ↓
Re-render MessageBubble
   ↓
Display ResultsDisplay
```

## Component Lifecycle

### ChatInterface Lifecycle
```
Mount
   ├─ Get currentSession from chatStore
   ├─ Subscribe to store changes
   └─ Render initial state

Update (when messages change)
   ├─ Re-render message list
   ├─ Trigger scrollToBottom()
   └─ Smooth scroll to latest message

Unmount
   └─ Cleanup (automatic with React)
```

### WebSocket Lifecycle
```
App Mount
   ├─ useWebSocket hook initializes
   ├─ wsService.connect()
   │  ├─ Create WebSocket connection
   │  ├─ Set up event handlers
   │  └─ Update wsConnected state
   │
   ├─ onMessage handler
   │  ├─ Parse message
   │  └─ Update UI based on message type
   │
   └─ Connection lost
      ├─ onDisconnect handler
      ├─ Update wsConnected to false
      └─ attemptReconnect()
         ├─ Wait (exponential backoff)
         └─ Retry up to 5 times

App Unmount
   └─ wsService.disconnect()
      ├─ Close connection
      └─ Cleanup handlers
```

## Rendering Optimization

### Memoization Points
```
TableView
   └─ useMemo for sortedBindings
   └─ useMemo for paginatedBindings

GraphView
   └─ useMemo for { nodes, edges }
   └─ useMemo for layoutNodes

ChartView
   └─ useMemo for chartData
```

### Conditional Rendering
```
ChatInterface
   ├─ if (!currentSession) → Empty state
   ├─ if (messages.length === 0) → Welcome message
   └─ else → Message list

MessageBubble
   ├─ if (message.query) → Query section
   ├─ if (message.results) → Results section
   └─ if (message.error) → Error section
```

## Component Responsibility Matrix

| Component | Responsibilities |
|-----------|-----------------|
| App | Query provider, theme provider, layout structure |
| Header | Navigation, theme toggle, status display |
| Sidebar | Session list, navigation actions |
| ChatInterface | Message display, scrolling, layout |
| MessageBubble | Single message rendering, expand/collapse |
| QueryInput | Input handling, suggestions, submission |
| ResultsDisplay | View mode switching, export menu |
| TableView | Tabular data display, sorting, pagination |
| GraphView | RDF graph visualization |
| ChartView | Chart rendering, axis selection |
| JSONView | JSON formatting and display |
| EndpointSelector | Endpoint selection, search, filtering |
| OntologyBrowser | Tree navigation, term search, details |
| ThemeProvider | Theme management, MUI theming |

## Summary

- **Total Components:** 15 React components
- **Component Depth:** Maximum 5 levels deep
- **State Management:** 2 Zustand stores (chat, UI)
- **Data Fetching:** TanStack Query with caching
- **Real-time:** WebSocket service with hooks
- **Communication:** Props, callbacks, shared state, events
- **Optimization:** Memoization, conditional rendering, lazy loading ready

This architecture provides:
- Clear separation of concerns
- Predictable data flow
- Efficient re-rendering
- Scalable component structure
- Easy to test and maintain
