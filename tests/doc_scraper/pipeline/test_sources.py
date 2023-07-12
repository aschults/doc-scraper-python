"""Test the sources and builder for bullet lists/items."""

import dataclasses
import unittest
from unittest import mock
from typing import Type, Any

from pyfakefs import fake_filesystem_unittest  # type: ignore

from doc_scraper.pipeline import sources
from doc_scraper import doc_struct
from doc_scraper import doc_loader


def _create_dummy_doc(tag_string: str) -> doc_struct.Document:
    """Create a simple doc containing a tag string."""
    return doc_struct.Document(
        attrs={'tag': tag_string},
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
    text_converter = doc_struct.RawTextConverter()
    return text_converter.convert(paragraph.elements[0])


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

# Sample response of DocDownloader.list_files
DRIVE_ENTRIES = [
    {
        'kind': 'drive#file',
        'mimeType': 'application/vnd.google-apps.document',
        'id': '_id1_',
        'name': '_name1_'
    },
    {
        'kind': 'drive#file',
        'mimeType': 'application/vnd.google-apps.document',
        'id': '_id2_',
        'name': '_name2_'
    },
]


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
        mock_downloader: Any = mock.Mock(spec=doc_loader.DocDownloader)
        mock_downloader.get_from_html.side_effect = [  # type: ignore
            _create_dummy_doc(tag) for tag in ('t1', 't2')
        ]
        loader = sources.DocLoader(doc_ids=['id1'],
                                   downloader_or_creds_store=mock_downloader)
        loader.set_commandline_args('id2')

        result = [_get_doc_tag(doc) for doc in loader]

        self.assertEqual(['t1', 't2'], result)

    def test_doc_downloader_by_config(self):
        """Test parsing doc usind downloader."""
        mock_creds = mock.Mock(spec=doc_loader.Credentials)
        creds_store = doc_loader.CredentialsStore()
        creds_store.add_credentials(mock_creds, 'someone')

        init_method_name = 'doc_scraper.doc_loader.DocDownloader.__init__'
        with mock.patch(init_method_name) as getter_patch:
            getter_patch.return_value = None
            config = sources.DocLoaderConfig(doc_ids=['id1'],
                                             username='someone')
            sources.DocLoader.from_config(config, creds_store)

            getter_patch.assert_called_once_with(username='someone',
                                                 creds_store=creds_store)

    def test_doc_downloader_by_config_default_user(self):
        """Test parsing doc usind downloader."""
        mock_creds = mock.Mock(spec=doc_loader.Credentials)
        creds_store = doc_loader.CredentialsStore()
        creds_store.add_credentials(mock_creds, 'someone', make_default=True)

        init_method_name = 'doc_scraper.doc_loader.DocDownloader.__init__'
        with mock.patch(init_method_name) as getter_patch:
            getter_patch.return_value = None
            config = sources.DocLoaderConfig(doc_ids=['id1'])
            sources.DocLoader.from_config(config, creds_store)

            getter_patch.assert_called_once_with(username='',
                                                 creds_store=creds_store)

    def test_doc_downloader_from_query(self):
        """Check if queries are passed down to the doc downloader."""
        mock_downloader: Any = mock.Mock(spec=doc_loader.DocDownloader)
        mock_downloader.get_from_html.side_effect = [  # type: ignore
            _create_dummy_doc(tag) for tag in ('t1', 't2', 't3', 't4')
        ]
        mock_downloader.list_files.return_value = DRIVE_ENTRIES
        loader = sources.DocLoader(queries=['_q1_', '_q2_'],
                                   downloader_or_creds_store=mock_downloader)
        result = [item.attrs for item in loader]
        self.assertEqual([{
            'doc_id': f'_id{id_}_',
            'doc_name': f'_name{id_}_',
            'tag': f't{index+1}'
        } for index, id_ in enumerate([1, 2, 1, 2])], result)
        self.assertEqual([
            mock.call.list_files('_q1_'),
            mock.call.get_from_html('_id1_'),
            mock.call.get_from_html('_id2_'),
            mock.call.list_files('_q2_'),
            mock.call.get_from_html('_id1_'),
            mock.call.get_from_html('_id2_')
        ], mock_downloader.mock_calls)
