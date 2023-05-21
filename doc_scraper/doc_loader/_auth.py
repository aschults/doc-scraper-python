# type: ignore
"""Provide Authentication methods to access the documents."""

import logging
import glob

from typing import Sequence, Optional, Dict

from google_auth_oauthlib import flow
from google.auth import credentials as auth_credentials
from google.oauth2 import credentials
from google.oauth2 import service_account
from google.auth.transport import requests as goog_requests
from google.auth.exceptions import RefreshError

# Default scopes to use for OAuth.
DEFAULT_SCOPES: Sequence[str] = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive.readonly'
]


class CredentialsStore():
    """Class containing available credentials for Google services."""

    # Username to use when storing/fetching the default cred.
    DEFAULT_USERNAME = ''

    def __init__(self) -> None:
        """Construct an instance."""
        self._by_user: Dict[str, auth_credentials.Credentials] = dict()

    def from_username(
        self,
        username: Optional[str] = None,
    ) -> auth_credentials.Credentials:
        """Fetch credentials by username."""
        if username is None:
            username = ''
        return self._by_user[username]

    def get_default(self) -> credentials.Credentials:
        """Get the default creds."""
        return self._by_user[self.DEFAULT_USERNAME]

    def add_credentials(self,
                        creds: credentials.Credentials,
                        username: Optional[str] = None,
                        make_default=False) -> None:
        """Add a credential by username, optionally as default."""
        if username is None:
            username = creds.client_id
        self._by_user[username] = creds
        if make_default:
            self._by_user[self.DEFAULT_USERNAME] = creds

    def add_available_credentials(self) -> None:
        """Try to add all implemented credential forms."""
        try:
            creds = get_credentials_from_webserver_auth()
            self._by_user[self.DEFAULT_USERNAME] = creds
            self._by_user[creds.client_id] = creds
        except FileNotFoundError:
            logging.info(
                'Could not find credentials files, continuing without.')

        creds_list = get_credentials_from_service_account()
        for creds in creds_list:
            self._by_user[creds.service_account_email] = creds

        if self.DEFAULT_USERNAME not in self._by_user and creds_list:
            self._by_user[self.DEFAULT_USERNAME] = creds_list[0]

    def __str__(self) -> str:
        return f'CredentialsStore({self._by_user})'


def get_credentials_from_webserver_auth(
        client_secret_file: str = 'client_secret.json',
        credentials_file: str = 'credentials.json',
        scopes: Optional[Sequence[str]] = None) -> credentials.Credentials:
    """Return Google OAuth credentials.

    Args:
        client_secret_file: Filename for JSON file as described in
            https://github.com/googleapis/google-api-python-client/blob/main/docs/client-secrets.md
        credentials_file: Filename to file containing the JSON-serialized
            version of google.oauth2.credentials.Credentials

    Returns:
        The credentials either rom credentials file or as a result of the
        OAuth flow. The returned credentials are stored in credentials_file
    """
    creds: Optional[credentials.Credentials] = None
    try:
        creds = credentials.Credentials.from_authorized_user_file(
            credentials_file, scopes or DEFAULT_SCOPES)
        if creds.valid:
            return creds
        creds.refresh(goog_requests.Request())
    except FileNotFoundError as exception:
        logging.info('No credentials file found: %s', exception)
    except ValueError as exception:
        logging.info('Could not parse content of credemtials file: %s',
                     exception)
    except RefreshError as exception:
        logging.info('could not refresh token: %s', exception)

    if creds is None or not creds.valid:
        client_flow = flow.InstalledAppFlow.from_client_secrets_file(
            client_secret_file, scopes or DEFAULT_SCOPES)
        creds = client_flow.run_local_server()

    if creds is None or not creds.valid:
        raise ValueError(f'Expecting valid credentials, got {creds}')

    try:
        with open(credentials_file, "w", encoding='utf-8') as filehandle:
            filehandle.write(creds.to_json())
    except OSError as exception:
        logging.warning('could not write credentials to file: %s', exception)

    return creds


def get_credentials_from_service_account(
    fileglob: str = 'service_accounts/*.json'
) -> Sequence[service_account.Credentials]:
    """Create service account credentials from a glob of creds files."""
    result: Sequence[service_account.Credentials] = []

    for acc_filename in glob.glob(fileglob):
        result.append(
            service_account.Credentials.from_service_account_file(
                acc_filename))
    return result
