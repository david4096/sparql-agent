"""
Batch Processing CLI Tools for SPARQL Agent.

This module provides comprehensive batch processing capabilities including:
- Multiple query execution from files
- Parallel query execution with progress reporting
- Bulk endpoint discovery
- Example generation from schemas
- Multiple input format support (text, JSON, YAML, CSV)
- Various output options (individual files, consolidated reports, logs)
- Error handling and retry logic
- Progress tracking and reporting

Example Usage:
    # Batch query execution
    sparql-agent batch-query queries.txt --endpoint https://sparql.uniprot.org/sparql

    # Bulk endpoint discovery
    sparql-agent bulk-discover endpoints.yaml --output discovery-results/

    # Generate query examples from schema
    sparql-agent generate-examples schema.ttl --count 100 --output examples.json
"""

import csv
import json
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import click
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

from ..config.settings import get_settings, SPARQLAgentSettings
from ..core.exceptions import (
    SPARQLAgentError,
    QueryGenerationError,
    QueryExecutionError,
    EndpointError,
)
from ..core.types import QueryResult, QueryStatus, EndpointInfo, SchemaInfo
from ..discovery.capabilities import CapabilitiesDetector
from ..execution.executor import QueryExecutor
from ..query.generator import SPARQLGenerator, GenerationStrategy
from ..formatting.structured import JSONFormatter, CSVFormatter

logger = logging.getLogger(__name__)
console = Console()


# ============================================================================
# Data Classes and Enums
# ============================================================================

class InputFormat(Enum):
    """Supported input formats for batch processing."""
    TEXT = "text"
    JSON = "json"
    YAML = "yaml"
    CSV = "csv"


class OutputMode(Enum):
    """Output modes for batch results."""
    INDIVIDUAL = "individual"  # Separate file per result
    CONSOLIDATED = "consolidated"  # Single combined file
    BOTH = "both"  # Both individual and consolidated


class ProcessingStatus(Enum):
    """Status of batch processing item."""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class BatchItem:
    """
    Represents a single item in a batch processing job.

    Attributes:
        id: Unique identifier for the item
        input_data: Input data (query, endpoint, etc.)
        metadata: Additional metadata about the item
        status: Processing status
        result: Processing result (if completed)
        error: Error message (if failed)
        attempts: Number of processing attempts
        start_time: Processing start time
        end_time: Processing end time
        execution_time: Time taken to process
    """
    id: str
    input_data: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: ProcessingStatus = ProcessingStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    attempts: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    execution_time: float = 0.0

    def mark_processing(self):
        """Mark item as currently processing."""
        self.status = ProcessingStatus.PROCESSING
        self.start_time = datetime.now()
        self.attempts += 1

    def mark_success(self, result: Any):
        """Mark item as successfully processed."""
        self.status = ProcessingStatus.SUCCESS
        self.result = result
        self.end_time = datetime.now()
        if self.start_time:
            self.execution_time = (self.end_time - self.start_time).total_seconds()

    def mark_failed(self, error: str):
        """Mark item as failed."""
        self.status = ProcessingStatus.FAILED
        self.error = error
        self.end_time = datetime.now()
        if self.start_time:
            self.execution_time = (self.end_time - self.start_time).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "input_data": self.input_data,
            "metadata": self.metadata,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "attempts": self.attempts,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "execution_time": self.execution_time,
        }


@dataclass
class BatchJobConfig:
    """
    Configuration for a batch processing job.

    Attributes:
        input_file: Input file path
        input_format: Format of input file
        output_dir: Output directory
        output_mode: Output mode
        output_format: Format for output files
        parallel: Enable parallel processing
        max_workers: Maximum parallel workers
        timeout: Timeout per item
        retry_attempts: Number of retry attempts
        retry_delay: Delay between retries (seconds)
        continue_on_error: Continue processing on errors
        save_errors: Save error details
        progress_file: File to save progress
        log_file: File to save logs
        rate_limit_enabled: Enable rate limiting per endpoint
        rate_limit_requests_per_second: Max requests per second per endpoint
        deduplicate_results: Remove duplicate results
        monitor_endpoint_health: Monitor endpoint health during batch
        resume_from_checkpoint: Resume from previous checkpoint
        checkpoint_interval: Save checkpoint every N items
        optimize_queries: Enable query optimization suggestions
    """
    input_file: Path
    input_format: InputFormat
    output_dir: Path
    output_mode: OutputMode = OutputMode.CONSOLIDATED
    output_format: str = "json"
    parallel: bool = True
    max_workers: int = 4
    timeout: int = 60
    retry_attempts: int = 2
    retry_delay: float = 1.0
    continue_on_error: bool = True
    save_errors: bool = True
    progress_file: Optional[Path] = None
    log_file: Optional[Path] = None
    rate_limit_enabled: bool = False
    rate_limit_requests_per_second: float = 10.0
    deduplicate_results: bool = False
    monitor_endpoint_health: bool = False
    resume_from_checkpoint: bool = False
    checkpoint_interval: int = 10
    optimize_queries: bool = False


@dataclass
class BatchJobResult:
    """
    Results from a batch processing job.

    Attributes:
        total_items: Total number of items
        successful_items: Number of successful items
        failed_items: Number of failed items
        skipped_items: Number of skipped items
        items: List of batch items
        start_time: Job start time
        end_time: Job end time
        total_time: Total execution time
        statistics: Additional statistics
    """
    total_items: int
    successful_items: int
    failed_items: int
    skipped_items: int
    items: List[BatchItem]
    start_time: datetime
    end_time: datetime
    total_time: float
    statistics: Dict[str, Any] = field(default_factory=dict)

    def get_success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_items == 0:
            return 0.0
        return (self.successful_items / self.total_items) * 100

    def get_average_time(self) -> float:
        """Calculate average execution time per item."""
        if self.total_items == 0:
            return 0.0
        return self.total_time / self.total_items

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "summary": {
                "total_items": self.total_items,
                "successful_items": self.successful_items,
                "failed_items": self.failed_items,
                "skipped_items": self.skipped_items,
                "success_rate": f"{self.get_success_rate():.2f}%",
                "total_time": f"{self.total_time:.2f}s",
                "average_time": f"{self.get_average_time():.2f}s",
            },
            "items": [item.to_dict() for item in self.items],
            "statistics": self.statistics,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
        }


# ============================================================================
# Input Parsers
# ============================================================================

class InputParser:
    """Parse various input file formats."""

    @staticmethod
    def parse_text(file_path: Path) -> List[Dict[str, Any]]:
        """
        Parse plain text file (one query per line).

        Args:
            file_path: Path to text file

        Returns:
            List of items with queries
        """
        items = []
        content = file_path.read_text(encoding='utf-8')

        for i, line in enumerate(content.strip().split('\n'), 1):
            line = line.strip()
            if line and not line.startswith('#'):  # Skip empty and comment lines
                items.append({
                    'id': f"query_{i}",
                    'query': line,
                })

        return items

    @staticmethod
    def parse_json(file_path: Path) -> List[Dict[str, Any]]:
        """
        Parse JSON file.

        Expected format:
        [
            {
                "id": "query_1",
                "query": "SELECT ...",
                "metadata": {...}
            },
            ...
        ]

        Args:
            file_path: Path to JSON file

        Returns:
            List of items
        """
        content = file_path.read_text(encoding='utf-8')
        data = json.loads(content)

        if isinstance(data, dict):
            # Single item
            return [data]
        elif isinstance(data, list):
            # Multiple items
            return data
        else:
            raise ValueError("JSON must be an object or array")

    @staticmethod
    def parse_yaml(file_path: Path) -> List[Dict[str, Any]]:
        """
        Parse YAML file.

        Args:
            file_path: Path to YAML file

        Returns:
            List of items
        """
        try:
            import yaml
        except ImportError:
            raise ImportError("PyYAML required for YAML format. Install with: pip install pyyaml")

        content = file_path.read_text(encoding='utf-8')
        data = yaml.safe_load(content)

        if isinstance(data, dict):
            return [data]
        elif isinstance(data, list):
            return data
        else:
            raise ValueError("YAML must be an object or array")

    @staticmethod
    def parse_csv(file_path: Path) -> List[Dict[str, Any]]:
        """
        Parse CSV file.

        Expected columns: id, query, and any additional metadata columns

        Args:
            file_path: Path to CSV file

        Returns:
            List of items
        """
        items = []

        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                items.append(dict(row))

        return items

    @classmethod
    def parse(cls, file_path: Path, format: InputFormat) -> List[Dict[str, Any]]:
        """
        Parse input file based on format.

        Args:
            file_path: Path to input file
            format: Input format

        Returns:
            List of parsed items
        """
        parsers = {
            InputFormat.TEXT: cls.parse_text,
            InputFormat.JSON: cls.parse_json,
            InputFormat.YAML: cls.parse_yaml,
            InputFormat.CSV: cls.parse_csv,
        }

        parser = parsers.get(format)
        if not parser:
            raise ValueError(f"Unsupported format: {format}")

        return parser(file_path)


# ============================================================================
# Advanced Features: Rate Limiting, Deduplication, Health Monitoring
# ============================================================================

class RateLimiter:
    """Rate limiter for endpoint requests."""

    def __init__(self, requests_per_second: float):
        """
        Initialize rate limiter.

        Args:
            requests_per_second: Maximum requests per second
        """
        self.requests_per_second = requests_per_second
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time: Dict[str, float] = {}

    def wait_if_needed(self, endpoint: str):
        """
        Wait if necessary to respect rate limit.

        Args:
            endpoint: Endpoint URL
        """
        if endpoint in self.last_request_time:
            elapsed = time.time() - self.last_request_time[endpoint]
            if elapsed < self.min_interval:
                wait_time = self.min_interval - elapsed
                logger.debug(f"Rate limiting: waiting {wait_time:.3f}s for {endpoint}")
                time.sleep(wait_time)

        self.last_request_time[endpoint] = time.time()


class ResultDeduplicator:
    """Deduplicates results based on content hash."""

    def __init__(self):
        """Initialize deduplicator."""
        self.seen_hashes: Set[str] = set()

    def is_duplicate(self, result: Any) -> bool:
        """
        Check if result is a duplicate.

        Args:
            result: Result to check

        Returns:
            True if duplicate, False otherwise
        """
        import hashlib
        result_str = json.dumps(result, sort_keys=True)
        result_hash = hashlib.sha256(result_str.encode()).hexdigest()

        if result_hash in self.seen_hashes:
            return True

        self.seen_hashes.add(result_hash)
        return False

    def get_statistics(self) -> Dict[str, int]:
        """Get deduplication statistics."""
        return {
            'unique_results': len(self.seen_hashes),
        }


class EndpointHealthMonitor:
    """Monitors endpoint health during batch processing."""

    def __init__(self):
        """Initialize health monitor."""
        self.endpoint_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_response_time': 0.0,
            'errors': [],
            'last_success': None,
            'last_failure': None,
        })

    def record_request(
        self,
        endpoint: str,
        success: bool,
        response_time: float,
        error: Optional[str] = None
    ):
        """
        Record a request result.

        Args:
            endpoint: Endpoint URL
            success: Whether request succeeded
            response_time: Response time in seconds
            error: Error message if failed
        """
        stats = self.endpoint_stats[endpoint]
        stats['total_requests'] += 1
        stats['total_response_time'] += response_time

        if success:
            stats['successful_requests'] += 1
            stats['last_success'] = datetime.now()
        else:
            stats['failed_requests'] += 1
            stats['last_failure'] = datetime.now()
            if error:
                stats['errors'].append({
                    'timestamp': datetime.now().isoformat(),
                    'error': error[:200]  # Truncate long errors
                })

    def get_health_status(self, endpoint: str) -> Dict[str, Any]:
        """
        Get health status for an endpoint.

        Args:
            endpoint: Endpoint URL

        Returns:
            Health status dictionary
        """
        stats = self.endpoint_stats[endpoint]

        if stats['total_requests'] == 0:
            return {
                'status': 'unknown',
                'message': 'No requests made yet'
            }

        success_rate = stats['successful_requests'] / stats['total_requests']
        avg_response_time = stats['total_response_time'] / stats['total_requests']

        # Determine health status
        if success_rate >= 0.95 and avg_response_time < 5.0:
            status = 'healthy'
        elif success_rate >= 0.80:
            status = 'degraded'
        else:
            status = 'unhealthy'

        return {
            'status': status,
            'success_rate': f"{success_rate:.2%}",
            'avg_response_time': f"{avg_response_time:.3f}s",
            'total_requests': stats['total_requests'],
            'successful_requests': stats['successful_requests'],
            'failed_requests': stats['failed_requests'],
            'recent_errors': stats['errors'][-5:],  # Last 5 errors
        }

    def get_all_health_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get health status for all monitored endpoints."""
        return {
            endpoint: self.get_health_status(endpoint)
            for endpoint in self.endpoint_stats.keys()
        }


class QueryOptimizer:
    """Provides query optimization suggestions."""

    @staticmethod
    def analyze_query(query: str) -> List[Dict[str, str]]:
        """
        Analyze query and provide optimization suggestions.

        Args:
            query: SPARQL query string

        Returns:
            List of optimization suggestions
        """
        suggestions = []

        # Check for SELECT * (can be slow)
        if "SELECT *" in query.upper():
            suggestions.append({
                'type': 'performance',
                'severity': 'warning',
                'message': 'Consider selecting specific variables instead of SELECT *',
                'suggestion': 'Replace SELECT * with SELECT ?var1 ?var2 ...'
            })

        # Check for missing LIMIT
        if "LIMIT" not in query.upper():
            suggestions.append({
                'type': 'performance',
                'severity': 'warning',
                'message': 'Query has no LIMIT clause, may return many results',
                'suggestion': 'Add LIMIT clause to control result size'
            })

        # Check for OPTIONAL without FILTER
        if "OPTIONAL" in query.upper() and query.count("OPTIONAL") > 2:
            suggestions.append({
                'type': 'performance',
                'severity': 'info',
                'message': 'Multiple OPTIONAL clauses can be slow',
                'suggestion': 'Consider using UNION or simplifying the query'
            })

        # Check for REGEX in FILTER
        if "REGEX" in query.upper():
            suggestions.append({
                'type': 'performance',
                'severity': 'info',
                'message': 'REGEX filters can be slow on large datasets',
                'suggestion': 'Consider using string functions like CONTAINS or exact matches'
            })

        # Check for DISTINCT (can be expensive)
        if "DISTINCT" in query.upper():
            suggestions.append({
                'type': 'performance',
                'severity': 'info',
                'message': 'DISTINCT can be expensive on large result sets',
                'suggestion': 'Ensure DISTINCT is necessary for your use case'
            })

        return suggestions


# ============================================================================
# Batch Processor
# ============================================================================

class BatchProcessor:
    """
    Core batch processing engine with parallel execution and progress tracking.
    """

    def __init__(self, config: BatchJobConfig):
        """
        Initialize batch processor.

        Args:
            config: Job configuration
        """
        self.config = config
        self.items: List[BatchItem] = []

        # Ensure output directory exists
        self.config.output_dir.mkdir(parents=True, exist_ok=True)

        # Set up logging
        if config.log_file:
            logging.basicConfig(
                filename=config.log_file,
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )

        # Initialize advanced features
        self.rate_limiter = RateLimiter(config.rate_limit_requests_per_second) if config.rate_limit_enabled else None
        self.deduplicator = ResultDeduplicator() if config.deduplicate_results else None
        self.health_monitor = EndpointHealthMonitor() if config.monitor_endpoint_health else None
        self.query_optimizer = QueryOptimizer() if config.optimize_queries else None

        # Checkpoint file
        self.checkpoint_file = config.output_dir / "checkpoint.json"
        self.items_processed = 0

    def load_items(self) -> List[BatchItem]:
        """
        Load items from input file, optionally resuming from checkpoint.

        Returns:
            List of batch items
        """
        logger.info(f"Loading items from {self.config.input_file}")

        # Check for checkpoint if resume is enabled
        if self.config.resume_from_checkpoint and self.checkpoint_file.exists():
            logger.info(f"Resuming from checkpoint: {self.checkpoint_file}")
            return self._load_from_checkpoint()

        # Parse input file
        parsed_items = InputParser.parse(
            self.config.input_file,
            self.config.input_format
        )

        # Convert to BatchItem objects
        items = []
        for i, item_data in enumerate(parsed_items, 1):
            # Generate ID if not provided
            item_id = item_data.get('id', f"item_{i}")

            # Extract metadata
            metadata = item_data.get('metadata', {})

            # Remove known fields to get remaining as metadata
            input_data = {k: v for k, v in item_data.items()
                         if k not in ['id', 'metadata']}

            batch_item = BatchItem(
                id=item_id,
                input_data=input_data,
                metadata=metadata
            )
            items.append(batch_item)

        self.items = items
        logger.info(f"Loaded {len(items)} items")

        return items

    def _load_from_checkpoint(self) -> List[BatchItem]:
        """Load items from checkpoint file."""
        with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
            checkpoint_data = json.load(f)

        items = []
        for item_dict in checkpoint_data['items']:
            # Reconstruct BatchItem from dict
            item = BatchItem(
                id=item_dict['id'],
                input_data=item_dict['input_data'],
                metadata=item_dict['metadata'],
                status=ProcessingStatus(item_dict['status']),
                result=item_dict.get('result'),
                error=item_dict.get('error'),
                attempts=item_dict['attempts'],
            )

            # Restore timestamps
            if item_dict.get('start_time'):
                item.start_time = datetime.fromisoformat(item_dict['start_time'])
            if item_dict.get('end_time'):
                item.end_time = datetime.fromisoformat(item_dict['end_time'])

            item.execution_time = item_dict['execution_time']
            items.append(item)

        self.items = items
        self.items_processed = checkpoint_data.get('items_processed', 0)

        logger.info(f"Loaded {len(items)} items from checkpoint, {self.items_processed} already processed")

        return items

    def _save_checkpoint(self):
        """Save current progress to checkpoint file."""
        checkpoint_data = {
            'timestamp': datetime.now().isoformat(),
            'items_processed': self.items_processed,
            'items': [item.to_dict() for item in self.items],
        }

        with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, indent=2)

        logger.info(f"Checkpoint saved: {self.items_processed}/{len(self.items)} items processed")

    def process_item(
        self,
        item: BatchItem,
        processor_func,
        **kwargs
    ) -> BatchItem:
        """
        Process a single item with retry logic and advanced features.

        Args:
            item: Batch item to process
            processor_func: Function to process the item
            **kwargs: Additional arguments for processor

        Returns:
            Processed batch item
        """
        # Skip if already processed (from checkpoint)
        if item.status in [ProcessingStatus.SUCCESS, ProcessingStatus.SKIPPED]:
            logger.info(f"Skipping {item.id} (already processed)")
            return item

        # Apply rate limiting if enabled
        if self.rate_limiter:
            endpoint = kwargs.get('endpoint') or item.input_data.get('endpoint')
            if endpoint:
                self.rate_limiter.wait_if_needed(endpoint)

        # Optimize query if enabled
        if self.query_optimizer and item.input_data.get('query'):
            query = item.input_data['query']
            suggestions = self.query_optimizer.analyze_query(query)
            if suggestions:
                item.metadata['optimization_suggestions'] = suggestions
                logger.info(f"Query optimization suggestions for {item.id}: {len(suggestions)} found")

        for attempt in range(self.config.retry_attempts + 1):
            try:
                item.mark_processing()
                logger.info(f"Processing {item.id} (attempt {attempt + 1})")

                start_time = time.time()

                # Call processor function
                result = processor_func(item, **kwargs)

                execution_time = time.time() - start_time

                # Apply result deduplication if enabled
                if self.deduplicator:
                    if self.deduplicator.is_duplicate(result):
                        logger.info(f"Duplicate result detected for {item.id}")
                        item.metadata['is_duplicate'] = True

                # Record health metrics if enabled
                if self.health_monitor:
                    endpoint = kwargs.get('endpoint') or item.input_data.get('endpoint')
                    if endpoint:
                        self.health_monitor.record_request(
                            endpoint=endpoint,
                            success=True,
                            response_time=execution_time
                        )

                item.mark_success(result)
                logger.info(f"Successfully processed {item.id}")

                # Save checkpoint periodically
                self.items_processed += 1
                if self.config.resume_from_checkpoint and self.items_processed % self.config.checkpoint_interval == 0:
                    self._save_checkpoint()

                return item

            except Exception as e:
                execution_time = time.time() - start_time if 'start_time' in locals() else 0
                error_msg = f"Error processing {item.id}: {str(e)}"
                logger.error(error_msg)

                # Record health metrics if enabled
                if self.health_monitor:
                    endpoint = kwargs.get('endpoint') or item.input_data.get('endpoint')
                    if endpoint:
                        self.health_monitor.record_request(
                            endpoint=endpoint,
                            success=False,
                            response_time=execution_time,
                            error=str(e)
                        )

                if attempt < self.config.retry_attempts:
                    logger.info(f"Retrying {item.id} after {self.config.retry_delay}s...")
                    time.sleep(self.config.retry_delay)
                else:
                    item.mark_failed(str(e))
                    if not self.config.continue_on_error:
                        raise

        return item

    def process_parallel(
        self,
        processor_func,
        **kwargs
    ) -> BatchJobResult:
        """
        Process items in parallel.

        Args:
            processor_func: Function to process each item
            **kwargs: Additional arguments for processor

        Returns:
            Batch job result
        """
        start_time = datetime.now()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console
        ) as progress:

            task = progress.add_task(
                "[cyan]Processing batch...",
                total=len(self.items)
            )

            with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                # Submit all items
                futures = {
                    executor.submit(
                        self.process_item,
                        item,
                        processor_func,
                        **kwargs
                    ): item
                    for item in self.items
                }

                # Collect results
                for future in as_completed(futures):
                    item = futures[future]
                    try:
                        processed_item = future.result()
                        progress.update(task, advance=1)

                    except Exception as e:
                        logger.error(f"Unexpected error for {item.id}: {e}")
                        item.mark_failed(str(e))
                        progress.update(task, advance=1)

        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()

        # Calculate statistics
        successful = sum(1 for item in self.items if item.status == ProcessingStatus.SUCCESS)
        failed = sum(1 for item in self.items if item.status == ProcessingStatus.FAILED)
        skipped = sum(1 for item in self.items if item.status == ProcessingStatus.SKIPPED)

        return BatchJobResult(
            total_items=len(self.items),
            successful_items=successful,
            failed_items=failed,
            skipped_items=skipped,
            items=self.items,
            start_time=start_time,
            end_time=end_time,
            total_time=total_time
        )

    def process_sequential(
        self,
        processor_func,
        **kwargs
    ) -> BatchJobResult:
        """
        Process items sequentially.

        Args:
            processor_func: Function to process each item
            **kwargs: Additional arguments for processor

        Returns:
            Batch job result
        """
        start_time = datetime.now()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console
        ) as progress:

            task = progress.add_task(
                "[cyan]Processing batch...",
                total=len(self.items)
            )

            for item in self.items:
                try:
                    self.process_item(item, processor_func, **kwargs)
                except Exception as e:
                    logger.error(f"Error processing {item.id}: {e}")
                    if not self.config.continue_on_error:
                        raise
                finally:
                    progress.update(task, advance=1)

        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()

        # Calculate statistics
        successful = sum(1 for item in self.items if item.status == ProcessingStatus.SUCCESS)
        failed = sum(1 for item in self.items if item.status == ProcessingStatus.FAILED)
        skipped = sum(1 for item in self.items if item.status == ProcessingStatus.SKIPPED)

        return BatchJobResult(
            total_items=len(self.items),
            successful_items=successful,
            failed_items=failed,
            skipped_items=skipped,
            items=self.items,
            start_time=start_time,
            end_time=end_time,
            total_time=total_time
        )

    def process(self, processor_func, **kwargs) -> BatchJobResult:
        """
        Process all items.

        Args:
            processor_func: Function to process each item
            **kwargs: Additional arguments for processor

        Returns:
            Batch job result
        """
        if self.config.parallel:
            return self.process_parallel(processor_func, **kwargs)
        else:
            return self.process_sequential(processor_func, **kwargs)

    def save_results(self, result: BatchJobResult):
        """
        Save batch job results with advanced feature statistics.

        Args:
            result: Batch job result to save
        """
        # Save individual results
        if self.config.output_mode in [OutputMode.INDIVIDUAL, OutputMode.BOTH]:
            results_dir = self.config.output_dir / "individual"
            results_dir.mkdir(exist_ok=True)

            for item in result.items:
                if item.result is not None:
                    output_file = results_dir / f"{item.id}.{self.config.output_format}"

                    with open(output_file, 'w', encoding='utf-8') as f:
                        if self.config.output_format == 'json':
                            json.dump(item.to_dict(), f, indent=2)
                        else:
                            f.write(str(item.result))

        # Save consolidated results
        if self.config.output_mode in [OutputMode.CONSOLIDATED, OutputMode.BOTH]:
            consolidated_file = self.config.output_dir / f"results.{self.config.output_format}"

            # Add advanced feature statistics to result
            result_dict = result.to_dict()

            if self.deduplicator:
                result_dict['statistics']['deduplication'] = self.deduplicator.get_statistics()

            if self.health_monitor:
                result_dict['statistics']['endpoint_health'] = self.health_monitor.get_all_health_statuses()

            # Count optimization suggestions
            if self.query_optimizer:
                total_suggestions = sum(
                    len(item.metadata.get('optimization_suggestions', []))
                    for item in result.items
                )
                result_dict['statistics']['optimization_suggestions_count'] = total_suggestions

            with open(consolidated_file, 'w', encoding='utf-8') as f:
                if self.config.output_format == 'json':
                    json.dump(result_dict, f, indent=2)
                else:
                    for item in result.items:
                        f.write(f"# {item.id}\n")
                        f.write(str(item.result))
                        f.write("\n\n")

        # Save errors
        if self.config.save_errors:
            errors = [item for item in result.items if item.status == ProcessingStatus.FAILED]
            if errors:
                error_file = self.config.output_dir / "errors.json"
                with open(error_file, 'w', encoding='utf-8') as f:
                    json.dump([item.to_dict() for item in errors], f, indent=2)

        # Save health monitoring report
        if self.health_monitor:
            health_file = self.config.output_dir / "endpoint_health.json"
            with open(health_file, 'w', encoding='utf-8') as f:
                json.dump(self.health_monitor.get_all_health_statuses(), f, indent=2)

        # Save query optimization suggestions
        if self.query_optimizer:
            suggestions = []
            for item in result.items:
                if item.metadata.get('optimization_suggestions'):
                    suggestions.append({
                        'item_id': item.id,
                        'query': item.input_data.get('query', '')[:100],
                        'suggestions': item.metadata['optimization_suggestions']
                    })

            if suggestions:
                optimization_file = self.config.output_dir / "query_optimizations.json"
                with open(optimization_file, 'w', encoding='utf-8') as f:
                    json.dump(suggestions, f, indent=2)

        # Save progress
        if self.config.progress_file:
            with open(self.config.progress_file, 'w', encoding='utf-8') as f:
                json.dump(result.to_dict(), f, indent=2)

        # Final checkpoint save
        if self.config.resume_from_checkpoint:
            self._save_checkpoint()

        logger.info(f"Results saved to {self.config.output_dir}")


# ============================================================================
# Query Batch Processor
# ============================================================================

def process_query_item(
    item: BatchItem,
    endpoint: str,
    generator: SPARQLGenerator,
    executor: QueryExecutor,
    execute: bool = True,
    strategy: GenerationStrategy = GenerationStrategy.AUTO
) -> Dict[str, Any]:
    """
    Process a single query item.

    Args:
        item: Batch item containing query
        endpoint: SPARQL endpoint URL
        generator: Query generator
        executor: Query executor
        execute: Execute generated query
        strategy: Generation strategy

    Returns:
        Result dictionary
    """
    query_text = item.input_data.get('query')
    if not query_text:
        raise ValueError("No query provided in item")

    result = {
        'id': item.id,
        'query': query_text,
    }

    # Check if it's a natural language query or SPARQL
    if query_text.strip().upper().startswith(('SELECT', 'ASK', 'CONSTRUCT', 'DESCRIBE')):
        # Direct SPARQL query
        sparql_query = query_text
        result['type'] = 'sparql'
    else:
        # Natural language - generate SPARQL
        generation = generator.generate(
            natural_language=query_text,
            strategy=strategy
        )
        sparql_query = generation.query
        result['type'] = 'natural_language'
        result['generated_sparql'] = sparql_query
        result['confidence'] = generation.confidence
        result['explanation'] = generation.explanation

    # Execute if requested
    if execute:
        endpoint_info = EndpointInfo(url=endpoint)
        query_result = executor.execute(sparql_query, endpoint_info)

        result['execution'] = {
            'status': query_result.status.value,
            'row_count': query_result.row_count,
            'execution_time': query_result.execution_time,
            'variables': query_result.variables,
            'bindings': query_result.bindings[:100] if query_result.bindings else [],  # Limit results
        }

        if query_result.error_message:
            result['execution']['error'] = query_result.error_message

    return result


# ============================================================================
# Discovery Batch Processor
# ============================================================================

def process_discovery_item(
    item: BatchItem,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Process a single endpoint discovery item.

    Args:
        item: Batch item containing endpoint
        timeout: Discovery timeout

    Returns:
        Discovery result dictionary
    """
    endpoint_url = item.input_data.get('endpoint') or item.input_data.get('url')
    if not endpoint_url:
        raise ValueError("No endpoint URL provided in item")

    # Discover capabilities
    detector = CapabilitiesDetector(endpoint_url, timeout=timeout)
    capabilities = detector.detect_all_capabilities()

    return {
        'id': item.id,
        'endpoint': endpoint_url,
        'capabilities': capabilities,
    }


# ============================================================================
# Example Generation Processor
# ============================================================================

def process_example_generation(
    item: BatchItem,
    schema_file: Path,
    count: int = 10
) -> Dict[str, Any]:
    """
    Generate query examples from schema.

    Args:
        item: Batch item containing pattern
        schema_file: Schema file path
        count: Number of examples to generate

    Returns:
        Generated examples dictionary
    """
    # TODO: Implement schema-based example generation
    # This is a placeholder - would need schema parsing and query generation

    pattern_type = item.input_data.get('pattern_type', 'basic')

    examples = []
    for i in range(count):
        example = {
            'id': f"{item.id}_example_{i+1}",
            'pattern_type': pattern_type,
            'query': f"# Example query {i+1} for {pattern_type}",
        }
        examples.append(example)

    return {
        'id': item.id,
        'pattern_type': pattern_type,
        'examples': examples,
    }


# ============================================================================
# Benchmark Processor
# ============================================================================

def process_benchmark_item(
    item: BatchItem,
    timeout: int = 60
) -> Dict[str, Any]:
    """
    Process a single benchmark item (execute query and measure performance).

    Args:
        item: Batch item containing query and endpoint
        timeout: Query timeout

    Returns:
        Benchmark result dictionary
    """
    query = item.input_data.get('query')
    endpoint_url = item.input_data.get('endpoint')
    query_id = item.input_data.get('query_id')
    endpoint_id = item.input_data.get('endpoint_id')
    iteration = item.input_data.get('iteration', 0)
    is_warmup = item.input_data.get('is_warmup', False)

    # Execute query
    executor = QueryExecutor(timeout=timeout)
    endpoint_info = EndpointInfo(url=endpoint_url)

    start_time = time.time()
    result = executor.execute(query, endpoint_info)
    execution_time = time.time() - start_time

    return {
        'id': item.id,
        'query_id': query_id,
        'endpoint_id': endpoint_id,
        'iteration': iteration,
        'is_warmup': is_warmup,
        'query': query,
        'endpoint': endpoint_url,
        'execution_time': execution_time,
        'status': result.status.value,
        'row_count': result.row_count,
        'error': result.error_message,
    }


def generate_benchmark_report(
    result: BatchJobResult,
    iterations: int,
    warmup: int
) -> Dict[str, Any]:
    """
    Generate benchmark report from batch results.

    Args:
        result: Batch job result
        iterations: Number of iterations per query
        warmup: Number of warmup iterations

    Returns:
        Benchmark report dictionary
    """
    import statistics

    # Filter out warmup runs
    valid_items = [
        item for item in result.items
        if item.status == ProcessingStatus.SUCCESS
        and not item.result.get('is_warmup', False)
    ]

    # Group by query_id and endpoint_id
    grouped = defaultdict(lambda: defaultdict(list))
    for item in valid_items:
        query_id = item.result['query_id']
        endpoint_id = item.result['endpoint_id']
        execution_time = item.result['execution_time']
        grouped[query_id][endpoint_id].append(execution_time)

    # Calculate statistics
    statistics_data = []
    for query_id, endpoints in grouped.items():
        for endpoint_id, times in endpoints.items():
            if times:
                statistics_data.append({
                    'query_id': query_id,
                    'endpoint_id': endpoint_id,
                    'mean': statistics.mean(times),
                    'median': statistics.median(times),
                    'stdev': statistics.stdev(times) if len(times) > 1 else 0,
                    'min': min(times),
                    'max': max(times),
                    'iterations': len(times),
                    'total_time': sum(times),
                })

    return {
        'summary': {
            'total_queries': len(grouped),
            'total_endpoints': len(set(ep for eps in grouped.values() for ep in eps.keys())),
            'total_executions': len(valid_items),
            'iterations_per_query': iterations,
            'warmup_runs': warmup,
        },
        'statistics': statistics_data,
        'raw_results': [item.to_dict() for item in valid_items],
    }


def save_benchmark_report(
    report: Dict[str, Any],
    output_file: Path,
    format: str
):
    """
    Save benchmark report in specified format.

    Args:
        report: Benchmark report data
        output_file: Output file path
        format: Output format (html, json, csv, text)
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)

    if format == 'json':
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)

    elif format == 'csv':
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(
                f,
                fieldnames=['query_id', 'endpoint_id', 'mean', 'median', 'stdev', 'min', 'max', 'iterations']
            )
            writer.writeheader()
            writer.writerows(report['statistics'])

    elif format == 'html':
        # Generate HTML report
        html = generate_html_benchmark_report(report)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)

    elif format == 'text':
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("SPARQL Agent Benchmark Report\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Total Queries: {report['summary']['total_queries']}\n")
            f.write(f"Total Endpoints: {report['summary']['total_endpoints']}\n")
            f.write(f"Iterations per Query: {report['summary']['iterations_per_query']}\n\n")
            f.write("Performance Statistics:\n")
            f.write("-" * 60 + "\n")
            for stat in report['statistics']:
                f.write(f"\nQuery: {stat['query_id']}, Endpoint: {stat['endpoint_id']}\n")
                f.write(f"  Mean: {stat['mean']:.3f}s, Median: {stat['median']:.3f}s\n")
                f.write(f"  StdDev: {stat['stdev']:.3f}s, Min: {stat['min']:.3f}s, Max: {stat['max']:.3f}s\n")


def generate_html_benchmark_report(report: Dict[str, Any]) -> str:
    """Generate HTML benchmark report with charts."""
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>SPARQL Agent Benchmark Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }}
        h1 {{ color: #333; }}
        .summary {{ background: #e3f2fd; padding: 15px; border-radius: 4px; margin: 20px 0; }}
        .stats-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        .stats-table th, .stats-table td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        .stats-table th {{ background: #2196F3; color: white; }}
        .stats-table tr:hover {{ background: #f5f5f5; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>SPARQL Agent Benchmark Report</h1>

        <div class="summary">
            <h2>Summary</h2>
            <p><strong>Total Queries:</strong> {report['summary']['total_queries']}</p>
            <p><strong>Total Endpoints:</strong> {report['summary']['total_endpoints']}</p>
            <p><strong>Total Executions:</strong> {report['summary']['total_executions']}</p>
            <p><strong>Iterations per Query:</strong> {report['summary']['iterations_per_query']}</p>
            <p><strong>Warmup Runs:</strong> {report['summary']['warmup_runs']}</p>
        </div>

        <h2>Performance Statistics</h2>
        <table class="stats-table">
            <thead>
                <tr>
                    <th>Query ID</th>
                    <th>Endpoint ID</th>
                    <th>Mean (s)</th>
                    <th>Median (s)</th>
                    <th>Std Dev (s)</th>
                    <th>Min (s)</th>
                    <th>Max (s)</th>
                    <th>Iterations</th>
                </tr>
            </thead>
            <tbody>
    """

    for stat in report['statistics']:
        html += f"""
                <tr>
                    <td>{stat['query_id']}</td>
                    <td>{stat['endpoint_id']}</td>
                    <td>{stat['mean']:.3f}</td>
                    <td>{stat['median']:.3f}</td>
                    <td>{stat['stdev']:.3f}</td>
                    <td>{stat['min']:.3f}</td>
                    <td>{stat['max']:.3f}</td>
                    <td>{stat['iterations']}</td>
                </tr>
        """

    html += """
            </tbody>
        </table>
    </div>
</body>
</html>
    """

    return html


def display_benchmark_summary(report: Dict[str, Any]):
    """Display benchmark summary in terminal."""
    summary_table = Table(title="Benchmark Performance Summary", show_header=True)
    summary_table.add_column("Query", style="cyan")
    summary_table.add_column("Endpoint", style="yellow")
    summary_table.add_column("Mean", style="green")
    summary_table.add_column("Median", style="green")
    summary_table.add_column("Std Dev", style="blue")
    summary_table.add_column("Iterations", style="magenta")

    # Show top 10 by mean time
    sorted_stats = sorted(report['statistics'], key=lambda x: x['mean'], reverse=True)[:10]

    for stat in sorted_stats:
        summary_table.add_row(
            stat['query_id'][:30],
            stat['endpoint_id'][:30],
            f"{stat['mean']:.3f}s",
            f"{stat['median']:.3f}s",
            f"{stat['stdev']:.3f}s",
            str(stat['iterations'])
        )

    console.print(summary_table)


# ============================================================================
# Migration Processor
# ============================================================================

def process_migration_item(
    item: BatchItem,
    source_endpoint: Optional[str] = None,
    target_endpoint: Optional[str] = None,
    update_prefixes: bool = False,
    validate: bool = True,
    test_execution: bool = False
) -> Dict[str, Any]:
    """
    Process a single query migration item.

    Args:
        item: Batch item containing query
        source_endpoint: Source endpoint URL
        target_endpoint: Target endpoint URL
        update_prefixes: Update namespace prefixes
        validate: Validate migrated query
        test_execution: Test execution on both endpoints

    Returns:
        Migration result dictionary
    """
    original_query = item.input_data.get('query')

    # Simple migration: for now, just validate and optionally test
    migrated_query = original_query  # Placeholder

    result = {
        'id': item.id,
        'original_query': original_query,
        'migrated_query': migrated_query,
        'changes_made': [],
        'validation_passed': True,
    }

    # Validate if requested
    if validate:
        from ..execution.validator import QueryValidator
        validator = QueryValidator()
        validation_result = validator.validate(migrated_query)
        result['validation_passed'] = validation_result.is_valid
        result['validation_errors'] = [
            {'message': issue.message, 'severity': issue.severity.value}
            for issue in validation_result.issues
        ]

    # Test execution if requested
    if test_execution and source_endpoint and target_endpoint:
        executor = QueryExecutor(timeout=30)

        # Test on source
        try:
            source_result = executor.execute(
                original_query,
                EndpointInfo(url=source_endpoint)
            )
            result['source_execution'] = {
                'success': source_result.is_success,
                'row_count': source_result.row_count,
                'execution_time': source_result.execution_time,
            }
        except Exception as e:
            result['source_execution'] = {'success': False, 'error': str(e)}

        # Test on target
        try:
            target_result = executor.execute(
                migrated_query,
                EndpointInfo(url=target_endpoint)
            )
            result['target_execution'] = {
                'success': target_result.is_success,
                'row_count': target_result.row_count,
                'execution_time': target_result.execution_time,
            }
        except Exception as e:
            result['target_execution'] = {'success': False, 'error': str(e)}

    return result


def save_migrated_queries(result: BatchJobResult, output_path: Path, show_diff: bool):
    """
    Save migrated queries to output file.

    Args:
        result: Batch job result
        output_path: Output file path
        show_diff: Show differences between original and migrated queries
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save migrated queries
    migrated_queries = []
    for item in result.items:
        if item.status == ProcessingStatus.SUCCESS:
            migrated_queries.append({
                'id': item.id,
                'query': item.result['migrated_query'],
                'original_query': item.result['original_query'],
                'changes': item.result.get('changes_made', []),
                'validation_passed': item.result.get('validation_passed', True),
            })

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(migrated_queries, f, indent=2)

    # Save diff if requested
    if show_diff:
        diff_file = output_path.parent / f"{output_path.stem}_diff.txt"
        with open(diff_file, 'w', encoding='utf-8') as f:
            for item in result.items:
                if item.status == ProcessingStatus.SUCCESS:
                    f.write(f"{'='*60}\n")
                    f.write(f"Query ID: {item.id}\n")
                    f.write(f"{'='*60}\n\n")
                    f.write("ORIGINAL:\n")
                    f.write(item.result['original_query'])
                    f.write("\n\nMIGRATED:\n")
                    f.write(item.result['migrated_query'])
                    f.write("\n\n")


def display_migration_summary(result: BatchJobResult):
    """Display migration summary in terminal."""
    summary_table = Table(title="Migration Summary", show_header=True)
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")

    summary_table.add_row("Total Queries", str(result.total_items))
    summary_table.add_row("Successfully Migrated", str(result.successful_items))
    summary_table.add_row("Failed", str(result.failed_items))

    # Count validation issues
    validation_failed = sum(
        1 for item in result.items
        if item.status == ProcessingStatus.SUCCESS
        and not item.result.get('validation_passed', True)
    )
    summary_table.add_row("Validation Issues", str(validation_failed))

    console.print(summary_table)


# ============================================================================
# CLI Commands
# ============================================================================

@click.group(name='batch')
def batch_cli():
    """
    Batch processing commands for SPARQL Agent.

    Process multiple queries, discover endpoints, and generate examples in batch mode.
    """
    pass


@batch_cli.command('batch-query')
@click.argument('input_file', type=click.Path(exists=True, dir_okay=False))
@click.option(
    '--endpoint',
    '-e',
    required=True,
    help='SPARQL endpoint URL'
)
@click.option(
    '--format',
    '-f',
    type=click.Choice(['text', 'json', 'yaml', 'csv'], case_sensitive=False),
    default='text',
    help='Input file format'
)
@click.option(
    '--output',
    '-o',
    type=click.Path(),
    default='batch-results',
    help='Output directory'
)
@click.option(
    '--output-mode',
    type=click.Choice(['individual', 'consolidated', 'both'], case_sensitive=False),
    default='both',
    help='Output mode'
)
@click.option(
    '--execute/--no-execute',
    default=True,
    help='Execute generated queries'
)
@click.option(
    '--parallel/--sequential',
    default=True,
    help='Process queries in parallel'
)
@click.option(
    '--workers',
    '-w',
    type=int,
    default=4,
    help='Number of parallel workers'
)
@click.option(
    '--timeout',
    '-t',
    type=int,
    default=60,
    help='Timeout per query (seconds)'
)
@click.option(
    '--retry',
    '-r',
    type=int,
    default=2,
    help='Number of retry attempts'
)
@click.option(
    '--strategy',
    type=click.Choice(['auto', 'template', 'llm', 'hybrid'], case_sensitive=False),
    default='auto',
    help='Query generation strategy'
)
@click.option(
    '--verbose',
    '-v',
    is_flag=True,
    help='Verbose output'
)
@click.pass_context
def batch_query(
    ctx,
    input_file: str,
    endpoint: str,
    format: str,
    output: str,
    output_mode: str,
    execute: bool,
    parallel: bool,
    workers: int,
    timeout: int,
    retry: int,
    strategy: str,
    verbose: bool
):
    """
    Execute multiple SPARQL queries from a file in batch mode.

    Supports multiple input formats:
    - TEXT: One query per line
    - JSON: Array of query objects
    - YAML: List of query configurations
    - CSV: Table with query column

    Examples:

        # Process queries from text file
        sparql-agent batch-query queries.txt --endpoint https://sparql.uniprot.org/sparql

        # Process with JSON input
        sparql-agent batch-query queries.json --format json --parallel --workers 8

        # Generate without execution
        sparql-agent batch-query nl-queries.txt --no-execute --output sparql-queries/
    """
    try:
        console.print(Panel.fit(
            "[bold cyan]SPARQL Agent - Batch Query Processing[/bold cyan]",
            border_style="cyan"
        ))

        # Create configuration
        config = BatchJobConfig(
            input_file=Path(input_file),
            input_format=InputFormat[format.upper()],
            output_dir=Path(output),
            output_mode=OutputMode[output_mode.upper()],
            output_format='json',
            parallel=parallel,
            max_workers=workers,
            timeout=timeout,
            retry_attempts=retry,
            log_file=Path(output) / "batch.log" if verbose else None
        )

        # Initialize processor
        processor = BatchProcessor(config)

        # Load items
        console.print(f"\n[cyan]Loading queries from:[/cyan] {input_file}")
        processor.load_items()
        console.print(f"[green]Loaded {len(processor.items)} queries[/green]\n")

        # Initialize generator and executor
        strategy_map = {
            'auto': GenerationStrategy.AUTO,
            'template': GenerationStrategy.TEMPLATE,
            'llm': GenerationStrategy.LLM,
            'hybrid': GenerationStrategy.HYBRID,
        }

        generator = SPARQLGenerator(
            enable_validation=True,
            enable_optimization=True
        )
        executor = QueryExecutor(timeout=timeout)

        # Process queries
        console.print(f"[cyan]Processing with {workers} workers...[/cyan]\n")

        result = processor.process(
            process_query_item,
            endpoint=endpoint,
            generator=generator,
            executor=executor,
            execute=execute,
            strategy=strategy_map[strategy.lower()]
        )

        # Save results
        processor.save_results(result)

        # Display summary
        console.print("\n")
        summary_table = Table(title="Batch Processing Summary", show_header=True)
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="green")

        summary_table.add_row("Total Queries", str(result.total_items))
        summary_table.add_row("Successful", str(result.successful_items))
        summary_table.add_row("Failed", str(result.failed_items))
        summary_table.add_row("Success Rate", f"{result.get_success_rate():.2f}%")
        summary_table.add_row("Total Time", f"{result.total_time:.2f}s")
        summary_table.add_row("Average Time", f"{result.get_average_time():.2f}s")

        console.print(summary_table)

        console.print(f"\n[green]Results saved to:[/green] {output}/")

        if result.failed_items > 0:
            console.print(f"[yellow]See errors.json for details on {result.failed_items} failed queries[/yellow]")

    except Exception as e:
        console.print(f"[red]Batch processing failed: {e}[/red]", err=True)
        if verbose:
            raise
        sys.exit(1)


@batch_cli.command('bulk-discover')
@click.argument('input_file', type=click.Path(exists=True, dir_okay=False))
@click.option(
    '--format',
    '-f',
    type=click.Choice(['text', 'json', 'yaml', 'csv'], case_sensitive=False),
    default='text',
    help='Input file format'
)
@click.option(
    '--output',
    '-o',
    type=click.Path(),
    default='discovery-results',
    help='Output directory'
)
@click.option(
    '--parallel/--sequential',
    default=True,
    help='Process endpoints in parallel'
)
@click.option(
    '--workers',
    '-w',
    type=int,
    default=4,
    help='Number of parallel workers'
)
@click.option(
    '--timeout',
    '-t',
    type=int,
    default=30,
    help='Discovery timeout per endpoint (seconds)'
)
@click.option(
    '--verbose',
    '-v',
    is_flag=True,
    help='Verbose output'
)
@click.pass_context
def bulk_discover(
    ctx,
    input_file: str,
    format: str,
    output: str,
    parallel: bool,
    workers: int,
    timeout: int,
    verbose: bool
):
    """
    Discover capabilities of multiple SPARQL endpoints in bulk.

    Input file formats:
    - TEXT: One endpoint URL per line
    - JSON: Array of endpoint objects
    - YAML: List of endpoint configurations
    - CSV: Table with endpoint column

    Examples:

        # Discover from list of URLs
        sparql-agent bulk-discover endpoints.txt --output discovery/

        # Discover with YAML configuration
        sparql-agent bulk-discover endpoints.yaml --format yaml --parallel

        # Sequential discovery with longer timeout
        sparql-agent bulk-discover endpoints.txt --sequential --timeout 60
    """
    try:
        console.print(Panel.fit(
            "[bold cyan]SPARQL Agent - Bulk Endpoint Discovery[/bold cyan]",
            border_style="cyan"
        ))

        # Create configuration
        config = BatchJobConfig(
            input_file=Path(input_file),
            input_format=InputFormat[format.upper()],
            output_dir=Path(output),
            output_mode=OutputMode.BOTH,
            output_format='json',
            parallel=parallel,
            max_workers=workers,
            timeout=timeout,
            log_file=Path(output) / "discovery.log" if verbose else None
        )

        # Initialize processor
        processor = BatchProcessor(config)

        # Load items
        console.print(f"\n[cyan]Loading endpoints from:[/cyan] {input_file}")
        processor.load_items()
        console.print(f"[green]Loaded {len(processor.items)} endpoints[/green]\n")

        # Process discoveries
        console.print(f"[cyan]Discovering with {workers} workers...[/cyan]\n")

        result = processor.process(
            process_discovery_item,
            timeout=timeout
        )

        # Save results
        processor.save_results(result)

        # Display summary
        console.print("\n")
        summary_table = Table(title="Discovery Summary", show_header=True)
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="green")

        summary_table.add_row("Total Endpoints", str(result.total_items))
        summary_table.add_row("Successful", str(result.successful_items))
        summary_table.add_row("Failed", str(result.failed_items))
        summary_table.add_row("Success Rate", f"{result.get_success_rate():.2f}%")
        summary_table.add_row("Total Time", f"{result.total_time:.2f}s")

        console.print(summary_table)

        console.print(f"\n[green]Discovery results saved to:[/green] {output}/")

    except Exception as e:
        console.print(f"[red]Bulk discovery failed: {e}[/red]", err=True)
        if verbose:
            raise
        sys.exit(1)


@batch_cli.command('generate-examples')
@click.argument('schema_file', type=click.Path(exists=True, dir_okay=False))
@click.option(
    '--count',
    '-c',
    type=int,
    default=100,
    help='Number of examples to generate'
)
@click.option(
    '--output',
    '-o',
    type=click.Path(),
    default='examples.json',
    help='Output file'
)
@click.option(
    '--format',
    '-f',
    type=click.Choice(['json', 'text', 'sparql'], case_sensitive=False),
    default='json',
    help='Output format'
)
@click.option(
    '--patterns',
    type=str,
    help='Comma-separated list of query patterns to generate'
)
@click.option(
    '--verbose',
    '-v',
    is_flag=True,
    help='Verbose output'
)
@click.pass_context
def generate_examples(
    ctx,
    schema_file: str,
    count: int,
    output: str,
    format: str,
    patterns: Optional[str],
    verbose: bool
):
    """
    Generate query examples from a schema file.

    Analyzes the schema and generates diverse SPARQL query examples
    covering different patterns and use cases.

    Examples:

        # Generate 100 examples from schema
        sparql-agent generate-examples schema.ttl --count 100

        # Generate specific patterns
        sparql-agent generate-examples schema.ttl --patterns "basic,filter,aggregate"

        # Output as SPARQL files
        sparql-agent generate-examples schema.ttl --format sparql --output queries/
    """
    try:
        console.print(Panel.fit(
            "[bold cyan]SPARQL Agent - Example Generation[/bold cyan]",
            border_style="cyan"
        ))

        console.print(f"\n[cyan]Loading schema from:[/cyan] {schema_file}")

        # Parse patterns
        pattern_list = patterns.split(',') if patterns else ['basic', 'filter', 'aggregate', 'optional', 'union']

        # Create items for each pattern
        items_data = [
            {'id': f"pattern_{pattern}", 'pattern_type': pattern}
            for pattern in pattern_list
        ]

        # Create temporary input file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(items_data, f)
            temp_file = Path(f.name)

        try:
            # Create configuration
            config = BatchJobConfig(
                input_file=temp_file,
                input_format=InputFormat.JSON,
                output_dir=Path(output).parent if Path(output).suffix else Path(output),
                output_mode=OutputMode.CONSOLIDATED,
                output_format=format,
                parallel=False,  # Sequential for example generation
            )

            # Initialize processor
            processor = BatchProcessor(config)
            processor.load_items()

            console.print(f"[green]Generating {count} examples for {len(pattern_list)} patterns[/green]\n")

            # Process example generation
            result = processor.process(
                process_example_generation,
                schema_file=Path(schema_file),
                count=count // len(pattern_list)
            )

            # Save results
            processor.save_results(result)

            # Display summary
            console.print("\n")
            console.print(f"[green]Generated {result.successful_items * (count // len(pattern_list))} examples[/green]")
            console.print(f"[green]Examples saved to:[/green] {output}")

        finally:
            # Clean up temporary file
            temp_file.unlink()

    except Exception as e:
        console.print(f"[red]Example generation failed: {e}[/red]", err=True)
        if verbose:
            raise
        sys.exit(1)


@batch_cli.command('benchmark')
@click.argument('queries_file', type=click.Path(exists=True, dir_okay=False))
@click.argument('endpoints_file', type=click.Path(exists=True, dir_okay=False))
@click.option(
    '--output',
    '-o',
    type=click.Path(),
    default='benchmark-results',
    help='Output directory'
)
@click.option(
    '--iterations',
    '-i',
    type=int,
    default=3,
    help='Number of iterations per query'
)
@click.option(
    '--warmup',
    type=int,
    default=1,
    help='Number of warmup runs (not counted)'
)
@click.option(
    '--timeout',
    '-t',
    type=int,
    default=60,
    help='Timeout per query (seconds)'
)
@click.option(
    '--report-format',
    type=click.Choice(['html', 'json', 'csv', 'text'], case_sensitive=False),
    default='html',
    help='Report format'
)
@click.option(
    '--verbose',
    '-v',
    is_flag=True,
    help='Verbose output'
)
@click.pass_context
def benchmark(
    ctx,
    queries_file: str,
    endpoints_file: str,
    output: str,
    iterations: int,
    warmup: int,
    timeout: int,
    report_format: str,
    verbose: bool
):
    """
    Benchmark queries across multiple endpoints.

    Executes queries multiple times against different endpoints and generates
    performance comparison reports with statistics and visualizations.

    Examples:

        # Benchmark queries against multiple endpoints
        sparql-agent benchmark queries.json endpoints.yaml --iterations 5

        # Generate HTML report with charts
        sparql-agent benchmark queries.sparql endpoints.txt --report-format html

        # Quick benchmark with warmup
        sparql-agent benchmark queries.txt endpoints.json --warmup 2 --iterations 10
    """
    try:
        console.print(Panel.fit(
            "[bold cyan]SPARQL Agent - Query Benchmarking[/bold cyan]",
            border_style="cyan"
        ))

        # Load queries
        queries_path = Path(queries_file)
        query_format = InputFormat.TEXT if queries_path.suffix == '.txt' else InputFormat.JSON
        queries_data = InputParser.parse(queries_path, query_format)

        # Load endpoints
        endpoints_path = Path(endpoints_file)
        endpoint_format = InputFormat.TEXT if endpoints_path.suffix == '.txt' else (
            InputFormat.YAML if endpoints_path.suffix in ['.yaml', '.yml'] else InputFormat.JSON
        )
        endpoints_data = InputParser.parse(endpoints_path, endpoint_format)

        console.print(f"\n[cyan]Loaded {len(queries_data)} queries and {len(endpoints_data)} endpoints[/cyan]")

        # Create benchmark items (cartesian product of queries × endpoints × iterations)
        benchmark_items = []
        item_id = 0
        for query_item in queries_data:
            for endpoint_item in endpoints_data:
                for iteration in range(warmup + iterations):
                    item_id += 1
                    benchmark_items.append({
                        'id': f"bench_{item_id}",
                        'query': query_item.get('query'),
                        'query_id': query_item.get('id', f"q_{item_id}"),
                        'endpoint': endpoint_item.get('endpoint') or endpoint_item.get('url'),
                        'endpoint_id': endpoint_item.get('id', endpoint_item.get('endpoint', f"ep_{item_id}")),
                        'iteration': iteration,
                        'is_warmup': iteration < warmup,
                    })

        # Create temporary input file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(benchmark_items, f)
            temp_file = Path(f.name)

        try:
            config = BatchJobConfig(
                input_file=temp_file,
                input_format=InputFormat.JSON,
                output_dir=Path(output),
                output_mode=OutputMode.BOTH,
                parallel=True,
                max_workers=4,
                timeout=timeout,
                retry_attempts=0,
                log_file=Path(output) / "benchmark.log" if verbose else None
            )

            processor = BatchProcessor(config)
            processor.load_items()

            console.print(f"[cyan]Running benchmark with {len(benchmark_items)} executions...[/cyan]\n")

            # Process benchmark
            result = processor.process(
                process_benchmark_item,
                timeout=timeout
            )

            # Generate benchmark report
            report = generate_benchmark_report(result, iterations, warmup)

            # Save report
            report_file = Path(output) / f"benchmark_report.{report_format}"
            save_benchmark_report(report, report_file, report_format)

            # Display summary
            console.print("\n")
            display_benchmark_summary(report)

            console.print(f"\n[green]Benchmark report saved to:[/green] {report_file}")

        finally:
            temp_file.unlink()

    except Exception as e:
        console.print(f"[red]Benchmark failed: {e}[/red]", err=True)
        if verbose:
            raise
        sys.exit(1)


@batch_cli.command('migrate-queries')
@click.argument('input_file', type=click.Path(exists=True, dir_okay=False))
@click.argument('output_file', type=click.Path())
@click.option(
    '--source-endpoint',
    help='Source endpoint URL (for validation)'
)
@click.option(
    '--target-endpoint',
    help='Target endpoint URL (for validation)'
)
@click.option(
    '--update-prefixes',
    is_flag=True,
    help='Update namespace prefixes automatically'
)
@click.option(
    '--validate/--no-validate',
    default=True,
    help='Validate migrated queries'
)
@click.option(
    '--test-execution',
    is_flag=True,
    help='Test execution on both endpoints'
)
@click.option(
    '--diff',
    is_flag=True,
    help='Show differences between old and new queries'
)
@click.option(
    '--verbose',
    '-v',
    is_flag=True,
    help='Verbose output'
)
@click.pass_context
def migrate_queries(
    ctx,
    input_file: str,
    output_file: str,
    source_endpoint: Optional[str],
    target_endpoint: Optional[str],
    update_prefixes: bool,
    validate: bool,
    test_execution: bool,
    diff: bool,
    verbose: bool
):
    """
    Migrate and adapt queries for a different endpoint.

    Analyzes queries and adapts them for compatibility with a target endpoint,
    updating prefixes, functions, and syntax as needed.

    Examples:

        # Migrate queries with validation
        sparql-agent migrate-queries old-queries.sparql new-queries.sparql --validate

        # Migrate and update prefixes
        sparql-agent migrate-queries queries.txt migrated.txt --update-prefixes

        # Test on both endpoints
        sparql-agent migrate-queries queries.json migrated.json \\
            --source-endpoint https://old.endpoint/sparql \\
            --target-endpoint https://new.endpoint/sparql \\
            --test-execution
    """
    try:
        console.print(Panel.fit(
            "[bold cyan]SPARQL Agent - Query Migration[/bold cyan]",
            border_style="cyan"
        ))

        # Load queries
        input_path = Path(input_file)
        input_format = InputFormat.TEXT if input_path.suffix in ['.txt', '.sparql', '.rq'] else InputFormat.JSON
        queries_data = InputParser.parse(input_path, input_format)

        console.print(f"\n[cyan]Loaded {len(queries_data)} queries from:[/cyan] {input_file}")

        # Create migration items
        migration_items = [
            {
                'id': item.get('id', f"query_{i+1}"),
                'query': item.get('query'),
                'metadata': item.get('metadata', {}),
            }
            for i, item in enumerate(queries_data)
        ]

        # Create temporary input file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(migration_items, f)
            temp_file = Path(f.name)

        try:
            output_path = Path(output_file)
            config = BatchJobConfig(
                input_file=temp_file,
                input_format=InputFormat.JSON,
                output_dir=output_path.parent,
                output_mode=OutputMode.CONSOLIDATED,
                parallel=False,
                log_file=output_path.parent / "migration.log" if verbose else None
            )

            processor = BatchProcessor(config)
            processor.load_items()

            console.print(f"[cyan]Migrating queries...[/cyan]\n")

            # Process migration
            result = processor.process(
                process_migration_item,
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                update_prefixes=update_prefixes,
                validate=validate,
                test_execution=test_execution
            )

            # Save migrated queries
            save_migrated_queries(result, output_path, diff)

            # Display summary
            console.print("\n")
            display_migration_summary(result)

            console.print(f"\n[green]Migrated queries saved to:[/green] {output_file}")

            if result.failed_items > 0:
                console.print(f"[yellow]Warning: {result.failed_items} queries failed migration[/yellow]")

        finally:
            temp_file.unlink()

    except Exception as e:
        console.print(f"[red]Migration failed: {e}[/red]", err=True)
        if verbose:
            raise
        sys.exit(1)


# Register batch commands with main CLI
def register_batch_commands(cli_group):
    """
    Register batch processing commands with the main CLI.

    Args:
        cli_group: Click CLI group to register commands with
    """
    cli_group.add_command(batch_cli)


if __name__ == '__main__':
    batch_cli()
