"""
Unit tests for the statistics module.

Tests the StatisticsCollector and DatasetStatistics classes.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from statistics import (
    DatasetStatistics,
    StatisticsCollector,
    collect_statistics
)


class TestDatasetStatistics(unittest.TestCase):
    """Test DatasetStatistics class."""

    def test_initialization(self):
        """Test basic initialization."""
        stats = DatasetStatistics()
        self.assertEqual(stats.total_triples, 0)
        self.assertEqual(stats.distinct_subjects, 0)
        self.assertEqual(len(stats.top_classes), 0)

    def test_to_dict(self):
        """Test conversion to dictionary."""
        stats = DatasetStatistics(
            total_triples=1000,
            distinct_subjects=500,
            top_classes=[("http://example.org/Class1", 100)],
            endpoint_url="http://example.org/sparql"
        )

        result = stats.to_dict()

        self.assertIn('basic_counts', result)
        self.assertEqual(result['basic_counts']['total_triples'], 1000)
        self.assertEqual(result['basic_counts']['distinct_subjects'], 500)
        self.assertEqual(result['metadata']['endpoint_url'], "http://example.org/sparql")

    def test_summary(self):
        """Test summary generation."""
        stats = DatasetStatistics(
            total_triples=1000,
            distinct_subjects=500,
            top_classes=[("http://example.org/Class1", 100)],
            endpoint_url="http://example.org/sparql",
            collection_time="2024-01-01T00:00:00",
            collection_duration_seconds=5.5
        )

        summary = stats.summary()

        self.assertIn("Total Triples: 1,000", summary)
        self.assertIn("Distinct Subjects: 500", summary)
        self.assertIn("http://example.org/sparql", summary)
        self.assertIn("Duration: 5.50s", summary)


class TestStatisticsCollector(unittest.TestCase):
    """Test StatisticsCollector class."""

    def setUp(self):
        """Set up test fixtures."""
        self.endpoint_url = "http://example.org/sparql"
        self.collector = StatisticsCollector(
            endpoint_url=self.endpoint_url,
            timeout=10,
            cache_results=True
        )

    def test_initialization(self):
        """Test collector initialization."""
        self.assertEqual(self.collector.endpoint_url, self.endpoint_url)
        self.assertEqual(self.collector.timeout, 10)
        self.assertTrue(self.collector.cache_results)
        self.assertEqual(len(self.collector._cache), 0)

    def test_extract_single_value(self):
        """Test extracting single value from results."""
        results = {
            'results': {
                'bindings': [
                    {'count': {'value': '42'}}
                ]
            }
        }

        value = self.collector._extract_single_value(results, 'count')
        self.assertEqual(value, 42)

    def test_extract_single_value_empty(self):
        """Test extracting from empty results."""
        results = {'results': {'bindings': []}}
        value = self.collector._extract_single_value(results, 'count')
        self.assertEqual(value, 0)

    def test_extract_counts(self):
        """Test extracting key-count pairs."""
        results = {
            'results': {
                'bindings': [
                    {
                        'class': {'value': 'http://example.org/Class1'},
                        'count': {'value': '100'}
                    },
                    {
                        'class': {'value': 'http://example.org/Class2'},
                        'count': {'value': '50'}
                    }
                ]
            }
        }

        counts = self.collector._extract_counts(results, 'class', 'count')

        self.assertEqual(len(counts), 2)
        self.assertEqual(counts[0], ('http://example.org/Class1', 100))
        self.assertEqual(counts[1], ('http://example.org/Class2', 50))

    @patch('statistics.SPARQLWrapper')
    def test_count_total_triples(self, mock_sparql_wrapper):
        """Test counting total triples."""
        # Mock the SPARQL query result
        mock_instance = MagicMock()
        mock_instance.queryAndConvert.return_value = {
            'results': {
                'bindings': [
                    {'triples': {'value': '1000'}}
                ]
            }
        }
        mock_sparql_wrapper.return_value = mock_instance

        collector = StatisticsCollector(self.endpoint_url)
        collector.sparql = mock_instance

        count = collector.count_total_triples()

        self.assertEqual(count, 1000)
        mock_instance.setQuery.assert_called_once()

    @patch('statistics.SPARQLWrapper')
    def test_get_top_classes(self, mock_sparql_wrapper):
        """Test getting top classes."""
        mock_instance = MagicMock()
        mock_instance.queryAndConvert.return_value = {
            'results': {
                'bindings': [
                    {
                        'class': {'value': 'http://example.org/Class1'},
                        'count': {'value': '100'}
                    },
                    {
                        'class': {'value': 'http://example.org/Class2'},
                        'count': {'value': '50'}
                    }
                ]
            }
        }
        mock_sparql_wrapper.return_value = mock_instance

        collector = StatisticsCollector(self.endpoint_url)
        collector.sparql = mock_instance

        classes = collector.get_top_classes(limit=10)

        self.assertEqual(len(classes), 2)
        self.assertEqual(classes[0][0], 'http://example.org/Class1')
        self.assertEqual(classes[0][1], 100)

    def test_cache_functionality(self):
        """Test query result caching."""
        # Mock execute_query to test caching
        mock_results = {'test': 'data'}

        # First call - should execute
        self.collector._cache['test_key'] = mock_results
        result1 = self.collector._execute_query("SELECT * WHERE {}", cache_key='test_key')

        self.assertEqual(result1, mock_results)

        # Clear cache
        self.collector.clear_cache()
        self.assertEqual(len(self.collector._cache), 0)

    def test_get_cache_info(self):
        """Test getting cache information."""
        self.collector._cache['key1'] = 'data1'
        self.collector._cache['key2'] = 'data2'
        self.collector._query_count = 5

        info = self.collector.get_cache_info()

        self.assertEqual(info['cache_size'], 2)
        self.assertEqual(info['query_count'], 5)
        self.assertIn('key1', info['cache_keys'])
        self.assertIn('key2', info['cache_keys'])

    def test_progress_callback(self):
        """Test progress reporting."""
        callback_calls = []

        def callback(message, current=0, total=0):
            callback_calls.append((message, current, total))

        collector = StatisticsCollector(
            self.endpoint_url,
            progress_callback=callback
        )

        collector._report_progress("Test message", 1, 10)

        self.assertEqual(len(callback_calls), 1)
        self.assertEqual(callback_calls[0], ("Test message", 1, 10))

    @patch('statistics.SPARQLWrapper')
    def test_error_handling(self, mock_sparql_wrapper):
        """Test error handling and retries."""
        from SPARQLWrapper.SPARQLExceptions import SPARQLWrapperException

        mock_instance = MagicMock()
        mock_instance.queryAndConvert.side_effect = SPARQLWrapperException("Test error")
        mock_sparql_wrapper.return_value = mock_instance

        collector = StatisticsCollector(
            self.endpoint_url,
            max_retries=2,
            timeout=1
        )
        collector.sparql = mock_instance

        result = collector._execute_query("SELECT * WHERE {}")

        self.assertIsNone(result)
        # Should have been called 3 times (initial + 2 retries)
        self.assertEqual(mock_instance.queryAndConvert.call_count, 3)


class TestCollectStatistics(unittest.TestCase):
    """Test the convenience function."""

    @patch('statistics.StatisticsCollector')
    def test_collect_statistics(self, mock_collector_class):
        """Test the collect_statistics convenience function."""
        # Mock the collector instance
        mock_instance = MagicMock()
        mock_stats = DatasetStatistics(
            total_triples=1000,
            endpoint_url="http://example.org/sparql"
        )
        mock_instance.collect_all_statistics.return_value = mock_stats
        mock_collector_class.return_value = mock_instance

        # Call the function
        result = collect_statistics(
            endpoint_url="http://example.org/sparql",
            timeout=30,
            class_limit=10
        )

        # Verify
        mock_collector_class.assert_called_once()
        mock_instance.collect_all_statistics.assert_called_once()
        self.assertEqual(result.total_triples, 1000)


class TestNamespaceAnalysis(unittest.TestCase):
    """Test namespace analysis functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.collector = StatisticsCollector("http://example.org/sparql")

    @patch('statistics.SPARQLWrapper')
    def test_analyze_namespace_usage(self, mock_sparql_wrapper):
        """Test namespace usage analysis."""
        mock_instance = MagicMock()
        mock_instance.queryAndConvert.return_value = {
            'results': {
                'bindings': [
                    {
                        'p': {'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
                        'count': {'value': '100'}
                    },
                    {
                        'p': {'value': 'http://www.w3.org/2000/01/rdf-schema#label'},
                        'count': {'value': '50'}
                    },
                    {
                        'p': {'value': 'http://example.org#property1'},
                        'count': {'value': '25'}
                    }
                ]
            }
        }
        mock_sparql_wrapper.return_value = mock_instance

        collector = StatisticsCollector("http://example.org/sparql")
        collector.sparql = mock_instance

        namespaces = collector.analyze_namespace_usage()

        # Check that namespaces were properly extracted and counted
        self.assertIn('http://www.w3.org/1999/02/22-rdf-syntax-ns#', namespaces)
        self.assertIn('http://www.w3.org/2000/01/rdf-schema#', namespaces)
        self.assertIn('http://example.org#', namespaces)


class TestPatternDetection(unittest.TestCase):
    """Test pattern detection functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.collector = StatisticsCollector("http://example.org/sparql")

    @patch('statistics.SPARQLWrapper')
    def test_detect_owl_patterns(self, mock_sparql_wrapper):
        """Test OWL pattern detection."""
        mock_instance = MagicMock()

        # Mock responses for different pattern queries
        def mock_query_convert(*args, **kwargs):
            query = mock_instance.setQuery.call_args[0][0]
            if 'owl#Class' in query or 'owl#ObjectProperty' in query:
                return {
                    'results': {
                        'bindings': [
                            {'count': {'value': '50'}}
                        ]
                    }
                }
            else:
                return {
                    'results': {
                        'bindings': [
                            {'count': {'value': '0'}}
                        ]
                    }
                }

        mock_instance.queryAndConvert.side_effect = mock_query_convert
        mock_sparql_wrapper.return_value = mock_instance

        collector = StatisticsCollector("http://example.org/sparql")
        collector.sparql = mock_instance

        patterns = collector.detect_patterns()

        # Should detect OWL ontology
        self.assertIn('has_owl_ontology', patterns)
        self.assertTrue(patterns['has_owl_ontology'])
        self.assertEqual(patterns['owl_entity_count'], 50)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
