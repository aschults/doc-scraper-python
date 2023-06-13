"""Test the style tagging transformation."""

import unittest
import re

from doc_scraper import doc_struct
from doc_scraper.basic_transforms import tags_basic

doc = doc_struct.Document(
    shared_data=doc_struct.SharedData(),
    content=doc_struct.DocContent(elements=[
        doc_struct.Paragraph(
            style={'a': 'x'},
            elements=[
                doc_struct.TextRun(style={
                    'b': 'z',
                    'a': 'x'
                }, text='xxx'),
            ],
        ),
        doc_struct.Table(style={'a': 'y'},
                         elements=[[
                             doc_struct.DocContent(
                                 style={'a': 'x'},
                                 elements=[
                                     doc_struct.BulletItem(
                                         elements=[
                                             doc_struct.TextRun(
                                                 style={'b': 'z'}, text='yyy')
                                         ],
                                         list_type='li',
                                     )
                                 ])
                         ]]),
        doc_struct.BulletList(items=[
            doc_struct.BulletItem(
                style={'a': 'x'},
                elements=[doc_struct.Chip(text='ccc')],
                list_type='li',
            ),
        ])
    ]))


class StyleTagTest(unittest.TestCase):
    """Test the transformation."""

    def test_one_tag(self):
        """Test a single tag."""
        expected = doc_struct.Document(
            shared_data=doc_struct.SharedData(),
            content=doc_struct.DocContent(elements=[
                doc_struct.Paragraph(
                    tags=doc_struct.tags_for('t1'),
                    style={'a': 'x'},
                    elements=[
                        doc_struct.TextRun(
                            tags=doc_struct.tags_for('t1'),
                            style={
                                'b': 'z',
                                'a': 'x'
                            },
                            text='xxx',
                        ),
                    ],
                ),
                doc_struct.Table(attrs={},
                                 style={'a': 'y'},
                                 elements=[[
                                     doc_struct.DocContent(
                                         style={'a': 'x'},
                                         tags=doc_struct.tags_for('t1'),
                                         elements=[
                                             doc_struct.BulletItem(
                                                 elements=[
                                                     doc_struct.TextRun(
                                                         attrs={},
                                                         style={'b': 'z'},
                                                         text='yyy')
                                                 ],
                                                 list_type='li',
                                             )
                                         ])
                                 ]]),
                doc_struct.BulletList(items=[
                    doc_struct.BulletItem(
                        tags=doc_struct.tags_for('t1'),
                        style={'a': 'x'},
                        elements=[doc_struct.Chip(text='ccc')],
                        list_type='li',
                    ),
                ])
            ]))

        transform = tags_basic.TaggingTransform(
            config=tags_basic.TaggingConfig(
                tags=doc_struct.tags_for('t1'),
                match_element=tags_basic.TagMatchConfig(required_style_sets=[{
                    'a': re.compile('x')
                }],),
            ))
        self.assertEqual(doc_struct.as_dict(expected),
                         doc_struct.as_dict(transform(doc)))

    def test_multiple_rules(self):
        """Test multiple tags in multiple rules."""
        expected = doc_struct.Document(
            shared_data=doc_struct.SharedData(),
            content=doc_struct.DocContent(elements=[
                doc_struct.Paragraph(
                    tags=doc_struct.tags_for('t2'),
                    style={'a': 'x'},
                    elements=[
                        doc_struct.TextRun(
                            tags={
                                't2': '1',
                                't4': '1'
                            },
                            style={
                                'b': 'z',
                                'a': 'x'
                            },
                            text='xxx',
                        ),
                    ],
                ),
                doc_struct.Table(
                    tags=doc_struct.tags_for('t3'),
                    style={'a': 'y'},
                    elements=[[
                        doc_struct.DocContent(
                            style={'a': 'x'},
                            tags=doc_struct.tags_for('t2'),
                            elements=[
                                doc_struct.BulletItem(
                                    elements=[
                                        doc_struct.TextRun(
                                            tags=doc_struct.tags_for('t4'),
                                            style={'b': 'z'},
                                            text='yyy')
                                    ],
                                    list_type='li',
                                )
                            ])
                    ]]),
                doc_struct.BulletList(items=[
                    doc_struct.BulletItem(
                        tags=doc_struct.tags_for('t2'),
                        style={'a': 'x'},
                        elements=[doc_struct.Chip(text='ccc')],
                        list_type='li',
                    ),
                ])
            ]))

        transform1 = tags_basic.TaggingTransform(
            config=tags_basic.TaggingConfig(
                tags=doc_struct.tags_for('t2'),
                match_element=tags_basic.TagMatchConfig(required_style_sets=[{
                    'a': re.compile('x')
                }],)))
        transform2 = tags_basic.TaggingTransform(
            config=tags_basic.TaggingConfig(
                tags=doc_struct.tags_for('t3'),
                match_element=tags_basic.TagMatchConfig(required_style_sets=[{
                    'a': re.compile('y')
                }],)))
        transform3 = tags_basic.TaggingTransform(
            config=tags_basic.TaggingConfig(
                tags=doc_struct.tags_for('t4'),
                match_element=tags_basic.TagMatchConfig(required_style_sets=[{
                    'b': re.compile('z')
                }],)))
        self.assertEqual(
            doc_struct.as_dict(expected),
            doc_struct.as_dict(transform3(transform2(transform1(doc)))))

    def test_type_specific(self):
        """Test tagging constrained to doc structure types."""
        expected = doc_struct.Document(
            shared_data=doc_struct.SharedData(),
            content=doc_struct.DocContent(elements=[
                doc_struct.Paragraph(
                    style={'a': 'x'},
                    elements=[
                        doc_struct.TextRun(
                            tags=doc_struct.tags_for('t5'),
                            style={
                                'b': 'z',
                                'a': 'x'
                            },
                            text='xxx',
                        ),
                    ],
                ),
                doc_struct.Table(style={'a': 'y'},
                                 elements=[[
                                     doc_struct.DocContent(
                                         style={'a': 'x'},
                                         elements=[
                                             doc_struct.BulletItem(
                                                 elements=[
                                                     doc_struct.TextRun(
                                                         style={'b': 'z'},
                                                         text='yyy')
                                                 ],
                                                 list_type='li',
                                             )
                                         ])
                                 ]]),
                doc_struct.BulletList(items=[
                    doc_struct.BulletItem(
                        tags=doc_struct.tags_for('t5'),
                        style={'a': 'x'},
                        elements=[doc_struct.Chip(text='ccc')],
                        list_type='li',
                    ),
                ])
            ]))

        transform = tags_basic.TaggingTransform(
            config=tags_basic.TaggingConfig(
                tags=doc_struct.tags_for('t5'),
                match_element=tags_basic.TagMatchConfig(
                    required_style_sets=[{
                        'a': re.compile('x')
                    }],
                    element_types=[
                        doc_struct.TextRun,
                        doc_struct.BulletItem,
                    ])))
        self.assertEqual(doc_struct.as_dict(expected),
                         doc_struct.as_dict(transform(doc)))

    def test_exclusion(self):
        """Test the exclusion tag for simple matchers."""
        expected = doc_struct.Document(
            shared_data=doc_struct.SharedData(),
            content=doc_struct.DocContent(elements=[
                doc_struct.Paragraph(
                    tags=doc_struct.tags_for('t6'),
                    style={'a': 'x'},
                    elements=[
                        doc_struct.TextRun(
                            style={
                                'b': 'z',
                                'a': 'x'
                            },
                            text='xxx',
                        ),
                    ],
                ),
                doc_struct.Table(style={'a': 'y'},
                                 elements=[[
                                     doc_struct.DocContent(
                                         style={'a': 'x'},
                                         tags=doc_struct.tags_for('t6'),
                                         elements=[
                                             doc_struct.BulletItem(
                                                 elements=[
                                                     doc_struct.TextRun(
                                                         style={'b': 'z'},
                                                         text='yyy')
                                                 ],
                                                 list_type='li',
                                             )
                                         ])
                                 ]]),
                doc_struct.BulletList(items=[
                    doc_struct.BulletItem(
                        tags=doc_struct.tags_for('t6'),
                        style={'a': 'x'},
                        elements=[doc_struct.Chip(text='ccc')],
                        list_type='li',
                    ),
                ])
            ]))

        transform = tags_basic.TaggingTransform(
            config=tags_basic.TaggingConfig(
                tags=doc_struct.tags_for('t6'),
                match_element=tags_basic.TagMatchConfig(
                    required_style_sets=[{
                        'a': re.compile('x')
                    }],
                    rejected_styles={'b': re.compile('z')})))
        self.assertEqual(doc_struct.as_dict(expected),
                         doc_struct.as_dict(transform(doc)))

    def test_style_intersection(self):
        """Test adding more than one style as include.

        Only matches when all styles are matched.
        """
        expected = doc_struct.Document(
            shared_data=doc_struct.SharedData(),
            content=doc_struct.DocContent(elements=[
                doc_struct.Paragraph(
                    style={'a': 'x'},
                    elements=[
                        doc_struct.TextRun(
                            tags=doc_struct.tags_for('t7'),
                            style={
                                'b': 'z',
                                'a': 'x'
                            },
                            text='xxx',
                        ),
                    ],
                ),
                doc_struct.Table(style={'a': 'y'},
                                 elements=[[
                                     doc_struct.DocContent(
                                         style={'a': 'x'},
                                         elements=[
                                             doc_struct.BulletItem(
                                                 elements=[
                                                     doc_struct.TextRun(
                                                         style={'b': 'z'},
                                                         text='yyy')
                                                 ],
                                                 list_type='li',
                                             )
                                         ])
                                 ]]),
                doc_struct.BulletList(items=[
                    doc_struct.BulletItem(
                        style={'a': 'x'},
                        elements=[doc_struct.Chip(text='ccc')],
                        list_type='li',
                    ),
                ])
            ]))

        transform = tags_basic.TaggingTransform(
            config=tags_basic.TaggingConfig(
                tags=doc_struct.tags_for('t7'),
                match_element=tags_basic.TagMatchConfig(required_style_sets=[{
                    'a': re.compile('x'),
                    'b': re.compile('z')
                }])))
        self.assertEqual(doc_struct.as_dict(expected),
                         doc_struct.as_dict(transform(doc)))
