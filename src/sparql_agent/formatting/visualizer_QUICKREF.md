# Visualization Quick Reference

## One-Liners

```python
from sparql_agent.formatting.visualizer import *

# Auto-select and create visualization
fig = auto_visualize(result)

# Network graph
fig = create_network_graph(result)

# Bar chart
fig = create_bar_chart(result, x_var="x", y_var="y")

# Pie chart
fig = create_pie_chart(result, labels_var="label", values_var="value")
```

## Common Patterns

### Gene Network
```python
visualizer = GraphVisualizer(backend="plotly")
fig = visualizer.create_network_graph(result)
visualizer.save_html(fig, "network.html")
```

### Expression Heatmap
```python
generator = ChartGenerator(backend="plotly")
fig = generator.create_heatmap(result, row_var="gene", col_var="sample", value_var="expression")
generator.save(fig, "heatmap.html")
```

### Time Series
```python
generator = ChartGenerator(backend="plotly")
fig = generator.create_line_chart(result, x_var="year", y_var="value")
generator.save(fig, "timeline.html")
```

### Colorblind-Safe
```python
viz_config = VisualizationConfig(color_scheme="colorblind_safe")
visualizer = GraphVisualizer(config=viz_config)
```

### D3.js Export
```python
import json
d3_data = visualizer.export_d3_json(result)
with open("data.json", "w") as f:
    json.dump(d3_data, f)
```

## Configuration Shortcuts

### Large Networks
```python
graph_config = NetworkGraphConfig(
    max_nodes=200,
    layout=LayoutAlgorithm.KAMADA_KAWAI
)
```

### Publication Quality
```python
viz_config = VisualizationConfig(
    width=1200,
    height=800,
    dpi=300,
    background_color="white"
)
```

### Show Values
```python
chart_config = ChartConfig(
    show_values=True,
    show_grid=True
)
```

## Detection

```python
# Time series
is_timeseries = TimeSeriesDetector.is_time_series(result)

# Geographic
is_geo = GeographicDataDetector.is_geographic(result)

# Get recommendation
viz_type = VisualizationSelector.recommend_visualization(result)
```

## Backends

```python
# Interactive
GraphVisualizer(backend="plotly")

# Static
GraphVisualizer(backend="matplotlib")

# Statistical
ChartGenerator(backend="seaborn")
```

## Export Formats

```python
# HTML (interactive)
visualizer.save_html(fig, "output.html")

# PNG (static)
visualizer.save_image(fig, "output.png", format="png")

# SVG (vector)
visualizer.save_image(fig, "output.svg", format="svg")

# PDF (document)
generator.save(fig, "output.pdf", format="pdf")
```

## Color Schemes

Available schemes:
- `colorblind_safe` - Safe for all
- `deuteranopia` - Red-green colorblindness
- `protanopia` - Red-green colorblindness
- `tritanopia` - Blue-yellow colorblindness
- `gene_expression` - For expression data
- `pathways` - For pathway data
- `viridis` - Default Plotly
- `plasma` - Perceptually uniform

## Layout Algorithms

- `SPRING` - Force-directed (default)
- `KAMADA_KAWAI` - Best for biological networks
- `CIRCULAR` - Circular layout
- `HIERARCHICAL` - Tree-like structure
- `SPECTRAL` - Based on graph spectrum
- `RANDOM` - Random positions

## Error Handling

```python
from sparql_agent.core.exceptions import VisualizationError

try:
    fig = visualizer.create_network_graph(result)
except VisualizationError as e:
    print(f"Error: {e}")
```

## Tips

1. **Use colorblind-safe schemes** for accessibility
2. **Set max_nodes** for large networks
3. **Add clear axis labels** with units
4. **Export both HTML and PNG** for flexibility
5. **Auto-detect time series** for line charts
6. **Use Kamada-Kawai** for biological networks
7. **Aggregate in SPARQL** before visualization
8. **Use heatmaps** for gene expression matrices
