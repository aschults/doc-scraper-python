"""Test base module of the HTML extractor."""

import unittest
from dataclasses import asdict

from doc_scraper.html_extractor import _base


class NodeTest(unittest.TestCase):
    """Test base class."""

    def test_parse_styles(self):
        """Test main functionality, to parse styles."""
        style = """
            style-a: 111;
            style-b: 'abc';
        """
        context = _base.ParseContext()
        node = _base.Frame(context, {'style': style, 'k': 'val'})

        style_as_struct = {'style-a': '111', 'style-b': '\'abc\''}
        self.assertEqual(style_as_struct, node.style)
        self.assertEqual(
            {
                'attrs': {
                    'k': 'val',
                    'style': style
                },
                'style': style_as_struct
            }, asdict(node.to_struct()))

    def test_repr(self):
        """Test convesion to str."""
        context = _base.ParseContext()
        node = _base.Frame(context, {'k': 'val'}, {'s': '111'})

        self.assertEqual(
            "Frame(ParseContext()," +
            "'Element(attrs={'k': 'val'}, style={'s': '111'})')", repr(node))

    def test_eq(self):
        """Test equality."""
        context = _base.ParseContext()
        node = _base.Frame(context, {'k': 'val'}, {'s': '111'})

        self.assertEqual(node, _base.Frame(context, {'k': 'val'}, {'s': '111'}))
        self.assertNotEqual(node, _base.Frame(context, {}, {'s': '111'}))
        self.assertNotEqual(node,
                            _base.Frame(context, {'k': 'val'}, {'s': '222'}))
