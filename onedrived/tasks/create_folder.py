import logging
import os

import onedrivesdk.error
from onedrivesdk import Item, Folder

from . import merge_dir
from .base import TaskBase as _TaskBase
from ..od_api_helper import item_request_call


class CreateFolderTask(_TaskBase):

    def __init__(self, repo, task_pool, item_name, parent_relpath, upload_if_success=True, abort_if_local_gone=True):
        """
        :param onedrived.od_repo.OneDriveLocalRepository repo:
        :param onedrived.od_task.TaskPool task_pool:
        :param str item_name:
        :param str parent_relpath:
        :param True | False upload_if_success:
        :param True | False abort_if_local_gone:
        """
        super().__init__(repo, task_pool)
        self.item_name = item_name
        self.parent_relpath = parent_relpath
        self.local_abspath = repo.local_root + parent_relpath + '/' + item_name
        self.upload_if_success = upload_if_success
        self.abort_if_local_gone = abort_if_local_gone

    def __repr__(self):
        return type(self).__name__ + '(%s, upload=%s)' % (self.local_abspath, self.upload_if_success)

    @staticmethod
    def _get_folder_pseudo_item(item_name):
        item = Item()
        item.name = item_name
        item.folder = Folder()
        return item

    def _get_item_request(self):
        if self.parent_relpath == '':
            return self.repo.authenticator.client.item(drive=self.repo.drive.id, id='root')
        else:
            return self.repo.authenticator.client.item(drive=self.repo.drive.id, path=self.parent_relpath)

    def handle(self):
        logging.info('Creating remote item for local dir "%s".', self.local_abspath)
        try:
            if self.abort_if_local_gone and not os.path.isdir(self.local_abspath):
                logging.warning('Local dir "%s" is gone. Skip creating remote item for it.', self.local_abspath)
                return
            item = self._get_folder_pseudo_item(self.item_name)
            item_request = self._get_item_request()
            item = item_request_call(self.repo, item_request.children.add, item)
            self.repo.update_item(item, self.parent_relpath, 0)
            logging.info('Created remote item for local dir "%s".', self.local_abspath)
            if self.upload_if_success:
                logging.info('Adding task to merge "%s" after remote item was created.', self.local_abspath)
                self.task_pool.add_task(merge_dir.MergeDirectoryTask(
                    self.repo, self.task_pool, self.parent_relpath + '/' + self.item_name,
                    self.repo.authenticator.client.item(drive=self.repo.drive.id, id=item.id)))
            return True
        except (onedrivesdk.error.OneDriveError, OSError) as e:
            logging.error('Error when creating remote dir of "%s": %s.', self.local_abspath, e)
            return False
