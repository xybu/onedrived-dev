import logging
import os
import shutil

from .base import TaskBase as _TaskBase
from .. import mkdir


class MergeDirectoryTask(_TaskBase):

    def __init__(self, repo, task_pool, rel_path, item_request=None):
        """
        :param onedrived.od_repo.OneDriveLocalRepository repo:
        :param onedrived.od_task.TaskPool task_pool:
        :param str rel_path: Path of the target item relative to repository root. Assume not ending with '/'.
        :param onedrivesdk.request.item_request_builder.ItemRequestBuilder item_request:
        """
        super().__init__(repo, task_pool)
        self.rel_path = rel_path
        self.item_request = item_request
        self._local_abspath = repo.local_root + rel_path

    def __repr__(self):
        return type(self).__name__ + '(%s)' % self.local_abspath

    def _list_local_names(self):
        """
        List all names under the task local directory. Try resolving naming conflict (same name case-INsensitive)
        as it goes.
        :return [str]: A list of entry names.
        """
        ent_list = set()
        ent_count = dict()
        for ent in os.listdir(self.local_abspath):
            ent_path = self.local_abspath + '/' + ent
            is_dir = os.path.isdir(ent_path)
            filename, ext = os.path.splitext(ent)
            if self.repo.path_filter.should_ignore(self.rel_path + '/' + ent, is_dir):
                logging.debug('Ignored local path "%s/%s".', self.rel_path, ent)
                continue
            ent_lower = ent.lower()
            if ent_lower in ent_count:
                ent_count[ent_lower] += 1
                abspath = self.local_abspath + '/' + ent
                try:
                    ent = filename + ' ' + str(ent_count[ent_lower]) + ext
                    os.rename(ent_path, abspath)
                    ent_count[ent.lower()] = 0
                except (IOError, OSError) as e:
                    logging.error('Error occurred when solving name conflict of "%s": %s.', abspath, e)
                    continue
            else:
                ent_count[ent_lower] = 0
            ent_list.add(ent)
        return ent_list

    def _rename_with_local_suffix(self, name):
        def _move(new_name):
            shutil.move(self.local_abspath + '/' + name, self.local_abspath + '/' + new_name)
            return new_name
        suffix = ' (' + self.repo.context.host_name + ')'
        new_name = name + suffix
        if not os.path.exists(self.local_abspath + '/' + new_name):
            return _move(new_name)
        count = 1
        new_name = name + ' ' + str(count) + suffix
        while os.path.exists(self.local_abspath + '/' + new_name):
            count += 1
            new_name = name + ' ' + str(count) + suffix
        return _move(new_name)

    def handle(self):
        if not os.path.isdir(self.local_abspath):
            logging.error('Error: Local path "%s" is not a directory.' % self.local_abspath)
            return

        try:
            all_local_items = self._list_local_names()
            all_remote_items = self.item_request.children.get()
        except (IOError, OSError) as e:
            logging.error('Error occurred when syncing "%s": %s.', self.local_abspath, e)
            return

        for remote_item in all_remote_items:
            remote_is_folder = remote_item.folder is not None
            all_local_items.discard(remote_item.name)  # Remove remote item from untouched list.
            if not self.repo.path_filter.should_ignore(self.rel_path + '/' + remote_item.name, remote_is_folder):
                self._handle_remote_item(remote_item, all_local_items)
            else:
                logging.debug('Ignored remote path "%s/%s".', self.rel_path, remote_item.name)

        for n in all_local_items:
            self._handle_local_item(n)

    def _item_matches_record(self, remote_item, item_record):
        """
        :param onedrivesdk.model.item.Item remote_item:
        :param onedrived.od_repo.ItemRecord item_record:
        """

        return (remote_item.id == item_record.item_id and
                remote_item.last_modified_date_time == item_record.modified_time and
                remote_item.size == item_record.size
                )

    def _handle_remote_file_with_record(self, remote_item, item_record, item_stat, item_local_abspath, all_local_items):
        """
        :param onedrivesdk.model.item.Item remote_item:
        :param onedrived.od_repo.ItemRecord item_record:
        :param posix.stat_result | None item_stat:
        :param str item_local_abspath:
        :param [str] all_local_items:
        """
        pass

    def _handle_remote_file_without_record(self, remote_item, item_stat, item_local_abspath, all_local_items):
        """
        :param onedrivesdk.model.item.Item remote_item:
        :param posix.stat_result | None item_stat:
        :param str item_local_abspath:
        :param [str] all_local_items:
        """
        pass

    def _handle_remote_folder(self, remote_item, item_local_abspath, all_local_items):
        try:
            if os.path.isfile(item_local_abspath):
                # Remote item is a directory but local item is a file. Rename the file to something else and proceed.
                all_local_items.add(self._rename_with_local_suffix(remote_item.name))

            if not os.path.exists(item_local_abspath):
                # Local directory does not exist. Create it.
                logging.debug('Create missing directory "%s".', item_local_abspath)
                mkdir(item_local_abspath, uid=self.repo.context.user_uid, exist_ok=True)

            self.repo.update_item(remote_item, self.rel_path)
            self.task_pool.add_task(MergeDirectoryTask(
                repo=self.repo, task_pool=self.task_pool, rel_path=self.rel_path + '/' + remote_item.name,
                item_request=self.repo.authenticator.client.item(drive=self.repo.drive.id, id=remote_item.id)))
        except OSError as e:
            logging.error('Error occurred when checking directory "%s": %s', item_local_abspath, e)

    def _handle_remote_item(self, remote_item, all_local_items):
        """
        :param onedrivesdk.model.item.Item remote_item:
        :param [str] all_local_items:
        """
        # So we have three pieces of information -- the remote item metadata, the record in database, and the inode
        # on local file system. For the case of handling a remote item, the last two may be missing.
        item_local_abspath = self.local_abspath + '/' + remote_item.name
        record = self.repo.get_item_by_path(item_name=remote_item.name, parent_path=self.rel_path)
        try:
            stat = os.stat(item_local_abspath)
        except FileNotFoundError:
            stat = None
        except OSError as e:
            logging.error('Error occurred when accessing path "%s": %s.', item_local_abspath, e)
            return

        if remote_item.folder is not None:
            return self._handle_remote_folder(remote_item, item_local_abspath, all_local_items)

        if record is None:
            self._handle_remote_file_without_record(remote_item, stat, item_local_abspath, all_local_items)
        else:
            self._handle_remote_file_with_record(remote_item, record, stat, item_local_abspath, all_local_items)

        print('%s: %s (%s B)' % (remote_item.id, remote_item.name, remote_item.size))

    def _handle_local_item(self, item_name):
        print(item_name)
