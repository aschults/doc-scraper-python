"""Tests for the Google document downloader."""

import unittest
from unittest import mock

from typing import Any
from google.oauth2 import credentials  # type: ignore

from doc_scraper import doc_struct

from doc_scraper.doc_loader import _google_docs  # type: ignore

HTML_DOC = '''
<html>
    <body>
        <p>__content__</p>
    </body>
</html>
'''

BAD_HTML = '<html><body><p>no html close</p></body>'


def _get_doc_tag(doc: doc_struct.Document) -> str:
    paragraph = doc.content.elements[0]
    if not isinstance(paragraph, doc_struct.Paragraph):
        raise AssertionError('Not a paragraph')
    return paragraph.elements[0].as_plain_text()


class TestDocDownloader(unittest.TestCase):
    """Test Google Docs download (as HTML via Drive)."""

    def setUp(self) -> None:
        """Set up mocks for discovery API."""
        super().setUp()

        discovery_patcher = mock.patch('googleapiclient.discovery.build')

        self.mock_build = discovery_patcher.start()
        self.addCleanup(discovery_patcher.stop)

        self.mock_service: Any = mock.Mock()
        self.mock_service.files().export_media(
        ).execute.return_value = HTML_DOC
        self.mock_build.return_value = self.mock_service

        self.mock_creds = mock.Mock(spec=credentials.Credentials)

    def test_html_download(self):
        """Test a successful download."""
        downloader = _google_docs.DocDownloader(creds=self.mock_creds)

        result = downloader.get_from_html('id1')
        self.assertEqual('__content__', _get_doc_tag(result))

    def test_html_download_empty(self):
        """Test a successful download of an empty doc."""
        self.mock_service.files().export_media().execute.return_value = ''

        downloader = _google_docs.DocDownloader(creds=self.mock_creds)

        self.assertRaisesRegex(ValueError, 'No HTML document root found',
                               lambda: downloader.get_from_html('id1'))

    def test_html_download_api_fail(self):
        """Test a download when the API fails."""
        self.mock_service.files().export_media(
        ).execute.side_effect = Exception('expected')

        downloader = _google_docs.DocDownloader(creds=self.mock_creds)

        self.assertRaisesRegex(Exception, 'expected',
                               lambda: downloader.get_from_html('id1'))

    def test_html_download_parse_fail(self):
        """Test a download when HTML parsing fails."""
        self.mock_service.files().export_media(
        ).execute.return_value = BAD_HTML

        downloader = _google_docs.DocDownloader(creds=self.mock_creds)

        self.assertRaisesRegex(ValueError, '.*balanced.*',
                               lambda: downloader.get_from_html('id1'))