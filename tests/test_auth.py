import json
import os
import unittest

from onedrivesdk.helpers.http_provider_with_proxy import HttpProviderWithProxy

from onedrive_client import get_resource, od_auth, od_api_session


def get_sample_authenticator():
    auth = od_auth.OneDriveAuthenticator()
    session_params = json.loads(get_resource('data/session_response.json', pkg_name='tests'))
    session_params['token_type'] = 'code'
    session_params['client_id'] = auth.APP_CLIENT_ID
    session_params['scope_string'] = session_params['scope']
    session_params['redirect_uri'] = auth.APP_REDIRECT_URL
    session_params['auth_server_url'] = 'https://localhost/auth'
    del session_params['scope']
    auth.client.auth_provider._session = od_api_session.OneDriveAPISession(**session_params)
    auth.refresh_session = lambda x: None
    return auth


class TestOneDriveAuthenticator(unittest.TestCase):

    def test_get_auth_url(self):
        authenticator = od_auth.OneDriveAuthenticator()
        self.assertIsInstance(authenticator.get_auth_url(), str)

    def test_get_proxies(self):
        expected = 'http://foo/bar'
        for k in ('http_proxy', 'HTTP_PROXY', 'https_proxy', 'HTTPS_PROXY'):
            os.environ[k] = expected
            authenticator = od_auth.OneDriveAuthenticator()
            self.assertIsInstance(
                authenticator.client.http_provider, HttpProviderWithProxy)
            key = k.split('_')[0].lower()
            self.assertEqual(
                authenticator.client.http_provider.proxies[key], expected)
            del os.environ[k]


if __name__ == '__main__':
    unittest.main()
