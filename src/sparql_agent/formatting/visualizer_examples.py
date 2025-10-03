"""
Usage examples for visualization module.

This module demonstrates how to use the GraphVisualizer and ChartGenerator
classes to create various types of visualizations from SPARQL query results.
"""

from sparql_agent.core.types import QueryResult, QueryStatus
from sparql_agent.formatting.visualizer import (
    GraphVisualizer,
    ChartGenerator,
    VisualizationConfig,
    NetworkGraphConfig,
    ChartConfig,
    LayoutAlgorithm,
    VisualizationType,
    VisualizationSelector,
    create_network_graph,
    create_bar_chart,
    create_pie_chart,
    auto_visualize,
)


def example_network_graph_basic():
    """
    Example 1: Basic network graph from RDF triples.

    This example shows how to create a simple network graph
    from query results containing RDF triple data.
    """
    print("=" * 80)
    print("Example 1: Basic Network Graph from RDF Triples")
    print("=" * 80)

    # Sample RDF triple data
    result = QueryResult(
        status=QueryStatus.SUCCESS,
        variables=["s", "p", "o"],
        bindings=[
            {
                "s": {"type": "uri", "value": "http://example.org/Person/Alice"},
                "p": {"type": "uri", "value": "http://example.org/knows"},
                "o": {"type": "uri", "value": "http://example.org/Person/Bob"},
            },
            {
                "s": {"type": "uri", "value": "http://example.org/Person/Alice"},
                "p": {"type": "uri", "value": "http://example.org/worksAt"},
                "o": {"type": "uri", "value": "http://example.org/Company/Acme"},
            },
            {
                "s": {"type": "uri", "value": "http://example.org/Person/Bob"},
                "p": {"type": "uri", "value": "http://example.org/knows"},
                "o": {"type": "uri", "value": "http://example.org/Person/Charlie"},
            },
            {
                "s": {"type": "uri", "value": "http://example.org/Person/Bob"},
                "p": {"type": "uri", "value": "http://example.org/worksAt"},
                "o": {"type": "uri", "value": "http://example.org/Company/Acme"},
            },
            {
                "s": {"type": "uri", "value": "http://example.org/Person/Charlie"},
                "p": {"type": "uri", "value": "http://example.org/worksAt"},
                "o": {"type": "uri", "value": "http://example.org/Company/BetaCorp"},
            },
        ],
        row_count=5,
    )

    try:
        # Create visualizer
        visualizer = GraphVisualizer(backend="plotly")

        # Create network graph
        fig = visualizer.create_network_graph(result)

        # Save as interactive HTML
        visualizer.save_html(fig, "/tmp/network_graph_basic.html")
        print("Created network graph: /tmp/network_graph_basic.html")

    except ImportError as e:
        print(f"Skipping: {e}")


def example_network_graph_advanced():
    """
    Example 2: Advanced network graph with custom configuration.

    This example demonstrates advanced configuration options including
    custom layouts, colors, and styling.
    """
    print("\n" + "=" * 80)
    print("Example 2: Advanced Network Graph with Custom Configuration")
    print("=" * 80)

    # Sample data
    result = QueryResult(
        status=QueryStatus.SUCCESS,
        variables=["subject", "predicate", "object"],
        bindings=[
            {
                "subject": {"type": "uri", "value": "http://dbpedia.org/resource/Python_(programming_language)"},
                "predicate": {"type": "uri", "value": "http://dbpedia.org/ontology/influenced"},
                "object": {"type": "uri", "value": "http://dbpedia.org/resource/JavaScript"},
            },
            {
                "subject": {"type": "uri", "value": "http://dbpedia.org/resource/Python_(programming_language)"},
                "predicate": {"type": "uri", "value": "http://dbpedia.org/ontology/influenced"},
                "object": {"type": "uri", "value": "http://dbpedia.org/resource/Ruby_(programming_language)"},
            },
            {
                "subject": {"type": "uri", "value": "http://dbpedia.org/resource/C_(programming_language)"},
                "predicate": {"type": "uri", "value": "http://dbpedia.org/ontology/influenced"},
                "object": {"type": "uri", "value": "http://dbpedia.org/resource/Python_(programming_language)"},
            },
            {
                "subject": {"type": "uri", "value": "http://dbpedia.org/resource/C_(programming_language)"},
                "predicate": {"type": "uri", "value": "http://dbpedia.org/ontology/influenced"},
                "object": {"type": "uri", "value": "http://dbpedia.org/resource/C++"},
            },
        ],
        row_count=4,
    )

    try:
        # Configure visualization
        viz_config = VisualizationConfig(
            width=1400,
            height=900,
            title="Programming Language Influence Network",
            show_legend=True,
            color_scheme="Pastel",
            background_color="#f8f9fa",
            interactive=True,
            show_labels=True,
            font_size=14,
        )

        # Configure network graph
        graph_config = NetworkGraphConfig(
            layout=LayoutAlgorithm.KAMADA_KAWAI,
            node_size=40,
            node_color="#3498db",
            edge_width=2.0,
            edge_color="#95a5a6",
            show_node_labels=True,
            show_edge_labels=False,
            curved_edges=True,
            max_nodes=100,
        )

        # Create visualizer
        visualizer = GraphVisualizer(
            backend="plotly",
            config=viz_config,
            graph_config=graph_config
        )

        # Create network graph
        fig = visualizer.create_network_graph(
            result,
            subject_var="subject",
            predicate_var="predicate",
            object_var="object"
        )

        # Save as HTML
        visualizer.save_html(fig, "/tmp/network_graph_advanced.html")
        print("Created advanced network graph: /tmp/network_graph_advanced.html")

    except ImportError as e:
        print(f"Skipping: {e}")


def example_bar_chart():
    """
    Example 3: Bar chart for categorical aggregations.

    This example shows how to create bar charts from
    aggregated SPARQL query results.
    """
    print("\n" + "=" * 80)
    print("Example 3: Bar Chart for Categorical Aggregations")
    print("=" * 80)

    # Sample aggregation data
    result = QueryResult(
        status=QueryStatus.SUCCESS,
        variables=["country", "population"],
        bindings=[
            {"country": {"type": "literal", "value": "USA"}, "population": {"type": "literal", "value": "331000000"}},
            {"country": {"type": "literal", "value": "China"}, "population": {"type": "literal", "value": "1440000000"}},
            {"country": {"type": "literal", "value": "India"}, "population": {"type": "literal", "value": "1380000000"}},
            {"country": {"type": "literal", "value": "Indonesia"}, "population": {"type": "literal", "value": "273000000"}},
            {"country": {"type": "literal", "value": "Pakistan"}, "population": {"type": "literal", "value": "220000000"}},
        ],
        row_count=5,
    )

    try:
        # Configure visualization
        viz_config = VisualizationConfig(
            title="Population by Country",
            width=900,
            height=600,
            color_scheme="Viridis",
        )

        # Configure chart
        chart_config = ChartConfig(
            x_axis_label="Country",
            y_axis_label="Population",
            show_values=True,
            show_grid=True,
        )

        # Create chart generator
        generator = ChartGenerator(
            backend="plotly",
            config=viz_config,
            chart_config=chart_config
        )

        # Create bar chart
        fig = generator.create_bar_chart(
            result,
            x_var="country",
            y_var="population"
        )

        # Save chart
        generator.save(fig, "/tmp/bar_chart.html")
        print("Created bar chart: /tmp/bar_chart.html")

    except ImportError as e:
        print(f"Skipping: {e}")


def example_pie_chart():
    """
    Example 4: Pie chart for proportions.

    This example demonstrates creating pie charts to show
    proportional distributions.
    """
    print("\n" + "=" * 80)
    print("Example 4: Pie Chart for Proportions")
    print("=" * 80)

    # Sample proportion data
    result = QueryResult(
        status=QueryStatus.SUCCESS,
        variables=["category", "count"],
        bindings=[
            {"category": {"type": "literal", "value": "Fiction"}, "count": {"type": "literal", "value": "450"}},
            {"category": {"type": "literal", "value": "Non-Fiction"}, "count": {"type": "literal", "value": "320"}},
            {"category": {"type": "literal", "value": "Science"}, "count": {"type": "literal", "value": "280"}},
            {"category": {"type": "literal", "value": "History"}, "count": {"type": "literal", "value": "190"}},
            {"category": {"type": "literal", "value": "Biography"}, "count": {"type": "literal", "value": "160"}},
        ],
        row_count=5,
    )

    try:
        # Configure visualization
        viz_config = VisualizationConfig(
            title="Book Collection by Category",
            width=800,
            height=800,
            show_legend=True,
        )

        # Create chart generator
        generator = ChartGenerator(backend="plotly", config=viz_config)

        # Create pie chart
        fig = generator.create_pie_chart(
            result,
            labels_var="category",
            values_var="count"
        )

        # Save chart
        generator.save(fig, "/tmp/pie_chart.html")
        print("Created pie chart: /tmp/pie_chart.html")

    except ImportError as e:
        print(f"Skipping: {e}")


def example_line_chart():
    """
    Example 5: Line chart for time series data.

    This example shows how to create line charts for
    visualizing trends over time.
    """
    print("\n" + "=" * 80)
    print("Example 5: Line Chart for Time Series")
    print("=" * 80)

    # Sample time series data
    result = QueryResult(
        status=QueryStatus.SUCCESS,
        variables=["year", "publications"],
        bindings=[
            {"year": {"type": "literal", "value": "2018"}, "publications": {"type": "literal", "value": "1250"}},
            {"year": {"type": "literal", "value": "2019"}, "publications": {"type": "literal", "value": "1380"}},
            {"year": {"type": "literal", "value": "2020"}, "publications": {"type": "literal", "value": "1520"}},
            {"year": {"type": "literal", "value": "2021"}, "publications": {"type": "literal", "value": "1680"}},
            {"year": {"type": "literal", "value": "2022"}, "publications": {"type": "literal", "value": "1850"}},
            {"year": {"type": "literal", "value": "2023"}, "publications": {"type": "literal", "value": "2020"}},
        ],
        row_count=6,
    )

    try:
        # Configure visualization
        viz_config = VisualizationConfig(
            title="Publications Over Time",
            width=1000,
            height=600,
        )

        # Configure chart
        chart_config = ChartConfig(
            x_axis_label="Year",
            y_axis_label="Number of Publications",
            show_grid=True,
            line_width=3.0,
            marker_size=10,
        )

        # Create chart generator
        generator = ChartGenerator(
            backend="plotly",
            config=viz_config,
            chart_config=chart_config
        )

        # Create line chart
        fig = generator.create_line_chart(
            result,
            x_var="year",
            y_var="publications"
        )

        # Save chart
        generator.save(fig, "/tmp/line_chart.html")
        print("Created line chart: /tmp/line_chart.html")

    except ImportError as e:
        print(f"Skipping: {e}")


def example_scatter_plot():
    """
    Example 6: Scatter plot for correlations.

    This example demonstrates creating scatter plots to
    visualize correlations between two numeric variables.
    """
    print("\n" + "=" * 80)
    print("Example 6: Scatter Plot for Correlations")
    print("=" * 80)

    # Sample correlation data
    result = QueryResult(
        status=QueryStatus.SUCCESS,
        variables=["citations", "h_index"],
        bindings=[
            {"citations": {"type": "literal", "value": "150"}, "h_index": {"type": "literal", "value": "12"}},
            {"citations": {"type": "literal", "value": "280"}, "h_index": {"type": "literal", "value": "18"}},
            {"citations": {"type": "literal", "value": "420"}, "h_index": {"type": "literal", "value": "24"}},
            {"citations": {"type": "literal", "value": "680"}, "h_index": {"type": "literal", "value": "32"}},
            {"citations": {"type": "literal", "value": "950"}, "h_index": {"type": "literal", "value": "41"}},
            {"citations": {"type": "literal", "value": "1200"}, "h_index": {"type": "literal", "value": "48"}},
            {"citations": {"type": "literal", "value": "1450"}, "h_index": {"type": "literal", "value": "54"}},
        ],
        row_count=7,
    )

    try:
        # Configure visualization
        viz_config = VisualizationConfig(
            title="Citations vs H-Index Correlation",
            width=900,
            height=700,
            color_scheme="Plasma",
        )

        # Configure chart
        chart_config = ChartConfig(
            x_axis_label="Total Citations",
            y_axis_label="H-Index",
            show_grid=True,
            marker_size=12,
        )

        # Create chart generator
        generator = ChartGenerator(
            backend="plotly",
            config=viz_config,
            chart_config=chart_config
        )

        # Create scatter plot
        fig = generator.create_scatter_plot(
            result,
            x_var="citations",
            y_var="h_index"
        )

        # Save chart
        generator.save(fig, "/tmp/scatter_plot.html")
        print("Created scatter plot: /tmp/scatter_plot.html")

    except ImportError as e:
        print(f"Skipping: {e}")


def example_histogram():
    """
    Example 7: Histogram for distributions.

    This example shows how to create histograms to visualize
    the distribution of a numeric variable.
    """
    print("\n" + "=" * 80)
    print("Example 7: Histogram for Distributions")
    print("=" * 80)

    # Sample distribution data
    result = QueryResult(
        status=QueryStatus.SUCCESS,
        variables=["age"],
        bindings=[
            {"age": {"type": "literal", "value": str(age)}}
            for age in [22, 25, 28, 30, 32, 35, 38, 40, 42, 45, 48, 50, 52, 55, 58, 60, 62, 65, 68, 70]
        ],
        row_count=20,
    )

    try:
        # Configure visualization
        viz_config = VisualizationConfig(
            title="Age Distribution",
            width=800,
            height=600,
            color_scheme="Blues",
        )

        # Configure chart
        chart_config = ChartConfig(
            x_axis_label="Age",
            y_axis_label="Frequency",
            show_grid=True,
        )

        # Create chart generator
        generator = ChartGenerator(
            backend="plotly",
            config=viz_config,
            chart_config=chart_config
        )

        # Create histogram
        fig = generator.create_histogram(result, var="age", bins=10)

        # Save chart
        generator.save(fig, "/tmp/histogram.html")
        print("Created histogram: /tmp/histogram.html")

    except ImportError as e:
        print(f"Skipping: {e}")


def example_auto_visualization():
    """
    Example 8: Automatic visualization selection.

    This example demonstrates the smart visualization selector
    that automatically chooses the best visualization type based
    on the data structure.
    """
    print("\n" + "=" * 80)
    print("Example 8: Automatic Visualization Selection")
    print("=" * 80)

    # Example 1: Triple data -> Network graph
    triple_result = QueryResult(
        status=QueryStatus.SUCCESS,
        variables=["s", "p", "o"],
        bindings=[
            {
                "s": {"type": "uri", "value": "http://example.org/Gene1"},
                "p": {"type": "uri", "value": "http://example.org/interactsWith"},
                "o": {"type": "uri", "value": "http://example.org/Gene2"},
            },
            {
                "s": {"type": "uri", "value": "http://example.org/Gene1"},
                "p": {"type": "uri", "value": "http://example.org/regulatedBy"},
                "o": {"type": "uri", "value": "http://example.org/Protein1"},
            },
        ],
        row_count=2,
    )

    # Example 2: Aggregation data -> Bar chart
    aggregation_result = QueryResult(
        status=QueryStatus.SUCCESS,
        variables=["species", "count"],
        bindings=[
            {"species": {"type": "literal", "value": "Homo sapiens"}, "count": {"type": "literal", "value": "5000"}},
            {"species": {"type": "literal", "value": "Mus musculus"}, "count": {"type": "literal", "value": "3500"}},
            {"species": {"type": "literal", "value": "Drosophila"}, "count": {"type": "literal", "value": "2800"}},
        ],
        row_count=3,
    )

    try:
        # Auto-visualize triple data
        viz_type1 = VisualizationSelector.recommend_visualization(triple_result)
        print(f"\nRecommended visualization for triple data: {viz_type1.value}")

        fig1 = auto_visualize(triple_result)
        print("Created automatic visualization for triple data")

        # Auto-visualize aggregation data
        viz_type2 = VisualizationSelector.recommend_visualization(aggregation_result)
        print(f"\nRecommended visualization for aggregation data: {viz_type2.value}")

        fig2 = auto_visualize(aggregation_result)
        print("Created automatic visualization for aggregation data")

    except ImportError as e:
        print(f"Skipping: {e}")


def example_convenience_functions():
    """
    Example 9: Using convenience functions.

    This example shows the simple convenience functions for
    quick visualization creation.
    """
    print("\n" + "=" * 80)
    print("Example 9: Convenience Functions")
    print("=" * 80)

    # Sample data
    result = QueryResult(
        status=QueryStatus.SUCCESS,
        variables=["topic", "articles"],
        bindings=[
            {"topic": {"type": "literal", "value": "AI"}, "articles": {"type": "literal", "value": "1200"}},
            {"topic": {"type": "literal", "value": "ML"}, "articles": {"type": "literal", "value": "980"}},
            {"topic": {"type": "literal", "value": "NLP"}, "articles": {"type": "literal", "value": "850"}},
        ],
        row_count=3,
    )

    try:
        # Quick bar chart
        fig1 = create_bar_chart(result, x_var="topic", y_var="articles")
        print("Created quick bar chart")

        # Quick pie chart
        fig2 = create_pie_chart(result, labels_var="topic", values_var="articles")
        print("Created quick pie chart")

    except ImportError as e:
        print(f"Skipping: {e}")


def example_layout_comparison():
    """
    Example 10: Comparing different layout algorithms.

    This example shows how different layout algorithms
    affect the appearance of network graphs.
    """
    print("\n" + "=" * 80)
    print("Example 10: Layout Algorithm Comparison")
    print("=" * 80)

    # Sample network data
    result = QueryResult(
        status=QueryStatus.SUCCESS,
        variables=["from", "to"],
        bindings=[
            {"from": {"type": "uri", "value": "A"}, "to": {"type": "uri", "value": "B"}},
            {"from": {"type": "uri", "value": "A"}, "to": {"type": "uri", "value": "C"}},
            {"from": {"type": "uri", "value": "B"}, "to": {"type": "uri", "value": "D"}},
            {"from": {"type": "uri", "value": "C"}, "to": {"type": "uri", "value": "D"}},
            {"from": {"type": "uri", "value": "D"}, "to": {"type": "uri", "value": "E"}},
        ],
        row_count=5,
    )

    try:
        layouts = [
            LayoutAlgorithm.SPRING,
            LayoutAlgorithm.CIRCULAR,
            LayoutAlgorithm.KAMADA_KAWAI,
        ]

        for layout in layouts:
            print(f"\nTesting {layout.value} layout...")

            graph_config = NetworkGraphConfig(layout=layout)
            visualizer = GraphVisualizer(backend="plotly", graph_config=graph_config)

            fig = visualizer.create_network_graph(
                result,
                subject_var="from",
                object_var="to"
            )

            filename = f"/tmp/network_{layout.value}.html"
            visualizer.save_html(fig, filename)
            print(f"Created: {filename}")

    except ImportError as e:
        print(f"Skipping: {e}")


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("SPARQL Agent Visualization Examples")
    print("=" * 80)

    examples = [
        example_network_graph_basic,
        example_network_graph_advanced,
        example_bar_chart,
        example_pie_chart,
        example_line_chart,
        example_scatter_plot,
        example_histogram,
        example_auto_visualization,
        example_convenience_functions,
        example_layout_comparison,
    ]

    for example_func in examples:
        try:
            example_func()
        except Exception as e:
            print(f"Error in {example_func.__name__}: {e}")

    print("\n" + "=" * 80)
    print("All examples completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
