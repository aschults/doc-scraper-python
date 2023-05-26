"""Test base module of the HTML extractor."""

import unittest
from doc_scraper.html_extractor import _base
from doc_scraper.html_extractor import _paragraph_elements
from doc_scraper import doc_struct


class ParagraphElementTest(unittest.TestCase):
    """Test common functionality for all paragraph elements."""

    def test_collect_simple_data(self):
        """Test collecting text fragments."""
        context = _base.ParseContext()
        element = _paragraph_elements.ParagraphElementFrame(
            context, {'k': 'val'})

        element.handle_data('here_some_data')
        self.assertEqual(
            doc_struct.TextRun(attrs={'k': 'val'},
                               style={},
                               text='here_some_data'), element.to_struct())

    def test_collect_data_with_spaces(self):
        """Test collecting text fragments."""
        context = _base.ParseContext()
        element = _paragraph_elements.ParagraphElementFrame(context)

        element.handle_data('   ')
        element.handle_data('some     data \n\none one\tline 1')
        element.handle_data('')
        element.handle_data('23')
        element.handle_data('\n')
        text_run = element.to_struct()
        if not isinstance(text_run, doc_struct.TextRun):
            self.fail()
        self.assertEqual(' some data one one line 123 ', text_run.text)

    def test_collect_data_empty(self):
        """Test struct conversion when no data added."""
        context = _base.ParseContext()
        element = _paragraph_elements.ParagraphElementFrame(context)

        text_run = element.to_struct()
        if not isinstance(text_run, doc_struct.TextRun):
            self.fail()
        self.assertEqual('', text_run.text)

    def test_collect_data_with_breaks(self):
        """Test struct conversion when line breaks are present."""
        context = _base.ParseContext()
        element = _paragraph_elements.ParagraphElementFrame(context)

        element.handle_data('before')
        element.handle_start('br', {})
        element.handle_data('after')

        text_run = element.to_struct()
        if not isinstance(text_run, doc_struct.TextRun):
            self.fail()
        self.assertEqual('before\nafter', text_run.text)


class LineBreakTest(unittest.TestCase):
    """Test for line breaks (br)."""

    def test_no_context_change(self):
        """Ensure that br doesn't change context entering or exiting."""
        context = _base.ParseContext()
        text = _paragraph_elements.ParagraphElementFrame(context, {'k': 'val'})

        self.assertIsNone(text.handle_start('xx', {}))
        self.assertIsNone(text.handle_end('br'))


class TextTest(unittest.TestCase):
    """Test text run class."""

    def test_simple(self):
        """Simple test, including construction."""
        context = _base.ParseContext()
        text = _paragraph_elements.ParagraphElementFrame(context, {'k': 'val'})

        text.handle_data('here_some_data')
        self.assertEqual(
            doc_struct.TextRun(
                attrs={'k': 'val'},
                style={},
                text='here_some_data',
            ), text.to_struct())

    def test_end_tag(self):
        """Test to ensure that ending span tags cause context update."""
        context = _base.ParseContext()
        text = _paragraph_elements.ParagraphElementFrame(context, {})

        self.assertIsNone(text.handle_end('br'))
        self.assertEqual(text, text.handle_end('span'))


_CHIP_STYLE = {'color': '#0000ee', 'text-decoration': 'underline'}


class ChipTest(unittest.TestCase):
    """Test the chip class."""

    def test_simple(self):
        """Simple test, including construction."""
        context = _base.ParseContext()
        chip = _paragraph_elements.ParagraphElementFrame(
            context, {'k': 'val'}, _CHIP_STYLE)
        chip.url = 'http://whatever'

        chip.handle_data('some_text')
        self.assertEqual(
            doc_struct.Chip(attrs={'k': 'val'},
                            style=_CHIP_STYLE,
                            text='some_text',
                            url='http://whatever'), chip.to_struct())

    def test_simple_link(self):
        """Simple test, including construction."""
        context = _base.ParseContext()
        chip = _paragraph_elements.ParagraphElementFrame(context, {'k': 'val'})
        chip.url = 'http://whatever'

        chip.handle_data('some_text')
        self.assertEqual(
            doc_struct.Link(attrs={'k': 'val'},
                            style={},
                            text='some_text',
                            url='http://whatever'), chip.to_struct())

    def test_end_tag(self):
        """Test to ensure that ending span tags cause context update."""
        context = _base.ParseContext()
        chip = _paragraph_elements.ParagraphElementFrame(context, {})

        self.assertIsNone(chip.handle_end('br'))
        self.assertEqual(chip, chip.handle_end('span'))

    def test_start_tag(self):
        """Test to ensure that ending span tags cause context update."""
        context = _base.ParseContext()
        chip = _paragraph_elements.ParagraphElementFrame(context, {})

        self.assertIsNone(chip.handle_start('a', {'href': 'http://whatever'}))
        self.assertEqual(chip.url, 'http://whatever')


class SuperscriptTest(unittest.TestCase):
    """Test the superscript frame class."""

    def test_start_tag(self):
        """Test to check if nested a tags set the url."""
        context = _base.ParseContext()
        sup = _paragraph_elements.SuperscriptFrame(context)

        sup.handle_data('some_text')
        sup.handle_start('a', {'href': 'http://whatever'})
        self.assertEqual(
            doc_struct.Reference(
                text='some_text',
                url='http://whatever',
            ), sup.to_struct())

    def test_end_tag(self):
        """Test to ensure that we're not mixing this with span tags."""
        context = _base.ParseContext()
        sup = _paragraph_elements.SuperscriptFrame(context)

        self.assertRaisesRegex(_base.UnexpectedHtmlTag,
                               'Unexpected tag span.*',
                               lambda: sup.handle_end('span'))
        self.assertEqual(sup, sup.handle_end('sup'))


class PlainAnchorTest(unittest.TestCase):
    """Test the plain anchor frame class."""

    def test_simple(self):
        """Simple test, including construction."""

        attrs = {'href': 'http://whatever', 'id': '#me'}
        context = _base.ParseContext()
        anchor = _paragraph_elements.PlainAnchorFrame(context, attrs)

        anchor.handle_data('some_text')
        self.assertEqual(
            doc_struct.ReferenceTarget(attrs=attrs,
                                       text='some_text',
                                       ref_id='#me'), anchor.to_struct())

    def test_end_tag(self):
        """Test to ensure that we're not mixing this with span tags."""
        context = _base.ParseContext()
        sup = _paragraph_elements.PlainAnchorFrame(context)

        self.assertRaisesRegex(_base.UnexpectedHtmlTag,
                               'Unexpected tag span.*',
                               lambda: sup.handle_end('span'))
        self.assertEqual(sup, sup.handle_end('a'))
