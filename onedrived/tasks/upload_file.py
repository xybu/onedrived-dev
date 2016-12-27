from datetime import datetime
import logging
import os

import onedrivesdk.error
from onedrivesdk.model.item import Item, FileSystemInfo

from .base import TaskBase as _TaskBase
from .. import fix_owner_and_timestamp
from ..od_dateutils import datetime_to_timestamp
from ..od_api_helper import get_item_modified_datetime


class UploadFileTask(_TaskBase):

    def __init__(self, repo, task_pool, parent_dir_request, parent_relpath, item_name):
        """
        :param onedrived.od_repo.OneDriveLocalRepository repo:
        :param onedrived.od_task.TaskPool task_pool:
        :param onedrivesdk.request.item_request_builder.ItemRequestBuilder item_request:
        :param str parent_relpath:
        """
        super().__init__(repo, task_pool)
        self.parent_dir_request = parent_dir_request
        self.parent_relpath = parent_relpath
        self.item_name = item_name
        self.local_abspath = repo.local_root + parent_relpath + '/' + item_name

    def __repr__(self):
        return type(self).__name__ + '(%s)' % (self.local_abspath)

    def update_item(self, modified_item):
        item_request = self.repo.authenticator.client.item(drive=self.repo.drive.id, id=modified_item.id)
        try:
            return item_request.update(modified_item)
        except onedrivesdk.error.OneDriveError as e:
            logging.error('API Error occurred when updating "%s": %s.', self.local_abspath, e)
            self.repo.authenticator.refresh_session(self.repo.account_id)
            return item_request.update(modified_item)

    def handle(self):
        logging.info('Uploading file "%s" to OneDrive.', self.local_abspath)
        try:
            item_stat = os.stat(self.local_abspath)
            try:
                returned_item = self.parent_dir_request.children[self.item_name].upload(self.local_abspath)
            except onedrivesdk.error.OneDriveError as e:
                logging.error('API Error occurred when uploading "%s": %s.', self.local_abspath, e)
                self.repo.authenticator.refresh_session(self.repo.account_id)
                returned_item = self.parent_dir_request.children[self.item_name].upload(self.local_abspath)

            remote_mtime, remote_mtime_w = get_item_modified_datetime(returned_item)
            if not remote_mtime_w:
                # last_modified_datetime attribute is not modifiable in OneDrive server. Update local mtime.
                fix_owner_and_timestamp(self.local_abspath, self.repo.context.user_uid,
                                        datetime_to_timestamp(remote_mtime))
            else:
                file_system_info = FileSystemInfo()
                file_system_info.last_modified_date_time = datetime.utcfromtimestamp(item_stat.st_mtime)
                updated_item = Item()
                updated_item.id = returned_item.id
                updated_item.file_system_info = file_system_info
                try:
                    returned_item = self.update_item(updated_item)
                except onedrivesdk.error.OneDriveError as e:
                    logging.error('API Error occurred when uploading "%s": %s.', self.local_abspath, e)
                    self.repo.authenticator.refresh_session(self.repo.account_id)
                    returned_item = self.update_item(updated_item)

            self.repo.update_item(returned_item, self.parent_relpath, item_stat.st_size)
            logging.info('Finished uploading file "%s".', self.local_abspath)
        except (onedrivesdk.error.OneDriveError, OSError) as e:
            logging.error('Error uploading file "%s": %s.', self.local_abspath, e)
