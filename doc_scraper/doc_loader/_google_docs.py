# type: ignore
"""Download Google Docs in various formats.

Currently only Google Drive API, using HTML export of Google Docs.
"""

from typing import Any, Optional
import logging

from google.auth import credentials as auth_credentials  # type: ignore
from googleapiclient import discovery, http

from doc_scraper import doc_struct, html_extractor

from . import _auth


class DocDownloader():
    """Download Google Docs and convert them to doc_struct."""

    def __init__(self,
                 creds: Optional[auth_credentials.Credentials] = None) -> None:
        """Create an instance.

        Args:
            creds: Credentials to use when accessing the doc.
        """
        self._creds = creds or _auth.get_credentials_from_webserver_auth()

    def get_json(self, doc_id: str) -> Any:
        """Get the doc as native JSON."""
        # pylint: disable=no-member
        docs_service = discovery.build('docs', 'v1', credentials=self._creds)
        req: http.HttpRequest = docs_service.documents().get(documentId=doc_id)
        resp = req.execute()
        return resp

    def _get_raw_html(self, doc_id: str) -> str:
        """Get the doc from drive, in HTML format."""
        # pylint: disable=no-member
        logging.info('Fetching from Google Drive: %s, creds: %s', doc_id,
                     self._creds)
        mime_type = "text/html"
        docs_service: Any = discovery.build('drive',
                                            'v3',
                                            credentials=self._creds)
        req: http.HttpRequest = docs_service.files().export_media(
            fileId=doc_id, mimeType=mime_type)
        resp = req.execute()
        if isinstance(resp, bytes):
            resp = resp.decode('utf-8')
        logging.debug('Raw HTML: %s', resp)
        return resp

    def get_from_html(self, doc_id: str) -> doc_struct.Document:
        """Create doc structure from the HTML based form of a Google Doc."""
        content = self._get_raw_html(doc_id=doc_id)
        parser = html_extractor.ToStructParser()
        parser.feed(content)
        return parser.as_struct()
