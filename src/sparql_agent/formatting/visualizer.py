"""
Visualization and Chart Generators for SPARQL Results.

This module provides comprehensive visualization capabilities for SPARQL query results,
including network graphs for RDF relationships, statistical charts, and interactive
visualizations.

Features:
- GraphVisualizer: Network graphs for RDF relationships using NetworkX
- ChartGenerator: Bar, pie, line, and scatter plots
- Interactive web visualizations with Plotly
- Static publication-quality plots with Matplotlib
- D3.js exports for web integration
- Smart visualization selection based on data patterns
- Export to multiple formats (PNG, SVG, HTML, JSON)

Example:
    >>> from sparql_agent.formatting.visualizer import GraphVisualizer, ChartGenerator
    >>> from sparql_agent.core.types import QueryResult
    >>>
    >>> # Visualize RDF relationships as network graph
    >>> graph_viz = GraphVisualizer()
    >>> fig = graph_viz.create_network_graph(query_result)
    >>> graph_viz.save_html(fig, "network.html")
    >>>
    >>> # Create interactive bar chart
    >>> chart_gen = ChartGenerator()
    >>> chart = chart_gen.create_bar_chart(query_result, x_var="category", y_var="count")
    >>> chart_gen.save(chart, "barchart.html")
"""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from urllib.parse import urlparse

from ..core.exceptions import FormattingError, VisualizationError
from ..core.types import QueryResult, QueryStatus

logger = logging.getLogger(__name__)


class VisualizationType(Enum):
    """Types of visualizations supported."""
    NETWORK_GRAPH = "network_graph"
    BAR_CHART = "bar_chart"
    PIE_CHART = "pie_chart"
    LINE_CHART = "line_chart"
    SCATTER_PLOT = "scatter_plot"
    HISTOGRAM = "histogram"
    HEATMAP = "heatmap"
    TREEMAP = "treemap"
    SANKEY = "sankey"


class ExportFormat(Enum):
    """Export formats for visualizations."""
    PNG = "png"
    SVG = "svg"
    PDF = "pdf"
    HTML = "html"
    JSON = "json"
    D3_JSON = "d3_json"


class LayoutAlgorithm(Enum):
    """Layout algorithms for network graphs."""
    SPRING = "spring"
    CIRCULAR = "circular"
    HIERARCHICAL = "hierarchical"
    RANDOM = "random"
    KAMADA_KAWAI = "kamada_kawai"
    SPECTRAL = "spectral"


@dataclass
class VisualizationConfig:
    """
    Configuration for visualizations.

    Attributes:
        width: Width of the visualization in pixels
        height: Height of the visualization in pixels
        title: Title of the visualization
        show_legend: Whether to show legend
        color_scheme: Color scheme name (e.g., "viridis", "plasma", "Set1")
        background_color: Background color
        interactive: Whether to create interactive visualization
        show_labels: Whether to show labels
        font_size: Font size for labels
        dpi: DPI for static image exports
    """
    width: int = 1200
    height: int = 800
    title: Optional[str] = None
    show_legend: bool = True
    color_scheme: str = "Set3"
    background_color: str = "white"
    interactive: bool = True
    show_labels: bool = True
    font_size: int = 12
    dpi: int = 300


@dataclass
class NetworkGraphConfig:
    """
    Configuration specific to network graph visualizations.

    Attributes:
        layout: Layout algorithm to use
        node_size: Size of nodes
        node_color: Node color or attribute to color by
        edge_width: Width of edges
        edge_color: Edge color
        show_node_labels: Whether to show node labels
        show_edge_labels: Whether to show edge labels
        curved_edges: Whether to use curved edges
        highlight_central_nodes: Highlight nodes with high centrality
        min_edge_weight: Minimum edge weight to display
        max_nodes: Maximum number of nodes to display
    """
    layout: LayoutAlgorithm = LayoutAlgorithm.SPRING
    node_size: Union[int, str] = 30
    node_color: Union[str, List[str]] = "#1f77b4"
    edge_width: Union[float, str] = 1.0
    edge_color: str = "#888888"
    show_node_labels: bool = True
    show_edge_labels: bool = False
    curved_edges: bool = True
    highlight_central_nodes: bool = False
    min_edge_weight: float = 0.0
    max_nodes: int = 500


@dataclass
class ChartConfig:
    """
    Configuration specific to charts.

    Attributes:
        x_axis_label: Label for x-axis
        y_axis_label: Label for y-axis
        show_values: Whether to show values on bars/points
        orientation: Chart orientation ("horizontal" or "vertical")
        stacked: Whether to stack series
        log_scale: Whether to use log scale
        show_grid: Whether to show grid
        marker_size: Size of markers in scatter plots
        line_width: Width of lines in line charts
    """
    x_axis_label: Optional[str] = None
    y_axis_label: Optional[str] = None
    show_values: bool = False
    orientation: str = "vertical"
    stacked: bool = False
    log_scale: bool = False
    show_grid: bool = True
    marker_size: int = 8
    line_width: float = 2.0


class BaseVisualizer(ABC):
    """Abstract base class for visualizers."""

    def __init__(
        self,
        config: Optional[VisualizationConfig] = None,
    ):
        """
        Initialize visualizer.

        Args:
            config: Visualization configuration
        """
        self.config = config or VisualizationConfig()

    @abstractmethod
    def create_visualization(
        self,
        result: QueryResult,
        **kwargs
    ) -> Any:
        """
        Create visualization from query result.

        Args:
            result: Query result to visualize
            **kwargs: Additional visualization options

        Returns:
            Visualization object (type depends on backend)
        """
        pass

    def _validate_result(self, result: QueryResult) -> None:
        """
        Validate query result before visualization.

        Args:
            result: Query result to validate

        Raises:
            VisualizationError: If result is invalid
        """
        if result.status != QueryStatus.SUCCESS:
            raise VisualizationError(
                f"Cannot visualize failed query result: {result.error_message}",
                details={"status": result.status.value}
            )

        if result.row_count == 0:
            raise VisualizationError(
                "Cannot visualize empty result set",
                details={"row_count": 0}
            )

    def _extract_value(self, binding: Any) -> str:
        """
        Extract string value from binding.

        Args:
            binding: Binding value

        Returns:
            Extracted string value
        """
        if isinstance(binding, dict):
            return binding.get("value", "")
        return str(binding) if binding is not None else ""

    def _shorten_uri(self, uri: str, max_length: int = 30) -> str:
        """
        Shorten URI for display.

        Args:
            uri: URI to shorten
            max_length: Maximum length

        Returns:
            Shortened URI
        """
        if not uri.startswith("http"):
            return uri

        try:
            parsed = urlparse(uri)
            # Extract last part
            fragment = parsed.fragment or parsed.path.split("/")[-1]
            if fragment and len(fragment) < max_length:
                return fragment
        except:
            pass

        # Fallback: truncate
        if len(uri) > max_length:
            return "..." + uri[-(max_length-3):]
        return uri


class GraphVisualizer(BaseVisualizer):
    """
    Visualize RDF relationships as network graphs.

    Supports:
    - NetworkX for graph structure
    - Matplotlib for static visualizations
    - Plotly for interactive web visualizations
    - Multiple layout algorithms
    - Node and edge customization
    - Centrality highlighting
    - Subgraph extraction
    """

    def __init__(
        self,
        config: Optional[VisualizationConfig] = None,
        graph_config: Optional[NetworkGraphConfig] = None,
        backend: str = "plotly",
    ):
        """
        Initialize graph visualizer.

        Args:
            config: General visualization configuration
            graph_config: Network graph specific configuration
            backend: Visualization backend ("plotly" or "matplotlib")
        """
        super().__init__(config)
        self.graph_config = graph_config or NetworkGraphConfig()
        self.backend = backend

        # Check dependencies
        try:
            import networkx as nx
            self.nx = nx
        except ImportError:
            raise ImportError(
                "networkx is required for GraphVisualizer. "
                "Install it with: pip install networkx"
            )

        if backend == "plotly":
            try:
                import plotly.graph_objects as go
                import plotly.express as px
                self.go = go
                self.px = px
            except ImportError:
                raise ImportError(
                    "plotly is required for interactive graphs. "
                    "Install it with: pip install plotly"
                )
        elif backend == "matplotlib":
            try:
                import matplotlib.pyplot as plt
                import matplotlib.patches as mpatches
                self.plt = plt
                self.mpatches = mpatches
            except ImportError:
                raise ImportError(
                    "matplotlib is required for static graphs. "
                    "Install it with: pip install matplotlib"
                )

    def create_visualization(
        self,
        result: QueryResult,
        subject_var: Optional[str] = None,
        predicate_var: Optional[str] = None,
        object_var: Optional[str] = None,
        **kwargs
    ) -> Any:
        """
        Create network graph visualization.

        Args:
            result: Query result containing RDF triples
            subject_var: Variable name for subjects (auto-detected if None)
            predicate_var: Variable name for predicates (auto-detected if None)
            object_var: Variable name for objects (auto-detected if None)
            **kwargs: Additional options

        Returns:
            Graph visualization object
        """
        self._validate_result(result)

        # Build NetworkX graph
        graph = self._build_graph(result, subject_var, predicate_var, object_var)

        # Apply node limit
        if graph.number_of_nodes() > self.graph_config.max_nodes:
            graph = self._extract_subgraph(graph, self.graph_config.max_nodes)
            logger.warning(
                f"Graph limited to {self.graph_config.max_nodes} nodes. "
                f"Original had {graph.number_of_nodes()} nodes."
            )

        # Create visualization
        if self.backend == "plotly":
            return self._create_plotly_graph(graph)
        else:
            return self._create_matplotlib_graph(graph)

    def create_network_graph(
        self,
        result: QueryResult,
        **kwargs
    ) -> Any:
        """
        Convenience method for creating network graph.

        Args:
            result: Query result
            **kwargs: Additional options

        Returns:
            Network graph visualization
        """
        return self.create_visualization(result, **kwargs)

    def _build_graph(
        self,
        result: QueryResult,
        subject_var: Optional[str],
        predicate_var: Optional[str],
        object_var: Optional[str],
    ) -> "nx.Graph":
        """
        Build NetworkX graph from query result.

        Args:
            result: Query result
            subject_var: Subject variable name
            predicate_var: Predicate variable name
            object_var: Object variable name

        Returns:
            NetworkX graph
        """
        graph = self.nx.DiGraph()

        # Auto-detect variables if not provided
        if not subject_var or not object_var:
            subject_var, predicate_var, object_var = self._detect_triple_variables(result)

        # Build graph
        for binding in result.bindings:
            subject = self._extract_value(binding.get(subject_var)) if subject_var else None
            predicate = self._extract_value(binding.get(predicate_var)) if predicate_var else "related"
            obj = self._extract_value(binding.get(object_var)) if object_var else None

            if subject and obj:
                # Add nodes
                graph.add_node(subject, label=self._shorten_uri(subject))
                graph.add_node(obj, label=self._shorten_uri(obj))

                # Add edge
                if graph.has_edge(subject, obj):
                    # Increment weight
                    graph[subject][obj]["weight"] += 1
                else:
                    graph.add_edge(subject, obj, label=predicate, weight=1.0)

        return graph

    def _detect_triple_variables(
        self,
        result: QueryResult
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Auto-detect subject, predicate, object variables.

        Args:
            result: Query result

        Returns:
            Tuple of (subject_var, predicate_var, object_var)
        """
        variables = result.variables

        # Common patterns
        patterns = [
            ("s", "p", "o"),
            ("subject", "predicate", "object"),
            ("subj", "pred", "obj"),
            ("source", "relation", "target"),
            ("from", "type", "to"),
        ]

        for s, p, o in patterns:
            if s in variables and o in variables:
                pred = p if p in variables else None
                return s, pred, o

        # Fallback: use first 2-3 variables
        if len(variables) >= 2:
            return variables[0], variables[1] if len(variables) > 2 else None, variables[-1]

        return None, None, None

    def _extract_subgraph(self, graph: "nx.Graph", max_nodes: int) -> "nx.Graph":
        """
        Extract subgraph with most important nodes.

        Args:
            graph: Full graph
            max_nodes: Maximum nodes to keep

        Returns:
            Subgraph
        """
        # Calculate centrality
        centrality = self.nx.degree_centrality(graph)

        # Get top nodes
        top_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:max_nodes]
        top_node_ids = [node for node, _ in top_nodes]

        # Extract subgraph
        return graph.subgraph(top_node_ids).copy()

    def _create_plotly_graph(self, graph: "nx.Graph") -> "go.Figure":
        """
        Create interactive Plotly graph.

        Args:
            graph: NetworkX graph

        Returns:
            Plotly figure
        """
        # Calculate layout
        pos = self._calculate_layout(graph)

        # Create edge traces
        edge_traces = []
        for edge in graph.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]

            edge_trace = self.go.Scatter(
                x=[x0, x1, None],
                y=[y0, y1, None],
                mode="lines",
                line=dict(
                    width=self.graph_config.edge_width,
                    color=self.graph_config.edge_color
                ),
                hoverinfo="none",
                showlegend=False,
            )
            edge_traces.append(edge_trace)

        # Create node trace
        node_x = []
        node_y = []
        node_text = []
        node_hover = []

        for node in graph.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)

            label = graph.nodes[node].get("label", node)
            degree = graph.degree(node)

            node_text.append(label if self.graph_config.show_node_labels else "")
            node_hover.append(f"{label}<br>Degree: {degree}<br>URI: {node}")

        node_trace = self.go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text" if self.graph_config.show_node_labels else "markers",
            text=node_text,
            textposition="top center",
            hovertext=node_hover,
            hoverinfo="text",
            marker=dict(
                size=self.graph_config.node_size if isinstance(self.graph_config.node_size, int) else 20,
                color=self.graph_config.node_color if isinstance(self.graph_config.node_color, str) else None,
                line=dict(width=2, color="white"),
            ),
            showlegend=False,
        )

        # Create figure
        fig = self.go.Figure(
            data=edge_traces + [node_trace],
            layout=self.go.Layout(
                title=self.config.title or "RDF Network Graph",
                titlefont=dict(size=16),
                showlegend=self.config.show_legend,
                hovermode="closest",
                margin=dict(b=20, l=5, r=5, t=40),
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                plot_bgcolor=self.config.background_color,
                width=self.config.width,
                height=self.config.height,
            )
        )

        return fig

    def _create_matplotlib_graph(self, graph: "nx.Graph") -> "plt.Figure":
        """
        Create static Matplotlib graph.

        Args:
            graph: NetworkX graph

        Returns:
            Matplotlib figure
        """
        fig, ax = self.plt.subplots(
            figsize=(self.config.width / 100, self.config.height / 100),
            facecolor=self.config.background_color
        )

        # Calculate layout
        pos = self._calculate_layout(graph)

        # Draw edges
        self.nx.draw_networkx_edges(
            graph,
            pos,
            ax=ax,
            width=self.graph_config.edge_width,
            edge_color=self.graph_config.edge_color,
            alpha=0.5,
            arrows=True,
        )

        # Draw nodes
        node_colors = self.graph_config.node_color
        if isinstance(node_colors, str):
            node_colors = [node_colors] * graph.number_of_nodes()

        self.nx.draw_networkx_nodes(
            graph,
            pos,
            ax=ax,
            node_size=self.graph_config.node_size if isinstance(self.graph_config.node_size, int) else 300,
            node_color=node_colors,
            alpha=0.8,
        )

        # Draw labels
        if self.graph_config.show_node_labels:
            labels = {node: graph.nodes[node].get("label", node) for node in graph.nodes()}
            self.nx.draw_networkx_labels(
                graph,
                pos,
                labels,
                ax=ax,
                font_size=self.config.font_size,
            )

        ax.set_title(self.config.title or "RDF Network Graph", fontsize=16)
        ax.axis("off")

        self.plt.tight_layout()
        return fig

    def _calculate_layout(self, graph: "nx.Graph") -> Dict[str, Tuple[float, float]]:
        """
        Calculate node positions using specified layout algorithm.

        Args:
            graph: NetworkX graph

        Returns:
            Dictionary mapping node IDs to (x, y) positions
        """
        layout_func = {
            LayoutAlgorithm.SPRING: self.nx.spring_layout,
            LayoutAlgorithm.CIRCULAR: self.nx.circular_layout,
            LayoutAlgorithm.RANDOM: self.nx.random_layout,
            LayoutAlgorithm.KAMADA_KAWAI: self.nx.kamada_kawai_layout,
            LayoutAlgorithm.SPECTRAL: self.nx.spectral_layout,
        }.get(self.graph_config.layout, self.nx.spring_layout)

        try:
            return layout_func(graph)
        except:
            # Fallback to spring layout
            return self.nx.spring_layout(graph)

    def save_html(self, fig: Any, filepath: str) -> None:
        """
        Save Plotly figure as interactive HTML.

        Args:
            fig: Plotly figure
            filepath: Output file path
        """
        if self.backend != "plotly":
            raise VisualizationError("HTML export only supported for Plotly backend")

        fig.write_html(filepath)
        logger.info(f"Saved interactive graph to {filepath}")

    def save_image(self, fig: Any, filepath: str, format: str = "png") -> None:
        """
        Save figure as static image.

        Args:
            fig: Figure to save
            filepath: Output file path
            format: Image format (png, svg, pdf)
        """
        if self.backend == "matplotlib":
            fig.savefig(filepath, format=format, dpi=self.config.dpi, bbox_inches="tight")
        else:
            # Plotly
            fig.write_image(filepath, format=format, width=self.config.width, height=self.config.height)

        logger.info(f"Saved graph image to {filepath}")

    def export_d3_json(
        self,
        result: QueryResult,
        subject_var: Optional[str] = None,
        predicate_var: Optional[str] = None,
        object_var: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Export network data in D3.js compatible JSON format.

        Args:
            result: Query result containing RDF triples
            subject_var: Variable name for subjects (auto-detected if None)
            predicate_var: Variable name for predicates (auto-detected if None)
            object_var: Variable name for objects (auto-detected if None)

        Returns:
            D3.js compatible JSON with nodes and links
        """
        # Auto-detect variables if not provided
        if not subject_var or not object_var:
            subject_var, predicate_var, object_var = self._detect_triple_variables(result)

        # Build nodes and links
        nodes = {}
        links = []

        for binding in result.bindings:
            subject = self._extract_value(binding.get(subject_var)) if subject_var else None
            predicate = self._extract_value(binding.get(predicate_var)) if predicate_var else "related"
            obj = self._extract_value(binding.get(object_var)) if object_var else None

            if subject and obj:
                # Add nodes
                if subject not in nodes:
                    nodes[subject] = {
                        "id": subject,
                        "label": self._shorten_uri(subject),
                        "group": self._get_node_group(subject)
                    }
                if obj not in nodes:
                    nodes[obj] = {
                        "id": obj,
                        "label": self._shorten_uri(obj),
                        "group": self._get_node_group(obj)
                    }

                # Add link
                links.append({
                    "source": subject,
                    "target": obj,
                    "label": predicate,
                    "value": 1
                })

        return {
            "nodes": list(nodes.values()),
            "links": links
        }

    def _get_node_group(self, uri: str) -> int:
        """
        Get node group for coloring based on URI pattern.

        Args:
            uri: Node URI

        Returns:
            Group number for coloring
        """
        # Simple hashing to group similar URIs
        if not uri.startswith("http"):
            return 0

        # Extract domain or namespace
        try:
            from urllib.parse import urlparse
            parsed = urlparse(uri)
            domain = parsed.netloc or parsed.path.split('/')[0]
            return hash(domain) % 10
        except:
            return 0


class ChartGenerator(BaseVisualizer):
    """
    Generate statistical charts for SPARQL results.

    Supports:
    - Bar charts for categorical data and aggregations
    - Pie charts for proportions
    - Line charts for time series
    - Scatter plots for correlations
    - Histograms for distributions
    - Heatmaps for relationship matrices
    - Interactive and static output
    """

    def __init__(
        self,
        config: Optional[VisualizationConfig] = None,
        chart_config: Optional[ChartConfig] = None,
        backend: str = "plotly",
    ):
        """
        Initialize chart generator.

        Args:
            config: General visualization configuration
            chart_config: Chart specific configuration
            backend: Visualization backend ("plotly", "matplotlib", or "seaborn")
        """
        super().__init__(config)
        self.chart_config = chart_config or ChartConfig()
        self.backend = backend

        # Check dependencies
        if backend == "plotly":
            try:
                import plotly.graph_objects as go
                import plotly.express as px
                self.go = go
                self.px = px
            except ImportError:
                raise ImportError(
                    "plotly is required for interactive charts. "
                    "Install it with: pip install plotly"
                )
        elif backend == "matplotlib":
            try:
                import matplotlib.pyplot as plt
                self.plt = plt
            except ImportError:
                raise ImportError(
                    "matplotlib is required for static charts. "
                    "Install it with: pip install matplotlib"
                )
        elif backend == "seaborn":
            try:
                import seaborn as sns
                import matplotlib.pyplot as plt
                self.sns = sns
                self.plt = plt
            except ImportError:
                raise ImportError(
                    "seaborn and matplotlib are required for statistical visualizations. "
                    "Install them with: pip install seaborn matplotlib"
                )

    def create_visualization(
        self,
        result: QueryResult,
        viz_type: VisualizationType = VisualizationType.BAR_CHART,
        **kwargs
    ) -> Any:
        """
        Create chart visualization.

        Args:
            result: Query result
            viz_type: Type of visualization
            **kwargs: Additional options

        Returns:
            Chart visualization object
        """
        self._validate_result(result)

        if viz_type == VisualizationType.BAR_CHART:
            return self.create_bar_chart(result, **kwargs)
        elif viz_type == VisualizationType.PIE_CHART:
            return self.create_pie_chart(result, **kwargs)
        elif viz_type == VisualizationType.LINE_CHART:
            return self.create_line_chart(result, **kwargs)
        elif viz_type == VisualizationType.SCATTER_PLOT:
            return self.create_scatter_plot(result, **kwargs)
        elif viz_type == VisualizationType.HISTOGRAM:
            return self.create_histogram(result, **kwargs)
        elif viz_type == VisualizationType.HEATMAP:
            return self.create_heatmap(result, **kwargs)
        else:
            raise VisualizationError(f"Unsupported visualization type: {viz_type}")

    def create_bar_chart(
        self,
        result: QueryResult,
        x_var: Optional[str] = None,
        y_var: Optional[str] = None,
        **kwargs
    ) -> Any:
        """
        Create bar chart for categorical data.

        Args:
            result: Query result
            x_var: Variable for x-axis (categories)
            y_var: Variable for y-axis (values)
            **kwargs: Additional options

        Returns:
            Bar chart figure
        """
        # Auto-detect variables
        if not x_var or not y_var:
            x_var, y_var = self._detect_chart_variables(result)

        # Extract data
        x_data = []
        y_data = []

        for binding in result.bindings:
            x_val = self._extract_value(binding.get(x_var))
            y_val = self._extract_value(binding.get(y_var))

            if x_val and y_val:
                x_data.append(self._shorten_uri(x_val, 40))
                try:
                    y_data.append(float(y_val))
                except ValueError:
                    y_data.append(0)

        if self.backend == "plotly":
            return self._create_plotly_bar_chart(x_data, y_data, x_var, y_var)
        else:
            return self._create_matplotlib_bar_chart(x_data, y_data, x_var, y_var)

    def create_pie_chart(
        self,
        result: QueryResult,
        labels_var: Optional[str] = None,
        values_var: Optional[str] = None,
        **kwargs
    ) -> Any:
        """
        Create pie chart for proportions.

        Args:
            result: Query result
            labels_var: Variable for labels
            values_var: Variable for values
            **kwargs: Additional options

        Returns:
            Pie chart figure
        """
        # Auto-detect variables
        if not labels_var or not values_var:
            labels_var, values_var = self._detect_chart_variables(result)

        # Extract data
        labels = []
        values = []

        for binding in result.bindings:
            label = self._extract_value(binding.get(labels_var))
            value = self._extract_value(binding.get(values_var))

            if label and value:
                labels.append(self._shorten_uri(label, 30))
                try:
                    values.append(float(value))
                except ValueError:
                    values.append(0)

        if self.backend == "plotly":
            return self._create_plotly_pie_chart(labels, values)
        else:
            return self._create_matplotlib_pie_chart(labels, values)

    def create_line_chart(
        self,
        result: QueryResult,
        x_var: Optional[str] = None,
        y_var: Optional[str] = None,
        **kwargs
    ) -> Any:
        """
        Create line chart for time series or trends.

        Args:
            result: Query result
            x_var: Variable for x-axis
            y_var: Variable for y-axis
            **kwargs: Additional options

        Returns:
            Line chart figure
        """
        # Auto-detect variables
        if not x_var or not y_var:
            x_var, y_var = self._detect_chart_variables(result)

        # Extract data
        x_data = []
        y_data = []

        for binding in result.bindings:
            x_val = self._extract_value(binding.get(x_var))
            y_val = self._extract_value(binding.get(y_var))

            if x_val and y_val:
                x_data.append(x_val)
                try:
                    y_data.append(float(y_val))
                except ValueError:
                    y_data.append(0)

        if self.backend == "plotly":
            return self._create_plotly_line_chart(x_data, y_data, x_var, y_var)
        else:
            return self._create_matplotlib_line_chart(x_data, y_data, x_var, y_var)

    def create_scatter_plot(
        self,
        result: QueryResult,
        x_var: Optional[str] = None,
        y_var: Optional[str] = None,
        **kwargs
    ) -> Any:
        """
        Create scatter plot for correlations.

        Args:
            result: Query result
            x_var: Variable for x-axis
            y_var: Variable for y-axis
            **kwargs: Additional options

        Returns:
            Scatter plot figure
        """
        # Auto-detect variables
        if not x_var or not y_var:
            vars = self._detect_numeric_variables(result)
            if len(vars) >= 2:
                x_var, y_var = vars[0], vars[1]

        # Extract data
        x_data = []
        y_data = []

        for binding in result.bindings:
            x_val = self._extract_value(binding.get(x_var))
            y_val = self._extract_value(binding.get(y_var))

            try:
                x_data.append(float(x_val))
                y_data.append(float(y_val))
            except (ValueError, TypeError):
                continue

        if self.backend == "plotly":
            return self._create_plotly_scatter_plot(x_data, y_data, x_var, y_var)
        else:
            return self._create_matplotlib_scatter_plot(x_data, y_data, x_var, y_var)

    def create_histogram(
        self,
        result: QueryResult,
        var: Optional[str] = None,
        bins: int = 20,
        **kwargs
    ) -> Any:
        """
        Create histogram for distributions.

        Args:
            result: Query result
            var: Variable to plot
            bins: Number of bins
            **kwargs: Additional options

        Returns:
            Histogram figure
        """
        # Auto-detect variable
        if not var:
            vars = self._detect_numeric_variables(result)
            if vars:
                var = vars[0]

        # Extract data
        data = []
        for binding in result.bindings:
            val = self._extract_value(binding.get(var))
            try:
                data.append(float(val))
            except (ValueError, TypeError):
                continue

        if self.backend == "plotly":
            return self._create_plotly_histogram(data, var, bins)
        else:
            return self._create_matplotlib_histogram(data, var, bins)

    def _detect_chart_variables(self, result: QueryResult) -> Tuple[str, str]:
        """
        Auto-detect appropriate variables for charts.

        Args:
            result: Query result

        Returns:
            Tuple of (x_var, y_var)
        """
        variables = result.variables

        if len(variables) >= 2:
            return variables[0], variables[1]
        elif len(variables) == 1:
            return variables[0], variables[0]

        raise VisualizationError("Could not detect chart variables")

    def _detect_numeric_variables(self, result: QueryResult) -> List[str]:
        """
        Detect numeric variables in result.

        Args:
            result: Query result

        Returns:
            List of numeric variable names
        """
        numeric_vars = []

        for var in result.variables:
            # Check first few values
            sample_values = []
            for binding in result.bindings[:10]:
                val = self._extract_value(binding.get(var))
                try:
                    sample_values.append(float(val))
                except (ValueError, TypeError):
                    break

            if len(sample_values) >= 5:
                numeric_vars.append(var)

        return numeric_vars

    # Plotly implementations
    def _create_plotly_bar_chart(self, x_data, y_data, x_label, y_label):
        """Create Plotly bar chart."""
        fig = self.go.Figure(data=[
            self.go.Bar(
                x=x_data,
                y=y_data,
                marker=dict(color=self.config.color_scheme),
                text=y_data if self.chart_config.show_values else None,
                textposition="auto",
            )
        ])

        fig.update_layout(
            title=self.config.title or "Bar Chart",
            xaxis_title=self.chart_config.x_axis_label or x_label,
            yaxis_title=self.chart_config.y_axis_label or y_label,
            width=self.config.width,
            height=self.config.height,
            showlegend=self.config.show_legend,
            plot_bgcolor=self.config.background_color,
        )

        return fig

    def _create_plotly_pie_chart(self, labels, values):
        """Create Plotly pie chart."""
        fig = self.go.Figure(data=[
            self.go.Pie(
                labels=labels,
                values=values,
                textinfo="label+percent",
            )
        ])

        fig.update_layout(
            title=self.config.title or "Pie Chart",
            width=self.config.width,
            height=self.config.height,
            showlegend=self.config.show_legend,
        )

        return fig

    def _create_plotly_line_chart(self, x_data, y_data, x_label, y_label):
        """Create Plotly line chart."""
        fig = self.go.Figure(data=[
            self.go.Scatter(
                x=x_data,
                y=y_data,
                mode="lines+markers",
                line=dict(width=self.chart_config.line_width),
                marker=dict(size=self.chart_config.marker_size),
            )
        ])

        fig.update_layout(
            title=self.config.title or "Line Chart",
            xaxis_title=self.chart_config.x_axis_label or x_label,
            yaxis_title=self.chart_config.y_axis_label or y_label,
            width=self.config.width,
            height=self.config.height,
            showlegend=self.config.show_legend,
            plot_bgcolor=self.config.background_color,
        )

        return fig

    def _create_plotly_scatter_plot(self, x_data, y_data, x_label, y_label):
        """Create Plotly scatter plot."""
        fig = self.go.Figure(data=[
            self.go.Scatter(
                x=x_data,
                y=y_data,
                mode="markers",
                marker=dict(
                    size=self.chart_config.marker_size,
                    color=self.config.color_scheme,
                ),
            )
        ])

        fig.update_layout(
            title=self.config.title or "Scatter Plot",
            xaxis_title=self.chart_config.x_axis_label or x_label,
            yaxis_title=self.chart_config.y_axis_label or y_label,
            width=self.config.width,
            height=self.config.height,
            showlegend=self.config.show_legend,
            plot_bgcolor=self.config.background_color,
        )

        return fig

    def _create_plotly_histogram(self, data, var, bins):
        """Create Plotly histogram."""
        fig = self.go.Figure(data=[
            self.go.Histogram(
                x=data,
                nbinsx=bins,
                marker=dict(color=self.config.color_scheme),
            )
        ])

        fig.update_layout(
            title=self.config.title or "Histogram",
            xaxis_title=self.chart_config.x_axis_label or var,
            yaxis_title="Frequency",
            width=self.config.width,
            height=self.config.height,
            showlegend=self.config.show_legend,
            plot_bgcolor=self.config.background_color,
        )

        return fig

    # Matplotlib implementations
    def _create_matplotlib_bar_chart(self, x_data, y_data, x_label, y_label):
        """Create Matplotlib bar chart."""
        fig, ax = self.plt.subplots(
            figsize=(self.config.width / 100, self.config.height / 100)
        )

        ax.bar(x_data, y_data, color=self.config.color_scheme)

        if self.chart_config.show_values:
            for i, v in enumerate(y_data):
                ax.text(i, v, str(v), ha="center", va="bottom")

        ax.set_xlabel(self.chart_config.x_axis_label or x_label)
        ax.set_ylabel(self.chart_config.y_axis_label or y_label)
        ax.set_title(self.config.title or "Bar Chart")

        self.plt.xticks(rotation=45, ha="right")
        self.plt.tight_layout()

        return fig

    def _create_matplotlib_pie_chart(self, labels, values):
        """Create Matplotlib pie chart."""
        fig, ax = self.plt.subplots(
            figsize=(self.config.width / 100, self.config.height / 100)
        )

        ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
        ax.set_title(self.config.title or "Pie Chart")

        return fig

    def _create_matplotlib_line_chart(self, x_data, y_data, x_label, y_label):
        """Create Matplotlib line chart."""
        fig, ax = self.plt.subplots(
            figsize=(self.config.width / 100, self.config.height / 100)
        )

        ax.plot(x_data, y_data, linewidth=self.chart_config.line_width,
                marker="o", markersize=self.chart_config.marker_size)

        ax.set_xlabel(self.chart_config.x_axis_label or x_label)
        ax.set_ylabel(self.chart_config.y_axis_label or y_label)
        ax.set_title(self.config.title or "Line Chart")

        if self.chart_config.show_grid:
            ax.grid(True, alpha=0.3)

        self.plt.tight_layout()

        return fig

    def _create_matplotlib_scatter_plot(self, x_data, y_data, x_label, y_label):
        """Create Matplotlib scatter plot."""
        fig, ax = self.plt.subplots(
            figsize=(self.config.width / 100, self.config.height / 100)
        )

        ax.scatter(x_data, y_data, s=self.chart_config.marker_size * 5,
                   c=self.config.color_scheme, alpha=0.6)

        ax.set_xlabel(self.chart_config.x_axis_label or x_label)
        ax.set_ylabel(self.chart_config.y_axis_label or y_label)
        ax.set_title(self.config.title or "Scatter Plot")

        if self.chart_config.show_grid:
            ax.grid(True, alpha=0.3)

        self.plt.tight_layout()

        return fig

    def _create_matplotlib_histogram(self, data, var, bins):
        """Create Matplotlib histogram."""
        fig, ax = self.plt.subplots(
            figsize=(self.config.width / 100, self.config.height / 100)
        )

        ax.hist(data, bins=bins, color=self.config.color_scheme, alpha=0.7)

        ax.set_xlabel(self.chart_config.x_axis_label or var)
        ax.set_ylabel("Frequency")
        ax.set_title(self.config.title or "Histogram")

        if self.chart_config.show_grid:
            ax.grid(True, alpha=0.3)

        self.plt.tight_layout()

        return fig

    def create_heatmap(
        self,
        result: QueryResult,
        row_var: Optional[str] = None,
        col_var: Optional[str] = None,
        value_var: Optional[str] = None,
        **kwargs
    ) -> Any:
        """
        Create heatmap for relationship matrices.

        Args:
            result: Query result
            row_var: Variable for rows
            col_var: Variable for columns
            value_var: Variable for cell values
            **kwargs: Additional options

        Returns:
            Heatmap figure
        """
        # Auto-detect variables
        if not row_var or not col_var or not value_var:
            vars = result.variables
            if len(vars) >= 3:
                row_var, col_var, value_var = vars[0], vars[1], vars[2]
            else:
                raise VisualizationError("Heatmap requires at least 3 variables")

        # Build matrix
        import pandas as pd

        rows = []
        for binding in result.bindings:
            row = self._extract_value(binding.get(row_var))
            col = self._extract_value(binding.get(col_var))
            value = self._extract_value(binding.get(value_var))

            try:
                value = float(value)
            except (ValueError, TypeError):
                value = 0

            rows.append({
                "row": self._shorten_uri(row, 30),
                "col": self._shorten_uri(col, 30),
                "value": value
            })

        df = pd.DataFrame(rows)
        matrix = df.pivot(index="row", columns="col", values="value").fillna(0)

        if self.backend == "plotly":
            return self._create_plotly_heatmap(matrix, row_var, col_var)
        elif self.backend == "seaborn":
            return self._create_seaborn_heatmap(matrix)
        else:
            return self._create_matplotlib_heatmap(matrix, row_var, col_var)

    def _create_plotly_heatmap(self, matrix, row_label, col_label):
        """Create Plotly heatmap."""
        fig = self.go.Figure(data=self.go.Heatmap(
            z=matrix.values,
            x=matrix.columns.tolist(),
            y=matrix.index.tolist(),
            colorscale=self.config.color_scheme,
            showscale=True,
        ))

        fig.update_layout(
            title=self.config.title or "Heatmap",
            xaxis_title=col_label,
            yaxis_title=row_label,
            width=self.config.width,
            height=self.config.height,
        )

        return fig

    def _create_seaborn_heatmap(self, matrix):
        """Create Seaborn heatmap."""
        fig, ax = self.plt.subplots(
            figsize=(self.config.width / 100, self.config.height / 100)
        )

        self.sns.heatmap(
            matrix,
            annot=self.chart_config.show_values,
            cmap=self.config.color_scheme,
            ax=ax,
            cbar=True,
            square=False,
        )

        ax.set_title(self.config.title or "Heatmap")
        self.plt.tight_layout()

        return fig

    def _create_matplotlib_heatmap(self, matrix, row_label, col_label):
        """Create Matplotlib heatmap."""
        fig, ax = self.plt.subplots(
            figsize=(self.config.width / 100, self.config.height / 100)
        )

        im = ax.imshow(matrix.values, cmap=self.config.color_scheme, aspect='auto')

        # Set ticks
        ax.set_xticks(range(len(matrix.columns)))
        ax.set_yticks(range(len(matrix.index)))
        ax.set_xticklabels(matrix.columns)
        ax.set_yticklabels(matrix.index)

        # Rotate the tick labels
        self.plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

        # Add colorbar
        self.plt.colorbar(im, ax=ax)

        ax.set_title(self.config.title or "Heatmap")
        ax.set_xlabel(col_label)
        ax.set_ylabel(row_label)

        self.plt.tight_layout()

        return fig

    def export_d3_json(self, result: QueryResult, viz_type: VisualizationType) -> Dict[str, Any]:
        """
        Export data in D3.js compatible JSON format.

        Args:
            result: Query result
            viz_type: Type of visualization

        Returns:
            D3.js compatible JSON data structure
        """
        if viz_type == VisualizationType.NETWORK_GRAPH:
            return self._export_d3_network(result)
        elif viz_type in [VisualizationType.BAR_CHART, VisualizationType.LINE_CHART]:
            return self._export_d3_chart(result)
        elif viz_type == VisualizationType.PIE_CHART:
            return self._export_d3_pie(result)
        else:
            raise VisualizationError(f"D3.js export not supported for {viz_type}")

    def _export_d3_network(self, result: QueryResult) -> Dict[str, Any]:
        """Export network data for D3.js force-directed graph."""
        # Auto-detect variables
        s_var, p_var, o_var = None, None, None
        vars = result.variables

        patterns = [("s", "p", "o"), ("subject", "predicate", "object"), ("source", "relation", "target")]
        for s, p, o in patterns:
            if s in vars and o in vars:
                s_var, p_var, o_var = s, p if p in vars else None, o
                break

        if not s_var:
            s_var, o_var = vars[0], vars[-1]

        # Build nodes and links
        nodes = {}
        links = []

        for binding in result.bindings:
            source = self._extract_value(binding.get(s_var))
            target = self._extract_value(binding.get(o_var))
            relation = self._extract_value(binding.get(p_var)) if p_var else "related"

            if source not in nodes:
                nodes[source] = {"id": source, "label": self._shorten_uri(source)}
            if target not in nodes:
                nodes[target] = {"id": target, "label": self._shorten_uri(target)}

            links.append({
                "source": source,
                "target": target,
                "label": relation,
                "value": 1
            })

        return {
            "nodes": list(nodes.values()),
            "links": links
        }

    def _export_d3_chart(self, result: QueryResult) -> List[Dict[str, Any]]:
        """Export chart data for D3.js bar/line charts."""
        vars = result.variables
        x_var, y_var = vars[0], vars[1] if len(vars) > 1 else vars[0]

        data = []
        for binding in result.bindings:
            x_val = self._extract_value(binding.get(x_var))
            y_val = self._extract_value(binding.get(y_var))

            try:
                y_val = float(y_val)
            except (ValueError, TypeError):
                y_val = 0

            data.append({
                "label": x_val,
                "value": y_val
            })

        return data

    def _export_d3_pie(self, result: QueryResult) -> List[Dict[str, Any]]:
        """Export pie chart data for D3.js."""
        return self._export_d3_chart(result)

    def save(self, fig: Any, filepath: str, format: Optional[str] = None) -> None:
        """
        Save chart to file.

        Args:
            fig: Figure to save
            filepath: Output file path
            format: Export format (auto-detected from filepath if None)
        """
        if format is None:
            format = filepath.split(".")[-1]

        if self.backend == "plotly":
            if format in ["html", "htm"]:
                fig.write_html(filepath)
            else:
                fig.write_image(filepath, format=format)
        else:
            fig.savefig(filepath, format=format, dpi=self.config.dpi, bbox_inches="tight")

        logger.info(f"Saved chart to {filepath}")


class ColorSchemes:
    """
    Predefined color schemes including colorblind-friendly palettes.
    """

    # Colorblind-friendly schemes
    COLORBLIND_SAFE = ["#0173B2", "#DE8F05", "#029E73", "#CC78BC", "#CA9161", "#949494", "#ECE133"]
    DEUTERANOPIA = ["#1b9e77", "#d95f02", "#7570b3", "#e7298a", "#66a61e", "#e6ab02"]
    PROTANOPIA = ["#377eb8", "#ff7f00", "#4daf4a", "#f781bf", "#a65628", "#984ea3"]
    TRITANOPIA = ["#0173B2", "#ECE133", "#56B4E9", "#CC78BC", "#029E73"]

    # Standard schemes
    PASTEL = ["#FFDAC1", "#FFB7B2", "#FFEAA7", "#B2FEFA", "#DFE6E9"]
    VIBRANT = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A", "#98D8C8"]
    OCEAN = ["#006994", "#247BA0", "#1E96FC", "#5BC8AF", "#C2EABD"]
    FOREST = ["#2D4A2B", "#3E6837", "#508D4E", "#80AF49", "#D4E157"]

    # Biomedical schemes
    GENE_EXPRESSION = ["#053061", "#2166ac", "#4393c3", "#92c5de", "#d1e5f0", "#fddbc7", "#f4a582", "#d6604d", "#b2182b", "#67001f"]
    PATHWAYS = ["#e41a1c", "#377eb8", "#4daf4a", "#984ea3", "#ff7f00", "#ffff33", "#a65628", "#f781bf"]

    @staticmethod
    def get_scheme(name: str) -> List[str]:
        """
        Get color scheme by name.

        Args:
            name: Scheme name (case-insensitive)

        Returns:
            List of color hex codes
        """
        name_upper = name.upper().replace("-", "_").replace(" ", "_")
        return getattr(ColorSchemes, name_upper, ColorSchemes.COLORBLIND_SAFE)

    @staticmethod
    def is_colorblind_safe(name: str) -> bool:
        """
        Check if scheme is colorblind-safe.

        Args:
            name: Scheme name

        Returns:
            True if colorblind-safe
        """
        safe_schemes = ["COLORBLIND_SAFE", "DEUTERANOPIA", "PROTANOPIA", "TRITANOPIA"]
        name_upper = name.upper().replace("-", "_").replace(" ", "_")
        return name_upper in safe_schemes


class TimeSeriesDetector:
    """
    Detect and format time series data in SPARQL results.
    """

    @staticmethod
    def is_time_series(result: QueryResult) -> bool:
        """
        Detect if result contains time series data.

        Args:
            result: Query result

        Returns:
            True if data appears to be time series
        """
        import re

        # Check for time-related variable names
        time_keywords = ["year", "month", "day", "date", "time", "timestamp", "period"]
        variables = [v.lower() for v in result.variables]

        for keyword in time_keywords:
            if any(keyword in var for var in variables):
                return True

        # Check for time-like values in first binding
        if result.bindings:
            first_binding = result.bindings[0]
            for var in result.variables:
                value = str(first_binding.get(var, ""))

                # Check for year patterns
                if re.match(r'^\d{4}$', value):
                    return True

                # Check for date patterns
                if re.match(r'^\d{4}-\d{2}-\d{2}', value):
                    return True

                # Check for ISO datetime
                if re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}', value):
                    return True

        return False

    @staticmethod
    def detect_time_variable(result: QueryResult) -> Optional[str]:
        """
        Detect which variable contains time data.

        Args:
            result: Query result

        Returns:
            Name of time variable or None
        """
        import re

        time_keywords = ["year", "month", "day", "date", "time", "timestamp", "period"]

        # Check variable names
        for var in result.variables:
            if any(keyword in var.lower() for keyword in time_keywords):
                return var

        # Check values
        for var in result.variables:
            if result.bindings:
                value = str(result.bindings[0].get(var, ""))
                if re.match(r'^\d{4}(-\d{2})?(-\d{2})?', value):
                    return var

        return None


class GeographicDataDetector:
    """
    Detect geographic data in SPARQL results.
    """

    @staticmethod
    def is_geographic(result: QueryResult) -> bool:
        """
        Detect if result contains geographic data.

        Args:
            result: Query result

        Returns:
            True if data appears to be geographic
        """
        # Check for geo-related variable names
        geo_keywords = ["lat", "lon", "longitude", "latitude", "geo", "location", "place", "city", "country"]
        variables = [v.lower() for v in result.variables]

        for keyword in geo_keywords:
            if any(keyword in var for var in variables):
                return True

        # Check for WKT or GeoJSON in values
        if result.bindings:
            first_binding = result.bindings[0]
            for var in result.variables:
                value = str(first_binding.get(var, ""))
                if "POINT" in value or "POLYGON" in value or "coordinates" in value:
                    return True

        return False

    @staticmethod
    def detect_lat_lon_variables(result: QueryResult) -> Tuple[Optional[str], Optional[str]]:
        """
        Detect latitude and longitude variables.

        Args:
            result: Query result

        Returns:
            Tuple of (latitude_var, longitude_var)
        """
        lat_var, lon_var = None, None

        for var in result.variables:
            var_lower = var.lower()
            if "lat" in var_lower and not lon_var:
                lat_var = var
            elif "lon" in var_lower or "lng" in var_lower:
                lon_var = var

        return lat_var, lon_var


class VisualizationSelector:
    """
    Smart selection of appropriate visualization based on query result patterns.
    """

    @staticmethod
    def recommend_visualization(result: QueryResult) -> VisualizationType:
        """
        Recommend best visualization type for result.

        Args:
            result: Query result to analyze

        Returns:
            Recommended visualization type
        """
        # Detect time series data
        if TimeSeriesDetector.is_time_series(result):
            return VisualizationType.LINE_CHART

        # Detect if it's triple data (subject-predicate-object pattern)
        if VisualizationSelector._is_triple_data(result):
            return VisualizationType.NETWORK_GRAPH

        # Detect numeric aggregations
        numeric_vars = VisualizationSelector._count_numeric_variables(result)

        if numeric_vars == 0:
            # No numeric data - network graph for relationships
            return VisualizationType.NETWORK_GRAPH

        elif numeric_vars == 1:
            # One numeric variable - bar chart or pie chart
            if result.row_count <= 10:
                return VisualizationType.PIE_CHART
            else:
                return VisualizationType.BAR_CHART

        elif numeric_vars >= 2:
            # Two or more numeric variables - scatter plot
            return VisualizationType.SCATTER_PLOT

        # Default to bar chart
        return VisualizationType.BAR_CHART

    @staticmethod
    def _is_triple_data(result: QueryResult) -> bool:
        """
        Check if result looks like RDF triple data.

        Args:
            result: Query result

        Returns:
            True if data appears to be triples
        """
        variables = result.variables

        # Check for common triple variable patterns
        triple_patterns = [
            {"s", "p", "o"},
            {"subject", "predicate", "object"},
            {"source", "relation", "target"},
            {"from", "type", "to"},
        ]

        var_set = set(variables)
        for pattern in triple_patterns:
            if pattern.issubset(var_set):
                return True

        # Check if 3 variables with URI-like values
        if len(variables) == 3:
            sample_binding = result.bindings[0] if result.bindings else {}
            uri_count = 0

            for var in variables:
                value = str(sample_binding.get(var, ""))
                if value.startswith("http://") or value.startswith("https://"):
                    uri_count += 1

            if uri_count >= 2:
                return True

        return False

    @staticmethod
    def _count_numeric_variables(result: QueryResult) -> int:
        """
        Count number of numeric variables in result.

        Args:
            result: Query result

        Returns:
            Number of numeric variables
        """
        numeric_count = 0

        for var in result.variables:
            # Sample first few values
            sample_values = 0
            numeric_values = 0

            for binding in result.bindings[:10]:
                val = binding.get(var)
                if val:
                    sample_values += 1
                    try:
                        if isinstance(val, dict):
                            val = val.get("value", "")
                        float(str(val))
                        numeric_values += 1
                    except (ValueError, TypeError):
                        pass

            if sample_values > 0 and numeric_values / sample_values > 0.5:
                numeric_count += 1

        return numeric_count


# Convenience functions

def create_network_graph(
    result: QueryResult,
    backend: str = "plotly",
    layout: LayoutAlgorithm = LayoutAlgorithm.SPRING,
    **kwargs
) -> Any:
    """
    Create network graph visualization.

    Args:
        result: Query result
        backend: Visualization backend
        layout: Layout algorithm
        **kwargs: Additional options

    Returns:
        Network graph figure
    """
    graph_config = NetworkGraphConfig(layout=layout)
    visualizer = GraphVisualizer(backend=backend, graph_config=graph_config)
    return visualizer.create_network_graph(result, **kwargs)


def create_bar_chart(
    result: QueryResult,
    x_var: Optional[str] = None,
    y_var: Optional[str] = None,
    backend: str = "plotly",
    **kwargs
) -> Any:
    """
    Create bar chart.

    Args:
        result: Query result
        x_var: X-axis variable
        y_var: Y-axis variable
        backend: Visualization backend
        **kwargs: Additional options

    Returns:
        Bar chart figure
    """
    generator = ChartGenerator(backend=backend)
    return generator.create_bar_chart(result, x_var=x_var, y_var=y_var, **kwargs)


def create_pie_chart(
    result: QueryResult,
    labels_var: Optional[str] = None,
    values_var: Optional[str] = None,
    backend: str = "plotly",
    **kwargs
) -> Any:
    """
    Create pie chart.

    Args:
        result: Query result
        labels_var: Labels variable
        values_var: Values variable
        backend: Visualization backend
        **kwargs: Additional options

    Returns:
        Pie chart figure
    """
    generator = ChartGenerator(backend=backend)
    return generator.create_pie_chart(result, labels_var=labels_var, values_var=values_var, **kwargs)


def auto_visualize(result: QueryResult, backend: str = "plotly", **kwargs) -> Any:
    """
    Automatically select and create appropriate visualization.

    Args:
        result: Query result
        backend: Visualization backend
        **kwargs: Additional options

    Returns:
        Visualization figure
    """
    viz_type = VisualizationSelector.recommend_visualization(result)

    if viz_type == VisualizationType.NETWORK_GRAPH:
        visualizer = GraphVisualizer(backend=backend)
        return visualizer.create_network_graph(result, **kwargs)
    else:
        generator = ChartGenerator(backend=backend)
        return generator.create_visualization(result, viz_type=viz_type, **kwargs)
