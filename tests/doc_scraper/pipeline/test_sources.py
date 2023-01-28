"""Test the sources and builder for bullet lists/items."""

import dataclasses
import unittest
from unittest import mock
from typing import Type

from pyfakefs import fake_filesystem_unittest  # type: ignore

from doc_scraper.pipeline import sources
from doc_scraper import doc_struct
from doc_scraper import doc_loader


def _create_dummy_doc(tag_string: str) -> doc_struct.Document:
    """Create a simple doc containing a tag string."""
    return doc_struct.Document(
        shared_data=doc_struct.SharedData(),
        content=doc_struct.DocContent(elements=[
            doc_struct.Paragraph(
                elements=[doc_struct.TextRun(text=tag_string)])
        ]))


def _get_doc_tag(doc: doc_struct.Document) -> str:
    """Extract the tag from the doc for verification."""
    paragraph = doc.content.elements[0]
    if not isinstance(paragraph, doc_struct.Paragraph):
        raise AssertionError('Not a paragraph')
    return paragraph.elements[0].as_plain_text()


@dataclasses.dataclass(kw_only=True)
class ConfigForTest():
    """Simple config to test the builder."""

    attr_a: int = 0
    attr_b: str = ''
    attr_c: Type[doc_struct.Element] = doc_struct.Element


class TestBuilder(unittest.TestCase):
    """Test the soure builder."""

    def setUp(self) -> None:
        """Provide a default builder instance."""
        super().setUp()
        self.builder = sources.SourceBuilder()

    def test_simple_register(self):
        """Test simple register and create an instance."""
        self.builder.register('x', lambda: [_create_dummy_doc('a')])
        result = self.builder.create_instance('x')

        self.assertEqual('a', _get_doc_tag(next(iter(result))))

    def test_chained(self):
        """Test creation of a chained source instance."""
        self.builder.register(
            'x', lambda: [_create_dummy_doc('a0'),
                          _create_dummy_doc('a1')])
        self.builder.register('y', lambda s: [_create_dummy_doc(s)])

        result = self.builder.create_chain(
            sources.SourceConfig(kind='x'),
            sources.SourceConfig(kind='y', config='b'))

        self.assertEqual(['a0', 'a1', 'b'],
                         [_get_doc_tag(item) for item in result])


# JTML doc to pars for source tests.
HTML_DOC = '''
<html>
    <body>
        <p>__content__</p>
    </body>
</html>
'''


class TestSources(fake_filesystem_unittest.TestCase):
    """Test the basic source types."""

    def setUp(self) -> None:
        """Set up fake filesystem."""
        super().setUp()
        self.setUpPyfakefs()

    def test_file_loader(self):
        """Test lading and parsing a doc from file."""
        self.fs.create_file(  # type: ignore
            file_path='/file', contents=HTML_DOC)
        self.fs.create_file(  # type: ignore
            file_path='/file2',
            contents=HTML_DOC.replace('__content__', '__content2__'))
        loader = sources.FileLoader(doc_filenames=['/file'])
        loader.set_commandline_args('/file2')

        result = [_get_doc_tag(doc) for doc in loader]

        self.assertEqual(['__content__', '__content2__'], result)

    def test_doc_downloader(self):
        """Test parsing doc usind downloader."""
        mock_downloader = mock.Mock(spec=doc_loader.DocDownloader)
        mock_downloader.get_from_html.side_effect = [  # type: ignore
            _create_dummy_doc(tag) for tag in ('t1', 't2')
        ]
        loader = sources.DocLoader(doc_ids=['id1'],
                                   doc_downloader=mock_downloader)
        loader.set_commandline_args('id2')

        result = [_get_doc_tag(doc) for doc in loader]

        self.assertEqual(['t1', 't2'], result)
