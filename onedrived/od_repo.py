"""
od_repo.py
Core component for local file management and tracking.
:copyright: (c) Xiangyu Bu <xybu92@live.com>
:license: MIT
"""

import atexit
import logging
import sqlite3
import threading

from . import get_resource as _get_resource
from .od_dateutils import str_to_datetime, datetime_to_str
from .models.path_filter import PathFilter as _PathFilter


class ItemRecord:

    def __init__(self, row):
        self.item_id, self.type, self.item_name, self.parent_id, self.parent_path, self.e_tag, self.c_tag, self.size, \
        self.created_time, self.modified_time, self.status, self.crc32_hash, self.sha1_hash = row
        self.created_time = str_to_datetime(self.created_time)
        self.modified_time = str_to_datetime(self.modified_time)


class ItemRecordType:

    FILE = 'file'
    FOLDER = 'folder'


class ItemRecordStatus:

    OK = 'ok'
    MOVE_FROM = 'MOVE_FROM'


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
        self._lock = threading.Lock()
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

    def get_item_by_path(self, item_name, parent_path):
        """
        Fetch a record form database. Return None if not found.
        :param str item_name:
        :param str parent_path:
        :return ItemRecord | None:
        """
        with self._lock:
            q = self._conn.execute('SELECT item_id, type, item_name, parent_id, parent_path, etag, ctag, size, '
                                   'created_time, modified_time, status, crc32_hash, sha1_hash FROM items WHERE ' +
                                   'item_name=? AND parent_path=? LIMIT 1', (item_name, parent_path))
            rec = q.fetchone()
            return ItemRecord(rec) if rec else rec

    def update_item(self, item, parent_relpath, status=ItemRecordStatus.OK):
        """
        :param onedrivesdk.model.item.Item remote_item:
        :param str parent_relpath:
        :param str status:
        """
        crc32_hash = None
        sha1_hash = None
        file_facet = item.file
        if file_facet:
            item_type = ItemRecordType.FILE
            hash_facet = file_facet.hashes
            if hash_facet:
                crc32_hash = hash_facet.crc32_hash
                sha1_hash = hash_facet.sha1_hash
        elif item.folder:
            item_type = ItemRecordType.FOLDER
        else:
            raise ValueError('Unknown type of item "%s (%s)".' % (item.name, item.id))
        parent_reference = item.parent_reference
        created_time_str = datetime_to_str(item.created_date_time)
        modified_time_str = datetime_to_str(item.last_modified_date_time)
        with self._lock:
            self._cursor.execute(
                'INSERT OR REPLACE INTO items (item_id, type, item_name, parent_id, parent_path, etag, '
                'ctag, size, created_time, modified_time, status, crc32_hash, sha1_hash)'
                ' VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (item.id, item_type, item.name, parent_reference.id, parent_relpath, item.e_tag, item.c_tag,
                item.size, created_time_str, modified_time_str, status, crc32_hash, sha1_hash))
            self._conn.commit()
