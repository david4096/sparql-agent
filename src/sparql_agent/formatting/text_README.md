# Human-Readable Text Formatters

This module provides comprehensive text formatting capabilities for SPARQL query results, making them human-friendly and readable across different output contexts.

## Overview

The text formatting module includes three main formatter classes:

1. **TextFormatter** - Natural language descriptions with context-aware formatting
2. **MarkdownFormatter** - Rich markdown tables with GitHub compatibility
3. **PlainTextFormatter** - ASCII tables optimized for terminal display

## Features

- **Natural Language Output**: Generate human-readable descriptions of query results
- **Context-Aware Formatting**: Automatically adapt formatting based on query type (count, list, table)
- **Configurable Verbosity**: Control detail level from minimal to debug
- **Markdown Tables**: Create GitHub-compatible markdown with clickable links
- **Terminal Tables**: Beautiful ASCII tables with Unicode box-drawing characters
- **Color Support**: ANSI color codes for terminal output with automatic detection
- **Smart Formatting**: Automatically choose best format based on result size and terminal capabilities
- **Progress Indicators**: Display progress bars for long-running operations
- **URI Handling**: Intelligent URI shortening and display options
- **Edge Case Handling**: Robust handling of missing values, special characters, and large datasets

## Installation

The text formatters are part of the `sparql_agent.formatting` module:

```python
from sparql_agent.formatting import (
    TextFormatter,
    MarkdownFormatter,
    PlainTextFormatter,
    format_as_text,
    format_as_markdown,
    format_as_table,
    smart_format,
)
```

## Quick Start

### Basic Usage

```python
from sparql_agent.core.types import QueryResult, QueryStatus
from sparql_agent.formatting import TextFormatter

# Assume you have a QueryResult
result = QueryResult(
    status=QueryStatus.SUCCESS,
    bindings=[
        {'name': {'value': 'Alice'}, 'age': {'value': '30'}},
        {'name': {'value': 'Bob'}, 'age': {'value': '25'}},
    ],
    variables=['name', 'age'],
    row_count=2,
    execution_time=0.123
)

# Create natural language description
formatter = TextFormatter()
print(formatter.format(result))
```

Output:
```
Retrieved 2 rows with 2 columns

name  | age
------+----
Alice | 30
Bob   | 25
```

### Markdown Output

```python
from sparql_agent.formatting import MarkdownFormatter

formatter = MarkdownFormatter()
print(formatter.format(result))
```

Output:
```markdown
## Query Results

**Rows:** 2 | **Columns:** 2 | **Time:** 0.123s

| name | age |
| :-- | :-- |
| Alice | 30 |
| Bob | 25 |

### Metadata

**Variables:** `name`, `age`
**Execution Time:** 0.123 seconds
```

### ASCII Table

```python
from sparql_agent.formatting import PlainTextFormatter

formatter = PlainTextFormatter(use_color=False, table_style='grid')
print(formatter.format(result))
```

Output:
```
┌────────┬──────┐
│  name  │ age  │
├────────┼──────┤
│ Alice  │ 30   │
│ Bob    │ 25   │
└────────┴──────┘
```

## TextFormatter

The `TextFormatter` creates natural language descriptions of query results with context awareness.

### Verbosity Levels

```python
from sparql_agent.formatting import TextFormatter, VerbosityLevel

# Minimal - just the essential data
formatter = TextFormatter(verbosity=VerbosityLevel.MINIMAL)

# Normal - balanced output with context (default)
formatter = TextFormatter(verbosity=VerbosityLevel.NORMAL)

# Detailed - includes metadata and timing
formatter = TextFormatter(verbosity=VerbosityLevel.DETAILED)

# Debug - full details for debugging
formatter = TextFormatter(verbosity=VerbosityLevel.DEBUG)
```

### Configuration Options

```python
from sparql_agent.formatting import TextFormatter, TextFormatterConfig, VerbosityLevel

config = TextFormatterConfig(
    verbosity=VerbosityLevel.NORMAL,
    max_width=80,                    # Maximum line width
    show_metadata=True,              # Include query metadata
    show_summary=True,               # Show result summary
    human_numbers=True,              # Format large numbers (1,000 or 1.5M)
    truncate_uris=True,              # Shorten long URIs
    uri_display='short',             # 'full', 'short', or 'label'
    indent_size=2,                   # Indentation spaces
)

formatter = TextFormatter(config=config)
```

### Context-Aware Formatting

The formatter automatically detects query types and formats appropriately:

**Count Queries:**
```python
# Single value with count-like variable name
count_result = QueryResult(
    bindings=[{'count': {'value': '1523'}}],
    variables=['count'],
    row_count=1
)

formatter = TextFormatter()
print(formatter.format(count_result))
# Output: Count: 1,523
```

**List Queries:**
```python
# Single column, multiple rows
list_result = QueryResult(
    bindings=[
        {'name': {'value': 'Apple'}},
        {'name': {'value': 'Banana'}},
        {'name': {'value': 'Cherry'}},
    ],
    variables=['name'],
    row_count=3
)

formatter = TextFormatter()
print(formatter.format(list_result))
# Output:
# 1. Apple
# 2. Banana
# 3. Cherry
```

**Tabular Data:**
```python
# Multiple columns, multiple rows - creates text table
```

### URI Handling

```python
config = TextFormatterConfig(uri_display='short')
formatter = TextFormatter(config=config)
# URIs shown as: .../LastSegment

config = TextFormatterConfig(uri_display='label')
formatter = TextFormatter(config=config)
# URIs shown as: Last Segment (with underscores removed)

config = TextFormatterConfig(uri_display='full')
formatter = TextFormatter(config=config)
# URIs shown in full
```

## MarkdownFormatter

The `MarkdownFormatter` creates GitHub-compatible markdown with rich formatting.

### Basic Options

```python
from sparql_agent.formatting import MarkdownFormatter

formatter = MarkdownFormatter(
    max_rows=100,                   # Limit rows displayed (None = all)
    include_metadata=True,          # Include metadata section
    generate_links=True,            # Convert URIs to clickable links
    code_blocks_for_uris=True,      # Wrap URIs in code blocks
    table_alignment='left',         # 'left', 'center', or 'right'
)
```

### URI Link Generation

```python
# With links and code blocks (default)
formatter = MarkdownFormatter(
    generate_links=True,
    code_blocks_for_uris=True
)
# Output: [`ResourceName`](http://example.org/resource/ResourceName)

# With links, no code blocks
formatter = MarkdownFormatter(
    generate_links=True,
    code_blocks_for_uris=False
)
# Output: [ResourceName](http://example.org/resource/ResourceName)

# No links, just code blocks
formatter = MarkdownFormatter(
    generate_links=False,
    code_blocks_for_uris=True
)
# Output: `http://example.org/resource/ResourceName`
```

### Large Result Handling

```python
# Automatically adds "... and N more rows" message
formatter = MarkdownFormatter(max_rows=50)
output = formatter.format(large_result)
```

### Special Character Escaping

The formatter automatically escapes markdown special characters to prevent formatting issues:
- Pipe (`|`) - escaped for table compatibility
- Asterisks (`*`) - escaped to prevent bold/italic
- Brackets (`[]`) - escaped to prevent link interpretation
- Hash (`#`) - escaped to prevent header interpretation

## PlainTextFormatter

The `PlainTextFormatter` creates beautiful ASCII tables optimized for terminal display.

### Table Styles

```python
from sparql_agent.formatting import PlainTextFormatter

# Grid style - Unicode box-drawing characters (default)
formatter = PlainTextFormatter(table_style='grid')
# ┌────┬────┐
# │ A  │ B  │
# ├────┼────┤
# │ 1  │ 2  │
# └────┴────┘

# Simple style - ASCII characters
formatter = PlainTextFormatter(table_style='simple')
# +----+----+
# | A  | B  |
# +----+----+
# | 1  | 2  |

# Minimal style - minimal borders
formatter = PlainTextFormatter(table_style='minimal')
#  A    B
#  1    2
```

### Color Support

```python
from sparql_agent.formatting import PlainTextFormatter, ColorScheme, ANSI

# Enable colors (auto-detected)
formatter = PlainTextFormatter(use_color=True)

# Check if terminal supports colors
if ANSI.supports_color():
    formatter = PlainTextFormatter(use_color=True)
else:
    formatter = PlainTextFormatter(use_color=False)

# Disable colors
formatter = PlainTextFormatter(use_color=False)

# Color schemes
formatter = PlainTextFormatter(
    use_color=True,
    color_scheme=ColorScheme.BASIC      # 8 colors
)

formatter = PlainTextFormatter(
    use_color=True,
    color_scheme=ColorScheme.EXTENDED   # 256 colors
)
```

### Column Width Management

```python
formatter = PlainTextFormatter(
    max_col_width=50,      # Maximum column width
    min_col_width=8,       # Minimum column width
    fit_terminal=True,     # Adjust to terminal width
)
```

### Row Numbers

```python
# Show row numbers
formatter = PlainTextFormatter(show_row_numbers=True)
# ┌───┬────┬────┐
# │ # │ A  │ B  │
# ├───┼────┼────┤
# │ 1 │ X  │ Y  │
# │ 2 │ P  │ Q  │
# └───┴────┴────┘
```

### Progress Indicators

```python
formatter = PlainTextFormatter()

# Display progress
for i in range(0, 101, 10):
    progress = formatter.format_progress(i, 100, prefix="Processing")
    print(progress)

# Output:
# Processing: ███████████████░░░░░░░░░ 50.0% (50/100)
```

## Convenience Functions

Simple functions for quick formatting:

```python
from sparql_agent.formatting import (
    format_as_text,
    format_as_markdown,
    format_as_table,
    smart_format,
)

# Natural language text
text = format_as_text(result, verbosity='normal', show_metadata=True)

# Markdown
markdown = format_as_markdown(result, max_rows=100, include_metadata=True)

# ASCII table
table = format_as_table(result, use_color=True, table_style='grid')

# Smart auto-detection
output = smart_format(result)
```

### smart_format()

The `smart_format()` function automatically chooses the best format:

- Small results (≤3 rows, ≤3 cols) → Natural language
- Medium results with wide terminal → ASCII table with colors
- Large results or narrow terminal → Compact text format

```python
from sparql_agent.formatting import smart_format

# Automatically adapts to result size and terminal
output = smart_format(result)

# Force color even if not auto-detected
output = smart_format(result, force_color=True)
```

## ANSI Color Utilities

The `ANSI` class provides color codes and utilities:

```python
from sparql_agent.formatting import ANSI

# Color codes
red_text = f"{ANSI.RED}Error{ANSI.RESET}"
bold_text = f"{ANSI.BOLD}Important{ANSI.RESET}"
blue_bg = f"{ANSI.BG_BLUE}Highlighted{ANSI.RESET}"

# Strip ANSI codes
clean_text = ANSI.strip(colored_text)

# Check color support
if ANSI.supports_color():
    print("Terminal supports colors!")
```

Available colors:
- Basic: BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE
- Bright: BRIGHT_BLACK, BRIGHT_RED, BRIGHT_GREEN, etc.
- Background: BG_BLACK, BG_RED, BG_GREEN, etc.
- Styles: BOLD, DIM, ITALIC, UNDERLINE

## Examples

See `text_examples.py` for comprehensive examples:

```bash
# Run all examples
python3 -m sparql_agent.formatting.text_examples

# Run specific example
python3 -m sparql_agent.formatting.text_examples markdown_formatter
```

Available examples:
- `text_formatter_basic` - Basic TextFormatter usage
- `text_formatter_query_types` - Context-aware formatting
- `text_formatter_configuration` - Configuration options
- `markdown_formatter` - Markdown output
- `plain_text_formatter` - ASCII tables
- `plain_text_with_color` - Color support
- `progress_indicator` - Progress bars
- `convenience_functions` - Quick functions
- `smart_format` - Auto-detection
- `error_handling` - Error cases
- `column_width_handling` - Width management
- `comparison` - Side-by-side comparison

## Testing

Run the test suite:

```bash
python3 -m unittest sparql_agent.formatting.test_text
```

Test coverage includes:
- All formatter classes
- Verbosity levels
- Query type detection
- URI handling
- Color support
- Edge cases (empty results, missing values, Unicode)
- Special characters
- Large datasets

## Best Practices

### For Terminal Output

```python
from sparql_agent.formatting import PlainTextFormatter, ANSI

# Check terminal support
if ANSI.supports_color():
    formatter = PlainTextFormatter(use_color=True, fit_terminal=True)
else:
    formatter = PlainTextFormatter(use_color=False)
```

### For Documentation

```python
from sparql_agent.formatting import MarkdownFormatter

formatter = MarkdownFormatter(
    generate_links=True,
    code_blocks_for_uris=True,
    include_metadata=True,
)
```

### For APIs/Logging

```python
from sparql_agent.formatting import TextFormatter, VerbosityLevel

# Structured but readable
formatter = TextFormatter(verbosity=VerbosityLevel.NORMAL)
```

### For End Users

```python
from sparql_agent.formatting import smart_format

# Let the formatter decide
output = smart_format(result)
```

## Performance

- **TextFormatter**: Very fast, suitable for large results
- **MarkdownFormatter**: Fast, minimal processing overhead
- **PlainTextFormatter**: Moderate, calculates column widths

For large datasets (>10,000 rows):
- Use `max_rows` limiting in MarkdownFormatter
- TextFormatter's minimal verbosity is most efficient
- Consider streaming for extremely large results

## Limitations

- **Terminal Width**: PlainTextFormatter may truncate on narrow terminals
- **Unicode Support**: Requires terminal with Unicode support for box-drawing
- **Color Detection**: May not detect all terminal color capabilities
- **Large Results**: Very large results may be slow to format

## Integration

The text formatters integrate seamlessly with other SPARQL agent components:

```python
from sparql_agent.execution import SPARQLExecutor
from sparql_agent.formatting import smart_format

executor = SPARQLExecutor(endpoint="http://example.org/sparql")
result = executor.execute("SELECT * WHERE { ?s ?p ?o } LIMIT 10")

# Format for display
output = smart_format(result)
print(output)
```

## Contributing

When adding new features:

1. Update the corresponding formatter class
2. Add tests in `test_text.py`
3. Add examples in `text_examples.py`
4. Update this documentation

## License

Part of the SPARQL Agent project.
