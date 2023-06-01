"""Test the basic transformations for all elements."""

import re
import unittest

from doc_scraper import doc_struct
from doc_scraper.basic_transforms import paragraph_element_basic
from doc_scraper.basic_transforms import tags_basic


class TestRegexReplace(unittest.TestCase):
    """Test regex replacement."""

    def test_replace_single(self):
        """Test simple replacement."""
        replacer = paragraph_element_basic.RegexReplacerConfig(substitutions=[
            paragraph_element_basic.RegexReplaceRule(
                regex=re.compile('x'),
                substitute='y',
            )
        ])

        self.assertEqual('ayc', replacer.transform_text('axc'))

    def test_replace_non_match(self):
        """Test non-matching replacement."""
        replacer = paragraph_element_basic.RegexReplacerConfig(substitutions=[
            paragraph_element_basic.RegexReplaceRule(
                regex=re.compile('x'),
                substitute='y',
            )
        ])

        self.assertEqual('abc', replacer.transform_text('abc'))

    def test_replace_chained(self):
        """Test chained replacements"""
        replacer = paragraph_element_basic.RegexReplacerConfig(substitutions=[
            paragraph_element_basic.RegexReplaceRule(
                regex=re.compile('x'),
                substitute='y',
            ),
            paragraph_element_basic.RegexReplaceRule(
                regex=re.compile('ay'),
                substitute='U',
            )
        ])

        self.assertEqual('Uc', replacer.transform_text('axc'))

    def test_replace_operations(self):
        """Test operations."""
        data = [
            ('upper', '_XY_12'),
            ('lower', '_xy_12'),
        ]
        for (operation, expected) in data:
            replacer = paragraph_element_basic.RegexReplacerConfig(
                substitutions=[
                    paragraph_element_basic.RegexReplaceRule(
                        regex=re.compile('^(..)'),
                        substitute=r'_\1_',
                        operation=operation)
                ])
            self.assertEqual(expected, replacer.transform_text('xY12'))

    def test_replace_bad_operation(self):
        """Test bad operations."""
        replacer = paragraph_element_basic.RegexReplacerConfig(substitutions=[
            paragraph_element_basic.RegexReplaceRule(regex=re.compile('^(..)'),
                                                     substitute=r'_\1_',
                                                     operation='bad_value')
        ])
        self.assertRaisesRegex(ValueError, 'Unknown substitution',
                               lambda: replacer.transform_text(''))


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
        config = paragraph_element_basic.RegexReplacerConfig(
            match=tags_basic.TagMatchConfig(required_tag_sets=[['A']]),
            substitutions=[
                paragraph_element_basic.RegexReplaceRule(regex=re.compile('.'),
                                                         substitute='X'),
            ])

        data = doc_struct.Paragraph(elements=[
            doc_struct.TextRun(attrs={'tags': {'A'}}, text='r1'),
            doc_struct.TextRun(attrs={'tags': {}}, text='r2'),
        ])

        expected = doc_struct.Paragraph(elements=[
            doc_struct.TextRun(attrs={'tags': {'A'}}, text='XX'),
            doc_struct.TextRun(attrs={'tags': {}}, text='r2'),
        ])

        self.assertEqual(
            expected,
            paragraph_element_basic.RegexReplacerTransform(
                config=config)(data))
