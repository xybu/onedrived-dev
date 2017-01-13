import logging
import os
from datetime import datetime

import onedrivesdk.error
from onedrivesdk import Item, FileSystemInfo

from .update_item_base import UpdateItemTaskBase as _TaskBase
from .. import fix_owner_and_timestamp
from ..od_api_helper import get_item_modified_datetime
from ..od_api_helper import item_request_call
from ..od_dateutils import datetime_to_timestamp


class UpdateTimestampTask(_TaskBase):

    def __init__(self, repo, task_pool, parent_relpath, item_name):
        """
        :param onedrived.od_repo.OneDriveLocalRepository repo:
        :param onedrived.od_task.TaskPool task_pool:
        :param onedrivesdk.request.item_request_builder.ItemRequestBuilder parent_dir_request:
        :param str parent_relpath:
        :param str item_name:
        """
        super().__init__(repo, task_pool, parent_relpath, item_name, item_id=None, is_folder=False)
        self.parent_relpath = parent_relpath
        self.item_name = item_name
        self.local_abspath = repo.local_root + parent_relpath + '/' + item_name

    def __repr__(self):
        return type(self).__name__ + '(%s)' % self.local_abspath

    def update_timestamp_and_record(self, new_item, item_local_stat):
        remote_mtime, remote_mtime_w = get_item_modified_datetime(new_item)
        if not remote_mtime_w:
            # last_modified_datetime attribute is not modifiable in OneDrive server. Update local mtime.
            fix_owner_and_timestamp(self.local_abspath, self.repo.context.user_uid,
                                    datetime_to_timestamp(remote_mtime))
        else:
            file_system_info = FileSystemInfo()
            file_system_info.last_modified_date_time = datetime.utcfromtimestamp(item_local_stat.st_mtime)
            updated_item = Item()
            updated_item.file_system_info = file_system_info
            item_request = self.repo.authenticator.client.item(drive=self.repo.drive.id, id=new_item.id)
            new_item = item_request_call(self.repo, item_request.update, updated_item)
        self.repo.update_item(new_item, self.parent_relpath, item_local_stat.st_size)

    def handle(self):
        logging.info('Updating timestamp for file "%s".', self.local_abspath)
        try:
            if not os.path.isfile(self.local_abspath):
                logging.warning('Local path "%s" is no longer a file. Cannot update timestamp.', self.local_abspath)
                return False

            item = item_request_call(self.repo, self.get_item_request().get)
            item_stat = os.stat(self.local_abspath)
            self.update_timestamp_and_record(item, item_stat)
            logging.info('Finished updating timestamp for file "%s".', self.local_abspath)
            return True
        except (onedrivesdk.error.OneDriveError, OSError) as e:
            logging.error('Error updating timestamp for file "%s": %s.', self.local_abspath, e)
            return False
