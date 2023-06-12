"""Test the basic transformations for all elements."""

from typing import Sequence, Callable, Any
import unittest

from doc_scraper.basic_transforms import tags_basic
from doc_scraper import doc_struct
from parameterized import parameterized  # type:ignore


def _make_chip(tags: Sequence[str]) -> doc_struct.Element:
    return doc_struct.Chip(tags=doc_struct.tags_for(*tags), text='blah')


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
        tag_match = tags_basic.TagMatchConfig(required_tag_sets=[
            tags_basic.match_for('A', 'B'),
        ])
        self.assertFalse(tag_match.is_matching(_make_chip([])))
        self.assertFalse(tag_match.is_matching(_make_chip(['X'])))
        self.assertFalse(tag_match.is_matching(_make_chip(['A'])))
        self.assertTrue(tag_match.is_matching(_make_chip(['A', 'B'])))
        self.assertTrue(tag_match.is_matching(_make_chip(['A', 'B', 'C'])))

    def test_multi_tag_groups(self):
        """Test multiple (alternatively) required tag sets."""
        tag_match = tags_basic.TagMatchConfig(required_tag_sets=[
            tags_basic.match_for('A', 'B'),
            tags_basic.match_for('C', 'D'),
        ])
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
        tag_match = tags_basic.TagMatchConfig(
            required_tag_sets=[tags_basic.match_for('A', 'B')],
            rejected_tags=tags_basic.match_for('R'))
        self.assertFalse(tag_match.is_matching(_make_chip([])))
        self.assertFalse(tag_match.is_matching(_make_chip(['R'])))
        self.assertFalse(tag_match.is_matching(_make_chip(['A', 'B', 'R'])))
        self.assertTrue(tag_match.is_matching(_make_chip(['A', 'B'])))
        self.assertTrue(tag_match.is_matching(_make_chip(['A', 'B', 'X'])))

    def test_only_reject(self):
        """Test matching all, except rejected."""
        tag_match = tags_basic.TagMatchConfig(
            rejected_tags=tags_basic.match_for('R'))
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

    def test_match_descendents(self):
        """Test the match_descendents function."""
        data = doc_struct.Section(
            heading=None,
            content=[
                doc_struct.BulletItem(list_type='ul',
                                      elements=[doc_struct.Chip(text='here')]),
            ])
        result = tags_basic.TagMatchConfig(element_types=[
            doc_struct.Chip,
        ]).match_descendents(data)

        self.assertEqual([doc_struct.Chip(text='here')], result)


class TestFilterConversion(unittest.TestCase):
    """Test the filtering conversion class."""

    def assertSameElements(self, first: Sequence[Any],
                           second: Sequence[Any]) -> None:
        """Assert that two lists contain the same elements."""
        for item in first:
            self.assertIn(item, second)

        for item in second:
            self.assertIn(item, first)

    @staticmethod
    def _is_text_run(element: doc_struct.Element) -> bool:
        return isinstance(element, doc_struct.TextRun)

    @staticmethod
    def _is_paragraph(element: doc_struct.Element) -> bool:
        return isinstance(element, doc_struct.Paragraph)

    @staticmethod
    def _is_paragraph_or_text_run(element: doc_struct.Element) -> bool:
        """Match Paragraph or TextRun, but NOT BulletItem."""
        if isinstance(element, doc_struct.BulletItem):
            return False
        return isinstance(element, (doc_struct.Paragraph, doc_struct.TextRun))

    @parameterized.expand([  # type: ignore
        (
            "single element",
            _is_text_run,
            doc_struct.TextRun(text='simple text'),
            [
                doc_struct.TextRun(text='simple text'),
            ],
        ),
        (
            "single wrong element",
            _is_text_run,
            doc_struct.Chip(text='simple text'),
            [],
        ),
        (
            "element with descendents",
            _is_paragraph,
            doc_struct.Paragraph(
                elements=[doc_struct.TextRun(text='another text')]),
            [
                doc_struct.Paragraph(
                    elements=[doc_struct.TextRun(text='another text')])
            ],
        ),
        (
            "element with matching descendents",
            _is_text_run,
            doc_struct.Paragraph(
                elements=[doc_struct.TextRun(text='another text')]),
            [doc_struct.TextRun(text='another text')],
        ),
        (
            "element with 2 matching descendents",
            _is_text_run,
            doc_struct.Paragraph(elements=[
                doc_struct.TextRun(text='A'),
                doc_struct.Chip(text='X'),
                doc_struct.TextRun(text='B'),
            ]),
            [doc_struct.TextRun(text='A'),
             doc_struct.TextRun(text='B')],
        ),
        (
            "element with matching descendents, both matching",
            _is_paragraph_or_text_run,
            doc_struct.Paragraph(
                elements=[doc_struct.TextRun(text='another text')]),
            [
                doc_struct.Paragraph(
                    elements=[doc_struct.TextRun(text='another text')]),
                doc_struct.TextRun(text='another text')
            ],
        ),
    ])
    # pylint: disable=unused-argument
    def test_conversion(self, name: str,
                        filter_func: Callable[[doc_struct.Element],
                                              bool], data: doc_struct.Element,
                        expected: Sequence[doc_struct.Element]):
        """Test multiple filtering scenarios."""
        converter = tags_basic.ElementFilterConverter(filter_func)
        self.assertSameElements(expected, converter.convert(data))
