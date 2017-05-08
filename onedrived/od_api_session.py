import base64
import pickle
import zlib
from time import time

import keyring
import onedrivesdk.session


def get_keyring_key(account_id):
    return OneDriveAPISession.KEYRING_ACCOUNT_KEY_PREFIX + account_id


class OneDriveAPISession(onedrivesdk.session.Session):

    SESSION_ARG_KEYNAME = 'key'
    KEYRING_SERVICE_NAME = 'onedrived_v2'
    KEYRING_ACCOUNT_KEY_PREFIX = 'user.'
    PICKLE_PROTOCOL = 3

    @property
    def expires_in_sec(self):
        return self._expires_at - time()

    def save_session(self, **save_session_kwargs):
        print('OneDriveAPISession.save_session')
        if self.SESSION_ARG_KEYNAME not in save_session_kwargs:
            raise ValueError('"%s" must be specified in save_session() argument.' % self.SESSION_ARG_KEYNAME)
        data = base64.b64encode(zlib.compress(pickle.dumps(self, self.PICKLE_PROTOCOL))).decode('utf-8')
        keyring.set_password(self.KEYRING_SERVICE_NAME, save_session_kwargs[self.SESSION_ARG_KEYNAME], data)

    @staticmethod
    def load_session(**load_session_kwargs):
        """
        :param dict[str, str] load_session_kwargs:
        :return onedrived.od_api_session.OneDriveAPISession:
        """
        keyarg = OneDriveAPISession.SESSION_ARG_KEYNAME
        if keyarg not in load_session_kwargs:
            raise ValueError('"%s" must be specified in load_session() argument.' % keyarg)
        saved_data = keyring.get_password(OneDriveAPISession.KEYRING_SERVICE_NAME, load_session_kwargs[keyarg])
        print('saved_data: ' + str(saved_data))
        
        if saved_data is None:
            raise ValueError("Don't find anything")
        
        data = zlib.decompress(base64.b64decode(saved_data.encode('utf-8')))
        return pickle.loads(data)
