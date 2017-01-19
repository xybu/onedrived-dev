import os
import keyring.backend


class MockKeyring(keyring.backend.KeyringBackend):

    priority = 1

    def __init__(self):
        super().__init__()
        self.passwords = dict()

    def set_password(self, service, username, password):
        self.passwords[service + '.' + username] = password

    def get_password(self, service, username):
        return self.passwords[service + '.' + username]

    def delete_password(self, service, username):
        del self.passwords[service + '.' + username]


if os.getenv('MOCK_KEYRING') is not None:
    keyring.set_keyring(MockKeyring())
