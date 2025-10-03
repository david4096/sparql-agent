"""
Unit tests for text formatting module.

Tests the TextFormatter, MarkdownFormatter, and PlainTextFormatter classes.
"""

import unittest
from unittest.mock import patch

from sparql_agent.core.types import QueryResult, QueryStatus
from sparql_agent.formatting.text import (
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
from sparql_agent.core.exceptions import FormattingError


class TestTextFormatter(unittest.TestCase):
    """Test TextFormatter class."""

    def setUp(self):
        """Set up test fixtures."""
        self.simple_result = QueryResult(
            status=QueryStatus.SUCCESS,
            bindings=[
                {'name': {'type': 'literal', 'value': 'Alice'}},
                {'name': {'type': 'literal', 'value': 'Bob'}},
            ],
            variables=['name'],
            row_count=2,
            execution_time=0.1
        )

        self.multi_col_result = QueryResult(
            status=QueryStatus.SUCCESS,
            bindings=[
                {'name': {'type': 'literal', 'value': 'Alice'}, 'age': {'type': 'literal', 'value': '30'}},
                {'name': {'type': 'literal', 'value': 'Bob'}, 'age': {'type': 'literal', 'value': '25'}},
            ],
            variables=['name', 'age'],
            row_count=2,
            execution_time=0.1
        )

        self.count_result = QueryResult(
            status=QueryStatus.SUCCESS,
            bindings=[{'count': {'type': 'literal', 'value': '42'}}],
            variables=['count'],
            row_count=1,
            execution_time=0.05
        )

        self.empty_result = QueryResult(
            status=QueryStatus.SUCCESS,
            bindings=[],
            variables=['subject', 'predicate'],
            row_count=0,
            execution_time=0.01
        )

    def test_basic_formatting(self):
        """Test basic text formatting."""
        formatter = TextFormatter(verbosity=VerbosityLevel.NORMAL)
        output = formatter.format(self.simple_result)

        self.assertIn("2", output)
        self.assertIn("Alice", output)
        self.assertIn("Bob", output)

    def test_verbosity_minimal(self):
        """Test minimal verbosity output."""
        formatter = TextFormatter(verbosity=VerbosityLevel.MINIMAL)
        output = formatter.format(self.simple_result)

        self.assertIn("2", output)
        self.assertIn("Alice", output)
        # Should be very compact
        self.assertLess(len(output.split('\n')), 5)

    def test_verbosity_detailed(self):
        """Test detailed verbosity output."""
        formatter = TextFormatter(verbosity=VerbosityLevel.DETAILED)
        output = formatter.format(self.multi_col_result)

        self.assertIn("0.1", output)  # Execution time
        self.assertIn("2", output)  # Row count

    def test_query_type_detection_list(self):
        """Test detection of list queries."""
        formatter = TextFormatter()
        query_type = formatter._detect_query_type(self.simple_result)
        self.assertEqual(query_type, "list")

    def test_query_type_detection_count(self):
        """Test detection of count queries."""
        formatter = TextFormatter()
        query_type = formatter._detect_query_type(self.count_result)
        self.assertEqual(query_type, "count")

    def test_query_type_detection_tabular(self):
        """Test detection of tabular queries."""
        formatter = TextFormatter()
        query_type = formatter._detect_query_type(self.multi_col_result)
        self.assertEqual(query_type, "tabular")

    def test_empty_result(self):
        """Test handling of empty results."""
        formatter = TextFormatter()
        output = formatter.format(self.empty_result)

        self.assertIn("No results", output)

    def test_failed_query(self):
        """Test handling of failed queries."""
        failed_result = QueryResult(
            status=QueryStatus.FAILED,
            bindings=[],
            variables=[],
            row_count=0,
            error_message="Connection error"
        )

        formatter = TextFormatter()
        output = formatter.format(failed_result)

        self.assertIn("failed", output.lower())
        self.assertIn("Connection error", output)

    def test_uri_shortening(self):
        """Test URI shortening."""
        formatter = TextFormatter()

        uri = "http://example.org/resource/LongResourceName"
        short = formatter._shorten_uri(uri)

        self.assertLess(len(short), len(uri))
        self.assertIn("LongResourceName", short)

    def test_number_formatting(self):
        """Test number formatting with human-readable output."""
        config = TextFormatterConfig(human_numbers=True)
        formatter = TextFormatter(config=config)

        # Test thousands
        self.assertEqual(formatter._format_number(1500), "1,500")

        # Test millions
        self.assertEqual(formatter._format_number(1500000), "1.5M")

        # Test small numbers
        self.assertEqual(formatter._format_number(42), "42")

    def test_pluralization(self):
        """Test word pluralization."""
        formatter = TextFormatter()

        self.assertEqual(formatter._pluralize("row", 1), "row")
        self.assertEqual(formatter._pluralize("row", 2), "rows")
        self.assertEqual(formatter._pluralize("query", 5), "queries")

    def test_configuration(self):
        """Test custom configuration."""
        config = TextFormatterConfig(
            verbosity=VerbosityLevel.MINIMAL,
            show_metadata=False,
            show_summary=False,
        )

        formatter = TextFormatter(config=config)
        output = formatter.format(self.simple_result)

        # Should be minimal with no metadata
        self.assertNotIn("execution", output.lower())


class TestMarkdownFormatter(unittest.TestCase):
    """Test MarkdownFormatter class."""

    def setUp(self):
        """Set up test fixtures."""
        self.result = QueryResult(
            status=QueryStatus.SUCCESS,
            bindings=[
                {'name': {'type': 'literal', 'value': 'Alice'}, 'age': {'type': 'literal', 'value': '30'}},
                {'name': {'type': 'literal', 'value': 'Bob'}, 'age': {'type': 'literal', 'value': '25'}},
            ],
            variables=['name', 'age'],
            row_count=2,
            execution_time=0.1
        )

    def test_basic_markdown_table(self):
        """Test basic markdown table generation."""
        formatter = MarkdownFormatter()
        output = formatter.format(self.result)

        self.assertIn("##", output)  # Header
        self.assertIn("|", output)   # Table separator
        self.assertIn("Alice", output)
        self.assertIn("Bob", output)
        self.assertIn(":--", output)  # Alignment

    def test_markdown_header(self):
        """Test markdown header generation."""
        formatter = MarkdownFormatter()
        output = formatter.format(self.result)

        self.assertIn("Query Results", output)
        self.assertIn("**Rows:** 2", output)
        self.assertIn("**Columns:** 2", output)

    def test_markdown_with_uri_links(self):
        """Test URI link generation."""
        uri_result = QueryResult(
            status=QueryStatus.SUCCESS,
            bindings=[
                {'resource': {'type': 'uri', 'value': 'http://example.org/resource/Test'}},
            ],
            variables=['resource'],
            row_count=1,
            execution_time=0.05
        )

        formatter = MarkdownFormatter(generate_links=True, code_blocks_for_uris=True)
        output = formatter.format(uri_result)

        self.assertIn("[`", output)  # Link with code block
        self.assertIn("](http://", output)

    def test_markdown_without_links(self):
        """Test markdown without link generation."""
        uri_result = QueryResult(
            status=QueryStatus.SUCCESS,
            bindings=[
                {'resource': {'type': 'uri', 'value': 'http://example.org/resource/Test'}},
            ],
            variables=['resource'],
            row_count=1,
            execution_time=0.05
        )

        formatter = MarkdownFormatter(generate_links=False)
        output = formatter.format(uri_result)

        self.assertNotIn("](http://", output)

    def test_markdown_row_limit(self):
        """Test row limiting in markdown."""
        large_result = QueryResult(
            status=QueryStatus.SUCCESS,
            bindings=[{'n': {'type': 'literal', 'value': str(i)}} for i in range(100)],
            variables=['n'],
            row_count=100,
            execution_time=0.5
        )

        formatter = MarkdownFormatter(max_rows=10)
        output = formatter.format(large_result)

        self.assertIn("90 more row", output)

    def test_markdown_escape_special_chars(self):
        """Test escaping of markdown special characters."""
        formatter = MarkdownFormatter()

        # Test pipe escape (important for tables)
        escaped = formatter._escape_markdown("test|value")
        self.assertIn("\\|", escaped)

        # Test other special chars
        escaped = formatter._escape_markdown("*bold* [link] #tag")
        self.assertIn("\\*", escaped)
        self.assertIn("\\[", escaped)
        self.assertIn("\\#", escaped)

    def test_markdown_metadata(self):
        """Test metadata section in markdown."""
        formatter = MarkdownFormatter(include_metadata=True)
        output = formatter.format(self.result)

        self.assertIn("Metadata", output)
        self.assertIn("Variables", output)
        self.assertIn("Execution Time", output)

    def test_markdown_without_metadata(self):
        """Test markdown without metadata."""
        formatter = MarkdownFormatter(include_metadata=False)
        output = formatter.format(self.result)

        self.assertNotIn("### Metadata", output)


class TestPlainTextFormatter(unittest.TestCase):
    """Test PlainTextFormatter class."""

    def setUp(self):
        """Set up test fixtures."""
        self.result = QueryResult(
            status=QueryStatus.SUCCESS,
            bindings=[
                {'name': {'type': 'literal', 'value': 'Alice'}, 'age': {'type': 'literal', 'value': '30'}},
                {'name': {'type': 'literal', 'value': 'Bob'}, 'age': {'type': 'literal', 'value': '25'}},
            ],
            variables=['name', 'age'],
            row_count=2,
            execution_time=0.1
        )

    def test_basic_ascii_table(self):
        """Test basic ASCII table generation."""
        formatter = PlainTextFormatter(use_color=False, table_style="grid")
        output = formatter.format(self.result)

        self.assertIn("─", output)  # Horizontal line
        self.assertIn("│", output)  # Vertical line
        self.assertIn("Alice", output)
        self.assertIn("Bob", output)

    def test_table_style_simple(self):
        """Test simple table style."""
        formatter = PlainTextFormatter(use_color=False, table_style="simple")
        output = formatter.format(self.result)

        self.assertIn("+", output)
        self.assertIn("-", output)
        self.assertIn("|", output)

    def test_table_style_minimal(self):
        """Test minimal table style."""
        formatter = PlainTextFormatter(use_color=False, table_style="minimal")
        output = formatter.format(self.result)

        # Should have data but minimal borders
        self.assertIn("Alice", output)
        self.assertNotIn("─", output)
        self.assertNotIn("┌", output)

    def test_row_numbers(self):
        """Test row number display."""
        formatter = PlainTextFormatter(use_color=False, show_row_numbers=True)
        output = formatter.format(self.result)

        self.assertIn("#", output)
        self.assertIn("1", output)
        self.assertIn("2", output)

    def test_column_width_calculation(self):
        """Test column width calculation."""
        formatter = PlainTextFormatter(use_color=False)
        widths = formatter._calculate_column_widths(self.result)

        self.assertIn('name', widths)
        self.assertIn('age', widths)
        self.assertGreater(widths['name'], 0)

    def test_max_column_width(self):
        """Test maximum column width constraint."""
        long_result = QueryResult(
            status=QueryStatus.SUCCESS,
            bindings=[
                {'text': {'type': 'literal', 'value': 'A' * 100}},
            ],
            variables=['text'],
            row_count=1,
            execution_time=0.01
        )

        formatter = PlainTextFormatter(use_color=False, max_col_width=20)
        output = formatter.format(long_result)

        # Should be truncated
        self.assertIn("...", output)

    def test_empty_result(self):
        """Test handling of empty results."""
        empty_result = QueryResult(
            status=QueryStatus.SUCCESS,
            bindings=[],
            variables=['x'],
            row_count=0,
            execution_time=0.01
        )

        formatter = PlainTextFormatter(use_color=False)
        output = formatter.format(empty_result)

        self.assertIn("No results", output)

    def test_progress_indicator(self):
        """Test progress indicator generation."""
        formatter = PlainTextFormatter(use_color=False)

        progress = formatter.format_progress(50, 100, prefix="Test")

        self.assertIn("Test", progress)
        self.assertIn("50", progress)
        self.assertIn("100", progress)
        self.assertIn("%", progress)

    def test_color_support_detection(self):
        """Test ANSI color support detection."""
        # This will depend on the environment
        supports = ANSI.supports_color()
        self.assertIsInstance(supports, bool)

    def test_ansi_strip(self):
        """Test ANSI code stripping."""
        colored = f"{ANSI.RED}Red text{ANSI.RESET}"
        stripped = ANSI.strip(colored)

        self.assertEqual(stripped, "Red text")
        self.assertNotIn("\033", stripped)


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.result = QueryResult(
            status=QueryStatus.SUCCESS,
            bindings=[
                {'x': {'type': 'literal', 'value': '1'}},
                {'x': {'type': 'literal', 'value': '2'}},
            ],
            variables=['x'],
            row_count=2,
            execution_time=0.05
        )

    def test_format_as_text(self):
        """Test format_as_text convenience function."""
        output = format_as_text(self.result, verbosity="normal")

        self.assertIsInstance(output, str)
        self.assertIn("2", output)

    def test_format_as_markdown(self):
        """Test format_as_markdown convenience function."""
        output = format_as_markdown(self.result)

        self.assertIsInstance(output, str)
        self.assertIn("|", output)
        self.assertIn("##", output)

    def test_format_as_table(self):
        """Test format_as_table convenience function."""
        output = format_as_table(self.result, use_color=False)

        self.assertIsInstance(output, str)
        self.assertIn("1", output)
        self.assertIn("2", output)

    def test_smart_format(self):
        """Test smart_format auto-detection."""
        output = smart_format(self.result)

        self.assertIsInstance(output, str)
        self.assertTrue(len(output) > 0)

    def test_smart_format_small_result(self):
        """Test smart format with small result."""
        small_result = QueryResult(
            status=QueryStatus.SUCCESS,
            bindings=[{'count': {'type': 'literal', 'value': '42'}}],
            variables=['count'],
            row_count=1,
            execution_time=0.01
        )

        output = smart_format(small_result)

        # Should use natural language for small results
        self.assertIsInstance(output, str)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def test_missing_values(self):
        """Test handling of missing values in bindings."""
        sparse_result = QueryResult(
            status=QueryStatus.SUCCESS,
            bindings=[
                {'a': {'type': 'literal', 'value': '1'}},  # Missing 'b'
                {'b': {'type': 'literal', 'value': '2'}},  # Missing 'a'
            ],
            variables=['a', 'b'],
            row_count=2,
            execution_time=0.01
        )

        formatter = PlainTextFormatter(use_color=False)
        output = formatter.format(sparse_result)

        # Should handle missing values gracefully
        self.assertIsInstance(output, str)
        self.assertIn("1", output)
        self.assertIn("2", output)

    def test_special_characters(self):
        """Test handling of special characters."""
        special_result = QueryResult(
            status=QueryStatus.SUCCESS,
            bindings=[
                {'text': {'type': 'literal', 'value': 'Test\nNewline\tTab|Pipe'}},
            ],
            variables=['text'],
            row_count=1,
            execution_time=0.01
        )

        # Should not crash
        text_formatter = TextFormatter()
        text_output = text_formatter.format(special_result)
        self.assertIsInstance(text_output, str)

        md_formatter = MarkdownFormatter()
        md_output = md_formatter.format(special_result)
        self.assertIsInstance(md_output, str)

    def test_unicode_handling(self):
        """Test Unicode character handling."""
        unicode_result = QueryResult(
            status=QueryStatus.SUCCESS,
            bindings=[
                {'text': {'type': 'literal', 'value': 'Hello 世界 🌍'}},
            ],
            variables=['text'],
            row_count=1,
            execution_time=0.01
        )

        formatter = PlainTextFormatter(use_color=False)
        output = formatter.format(unicode_result)

        self.assertIn("世界", output)
        self.assertIn("🌍", output)

    def test_very_large_result(self):
        """Test handling of very large results."""
        large_bindings = [
            {'n': {'type': 'literal', 'value': str(i)}}
            for i in range(1000)
        ]

        large_result = QueryResult(
            status=QueryStatus.SUCCESS,
            bindings=large_bindings,
            variables=['n'],
            row_count=1000,
            execution_time=2.5
        )

        # Should not crash with large result
        formatter = TextFormatter()
        output = formatter.format(large_result)
        self.assertIsInstance(output, str)

    def test_empty_variable_names(self):
        """Test handling of empty or unusual variable names."""
        result = QueryResult(
            status=QueryStatus.SUCCESS,
            bindings=[
                {'': {'type': 'literal', 'value': 'test'}},
            ],
            variables=[''],
            row_count=1,
            execution_time=0.01
        )

        # Should handle gracefully
        formatter = TextFormatter()
        output = formatter.format(result)
        self.assertIsInstance(output, str)


def run_tests():
    """Run all tests."""
    unittest.main(argv=[''], verbosity=2, exit=False)


if __name__ == "__main__":
    run_tests()
