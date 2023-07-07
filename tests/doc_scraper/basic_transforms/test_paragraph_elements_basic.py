"""Test the basic transformations for all elements."""

import unittest

from doc_scraper import doc_struct
from doc_scraper.basic_transforms import paragraph_element_basic
from doc_scraper.basic_transforms import tags_basic


class _SampleTextTransform(paragraph_element_basic.TextTransformBase):

    def __init__(self, match: int) -> None:
        super().__init__()
        self.match = match

    def _is_matching(self, element: doc_struct.Element) -> bool:
        return element.attrs.get('a', 0) == self.match

    def _process_text_string(self, text: str | None) -> str:
        return f'{text}{self.match}'


class TestTextTransformBase(unittest.TestCase):
    """Test base class for text transforms."""

    def test_simple_transform(self):
        """Transform a simple element tree."""
        data = doc_struct.Paragraph(elements=[
            doc_struct.TextRun(attrs={'a': 1}, text='run'),
            doc_struct.Chip(attrs={'a': 2}, text='chip'),
            doc_struct.Link(attrs={'a': 1}, text='link'),
            doc_struct.TextLine(elements=[
                doc_struct.Reference(attrs={'a': 1}, url='x', text='ref'),
                doc_struct.ReferenceTarget(
                    attrs={'a': 2}, ref_id='x', text='ref_target'),
            ]),
        ])

        expected1 = doc_struct.Paragraph(elements=[
            doc_struct.TextRun(attrs={'a': 1}, text='run1'),
            doc_struct.Chip(attrs={'a': 2}, text='chip'),
            doc_struct.Link(attrs={'a': 1}, text='link1'),
            doc_struct.TextLine(elements=[
                doc_struct.Reference(attrs={'a': 1}, url='x', text='ref1'),
                doc_struct.ReferenceTarget(
                    attrs={'a': 2}, ref_id='x', text='ref_target'),
            ]),
        ])

        expected2 = doc_struct.Paragraph(elements=[
            doc_struct.TextRun(attrs={'a': 1}, text='run'),
            doc_struct.Chip(attrs={'a': 2}, text='chip2'),
            doc_struct.Link(attrs={'a': 1}, text='link'),
            doc_struct.TextLine(elements=[
                doc_struct.Reference(attrs={'a': 1}, url='x', text='ref'),
                doc_struct.ReferenceTarget(
                    attrs={'a': 2}, ref_id='x', text='ref_target2'),
            ]),
        ])

        self.assertEqual(expected1, _SampleTextTransform(1)(data))
        self.assertEqual(expected2, _SampleTextTransform(2)(data))


class TestRegexReplacerTransform(unittest.TestCase):
    """Test regex replacer class."""

    def test_simple_transform(self):
        """Transform a simple text, marked by tag."""
        config = paragraph_element_basic.RegexReplacerConfig(
            match=tags_basic.TagMatchConfig(
                required_tag_sets=[tags_basic.MappingMatcher.tags('A')]),
            substitutions=[
                tags_basic.RegexReplaceRule(
                    regex=tags_basic.StringMatcher('.'), substitute='X'),
            ])

        data = doc_struct.Paragraph(elements=[
            doc_struct.TextRun(tags=doc_struct.tags_for('A'), text='r1'),
            doc_struct.TextRun(text='r2'),
        ])

        expected = doc_struct.Paragraph(elements=[
            doc_struct.TextRun(tags=doc_struct.tags_for('A'), text='XX'),
            doc_struct.TextRun(text='r2'),
        ])

        self.assertEqual(
            expected,
            paragraph_element_basic.RegexReplacerTransform(
                config=config)(data))
