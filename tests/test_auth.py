import unittest

from onedrived import od_auth


class TestOneDriveAuthenticator(unittest.TestCase):

    def setUp(self):
        self.authenticator = od_auth.OneDriveAuthenticator()

    def test_instantiate_w_proxy(self):
        od_auth.OneDriveAuthenticator(proxies={'https': 'https://127.0.0.1'})

    def test_get_auth_url(self):
        self.assertIsInstance(self.authenticator.get_auth_url(), str)


if __name__ == '__main__':
    unittest.main()
