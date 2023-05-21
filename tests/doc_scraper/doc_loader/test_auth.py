"""Tests for the OAuth authentication for Google."""

from unittest import mock
import os
import os.path
from typing import Any

from google.auth import exceptions  # type: ignore
from google.oauth2 import credentials  # type: ignore
from google.oauth2 import service_account  # type: ignore
from google_auth_oauthlib import flow  # type: ignore
from pyfakefs import fake_filesystem_unittest  # type: ignore

from doc_scraper.doc_loader import _auth  # type: ignore


class TestServerAuth(fake_filesystem_unittest.TestCase):
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
        self.mock_flow.run_local_server.return_value = self.mock_creds2

        self.setUpPyfakefs()

    def test_get_credentials_from_files_valid(self):
        """Test when file credentials are initially valid."""
        self.mock_creds.valid = True
        creds: Any = _auth.get_credentials_from_webserver_auth(
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

        creds: Any = _auth.get_credentials_from_webserver_auth(
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

        creds = _auth.get_credentials_from_webserver_auth(
            client_secret_file='cs.json',
            credentials_file='creds.json',
            scopes=['a'])

        self.assertEqual(self.mock_creds2, creds)
        self.mock_creds_class.from_authorized_user_file.assert_called_with(
            'creds.json', ['a'])
        self.mock_creds.refresh.assert_called()
        self.mock_flow_class.from_client_secrets_file.assert_called_with(
            'cs.json', ['a'])
        self.mock_flow.run_local_server.assert_called()
        with open('creds.json', 'r', encoding='utf-8') as cred_file:
            self.assertEqual('234', cred_file.read())

    def test_get_credentials_from_files_no_creds_file(self):
        """Test when creds file is missing."""
        self.mock_creds.valid = False
        self.mock_creds2.valid = True

        mock_from_file = self.mock_creds_class.from_authorized_user_file
        mock_from_file.side_effect = FileNotFoundError

        creds = _auth.get_credentials_from_webserver_auth(
            credentials_file='creds.json')

        self.assertEqual(self.mock_creds2, creds)
        self.mock_creds_class.from_authorized_user_file.assert_called()
        self.mock_creds.refresh.assert_not_called()
        self.mock_flow_class.from_client_secrets_file.assert_called()
        self.mock_flow.run_local_server.assert_called()

    def test_get_credentials_from_files_no_refresh(self):
        """Test when refresh goes wrong."""
        self.mock_creds.valid = False
        self.mock_creds2.valid = True

        self.mock_creds.refresh.side_effect = exceptions.RefreshError

        creds = _auth.get_credentials_from_webserver_auth(
            credentials_file='creds.json')

        self.assertEqual(self.mock_creds2, creds)
        self.mock_creds_class.from_authorized_user_file.assert_called()
        self.mock_creds.refresh.assert_called()
        self.mock_flow_class.from_client_secrets_file.assert_called()
        self.mock_flow.run_local_server.assert_called()


class TestServiceAccountAuth(fake_filesystem_unittest.TestCase):
    """Test the auth module, service accounts."""

    def setUp(self) -> None:
        """Set up the mocks for the Google Auth API and filesystem."""
        super().setUp()

        credentials_patcher = mock.patch(
            'google.oauth2.service_account.Credentials',
            spec=service_account.Credentials)
        self.mock_creds_class: Any = credentials_patcher.start()
        self.addCleanup(credentials_patcher.stop)
        self.mock_creds: Any = mock.Mock(spec=service_account.Credentials)
        self.mock_creds.service_account_email.return_value = '123'
        self.mock_from_file = self.mock_creds_class.from_service_account_file

        self.mock_creds2: Any = mock.Mock(spec=service_account.Credentials)
        self.mock_creds2.service_account_email.return_value = '234'

        self.setUpPyfakefs()

    def test_get_credentials_from_sa_file(self):
        """Test single service account in files."""
        self.mock_creds.valid = True
        from_sa_file = self.mock_creds_class.from_service_account_file
        from_sa_file.return_value = self.mock_creds
        os.mkdir('service_accounts')
        with open('service_accounts/a.json', 'w') as sa_file:
            sa_file.write('content unused')

        creds: Any = _auth.get_credentials_from_service_account()

        self.assertEqual([self.mock_creds], creds)
        self.mock_from_file.assert_called_with('service_accounts/a.json')

    def test_get_credentials_from_sa_file_two_files(self):
        """Test two service accounts in files."""
        self.mock_creds.valid = True
        from_sa_file = self.mock_creds_class.from_service_account_file
        from_sa_file.side_effect = [self.mock_creds, self.mock_creds2]
        os.mkdir('service_accounts')
        with open('service_accounts/a.json', 'w') as sa_file:
            sa_file.write('content unused')
        with open('service_accounts/b.json', 'w') as sa_file:
            sa_file.write('content unused')

        creds: Any = _auth.get_credentials_from_service_account()

        self.assertEqual([self.mock_creds, self.mock_creds2], creds)
        self.mock_from_file.assert_has_calls([
            mock.call('service_accounts/a.json'),
            mock.call('service_accounts/b.json'),
        ])

    def test_get_credentials_from_sa_file_no_file(self):
        """Test service account loading when no file present."""
        self.mock_creds.valid = True
        from_sa_file = self.mock_creds_class.from_service_account_file
        from_sa_file.return_value = self.mock_creds
        os.mkdir('service_accounts')

        creds: Any = _auth.get_credentials_from_service_account()

        self.assertEqual([], creds)
        self.mock_from_file.assert_not_called()

    def test_get_credentials_from_sa_file_no_dir(self):
        """Test when not even the base dir is present.."""
        self.mock_creds.valid = True
        from_sa_file = self.mock_creds_class.from_service_account_file
        from_sa_file.return_value = self.mock_creds

        creds: Any = _auth.get_credentials_from_service_account()

        self.assertEqual([], creds)
        self.mock_from_file.assert_not_called()


class TestCredentialsStore(fake_filesystem_unittest.TestCase):
    """Test the CredentialsStore class."""

    def setUp(self) -> None:
        """Set up the mocks for the Google Auth API and filesystem."""
        super().setUp()

        # server flow mocks
        credentials_patcher = mock.patch(
            'google.oauth2.credentials.Credentials',
            spec=credentials.Credentials)
        self.mock_creds_class: Any = credentials_patcher.start()
        self.addCleanup(credentials_patcher.stop)
        self.mock_creds: Any = mock.Mock(spec=credentials.Credentials)
        self.mock_creds.to_json.return_value = '123'
        self.mock_creds.client_id = 'id1'
        self.mock_creds.valid = True
        from_user_file = self.mock_creds_class.from_authorized_user_file
        from_user_file.return_value = self.mock_creds

        credentials_patcher2 = mock.patch(
            'google.oauth2.service_account.Credentials',
            spec=service_account.Credentials)
        self.mock_creds_class2: Any = credentials_patcher2.start()
        self.addCleanup(credentials_patcher2.stop)
        self.mock_creds2: Any = mock.Mock(spec=service_account.Credentials)
        self.mock_creds2.service_account_email = 'id2'

        self.setUpPyfakefs()

    def test_setup_default_creds(self):
        """Test adding server and service account creds."""
        from_sa_file = self.mock_creds_class2.from_service_account_file
        from_sa_file.return_value = self.mock_creds2
        os.mkdir('service_accounts')
        with open('service_accounts/a.json', 'w') as sa_file:
            sa_file.write('content unused')

        store = _auth.CredentialsStore()
        store.add_available_credentials()

        self.assertEqual(self.mock_creds, store.from_username(''))
        self.assertEqual(self.mock_creds, store.from_username('id1'))
        self.assertEqual(self.mock_creds2, store.from_username('id2'))

    def test_setup_default_no_creds(self):
        """Test no available creds."""
        from_user_file = self.mock_creds_class.from_authorized_user_file
        from_user_file.side_effect = FileNotFoundError()

        store = _auth.CredentialsStore()
        store.add_available_credentials()

        self.assertRaisesRegex(KeyError, '.*', lambda: store.from_username(''))

    def test_add_cred(self):
        """Test adding individual cred."""

        store = _auth.CredentialsStore()
        store.add_credentials(self.mock_creds, 'a', True)

        self.assertEqual(self.mock_creds, store.from_username(''))
        self.assertEqual(self.mock_creds, store.from_username('a'))
