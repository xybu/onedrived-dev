import logging
import os

import onedrivesdk.error

import base
from onedrived import fix_owner_and_timestamp
from onedrived.od_api_helper import get_item_modified_datetime
from onedrived.od_api_helper import item_request_call
from onedrived.od_dateutils import datetime_to_timestamp
from onedrived.od_hashutils import sha1_value


class DownloadFileTask(base.TaskBase):

    def __init__(self, repo, task_pool, remote_item, parent_relpath):
        """
        :param onedrived.od_repo.OneDriveLocalRepository repo:
        :param onedrived.od_task.TaskPool task_pool:
        :param onedrivesdk.model.item.Item remote_item:
        :param str parent_relpath:
        """
        super().__init__(repo, task_pool)
        self.remote_item = remote_item
        self.parent_relpath = parent_relpath
        self.local_abspath = repo.local_root + parent_relpath + '/' + remote_item.name

    def __repr__(self):
        return type(self).__name__ + '(%s)' % self.local_abspath

    def handle(self):
        logging.info('Downloading file "%s" to "%s".', self.remote_item.id, self.local_abspath)
        try:
            tmp_name = self.repo.path_filter.get_temp_name(self.remote_item.name)
            tmp_path = self.repo.local_root + self.parent_relpath + '/' + tmp_name
            item_request = self.repo.authenticator.client.item(drive=self.repo.drive.id, id=self.remote_item.id)
            item_mtime, item_mtime_editable = get_item_modified_datetime(self.remote_item)
            item_request_call(self.repo, item_request.download, tmp_path)
            hashes = self.remote_item.file.hashes
            if hashes is None or hashes.sha1_hash is None or hashes.sha1_hash == sha1_value(tmp_path):
                item_size_local = os.path.getsize(tmp_path)
                os.rename(tmp_path, self.local_abspath)
                fix_owner_and_timestamp(self.local_abspath, self.repo.context.user_uid,
                                        datetime_to_timestamp(item_mtime))
                self.repo.update_item(self.remote_item, self.parent_relpath, item_size_local)
                logging.info('Finished downloading item "%s".', self.remote_item.id)
                return True
            else:
                # We assumed server's SHA-1 value is always correct -- might not be true.
                logging.error('Hash mismatch for downloaded file "%s".', self.local_abspath)
                os.remove(tmp_path)
        except (onedrivesdk.error.OneDriveError, OSError) as e:
            logging.error('Error when downloading file "%s": %s.', self.remote_item.id, e)
        return False
