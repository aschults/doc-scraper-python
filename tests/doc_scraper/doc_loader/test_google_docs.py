"""Tests for the Google document downloader."""

from unittest import mock
from pyfakefs import fake_filesystem_unittest  # type: ignore
from parameterized import parameterized  # type:ignore

from typing import Any
from google.oauth2 import credentials  # type: ignore

from doc_scraper import doc_struct

from doc_scraper.doc_loader import _google_docs  # type: ignore
from doc_scraper.doc_loader import _auth  # type: ignore

HTML_DOC = '''
<html>
    <body>
        <p>__content__</p>
    </body>
</html>
'''

BAD_HTML = '<html><body><p>no html close</p></body>'

# Response of drive.files.list, partial result / first page
DRIVE_FILE_LIST1 = {
    'kind':
        'drive#fileList',
    'incompleteSearch':
        True,
    'nextPageToken':
        't2',
    'files': [
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
    ],
}

# drive.files.list result, last page.
DRIVE_FILE_LIST2 = {
    'kind':
        'drive#fileList',
    'incompleteSearch':
        False,
    'files': [{
        'kind': 'drive#file',
        'mimeType': 'application/vnd.google-apps.document',
        'id': '_id3_',
        'name': '_name3_'
    }],
}

MIME = 'application/vnd.google-apps.document'


def _get_doc_tag(doc: doc_struct.Document) -> str:
    paragraph = doc.content.elements[0]
    if not isinstance(paragraph, doc_struct.Paragraph):
        raise AssertionError('Not a paragraph')
    text_converter = doc_struct.RawTextConverter()
    return text_converter.convert(paragraph.elements[0])


class TestDocDownloader(fake_filesystem_unittest.TestCase):
    """Test Google Docs download (as HTML via Drive)."""

    def setUp(self) -> None:
        """Set up fake filesystem."""
        super().setUp()
        self.setUpPyfakefs()

        discovery_patcher = mock.patch('googleapiclient.discovery.build')

        self.mock_build = discovery_patcher.start()
        self.addCleanup(discovery_patcher.stop)

        self.mock_service: Any = mock.Mock()
        self.mock_service.files().export_media(
        ).execute.return_value = HTML_DOC
        self.mock_service.files().list().execute.side_effect = [
            DRIVE_FILE_LIST1, DRIVE_FILE_LIST2
        ]

        self.mock_build.return_value = self.mock_service

        self.mock_creds = mock.Mock(spec=credentials.Credentials)
        self.creds_store = _auth.CredentialsStore()
        self.creds_store.add_credentials(self.mock_creds, make_default=True)

    def test_html_download(self):
        """Test a successful download."""
        downloader = _google_docs.DocDownloader(creds_store=self.creds_store)

        result = downloader.get_from_html('id1')
        self.assertEqual('__content__', _get_doc_tag(result))

        self.assertEqual(['tmp'], self.fs.listdir('/'))

    def test_html_download_dump(self):
        """Test a successful download."""
        downloader = _google_docs.DocDownloader(creds_store=self.creds_store)

        _google_docs.DocDownloader.raw_html_dump_dir = '/'

        result = downloader.get_from_html('id1')
        self.assertEqual('__content__', _get_doc_tag(result))

        self.assertIn(
            '__content__',
            self.fs.get_object('/id1_raw.html').contents)  # type: ignore

    def test_html_download_empty(self):
        """Test a successful download of an empty doc."""
        self.mock_service.files().export_media().execute.return_value = ''

        downloader = _google_docs.DocDownloader(creds_store=self.creds_store)

        self.assertRaisesRegex(ValueError, 'No HTML document root found',
                               lambda: downloader.get_from_html('id1'))

    def test_html_download_api_fail(self):
        """Test a download when the API fails."""
        self.mock_service.files().export_media(
        ).execute.side_effect = Exception('expected')

        downloader = _google_docs.DocDownloader(creds_store=self.creds_store)

        self.assertRaisesRegex(Exception, 'expected',
                               lambda: downloader.get_from_html('id1'))

    def test_html_download_parse_fail(self):
        """Test a download when HTML parsing fails."""
        self.mock_service.files().export_media(
        ).execute.return_value = BAD_HTML

        downloader = _google_docs.DocDownloader(creds_store=self.creds_store)

        self.assertRaisesRegex(ValueError, '.*balanced.*',
                               lambda: downloader.get_from_html('id1'))

    def test_delayed_cred_use(self):
        """Test a successful download."""
        downloader = _google_docs.DocDownloader(
            username='whoever@wherever.com', creds_store=self.creds_store)

        self.creds_store.add_credentials(self.mock_creds,
                                         'whoever@wherever.com')
        result = downloader.get_from_html('id1')
        self.assertEqual('__content__', _get_doc_tag(result))

    def test_files_list(self):
        """Test listing Drive files."""
        downloader = _google_docs.DocDownloader(creds_store=self.creds_store)

        result = list(downloader.list_files('_q_'))

        self.assertEqual(
            [f'_name{i}_' for i in [1, 2, 3]],
            [item['name'] for item in result],
        )

        self.assertEqual(
            [f'_id{i}_' for i in [1, 2, 3]],
            [item['id'] for item in result],
        )

    @parameterized.expand([  # type:ignore
        (
            'default',
            {},
            '(_q_) and sharedWithMe = true and trashed = false ' +
            f'and mimeType = {MIME!r}',
        ),
        (
            'none_shared',
            {
                'shared_with_me': None
            },
            f'(_q_) and trashed = false and mimeType = {MIME!r}',
        ),
        (
            'shared_false_trash_true',
            {
                'shared_with_me': False,
                'is_trashed': True
            },
            '(_q_) and sharedWithMe = false and trashed = true ' +
            f'and mimeType = {MIME!r}',
        ),
        (
            'minimal',
            {
                'shared_with_me': None,
                'is_trashed': None,
                'docs_only': False
            },
            '(_q_)',
        ),
    ])
    def test_files_list_kwargs(self, name: str, kwargs: Any, expected: str):
        """Test the effects of kwargs on the query string."""
        downloader = _google_docs.DocDownloader(creds_store=self.creds_store)

        _ = list(downloader.list_files('_q_', **kwargs))

        self.mock_service.files().list.assert_called_with(
            q=expected, pageToken='t2', includeItemsFromAllDrives=True)

    def test_files_list_minimal_not_all(self):
        """Test a minimal query with all drives set to false."""
        downloader = _google_docs.DocDownloader(creds_store=self.creds_store)

        _ = list(
            downloader.list_files('_q_',
                                  all_drives=False,
                                  docs_only=False,
                                  is_trashed=None,
                                  shared_with_me=None))

        self.mock_service.files().list.assert_called_with(
            q='(_q_)', pageToken='t2', includeItemsFromAllDrives=False)
