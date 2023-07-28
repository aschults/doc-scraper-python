"""Tests for the JSON Query classes (backed by jq)."""

from typing import Any
import unittest
from unittest import mock
import re

from doc_scraper import json_query


class _MatchRegex():
    """Match string arguments in recorded calls by regex."""

    def __init__(self, regex: str) -> None:
        self.regex = re.compile(regex, re.S)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, str):
            return False
        return bool(self.regex.search(other))


class JsonQueryTest(unittest.TestCase):
    """Test JSON query functions."""

    def setUp(self) -> None:
        """Provide mocks for the jq module."""
        self.jq_patch = mock.patch('doc_scraper.json_query.jq')
        self.jq_mock: Any = self.jq_patch.start()
        self.compile_rv_mock: Any = mock.Mock()
        self.jq_mock.compile.return_value = self.compile_rv_mock
        self.input_rv_mock: Any = mock.Mock()
        self.compile_rv_mock.input.return_value = self.input_rv_mock
        self.addClassCleanup(self.jq_patch.stop)
        return super().setUp()

    def test_get_all(self):
        """Test get_all."""
        self.input_rv_mock.all.return_value = [1, 2, 3]
        query = json_query.Query('_expr_')

        self.assertEqual([1, 2, 3], query.get_all('_in_'))

        self.jq_mock.compile.assert_called_with(_MatchRegex('_expr_'))
        self.compile_rv_mock.input.assert_called_with(value={
            '_vars': [],
            '_content': '_in_'
        })
        self.input_rv_mock.all.assert_called_with()

    def test_get_first(self):
        """Test get_first."""
        self.input_rv_mock.first.return_value = 999
        query = json_query.Query('_expr_')

        self.assertEqual(999, query.get_first('_in_'))

        self.jq_mock.compile.assert_called_with(_MatchRegex('_expr_'))
        self.compile_rv_mock.input.assert_called_with(value={
            '_vars': [],
            '_content': '_in_'
        })
        self.input_rv_mock.first.assert_called_with()

    def test_get_first_no_output(self):
        """Test get_first when no output is returned."""
        self.input_rv_mock.first.side_effect = StopIteration()
        query = json_query.Query('_expr_')

        self.assertIsInstance(query.get_first('_in_'), json_query.NoOutput)

        self.jq_mock.compile.assert_called_with(_MatchRegex('_expr_'))
        self.compile_rv_mock.input.assert_called_with(value={
            '_vars': [],
            '_content': '_in_'
        })
        self.input_rv_mock.first.assert_called_with()

    def test_set_args(self):
        """Test setting variables, triggering recompilation."""
        self.input_rv_mock.all.return_value = [1, 2, 3]
        query = json_query.Query('_expr_', var='val', var_names=['other_var'])
        self.jq_mock.compile.assert_called_with(
            _MatchRegex('other_var.*_expr_'), args={'var': 'val'})
        self.jq_mock.compile.reset_mock()

        self.assertEqual([1, 2, 3], query.get_all('_in_'))
        self.compile_rv_mock.input.assert_called_with(value={
            '_vars': [None],
            '_content': '_in_'
        })

        self.assertEqual([1, 2, 3], query.get_all('_in_', other_var='val2'))
        self.compile_rv_mock.input.assert_called_with(value={
            '_vars': ['val2'],
            '_content': '_in_'
        })
        self.jq_mock.compile.assert_not_called()


class JsonQueryDeepTest(unittest.TestCase):
    """Run JQ tests without mocks."""

    def test_eval(self):
        """Compile and execute some queries."""
        self.assertEqual(222, json_query.Query('.x').get_first({'x': 222}))
        self.assertEqual([222, 333],
                         json_query.Query('.[].x').get_all([{
                             'x': 222
                         }, {
                             'x': 333
                         }]))
        self.assertEqual(
            123,
            json_query.Query('$v', var_names=['v']).get_first({'x': 222},
                                                              v=123))
        self.assertEqual(
            None,
            json_query.Query('$v', var_names=['v']).get_first({'x': 222}))
        self.assertEqual(
            123,
            json_query.Query('$c', var_names=['v'],
                             c=123).get_first({'x': 222}))
        self.assertEqual(
            123,
            json_query.Query('.| f',
                             preamble='def f: 123').get_first({'x': 222}))

        self.assertEqual(
            123,
            json_query.Query('.| f',
                             preamble='def f: 123;').get_first({'x': 222}))


class FilterTest(unittest.TestCase):
    """Test JSON query functions."""

    def setUp(self) -> None:
        """Mock _jq_compile to work without jq."""
        self.jq_patch = mock.patch('doc_scraper.json_query._jq_compile')
        self.jq_mock = self.jq_patch.start()
        self.addClassCleanup(self.jq_patch.stop)
        return super().setUp()

    def test_filter(self):
        """Test filtering."""
        self.jq_mock().input().first.return_value = True
        filt = json_query.Filter('_a_', '_b_')

        self.assertEqual(['_in_'], filt.filter(['_in_']))

        print(self.jq_mock.mock_calls)

        self.assertIn(mock.call(_MatchRegex('_a_'), args={}),
                      self.jq_mock.mock_calls)
        self.assertIn(mock.call(_MatchRegex('_b_'), args={}),
                      self.jq_mock.mock_calls)

    def test_filter_none(self):
        """Test filtering when filters are false."""
        self.jq_mock().input().first.return_value = False
        filt = json_query.Filter('_a_', '_b_')

        self.assertEqual([], filt.filter(['_in_']))

    def test_filter_none2(self):
        """Test filtering when only one fails."""
        self.jq_mock().input().first.side_effect = [False, True]
        filt = json_query.Filter('_a_', '_b_')

        self.assertEqual([], filt.filter(['_in_']))

    def test_filter_no_output(self):
        """Test filtering when no output is returned."""
        self.jq_mock().input().first.side_effect = StopIteration
        filt = json_query.Filter('_a_', '_b_')

        self.assertEqual([], filt.filter(['_in_']))

    def test_get_unmatched(self):
        """Test get_unmatched."""
        self.jq_mock().input().first.side_effect = [False, True]
        filt = json_query.Filter('_a_', '_b_')

        self.assertEqual([json_query.Query('_a_')],
                         filt.get_unmatched(['_in_']))
