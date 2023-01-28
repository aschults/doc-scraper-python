"""Tests the parser/extractor."""

import unittest
from doc_scraper.html_extractor import _extractor
from doc_scraper.html_extractor import _base
from doc_scraper import doc_struct


class ParserTest(unittest.TestCase):
    """Test head class."""

    def test_simple_parse(self):
        """Test parsing simple HTML."""
        parser = _extractor.ToStructParser()
        parser.feed("""<html><body><p>some text</p></body></html>""")

        expected = doc_struct.Document(
            shared_data=doc_struct.SharedData(),
            content=doc_struct.DocContent(elements=[
                doc_struct.Paragraph(elements=[
                    doc_struct.TextRun(text='some text'),
                    doc_struct.TextRun(text='\n')
                ])
            ]))
        actual = parser.as_struct()
        print(actual)
        self.assertEqual(expected, actual)

    def test_empty_doc(self):
        """Test parsing simple HTML."""
        parser = _extractor.ToStructParser()
        parser.feed('ignored as outside html tag')

        self.assertRaisesRegex(_base.UnexpectedHtmlTag, 'No HTML document.*',
                               parser.as_struct)

    def test_missing_html_end(self):
        """Test parsing simple HTML."""
        parser = _extractor.ToStructParser()
        parser.feed("""<html><body><p>some text</p></body>""")

        self.assertRaisesRegex(_base.UnexpectedHtmlTag,
                               'HTML tags not balanced.*', parser.as_struct)

    def test_bad_tag(self):
        """Test parsing simple HTML."""
        parser = _extractor.ToStructParser()

        self.assertRaisesRegex(
            _base.UnexpectedHtmlTag, 'Unexpected tag.*',
            lambda: parser.feed("""<html><body><q>some text</q></body>"""))
