"""
Unit tests for visualization module.

Tests the GraphVisualizer and ChartGenerator classes for creating
various types of visualizations from SPARQL query results.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

from ..core.types import QueryResult, QueryStatus
from ..core.exceptions import VisualizationError
from .visualizer import (
    GraphVisualizer,
    ChartGenerator,
    VisualizationSelector,
    VisualizationType,
    LayoutAlgorithm,
    VisualizationConfig,
    NetworkGraphConfig,
    ChartConfig,
    ExportFormat,
    create_network_graph,
    create_bar_chart,
    create_pie_chart,
    auto_visualize,
)


# Test Fixtures

@pytest.fixture
def triple_result():
    """Sample query result with triple structure."""
    return QueryResult(
        status=QueryStatus.SUCCESS,
        variables=["s", "p", "o"],
        bindings=[
            {
                "s": {"type": "uri", "value": "http://example.org/resource/Person1"},
                "p": {"type": "uri", "value": "http://example.org/property/knows"},
                "o": {"type": "uri", "value": "http://example.org/resource/Person2"},
            },
            {
                "s": {"type": "uri", "value": "http://example.org/resource/Person1"},
                "p": {"type": "uri", "value": "http://example.org/property/worksAt"},
                "o": {"type": "uri", "value": "http://example.org/resource/Company1"},
            },
            {
                "s": {"type": "uri", "value": "http://example.org/resource/Person2"},
                "p": {"type": "uri", "value": "http://example.org/property/knows"},
                "o": {"type": "uri", "value": "http://example.org/resource/Person3"},
            },
            {
                "s": {"type": "uri", "value": "http://example.org/resource/Person2"},
                "p": {"type": "uri", "value": "http://example.org/property/worksAt"},
                "o": {"type": "uri", "value": "http://example.org/resource/Company1"},
            },
        ],
        row_count=4,
    )


@pytest.fixture
def aggregation_result():
    """Sample query result with aggregation data."""
    return QueryResult(
        status=QueryStatus.SUCCESS,
        variables=["category", "count"],
        bindings=[
            {
                "category": {"type": "literal", "value": "Science"},
                "count": {"type": "literal", "datatype": "http://www.w3.org/2001/XMLSchema#integer", "value": "150"},
            },
            {
                "category": {"type": "literal", "value": "Technology"},
                "count": {"type": "literal", "datatype": "http://www.w3.org/2001/XMLSchema#integer", "value": "200"},
            },
            {
                "category": {"type": "literal", "value": "Engineering"},
                "count": {"type": "literal", "datatype": "http://www.w3.org/2001/XMLSchema#integer", "value": "175"},
            },
            {
                "category": {"type": "literal", "value": "Mathematics"},
                "count": {"type": "literal", "datatype": "http://www.w3.org/2001/XMLSchema#integer", "value": "125"},
            },
        ],
        row_count=4,
    )


@pytest.fixture
def time_series_result():
    """Sample query result with time series data."""
    return QueryResult(
        status=QueryStatus.SUCCESS,
        variables=["year", "value"],
        bindings=[
            {"year": {"type": "literal", "value": "2020"}, "value": {"type": "literal", "value": "100"}},
            {"year": {"type": "literal", "value": "2021"}, "value": {"type": "literal", "value": "120"}},
            {"year": {"type": "literal", "value": "2022"}, "value": {"type": "literal", "value": "145"}},
            {"year": {"type": "literal", "value": "2023"}, "value": {"type": "literal", "value": "160"}},
        ],
        row_count=4,
    )


@pytest.fixture
def scatter_result():
    """Sample query result for scatter plot."""
    return QueryResult(
        status=QueryStatus.SUCCESS,
        variables=["x", "y"],
        bindings=[
            {"x": {"type": "literal", "value": "1.5"}, "y": {"type": "literal", "value": "2.3"}},
            {"x": {"type": "literal", "value": "2.1"}, "y": {"type": "literal", "value": "3.5"}},
            {"x": {"type": "literal", "value": "3.4"}, "y": {"type": "literal", "value": "4.1"}},
            {"x": {"type": "literal", "value": "4.2"}, "y": {"type": "literal", "value": "5.8"}},
            {"x": {"type": "literal", "value": "5.1"}, "y": {"type": "literal", "value": "6.2"}},
        ],
        row_count=5,
    )


@pytest.fixture
def empty_result():
    """Empty query result."""
    return QueryResult(
        status=QueryStatus.SUCCESS,
        variables=["s", "p", "o"],
        bindings=[],
        row_count=0,
    )


@pytest.fixture
def failed_result():
    """Failed query result."""
    return QueryResult(
        status=QueryStatus.FAILED,
        error_message="Query execution failed",
        variables=[],
        bindings=[],
        row_count=0,
    )


# GraphVisualizer Tests

class TestGraphVisualizer:
    """Tests for GraphVisualizer class."""

    @patch('sparql_agent.formatting.visualizer.GraphVisualizer._create_plotly_graph')
    def test_create_network_graph_plotly(self, mock_plotly, triple_result):
        """Test creating network graph with Plotly backend."""
        mock_fig = Mock()
        mock_plotly.return_value = mock_fig

        with patch('sparql_agent.formatting.visualizer.GraphVisualizer.__init__',
                   lambda self, **kwargs: GraphVisualizer.__init__(
                       GraphVisualizer.__new__(GraphVisualizer), **kwargs)):
            visualizer = GraphVisualizer(backend="plotly")

            # Mock NetworkX
            visualizer.nx = Mock()
            visualizer.nx.DiGraph = Mock(return_value=Mock())

            fig = visualizer.create_network_graph(triple_result)

            assert fig == mock_fig
            mock_plotly.assert_called_once()

    def test_detect_triple_variables(self, triple_result):
        """Test auto-detection of triple variables."""
        try:
            visualizer = GraphVisualizer(backend="plotly")

            s_var, p_var, o_var = visualizer._detect_triple_variables(triple_result)

            assert s_var == "s"
            assert p_var == "p"
            assert o_var == "o"
        except ImportError:
            pytest.skip("NetworkX or Plotly not installed")

    def test_shorten_uri(self):
        """Test URI shortening."""
        try:
            visualizer = GraphVisualizer(backend="plotly")

            # Test URI shortening
            uri = "http://example.org/resource/LongResourceName"
            shortened = visualizer._shorten_uri(uri, max_length=30)
            assert len(shortened) <= 30

            # Test short URI
            short_uri = "http://ex.org/short"
            result = visualizer._shorten_uri(short_uri, max_length=30)
            assert result == "short"

            # Test non-URI
            non_uri = "simple_name"
            result = visualizer._shorten_uri(non_uri, max_length=30)
            assert result == "simple_name"
        except ImportError:
            pytest.skip("NetworkX or Plotly not installed")

    def test_validate_result_failed(self, failed_result):
        """Test validation of failed result."""
        try:
            visualizer = GraphVisualizer(backend="plotly")

            with pytest.raises(VisualizationError) as exc_info:
                visualizer._validate_result(failed_result)

            assert "Cannot visualize failed query result" in str(exc_info.value)
        except ImportError:
            pytest.skip("NetworkX or Plotly not installed")

    def test_validate_result_empty(self, empty_result):
        """Test validation of empty result."""
        try:
            visualizer = GraphVisualizer(backend="plotly")

            with pytest.raises(VisualizationError) as exc_info:
                visualizer._validate_result(empty_result)

            assert "Cannot visualize empty result set" in str(exc_info.value)
        except ImportError:
            pytest.skip("NetworkX or Plotly not installed")

    def test_layout_algorithms(self, triple_result):
        """Test different layout algorithms."""
        try:
            import networkx as nx

            for layout in LayoutAlgorithm:
                config = NetworkGraphConfig(layout=layout)
                visualizer = GraphVisualizer(
                    backend="plotly",
                    graph_config=config
                )

                # Create a simple graph
                graph = nx.DiGraph()
                graph.add_edge("A", "B")
                graph.add_edge("B", "C")
                graph.add_edge("C", "A")

                pos = visualizer._calculate_layout(graph)

                assert len(pos) == 3  # 3 nodes
                assert all(isinstance(coord, tuple) for coord in pos.values())
        except ImportError:
            pytest.skip("NetworkX not installed")


# ChartGenerator Tests

class TestChartGenerator:
    """Tests for ChartGenerator class."""

    def test_create_bar_chart(self, aggregation_result):
        """Test creating bar chart."""
        try:
            generator = ChartGenerator(backend="plotly")

            fig = generator.create_bar_chart(
                aggregation_result,
                x_var="category",
                y_var="count"
            )

            assert fig is not None
        except ImportError:
            pytest.skip("Plotly not installed")

    def test_create_pie_chart(self, aggregation_result):
        """Test creating pie chart."""
        try:
            generator = ChartGenerator(backend="plotly")

            fig = generator.create_pie_chart(
                aggregation_result,
                labels_var="category",
                values_var="count"
            )

            assert fig is not None
        except ImportError:
            pytest.skip("Plotly not installed")

    def test_create_line_chart(self, time_series_result):
        """Test creating line chart."""
        try:
            generator = ChartGenerator(backend="plotly")

            fig = generator.create_line_chart(
                time_series_result,
                x_var="year",
                y_var="value"
            )

            assert fig is not None
        except ImportError:
            pytest.skip("Plotly not installed")

    def test_create_scatter_plot(self, scatter_result):
        """Test creating scatter plot."""
        try:
            generator = ChartGenerator(backend="plotly")

            fig = generator.create_scatter_plot(
                scatter_result,
                x_var="x",
                y_var="y"
            )

            assert fig is not None
        except ImportError:
            pytest.skip("Plotly not installed")

    def test_create_histogram(self, scatter_result):
        """Test creating histogram."""
        try:
            generator = ChartGenerator(backend="plotly")

            fig = generator.create_histogram(
                scatter_result,
                var="x",
                bins=10
            )

            assert fig is not None
        except ImportError:
            pytest.skip("Plotly not installed")

    def test_detect_chart_variables(self, aggregation_result):
        """Test auto-detection of chart variables."""
        try:
            generator = ChartGenerator(backend="plotly")

            x_var, y_var = generator._detect_chart_variables(aggregation_result)

            assert x_var == "category"
            assert y_var == "count"
        except ImportError:
            pytest.skip("Plotly not installed")

    def test_detect_numeric_variables(self, aggregation_result):
        """Test detection of numeric variables."""
        try:
            generator = ChartGenerator(backend="plotly")

            numeric_vars = generator._detect_numeric_variables(aggregation_result)

            assert "count" in numeric_vars
        except ImportError:
            pytest.skip("Plotly not installed")

    def test_chart_config(self, aggregation_result):
        """Test chart with custom configuration."""
        try:
            chart_config = ChartConfig(
                x_axis_label="Category",
                y_axis_label="Count",
                show_values=True,
                show_grid=True
            )

            viz_config = VisualizationConfig(
                title="Test Bar Chart",
                width=800,
                height=600,
                color_scheme="viridis"
            )

            generator = ChartGenerator(
                backend="plotly",
                config=viz_config,
                chart_config=chart_config
            )

            fig = generator.create_bar_chart(
                aggregation_result,
                x_var="category",
                y_var="count"
            )

            assert fig is not None
        except ImportError:
            pytest.skip("Plotly not installed")


# VisualizationSelector Tests

class TestVisualizationSelector:
    """Tests for VisualizationSelector class."""

    def test_recommend_network_graph(self, triple_result):
        """Test recommendation for triple data."""
        viz_type = VisualizationSelector.recommend_visualization(triple_result)
        assert viz_type == VisualizationType.NETWORK_GRAPH

    def test_recommend_bar_chart(self, aggregation_result):
        """Test recommendation for aggregation data."""
        viz_type = VisualizationSelector.recommend_visualization(aggregation_result)
        assert viz_type in [VisualizationType.BAR_CHART, VisualizationType.PIE_CHART]

    def test_recommend_scatter_plot(self, scatter_result):
        """Test recommendation for scatter data."""
        viz_type = VisualizationSelector.recommend_visualization(scatter_result)
        assert viz_type == VisualizationType.SCATTER_PLOT

    def test_is_triple_data(self, triple_result, aggregation_result):
        """Test triple data detection."""
        assert VisualizationSelector._is_triple_data(triple_result) is True
        assert VisualizationSelector._is_triple_data(aggregation_result) is False

    def test_count_numeric_variables(self, aggregation_result, scatter_result):
        """Test numeric variable counting."""
        count1 = VisualizationSelector._count_numeric_variables(aggregation_result)
        assert count1 >= 1  # At least the count variable

        count2 = VisualizationSelector._count_numeric_variables(scatter_result)
        assert count2 == 2  # Both x and y are numeric


# Convenience Function Tests

class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_create_network_graph_function(self, triple_result):
        """Test create_network_graph convenience function."""
        try:
            fig = create_network_graph(
                triple_result,
                backend="plotly",
                layout=LayoutAlgorithm.SPRING
            )
            assert fig is not None
        except ImportError:
            pytest.skip("Required visualization libraries not installed")

    def test_create_bar_chart_function(self, aggregation_result):
        """Test create_bar_chart convenience function."""
        try:
            fig = create_bar_chart(
                aggregation_result,
                x_var="category",
                y_var="count",
                backend="plotly"
            )
            assert fig is not None
        except ImportError:
            pytest.skip("Plotly not installed")

    def test_create_pie_chart_function(self, aggregation_result):
        """Test create_pie_chart convenience function."""
        try:
            fig = create_pie_chart(
                aggregation_result,
                labels_var="category",
                values_var="count",
                backend="plotly"
            )
            assert fig is not None
        except ImportError:
            pytest.skip("Plotly not installed")

    def test_auto_visualize_function(self, triple_result, aggregation_result):
        """Test auto_visualize convenience function."""
        try:
            # Should create network graph for triple data
            fig1 = auto_visualize(triple_result, backend="plotly")
            assert fig1 is not None

            # Should create bar/pie chart for aggregation data
            fig2 = auto_visualize(aggregation_result, backend="plotly")
            assert fig2 is not None
        except ImportError:
            pytest.skip("Required visualization libraries not installed")


# Configuration Tests

class TestConfigurations:
    """Tests for configuration classes."""

    def test_visualization_config(self):
        """Test VisualizationConfig."""
        config = VisualizationConfig(
            width=1000,
            height=800,
            title="Test Visualization",
            show_legend=True,
            color_scheme="viridis",
            background_color="white",
            interactive=True,
            show_labels=True,
            font_size=14,
            dpi=300
        )

        assert config.width == 1000
        assert config.height == 800
        assert config.title == "Test Visualization"
        assert config.show_legend is True
        assert config.color_scheme == "viridis"
        assert config.font_size == 14
        assert config.dpi == 300

    def test_network_graph_config(self):
        """Test NetworkGraphConfig."""
        config = NetworkGraphConfig(
            layout=LayoutAlgorithm.KAMADA_KAWAI,
            node_size=50,
            node_color="#ff0000",
            edge_width=2.0,
            edge_color="#888888",
            show_node_labels=True,
            show_edge_labels=False,
            curved_edges=True,
            max_nodes=1000
        )

        assert config.layout == LayoutAlgorithm.KAMADA_KAWAI
        assert config.node_size == 50
        assert config.node_color == "#ff0000"
        assert config.edge_width == 2.0
        assert config.max_nodes == 1000

    def test_chart_config(self):
        """Test ChartConfig."""
        config = ChartConfig(
            x_axis_label="X Axis",
            y_axis_label="Y Axis",
            show_values=True,
            orientation="horizontal",
            stacked=False,
            log_scale=False,
            show_grid=True,
            marker_size=10,
            line_width=3.0
        )

        assert config.x_axis_label == "X Axis"
        assert config.y_axis_label == "Y Axis"
        assert config.show_values is True
        assert config.orientation == "horizontal"
        assert config.marker_size == 10
        assert config.line_width == 3.0


# Integration Tests

class TestIntegration:
    """Integration tests for visualization module."""

    def test_full_network_graph_workflow(self, triple_result):
        """Test complete network graph creation workflow."""
        try:
            # Create visualizer with custom config
            viz_config = VisualizationConfig(
                title="RDF Relationship Network",
                width=1200,
                height=800
            )

            graph_config = NetworkGraphConfig(
                layout=LayoutAlgorithm.SPRING,
                show_node_labels=True
            )

            visualizer = GraphVisualizer(
                backend="plotly",
                config=viz_config,
                graph_config=graph_config
            )

            # Create visualization
            fig = visualizer.create_network_graph(triple_result)

            assert fig is not None
        except ImportError:
            pytest.skip("Required visualization libraries not installed")

    def test_full_chart_workflow(self, aggregation_result):
        """Test complete chart creation workflow."""
        try:
            # Create generator with custom config
            viz_config = VisualizationConfig(
                title="Category Distribution",
                width=800,
                height=600
            )

            chart_config = ChartConfig(
                x_axis_label="Category",
                y_axis_label="Count",
                show_values=True
            )

            generator = ChartGenerator(
                backend="plotly",
                config=viz_config,
                chart_config=chart_config
            )

            # Create bar chart
            bar_fig = generator.create_bar_chart(
                aggregation_result,
                x_var="category",
                y_var="count"
            )

            # Create pie chart
            pie_fig = generator.create_pie_chart(
                aggregation_result,
                labels_var="category",
                values_var="count"
            )

            assert bar_fig is not None
            assert pie_fig is not None
        except ImportError:
            pytest.skip("Plotly not installed")

    def test_smart_visualization_selection(self, triple_result, aggregation_result):
        """Test smart visualization selection and creation."""
        try:
            # Triple data should get network graph
            fig1 = auto_visualize(triple_result)
            assert fig1 is not None

            # Aggregation data should get bar/pie chart
            fig2 = auto_visualize(aggregation_result)
            assert fig2 is not None
        except ImportError:
            pytest.skip("Required visualization libraries not installed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
