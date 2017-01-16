import logging

import onedrivesdk.error
from onedrivesdk import Item, ItemReference

from . import update_item_base
from ..od_api_helper import item_request_call


class MoveItemTask(update_item_base.UpdateItemTaskBase):

    def __init__(self, repo, task_pool, parent_relpath, item_name,
                 new_parent_relpath=None, new_name=None, item_id=None, is_folder=False):
        """
        :param onedrived.od_repo.OneDriveLocalRepository repo:
        :param onedrived.od_task.TaskPool task_pool:
        :param str parent_relpath:
        :param str item_name:
        :param str | None new_parent_relpath:
        :param str | None new_name:
        :param str | None item_id:
        :param True | False is_folder:
        """
        super().__init__(repo=repo, task_pool=task_pool, parent_relpath=parent_relpath,
                         item_name=item_name, item_id=item_id, is_folder=is_folder)
        if new_parent_relpath is None and new_name is None:
            raise ValueError('New parent directory or name cannot both be None in MoveItemTask.')
        if new_parent_relpath is None:
            new_parent_relpath = parent_relpath
        if new_name is None:
            new_name = item_name
        if new_parent_relpath == parent_relpath and new_name == item_name:
            raise ValueError('Old path and new path are the same. No move is needed.')
        self.new_parent_relpath = new_parent_relpath
        self.new_name = new_name
        self.new_relpath = new_parent_relpath + '/' + new_name

    def _get_new_item(self):
        item = Item()
        if self.new_parent_relpath != self.parent_relpath:
            ref = ItemReference()
            # Refer to https://dev.onedrive.com/items/move.htm for Move API request.
            ref.path = '/drives/' + self.repo.drive.id + '/root:'
            if self.new_parent_relpath != '':
                ref.path += self.new_parent_relpath
            item.parent_reference = ref
        if self.new_name != self.item_name:
            item.name = self.new_name
        return item

    def __repr__(self):
        return type(self).__name__ + '(from=%s, to=%s, is_folder=%s)' % (
            self.rel_path, self.new_relpath, self.is_folder)

    def handle(self):
        logging.info('Moving item "%s" to "%s".', self.rel_path, self.new_relpath)

        # The routine assumes that the directory to save the new path exists remotely.
        item_request = self.get_item_request()
        try:
            item = item_request_call(self.repo, item_request.update, self._get_new_item())
            # TODO: update all records or rebuild records after deletion?
            # self.repo.delete_item(self.item_name, self.parent_relpath, self.is_folder)
            self.repo.move_item(item_name=self.item_name, parent_relpath=self.parent_relpath,
                                new_name=self.new_name, new_parent_relpath=self.new_parent_relpath,
                                is_folder=self.is_folder)
            self.repo.update_item(item, self.new_parent_relpath, 0)
            return True
        except (onedrivesdk.error.OneDriveError, OSError) as e:
            logging.error('Error moving item "%s" to "%s": %s.', self.rel_path, self.new_relpath, e)
            return False
