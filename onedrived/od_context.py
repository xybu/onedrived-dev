import json
import logging
import logging.handlers
import os
from pwd import getpwnam

import xdg

from . import mkdir, get_resource
from .models import account_profile as _account_profile
from .models import drive_config as _drive_config


def is_invalid_username(s):
    return s is None or not isinstance(s, str) or len(s.strip()) == 0


def get_login_username():
    # If allow for sudo, prepend SUDO_USER.
    for key in ('LOGNAME', 'USER', 'LNAME', 'USERNAME'):
        s = os.getenv(key)
        if not is_invalid_username(s):
            return s
    raise ValueError('Cannot find login name of current user.')


def load_context(loop=None):
    ctx = UserContext(loop=loop)
    try:
        ctx.load_config(ctx.DEFAULT_CONFIG_FILENAME)
    except OSError as e:
        logging.error('Failed to load config file: %s. Use default.', e)
    return ctx


def save_context(ctx):
    try:
        ctx.save_config(ctx.DEFAULT_CONFIG_FILENAME)
    except OSError as e:
        logging.error('Failed to save config file: %s. Changes were discarded.', e)


class UserContext:
    """Stores config params for a single local user."""

    KEY_LOGFILE_PATH = 'logfile_path'

    DEFAULT_CONFIG = {
        'proxies': {},  # Proxy is of format {'http': url1, 'https': url2}.
        'accounts': {},
        'drives': {},
        'scan_interval_sec': 1800,
        'num_workers': 2,
        KEY_LOGFILE_PATH: '',
    }

    DEFAULT_CONFIG_FILENAME = 'onedrived_config_v2.json'
    DEFAULT_IGNORE_FILENAME = 'ignore_v2.txt'

    CONFIGURABLE_INT_KEYS = {
        'scan_interval_sec': 'Interval, in sec, between two actions of scanning the entire repository.',
        'num_workers': 'Total number of worker threads.'
    }

    CONFIGURABLE_STR_KEYS = {
        KEY_LOGFILE_PATH: 'Path to log file. Empty string means writing to stdout.'
    }

    SUPPORTED_PROXY_PROTOCOLS = ('http', 'https')

    def __init__(self, loop):
        # Information about host and user.
        self.host_name = os.uname()[1]
        self.user_name = get_login_username()
        self.user_uid = getpwnam(self.user_name).pw_uid
        self.user_home = os.path.expanduser('~' + self.user_name)
        # Configuration of onedrived program.
        if os.path.isdir(xdg.XDG_CONFIG_HOME):
            self.config_dir = xdg.XDG_CONFIG_HOME + '/onedrived'
        else:
            self.config_dir = self.user_home + '/.onedrived'
        self._create_config_dir_if_missing()
        self.config = self.DEFAULT_CONFIG
        self.loop = loop

    def _create_config_dir_if_missing(self):
        if os.path.exists(self.config_dir) and not os.path.isdir(self.config_dir):
            logging.info('Config dir "' + self.config_dir + '" is not a directory. Delete it.')
            os.remove(self.config_dir)
        if not os.path.exists(self.config_dir):
            logging.info('Config dir "' + self.config_dir + '" does not exist. Create it.')
            mkdir(self.config_dir, self.user_uid, mode=0o700, exist_ok=True)
            with open(self.config_dir + '/' + self.DEFAULT_IGNORE_FILENAME, 'w') as f:
                f.write(get_resource('data/ignore_v2.txt'))

    @property
    def loop(self):
        return self._loop

    @loop.setter
    def loop(self, v):
        self._loop = v

    @staticmethod
    def set_logger(min_level=logging.WARNING, path=None):
        logging_config = {'level': min_level, 'format': '[%(asctime)-15s] %(levelname)s: %(threadName)s: %(message)s'}
        if path:
            logging_config['filename'] = path
        logging.basicConfig(**logging_config)

    def _add_and_return(self, config_key, id_key, obj):
        self.config[config_key][getattr(obj, id_key)] = obj.data
        return obj

    def add_account(self, account_profile):
        """
        Add a new account to config file.
        :param models.account_profile.OneDriveAccountProfile account_profile:
        :return models.account_profile.OneDriveAccountProfile: The account profile argument.
        """
        return self._add_and_return('accounts', 'account_id', account_profile)

    def get_account(self, account_id):
        """
        Return profile of a saved account.
        :param str account_id: ID of the account to query.
        :return models.account_profile.OneDriveAccountProfile: An OneDriveAccountProfile object of the account profile.
        """
        return _account_profile.OneDriveAccountProfile(self.config['accounts'][account_id])

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
        :return models.drive_config.LocalDriveConfig drive_config:
        """
        return self._add_and_return('drives', 'drive_id', drive_config)

    def get_drive(self, drive_id):
        """
        :param str drive_id:
        :return models.drive_config.LocalDriveConfig:
        """
        return _drive_config.LocalDriveConfig(**self.config['drives'][drive_id])

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
