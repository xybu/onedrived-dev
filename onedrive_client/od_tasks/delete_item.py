import logging

import onedrivesdk.error

from onedrive_client.od_tasks import update_item_base
from onedrive_client import od_api_helper


class DeleteRemoteItemTask(update_item_base.UpdateItemTaskBase):

    def __init__(self, repo, task_pool, parent_relpath, item_name, item_id=None, is_folder=False):
        """
        :param onedrive_client.od_repo.OneDriveLocalRepository repo:
        :param onedrive_client.od_task.TaskPool task_pool:
        :param str parent_relpath:
        :param str item_name:
        :param str | None item_id:
        :param True | False is_folder:
        """
        super().__init__(repo=repo, task_pool=task_pool, parent_relpath=parent_relpath,
                         item_name=item_name, item_id=item_id, is_folder=is_folder)

    def __repr__(self):
        return type(self).__name__ + '(%s, is_folder=%s)' % (self.local_abspath, self.is_folder)

    def handle(self):
        logging.info('Deleting remote item "%s".', self.rel_path)
        item_request = self.get_item_request()
        try:
            od_api_helper.item_request_call(self.repo, item_request.delete)
            self.repo.delete_item(self.item_name, self.parent_relpath, self.is_folder)
            logging.info('Deleted remote item "%s".', self.rel_path)
            return True
        except (onedrivesdk.error.OneDriveError, OSError) as e:
            logging.error('Error deleting item "%s": %s.', self.rel_path, e)
            return False
