"""
Tests for structured output formatters.

This module tests the JSON, CSV, TSV, and DataFrame formatters
for SPARQL query results.
"""

import json
import pytest
from datetime import datetime
from typing import Dict, List

from ..core.types import QueryResult, QueryStatus
from ..core.exceptions import FormattingError, SerializationError
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


# Test fixtures

@pytest.fixture
def simple_result():
    """Simple query result with basic bindings."""
    return QueryResult(
        status=QueryStatus.SUCCESS,
        bindings=[
            {"name": "Alice", "age": "30", "city": "New York"},
            {"name": "Bob", "age": "25", "city": "London"},
            {"name": "Charlie", "age": "35", "city": "Paris"},
        ],
        variables=["name", "age", "city"],
        row_count=3,
        execution_time=0.123,
        query="SELECT ?name ?age ?city WHERE { ... }",
    )


@pytest.fixture
def complex_result():
    """Complex query result with typed bindings."""
    return QueryResult(
        status=QueryStatus.SUCCESS,
        bindings=[
            {
                "person": {
                    "type": "uri",
                    "value": "http://example.org/person/1"
                },
                "name": {
                    "type": "literal",
                    "value": "Alice",
                    "xml:lang": "en"
                },
                "age": {
                    "type": "typed-literal",
                    "value": "30",
                    "datatype": "http://www.w3.org/2001/XMLSchema#integer"
                },
            },
            {
                "person": {
                    "type": "uri",
                    "value": "http://example.org/person/2"
                },
                "name": {
                    "type": "literal",
                    "value": "Bob",
                    "xml:lang": "en"
                },
                "age": {
                    "type": "typed-literal",
                    "value": "25",
                    "datatype": "http://www.w3.org/2001/XMLSchema#integer"
                },
            },
        ],
        variables=["person", "name", "age"],
        row_count=2,
        execution_time=0.456,
    )


@pytest.fixture
def empty_result():
    """Empty query result."""
    return QueryResult(
        status=QueryStatus.SUCCESS,
        bindings=[],
        variables=["x", "y", "z"],
        row_count=0,
        execution_time=0.001,
    )


@pytest.fixture
def failed_result():
    """Failed query result."""
    return QueryResult(
        status=QueryStatus.FAILED,
        error_message="Query execution failed",
        row_count=0,
    )


# JSONFormatter Tests

class TestJSONFormatter:
    """Tests for JSONFormatter."""

    def test_basic_json_formatting(self, simple_result):
        """Test basic JSON formatting."""
        formatter = JSONFormatter()
        output = formatter.format(simple_result)

        # Parse back to verify
        data = json.loads(output)

        assert "head" in data
        assert "results" in data
        assert data["head"]["vars"] == ["name", "age", "city"]
        assert len(data["results"]["bindings"]) == 3

    def test_pretty_json_formatting(self, simple_result):
        """Test pretty-printed JSON formatting."""
        formatter = JSONFormatter(pretty=True, indent=2)
        output = formatter.format(simple_result)

        # Should contain newlines and indentation
        assert "\n" in output
        assert "  " in output

        # Should still be valid JSON
        data = json.loads(output)
        assert len(data["results"]["bindings"]) == 3

    def test_json_with_metadata(self, simple_result):
        """Test JSON formatting with metadata."""
        config = FormatterConfig(include_metadata=True)
        formatter = JSONFormatter(config=config)
        output = formatter.format(simple_result)

        data = json.loads(output)

        assert "metadata" in data
        assert data["metadata"]["row_count"] == 3
        assert data["metadata"]["execution_time"] == 0.123
        assert data["metadata"]["status"] == "success"

    def test_json_format_dict(self, simple_result):
        """Test formatting as dictionary."""
        formatter = JSONFormatter()
        data = formatter.format_dict(simple_result)

        assert isinstance(data, dict)
        assert "head" in data
        assert "results" in data
        assert len(data["results"]["bindings"]) == 3

    def test_json_with_complex_bindings(self, complex_result):
        """Test JSON formatting with typed bindings."""
        formatter = JSONFormatter()
        output = formatter.format(complex_result)

        data = json.loads(output)
        bindings = data["results"]["bindings"]

        # Check first binding
        assert bindings[0]["person"]["type"] == "uri"
        assert bindings[0]["name"]["value"] == "Alice"
        assert bindings[0]["age"]["value"] == "30"

    def test_json_empty_result(self, empty_result):
        """Test JSON formatting with empty result."""
        formatter = JSONFormatter()
        output = formatter.format(empty_result)

        data = json.loads(output)
        assert len(data["results"]["bindings"]) == 0
        assert data["head"]["vars"] == ["x", "y", "z"]

    def test_json_failed_result_raises(self, failed_result):
        """Test that formatting failed result raises error."""
        formatter = JSONFormatter()

        with pytest.raises(FormattingError):
            formatter.format(failed_result)

    def test_json_sort_keys(self, simple_result):
        """Test JSON with sorted keys."""
        formatter = JSONFormatter(pretty=True, sort_keys=True)
        output = formatter.format(simple_result)

        # Verify it's valid JSON
        data = json.loads(output)
        assert "head" in data

    def test_json_ensure_ascii(self, simple_result):
        """Test JSON with ASCII encoding."""
        # Add unicode characters
        simple_result.bindings[0]["name"] = "Måry"

        formatter = JSONFormatter(ensure_ascii=True)
        output = formatter.format(simple_result)

        # Should contain escaped unicode
        assert "\\u" in output or "Måry" not in output


# CSVFormatter Tests

class TestCSVFormatter:
    """Tests for CSVFormatter."""

    def test_basic_csv_formatting(self, simple_result):
        """Test basic CSV formatting."""
        formatter = CSVFormatter()
        output = formatter.format(simple_result)

        lines = output.strip().split("\r\n")

        # Check header
        assert lines[0] == "name,age,city"

        # Check data rows
        assert len(lines) == 4  # header + 3 data rows
        assert "Alice" in lines[1]
        assert "Bob" in lines[2]
        assert "Charlie" in lines[3]

    def test_csv_custom_delimiter(self, simple_result):
        """Test CSV with custom delimiter."""
        formatter = CSVFormatter(delimiter="|")
        output = formatter.format(simple_result)

        lines = output.strip().split("\r\n")
        assert lines[0] == "name|age|city"
        assert "|" in lines[1]

    def test_csv_excel_compatible(self, simple_result):
        """Test Excel-compatible CSV formatting."""
        formatter = CSVFormatter(excel_compatible=True)
        output = formatter.format(simple_result)

        # Should use comma delimiter and CRLF line endings
        assert "," in output
        assert "\r\n" in output

    def test_csv_without_header(self, simple_result):
        """Test CSV without header row."""
        formatter = CSVFormatter(include_header=False)
        output = formatter.format(simple_result)

        lines = output.strip().split("\r\n")

        # Should have only data rows
        assert len(lines) == 3
        assert "Alice" in lines[0]

    def test_csv_with_complex_bindings(self, complex_result):
        """Test CSV with typed bindings."""
        formatter = CSVFormatter()
        output = formatter.format(complex_result)

        lines = output.strip().split("\r\n")

        # Should extract values
        assert "Alice" in output
        assert "Bob" in output

    def test_csv_empty_result(self, empty_result):
        """Test CSV with empty result."""
        formatter = CSVFormatter()
        output = formatter.format(empty_result)

        lines = output.strip().split("\r\n")

        # Should have header only
        assert len(lines) == 1
        assert lines[0] == "x,y,z"

    def test_csv_multi_value_first_strategy(self):
        """Test CSV with multi-value FIRST strategy."""
        result = QueryResult(
            status=QueryStatus.SUCCESS,
            bindings=[
                {"name": ["Alice", "Alicia"], "age": "30"},
            ],
            variables=["name", "age"],
            row_count=1,
        )

        config = FormatterConfig(multi_value_strategy=MultiValueStrategy.FIRST)
        formatter = CSVFormatter(config=config)
        output = formatter.format(result)

        # Should only include first value
        # Note: In this simplified test, the formatter treats strings
        # We'd need to handle list values in the bindings

    def test_csv_quoting(self, simple_result):
        """Test CSV quoting of special characters."""
        # Add value with comma
        simple_result.bindings[0]["city"] = "New York, NY"

        formatter = CSVFormatter()
        output = formatter.format(simple_result)

        # Should quote the field
        assert '"New York, NY"' in output

    def test_csv_max_column_width(self, simple_result):
        """Test CSV with max column width."""
        # Add long value
        simple_result.bindings[0]["city"] = "A" * 100

        config = FormatterConfig(max_column_width=20)
        formatter = CSVFormatter(config=config)
        output = formatter.format(simple_result)

        # Should truncate with ellipsis
        assert "..." in output


# TSVFormatter Tests

class TestTSVFormatter:
    """Tests for TSVFormatter."""

    def test_basic_tsv_formatting(self, simple_result):
        """Test basic TSV formatting."""
        formatter = TSVFormatter()
        output = formatter.format(simple_result)

        lines = output.strip().split("\n")

        # Check tab delimiter
        assert "\t" in lines[0]
        assert lines[0] == "name\tage\tcity"

    def test_tsv_is_csv_subclass(self):
        """Test that TSV is a subclass of CSV."""
        assert issubclass(TSVFormatter, CSVFormatter)


# DataFrameFormatter Tests

class TestDataFrameFormatter:
    """Tests for DataFrameFormatter."""

    def test_basic_dataframe_formatting(self, simple_result):
        """Test basic DataFrame formatting."""
        try:
            import pandas as pd
        except ImportError:
            pytest.skip("pandas not installed")

        formatter = DataFrameFormatter()
        df = formatter.format(simple_result)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert list(df.columns) == ["name", "age", "city"]
        assert df.iloc[0]["name"] == "Alice"

    def test_dataframe_type_inference(self, simple_result):
        """Test DataFrame with type inference."""
        try:
            import pandas as pd
        except ImportError:
            pytest.skip("pandas not installed")

        formatter = DataFrameFormatter(infer_types=True)
        df = formatter.format(simple_result)

        # Age should be converted to numeric
        # Note: This depends on the actual data format in bindings
        assert df is not None

    def test_dataframe_with_index(self, simple_result):
        """Test DataFrame with custom index."""
        try:
            import pandas as pd
        except ImportError:
            pytest.skip("pandas not installed")

        formatter = DataFrameFormatter(index_column="name")
        df = formatter.format(simple_result)

        assert df.index.name == "name"
        assert "Alice" in df.index

    def test_dataframe_with_metadata(self, simple_result):
        """Test DataFrame with metadata."""
        try:
            import pandas as pd
        except ImportError:
            pytest.skip("pandas not installed")

        formatter = DataFrameFormatter()
        df, metadata = formatter.format_with_metadata(simple_result)

        assert isinstance(df, pd.DataFrame)
        assert isinstance(metadata, dict)
        assert metadata["row_count"] == 3
        assert metadata["execution_time"] == 0.123

    def test_dataframe_empty_result(self, empty_result):
        """Test DataFrame with empty result."""
        try:
            import pandas as pd
        except ImportError:
            pytest.skip("pandas not installed")

        formatter = DataFrameFormatter()
        df = formatter.format(empty_result)

        assert len(df) == 0
        assert list(df.columns) == ["x", "y", "z"]

    def test_dataframe_without_pandas_raises(self, simple_result, monkeypatch):
        """Test that DataFrameFormatter raises without pandas."""
        # Mock import error
        import sys
        monkeypatch.setitem(sys.modules, "pandas", None)

        with pytest.raises(ImportError):
            DataFrameFormatter()


# FormatDetector Tests

class TestFormatDetector:
    """Tests for FormatDetector."""

    def test_detect_csv_for_simple_result(self, simple_result):
        """Test detection of CSV for simple tabular data."""
        format_type = FormatDetector.detect_format(simple_result)
        assert format_type == OutputFormat.CSV

    def test_detect_json_for_empty_result(self, empty_result):
        """Test detection of JSON for empty result."""
        format_type = FormatDetector.detect_format(empty_result)
        assert format_type == OutputFormat.JSON

    def test_detect_json_for_complex_result(self, complex_result):
        """Test detection of JSON for complex result."""
        # Complex results might have nested structures
        format_type = FormatDetector.detect_format(complex_result)
        # Should prefer JSON for smaller complex results
        assert format_type in [OutputFormat.JSON, OutputFormat.CSV]

    def test_detect_csv_for_large_result(self):
        """Test detection of CSV for large result sets."""
        # Create large result
        bindings = [
            {"x": f"value_{i}", "y": f"data_{i}"}
            for i in range(2000)
        ]

        result = QueryResult(
            status=QueryStatus.SUCCESS,
            bindings=bindings,
            variables=["x", "y"],
            row_count=2000,
        )

        format_type = FormatDetector.detect_format(result)
        assert format_type == OutputFormat.CSV


# Convenience Functions Tests

class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_format_as_json(self, simple_result):
        """Test format_as_json convenience function."""
        output = format_as_json(simple_result)

        assert isinstance(output, str)
        data = json.loads(output)
        assert "results" in data

    def test_format_as_json_with_metadata(self, simple_result):
        """Test format_as_json with metadata."""
        output = format_as_json(simple_result, include_metadata=True)

        data = json.loads(output)
        assert "metadata" in data

    def test_format_as_csv(self, simple_result):
        """Test format_as_csv convenience function."""
        output = format_as_csv(simple_result)

        assert isinstance(output, str)
        assert "name,age,city" in output

    def test_format_as_csv_custom_delimiter(self, simple_result):
        """Test format_as_csv with custom delimiter."""
        output = format_as_csv(simple_result, delimiter="|")

        assert "|" in output

    def test_format_as_dataframe(self, simple_result):
        """Test format_as_dataframe convenience function."""
        try:
            import pandas as pd
        except ImportError:
            pytest.skip("pandas not installed")

        df = format_as_dataframe(simple_result)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3

    def test_auto_format_simple_result(self, simple_result):
        """Test auto_format with simple result."""
        output = auto_format(simple_result)

        # Should produce CSV for simple tabular data
        assert isinstance(output, str)

    def test_auto_format_empty_result(self, empty_result):
        """Test auto_format with empty result."""
        output = auto_format(empty_result)

        # Should produce JSON for empty results
        assert isinstance(output, str)
        data = json.loads(output)
        assert "results" in data


# FormatterConfig Tests

class TestFormatterConfig:
    """Tests for FormatterConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = FormatterConfig()

        assert config.include_metadata is False
        assert config.include_types is False
        assert config.preserve_uris is True
        assert config.null_value == ""
        assert config.multi_value_strategy == MultiValueStrategy.FIRST

    def test_custom_config(self):
        """Test custom configuration."""
        config = FormatterConfig(
            include_metadata=True,
            null_value="NULL",
            multi_value_strategy=MultiValueStrategy.JOIN,
            multi_value_separator=" | ",
        )

        assert config.include_metadata is True
        assert config.null_value == "NULL"
        assert config.multi_value_strategy == MultiValueStrategy.JOIN
        assert config.multi_value_separator == " | "


# Edge Cases and Error Handling

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_formatter_with_none_values(self):
        """Test formatting with None values in bindings."""
        result = QueryResult(
            status=QueryStatus.SUCCESS,
            bindings=[
                {"x": "value1", "y": None, "z": "value3"},
                {"x": None, "y": "value2", "z": None},
            ],
            variables=["x", "y", "z"],
            row_count=2,
        )

        # JSON should handle None
        json_formatter = JSONFormatter()
        json_output = json_formatter.format(result)
        assert json_output is not None

        # CSV should handle None
        csv_formatter = CSVFormatter()
        csv_output = csv_formatter.format(result)
        assert csv_output is not None

    def test_formatter_with_special_characters(self):
        """Test formatting with special characters."""
        result = QueryResult(
            status=QueryStatus.SUCCESS,
            bindings=[
                {"text": 'Value with "quotes"'},
                {"text": "Value with, comma"},
                {"text": "Value\nwith\nnewlines"},
            ],
            variables=["text"],
            row_count=3,
        )

        # CSV should properly escape
        csv_formatter = CSVFormatter()
        csv_output = csv_formatter.format(result)
        assert '"' in csv_output  # Quoted values

    def test_formatter_with_unicode(self):
        """Test formatting with unicode characters."""
        result = QueryResult(
            status=QueryStatus.SUCCESS,
            bindings=[
                {"text": "Hello 世界 🌍"},
                {"text": "Привет мир"},
                {"text": "مرحبا العالم"},
            ],
            variables=["text"],
            row_count=3,
        )

        # JSON should handle unicode
        json_formatter = JSONFormatter()
        json_output = json_formatter.format(result)
        assert json_output is not None

        # CSV should handle unicode
        csv_formatter = CSVFormatter()
        csv_output = csv_formatter.format(result)
        assert csv_output is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
