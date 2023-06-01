"""Test the basic transformations for all elements."""

from typing import Sequence
import unittest

from doc_scraper.basic_transforms import tags_basic
from doc_scraper import doc_struct


def _make_chip(tags: Sequence[str]) -> doc_struct.Element:
    return doc_struct.Chip(tags=set(tags), text='blah')


class TestTagMatching(unittest.TestCase):
    """Test matching elements by tags."""

    def test_match_all(self):
        """Test that all tags match when none given."""
        tag_match = tags_basic.TagMatchConfig()
        self.assertTrue(tag_match.is_matching(_make_chip([])))
        self.assertTrue(tag_match.is_matching(_make_chip(['A'])))
        self.assertTrue(tag_match.is_matching(_make_chip(['X'])))

    def test_single_tag_groups(self):
        """Test a match with a single required tag set."""
        tag_match = tags_basic.TagMatchConfig(required_tag_sets=[['A', 'B']])
        self.assertFalse(tag_match.is_matching(_make_chip([])))
        self.assertFalse(tag_match.is_matching(_make_chip(['X'])))
        self.assertFalse(tag_match.is_matching(_make_chip(['A'])))
        self.assertTrue(tag_match.is_matching(_make_chip(['A', 'B'])))
        self.assertTrue(tag_match.is_matching(_make_chip(['A', 'B', 'C'])))

    def test_multi_tag_groups(self):
        """Test multiple (alternatively) required tag sets."""
        tag_match = tags_basic.TagMatchConfig(
            required_tag_sets=[['A', 'B'], ['C', 'D']])
        self.assertFalse(tag_match.is_matching(_make_chip([])))
        self.assertFalse(tag_match.is_matching(_make_chip(['C'])))
        self.assertFalse(tag_match.is_matching(_make_chip(['A'])))
        self.assertFalse(tag_match.is_matching(_make_chip(['A', 'D'])))
        self.assertTrue(tag_match.is_matching(_make_chip(['A', 'B'])))
        self.assertTrue(tag_match.is_matching(_make_chip(['A', 'B', 'C',
                                                          'D'])))
        self.assertTrue(
            tag_match.is_matching(_make_chip(['A', 'B', 'C', 'D', 'X'])))
        self.assertTrue(tag_match.is_matching(_make_chip(['B', 'C', 'D'])))
        self.assertTrue(tag_match.is_matching(_make_chip(['C', 'D'])))

    def test_tag_groups_with_reject(self):
        """Test matching with rejected tags."""
        tag_match = tags_basic.TagMatchConfig(required_tag_sets=[['A', 'B']],
                                              rejected_tags=['R'])
        self.assertFalse(tag_match.is_matching(_make_chip([])))
        self.assertFalse(tag_match.is_matching(_make_chip(['R'])))
        self.assertFalse(tag_match.is_matching(_make_chip(['A', 'B', 'R'])))
        self.assertTrue(tag_match.is_matching(_make_chip(['A', 'B'])))
        self.assertTrue(tag_match.is_matching(_make_chip(['A', 'B', 'X'])))

    def test_only_reject(self):
        """Test matching all, except rejected."""
        tag_match = tags_basic.TagMatchConfig(rejected_tags=['R'])
        self.assertTrue(tag_match.is_matching(_make_chip([])))
        self.assertFalse(tag_match.is_matching(_make_chip(['R'])))
        self.assertFalse(tag_match.is_matching(_make_chip(['A', 'B', 'R'])))
        self.assertTrue(tag_match.is_matching(_make_chip(['A', 'B'])))

    def test_element_type(self):
        """Test element type constraint."""
        sample_chip = doc_struct.Chip(text='a')
        sample_run = doc_struct.TextRun(text='a')
        sample_table = doc_struct.Table(elements=[])

        self.assertTrue(
            tags_basic.TagMatchConfig(
                element_types=[doc_struct.Chip]).is_matching(sample_chip))
        self.assertTrue(
            tags_basic.TagMatchConfig(
                element_types=[doc_struct.ParagraphElement]).is_matching(
                    sample_chip))
        self.assertTrue(
            tags_basic.TagMatchConfig(
                element_types=[doc_struct.ParagraphElement]).is_matching(
                    sample_run))
        self.assertFalse(
            tags_basic.TagMatchConfig(
                element_types=[doc_struct.Heading]).is_matching(sample_chip))
        self.assertFalse(
            tags_basic.TagMatchConfig(
                element_types=[doc_struct.Heading]).is_matching(sample_table))
        self.assertTrue(
            tags_basic.TagMatchConfig(element_types=[
                doc_struct.Table,
                doc_struct.ParagraphElement,
            ]).is_matching(sample_table))
        self.assertTrue(
            tags_basic.TagMatchConfig(element_types=[
                doc_struct.Table,
                doc_struct.ParagraphElement,
            ]).is_matching(sample_run))
