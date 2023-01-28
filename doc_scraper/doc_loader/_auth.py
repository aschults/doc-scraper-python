# type: ignore
"""Provide Authentication methods to access the documents."""

import logging
from typing import Sequence, Optional

from google_auth_oauthlib import flow
from google.oauth2 import credentials
from google.auth.transport import requests as goog_requests
from google.auth.exceptions import RefreshError

# Default scopes to use for OAuth.
DEFAULT_SCOPES: Sequence[str] = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive.readonly'
]


def get_credentials_from_files(
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
        creds = client_flow.run_console()

    if creds is None or not creds.valid:
        raise ValueError(f'Expecting valid credentials, got {creds}')

    try:
        with open(credentials_file, "w", encoding='utf-8') as filehandle:
            filehandle.write(creds.to_json())
    except OSError as exception:
        logging.warning('could not write credentials to file: %s', exception)

    return creds
