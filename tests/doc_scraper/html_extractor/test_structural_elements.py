"""Test base module of the HTML extractor."""

import unittest
from typing import TypeVar, Optional

from doc_scraper.html_extractor import _base
from doc_scraper.html_extractor import _paragraph_elements
from doc_scraper.html_extractor import _structural_elements
from doc_scraper import doc_struct

T = TypeVar('T', bound=object)


def fail_none(obj: Optional[T]) -> T:
    """Remove None/Optional from type and raise exception if seen."""
    if obj is None:
        raise Exception('Is NONE')
    return obj


class TableTest(unittest.TestCase):
    """Test common functionality for all paragraph elements."""

    def test_simple_table(self):
        """Test simple table extraction."""
        context = _base.ParseContext()
        table = _structural_elements.TableFrame(context, {'k': 'val'})

        self.assertIsNone(table.handle_start('tr', {'x': 2}))
        table.handle_start('td', {'x': 3})

        self.assertEqual(
            doc_struct.Table(
                attrs={'k': 'val'},
                elements=[[
                    doc_struct.DocContent(
                        attrs={'x': 3},
                        elements=[],
                    )
                ]],
            ), table.to_struct())

    def test_end_tag(self):
        """Test to ensure that ending table tags cause context update."""
        context = _base.ParseContext()
        table = _structural_elements.TableFrame(context, {})

        self.assertIsNone(table.handle_end('th'))
        self.assertEqual(table, table.handle_end('table'))


class ParagraphTest(unittest.TestCase):
    """Test paragraph element."""

    def test_simple_paragraph(self):
        """Test simple paragraph extraction."""
        context = _base.ParseContext()
        paragraph = _structural_elements.ParagraphFrame(context, {'k': 'val'})

        text = paragraph.handle_start('span', {'x': 2})
        if text is None:
            self.fail()
        text.handle_data('some text')

        self.assertEqual(
            doc_struct.Paragraph(attrs={'k': 'val'},
                                 elements=[
                                     doc_struct.TextRun(attrs={'x': 2},
                                                        text='some text')
                                 ]), paragraph.to_struct())

    def test_left_offset(self):
        """Test paragraph with empty text run."""
        context = _base.ParseContext()
        style = 'margin-left: 11pt'
        paragraph = _structural_elements.ParagraphFrame(
            context, {'style': style})

        self.assertEqual(
            doc_struct.Paragraph(attrs={'style': style},
                                 style={'margin-left': '11pt'},
                                 left_offset=11,
                                 elements=[]), paragraph.to_struct())

    def test_empty_text(self):
        """Test paragraph with empty text run."""
        context = _base.ParseContext()
        paragraph = _structural_elements.ParagraphFrame(context, {'k': 'val'})

        text = fail_none(paragraph.handle_start('span', {'x': 2}))
        text.handle_data('')

        self.assertEqual(
            doc_struct.Paragraph(
                attrs={'k': 'val'},
                elements=[doc_struct.TextRun(attrs={'x': 2}, text='')]),
            paragraph.to_struct())

    def test_text_outside_span(self):
        """Test paragraph with empty text run."""
        context = _base.ParseContext()
        paragraph = _structural_elements.ParagraphFrame(context, {'k': 'val'})

        paragraph.handle_data('some data')

        self.assertEqual(
            doc_struct.Paragraph(
                attrs={'k': 'val'},
                elements=[doc_struct.TextRun(text='some data')],
            ), paragraph.to_struct())

    def test_no_text(self):
        """Test paragraph with text run without any text added."""
        context = _base.ParseContext()
        paragraph = _structural_elements.ParagraphFrame(context, {'k': 'val'})

        paragraph.handle_start('span', {'x': 2})

        self.assertEqual(
            doc_struct.Paragraph(
                attrs={'k': 'val'},
                elements=[doc_struct.TextRun(attrs={'x': 2}, text='')],
            ), paragraph.to_struct())

    def test_multiple_lines_styled(self):
        """Test paragraph with empty text run."""
        context = _base.ParseContext()
        paragraph = _structural_elements.ParagraphFrame(context, {})

        fail_none(paragraph.handle_start('span', {})).handle_data('some')
        fail_none(paragraph.handle_start(
            'span', {'style': 'a:111'})).handle_data('text')
        paragraph.handle_start('br', {})
        fail_none(paragraph.handle_start('span', {})).handle_data('second')
        fail_none(paragraph.handle_start(
            'span', {'style': 'a:111'})).handle_data('line')

        expected_lines = [
            doc_struct.TextRun(text='some'),
            doc_struct.TextRun(attrs={'style': 'a:111'},
                               style={'a': '111'},
                               text='text'),
            doc_struct.TextRun(text='\n'),
            doc_struct.TextRun(text='second'),
            doc_struct.TextRun(attrs={'style': 'a:111'},
                               style={'a': '111'},
                               text='line'),
        ]

        self.assertEqual(doc_struct.Paragraph(elements=expected_lines),
                         paragraph.to_struct())

    def test_end_tag(self):
        """Test to ensure that ending paragraph tags cause context update."""
        context = _base.ParseContext()
        paragraph = _structural_elements.ParagraphFrame(context, {})

        self.assertRaisesRegex(_base.UnexpectedHtmlTag, 'Unexpected.*',
                               lambda: paragraph.handle_end('xxx'))
        self.assertEqual(paragraph, paragraph.handle_end('p'))

    def test_start_tag(self):
        """Test to ensure that ending paragraph tags cause context update."""
        context = _base.ParseContext()
        paragraph = _structural_elements.ParagraphFrame(context, {})
        chip_style_str = 'color: #0000ee; text-decoration: underline'

        self.assertIsNone(paragraph.handle_start('xxx', {}))
        self.assertIsInstance(paragraph.handle_start('span', {}),
                              _paragraph_elements.ParagraphElementFrame)
        self.assertIsInstance(
            paragraph.handle_start('span', {'style': chip_style_str}),
            _paragraph_elements.ParagraphElementFrame)

        self.assertIsInstance(paragraph.handle_start('sup', {}),
                              _paragraph_elements.SuperscriptFrame)
        self.assertIsInstance(paragraph.handle_start('a', {}),
                              _paragraph_elements.PlainAnchorFrame)


class NotesTest(unittest.TestCase):
    """Test notes appendix extraction."""

    def test_simple_heading(self):
        """Test simple notes extraction."""
        context = _base.ParseContext()
        notes = _structural_elements.NotesFrame(context, {'k': 'val'})

        self.assertIsNotNone(notes.handle_start('p', {'x': 2}))

        self.assertEqual(
            doc_struct.NotesAppendix(
                attrs={'k': 'val'},
                elements=[doc_struct.Paragraph(attrs={'x': 2}, elements=[])],
            ), notes.to_struct())

    def test_end_tag(self):
        """Test to ensure that ending paragraph tags cause context update."""
        context = _base.ParseContext()
        notes = _structural_elements.NotesFrame(context)

        self.assertEqual(notes, notes.handle_end('div'))


class HeadingTest(unittest.TestCase):
    """Test heading extraction."""

    def test_simple_heading(self):
        """Test simple heading extraction."""
        context = _base.ParseContext()
        heading = _structural_elements.HeadingFrame(context, 'h2',
                                                    {'k': 'val'})

        text = fail_none(heading.handle_start('span', {'x': 2}))
        text.handle_data('some text')

        self.assertEqual(
            doc_struct.Heading(
                attrs={'k': 'val'},
                elements=[
                    doc_struct.TextRun(
                        attrs={'x': 2},
                        text='some text',
                    )
                ],
                level=2,
            ), heading.to_struct())

    def test_end_tag(self):
        """Test to ensure that ending paragraph tags cause context update."""
        context = _base.ParseContext()
        heading = _structural_elements.HeadingFrame(context, 'h3', {})

        self.assertRaisesRegex(_base.UnexpectedHtmlTag, 'Unexpected.*',
                               lambda: heading.handle_end('h2'))
        self.assertEqual(heading, heading.handle_end('h3'))


class BulletListTest(unittest.TestCase):
    """Test bullet list extraction."""

    def test_simple_list(self):
        """Test simple list item extraction."""
        context = _base.ParseContext()
        bullet_list = _structural_elements.BulletListFrame(
            context, 'ul', {'k': 'val'})

        item = fail_none(bullet_list.handle_start('li', {'x': 2}))
        item.left_offset = 10
        span = fail_none(item.handle_start('span', {'y': 22}))
        span.handle_data('abc')

        self.assertEqual(
            doc_struct.BulletList(
                attrs={'k': 'val'},
                items=[
                    doc_struct.BulletItem(
                        attrs={'x': 2},
                        left_offset=10,
                        level=0,
                        elements=[
                            doc_struct.TextRun(
                                attrs={'y': 22},
                                text='abc',
                            )
                        ],
                        list_class=None,
                        list_type='ul',
                        nested=[],
                    )
                ],
            ), bullet_list.to_struct())

    def test_indented_bullet_list(self):
        """Test indented items."""
        context = _base.ParseContext()
        bullet_list = _structural_elements.BulletListFrame(
            context, 'ul', {'k': 'val'})

        item1 = fail_none(bullet_list.handle_start('li', {'x': 2}))
        item1.left_offset = 10
        item1.list_type = 'item1'
        item2 = fail_none(bullet_list.handle_start('li', {'x': 3}))
        item2.left_offset = 20
        item2.list_type = 'item2'

        expected = doc_struct.BulletList(
            attrs={'k': 'val'},
            items=[
                doc_struct.BulletItem(
                    attrs={'x': 2},
                    level=0,
                    left_offset=10,
                    elements=[],
                    list_class=None,
                    list_type='item1',
                    nested=[],
                ),
                doc_struct.BulletItem(
                    attrs={'x': 3},
                    level=1,
                    left_offset=20,
                    elements=[],
                    list_class=None,
                    list_type='item2',
                    nested=[],
                )
            ],
        )
        self.assertEqual(expected, bullet_list.to_struct())


class DocContentTest(unittest.TestCase):
    """Test doc content extraction."""

    def test_simple_content(self):
        """Test simple case."""
        context = _base.ParseContext()
        content = _structural_elements.DocContentFrame(context, 'body',
                                                       {'k': 'val'})

        paragraph = fail_none(content.handle_start('p', {'x': 2}))
        fail_none(paragraph.handle_start('span', {})).handle_data('xxx')

        bullet_list = fail_none(content.handle_start('ul', {'x': 3}))
        bullet_list.handle_start('li', {'y': 2})

        table = fail_none(content.handle_start('table', {'x': 4}))
        table.handle_start('tr', {'y': 3})
        table.handle_start('td', {'y': 5})

        heading = fail_none(content.handle_start('h2', {'x': 5}))
        fail_none(heading.handle_start('span', {})).handle_data('yyy')

        expected = doc_struct.DocContent(
            attrs={'k': 'val'},
            elements=[
                doc_struct.Paragraph(
                    attrs={'x': 2},
                    elements=[doc_struct.TextRun(text='xxx',)],
                ),
                doc_struct.BulletList(
                    attrs={'x': 3},
                    items=[
                        doc_struct.BulletItem(
                            attrs={'y': 2},
                            level=0,
                            elements=[],
                            list_class=None,
                            list_type='ul',
                            nested=[],
                        )
                    ],
                ),
                doc_struct.Table(
                    attrs={'x': 4},
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
                    elements=[doc_struct.TextRun(text='yyy',)],
                ),
            ],
        )

        actual: doc_struct.DocContent = content.to_struct()
        self.assertEqual(expected, actual)

    def test_start_tag(self):
        """Test simple case."""
        context = _base.ParseContext()
        content = _structural_elements.DocContentFrame(context, 'body',
                                                       {'k': 'val'})

        self.assertIsInstance(content.handle_start('sup', {}),
                              _base.DummyFrame)
        self.assertIsInstance(content.handle_start('a', {}),
                              _base.DummyFrame)
