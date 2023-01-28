"""Test the basic transformations for all elements."""

import unittest

from doc_scraper.basic_transforms import elements_basics
from doc_scraper import doc_struct


class TestStripElements(unittest.TestCase):
    """Test the Strip elements transformation."""

    def test_simple_transform(self):
        """Test a simple transformation."""
        transform = elements_basics.StripElementsTransform(
            remove_attrs_re=['_.*'],
            remove_styles_re=['-.*', '0.*'],
            remove_style_rules_re=['x.*'])

        data = doc_struct.SharedData(
            attrs={
                'k0': 0,
                '_k1': 1
            },
            style={
                '-s0': 'a',
                's1': 'b',
                '0s2': 'c',
            },
            style_rules={
                'ok': {},
                'xbad': {}
            },
        )
        expected = doc_struct.SharedData(
            attrs={'k0': 0},
            style={'s1': 'b'},
            style_rules={'ok': {}},
        )
        self.assertEqual(expected, transform(data))

    def test_empty_lists(self):
        """Test with empty config."""
        transform = elements_basics.StripElementsTransform(
            remove_attrs_re=[],
            remove_styles_re=[],
            remove_style_rules_re=[])

        data = doc_struct.SharedData(
            attrs={
                'k0': 0,
                '_k1': 1
            },
            style={
                '-s0': 'a',
                's1': 'b',
                '0s2': 'c',
            },
            style_rules={
                'ok': {},
                'xbad': {}
            },
        )
        self.assertEqual(data, transform(data))
