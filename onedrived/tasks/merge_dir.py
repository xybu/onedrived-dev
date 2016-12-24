import logging
import os

from .base import TaskBase as _TaskBase


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
        self._local_abspath = repo.local_root + ('/' + rel_path if len(rel_path) else '')

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

    def _handle_remote_item(self, remote_item, all_local_items):
        """
        :param onedrivesdk.model.item.Item remote_item:
        :param [str] all_local_items:
        """
        print('%s: %s (%s B)' % (remote_item.id, remote_item.name, remote_item.size))

    def _handle_local_item(self, item_name):
        print(item_name)
