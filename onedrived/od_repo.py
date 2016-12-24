"""
od_repo.py
Core component for local file management and tracking.
:copyright: (c) Xiangyu Bu <xybu92@live.com>
:license: MIT
"""

import atexit
import logging
import sqlite3

from . import get_resource as _get_resource
from .models.path_filter import PathFilter as _PathFilter


class OneDriveLocalRepository:

    def __init__(self, context, authenticator, drive, drive_config):
        """
        :param od_context.UserContext context:
        :param od_auth.OneDriveAuthenticator authenticator:
        :param onedrivesdk.model.drive.Drive drive:
        :param models.drive_config.LocalDriveConfig drive_config:
        """
        self.context = context
        self.authenticator = authenticator
        self.drive = drive
        self.account_id = drive_config.account_id
        self.local_root = drive_config.localroot_path
        self._init_path_filter(ignore_file=drive_config.ignorefile_path)
        self._init_item_store()

    @property
    def _item_store_path(self):
        return self.context.config_dir + '/items_' + self.drive.id + '.sqlite3'

    def _init_path_filter(self, ignore_file):
        try:
            with open(ignore_file, 'r') as f:
                rules = set(f.read().splitlines(keepends=False))
        except OSError as e:
            logging.error('Failed to load ignore list file "%s": %s', ignore_file, e)
            rules = set()
        self.path_filter = _PathFilter(rules)

    def _init_item_store(self):
        self._conn = sqlite3.connect(self._item_store_path, isolation_level=None, check_same_thread=False)
        self._cursor = self._conn.cursor()
        self._cursor.execute(_get_resource('data/items_db.sql', pkg_name='onedrived'))
        self._conn.commit()
        atexit.register(self.close)

    def close(self):
        self._cursor.close()
        self._conn.close()
