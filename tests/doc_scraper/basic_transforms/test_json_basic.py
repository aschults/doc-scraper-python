"""Test the basic, JSON-based transformations."""

import unittest

from doc_scraper.basic_transforms import json_basic
from doc_scraper import doc_struct

DATA = {
    'a': {
        'x': {
            'v': 10,
            'n': [1, 2, 3],
        }
    },
    'b': {
        'x': {
            'v': 11,
            'n': [4, 5, 6],
        },
        'y': {
            'v': 12,
            'n': [7, 8, 9],
        }
    },
}


class TestJsonExtractionConfig(unittest.TestCase):
    """Test the JsonExtraction transformation config."""

    def test_transform_items_minimal(self):
        """Test minimal extraction."""
        config = json_basic.JsonExtractionTransformConfig(
            extract_all='..|.v? | select(.)')
        result = config.transform_items(DATA)
        self.assertEqual([10, 11, 12], result)

    def test_transform_items_minimal_render(self):
        """Test minimal extraction with rendering expression."""
        config = json_basic.JsonExtractionTransformConfig(
            extract_all='..|.x? | select(.)', render='.v')
        result = config.transform_items(DATA)
        self.assertEqual([10, 11], result)

    def test_transform_items_first_only(self):
        """Test first_item_only flag."""
        config = json_basic.JsonExtractionTransformConfig(
            extract_all='..|.x? | select(.)',
            render='.v',
            first_item_only=True)
        result = config.transform_items(DATA)
        self.assertEqual(10, result)

    def test_transform_items_no_match(self):
        """Test extraction with no match."""
        config = json_basic.JsonExtractionTransformConfig(
            extract_all='..|.x? | select(1==0)')
        result = config.transform_items(DATA)
        self.assertEqual([], result)

    def test_transform_items_filter(self):
        """Test filtering."""
        config = json_basic.JsonExtractionTransformConfig(
            extract_all='..|.v? | select(.)', filters=['. > 10', '. < 12'])
        result = config.transform_items(DATA)
        self.assertEqual([11], result)

    def test_transform_items_filter_no_output(self):
        """Test filtering with filter producing empty output."""
        config = json_basic.JsonExtractionTransformConfig(
            extract_all='..|.v? | select(.)', filters=['select(1==0)'])
        result = config.transform_items(DATA)
        self.assertEqual([], result)

    def test_transform_items_minimal_nested(self):
        """Test nested rendering with variables."""
        nested_config = json_basic.JsonExtractionTransformConfig(
            extract_all='.n[]', render='.*10')
        nested_config2 = json_basic.JsonExtractionTransformConfig(
            extract_all='.n[]', render='.*11')
        config = json_basic.JsonExtractionTransformConfig(
            extract_all='..|.x? | select(.)',
            render='{"v": .v, "n": $nest, "n2": $nest2}',
            nested={
                'nest': nested_config,
                'nest2': nested_config2
            })
        result = config.transform_items(DATA)
        expected = [{
            'n': [10, 20, 30],
            'n2': [11, 22, 33],
            'v': 10
        }, {
            'n': [40, 50, 60],
            'n2': [44, 55, 66],
            'v': 11
        }]
        self.assertEqual(expected, result)

    def test_transform_items_convert_doc_struct(self):
        """Test implicit conversion from doc_stuct to JSON."""
        config = json_basic.JsonExtractionTransformConfig(extract_all='.',
                                                          render='.tags.label')
        result = config.transform_items(
            doc_struct.Element(tags={'label': 'here'}))
        self.assertEqual(['here'], result)
