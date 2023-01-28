"""Test the basic transformations for paragraphs."""
# pylint: disable=protected-access

import unittest
from typing import Sequence

from parameterized import parameterized  # type: ignore

from doc_scraper.basic_transforms import paragraph_basic
from doc_scraper import doc_struct


class TextBreakTest(unittest.TestCase):
    """Test the Text break transformation."""

    @parameterized.expand([  # type: ignore
        (
            "single line",
            [doc_struct.TextRun(text='simple text')],
            [
                doc_struct.TextLine(
                    elements=[doc_struct.TextRun(text='simple text')])
            ],
        ),
        (
            "two lines",
            [doc_struct.TextRun(text='simple\ntext')],
            [
                doc_struct.TextLine(elements=[
                    doc_struct.TextRun(text='simple'),
                    doc_struct.TextRun(text='\n')
                ]),
                doc_struct.TextLine(elements=[doc_struct.TextRun(text='text')])
            ],
        ),
        (
            "empty",
            [],
            [],
        ),
        (
            "two items one line",
            [
                doc_struct.TextRun(text='simple'),
                doc_struct.TextRun(text='text')
            ],
            [
                doc_struct.TextLine(elements=[
                    doc_struct.TextRun(text='simple'),
                    doc_struct.TextRun(text='text')
                ])
            ],
        ),
        (
            "empty lines",
            [doc_struct.TextRun(text='\nsimple\n\ntext\n')],
            [
                doc_struct.TextLine(elements=[
                    doc_struct.TextRun(text='\n'),
                ]),
                doc_struct.TextLine(elements=[
                    doc_struct.TextRun(text='simple'),
                    doc_struct.TextRun(text='\n')
                ]),
                doc_struct.TextLine(elements=[
                    doc_struct.TextRun(text='\n'),
                ]),
                doc_struct.TextLine(elements=[
                    doc_struct.TextRun(text='text'),
                    doc_struct.TextRun(text='\n')
                ]),
            ],
        ),
    ])
    # pylint: disable=unused-argument
    def test_break_function(self, name: str,
                            data: Sequence[doc_struct.ParagraphElement],
                            expected: Sequence[doc_struct.ParagraphElement]):
        """Run all tests."""
        self.assertEqual(expected,
                         paragraph_basic._break_text(data))  # type: ignore


style1 = {'a': '1'}
style2 = {'a': '2'}
style3 = {'a': '3'}


class TextMergeTest(unittest.TestCase):
    """Test the TextMerge transform."""

    @parameterized.expand([  # type: ignore
        (
            "single run",
            doc_struct.Paragraph(elements=[
                doc_struct.TextRun(style=style1, text='first'),
            ]),
            doc_struct.Paragraph(elements=[
                doc_struct.TextRun(style=style1, text='first'),
            ]),
        ),
        (
            "empty",
            doc_struct.Paragraph(elements=[]),
            doc_struct.Paragraph(elements=[]),
        ),
        (
            "two mergeable",
            doc_struct.Paragraph(elements=[
                doc_struct.TextRun(style=style1, text='first'),
                doc_struct.TextRun(style=style1, text='second'),
            ]),
            doc_struct.Paragraph(elements=[
                doc_struct.TextRun(style=style1, text='firstsecond'),
            ]),
        ),
        (
            "two mergeable at start",
            doc_struct.Paragraph(elements=[
                doc_struct.TextRun(style=style1, text='first'),
                doc_struct.TextRun(style=style1, text='second'),
                doc_struct.TextRun(style=style2, text='third'),
            ]),
            doc_struct.Paragraph(elements=[
                doc_struct.TextRun(style=style1, text='firstsecond'),
                doc_struct.TextRun(style=style2, text='third'),
            ]),
        ),
        (
            "two mergeable at end",
            doc_struct.Paragraph(elements=[
                doc_struct.TextRun(style=style2, text='third'),
                doc_struct.TextRun(style=style1, text='first'),
                doc_struct.TextRun(style=style1, text='second'),
            ]),
            doc_struct.Paragraph(elements=[
                doc_struct.TextRun(style=style2, text='third'),
                doc_struct.TextRun(style=style1, text='firstsecond'),
            ]),
        ),
        (
            "two mergeable middle",
            doc_struct.Paragraph(elements=[
                doc_struct.TextRun(style=style2, text='third'),
                doc_struct.TextRun(style=style1, text='first'),
                doc_struct.TextRun(style=style1, text='second'),
                doc_struct.TextRun(style=style2, text='fourth'),
            ]),
            doc_struct.Paragraph(elements=[
                doc_struct.TextRun(style=style2, text='third'),
                doc_struct.TextRun(style=style1, text='firstsecond'),
                doc_struct.TextRun(style=style2, text='fourth'),
            ]),
        ),
        (
            "two pairs",
            doc_struct.Paragraph(elements=[
                doc_struct.TextRun(style=style1, text='first'),
                doc_struct.TextRun(style=style1, text='second'),
                doc_struct.TextRun(style=style2, text='third'),
                doc_struct.TextRun(style=style2, text='fourth'),
            ]),
            doc_struct.Paragraph(elements=[
                doc_struct.TextRun(style=style1, text='firstsecond'),
                doc_struct.TextRun(style=style2, text='thirdfourth'),
            ]),
        ),
        (
            "chip not matching",
            doc_struct.Paragraph(elements=[
                doc_struct.Chip(style=style1, text='nope1'),
                doc_struct.TextRun(style=style1, text='first'),
                doc_struct.Chip(style=style1, text='nope2'),
            ]),
            doc_struct.Paragraph(elements=[
                doc_struct.Chip(style=style1, text='nope1'),
                doc_struct.TextRun(style=style1, text='first'),
                doc_struct.Chip(style=style1, text='nope2'),
            ]),
        ),
    ])
    # pylint: disable=unused-argument
    def test_merge_transform(self, name: str, data: doc_struct.Paragraph,
                             expected: doc_struct.Paragraph):
        """Perform the transformation and compare the result."""
        transform = paragraph_basic.TextMergeParagraphTransformation()
        print(transform(data))
        self.assertEqual(expected, transform(data))


class TestTagMergePolicy(unittest.TestCase):
    """Test the TagMergePolicy class."""

    @parameterized.expand([  # type: ignore
        (
            'Default case',
            paragraph_basic.TagMergeConfig(),
            doc_struct.TextRun(text='a'),
            doc_struct.TextRun(text='b'),
            'ab',
        ),
        (
            'matching relaxed match',
            paragraph_basic.TagMergeConfig(
                element_types=[doc_struct.ParagraphElement]),
            doc_struct.TextRun(text='a'),
            doc_struct.Chip(text='b'),
            'a[b]',
        ),
        (
            'matching relaxed match',
            paragraph_basic.TagMergeConfig(
                element_types=[doc_struct.ParagraphElement]),
            doc_struct.Link(text='a', url='x'),
            doc_struct.Chip(text='b', url='x'),
            '[ab](x)',
        ),
        (
            'matching relaxed match',
            paragraph_basic.TagMergeConfig(
                merge_as_text_run=True,
                element_types=[doc_struct.ParagraphElement]),
            doc_struct.Link(text='a', url='x'),
            doc_struct.Chip(text='b', url='x'),
            '[a](x)[b](x)',
        ),
        (
            'matching text line',
            paragraph_basic.TagMergeConfig(
                element_types=[doc_struct.ParagraphElement]),
            doc_struct.TextLine(elements=[doc_struct.TextRun(text='a')]),
            doc_struct.TextLine(elements=[doc_struct.Chip(text='b')]),
            'a[b]',
        ),
        (
            'matching single tag',
            paragraph_basic.TagMergeConfig(acceptable_tag_sets=[['x']]),
            doc_struct.TextRun(attrs={'tags': ['x']}, text='a'),
            doc_struct.TextRun(attrs={'tags': ['x']}, text='b'),
            'ab',
        ),
        (
            'matching single tag with extra',
            paragraph_basic.TagMergeConfig(acceptable_tag_sets=[['x']]),
            doc_struct.TextRun(attrs={'tags': ['x', 'y']}, text='a'),
            doc_struct.TextRun(attrs={'tags': ['x', 'z']}, text='b'),
            'ab',
        ),
        (
            'matching single tag, after non-match',
            paragraph_basic.TagMergeConfig(
                acceptable_tag_sets=[['x', 'y'], ['x']]),
            doc_struct.TextRun(attrs={'tags': ['x']}, text='a'),
            doc_struct.TextRun(attrs={'tags': ['x']}, text='b'),
            'ab',
        ),
        (
            'matching single tag, after first match only',
            paragraph_basic.TagMergeConfig(
                acceptable_tag_sets=[['x', 'y'], ['x']]),
            doc_struct.TextRun(attrs={'tags': ['x', 'y']}, text='a'),
            doc_struct.TextRun(attrs={'tags': ['x']}, text='b'),
            'ab',
        ),
        (
            'matching tag set',
            paragraph_basic.TagMergeConfig(acceptable_tag_sets=[['x', 'y']]),
            doc_struct.TextRun(attrs={'tags': ['x', 'y']}, text='a'),
            doc_struct.TextRun(attrs={'tags': ['x', 'y']}, text='b'),
            'ab',
        ),
        (
            'matching tag set plus matching tag',
            paragraph_basic.TagMergeConfig(acceptable_tag_sets=[['x', 'y']]),
            doc_struct.TextRun(attrs={'tags': ['x', 'y', 'z']}, text='a'),
            doc_struct.TextRun(attrs={'tags': ['x', 'y', 'z']}, text='b'),
            'ab',
        ),
        (
            'Non-matching rejected tag',
            paragraph_basic.TagMergeConfig(
                acceptable_tag_sets=[['x']],
                rejected_tags=['r'],
            ),
            doc_struct.TextRun(attrs={'tags': ['x']}, text='a'),
            doc_struct.TextRun(attrs={'tags': ['x']}, text='b'),
            'ab',
        ),
    ])
    # pylint: disable=unused-argument
    def test_merge(self, description: str,
                   config: paragraph_basic.TagMergeConfig,
                   first: doc_struct.ParagraphElement,
                   second: doc_struct.ParagraphElement, merged_text: str):
        """Run all tests."""
        policy = paragraph_basic.TagMergePolicy(config)

        self.assertTrue(policy._is_matching(first, second))  # type: ignore
        self.assertEqual(merged_text,
                         policy._create_merged(  # type: ignore
                             first,
                             second,
                         ).as_plain_text())

    @parameterized.expand([  # type: ignore
        (
            'Non-matching types',
            paragraph_basic.TagMergeConfig(element_types=[doc_struct.Chip]),
            doc_struct.TextRun(text='a'),
            doc_struct.TextRun(text='b'),
        ),
        (
            'Non-matching second type',
            paragraph_basic.TagMergeConfig(),
            doc_struct.TextRun(text='a'),
            doc_struct.Chip(text='b'),
        ),
        (
            'Non-matching first type',
            paragraph_basic.TagMergeConfig(),
            doc_struct.Chip(text='a'),
            doc_struct.TextRun(text='b'),
        ),
        (
            'Non-matching relaxed match different URLs',
            paragraph_basic.TagMergeConfig(
                element_types=[doc_struct.ParagraphElement]),
            doc_struct.Link(text='a', url='x'),
            doc_struct.Chip(text='b', url='y'),
        ),
        (
            'Missing tags',
            paragraph_basic.TagMergeConfig(acceptable_tag_sets=[['x']]),
            doc_struct.TextRun(text='a'),
            doc_struct.TextRun(text='b'),
        ),
        (
            'Missing 2nd tags',
            paragraph_basic.TagMergeConfig(acceptable_tag_sets=[['x']]),
            doc_struct.TextRun(attrs={'tags': ['x']}, text='a'),
            doc_struct.TextRun(text='b'),
        ),
        (
            'Missing 1st tag',
            paragraph_basic.TagMergeConfig(acceptable_tag_sets=[['x']]),
            doc_struct.TextRun(text='a'),
            doc_struct.TextRun(attrs={'tags': ['x']}, text='b'),
        ),
        (
            'unrelated, matching tags',
            paragraph_basic.TagMergeConfig(acceptable_tag_sets=[['x']]),
            doc_struct.TextRun(attrs={'tags': ['y']}, text='a'),
            doc_struct.TextRun(attrs={'tags': ['z']}, text='b'),
        ),
        (
            'Only 1st matching',
            paragraph_basic.TagMergeConfig(acceptable_tag_sets=[['x']]),
            doc_struct.TextRun(attrs={'tags': ['x']}, text='a'),
            doc_struct.TextRun(attrs={'tags': ['z']}, text='b'),
        ),
        (
            'Only 2nd matching',
            paragraph_basic.TagMergeConfig(acceptable_tag_sets=[['x']]),
            doc_struct.TextRun(attrs={'tags': ['y']}, text='a'),
            doc_struct.TextRun(attrs={'tags': ['x']}, text='b'),
        ),
        (
            'Tag set not subset',
            paragraph_basic.TagMergeConfig(acceptable_tag_sets=[['x', 'y']]),
            doc_struct.TextRun(attrs={'tags': ['x']}, text='a'),
            doc_struct.TextRun(attrs={'tags': ['x']}, text='b'),
        ),
        (
            'Tag set not not intersecting',
            paragraph_basic.TagMergeConfig(acceptable_tag_sets=[['x', 'y']]),
            doc_struct.TextRun(attrs={'tags': ['x', 'z']}, text='a'),
            doc_struct.TextRun(attrs={'tags': ['y', 'z']}, text='b'),
        ),
        (
            'Tag set multiple disjoint',
            paragraph_basic.TagMergeConfig(
                acceptable_tag_sets=[['x', 'y'], ['u', 'v']]),
            doc_struct.TextRun(attrs={'tags': ['x', 'y']}, text='a'),
            doc_struct.TextRun(attrs={'tags': ['u', 'v']}, text='b'),
        ),
        (
            'Rejected in 1st',
            paragraph_basic.TagMergeConfig(acceptable_tag_sets=[['x']],
                                           rejected_tags=['r']),
            doc_struct.TextRun(attrs={'tags': ['x', 'r']}, text='a'),
            doc_struct.TextRun(attrs={'tags': ['x']}, text='b'),
        ),
        (
            'Rejected in 2st',
            paragraph_basic.TagMergeConfig(acceptable_tag_sets=[['x']],
                                           rejected_tags=['r']),
            doc_struct.TextRun(attrs={'tags': ['x']}, text='a'),
            doc_struct.TextRun(attrs={'tags': ['x', 'r']}, text='b'),
        ),
        (
            'Rejected in 2st',
            paragraph_basic.TagMergeConfig(acceptable_tag_sets=[['x']],
                                           rejected_tags=['q', 'r']),
            doc_struct.TextRun(attrs={'tags': ['x']}, text='a'),
            doc_struct.TextRun(attrs={'tags': ['x', 'r']}, text='b'),
        ),
    ])
    # pylint: disable=unused-argument
    def test_non_merge(self, description: str,
                       config: paragraph_basic.TagMergeConfig,
                       first: doc_struct.ParagraphElement,
                       second: doc_struct.ParagraphElement):
        """Tun all tests."""
        policy = paragraph_basic.TagMergePolicy(config)

        self.assertFalse(policy._is_matching(first, second))  # type: ignore
