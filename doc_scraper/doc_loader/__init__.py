"""Classes to load documents, in doc_struct form.

Currently only fetching Google Docs via Google Drive API as HTML is
implemented.
"""

from ._auth import (
    get_credentials_from_service_account,
    get_credentials_from_webserver_auth,
    CredentialsStore,
)
from ._google_docs import DocDownloader
from google.auth.credentials import Credentials  # type:ignore

_ = [
    get_credentials_from_webserver_auth,
    get_credentials_from_service_account,
    DocDownloader,
    Credentials,
    CredentialsStore,
]
