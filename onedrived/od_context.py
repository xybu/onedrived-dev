import json
import logging
import logging.handlers
import os
from pwd import getpwnam

import xdg

from . import mkdir, get_resource, od_webhooks
from .od_models import account_profile as _account_profile
from .od_models import drive_config as _drive_config


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
        logging.warning('Failed to load config file: %s. Use default.', e)
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
        'scan_interval_sec': 21600,  # Poll every 6 hours.
        'webhook_type': od_webhooks.DEFAULT_WEBHOOK_TYPE,
        'webhook_host': '',
        'webhook_port': 0,
        'webhook_renew_interval_sec': 7200,  # Renew webhook every 2 hours.
        'num_workers': 2,
        'start_delay_sec': 0,
        KEY_LOGFILE_PATH: '',
    }

    DEFAULT_CONFIG_FILENAME = 'onedrived_config_v2.json'
    DEFAULT_IGNORE_FILENAME = 'ignore_v2.txt'
    DEFAULT_NGROK_CONF_FILENAME = 'ngrok_conf.yaml'

    CONFIGURABLE_INT_KEYS = {
        'scan_interval_sec': 'Interval, in seconds, between two actions of scanning the entire repository.',
        'num_workers': 'Total number of worker threads.',
        'webhook_renew_interval_sec': 'Renew webhook after this amount of time, in seconds. Ideal value should be '
                                      'slightly larger than the lifespan of onedrived process.',
        'webhook_port': 'Port number for webhook. Default: 0 (let OS allocate a free port).',
        'start_delay_sec': 'Amount of time, in seconds, to sleep before main starts working.'
    }

    CONFIGURABLE_STR_KEYS = {
        KEY_LOGFILE_PATH: 'Path to log file. Empty string means writing to stdout.',
        'webhook_host': 'Host to receive webhook notifications. Requests to https://host:port much reach localhost.'
                        'Use empty string "" to mean localhost.',
        'webhook_type': 'Type of webhook. Use "direct" only if your machine can be reached from public network.'
    }

    ACCEPTED_VALUES = {
        'webhook_type': od_webhooks.SUPPORTED_WEBHOOK_TYPES
    }

    SUPPORTED_PROXY_PROTOCOLS = ('http', 'https')

    def __init__(self, loop):
        """
        :param asyncio.AbstractEventLoop | None loop:
        """
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
        self._watcher = None

    def _create_config_dir_if_missing(self):
        if os.path.exists(self.config_dir) and not os.path.isdir(self.config_dir):
            logging.info('Config dir "' + self.config_dir + '" is not a directory. Delete it.')
            os.remove(self.config_dir)
        if not os.path.exists(self.config_dir):
            logging.info('Config dir "' + self.config_dir + '" does not exist. Create it.')
            mkdir(self.config_dir, self.user_uid, mode=0o700, exist_ok=True)
            with open(self.config_dir + '/' + self.DEFAULT_IGNORE_FILENAME, 'w') as f:
                f.write(get_resource('data/ignore_v2.txt'))
            with open(self.config_dir + '/' + self.DEFAULT_NGROK_CONF_FILENAME, 'w') as f:
                f.write(get_resource('data/ngrok_default_conf.yaml'))

    @property
    def loop(self):
        """
        :return asyncio.SelectorEventLoop | None:
        """
        return self._loop

    # noinspection PyAttributeOutsideInit
    @loop.setter
    def loop(self, v):
        self._loop = v

    @property
    def watcher(self):
        """
        :return onedrived.od_watcher.LocalRepositoryWatcher:
        """
        return self._watcher

    @watcher.setter
    def watcher(self, watcher):
        self._watcher = watcher

    @staticmethod
    def set_logger(min_level=logging.WARNING, path=None):
        logging_config = {'level': min_level, 'format': '[%(asctime)-15s] %(levelname)s: %(threadName)s: %(message)s'}
        if path:
            logging_config['filename'] = path
        logging.basicConfig(**logging_config)

    def _add_and_return(self, config_key, id_key, obj, data):
        self.config[config_key][getattr(obj, id_key)] = data
        return obj

    def add_account(self, account_profile):
        """
        Add a new account to config file.
        :param od_models.account_profile.OneDriveAccountProfile account_profile:
        :return od_models.account_profile.OneDriveAccountProfile: The account profile argument.
        """
        return self._add_and_return('accounts', 'account_id', account_profile, account_profile.data)

    def get_account(self, account_id):
        """
        Return profile of a saved account.
        :param str account_id: ID of the account to query.
        :return od_models.account_profile.OneDriveAccountProfile:
            An OneDriveAccountProfile object of the account profile.
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
        :param od_models.drive_config.LocalDriveConfig drive_config:
        :return od_models.drive_config.LocalDriveConfig drive_config:
        """
        return self._add_and_return('drives', 'drive_id', drive_config, drive_config._asdict())

    def get_drive(self, drive_id):
        """
        :param str drive_id:
        :return od_models.drive_config.LocalDriveConfig:
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
