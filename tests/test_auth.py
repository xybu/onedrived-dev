import json
import unittest

from onedrived import get_resource, od_auth, od_api_session


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

    def setUp(self):
        self.authenticator = od_auth.OneDriveAuthenticator()

    def test_instantiate_w_proxy(self):
        od_auth.OneDriveAuthenticator(proxies={'https': 'https://127.0.0.1'})

    def test_get_auth_url(self):
        self.assertIsInstance(self.authenticator.get_auth_url(), str)


if __name__ == '__main__':
    unittest.main()
