import unittest

import keyring

from onedrive_client import od_api_session, od_auth


class OneDriveAPISession(unittest.TestCase):

    def setUp(self):
        self.session = od_api_session.OneDriveAPISession(
            token_type='code', expires_in=100, scope_string=' '.join(od_auth.OneDriveAuthenticator.APP_SCOPES),
            access_token='abc', client_id='client_id', auth_server_url='https://foo/bar', redirect_uri='https://baz',
            refresh_token='hehe', client_secret='no_secret')

    def test_expires_in(self):
        self.assertLess(self.session.expires_in_sec, 100)

    def test_save_and_load(self):
        keydict = {self.session.SESSION_ARG_KEYNAME: 'mock_key'}
        self.session.save_session(**keydict)
        session = od_api_session.OneDriveAPISession.load_session(**keydict)
        self.assertEqual(self.session.token_type, session.token_type)
        self.assertEqual(self.session.scope, session.scope)
        self.assertEqual(self.session.access_token, session.access_token)
        self.assertEqual(self.session.client_id, session.client_id)
        self.assertEqual(self.session.client_secret, session.client_secret)
        self.assertEqual(self.session.refresh_token, session.refresh_token)
        keyring.delete_password(od_api_session.OneDriveAPISession.KEYRING_SERVICE_NAME, 'mock_key')
