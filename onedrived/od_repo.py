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
from datetime import datetime
from contextlib import closing

from . import get_resource as _get_resource
from .od_models.path_filter import PathFilter as _PathFilter
from .od_api_helper import get_item_modified_datetime, get_item_created_datetime
from .od_dateutils import str_to_datetime, datetime_to_str


class ItemRecord:
    def __init__(self, row):
        self.item_id, self.type, self.item_name, self.parent_id, self.parent_path, self.e_tag, self.c_tag, \
            self.size, self.size_local, self.created_time, self.modified_time, self.status, self.sha1_hash, \
            self.record_time_str = row
        self.created_time = str_to_datetime(self.created_time)
        self.modified_time = str_to_datetime(self.modified_time)


class ItemRecordType:
    FOLDER = 0
    FILE = 1


class ItemRecordStatus:
    OK = 0


class RepositoryType:
    PERSONAL = 0
    BUSINESS = 1


def get_drive_db_path(config_dir, drive_id):
    return config_dir +  '/items_' + drive_id + '.sqlite3'


class OneDriveLocalRepository:
    SESSION_EXPIRE_THRESHOLD_SEC = 120

    def __init__(self, context, authenticator, drive, drive_config):
        """
        :param onedrived.od_context.UserContext context:
        :param onedrived.od_auth.OneDriveAuthenticator authenticator:
        :param onedrivesdk.model.drive.Drive drive:
        :param onedrived.od_models.drive_config.LocalDriveConfig drive_config:
        """
        self.context = context
        self.authenticator = authenticator
        self.drive = drive
        self.account_id = drive_config.account_id
        self.local_root = drive_config.localroot_path
        self.type = RepositoryType.BUSINESS if drive.drive_type == 'business' else RepositoryType.PERSONAL
        self._lock = threading.Lock()
        self._init_path_filter(ignore_file=drive_config.ignorefile_path)
        self._init_item_store()
        self.refresh_session()

    @property
    def _item_store_path(self):
        return get_drive_db_path(self.context.config_dir, self.drive.id)

    def _init_path_filter(self, ignore_file):
        try:
            with open(ignore_file, 'r') as f:
                rules = set(f.read().splitlines(keepends=False))
        except OSError as e:
            logging.error('Failed to load ignore list file "%s": %s', ignore_file, e)
            rules = set()
        self.path_filter = _PathFilter(rules)

    def _init_item_store(self):
        self._conn = sqlite3.connect(self._item_store_path, check_same_thread=False)
        self._conn.execute(_get_resource('data/items_db.sql', pkg_name='onedrived'))
        atexit.register(self.close)

    def refresh_session(self):
        logging.debug('Refreshing repository session.')
        self.authenticator.refresh_session(self.account_id)
        logging.info('Session for account %s will expire in %d seconds.',
                     self.account_id, self.authenticator.session_expires_in_sec)
        if self.context.loop:
            t = self.authenticator.session_expires_in_sec - self.SESSION_EXPIRE_THRESHOLD_SEC
            logging.debug('Will refresh session in %d seconds.', t)
            self.context.loop.call_later(t, self.refresh_session)

    def close(self):
        logging.debug('Closing database "%s".', self._item_store_path)
        self._conn.close()

    def get_item_by_path(self, item_name, parent_relpath):
        """
        Fetch a record form database. Return None if not found.
        :param str item_name:
        :param str parent_relpath:
        :return ItemRecord | None:
        """
        with self._lock:
            q = self._conn.execute('SELECT id, type, name, parent_id, parent_path, etag, ctag, size, size_local, '
                                   'created_time, modified_time, status, sha1_hash, record_time FROM items '
                                   'WHERE name=? AND parent_path=? LIMIT 1', (item_name, parent_relpath))
            rec = q.fetchone()
            return ItemRecord(rec) if rec else None

    def get_immediate_children_of_dir(self, relpath):
        """
        :param str relpath:
        :return dict(str, ItemRecord):
        """
        with self._lock:
            q = self._conn.execute('SELECT id, type, name, parent_id, parent_path, etag, ctag, size, size_local, '
                                   'created_time, modified_time, status, sha1_hash, record_time FROM items '
                                   'WHERE parent_path=?', (relpath,))
            return {rec[2]: ItemRecord(rec) for rec in q.fetchall() if rec}

    def delete_item(self, item_name, parent_relpath, is_folder=False):
        """
        Delete the specified item from database. If it is a directory, then also delete all its children items.
        :param str item_name: Name of the item.
        :param str parent_relpath: Relative path of its parent item.
        :param True | False is_folder: True to indicate that the item is a folder (delete all children).
        """
        with self._lock, self._conn, closing(self._conn.cursor()) as cursor:
            if is_folder:
                item_relpath = parent_relpath + '/' + item_name
                cursor.execute('DELETE FROM items WHERE parent_path=? OR parent_path LIKE ?',
                               (item_relpath, item_relpath + '/%'))
            cursor.execute('DELETE FROM items WHERE parent_path=? AND name=?', (parent_relpath, item_name))

    def move_item(self, item_name, parent_relpath, new_name, new_parent_relpath, is_folder=False):
        """
        :param str item_name: Name of the item.
        :param str parent_relpath: Relative path of its parent item.
        :param str new_name: Name of the item.
        :param str new_parent_relpath: Relative path of its parent item.
        :param True | False is_folder: True to indicate that the item is a folder (delete all children).
        """
        with self._lock, self._conn, closing(self._conn.cursor()) as cursor:
            if is_folder:
                item_relpath = parent_relpath + '/' + item_name
                cursor.execute('UPDATE items SET parent_path=? || substr(parent_path, ?) '
                               'WHERE parent_path=? OR parent_path LIKE ?',
                               (new_parent_relpath + '/' + new_name, len(item_relpath) + 1,
                                item_relpath, item_relpath + '/%'))
            cursor.execute('UPDATE items SET parent_path=?, name=? WHERE parent_path=? AND name=?',
                           (new_parent_relpath, new_name, parent_relpath, item_name))

    def update_item(self, item, parent_relpath, size_local=0, status=ItemRecordStatus.OK):
        """
        :param onedrivesdk.model.item.Item item:
        :param str parent_relpath:
        :param int size_local:
        :param int status:
        """
        sha1_hash = None
        file_facet = item.file
        if file_facet:
            item_type = ItemRecordType.FILE
            hash_facet = file_facet.hashes
            if hash_facet:
                sha1_hash = hash_facet.sha1_hash
        elif item.folder:
            item_type = ItemRecordType.FOLDER
        else:
            raise ValueError('Unknown type of item "%s (%s)".' % (item.name, item.id))
        parent_reference = item.parent_reference
        modified_time, _ = get_item_modified_datetime(item)
        modified_time_str = datetime_to_str(modified_time)
        created_time_str = datetime_to_str(get_item_created_datetime(item))
        with self._lock, self._conn:
            self._conn.execute(
                'INSERT OR REPLACE INTO items (id, type, name, parent_id, parent_path, etag, '
                'ctag, size, size_local, created_time, modified_time, status, sha1_hash, record_time)'
                ' VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (item.id, item_type, item.name, parent_reference.id, parent_relpath, item.e_tag, item.c_tag,
                 item.size, size_local, created_time_str, modified_time_str, status, sha1_hash,
                 str(datetime.utcnow().isoformat()) + 'Z'))
