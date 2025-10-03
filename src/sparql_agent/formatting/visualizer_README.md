# Visualization Module

Comprehensive visualization and chart generation for SPARQL query results.

## Overview

The visualization module provides powerful tools for creating interactive and static visualizations from SPARQL query results. It supports:

- **Network Graphs**: RDF relationship visualization using NetworkX
- **Statistical Charts**: Bar, pie, line, scatter plots, histograms, and heatmaps
- **Multiple Backends**: Plotly (interactive), Matplotlib (static), Seaborn (statistical)
- **Smart Selection**: Automatic visualization type recommendation
- **D3.js Export**: Export data in D3-compatible JSON format
- **Biomedical Focus**: Specialized support for genomics, proteomics, and clinical data

## Features

### 1. GraphVisualizer

Visualize RDF relationships as interactive network graphs.

**Key Features:**
- Multiple layout algorithms (spring, circular, hierarchical, Kamada-Kawai, spectral)
- Node and edge customization
- Centrality-based highlighting
- Subgraph extraction for large graphs
- D3.js export for web integration

**Example:**
```python
from sparql_agent.formatting.visualizer import GraphVisualizer, NetworkGraphConfig, LayoutAlgorithm

# Configure visualization
graph_config = NetworkGraphConfig(
    layout=LayoutAlgorithm.KAMADA_KAWAI,
    node_size=40,
    node_color="#3498db",
    show_node_labels=True,
    max_nodes=500
)

# Create visualizer
visualizer = GraphVisualizer(backend="plotly", graph_config=graph_config)

# Generate network graph
fig = visualizer.create_network_graph(query_result)

# Save as interactive HTML
visualizer.save_html(fig, "network.html")

# Export for D3.js
d3_data = visualizer.export_d3_json(query_result)
```

### 2. ChartGenerator

Create statistical charts for aggregated data.

**Supported Chart Types:**
- **Bar Charts**: Categorical aggregations
- **Pie Charts**: Proportional distributions
- **Line Charts**: Time series and trends
- **Scatter Plots**: Correlations
- **Histograms**: Numeric distributions
- **Heatmaps**: Relationship matrices

**Example:**
```python
from sparql_agent.formatting.visualizer import ChartGenerator, ChartConfig

# Configure chart
chart_config = ChartConfig(
    x_axis_label="Category",
    y_axis_label="Count",
    show_values=True,
    show_grid=True
)

# Create generator
generator = ChartGenerator(backend="plotly", chart_config=chart_config)

# Generate bar chart
fig = generator.create_bar_chart(result, x_var="category", y_var="count")

# Save
generator.save(fig, "chart.html")
```

### 3. Smart Visualization Selection

Automatically choose the best visualization type based on data patterns.

**Example:**
```python
from sparql_agent.formatting.visualizer import auto_visualize, VisualizationSelector

# Automatically detect and create appropriate visualization
fig = auto_visualize(query_result)

# Or get recommendation first
viz_type = VisualizationSelector.recommend_visualization(query_result)
print(f"Recommended: {viz_type.value}")
```

### 4. Color Schemes

Predefined color schemes including colorblind-friendly palettes.

**Available Schemes:**
- **Colorblind-Safe**: Deuteranopia, Protanopia, Tritanopia
- **Standard**: Pastel, Vibrant, Ocean, Forest
- **Biomedical**: Gene Expression, Pathways

**Example:**
```python
from sparql_agent.formatting.visualizer import ColorSchemes

# Get colorblind-safe scheme
colors = ColorSchemes.get_scheme("colorblind_safe")

# Check if scheme is colorblind-safe
is_safe = ColorSchemes.is_colorblind_safe("deuteranopia")  # True
```

### 5. Time Series Detection

Automatically detect and format time series data.

**Example:**
```python
from sparql_agent.formatting.visualizer import TimeSeriesDetector

# Detect time series data
is_time_series = TimeSeriesDetector.is_time_series(result)

# Detect time variable
time_var = TimeSeriesDetector.detect_time_variable(result)
```

### 6. Geographic Data Detection

Identify and handle geographic data in SPARQL results.

**Example:**
```python
from sparql_agent.formatting.visualizer import GeographicDataDetector

# Detect geographic data
is_geo = GeographicDataDetector.is_geographic(result)

# Detect lat/lon variables
lat_var, lon_var = GeographicDataDetector.detect_lat_lon_variables(result)
```

## Configuration Options

### VisualizationConfig

General configuration for all visualizations:

```python
VisualizationConfig(
    width=1200,                    # Width in pixels
    height=800,                    # Height in pixels
    title="My Visualization",      # Chart title
    show_legend=True,              # Show legend
    color_scheme="viridis",        # Color scheme name
    background_color="white",      # Background color
    interactive=True,              # Interactive mode
    show_labels=True,              # Show labels
    font_size=12,                  # Font size
    dpi=300                        # DPI for static exports
)
```

### NetworkGraphConfig

Configuration specific to network graphs:

```python
NetworkGraphConfig(
    layout=LayoutAlgorithm.SPRING, # Layout algorithm
    node_size=30,                  # Node size
    node_color="#1f77b4",          # Node color
    edge_width=1.0,                # Edge width
    edge_color="#888888",          # Edge color
    show_node_labels=True,         # Show node labels
    show_edge_labels=False,        # Show edge labels
    curved_edges=True,             # Use curved edges
    highlight_central_nodes=False, # Highlight by centrality
    max_nodes=500                  # Maximum nodes to display
)
```

### ChartConfig

Configuration specific to charts:

```python
ChartConfig(
    x_axis_label="X Axis",         # X-axis label
    y_axis_label="Y Axis",         # Y-axis label
    show_values=False,             # Show values on bars/points
    orientation="vertical",        # Chart orientation
    stacked=False,                 # Stack series
    log_scale=False,               # Use log scale
    show_grid=True,                # Show grid
    marker_size=8,                 # Marker size (scatter)
    line_width=2.0                 # Line width (line charts)
)
```

## Layout Algorithms

Available layout algorithms for network graphs:

- **SPRING**: Force-directed spring layout (default)
- **CIRCULAR**: Circular layout
- **HIERARCHICAL**: Hierarchical/tree layout
- **KAMADA_KAWAI**: Kamada-Kawai layout (good for biological networks)
- **SPECTRAL**: Spectral layout
- **RANDOM**: Random layout

## Backends

### Plotly (Interactive)
- Interactive web-based visualizations
- Zoom, pan, hover tooltips
- Export to HTML
- Best for: web dashboards, exploration

### Matplotlib (Static)
- Publication-quality static plots
- High DPI export (PNG, SVG, PDF)
- Customizable for papers
- Best for: publications, reports

### Seaborn (Statistical)
- Statistical visualizations
- Built on Matplotlib
- Optimized for heatmaps
- Best for: statistical analysis

## Export Formats

Supported export formats:

- **HTML**: Interactive web visualizations (Plotly)
- **PNG**: Raster images (all backends)
- **SVG**: Vector graphics (all backends)
- **PDF**: Portable documents (Matplotlib)
- **JSON**: D3.js compatible data (all)

## Biomedical Applications

### Gene Interaction Networks

```python
# Visualize gene-gene interactions
visualizer = GraphVisualizer(backend="plotly")
fig = visualizer.create_network_graph(
    gene_interaction_result,
    subject_var="gene1",
    predicate_var="interaction_type",
    object_var="gene2"
)
```

### Gene Expression Heatmaps

```python
# Create expression heatmap
generator = ChartGenerator(backend="plotly")
fig = generator.create_heatmap(
    expression_result,
    row_var="gene",
    col_var="sample",
    value_var="expression_level"
)
```

### Clinical Trial Timeline

```python
# Visualize temporal trends
generator = ChartGenerator(backend="plotly")
fig = generator.create_line_chart(
    clinical_trial_result,
    x_var="year",
    y_var="enrollment_count"
)
```

### Disease Prevalence

```python
# Show disease distribution
generator = ChartGenerator(backend="plotly")
fig = generator.create_bar_chart(
    disease_result,
    x_var="disease_category",
    y_var="patient_count"
)
```

## Best Practices

### 1. Choose Appropriate Visualization

- **Network graphs**: For RDF triples, relationships, pathways
- **Bar charts**: For categorical comparisons, counts
- **Line charts**: For time series, trends over time
- **Scatter plots**: For correlations, dose-response
- **Heatmaps**: For matrices, gene expression
- **Pie charts**: For small categorical proportions (<10 categories)

### 2. Use Colorblind-Friendly Schemes

```python
# Always consider accessibility
viz_config = VisualizationConfig(
    color_scheme="colorblind_safe"
)
```

### 3. Limit Node Count in Networks

```python
# Set max_nodes to prevent performance issues
graph_config = NetworkGraphConfig(
    max_nodes=200  # Automatically extract subgraph
)
```

### 4. Add Clear Labels

```python
chart_config = ChartConfig(
    x_axis_label="Clear X Label",
    y_axis_label="Clear Y Label with Units (mg)"
)
```

### 5. Export Multiple Formats

```python
# Save both interactive and static versions
visualizer.save_html(fig, "interactive.html")
visualizer.save_image(fig, "static.png", format="png")
```

## Error Handling

All visualization functions raise `VisualizationError` on failure:

```python
from sparql_agent.core.exceptions import VisualizationError

try:
    fig = visualizer.create_network_graph(result)
except VisualizationError as e:
    print(f"Visualization failed: {e}")
    print(f"Details: {e.details}")
```

## Dependencies

Required packages:

```bash
# Core dependencies
pip install networkx plotly matplotlib

# Optional for enhanced features
pip install seaborn pandas
```

## Examples

See comprehensive examples in:
- `visualizer_examples.py` - General visualization examples
- `visualizer_biomedical_examples.py` - Biomedical data patterns

Run examples:
```bash
python -m sparql_agent.formatting.visualizer_examples
python -m sparql_agent.formatting.visualizer_biomedical_examples
```

## API Reference

### Convenience Functions

Quick functions for common visualizations:

```python
# Create network graph
fig = create_network_graph(result, backend="plotly")

# Create bar chart
fig = create_bar_chart(result, x_var="x", y_var="y")

# Create pie chart
fig = create_pie_chart(result, labels_var="labels", values_var="values")

# Auto-visualize
fig = auto_visualize(result)
```

## Performance Considerations

### Large Networks (>1000 nodes)

```python
# Use subgraph extraction
graph_config = NetworkGraphConfig(max_nodes=500)

# Or use faster layout algorithms
graph_config = NetworkGraphConfig(layout=LayoutAlgorithm.RANDOM)
```

### Large Datasets

```python
# Aggregate data in SPARQL query before visualization
# Use sampling for scatter plots with >10,000 points
# Consider binning for histograms
```

### Interactive vs Static

- Interactive (Plotly): Better for exploration, larger file sizes
- Static (Matplotlib): Better for publications, smaller file sizes

## Integration with SPARQL Agent

The visualization module integrates seamlessly with the SPARQL agent workflow:

```python
from sparql_agent.execution.executor import QueryExecutor
from sparql_agent.formatting.visualizer import auto_visualize

# Execute query
executor = QueryExecutor(endpoint_url)
result = executor.execute_query(sparql_query)

# Auto-visualize results
fig = auto_visualize(result)
```

## Troubleshooting

### ImportError: No module named 'plotly'

Install required dependencies:
```bash
pip install plotly matplotlib networkx
```

### Empty visualization

Check that:
- Query result has data (`result.row_count > 0`)
- Query status is SUCCESS
- Variable names are correct

### Slow rendering

- Reduce `max_nodes` for networks
- Use faster layout algorithm
- Aggregate data in SPARQL query

### Colors not showing

- Check color_scheme name is valid
- Use hex colors for custom schemes
- Verify backend supports color scheme

## Contributing

To add new visualization types:

1. Add enum to `VisualizationType`
2. Implement `create_<type>` method in `ChartGenerator` or `GraphVisualizer`
3. Update `create_visualization` dispatch
4. Add tests in `test_visualizer.py`
5. Add examples in `visualizer_examples.py`

## License

Part of the SPARQL Agent project.
