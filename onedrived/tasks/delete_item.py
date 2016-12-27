import logging

import onedrivesdk.error

from .base import TaskBase as _TaskBase


class DeleteRemoteItemTask(_TaskBase):

    def __init__(self, repo, task_pool, parent_relpath, item_name, item_id=None, is_folder=False):
        """
        :param onedrived.od_repo.OneDriveLocalRepository repo:
        :param onedrived.od_task.TaskPool task_pool:
        :param str parent_relpath:
        :param str item_name:
        :param str | None item_id:
        :param True | False is_folder:
        """
        super().__init__(repo, task_pool)
        self.parent_relpath = parent_relpath
        self.item_name = item_name
        self.rel_path = parent_relpath + '/' + item_name
        self.item_id = item_id
        self.is_folder = is_folder
        self.local_abspath = repo.local_root + self.rel_path

    def __repr__(self):
        return type(self).__name__ + '(%s, is_folder=%s)' % (self.local_abspath, self.is_folder)

    def handle(self):
        logging.info('Deleting remote item "%s".', self.rel_path)
        try:
            if self.item_id is not None:
                item_request = self.repo.authenticator.client.item(drive=self.repo.drive.id, id=self.item_id)
            else:
                item_request = self.repo.authenticator.client.item(drive=self.repo.drive.id, path=self.rel_path)
            try:
                item_request.delete()
            except onedrivesdk.error.OneDriveError as e:
                logging.error('API Error occurred when deleting "%s": %s.', self.rel_path, e)
                self.repo.authenticator.refresh_session(self.repo.account_id)
                item_request.delete()
            self.repo.delete_item(self.parent_relpath, self.item_name, self.is_folder)
            logging.info('Deleted remote item "%s".', self.rel_path)
        except (onedrivesdk.error.OneDriveError, OSError) as e:
            logging.error('Error deleting item "%s": %s.', self.rel_path, e)
