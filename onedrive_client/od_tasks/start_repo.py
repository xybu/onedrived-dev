import logging
import os

from . import base
from . import merge_dir


class StartRepositoryTask(base.TaskBase):
    """A simple task that bootstraps the syncing process of a Drive.
    It checks if the root path is a directory, and if so, create a task to merge the remote root with local root.
    """

    def __init__(self, repo, task_pool):
        """
        :param onedrive_client.od_repo.OneDriveLocalRepository repo:
        :param onedrive_client.od_task.TaskPool task_pool:
        """
        super().__init__(repo, task_pool)
        self.local_abspath = repo.local_root

    def __repr__(self):
        return type(self).__name__ + '(drive=' + self.repo.drive.id + ')'

    def handle(self):
        try:
            if os.path.isdir(self.repo.local_root):
                # And add a recursive merge task to task queue.
                item_request = self.repo.authenticator.client.item(drive=self.repo.drive.id, path='/')
                self.task_pool.add_task(merge_dir.MergeDirectoryTask(self.repo, self.task_pool, '', item_request))
            else:
                raise OSError('Local root of Drive %s does not exist or is not a directory. Please check "%s".' %
                              (self.repo.drive.id, self.repo.local_root))
        except OSError as e:
            logging.error('Error: %s', e)


# class ApplyLatestDeltaTask(StartRepositoryTask):
#
#     TOKEN_LATEST = 'latest'
#
#     def handle(self):
#         try:
#             logging.debug('Checking delta for Drive %s.', self.repo.drive.id)
#             item_request = self.repo.authenticator.client.item(drive=self.repo.drive.id, path='/')
#             delta_collection = item_request.delta(token=self.TOKEN_LATEST).get()
#             for item in delta_collection:
#                 print(item.name)
#             logging.info('Delta token: %s.', delta_collection.token)
#             import json
#             with open('delta_latest.json', 'a') as f:
#                 json.dump(delta_collection.__dict__, f, sort_keys=True, indent=4, separators=(',', ': '))
#                 f.write('\n')
#             delta_collection_2 = item_request.delta(token=delta_collection.token).get()
#             for item in delta_collection_2:
#                 print(item.name)
#             logging.info('Delta token 2: %s.', delta_collection_2.token)
#             with open('delta_latest_succ.json', 'a') as f:
#                 json.dump(delta_collection_2.__dict__, f, sort_keys=True, indent=4, separators=(',', ': '))
#                 f.write('\n')
#         except:
#             raise
