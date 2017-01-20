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
        logging.debug('Uploading file "%s": Part %d / %d.', self.local_abspath, curr_part, total_part)

    def handle(self):
        logging.info('Uploading file "%s" to OneDrive.', self.local_abspath)
        occupy_task = self.task_pool.occupy_path(self.local_abspath, self)
        if occupy_task is not self:
            logging.warning('Cannot upload "%s" because %s.', self.local_abspath,
                            "path is blacklisted" if occupy_task is None else str(occupy_task) + ' is in progress')
            return False
        try:
            item_stat = os.stat(self.local_abspath)
            if item_stat.st_size < self.PUT_FILE_SIZE_THRESHOLD_BYTES:
                item_request = self.parent_dir_request.children[self.item_name]
                returned_item = item_request_call(self.repo, item_request.upload, self.local_abspath)
            else:
                logging.info('Uploading large file "%s" in chunks of 10MB.', self.local_abspath)
                item_request = self.repo.authenticator.client.item(drive=self.repo.drive.id, path=self.rel_path)
                returned_item = item_request_call(self.repo, item_request.upload_async,
                                                  local_path=self.local_abspath, upload_status=self.update_progress)
            self.update_timestamp_and_record(returned_item, item_stat)
            self.task_pool.release_path(self.local_abspath)
            logging.info('Finished uploading file "%s".', self.local_abspath)
            return True
        except (onedrivesdk.error.OneDriveError, OSError) as e:
            logging.error('Error uploading file "%s": %s.', self.local_abspath, e)
            # TODO: what if quota is exceeded?
            if (isinstance(e, onedrivesdk.error.OneDriveError) and
                e.code == onedrivesdk.error.ErrorCode.MalwareDetected):
                    logging.warning('File "%s" was detected as malware by OneDrive. '
                                    'Do not upload during program session.', self.local_abspath)
                    self.task_pool.occupy_path(self.local_abspath, None)
                    return False
        self.task_pool.release_path(self.local_abspath)
        return False
