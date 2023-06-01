"""Tests for the document structure dataclasses."""

import unittest
from typing import Any

from doc_scraper import doc_struct


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
                    elements=[doc_struct.TextRun(text='xxx',)],
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
                'elements': [{
                    'text': 'xxx',
                    'type': 'TextRun'
                }],
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
