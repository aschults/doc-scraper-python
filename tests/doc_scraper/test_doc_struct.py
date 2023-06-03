"""Tests for the document structure dataclasses."""

import unittest
from typing import Any

from doc_scraper import doc_struct
from parameterized import parameterized  # type:ignore


class CommonFunctionsTest(unittest.TestCase):
    """Test common functions."""

    def test_from_super(self):
        """Test the from_super() function."""
        parent = doc_struct.Element(attrs={'x': 1}, style={'a': 'xx'})
        new_element = doc_struct.from_super(doc_struct.TextRun,
                                            parent,
                                            text='xxx')
        self.assertIsInstance(new_element, doc_struct.TextRun)
        self.assertEqual(
            doc_struct.TextRun(attrs={'x': 1}, style={'a': 'xx'}, text='xxx'),
            new_element)

    def test_struct_conversion(self):
        """Ensure that conversion to JSON-like structure works as expected."""
        element = doc_struct.DocContent(
            attrs={'k': 'val'},
            style={},
            elements=[
                doc_struct.Paragraph(
                    attrs={'x': 2},
                    style={'a': '11'},
                    left_offset=0,
                    elements=[
                        doc_struct.TextRun(text='xxx',),
                        doc_struct.TextLine(elements=[
                            doc_struct.TextRun(text='xxx',),
                        ]),
                    ],
                ),
                doc_struct.BulletList(
                    attrs={'x': 3},
                    left_offset=0,
                    items=[
                        doc_struct.BulletItem(
                            attrs={'y': 2},
                            left_offset=0,
                            level=0,
                            elements=[],
                            list_type='ul',
                        )
                    ],
                ),
                doc_struct.Table(
                    attrs={'x': 4},
                    left_offset=0,
                    elements=[[
                        doc_struct.DocContent(
                            attrs={'y': 5},
                            elements=[],
                        )
                    ]],
                ),
                doc_struct.Heading(
                    attrs={'x': 5},
                    level=2,
                    left_offset=0,
                    elements=[doc_struct.TextRun(text='yyy',)],
                ),
            ],
        )

        expected: Any = {
            'attrs': {
                'k': 'val'
            },
            'elements': [{
                'attrs': {
                    'x': 2
                },
                'style': {
                    'a': '11'
                },
                'left_offset': 0,
                'elements': [
                    {
                        'text': 'xxx',
                        'type': 'TextRun'
                    },
                    {
                        'elements': [{
                            'text': 'xxx',
                            'type': 'TextRun'
                        },],
                        'type': 'TextLine'
                    },
                ],
                'type': 'Paragraph'
            }, {
                'attrs': {
                    'x': 3
                },
                'left_offset': 0,
                'items': [{
                    'attrs': {
                        'y': 2
                    },
                    'left_offset': 0,
                    'elements': [],
                    'level': 0,
                    'list_type': 'ul',
                    'type': 'BulletItem'
                }],
                'type': 'BulletList'
            }, {
                'attrs': {
                    'x': 4
                },
                'left_offset': 0,
                'elements': [[{
                    'attrs': {
                        'y': 5
                    },
                    'elements': [],
                    'type': 'DocContent'
                }]],
                'type': 'Table'
            }, {
                'attrs': {
                    'x': 5
                },
                'left_offset': 0,
                'elements': [{
                    'text': 'yyy',
                    'type': 'TextRun'
                }],
                'level': 2,
                'type': 'Heading'
            }],
            'type': 'DocContent'
        }

        self.assertEqual(expected, doc_struct.as_dict(element))

    def test_as_dict_sets(self):
        """Test the from_super() function."""
        element = doc_struct.Element(tags={'x', 'y'})
        result = doc_struct.as_dict(element)
        self.assertEqual({
            'tags': {
                'x': True,
                'y': True
            },
            'type': 'Element'
        }, result)


class RawTextConversionTest(unittest.TestCase):
    """Test conversion to raw text."""

    @parameterized.expand([  # type:ignore
        (
            doc_struct.Chip(text='xxx'),
            'xxx',
        ),
        (
            doc_struct.TextRun(text='xxx'),
            'xxx',
        ),
        (
            doc_struct.Paragraph(elements=[
                doc_struct.TextRun(text='a '),
                doc_struct.TextRun(text='b'),
            ]),
            'a b',
        ),
        (
            doc_struct.DocContent(elements=[
                doc_struct.Paragraph(elements=[
                    doc_struct.TextRun(text='a'),
                    doc_struct.Reference(text='A', url='x'),
                ]),
                doc_struct.Paragraph(elements=[
                    doc_struct.Chip(text='b'),
                    doc_struct.ReferenceTarget(text='B', ref_id='x'),
                ]),
            ]),
            'aA\nbB\n',
        ),
        (
            doc_struct.NotesAppendix(elements=[
                doc_struct.Paragraph(elements=[
                    doc_struct.TextRun(text='a'),
                ]),
                doc_struct.Paragraph(elements=[
                    doc_struct.Chip(text='b'),
                ]),
            ]),
            'a\nb\n',
        ),
        (
            doc_struct.Paragraph(elements=[
                doc_struct.TextLine(elements=[
                    doc_struct.TextRun(text='a\n'),
                ]),
                doc_struct.TextLine(elements=[
                    doc_struct.TextRun(text='b'),
                ]),
            ]),
            'a\nb',
        ),
        (
            doc_struct.Section(
                content=[
                    doc_struct.Paragraph(elements=[
                        doc_struct.TextRun(text='a'),
                    ]),
                ],
                heading=doc_struct.Heading(
                    level=2, elements=[doc_struct.TextRun(text='xxx')]),
            ),
            'xxx\na\n\f',
        ),
        (
            doc_struct.Document(
                shared_data=doc_struct.SharedData(),
                content=doc_struct.DocContent(elements=[
                    doc_struct.Paragraph(elements=[
                        doc_struct.TextRun(text='a'),
                    ]),
                ]),
            ),
            'a\n',
        ),
        (
            doc_struct.DocContent(elements=[
                doc_struct.BulletList(items=[
                    doc_struct.BulletItem(list_type='ul',
                                          level=0,
                                          elements=[
                                              doc_struct.TextRun(text='a'),
                                          ]),
                    doc_struct.BulletItem(list_type='ul',
                                          level=1,
                                          elements=[
                                              doc_struct.TextRun(text='b'),
                                          ],
                                          nested=[
                                              doc_struct.BulletItem(
                                                  list_type='ul',
                                                  level=2,
                                                  elements=[
                                                      doc_struct.TextRun(
                                                          text='c'),
                                                  ]),
                                          ])
                ]),
            ],),
            'a\n  b\n    c\n',
        ),
        (
            doc_struct.Table(elements=[
                [
                    doc_struct.DocContent(elements=[
                        doc_struct.Paragraph(elements=[
                            doc_struct.TextRun(text='a'),
                        ])
                    ]),
                    doc_struct.DocContent(elements=[
                        doc_struct.Paragraph(elements=[
                            doc_struct.TextRun(text='b'),
                        ])
                    ]),
                ],
                [
                    doc_struct.DocContent(elements=[
                        doc_struct.Paragraph(elements=[
                            doc_struct.TextRun(text='c'),
                        ])
                    ]),
                    doc_struct.DocContent(elements=[
                        doc_struct.Paragraph(elements=[
                            doc_struct.TextRun(text='d'),
                        ])
                    ]),
                ],
            ],),
            'a\n\tb\n\vc\n\td\n\n',
        ),
    ])
    def test_conversion(self, data: doc_struct.Element, expected: str):
        """Test parametrized conversion cases."""
        self.assertEqual(expected, doc_struct.RawTextConverter().convert(data))
