"""Tests for document-level classes."""

import unittest
from typing import Optional, TypeVar

from doc_scraper import doc_struct
from doc_scraper.html_extractor import _base, _document_elements

_SPC = "  "

T = TypeVar('T', bound=object)


def fail_none(obj: Optional[T]) -> T:
    """Remove None/Optional from type and raise exception if seen."""
    if obj is None:
        raise Exception('Is NONE')
    return obj


class HeadTest(unittest.TestCase):
    """Test head class."""

    def test_parse_css(self):
        """Test simple scenario."""
        context = _base.ParseContext()
        head = _document_elements.HeadFrame(context, {'k': 'val'})

        self.assertIsNone(head.handle_start('style', {}))
        head.handle_data(".xxx {attrib-a:1234; attrib-b:'x'}")
        self.assertIsNone(head.handle_end('style'))

        self.assertEqual({'.xxx': {
            'attrib-a': '1234',
            'attrib-b': "'x'"
        }},
                         head.to_struct().style_rules)

    def test_empty(self):
        """Test empty head."""
        context = _base.ParseContext()
        head = _document_elements.HeadFrame(context, {'k': 'val'})

        self.assertIsNone(head.handle_start('style', {}))
        head.handle_data("")
        self.assertIsNone(head.handle_end('style'))

        self.assertEqual({}, head.to_struct().style_rules)

    def test_handle_end(self):
        """Check that handling end works."""
        context = _base.ParseContext()
        head = _document_elements.HeadFrame(context, {'k': 'val'})

        self.assertIsNone(head.handle_start('style', {}))
        head.handle_data("")
        self.assertIsNone(head.handle_end('style'))
        self.assertEqual(head, head.handle_end('head'))

    def test_handle_end_inside_style(self):
        """Test that closing head works even if still in style tag."""
        context = _base.ParseContext()
        head = _document_elements.HeadFrame(context, {'k': 'val'})

        self.assertIsNone(head.handle_start('style', {}))
        head.handle_data("")
        self.assertEqual(head, head.handle_end('head'))

    def test_text_outside(self):
        """Check to ensure data outside style tags is ignored."""
        context = _base.ParseContext()
        head = _document_elements.HeadFrame(context, {'k': 'val'})

        self.assertIsNone(head.handle_start('style', {}))
        self.assertIsNone(head.handle_end('style'))
        head.handle_data("something else")

        self.assertEqual({}, head.to_struct().style_rules)

    def test_multi_rules(self):
        """Test multile rules and add spacing."""
        context = _base.ParseContext()
        head = _document_elements.HeadFrame(context, {'k': 'val'})

        self.assertIsNone(head.handle_start('style', {}))
        head.handle_data("""
            .a #u >    v {_SPC
                attrib-a: val-a;
                attrib-b:     val-b   ;_SPC
            }{_SPC
            b { attrib-a  :val-a2; }
        """.replace("_SPC", _SPC))
        self.assertIsNone(head.handle_end('style'))
        self.assertIsNone(head.handle_start('style', {}))
        head.handle_data("""
            .c {
                attrib-c: val-c;

            }
        """)
        self.assertIsNone(head.handle_end('style'))

        self.assertEqual(
            {
                '.a #u > v': {
                    'attrib-a': 'val-a',
                    'attrib-b': 'val-b'
                },
                '.c': {
                    'attrib-c': 'val-c'
                },
                'b': {
                    'attrib-a': 'val-a2'
                }
            },
            head.to_struct().style_rules)


class RootTest(unittest.TestCase):
    """Test root element."""

    def test_simple(self):
        """Test simple scenario."""
        context = _base.ParseContext()
        root = _document_elements.RootFrame(context, {'k': 'val'})

        head = fail_none(root.handle_start('head', {}))
        self.assertIsNone(head.handle_start('style', {}))
        head.handle_data(".xxx {attrib-a:1234}")
        self.assertIsNone(head.handle_end('style'))
        self.assertEqual(head, head.handle_end('head'))
        document = fail_none(root.handle_start('body', {}))
        paragraph = fail_none(document.handle_start('p', {}))
        self.assertEqual(paragraph, paragraph.handle_end('p'))
        self.assertEqual(document, document.handle_end('body'))

        self.assertEqual(
            doc_struct.Document(
                shared_data=doc_struct.SharedData(
                    style_rules={'.xxx': {
                        'attrib-a': '1234'
                    }}),
                content=doc_struct.DocContent(elements=[
                    doc_struct.Paragraph(
                        attrs={}, elements=[doc_struct.TextRun(text='\n')])
                ])),
            root.to_struct(),
        )
