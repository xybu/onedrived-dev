import logging
import os

import onedrivesdk.error

from . import update_mtime
from ..od_api_helper import item_request_call


class UploadFileTask(update_mtime.UpdateTimestampTask):

    # If file is smaller than this size (in Bytes) use HTTP PUT method to upload. Otherwise upload in chunks
    # using Session API (https://dev.onedrive.com/items/upload_large_files.htm).
    PUT_FILE_SIZE_THRESHOLD_BYTES = 10 << 20

    def __init__(self, repo, task_pool, parent_dir_request, parent_relpath, item_name):
        """
        :param onedrived.od_repo.OneDriveLocalRepository repo:
        :param onedrived.od_task.TaskPool task_pool:
        :param onedrivesdk.request.item_request_builder.ItemRequestBuilder parent_dir_request:
        :param str parent_relpath:
        :param str item_name:
        """
        super().__init__(repo, task_pool, parent_relpath, item_name)
        self.parent_dir_request = parent_dir_request

    def __repr__(self):
        return type(self).__name__ + '(%s)' % self.local_abspath

    def update_progress(self, curr_part, total_part):
        logging.info('Uploading file "%s": Part %d / %d.', self.local_abspath, curr_part, total_part)

    def handle(self):
        logging.info('Uploading file "%s" to OneDrive.', self.local_abspath)
        try:
            item_stat = os.stat(self.local_abspath)
            item_request = self.parent_dir_request.children[self.item_name]
            if item_stat.st_size < self.PUT_FILE_SIZE_THRESHOLD_BYTES:
                returned_item = item_request_call(self.repo, item_request.upload, self.local_abspath)
            else:
                returned_item = item_request_call(self.repo, item_request.upload_async,
                                                  self.local_abspath, upload_status=self.update_progress)
            self.update_timestamp_and_record(returned_item, item_stat)
            logging.info('Finished uploading file "%s".', self.local_abspath)
            return True
        except (onedrivesdk.error.OneDriveError, OSError) as e:
            logging.error('Error uploading file "%s": %s.', self.local_abspath, e)
            return False
