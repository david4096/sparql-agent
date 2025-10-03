"""
Human-Readable Text Formatters for SPARQL Results.

This module provides human-friendly text formatters for presenting SPARQL query results
in natural language, markdown, and plain text formats with terminal support.

Features:
- TextFormatter: Natural language descriptions with context awareness
- MarkdownFormatter: Rich markdown tables with GitHub compatibility
- PlainTextFormatter: ASCII tables for terminal with color support
- Smart formatting based on result size and terminal capabilities
- Configurable verbosity levels
- Progress indicators and status messages

Example:
    >>> from sparql_agent.formatting.text import TextFormatter, MarkdownFormatter
    >>> from sparql_agent.core.types import QueryResult
    >>>
    >>> # Natural language output
    >>> text_formatter = TextFormatter(verbosity='normal')
    >>> description = text_formatter.format(query_result)
    >>>
    >>> # Markdown table
    >>> md_formatter = MarkdownFormatter(max_rows=100)
    >>> markdown = md_formatter.format(query_result)
    >>>
    >>> # Terminal ASCII table
    >>> plain_formatter = PlainTextFormatter(use_color=True)
    >>> table = plain_formatter.format(query_result)
"""

import logging
import os
import shutil
import textwrap
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse

from ..core.types import QueryResult, QueryStatus
from ..core.exceptions import FormattingError

logger = logging.getLogger(__name__)


class VerbosityLevel(Enum):
    """Verbosity levels for text output."""
    MINIMAL = "minimal"      # Just the data, minimal explanation
    NORMAL = "normal"        # Balanced output with context
    DETAILED = "detailed"    # Comprehensive with metadata
    DEBUG = "debug"          # Full details for debugging


class ColorScheme(Enum):
    """Color schemes for terminal output."""
    NONE = "none"           # No colors
    BASIC = "basic"         # Basic 8-color support
    EXTENDED = "extended"   # 256-color support
    TRUE_COLOR = "true"     # 24-bit true color


@dataclass
class TextFormatterConfig:
    """
    Configuration for text formatters.

    Attributes:
        verbosity: Level of detail in output
        max_width: Maximum line width (None = terminal width)
        show_metadata: Include query metadata
        show_summary: Show result summary
        human_numbers: Format large numbers with commas/abbreviations
        truncate_uris: Shorten long URIs
        uri_display: How to display URIs (full, short, label)
        indent_size: Number of spaces for indentation
        locale: Locale for number/date formatting
    """
    verbosity: VerbosityLevel = VerbosityLevel.NORMAL
    max_width: Optional[int] = None
    show_metadata: bool = True
    show_summary: bool = True
    human_numbers: bool = True
    truncate_uris: bool = True
    uri_display: str = "short"  # full, short, label
    indent_size: int = 2
    locale: str = "en_US"


class ANSI:
    """ANSI color codes for terminal output."""
    # Reset
    RESET = "\033[0m"

    # Text styles
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"

    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright foreground colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

    # Background colors
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"

    @staticmethod
    def strip(text: str) -> str:
        """Remove all ANSI codes from text."""
        import re
        return re.sub(r'\033\[[0-9;]*m', '', text)

    @staticmethod
    def supports_color() -> bool:
        """Check if terminal supports ANSI colors."""
        # Check common environment variables
        if os.getenv('NO_COLOR'):
            return False
        if os.getenv('FORCE_COLOR'):
            return True

        # Check if output is a TTY
        try:
            return os.isatty(1)  # stdout
        except:
            return False


class TextFormatter:
    """
    Format SPARQL results as natural language descriptions.

    Provides context-aware, human-readable descriptions of query results
    with configurable verbosity and query type detection.
    """

    def __init__(
        self,
        verbosity: Union[str, VerbosityLevel] = VerbosityLevel.NORMAL,
        config: Optional[TextFormatterConfig] = None
    ):
        """
        Initialize text formatter.

        Args:
            verbosity: Verbosity level (minimal, normal, detailed, debug)
            config: Formatter configuration
        """
        self.config = config or TextFormatterConfig()

        if isinstance(verbosity, str):
            self.verbosity = VerbosityLevel(verbosity)
        else:
            self.verbosity = verbosity

    def format(self, result: QueryResult, **kwargs) -> str:
        """
        Format query result as natural language text.

        Args:
            result: Query result to format
            **kwargs: Additional formatting options

        Returns:
            Human-readable text description

        Raises:
            FormattingError: If formatting fails
        """
        try:
            output_parts = []

            # Add summary if requested
            if self.config.show_summary:
                summary = self._generate_summary(result)
                output_parts.append(summary)

            # Add main content based on verbosity
            if self.verbosity != VerbosityLevel.MINIMAL:
                output_parts.append("")  # Blank line

            content = self._format_content(result)
            output_parts.append(content)

            # Add metadata if requested and verbosity allows
            if self.config.show_metadata and self.verbosity in [VerbosityLevel.DETAILED, VerbosityLevel.DEBUG]:
                metadata = self._format_metadata(result)
                if metadata:
                    output_parts.append("")
                    output_parts.append(metadata)

            return "\n".join(output_parts)

        except Exception as e:
            logger.error(f"Text formatting error: {e}")
            raise FormattingError(f"Failed to format as text: {e}")

    def _generate_summary(self, result: QueryResult) -> str:
        """Generate summary statement about the result."""
        if result.status != QueryStatus.SUCCESS:
            return f"Query failed: {result.error_message or 'Unknown error'}"

        if result.row_count == 0:
            return "No results found."

        # Detect query type from result structure
        query_type = self._detect_query_type(result)

        if self.verbosity == VerbosityLevel.MINIMAL:
            return f"Found {self._format_number(result.row_count)} result{'s' if result.row_count != 1 else ''}."

        # Generate contextual summary
        summary_parts = []

        if query_type == "count":
            summary_parts.append(f"Count result: {self._format_number(result.row_count)}")
        elif query_type == "list":
            item_word = self._pluralize("item", result.row_count)
            summary_parts.append(f"Found {self._format_number(result.row_count)} {item_word}")
        elif query_type == "single":
            summary_parts.append(f"Retrieved 1 result with {len(result.variables)} field{'s' if len(result.variables) != 1 else ''}")
        else:
            row_word = self._pluralize("row", result.row_count)
            col_word = self._pluralize("column", len(result.variables))
            summary_parts.append(
                f"Retrieved {self._format_number(result.row_count)} {row_word} "
                f"with {len(result.variables)} {col_word}"
            )

        # Add timing if available and verbosity allows
        if result.execution_time and self.verbosity in [VerbosityLevel.DETAILED, VerbosityLevel.DEBUG]:
            summary_parts.append(f"(executed in {result.execution_time:.3f}s)")

        return " ".join(summary_parts)

    def _format_content(self, result: QueryResult) -> str:
        """Format the main content based on query type."""
        if result.row_count == 0:
            return ""

        query_type = self._detect_query_type(result)

        if query_type == "count":
            return self._format_count_result(result)
        elif query_type == "single":
            return self._format_single_result(result)
        elif query_type == "list":
            return self._format_list_result(result)
        else:
            return self._format_tabular_result(result)

    def _format_count_result(self, result: QueryResult) -> str:
        """Format a count query result."""
        if result.bindings and len(result.bindings) > 0:
            first_binding = result.bindings[0]
            # Look for common count variable names
            count_vars = ['count', 'total', 'cnt', 'n']

            for var in count_vars:
                if var in first_binding:
                    value = self._extract_value(first_binding[var])
                    return f"Count: {self._format_number(int(value))}"

            # If no standard count variable, show first value
            first_var = list(first_binding.keys())[0]
            value = self._extract_value(first_binding[first_var])
            return f"{first_var}: {self._format_number(int(value))}"

        return ""

    def _format_single_result(self, result: QueryResult) -> str:
        """Format a single result record."""
        if not result.bindings:
            return ""

        record = result.bindings[0]
        lines = []

        if self.verbosity == VerbosityLevel.MINIMAL:
            # Compact single-line format
            values = []
            for var in result.variables:
                if var in record:
                    value = self._extract_value(record[var])
                    values.append(self._format_value(value))
            return ", ".join(values)

        # Detailed field-by-field format
        max_key_len = max(len(var) for var in result.variables)

        for var in result.variables:
            if var in record:
                value = self._extract_value(record[var])
                formatted_value = self._format_value(value)

                if self.verbosity == VerbosityLevel.DEBUG:
                    type_info = self._get_type_info(record[var])
                    formatted_value += f" ({type_info})"

                lines.append(f"{var.ljust(max_key_len)}: {formatted_value}")

        return "\n".join(lines)

    def _format_list_result(self, result: QueryResult) -> str:
        """Format a simple list of values."""
        lines = []

        # Use first variable as the list items
        primary_var = result.variables[0]

        for i, binding in enumerate(result.bindings, 1):
            if primary_var in binding:
                value = self._extract_value(binding[primary_var])
                formatted_value = self._format_value(value)

                if self.verbosity == VerbosityLevel.MINIMAL:
                    lines.append(formatted_value)
                else:
                    lines.append(f"{i}. {formatted_value}")

        return "\n".join(lines)

    def _format_tabular_result(self, result: QueryResult) -> str:
        """Format multi-row, multi-column results."""
        if self.verbosity == VerbosityLevel.MINIMAL:
            # Compact CSV-like format
            lines = []
            for binding in result.bindings:
                values = []
                for var in result.variables:
                    if var in binding:
                        value = self._extract_value(binding[var])
                        values.append(self._format_value(value, compact=True))
                    else:
                        values.append("")
                lines.append(", ".join(values))
            return "\n".join(lines)

        # Create a simple text table
        return self._create_text_table(result)

    def _create_text_table(self, result: QueryResult) -> str:
        """Create a simple text table representation."""
        # Calculate column widths
        col_widths = {var: len(var) for var in result.variables}

        for binding in result.bindings:
            for var in result.variables:
                if var in binding:
                    value = self._extract_value(binding[var])
                    formatted = self._format_value(value, compact=True)
                    col_widths[var] = max(col_widths[var], len(formatted))

        # Apply max width constraints
        max_col_width = 50
        for var in col_widths:
            col_widths[var] = min(col_widths[var], max_col_width)

        lines = []

        # Header
        header_parts = [var.ljust(col_widths[var]) for var in result.variables]
        lines.append(" | ".join(header_parts))

        # Separator
        sep_parts = ["-" * col_widths[var] for var in result.variables]
        lines.append("-+-".join(sep_parts))

        # Data rows
        for binding in result.bindings:
            row_parts = []
            for var in result.variables:
                if var in binding:
                    value = self._extract_value(binding[var])
                    formatted = self._format_value(value, compact=True)

                    # Truncate if needed
                    if len(formatted) > col_widths[var]:
                        formatted = formatted[:col_widths[var]-3] + "..."

                    row_parts.append(formatted.ljust(col_widths[var]))
                else:
                    row_parts.append(" " * col_widths[var])

            lines.append(" | ".join(row_parts))

        return "\n".join(lines)

    def _format_metadata(self, result: QueryResult) -> str:
        """Format query metadata."""
        lines = ["Query Metadata:"]

        if result.execution_time:
            lines.append(f"  Execution time: {result.execution_time:.3f}s")

        if result.query and self.verbosity == VerbosityLevel.DEBUG:
            lines.append(f"  Query: {result.query[:100]}...")

        if result.metadata:
            for key, value in result.metadata.items():
                lines.append(f"  {key}: {value}")

        return "\n".join(lines)

    def _detect_query_type(self, result: QueryResult) -> str:
        """Detect the type of query from result structure."""
        if result.row_count == 0:
            return "empty"

        if result.row_count == 1:
            # Check if it's a count query
            if len(result.variables) == 1:
                var_name = result.variables[0].lower()
                if any(term in var_name for term in ['count', 'total', 'cnt', 'num', 'n']):
                    return "count"
            return "single"

        # Multiple rows with single column = list
        if len(result.variables) == 1:
            return "list"

        return "tabular"

    def _extract_value(self, binding: Any) -> str:
        """Extract string value from binding."""
        if isinstance(binding, dict):
            return binding.get("value", "")
        return str(binding) if binding is not None else ""

    def _format_value(self, value: str, compact: bool = False) -> str:
        """Format a value for display."""
        if not value:
            return ""

        # Handle URIs
        if value.startswith("http://") or value.startswith("https://"):
            if self.config.truncate_uris:
                return self._shorten_uri(value)

        # Wrap long values if not compact
        if not compact and len(value) > 60:
            return value[:57] + "..."

        return value

    def _shorten_uri(self, uri: str) -> str:
        """Shorten a URI for display."""
        if self.config.uri_display == "full":
            return uri

        # Extract last segment
        parsed = urlparse(uri)
        path_parts = parsed.path.rstrip('/').split('/')

        if path_parts:
            last_segment = path_parts[-1]
            if last_segment:
                if self.config.uri_display == "label":
                    # Try to make it more readable
                    return last_segment.replace('_', ' ')
                else:  # short
                    return f".../{last_segment}"

        return uri

    def _get_type_info(self, binding: Any) -> str:
        """Get type information from binding."""
        if isinstance(binding, dict):
            binding_type = binding.get("type", "literal")
            datatype = binding.get("datatype")
            if datatype:
                return f"{binding_type}, {datatype}"
            return binding_type
        return "literal"

    def _format_number(self, num: int) -> str:
        """Format number with thousands separators if enabled."""
        if not self.config.human_numbers:
            return str(num)

        if num >= 1_000_000:
            return f"{num/1_000_000:.1f}M"
        elif num >= 1_000:
            return f"{num:,}"
        return str(num)

    def _pluralize(self, word: str, count: int) -> str:
        """Simple pluralization."""
        if count == 1:
            return word

        # Simple rules
        if word.endswith('y'):
            return word[:-1] + "ies"
        elif word.endswith('s'):
            return word + "es"
        else:
            return word + "s"


class MarkdownFormatter:
    """
    Format SPARQL results as rich Markdown with tables and links.

    Generates GitHub-compatible markdown with proper table formatting,
    code blocks for URIs, and automatic link generation.
    """

    def __init__(
        self,
        max_rows: Optional[int] = None,
        include_metadata: bool = True,
        generate_links: bool = True,
        code_blocks_for_uris: bool = True,
        table_alignment: str = "left",  # left, center, right
    ):
        """
        Initialize markdown formatter.

        Args:
            max_rows: Maximum rows to include (None = all)
            include_metadata: Include query metadata section
            generate_links: Convert URIs to clickable links
            code_blocks_for_uris: Wrap URIs in code blocks
            table_alignment: Table column alignment
        """
        self.max_rows = max_rows
        self.include_metadata = include_metadata
        self.generate_links = generate_links
        self.code_blocks_for_uris = code_blocks_for_uris
        self.table_alignment = table_alignment

    def format(self, result: QueryResult, **kwargs) -> str:
        """
        Format query result as Markdown.

        Args:
            result: Query result to format
            **kwargs: Additional formatting options

        Returns:
            Markdown string

        Raises:
            FormattingError: If formatting fails
        """
        try:
            sections = []

            # Title and summary
            sections.append(self._format_header(result))

            # Main content
            if result.row_count > 0:
                sections.append(self._format_table(result))
            else:
                sections.append("*No results found.*")

            # Metadata
            if self.include_metadata:
                metadata = self._format_metadata(result)
                if metadata:
                    sections.append(metadata)

            return "\n\n".join(sections)

        except Exception as e:
            logger.error(f"Markdown formatting error: {e}")
            raise FormattingError(f"Failed to format as markdown: {e}")

    def _format_header(self, result: QueryResult) -> str:
        """Format markdown header with summary."""
        lines = ["## Query Results"]

        if result.status != QueryStatus.SUCCESS:
            lines.append(f"\n**Status:** Failed - {result.error_message}")
            return "\n".join(lines)

        # Summary line
        summary_parts = []
        summary_parts.append(f"**Rows:** {result.row_count}")
        summary_parts.append(f"**Columns:** {len(result.variables)}")

        if result.execution_time:
            summary_parts.append(f"**Time:** {result.execution_time:.3f}s")

        lines.append("\n" + " | ".join(summary_parts))

        return "\n".join(lines)

    def _format_table(self, result: QueryResult) -> str:
        """Format results as markdown table."""
        lines = []

        # Determine rows to display
        rows_to_show = result.bindings
        truncated = False

        if self.max_rows and len(rows_to_show) > self.max_rows:
            rows_to_show = rows_to_show[:self.max_rows]
            truncated = True

        # Header row
        header_cells = [self._escape_markdown(var) for var in result.variables]
        lines.append("| " + " | ".join(header_cells) + " |")

        # Alignment row
        align_char = {
            "left": ":--",
            "center": ":-:",
            "right": "--:"
        }.get(self.table_alignment, ":--")

        lines.append("| " + " | ".join([align_char] * len(result.variables)) + " |")

        # Data rows
        for binding in rows_to_show:
            row_cells = []
            for var in result.variables:
                if var in binding:
                    value = self._extract_value(binding[var])
                    formatted = self._format_cell(value)
                    row_cells.append(formatted)
                else:
                    row_cells.append("")

            lines.append("| " + " | ".join(row_cells) + " |")

        # Truncation notice
        if truncated:
            remaining = result.row_count - self.max_rows
            lines.append("")
            lines.append(f"*... and {remaining} more row{'s' if remaining != 1 else ''}*")

        return "\n".join(lines)

    def _format_cell(self, value: str) -> str:
        """Format a table cell value."""
        if not value:
            return ""

        # Check if it's a URI
        is_uri = value.startswith("http://") or value.startswith("https://")

        if is_uri:
            if self.generate_links:
                # Extract label from URI
                label = value.split('/')[-1].split('#')[-1]
                if self.code_blocks_for_uris:
                    return f"[`{self._escape_markdown(label)}`]({value})"
                else:
                    return f"[{self._escape_markdown(label)}]({value})"
            elif self.code_blocks_for_uris:
                return f"`{self._escape_markdown(value)}`"

        # Escape markdown special characters
        return self._escape_markdown(value)

    def _format_metadata(self, result: QueryResult) -> str:
        """Format metadata section."""
        lines = ["### Metadata"]

        if result.variables:
            lines.append(f"\n**Variables:** {', '.join(f'`{v}`' for v in result.variables)}")

        if result.execution_time:
            lines.append(f"**Execution Time:** {result.execution_time:.3f} seconds")

        if result.metadata:
            for key, value in result.metadata.items():
                lines.append(f"**{key}:** {value}")

        if result.query:
            lines.append("\n**Query:**")
            lines.append("```sparql")
            lines.append(result.query)
            lines.append("```")

        return "\n".join(lines)

    def _extract_value(self, binding: Any) -> str:
        """Extract value from binding."""
        if isinstance(binding, dict):
            return binding.get("value", "")
        return str(binding) if binding is not None else ""

    def _escape_markdown(self, text: str) -> str:
        """Escape markdown special characters."""
        # Escape pipe characters for tables
        text = text.replace("|", "\\|")
        # Escape other markdown characters
        for char in ['*', '_', '[', ']', '(', ')', '#', '`', '!']:
            text = text.replace(char, '\\' + char)
        return text


class PlainTextFormatter:
    """
    Format SPARQL results as ASCII tables for terminal display.

    Provides terminal-optimized tables with:
    - Automatic column width calculation
    - Color support with ANSI codes
    - Progress indicators
    - Configurable borders and styles
    """

    def __init__(
        self,
        use_color: bool = True,
        color_scheme: Union[str, ColorScheme] = ColorScheme.BASIC,
        max_col_width: int = 50,
        min_col_width: int = 8,
        table_style: str = "grid",  # grid, simple, minimal
        show_row_numbers: bool = False,
        fit_terminal: bool = True,
    ):
        """
        Initialize plain text formatter.

        Args:
            use_color: Enable ANSI color codes
            color_scheme: Color scheme to use
            max_col_width: Maximum column width
            min_col_width: Minimum column width
            table_style: Table border style
            show_row_numbers: Show row number column
            fit_terminal: Fit table to terminal width
        """
        self.use_color = use_color and ANSI.supports_color()

        if isinstance(color_scheme, str):
            self.color_scheme = ColorScheme(color_scheme)
        else:
            self.color_scheme = color_scheme

        self.max_col_width = max_col_width
        self.min_col_width = min_col_width
        self.table_style = table_style
        self.show_row_numbers = show_row_numbers
        self.fit_terminal = fit_terminal

        # Get terminal size
        try:
            self.terminal_width, self.terminal_height = shutil.get_terminal_size()
        except:
            self.terminal_width = 80
            self.terminal_height = 24

    def format(self, result: QueryResult, **kwargs) -> str:
        """
        Format query result as ASCII table.

        Args:
            result: Query result to format
            **kwargs: Additional formatting options

        Returns:
            ASCII table string

        Raises:
            FormattingError: If formatting fails
        """
        try:
            if result.status != QueryStatus.SUCCESS:
                return self._colorize(f"Error: {result.error_message}", ANSI.RED)

            if result.row_count == 0:
                return self._colorize("No results found.", ANSI.YELLOW)

            # Build table
            table = self._build_table(result)

            # Add header/footer if there's color support
            if self.use_color:
                header = self._build_header(result)
                footer = self._build_footer(result)
                return f"{header}\n{table}\n{footer}"

            return table

        except Exception as e:
            logger.error(f"Plain text formatting error: {e}")
            raise FormattingError(f"Failed to format as plain text: {e}")

    def _build_table(self, result: QueryResult) -> str:
        """Build ASCII table."""
        # Calculate column widths
        col_widths = self._calculate_column_widths(result)

        # Determine table characters based on style
        chars = self._get_table_chars()

        lines = []

        # Top border
        if self.table_style == "grid":
            lines.append(self._build_border(col_widths, chars, "top"))

        # Header row
        header_row = self._build_header_row(result, col_widths, chars)
        lines.append(header_row)

        # Header separator
        lines.append(self._build_border(col_widths, chars, "middle"))

        # Data rows
        for i, binding in enumerate(result.bindings, 1):
            row = self._build_data_row(result, binding, i, col_widths, chars)
            lines.append(row)

        # Bottom border
        if self.table_style == "grid":
            lines.append(self._build_border(col_widths, chars, "bottom"))

        return "\n".join(lines)

    def _calculate_column_widths(self, result: QueryResult) -> Dict[str, int]:
        """Calculate optimal column widths."""
        widths = {}

        # Start with header widths
        for var in result.variables:
            widths[var] = max(self.min_col_width, len(var))

        # Check data widths
        for binding in result.bindings:
            for var in result.variables:
                if var in binding:
                    value = self._extract_value(binding[var])
                    # Remove color codes for width calculation
                    clean_value = ANSI.strip(value)
                    widths[var] = max(widths[var], min(len(clean_value), self.max_col_width))

        # Adjust for terminal width if needed
        if self.fit_terminal:
            widths = self._fit_to_terminal(widths)

        return widths

    def _fit_to_terminal(self, widths: Dict[str, int]) -> Dict[str, int]:
        """Adjust column widths to fit terminal."""
        # Calculate total width needed
        border_chars = (len(widths) + 1) * 3  # borders and padding
        total_width = sum(widths.values()) + border_chars

        if self.show_row_numbers:
            total_width += 7  # "#   | "

        # If it fits, return as-is
        if total_width <= self.terminal_width:
            return widths

        # Need to reduce widths
        excess = total_width - self.terminal_width

        # Reduce proportionally, but respect minimum
        adjusted = {}
        for var, width in widths.items():
            reduction = int(excess * (width / sum(widths.values())))
            new_width = max(self.min_col_width, width - reduction)
            adjusted[var] = new_width

        return adjusted

    def _build_header_row(self, result: QueryResult, widths: Dict[str, int], chars: Dict) -> str:
        """Build header row."""
        cells = []

        if self.show_row_numbers:
            cells.append(self._colorize("#".center(3), ANSI.CYAN + ANSI.BOLD))

        for var in result.variables:
            cell = var[:widths[var]].center(widths[var])
            cells.append(self._colorize(cell, ANSI.CYAN + ANSI.BOLD))

        return chars["left"] + chars["vsep"].join(f" {cell} " for cell in cells) + chars["right"]

    def _build_data_row(
        self,
        result: QueryResult,
        binding: Dict[str, Any],
        row_num: int,
        widths: Dict[str, int],
        chars: Dict
    ) -> str:
        """Build data row."""
        cells = []

        if self.show_row_numbers:
            num_cell = str(row_num).rjust(3)
            cells.append(self._colorize(num_cell, ANSI.BRIGHT_BLACK))

        for var in result.variables:
            if var in binding:
                value = self._extract_value(binding[var])

                # Apply color based on content type
                if self.use_color:
                    value = self._colorize_value(value)

                # Truncate if needed
                clean_value = ANSI.strip(value)
                if len(clean_value) > widths[var]:
                    # Calculate how much to keep (accounting for ANSI codes)
                    display_len = widths[var] - 3
                    truncated = clean_value[:display_len] + "..."
                    # Reapply color
                    if self.use_color:
                        truncated = self._colorize_value(truncated)
                    value = truncated
                else:
                    # Pad to width
                    padding = widths[var] - len(clean_value)
                    value = value + " " * padding

                cells.append(value)
            else:
                cells.append(self._colorize("-".center(widths[var]), ANSI.DIM))

        return chars["left"] + chars["vsep"].join(f" {cell} " for cell in cells) + chars["right"]

    def _build_border(self, widths: Dict[str, int], chars: Dict, position: str) -> str:
        """Build horizontal border."""
        segments = []

        if self.show_row_numbers:
            segments.append(chars["hsep"] * 5)

        for var in widths:
            segments.append(chars["hsep"] * (widths[var] + 2))

        if position == "top":
            return chars["tl"] + chars["tsep"].join(segments) + chars["tr"]
        elif position == "middle":
            return chars["ml"] + chars["msep"].join(segments) + chars["mr"]
        else:  # bottom
            return chars["bl"] + chars["bsep"].join(segments) + chars["br"]

    def _get_table_chars(self) -> Dict[str, str]:
        """Get table border characters based on style."""
        if self.table_style == "grid":
            return {
                "hsep": "─", "vsep": "│",
                "tl": "┌", "tr": "┐", "bl": "└", "br": "┘",
                "ml": "├", "mr": "┤",
                "tsep": "┬", "bsep": "┴", "msep": "┼",
                "left": "│", "right": "│"
            }
        elif self.table_style == "simple":
            return {
                "hsep": "-", "vsep": "|",
                "tl": "+", "tr": "+", "bl": "+", "br": "+",
                "ml": "+", "mr": "+",
                "tsep": "+", "bsep": "+", "msep": "+",
                "left": "|", "right": "|"
            }
        else:  # minimal
            return {
                "hsep": " ", "vsep": " ",
                "tl": "", "tr": "", "bl": "", "br": "",
                "ml": "", "mr": "",
                "tsep": "", "bsep": "", "msep": "",
                "left": " ", "right": " "
            }

    def _build_header(self, result: QueryResult) -> str:
        """Build header with summary."""
        parts = []
        parts.append(self._colorize("SPARQL Results", ANSI.BOLD + ANSI.GREEN))
        parts.append(self._colorize(f"({result.row_count} rows)", ANSI.DIM))

        if result.execution_time:
            parts.append(self._colorize(f"[{result.execution_time:.3f}s]", ANSI.YELLOW))

        return " ".join(parts)

    def _build_footer(self, result: QueryResult) -> str:
        """Build footer with metadata."""
        if result.row_count > 10:
            return self._colorize(f"Showing {result.row_count} rows", ANSI.DIM)
        return ""

    def _extract_value(self, binding: Any) -> str:
        """Extract value from binding."""
        if isinstance(binding, dict):
            return binding.get("value", "")
        return str(binding) if binding is not None else ""

    def _colorize(self, text: str, color_code: str) -> str:
        """Apply color to text if colors are enabled."""
        if not self.use_color:
            return text
        return f"{color_code}{text}{ANSI.RESET}"

    def _colorize_value(self, value: str) -> str:
        """Apply appropriate color based on value type."""
        if not self.use_color:
            return value

        # URI - blue
        if value.startswith("http://") or value.startswith("https://"):
            return self._colorize(value, ANSI.BLUE)

        # Number - green
        try:
            float(value)
            return self._colorize(value, ANSI.GREEN)
        except:
            pass

        # Boolean - yellow
        if value.lower() in ["true", "false"]:
            return self._colorize(value, ANSI.YELLOW)

        # Default - no color
        return value

    def format_progress(self, current: int, total: int, prefix: str = "Progress") -> str:
        """
        Format a progress indicator.

        Args:
            current: Current progress value
            total: Total value
            prefix: Prefix text

        Returns:
            Progress bar string
        """
        if total == 0:
            return ""

        percentage = (current / total) * 100
        bar_width = min(50, self.terminal_width - 30)
        filled = int(bar_width * current / total)

        bar = "█" * filled + "░" * (bar_width - filled)

        if self.use_color:
            bar = self._colorize(bar, ANSI.GREEN)
            prefix = self._colorize(prefix, ANSI.CYAN)

        return f"{prefix}: {bar} {percentage:.1f}% ({current}/{total})"


# Convenience functions

def format_as_text(
    result: QueryResult,
    verbosity: str = "normal",
    show_metadata: bool = True,
) -> str:
    """
    Format query result as natural language text.

    Args:
        result: Query result
        verbosity: Verbosity level (minimal, normal, detailed, debug)
        show_metadata: Include metadata

    Returns:
        Text string
    """
    config = TextFormatterConfig(
        verbosity=VerbosityLevel(verbosity),
        show_metadata=show_metadata
    )
    formatter = TextFormatter(config=config)
    return formatter.format(result)


def format_as_markdown(
    result: QueryResult,
    max_rows: Optional[int] = None,
    include_metadata: bool = True,
) -> str:
    """
    Format query result as Markdown.

    Args:
        result: Query result
        max_rows: Maximum rows to include
        include_metadata: Include metadata section

    Returns:
        Markdown string
    """
    formatter = MarkdownFormatter(
        max_rows=max_rows,
        include_metadata=include_metadata
    )
    return formatter.format(result)


def format_as_table(
    result: QueryResult,
    use_color: bool = True,
    table_style: str = "grid",
) -> str:
    """
    Format query result as ASCII table.

    Args:
        result: Query result
        use_color: Enable color support
        table_style: Table style (grid, simple, minimal)

    Returns:
        ASCII table string
    """
    formatter = PlainTextFormatter(
        use_color=use_color,
        table_style=table_style
    )
    return formatter.format(result)


def smart_format(result: QueryResult, force_color: bool = False) -> str:
    """
    Automatically choose best text format based on result size and terminal.

    Args:
        result: Query result
        force_color: Force color output even if terminal doesn't support it

    Returns:
        Formatted string in appropriate format
    """
    # For very small results, use natural language
    if result.row_count <= 3 and len(result.variables) <= 3:
        return format_as_text(result, verbosity="normal")

    # For larger results, use table if terminal is wide enough
    try:
        terminal_width, _ = shutil.get_terminal_size()

        # Estimate needed width
        estimated_width = len(result.variables) * 15 + 10

        if terminal_width >= estimated_width:
            return format_as_table(result, use_color=force_color or ANSI.supports_color())
        else:
            # Terminal too narrow, use text format
            return format_as_text(result, verbosity="minimal")
    except:
        # Can't determine terminal size, use text
        return format_as_text(result, verbosity="normal")
