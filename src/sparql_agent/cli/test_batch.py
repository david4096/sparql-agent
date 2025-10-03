"""
Tests for Batch Processing Module.

This module contains comprehensive tests for the batch processing functionality
including input parsing, item processing, parallel execution, and result aggregation.
"""

import json
import tempfile
from pathlib import Path
from datetime import datetime
import pytest

from .batch import (
    InputParser,
    InputFormat,
    BatchItem,
    BatchJobConfig,
    BatchProcessor,
    ProcessingStatus,
    OutputMode,
    BatchJobResult,
)


# ============================================================================
# Input Parser Tests
# ============================================================================

class TestInputParser:
    """Test input file parsing for various formats."""

    def test_parse_text(self, tmp_path):
        """Test parsing text format."""
        # Create test file
        test_file = tmp_path / "queries.txt"
        test_file.write_text("""
# Comment line
SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10

# Another comment
SELECT ?class WHERE { ?s a ?class }
""")

        # Parse
        items = InputParser.parse_text(test_file)

        # Verify
        assert len(items) == 2
        assert items[0]['id'] == 'query_1'
        assert 'SELECT' in items[0]['query']
        assert items[1]['id'] == 'query_2'

    def test_parse_json(self, tmp_path):
        """Test parsing JSON format."""
        # Create test file
        test_file = tmp_path / "queries.json"
        data = [
            {
                "id": "q1",
                "query": "SELECT * WHERE { ?s ?p ?o }",
                "metadata": {"type": "basic"}
            },
            {
                "id": "q2",
                "query": "Find all proteins",
                "metadata": {"type": "nl"}
            }
        ]
        test_file.write_text(json.dumps(data))

        # Parse
        items = InputParser.parse_json(test_file)

        # Verify
        assert len(items) == 2
        assert items[0]['id'] == 'q1'
        assert items[0]['metadata']['type'] == 'basic'
        assert items[1]['query'] == 'Find all proteins'

    def test_parse_yaml(self, tmp_path):
        """Test parsing YAML format."""
        pytest.importorskip("yaml")

        # Create test file
        test_file = tmp_path / "queries.yaml"
        yaml_content = """
- id: query_1
  query: SELECT ?s ?p ?o WHERE { ?s ?p ?o }
  metadata:
    description: Basic query
- id: query_2
  query: Find all proteins
"""
        test_file.write_text(yaml_content)

        # Parse
        items = InputParser.parse_yaml(test_file)

        # Verify
        assert len(items) == 2
        assert items[0]['id'] == 'query_1'

    def test_parse_csv(self, tmp_path):
        """Test parsing CSV format."""
        # Create test file
        test_file = tmp_path / "queries.csv"
        csv_content = """id,query,description
q1,SELECT ?s ?p ?o WHERE { ?s ?p ?o },Basic query
q2,Find all proteins,Natural language query
"""
        test_file.write_text(csv_content)

        # Parse
        items = InputParser.parse_csv(test_file)

        # Verify
        assert len(items) == 2
        assert items[0]['id'] == 'q1'
        assert items[1]['description'] == 'Natural language query'


# ============================================================================
# BatchItem Tests
# ============================================================================

class TestBatchItem:
    """Test BatchItem functionality."""

    def test_batch_item_creation(self):
        """Test creating a batch item."""
        item = BatchItem(
            id="test_1",
            input_data={"query": "SELECT * WHERE { ?s ?p ?o }"},
            metadata={"priority": "high"}
        )

        assert item.id == "test_1"
        assert item.status == ProcessingStatus.PENDING
        assert item.attempts == 0

    def test_mark_processing(self):
        """Test marking item as processing."""
        item = BatchItem(id="test_1", input_data={})

        item.mark_processing()

        assert item.status == ProcessingStatus.PROCESSING
        assert item.start_time is not None
        assert item.attempts == 1

    def test_mark_success(self):
        """Test marking item as successful."""
        item = BatchItem(id="test_1", input_data={})
        item.mark_processing()

        result_data = {"bindings": [], "count": 0}
        item.mark_success(result_data)

        assert item.status == ProcessingStatus.SUCCESS
        assert item.result == result_data
        assert item.end_time is not None
        assert item.execution_time > 0

    def test_mark_failed(self):
        """Test marking item as failed."""
        item = BatchItem(id="test_1", input_data={})
        item.mark_processing()

        error_msg = "Query timeout"
        item.mark_failed(error_msg)

        assert item.status == ProcessingStatus.FAILED
        assert item.error == error_msg
        assert item.end_time is not None

    def test_to_dict(self):
        """Test converting item to dictionary."""
        item = BatchItem(
            id="test_1",
            input_data={"query": "SELECT * WHERE { ?s ?p ?o }"},
            metadata={"priority": "high"}
        )
        item.mark_processing()
        item.mark_success({"count": 10})

        item_dict = item.to_dict()

        assert item_dict['id'] == "test_1"
        assert item_dict['status'] == ProcessingStatus.SUCCESS.value
        assert item_dict['result'] == {"count": 10}


# ============================================================================
# BatchProcessor Tests
# ============================================================================

class TestBatchProcessor:
    """Test batch processor functionality."""

    def test_processor_initialization(self, tmp_path):
        """Test processor initialization."""
        config = BatchJobConfig(
            input_file=tmp_path / "queries.txt",
            input_format=InputFormat.TEXT,
            output_dir=tmp_path / "output"
        )

        processor = BatchProcessor(config)

        assert processor.config == config
        assert processor.config.output_dir.exists()

    def test_load_items(self, tmp_path):
        """Test loading items from input file."""
        # Create test file
        test_file = tmp_path / "queries.txt"
        test_file.write_text("""
SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10
SELECT ?class WHERE { ?s a ?class }
""")

        config = BatchJobConfig(
            input_file=test_file,
            input_format=InputFormat.TEXT,
            output_dir=tmp_path / "output"
        )

        processor = BatchProcessor(config)
        items = processor.load_items()

        assert len(items) == 2
        assert all(isinstance(item, BatchItem) for item in items)

    def test_process_item_success(self, tmp_path):
        """Test processing a single item successfully."""
        config = BatchJobConfig(
            input_file=tmp_path / "queries.txt",
            input_format=InputFormat.TEXT,
            output_dir=tmp_path / "output"
        )

        processor = BatchProcessor(config)

        item = BatchItem(
            id="test_1",
            input_data={"value": 42}
        )

        def mock_processor(item, **kwargs):
            return {"result": item.input_data['value'] * 2}

        processed_item = processor.process_item(item, mock_processor)

        assert processed_item.status == ProcessingStatus.SUCCESS
        assert processed_item.result['result'] == 84

    def test_process_item_failure(self, tmp_path):
        """Test processing a failing item."""
        config = BatchJobConfig(
            input_file=tmp_path / "queries.txt",
            input_format=InputFormat.TEXT,
            output_dir=tmp_path / "output",
            retry_attempts=1,
            continue_on_error=True
        )

        processor = BatchProcessor(config)

        item = BatchItem(id="test_1", input_data={})

        def failing_processor(item, **kwargs):
            raise ValueError("Processing error")

        processed_item = processor.process_item(item, failing_processor)

        assert processed_item.status == ProcessingStatus.FAILED
        assert "Processing error" in processed_item.error

    def test_save_results(self, tmp_path):
        """Test saving batch results."""
        config = BatchJobConfig(
            input_file=tmp_path / "queries.txt",
            input_format=InputFormat.TEXT,
            output_dir=tmp_path / "output",
            output_mode=OutputMode.BOTH,
            output_format='json'
        )

        processor = BatchProcessor(config)

        # Create mock items
        item1 = BatchItem(id="test_1", input_data={})
        item1.mark_processing()
        item1.mark_success({"count": 10})

        item2 = BatchItem(id="test_2", input_data={})
        item2.mark_processing()
        item2.mark_failed("Error")

        processor.items = [item1, item2]

        # Create result
        result = BatchJobResult(
            total_items=2,
            successful_items=1,
            failed_items=1,
            skipped_items=0,
            items=[item1, item2],
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_time=1.0
        )

        # Save results
        processor.save_results(result)

        # Verify files exist
        assert (config.output_dir / "results.json").exists()
        assert (config.output_dir / "errors.json").exists()
        assert (config.output_dir / "individual" / "test_1.json").exists()


# ============================================================================
# BatchJobResult Tests
# ============================================================================

class TestBatchJobResult:
    """Test batch job result functionality."""

    def test_success_rate(self):
        """Test success rate calculation."""
        result = BatchJobResult(
            total_items=100,
            successful_items=95,
            failed_items=5,
            skipped_items=0,
            items=[],
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_time=10.0
        )

        assert result.get_success_rate() == 95.0

    def test_average_time(self):
        """Test average time calculation."""
        result = BatchJobResult(
            total_items=10,
            successful_items=10,
            failed_items=0,
            skipped_items=0,
            items=[],
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_time=20.0
        )

        assert result.get_average_time() == 2.0

    def test_to_dict(self):
        """Test converting result to dictionary."""
        item = BatchItem(id="test_1", input_data={})
        item.mark_processing()
        item.mark_success({"count": 10})

        result = BatchJobResult(
            total_items=1,
            successful_items=1,
            failed_items=0,
            skipped_items=0,
            items=[item],
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_time=1.0
        )

        result_dict = result.to_dict()

        assert result_dict['summary']['total_items'] == 1
        assert result_dict['summary']['successful_items'] == 1
        assert len(result_dict['items']) == 1


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for complete workflows."""

    def test_full_batch_workflow(self, tmp_path):
        """Test complete batch processing workflow."""
        # Create input file
        test_file = tmp_path / "queries.json"
        data = [
            {"id": "q1", "query": "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10"},
            {"id": "q2", "query": "SELECT ?class WHERE { ?s a ?class }"}
        ]
        test_file.write_text(json.dumps(data))

        # Create config
        config = BatchJobConfig(
            input_file=test_file,
            input_format=InputFormat.JSON,
            output_dir=tmp_path / "output",
            output_mode=OutputMode.BOTH,
            parallel=False,  # Sequential for testing
            retry_attempts=0
        )

        # Create processor
        processor = BatchProcessor(config)
        processor.load_items()

        # Mock processor function
        def mock_processor(item, **kwargs):
            return {"processed": True, "query": item.input_data['query']}

        # Process
        result = processor.process(mock_processor)

        # Verify
        assert result.total_items == 2
        assert result.successful_items == 2
        assert result.failed_items == 0

        # Save results
        processor.save_results(result)

        # Verify output files
        assert (config.output_dir / "results.json").exists()


# ============================================================================
# Performance Tests
# ============================================================================

class TestPerformance:
    """Performance and stress tests."""

    def test_large_batch_processing(self, tmp_path):
        """Test processing a large batch."""
        # Create large input file
        test_file = tmp_path / "large_batch.json"
        data = [
            {"id": f"q{i}", "query": f"Query {i}"}
            for i in range(100)
        ]
        test_file.write_text(json.dumps(data))

        # Create config with parallel processing
        config = BatchJobConfig(
            input_file=test_file,
            input_format=InputFormat.JSON,
            output_dir=tmp_path / "output",
            parallel=True,
            max_workers=4,
            retry_attempts=0
        )

        # Process
        processor = BatchProcessor(config)
        processor.load_items()

        def fast_processor(item, **kwargs):
            return {"id": item.id, "processed": True}

        result = processor.process(fast_processor)

        # Verify
        assert result.total_items == 100
        assert result.successful_items == 100


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
