"""
Result formatting module.

This module provides formatting and serialization of SPARQL query results.
"""

from .structured import (
    BaseFormatter,
    CSVFormatter,
    DataFrameFormatter,
    FormatDetector,
    FormatterConfig,
    JSONFormatter,
    MultiValueStrategy,
    OutputFormat,
    TSVFormatter,
    auto_format,
    format_as_csv,
    format_as_dataframe,
    format_as_json,
)

from .text import (
    ANSI,
    ColorScheme,
    MarkdownFormatter,
    PlainTextFormatter,
    TextFormatter,
    TextFormatterConfig,
    VerbosityLevel,
    format_as_markdown,
    format_as_table,
    format_as_text,
    smart_format,
)

from .visualizer import (
    ChartConfig,
    ChartGenerator,
    ColorSchemes,
    ExportFormat,
    GeographicDataDetector,
    GraphVisualizer,
    LayoutAlgorithm,
    NetworkGraphConfig,
    TimeSeriesDetector,
    VisualizationConfig,
    VisualizationSelector,
    VisualizationType,
    auto_visualize,
    create_bar_chart,
    create_network_graph,
    create_pie_chart,
)

__all__ = [
    # Structured formatters
    "BaseFormatter",
    "JSONFormatter",
    "CSVFormatter",
    "TSVFormatter",
    "DataFrameFormatter",
    # Text formatters
    "TextFormatter",
    "MarkdownFormatter",
    "PlainTextFormatter",
    # Visualizers
    "GraphVisualizer",
    "ChartGenerator",
    "VisualizationSelector",
    "ColorSchemes",
    "TimeSeriesDetector",
    "GeographicDataDetector",
    # Configuration
    "FormatterConfig",
    "TextFormatterConfig",
    "VisualizationConfig",
    "NetworkGraphConfig",
    "ChartConfig",
    "OutputFormat",
    "MultiValueStrategy",
    "VerbosityLevel",
    "ColorScheme",
    "ANSI",
    "VisualizationType",
    "ExportFormat",
    "LayoutAlgorithm",
    # Utilities
    "FormatDetector",
    "auto_format",
    "smart_format",
    # Convenience functions - structured
    "format_as_json",
    "format_as_csv",
    "format_as_dataframe",
    # Convenience functions - text
    "format_as_text",
    "format_as_markdown",
    "format_as_table",
    # Convenience functions - visualization
    "create_network_graph",
    "create_bar_chart",
    "create_pie_chart",
    "auto_visualize",
]
