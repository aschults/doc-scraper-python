"""Tests for the OAuth authentication for Google."""

from unittest import mock
import os.path
from typing import Any

from google.auth import exceptions  # type: ignore
from google.oauth2 import credentials  # type: ignore
from google_auth_oauthlib import flow  # type: ignore
from pyfakefs import fake_filesystem_unittest  # type: ignore

from doc_scraper.doc_loader import _auth  # type: ignore


class TestAuth(fake_filesystem_unittest.TestCase):
    """Test the auth module."""

    def setUp(self) -> None:
        """Set up the mocks for the Google Auth API and filesystem."""
        super().setUp()

        credentials_patcher = mock.patch(
            'google.oauth2.credentials.Credentials',
            spec=credentials.Credentials)
        self.mock_creds_class: Any = credentials_patcher.start()
        self.addCleanup(credentials_patcher.stop)
        self.mock_creds: Any = mock.Mock(spec=credentials.Credentials)
        self.mock_creds.to_json.return_value = '123'
        mock_from_file = self.mock_creds_class.from_authorized_user_file
        mock_from_file.return_value = self.mock_creds

        flow_patcher = mock.patch('google_auth_oauthlib.flow.InstalledAppFlow',
                                  spec=flow.InstalledAppFlow)
        self.mock_flow_class: Any = flow_patcher.start()
        self.addCleanup(flow_patcher.stop)
        self.mock_flow: Any = mock.Mock(spec=flow.InstalledAppFlow)
        mock_from_secrets = self.mock_flow_class.from_client_secrets_file
        mock_from_secrets.return_value = self.mock_flow

        self.mock_creds2: Any = mock.Mock(spec=credentials.Credentials)
        self.mock_creds2.to_json.return_value = '234'
        self.mock_flow.run_console.return_value = self.mock_creds2

        self.setUpPyfakefs()

    def test_get_credentials_from_files_valid(self):
        """Test when file credentials are initially valid."""
        self.mock_creds.valid = True
        creds: Any = _auth.get_credentials_from_files(
            credentials_file='creds.json', scopes=['a', 'b'])
        self.assertEqual(self.mock_creds, creds)
        self.mock_creds_class.from_authorized_user_file.assert_called_with(
            'creds.json', ['a', 'b'])
        creds.refresh.assert_not_called()
        self.mock_flow_class.from_client_secrets_file.assert_not_called()
        self.assertFalse(os.path.exists('creds.json'))

    def test_get_credentials_from_files_refresh(self):
        """Test when credentials are valid after refresh."""
        self.mock_creds.valid = False

        def set_creds_valid(_: Any) -> None:
            """Change the credential to True as side effect."""
            self.mock_creds.valid = True

        self.mock_creds.refresh.side_effect = set_creds_valid

        creds: Any = _auth.get_credentials_from_files(
            credentials_file='creds.json')
        self.assertEqual(self.mock_creds, creds)
        self.mock_creds_class.from_authorized_user_file.assert_called_with(
            'creds.json', mock.ANY)
        creds.refresh.assert_called()
        self.mock_flow_class.from_client_secrets_file.assert_not_called()
        with open('creds.json', 'r', encoding='utf-8') as cred_file:
            self.assertEqual('123', cred_file.read())

    def test_get_credentials_from_files_flow(self):
        """Test when file credentials are valid after OAuth flow."""
        self.mock_creds.valid = False
        self.mock_creds2.valid = True

        creds = _auth.get_credentials_from_files(client_secret_file='cs.json',
                                                 credentials_file='creds.json',
                                                 scopes=['a'])

        self.assertEqual(self.mock_creds2, creds)
        self.mock_creds_class.from_authorized_user_file.assert_called_with(
            'creds.json', ['a'])
        self.mock_creds.refresh.assert_called()
        self.mock_flow_class.from_client_secrets_file.assert_called_with(
            'cs.json', ['a'])
        self.mock_flow.run_console.assert_called()
        with open('creds.json', 'r', encoding='utf-8') as cred_file:
            self.assertEqual('234', cred_file.read())

    def test_get_credentials_from_files_no_creds_file(self):
        """Test when creds file is missing."""
        self.mock_creds.valid = False
        self.mock_creds2.valid = True

        mock_from_file = self.mock_creds_class.from_authorized_user_file
        mock_from_file.side_effect = FileNotFoundError

        creds = _auth.get_credentials_from_files(credentials_file='creds.json')

        self.assertEqual(self.mock_creds2, creds)
        self.mock_creds_class.from_authorized_user_file.assert_called()
        self.mock_creds.refresh.assert_not_called()
        self.mock_flow_class.from_client_secrets_file.assert_called()
        self.mock_flow.run_console.assert_called()

    def test_get_credentials_from_files_no_refresh(self):
        """Test when refresh goes wrong."""
        self.mock_creds.valid = False
        self.mock_creds2.valid = True

        self.mock_creds.refresh.side_effect = exceptions.RefreshError

        creds = _auth.get_credentials_from_files(credentials_file='creds.json')

        self.assertEqual(self.mock_creds2, creds)
        self.mock_creds_class.from_authorized_user_file.assert_called()
        self.mock_creds.refresh.assert_called()
        self.mock_flow_class.from_client_secrets_file.assert_called()
        self.mock_flow.run_console.assert_called()
