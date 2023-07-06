# type: ignore
"""Download Google Docs in various formats.

Currently only Google Drive API, using HTML export of Google Docs.
"""

from typing import Any, Optional
import logging
import os.path

from google.auth import credentials as auth_credentials  # type: ignore
from googleapiclient import discovery, http

from doc_scraper import doc_struct, html_extractor

from . import _auth


class DocDownloader():
    """Download Google Docs and convert them to doc_struct."""

    raw_html_dump_dir: Optional[str] = None

    # API Key, for use with the API client
    developer_key: Optional[str] = None

    def __init__(self,
                 username: Optional[str] = None,
                 creds_store: Optional[_auth.CredentialsStore] = None) -> None:
        """Create an instance.

        Args:
            username: Username associated with the credentials to use.
            creds_store: Credentials manager to use when accessing docs.
        """
        self._username = username

        if creds_store is None:
            creds_store = _auth.CredentialsStore()
            creds_store.add_available_credentials()
        self._creds_manager = creds_store

    @property
    def _creds(self) -> auth_credentials.Credentials:
        return self._creds_manager.from_username(self._username)

    def get_json(self, doc_id: str) -> Any:
        """Get the doc as native JSON."""
        # pylint: disable=no-member
        docs_service = discovery.build('docs',
                                       'v1',
                                       credentials=self._creds,
                                       developerKey=self.developer_key)
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
                                            credentials=self._creds,
                                            developerKey=self.developer_key)
        req: http.HttpRequest = docs_service.files().export_media(
            fileId=doc_id, mimeType=mime_type)
        resp = req.execute()
        if isinstance(resp, bytes):
            resp = resp.decode('utf-8')

        if self.raw_html_dump_dir is not None:
            dump_path = os.path.join(self.raw_html_dump_dir,
                                     doc_id + '_raw.html')
            with open(dump_path, 'w', encoding='utf-8') as dump_file:
                dump_file.write(resp)

        return resp

    def get_from_html(self, doc_id: str) -> doc_struct.Document:
        """Create doc structure from the HTML based form of a Google Doc."""
        content = self._get_raw_html(doc_id=doc_id)
        parser = html_extractor.ToStructParser()
        parser.feed(content)
        return parser.as_struct()
