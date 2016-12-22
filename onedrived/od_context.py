import json
import logging
import os
from pwd import getpwnam

import xdg

from . import mkdir
from .models import account_profile
from .models import drive_config


def is_invalid_username(s):
    return s is None or not isinstance(s, str) or len(s.strip()) == 0


def get_login_username():
    # TODO: Allow for sudoing or not? If so, prepend SUDO_USER.
    for key in ('LOGNAME', 'USER', 'LNAME', 'USERNAME'):
        s = os.getenv(key)
        if not is_invalid_username(s):
            return s
    raise ValueError('Cannot find login name of current user.')


class UserContext:
    """Stores config params for a single local user."""

    DEFAULT_CONFIG = {
        'proxies': {}, # Proxy is of format {'http': url1, 'https': url2}.
        'accounts': {},
        'drives': {}
    }

    DEFAULT_CONFIG_FILENAME = 'onedrived_config_v2.json'

    SUPPORTED_PROXY_PROTOCOLS = ('http', 'https')

    def __init__(self):
        logging.basicConfig(format='[%(asctime)-15s] %(levelname)s: %(threadName)s: %(message)s')
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        self.host_name = os.uname()[1]
        self.user_name = get_login_username()
        self.user_uid = getpwnam(self.user_name).pw_uid
        self.user_home = os.path.expanduser('~' + self.user_name)
        if os.path.isdir(xdg.XDG_CONFIG_HOME):
            self.config_dir = xdg.XDG_CONFIG_HOME + '/onedrived'
        else:
            self.config_dir = self.user_home + '/.onedrived'
        self._create_config_dir_if_missing()
        self.config = self.DEFAULT_CONFIG

    def _create_config_dir_if_missing(self):
        if not os.path.exists(self.config_dir):
            self.logger.info('Config dir "' + self.config_dir + '" does not exist. Create it.')
            mkdir(self.config_dir, self.user_uid, mode=0o700, exist_ok=True)
        elif not os.path.isdir(self.config_dir):
            self.logger.info('Config dir "' + self.config_dir + '" is not a directory. Delete and re-create it.')
            os.remove(self.config_dir)
            mkdir(self.config_dir, self.user_uid, mode=0o700, exist_ok=True)

    def add_account(self, account_profile):
        """
        Add a new account to config file.
        :param models.account_profile.OneDriveAccountProfile account_profile:
        """
        self.config['accounts'][account_profile.account_id] = account_profile.data

    def get_account(self, account_id):
        """
        Return profile of a saved account.
        :param str account_id: ID of the account to query.
        :return models.account_profile.OneDriveAccountProfile: An OneDriveAccountProfile object of the account profile.
        """
        return account_profile.OneDriveAccountProfile(self.config['accounts'][account_id])

    def delete_account(self, account_id):
        """
        Delete a saved account from config.
        :param str account_id: ID of the account to delete.
        """
        del self.config['accounts'][account_id]

    def all_accounts(self):
        """Return a list of all linked account IDs."""
        return sorted(self.config['accounts'].keys())

    def add_drive(self, drive_config):
        """
        Add a new drive to local config.
        :param models.drive_config.LocalDriveConfig drive_config:
        """
        self.config['drives'][drive_config.drive_id] = drive_config.data

    def get_drive(self, drive_id):
        """
        :param str drive_id:
        :return models.drive_config.LocalDriveConfig:
        """
        return drive_config.LocalDriveConfig(drive_id, **self.config['drives'][drive_id])

    def delete_drive(self, drive_id):
        del self.config['drives'][drive_id]

    def all_drives(self):
        return sorted(self.config['drives'].keys())

    def load_config(self, filename):
        with open(self.config_dir + '/' + filename, 'r') as f:
            config = json.load(f)
        for k, v in config.items():
            self.config[k] = v

    def save_config(self, filename):
        with open(self.config_dir + '/' + filename, 'w') as f:
            json.dump(self.config, f, sort_keys=True, indent=4, separators=(',', ': '))
