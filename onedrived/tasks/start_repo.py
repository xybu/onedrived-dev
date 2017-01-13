import logging
import os

from . import merge_dir as _merge_dir
from .base import TaskBase as _TaskBase


class StartRepositoryTask(_TaskBase):
    """A simple task that bootstraps the syncing process of a Drive.
    It checks if the root path is a directory, and if so, create a task to merge the remote root with local root.
    """

    def __init__(self, repo, task_pool):
        """
        :param onedrived.od_repo.OneDriveLocalRepository repo:
        :param onedrived.od_task.TaskPool task_pool:
        """
        super().__init__(repo, task_pool)
        self.local_abspath = repo.local_root

    def __repr__(self):
        return type(self).__name__ + '(drive=' + self.repo.drive.id + ')'

    def handle(self):
        try:
            if os.path.isdir(self.repo.local_root):
                # Clean up dead records in the database.
                self.repo.sweep_marked_items()
                self.repo.mark_all_items()
                # And add a recursive merge task to task queue.
                item_request = self.repo.authenticator.client.item(drive=self.repo.drive.id, path='/')
                self.task_pool.add_task(_merge_dir.MergeDirectoryTask(self.repo, self.task_pool, '', item_request))
            else:
                raise OSError('Local root of Drive %s does not exist or is not a directory. Please check "%s".' %
                              (self.repo.drive.id, self.repo.local_root))
        except OSError as e:
            logging.error('Error: %s', e)
