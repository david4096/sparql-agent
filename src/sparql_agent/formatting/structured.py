"""
Structured Output Formatters for SPARQL Results.

This module provides comprehensive formatters for converting SPARQL query results
into various structured formats including JSON, CSV, and Pandas DataFrames.

Features:
- Clean JSON output with nested structure support
- CSV/TSV formatting with multi-valued field handling
- Pandas DataFrame integration for data analysis
- Automatic type inference and conversion
- Configurable formatting options
- Excel-compatible CSV output
- Handle URIs, literals, and blank nodes appropriately

Example:
    >>> from sparql_agent.formatting.structured import JSONFormatter, CSVFormatter
    >>> from sparql_agent.core.types import QueryResult
    >>>
    >>> # Format as JSON
    >>> formatter = JSONFormatter(pretty=True, include_metadata=True)
    >>> json_output = formatter.format(query_result)
    >>>
    >>> # Format as CSV
    >>> csv_formatter = CSVFormatter(delimiter=',', excel_compatible=True)
    >>> csv_output = csv_formatter.format(query_result)
    >>>
    >>> # Convert to DataFrame
    >>> df_formatter = DataFrameFormatter(infer_types=True)
    >>> df = df_formatter.format(query_result)
"""

import csv
import io
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union
from urllib.parse import urlparse

from ..core.types import QueryResult, QueryStatus
from ..core.exceptions import FormattingError, SerializationError, InvalidFormatError


logger = logging.getLogger(__name__)


class OutputFormat(Enum):
    """Supported output formats."""
    JSON = "json"
    JSON_LD = "json-ld"
    CSV = "csv"
    TSV = "tsv"
    DATAFRAME = "dataframe"
    DICT = "dict"
    LIST = "list"


class MultiValueStrategy(Enum):
    """Strategies for handling multi-valued fields in tabular formats."""
    FIRST = "first"  # Take only first value
    LAST = "last"  # Take only last value
    JOIN = "join"  # Join with separator
    SEPARATE_COLUMNS = "separate_columns"  # Create separate columns (col_1, col_2, etc.)
    JSON_ARRAY = "json_array"  # Store as JSON array string


@dataclass
class FormatterConfig:
    """
    Configuration for result formatters.

    Attributes:
        include_metadata: Include query metadata in output
        include_types: Include datatype/binding type information
        preserve_uris: Keep full URIs (vs. shortening with prefixes)
        null_value: Value to use for null/missing data
        multi_value_strategy: How to handle multi-valued fields
        multi_value_separator: Separator for JOIN strategy
        date_format: Format string for datetime values
        number_format: Format string for numeric values
        max_column_width: Maximum width for text columns (CSV/TSV)
        encoding: Character encoding for output
    """
    include_metadata: bool = False
    include_types: bool = False
    preserve_uris: bool = True
    null_value: str = ""
    multi_value_strategy: MultiValueStrategy = MultiValueStrategy.FIRST
    multi_value_separator: str = "; "
    date_format: Optional[str] = None
    number_format: Optional[str] = None
    max_column_width: Optional[int] = None
    encoding: str = "utf-8"


class BaseFormatter(ABC):
    """
    Abstract base class for result formatters.
    """

    def __init__(self, config: Optional[FormatterConfig] = None):
        """
        Initialize formatter.

        Args:
            config: Formatter configuration
        """
        self.config = config or FormatterConfig()

    @abstractmethod
    def format(self, result: QueryResult, **kwargs) -> Any:
        """
        Format query result.

        Args:
            result: Query result to format
            **kwargs: Additional formatting options

        Returns:
            Formatted output

        Raises:
            FormattingError: If formatting fails
        """
        pass

    def _validate_result(self, result: QueryResult) -> None:
        """
        Validate query result before formatting.

        Args:
            result: Query result to validate

        Raises:
            FormattingError: If result is invalid
        """
        if result.status != QueryStatus.SUCCESS:
            raise FormattingError(
                f"Cannot format failed query result: {result.error_message}",
                details={"status": result.status.value}
            )

    def _extract_value(self, binding: Any, include_type: bool = False) -> Union[str, Dict[str, Any]]:
        """
        Extract value from a binding.

        Args:
            binding: Binding value (can be string, dict, or object)
            include_type: Include type information

        Returns:
            Extracted value or dict with value and type
        """
        if isinstance(binding, dict):
            # Standard SPARQL JSON result binding
            value = binding.get("value", "")
            binding_type = binding.get("type", "literal")
            datatype = binding.get("datatype")
            language = binding.get("xml:lang")

            if include_type:
                return {
                    "value": value,
                    "type": binding_type,
                    "datatype": datatype,
                    "language": language,
                }
            return value
        else:
            # Already a plain value
            if include_type:
                return {"value": str(binding), "type": "literal"}
            return str(binding) if binding is not None else self.config.null_value

    def _infer_datatype(self, value: str) -> tuple[Any, str]:
        """
        Infer datatype from string value and convert.

        Args:
            value: String value to analyze

        Returns:
            Tuple of (converted_value, datatype_name)
        """
        if not value or value == self.config.null_value:
            return None, "null"

        # Try boolean
        if value.lower() in ["true", "false"]:
            return value.lower() == "true", "boolean"

        # Try integer
        try:
            int_val = int(value)
            return int_val, "integer"
        except ValueError:
            pass

        # Try float
        try:
            float_val = float(value)
            return float_val, "float"
        except ValueError:
            pass

        # Try to detect URI
        if value.startswith("http://") or value.startswith("https://"):
            return value, "uri"

        # Default to string
        return value, "string"


class JSONFormatter(BaseFormatter):
    """
    Format SPARQL results as JSON with various configuration options.

    Supports:
    - Pretty printing with indentation
    - Nested structure preservation
    - Metadata inclusion
    - Type information
    - Compact or expanded output
    """

    def __init__(
        self,
        pretty: bool = False,
        indent: int = 2,
        sort_keys: bool = False,
        ensure_ascii: bool = False,
        config: Optional[FormatterConfig] = None,
    ):
        """
        Initialize JSON formatter.

        Args:
            pretty: Enable pretty printing
            indent: Indentation level for pretty printing
            sort_keys: Sort dictionary keys
            ensure_ascii: Escape non-ASCII characters
            config: Formatter configuration
        """
        super().__init__(config)
        self.pretty = pretty
        self.indent = indent if pretty else None
        self.sort_keys = sort_keys
        self.ensure_ascii = ensure_ascii

    def format(self, result: QueryResult, **kwargs) -> str:
        """
        Format query result as JSON string.

        Args:
            result: Query result to format
            **kwargs: Additional JSON serialization options

        Returns:
            JSON string

        Raises:
            SerializationError: If JSON serialization fails
        """
        self._validate_result(result)

        try:
            data = self._build_json_structure(result)

            return json.dumps(
                data,
                indent=self.indent,
                sort_keys=self.sort_keys,
                ensure_ascii=self.ensure_ascii,
                default=self._json_default,
                **kwargs
            )
        except Exception as e:
            raise SerializationError(
                f"Failed to serialize to JSON: {e}",
                details={"error": str(e)}
            )

    def format_dict(self, result: QueryResult) -> Dict[str, Any]:
        """
        Format query result as Python dictionary.

        Args:
            result: Query result to format

        Returns:
            Dictionary representation
        """
        self._validate_result(result)
        return self._build_json_structure(result)

    def _build_json_structure(self, result: QueryResult) -> Dict[str, Any]:
        """Build JSON structure from query result."""
        structure = {
            "head": {
                "vars": result.variables
            },
            "results": {
                "bindings": []
            }
        }

        # Add bindings
        for binding_row in result.bindings:
            binding_dict = {}
            for var, value in binding_row.items():
                if self.config.include_types and isinstance(value, dict):
                    binding_dict[var] = value
                else:
                    binding_dict[var] = {
                        "type": self._detect_type(value),
                        "value": self._extract_value(value, include_type=False)
                    }
            structure["results"]["bindings"].append(binding_dict)

        # Add metadata if requested
        if self.config.include_metadata:
            structure["metadata"] = {
                "row_count": result.row_count,
                "execution_time": result.execution_time,
                "status": result.status.value,
            }

            if result.query:
                structure["metadata"]["query"] = result.query

            if result.metadata:
                structure["metadata"].update(result.metadata)

        return structure

    def _detect_type(self, value: Any) -> str:
        """Detect binding type from value."""
        if isinstance(value, dict):
            return value.get("type", "literal")

        if isinstance(value, str):
            if value.startswith("http://") or value.startswith("https://"):
                return "uri"

        return "literal"

    def _json_default(self, obj: Any) -> Any:
        """Handle non-serializable objects."""
        if isinstance(obj, datetime):
            if self.config.date_format:
                return obj.strftime(self.config.date_format)
            return obj.isoformat()

        if isinstance(obj, set):
            return list(obj)

        if hasattr(obj, "__dict__"):
            return obj.__dict__

        return str(obj)


class CSVFormatter(BaseFormatter):
    """
    Format SPARQL results as CSV/TSV with multi-valued field handling.

    Supports:
    - Multiple delimiter options (comma, tab, pipe, etc.)
    - Multi-valued field strategies
    - Excel compatibility
    - Custom quoting and escaping
    - Header customization
    """

    def __init__(
        self,
        delimiter: str = ",",
        quotechar: str = '"',
        escapechar: Optional[str] = None,
        doublequote: bool = True,
        lineterminator: str = "\r\n",
        include_header: bool = True,
        excel_compatible: bool = False,
        config: Optional[FormatterConfig] = None,
    ):
        """
        Initialize CSV formatter.

        Args:
            delimiter: Field delimiter character
            quotechar: Quote character for fields
            escapechar: Escape character
            doublequote: Use double quotes for escaping
            lineterminator: Line terminator
            include_header: Include header row
            excel_compatible: Use Excel-compatible settings
            config: Formatter configuration
        """
        super().__init__(config)

        if excel_compatible:
            # Override settings for Excel compatibility
            self.delimiter = ","
            self.lineterminator = "\r\n"
            self.quotechar = '"'
            self.doublequote = True
            self.escapechar = None
        else:
            self.delimiter = delimiter
            self.quotechar = quotechar
            self.escapechar = escapechar
            self.doublequote = doublequote
            self.lineterminator = lineterminator

        self.include_header = include_header
        self.excel_compatible = excel_compatible

    def format(self, result: QueryResult, **kwargs) -> str:
        """
        Format query result as CSV string.

        Args:
            result: Query result to format
            **kwargs: Additional CSV writer options

        Returns:
            CSV string

        Raises:
            FormattingError: If formatting fails
        """
        self._validate_result(result)

        try:
            output = io.StringIO()

            # Determine columns
            columns = self._determine_columns(result)

            # Create CSV writer
            writer_kwargs = {
                "delimiter": self.delimiter,
                "quotechar": self.quotechar,
                "doublequote": self.doublequote,
                "lineterminator": self.lineterminator,
            }

            if self.escapechar:
                writer_kwargs["escapechar"] = self.escapechar
                writer_kwargs["doublequote"] = False

            writer_kwargs.update(kwargs)

            writer = csv.DictWriter(
                output,
                fieldnames=columns,
                extrasaction="ignore",
                restval=self.config.null_value,
                **writer_kwargs
            )

            # Write header
            if self.include_header:
                writer.writeheader()

            # Write rows
            for binding_row in result.bindings:
                processed_row = self._process_row(binding_row, columns)
                writer.writerow(processed_row)

            return output.getvalue()

        except Exception as e:
            raise FormattingError(
                f"Failed to format as CSV: {e}",
                details={"error": str(e)}
            )

    def format_to_file(self, result: QueryResult, filepath: str) -> None:
        """
        Write CSV directly to file.

        Args:
            result: Query result to format
            filepath: Output file path
        """
        csv_data = self.format(result)

        with open(filepath, "w", encoding=self.config.encoding, newline="") as f:
            f.write(csv_data)

        logger.info(f"Wrote CSV output to {filepath}")

    def _determine_columns(self, result: QueryResult) -> List[str]:
        """
        Determine column names from result.

        Args:
            result: Query result

        Returns:
            List of column names
        """
        if result.variables:
            return result.variables

        # Collect all unique keys from bindings
        columns = set()
        for binding_row in result.bindings:
            columns.update(binding_row.keys())

        return sorted(list(columns))

    def _process_row(self, binding_row: Dict[str, Any], columns: List[str]) -> Dict[str, str]:
        """
        Process a single row for CSV output.

        Args:
            binding_row: Row bindings
            columns: Column names

        Returns:
            Processed row as string dict
        """
        processed = {}

        for col in columns:
            value = binding_row.get(col)

            if value is None:
                processed[col] = self.config.null_value
                continue

            # Extract actual value
            str_value = self._extract_value(value, include_type=False)

            # Handle multi-valued fields
            if isinstance(str_value, (list, tuple)):
                str_value = self._handle_multi_value(str_value)

            # Apply column width limit if set
            if self.config.max_column_width and len(str_value) > self.config.max_column_width:
                str_value = str_value[:self.config.max_column_width] + "..."

            processed[col] = str_value

        return processed

    def _handle_multi_value(self, values: List[Any]) -> str:
        """
        Handle multi-valued field based on strategy.

        Args:
            values: List of values

        Returns:
            String representation
        """
        if not values:
            return self.config.null_value

        strategy = self.config.multi_value_strategy

        if strategy == MultiValueStrategy.FIRST:
            return str(values[0])

        elif strategy == MultiValueStrategy.LAST:
            return str(values[-1])

        elif strategy == MultiValueStrategy.JOIN:
            return self.config.multi_value_separator.join(str(v) for v in values)

        elif strategy == MultiValueStrategy.JSON_ARRAY:
            return json.dumps(values)

        else:  # Default to JOIN
            return self.config.multi_value_separator.join(str(v) for v in values)


class TSVFormatter(CSVFormatter):
    """
    Format SPARQL results as TSV (Tab-Separated Values).

    Convenience class that configures CSVFormatter for TSV output.
    """

    def __init__(
        self,
        include_header: bool = True,
        config: Optional[FormatterConfig] = None,
    ):
        """
        Initialize TSV formatter.

        Args:
            include_header: Include header row
            config: Formatter configuration
        """
        super().__init__(
            delimiter="\t",
            quotechar='"',
            lineterminator="\n",
            include_header=include_header,
            excel_compatible=False,
            config=config,
        )


class DataFrameFormatter(BaseFormatter):
    """
    Format SPARQL results as Pandas DataFrame with type inference.

    Supports:
    - Automatic type inference and conversion
    - Index management
    - Column ordering
    - Missing value handling
    - Multi-index support
    - Integration with pandas analysis workflows

    Note: Requires pandas to be installed.
    """

    def __init__(
        self,
        infer_types: bool = True,
        index_column: Optional[str] = None,
        parse_dates: Optional[List[str]] = None,
        categorical_columns: Optional[List[str]] = None,
        config: Optional[FormatterConfig] = None,
    ):
        """
        Initialize DataFrame formatter.

        Args:
            infer_types: Automatically infer and convert data types
            index_column: Column to use as DataFrame index
            parse_dates: Columns to parse as dates
            categorical_columns: Columns to treat as categorical
            config: Formatter configuration
        """
        super().__init__(config)
        self.infer_types = infer_types
        self.index_column = index_column
        self.parse_dates = parse_dates or []
        self.categorical_columns = categorical_columns or []

        # Check if pandas is available
        try:
            import pandas as pd
            self.pd = pd
        except ImportError:
            raise ImportError(
                "pandas is required for DataFrameFormatter. "
                "Install it with: pip install pandas"
            )

    def format(self, result: QueryResult, **kwargs) -> "pd.DataFrame":
        """
        Format query result as Pandas DataFrame.

        Args:
            result: Query result to format
            **kwargs: Additional DataFrame constructor options

        Returns:
            Pandas DataFrame

        Raises:
            FormattingError: If formatting fails
        """
        self._validate_result(result)

        try:
            # Build data dict
            data = self._build_data_dict(result)

            # Create DataFrame
            df = self.pd.DataFrame(data, **kwargs)

            # Apply type inference
            if self.infer_types:
                df = self._apply_type_inference(df)

            # Parse dates
            for col in self.parse_dates:
                if col in df.columns:
                    df[col] = self.pd.to_datetime(df[col], errors="coerce")

            # Convert to categorical
            for col in self.categorical_columns:
                if col in df.columns:
                    df[col] = df[col].astype("category")

            # Set index if specified
            if self.index_column and self.index_column in df.columns:
                df = df.set_index(self.index_column)

            return df

        except Exception as e:
            raise FormattingError(
                f"Failed to create DataFrame: {e}",
                details={"error": str(e)}
            )

    def _build_data_dict(self, result: QueryResult) -> Dict[str, List[Any]]:
        """
        Build data dictionary for DataFrame construction.

        Args:
            result: Query result

        Returns:
            Dictionary mapping column names to value lists
        """
        # Initialize columns
        data = {var: [] for var in result.variables}

        # Add values
        for binding_row in result.bindings:
            for var in result.variables:
                value = binding_row.get(var)

                if value is None:
                    data[var].append(None)
                else:
                    # Extract value
                    extracted = self._extract_value(value, include_type=False)
                    data[var].append(extracted)

        return data

    def _apply_type_inference(self, df: "pd.DataFrame") -> "pd.DataFrame":
        """
        Apply automatic type inference to DataFrame columns.

        Args:
            df: Input DataFrame

        Returns:
            DataFrame with inferred types
        """
        for col in df.columns:
            try:
                # Try to infer better type
                df[col] = self.pd.to_numeric(df[col], errors="ignore")

                # Try datetime conversion for string columns
                if df[col].dtype == "object":
                    # Check if looks like datetime
                    sample = df[col].dropna().head(10)
                    if len(sample) > 0:
                        try:
                            self.pd.to_datetime(sample, errors="raise")
                            df[col] = self.pd.to_datetime(df[col], errors="coerce")
                        except:
                            pass

            except Exception as e:
                logger.debug(f"Could not infer type for column {col}: {e}")
                continue

        return df

    def format_with_metadata(self, result: QueryResult) -> tuple["pd.DataFrame", Dict[str, Any]]:
        """
        Format result as DataFrame with separate metadata dict.

        Args:
            result: Query result to format

        Returns:
            Tuple of (DataFrame, metadata_dict)
        """
        df = self.format(result)

        metadata = {
            "row_count": result.row_count,
            "column_count": len(result.variables),
            "execution_time": result.execution_time,
            "variables": result.variables,
            "status": result.status.value,
        }

        if result.metadata:
            metadata.update(result.metadata)

        return df, metadata


class FormatDetector:
    """
    Automatically detect the best format for query results based on structure.
    """

    @staticmethod
    def detect_format(result: QueryResult) -> OutputFormat:
        """
        Detect appropriate output format based on result structure.

        Args:
            result: Query result to analyze

        Returns:
            Recommended output format
        """
        # Empty results - use JSON
        if result.row_count == 0:
            return OutputFormat.JSON

        # Check for nested structures
        has_nested = FormatDetector._has_nested_structure(result)

        # Large result sets benefit from CSV/DataFrame
        if result.row_count > 1000 and not has_nested:
            return OutputFormat.CSV

        # Complex nested structures - use JSON
        if has_nested:
            return OutputFormat.JSON

        # Small tabular data - CSV is fine
        if result.row_count < 100:
            return OutputFormat.CSV

        # Default to JSON
        return OutputFormat.JSON

    @staticmethod
    def _has_nested_structure(result: QueryResult) -> bool:
        """
        Check if result has nested/complex structure.

        Args:
            result: Query result to check

        Returns:
            True if result has nested structure
        """
        if not result.bindings:
            return False

        # Check first few rows
        sample_size = min(10, len(result.bindings))

        for i in range(sample_size):
            binding_row = result.bindings[i]

            for value in binding_row.values():
                if isinstance(value, (dict, list, tuple)):
                    # Check if it's just a standard binding dict
                    if isinstance(value, dict):
                        if set(value.keys()) - {"value", "type", "datatype", "xml:lang", "language"}:
                            return True
                    else:
                        return True

        return False


# Convenience functions

def format_as_json(
    result: QueryResult,
    pretty: bool = True,
    include_metadata: bool = False,
) -> str:
    """
    Format query result as JSON string.

    Args:
        result: Query result
        pretty: Enable pretty printing
        include_metadata: Include query metadata

    Returns:
        JSON string
    """
    config = FormatterConfig(include_metadata=include_metadata)
    formatter = JSONFormatter(pretty=pretty, config=config)
    return formatter.format(result)


def format_as_csv(
    result: QueryResult,
    delimiter: str = ",",
    excel_compatible: bool = False,
) -> str:
    """
    Format query result as CSV string.

    Args:
        result: Query result
        delimiter: Field delimiter
        excel_compatible: Use Excel-compatible settings

    Returns:
        CSV string
    """
    formatter = CSVFormatter(
        delimiter=delimiter,
        excel_compatible=excel_compatible,
    )
    return formatter.format(result)


def format_as_dataframe(
    result: QueryResult,
    infer_types: bool = True,
) -> Any:  # Returns pd.DataFrame
    """
    Format query result as Pandas DataFrame.

    Args:
        result: Query result
        infer_types: Automatically infer types

    Returns:
        Pandas DataFrame

    Raises:
        ImportError: If pandas is not installed
    """
    formatter = DataFrameFormatter(infer_types=infer_types)
    return formatter.format(result)


def auto_format(result: QueryResult) -> Union[str, Any]:
    """
    Automatically detect and apply best format for result.

    Args:
        result: Query result

    Returns:
        Formatted output in detected format
    """
    format_type = FormatDetector.detect_format(result)

    if format_type == OutputFormat.JSON:
        return format_as_json(result, pretty=True)
    elif format_type == OutputFormat.CSV:
        return format_as_csv(result)
    elif format_type == OutputFormat.DATAFRAME:
        try:
            return format_as_dataframe(result)
        except ImportError:
            # Fallback to CSV if pandas not available
            return format_as_csv(result)
    else:
        return format_as_json(result)
