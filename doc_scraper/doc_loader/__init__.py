"""Classes to load documents, in doc_struct form.

Currently only fetching Google Docs via Google Drive API as HTML is
implemented.
"""
from ._auth import get_credentials_from_files
from ._google_docs import DocDownloader

_ = [get_credentials_from_files, DocDownloader]
