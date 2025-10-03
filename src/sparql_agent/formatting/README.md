# SPARQL Result Formatters

Comprehensive structured output formatters for SPARQL query results.

## Overview

This module provides formatters for converting SPARQL query results into various structured formats including JSON, CSV, TSV, and Pandas DataFrames. The formatters handle complex data types, multi-valued fields, and provide extensive configuration options.

## Features

- **JSON Formatting**: Clean JSON output with pretty-printing, metadata inclusion, and type preservation
- **CSV/TSV Formatting**: Tabular output with multi-valued field handling, Excel compatibility, and custom delimiters
- **DataFrame Integration**: Pandas DataFrame conversion with automatic type inference and analysis workflow support
- **Format Auto-Detection**: Intelligent format selection based on result structure
- **Configurable Output**: Extensive configuration options for all formatters
- **Type Preservation**: Handle URIs, literals, typed literals, and blank nodes
- **Error Handling**: Comprehensive error handling with descriptive exceptions

## Quick Start

### JSON Formatting

```python
from sparql_agent.formatting import JSONFormatter, format_as_json
from sparql_agent.core.types import QueryResult

# Using formatter class
formatter = JSONFormatter(pretty=True, indent=2)
json_output = formatter.format(query_result)

# Using convenience function
json_output = format_as_json(query_result, pretty=True, include_metadata=True)
```

### CSV Formatting

```python
from sparql_agent.formatting import CSVFormatter, format_as_csv

# Basic CSV
formatter = CSVFormatter()
csv_output = formatter.format(query_result)

# Excel-compatible CSV
formatter = CSVFormatter(excel_compatible=True)
csv_output = formatter.format(query_result)

# Custom delimiter
csv_output = format_as_csv(query_result, delimiter="|")
```

### DataFrame Formatting

```python
from sparql_agent.formatting import DataFrameFormatter, format_as_dataframe

# With type inference
formatter = DataFrameFormatter(infer_types=True)
df = formatter.format(query_result)

# With custom index
formatter = DataFrameFormatter(index_column="id")
df = formatter.format(query_result)

# Using convenience function
df = format_as_dataframe(query_result, infer_types=True)
```

### Auto-Detection

```python
from sparql_agent.formatting import auto_format, FormatDetector

# Automatically detect and apply best format
output = auto_format(query_result)

# Just detect format
format_type = FormatDetector.detect_format(query_result)
```

## Formatters

### JSONFormatter

Converts SPARQL results to clean JSON format.

**Features:**
- Pretty printing with configurable indentation
- Metadata inclusion (execution time, row count, etc.)
- Type information preservation
- Dictionary output for programmatic use

**Example:**
```python
formatter = JSONFormatter(
    pretty=True,
    indent=2,
    sort_keys=False,
    ensure_ascii=False,
    config=FormatterConfig(include_metadata=True)
)
json_string = formatter.format(query_result)
```

### CSVFormatter

Converts SPARQL results to CSV format with extensive options.

**Features:**
- Custom delimiters (comma, pipe, semicolon, etc.)
- Excel compatibility mode
- Multi-valued field handling strategies
- Header customization
- Column width limiting
- Custom null value handling

**Multi-Value Strategies:**
- `FIRST`: Take only the first value
- `LAST`: Take only the last value
- `JOIN`: Join values with a separator
- `JSON_ARRAY`: Store as JSON array string

**Example:**
```python
config = FormatterConfig(
    multi_value_strategy=MultiValueStrategy.JOIN,
    multi_value_separator=" | ",
    max_column_width=50,
    null_value="N/A"
)
formatter = CSVFormatter(
    delimiter=",",
    excel_compatible=True,
    config=config
)
csv_string = formatter.format(query_result)
```

### TSVFormatter

Convenience class for tab-separated values (TSV) format.

**Example:**
```python
formatter = TSVFormatter(include_header=True)
tsv_string = formatter.format(query_result)
```

### DataFrameFormatter

Converts SPARQL results to Pandas DataFrame for data analysis.

**Features:**
- Automatic type inference and conversion
- Custom index column selection
- Date parsing
- Categorical column support
- Metadata extraction

**Example:**
```python
formatter = DataFrameFormatter(
    infer_types=True,
    index_column="id",
    parse_dates=["created_date", "modified_date"],
    categorical_columns=["category", "status"]
)
df = formatter.format(query_result)

# With metadata
df, metadata = formatter.format_with_metadata(query_result)
```

## Configuration

### FormatterConfig

Global configuration for all formatters.

**Options:**
- `include_metadata`: Include query metadata in output
- `include_types`: Include datatype/binding type information
- `preserve_uris`: Keep full URIs vs. shortening with prefixes
- `null_value`: Value to use for null/missing data
- `multi_value_strategy`: How to handle multi-valued fields
- `multi_value_separator`: Separator for JOIN strategy
- `date_format`: Format string for datetime values
- `number_format`: Format string for numeric values
- `max_column_width`: Maximum width for text columns
- `encoding`: Character encoding for output

**Example:**
```python
config = FormatterConfig(
    include_metadata=True,
    include_types=False,
    preserve_uris=True,
    null_value="",
    multi_value_strategy=MultiValueStrategy.JOIN,
    multi_value_separator="; ",
    max_column_width=100,
    encoding="utf-8"
)
```

## Format Detection

The `FormatDetector` class automatically selects the best output format based on result characteristics:

- **Empty results** → JSON
- **Large datasets (>1000 rows)** → CSV
- **Complex nested structures** → JSON
- **Small tabular data** → CSV

**Example:**
```python
from sparql_agent.formatting import FormatDetector, OutputFormat

detected = FormatDetector.detect_format(query_result)

if detected == OutputFormat.JSON:
    output = format_as_json(query_result)
elif detected == OutputFormat.CSV:
    output = format_as_csv(query_result)
```

## Advanced Usage

### Custom Binding Extraction

```python
formatter = JSONFormatter(pretty=True)
data_dict = formatter.format_dict(query_result)

# Access bindings programmatically
for binding in data_dict['results']['bindings']:
    for var, value in binding.items():
        print(f"{var}: {value['value']} (type: {value['type']})")
```

### File Output

```python
csv_formatter = CSVFormatter(excel_compatible=True)
csv_formatter.format_to_file(query_result, "output.csv")
```

### Data Analysis Workflow

```python
# 1. Execute query
result = executor.execute(query, endpoint)

# 2. Convert to DataFrame
df = format_as_dataframe(result, infer_types=True)

# 3. Analyze
print(df.describe())
print(df.groupby('category').size())

# 4. Export
csv_output = format_as_csv(result, excel_compatible=True)
with open('results.csv', 'w') as f:
    f.write(csv_output)
```

## Error Handling

All formatters validate input and raise appropriate exceptions:

```python
from sparql_agent.core.exceptions import FormattingError, SerializationError

try:
    formatter = JSONFormatter()
    output = formatter.format(query_result)
except FormattingError as e:
    print(f"Formatting failed: {e}")
    print(f"Details: {e.details}")
except SerializationError as e:
    print(f"Serialization failed: {e}")
```

## Dependencies

**Core:**
- Python 3.8+
- Standard library only (csv, json, io, etc.)

**Optional:**
- `pandas`: Required for DataFrameFormatter
- Install with: `pip install pandas`

## Examples

See `examples_structured.py` for comprehensive examples including:
- Basic formatting for all types
- Advanced configuration options
- Multi-valued field handling
- Real-world data analysis workflows
- Error handling patterns

Run examples:
```bash
python -m sparql_agent.formatting.examples_structured
```

## Testing

Run tests:
```bash
pytest src/sparql_agent/formatting/test_structured.py -v
```

## API Reference

### Convenience Functions

#### `format_as_json(result, pretty=True, include_metadata=False) -> str`
Quick JSON formatting.

#### `format_as_csv(result, delimiter=",", excel_compatible=False) -> str`
Quick CSV formatting.

#### `format_as_dataframe(result, infer_types=True) -> pd.DataFrame`
Quick DataFrame conversion (requires pandas).

#### `auto_format(result) -> Union[str, pd.DataFrame]`
Automatically detect and apply best format.

## Related Modules

- `sparql_agent.core.types`: Core type definitions (QueryResult, etc.)
- `sparql_agent.execution.executor`: Query execution
- `sparql_agent.core.exceptions`: Exception hierarchy
