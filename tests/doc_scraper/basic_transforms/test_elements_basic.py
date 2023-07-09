"""Test the basic transformations for all elements."""

import unittest

from doc_scraper.basic_transforms import elements_basics
from doc_scraper.basic_transforms import tags_basic
from doc_scraper.basic_transforms import tags_relation
from doc_scraper import doc_struct


class TestStripElements(unittest.TestCase):
    """Test the Strip elements transformation."""

    def test_simple_transform(self):
        """Test a simple transformation."""
        transform = elements_basics.StripElementsTransform(
            remove_attrs_re=tags_basic.StringMatcher.make_list('_.*'),
            remove_styles_re=tags_basic.StringMatcher.make_list('-.*', '0.*'),
            remove_style_rules_re=tags_basic.StringMatcher.make_list('x.*'))

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
            remove_attrs_re=[], remove_styles_re=[], remove_style_rules_re=[])

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


class TestDropElements(unittest.TestCase):
    """Test the Drop elements transformation."""

    def test_simple_transform(self):
        """Test by dropping all elements that have tag 'X'."""
        transform = elements_basics.DropElementsTransform(
            config=elements_basics.DropElementsConfig(
                match_element=tags_relation.PositionMatchConfig(
                    required_tag_sets=[tags_basic.MappingMatcher(X=".*")])))

        data = doc_struct.DocContent(elements=[
            doc_struct.Paragraph(tags={'X': '1'}, elements=[]),
            doc_struct.Paragraph(
                tags={'O': '1'},
                elements=[
                    doc_struct.TextRun(tags={'X': '1'}, text='bad'),
                    doc_struct.TextRun(tags={'O': '1'}, text='good'),
                    doc_struct.TextLine(
                        tags={'O': '1'},
                        elements=[
                            doc_struct.TextRun(tags={'X': '1'}, text='bad2'),
                            doc_struct.TextRun(tags={'O': '1'}, text='good2'),
                        ]),
                ]),
            doc_struct.Section(
                heading=doc_struct.Heading(elements=[], level=0),
                content=[
                    doc_struct.Paragraph(tags={'X': '1'}, elements=[]),
                    doc_struct.Paragraph(tags={'O': '1'}, elements=[]),
                ],
            ),
            doc_struct.BulletList(
                tags={'O': '1'},
                items=[
                    doc_struct.BulletItem(
                        tags={'X': '1'},
                        elements=[],
                        left_offset=999,
                        list_type='ul',
                    ),
                    doc_struct.BulletItem(
                        tags={'O': '1'},
                        elements=[],
                        nested=[
                            doc_struct.BulletItem(
                                tags={'X': '1'},
                                elements=[],
                                left_offset=999,
                                list_type='ul',
                            ),
                            doc_struct.BulletItem(
                                tags={'O': '1'},
                                elements=[],
                                left_offset=0,
                                list_type='ul',
                            ),
                        ],
                        left_offset=0,
                        list_type='ul',
                    ),
                ],
            ),
        ])

        expected = doc_struct.DocContent(elements=[
            doc_struct.Paragraph(
                tags={'O': '1'},
                elements=[
                    doc_struct.TextRun(tags={'O': '1'}, text='good'),
                    doc_struct.TextLine(tags={'O': '1'},
                                        elements=[
                                            doc_struct.TextRun(tags={'O': '1'},
                                                               text='good2'),
                                        ]),
                ]),
            doc_struct.Section(
                heading=doc_struct.Heading(elements=[], level=0),
                content=[
                    doc_struct.Paragraph(tags={'O': '1'}, elements=[]),
                ],
            ),
            doc_struct.BulletList(
                tags={'O': '1'},
                items=[
                    doc_struct.BulletItem(
                        tags={'O': '1'},
                        elements=[],
                        nested=[
                            doc_struct.BulletItem(
                                tags={'O': '1'},
                                elements=[],
                                left_offset=0,
                                list_type='ul',
                            ),
                        ],
                        left_offset=0,
                        list_type='ul',
                    ),
                ],
            ),
        ])
        self.assertEqual(expected, transform(data))
