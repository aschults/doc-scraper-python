"""Test the basic transformations for bullet lists/items."""
# pylint: disable=protected-access

import unittest
from typing import Any, Optional, Sequence, Union

from doc_scraper import doc_struct
from doc_scraper.basic_transforms import sections_basic
from parameterized import parameterized  # type:ignore


def mkheading(
    level: int,
    label: str,
) -> doc_struct.Heading:
    """Make a bullet item more easily."""
    return doc_struct.Heading(style={'label': label}, level=level, elements=[])


def mkpar(label: str) -> doc_struct.Paragraph:
    """Create a paragraph element with text to match in tests."""
    return doc_struct.Paragraph(style={'label': label}, elements=[])


class StructureDocTest(unittest.TestCase):
    """Test the structure_doc function."""

    def condense_result(
        self, data: Union[doc_struct.StructuralElement,
                          Sequence[doc_struct.StructuralElement]]
    ) -> Any:
        """Filter out only what is relevant from results."""
        if isinstance(data, list):
            return [self.condense_result(e) for e in data]

        if isinstance(data, doc_struct.Heading):
            return '^' + data.style.get('label', '-')

        if isinstance(data, doc_struct.Paragraph):
            return data.style.get('label', '-')

        if isinstance(data, doc_struct.Section):
            htext = data.heading.style.get('label', '-') + str(
                data.heading.level) if data.heading else '--'
            content = self.condense_result(data.content)
            return (htext, content)

        raise Exception(f'unexpected type of: {data}')

    @parameterized.expand([  # type: ignore
        (
            'empty',
            0,
            None,
            [],
            ('--', []),
        ),
        (
            'empty with heading',
            1,
            mkheading(1, 'x'),
            [],
            ('x1', []),
        ),
        (
            'Single non heading',
            0,
            None,
            [mkpar('a')],
            ('--', ['a']),
        ),
        (
            'two headings only',
            1,
            None,
            [mkheading(1, 'x'), mkheading(1, 'y')],
            ('--', [
                ('x1', []),
                ('y1', []),
            ]),
        ),
        (
            'two headings nested',
            1,
            None,
            [mkheading(1, 'x'), mkheading(2, 'y')],
            ('--', [
                ('x1', [
                    ('y2', []),
                ]),
            ]),
        ),
        (
            'two headings nested reverse',
            1,
            None,
            [mkheading(2, 'x'), mkheading(1, 'y')],
            ('--', [
                ('--', [
                    ('x2', []),
                ]),
                ('y1', []),
            ]),
        ),
        (
            'two headings plus paragraphs',
            1,
            None,
            [
                mkpar('r'),
                mkheading(1, 'x'),
                mkpar('s'),
                mkheading(1, 'y'),
                mkpar('t')
            ],
            ('--', [
                'r',
                ('x1', ['s']),
                ('y1', ['t']),
            ]),
        ),
        (
            'two headings nested plus paragraphs',
            1,
            None,
            [
                mkpar('r'),
                mkheading(1, 'x'),
                mkpar('s'),
                mkheading(2, 'y'),
                mkpar('t')
            ],
            ('--', [
                'r',
                ('x1', [
                    's',
                    ('y2', ['t']),
                ]),
            ]),
        ),
        (
            'two headings nested inverse plus paragraphs',
            1,
            None,
            [
                mkpar('r'),
                mkheading(2, 'x'),
                mkpar('s'),
                mkheading(1, 'y'),
                mkpar('t')
            ],
            ('--', [
                'r',
                ('--', [
                    ('x2', ['s']),
                ]),
                ('y1', ['t']),
            ]),
        ),
        (
            'three headings nested plus paragraphs',
            1,
            None,
            [
                mkpar('r'),
                mkheading(1, 'x'),
                mkpar('s'),
                mkheading(2, 'y'),
                mkpar('t'),
                mkheading(3, 'z'),
            ],
            ('--', [
                'r',
                ('x1', [
                    's',
                    ('y2', ['t', ('z3', [])]),
                ]),
            ]),
        ),
        (
            'three headings nested plus paragraphs',
            1,
            None,
            [
                mkheading(2, 'x'),
                mkpar('s'),
                mkheading(1, 'y'),
                mkpar('t'),
                mkheading(3, 'z'),
            ],
            ('--', [
                ('--', [
                    ('x2', ['s']),
                ]),
                ('y1', [
                    't',
                    ('--', [('z3', [])]),
                ]),
            ]),
        ),
    ])
    # pylint: disable=unused-argument
    def test_structure_doc(self, name: str, level: int,
                           heading: Optional[doc_struct.Heading],
                           data: Sequence[doc_struct.StructuralElement],
                           expected: Any):
        """Test various structure changes."""
        result = sections_basic._structure_doc(  # type: ignore
            level,
            heading,
            data,
        )

        self.assertEqual(expected, self.condense_result(result))


class SectionNestingTransformationTest(unittest.TestCase):
    """Test section nesting transformation."""

    def test_simple_transformation(self):
        """Test a simple scenario."""
        data = doc_struct.DocContent(elements=[
            mkpar('r'),
            mkheading(1, 'x'),
            mkpar('s'),
        ])

        expected = doc_struct.DocContent(elements=[
            mkpar('r'),
            doc_struct.Section(
                heading=mkheading(1, 'x'),
                content=[mkpar('s')],
            )
        ])

        transform = sections_basic.SectionNestingTransform()
        self.assertEqual(expected, transform(data))
