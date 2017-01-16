import logging
import os
import shutil

import onedrivesdk.error
from send2trash import send2trash

from . import base, create_folder, delete_item, download_file, upload_file
from .. import mkdir, fix_owner_and_timestamp
from ..od_api_helper import get_item_modified_datetime, item_request_call
from ..od_dateutils import datetime_to_timestamp, diff_timestamps
from ..od_hashutils import hash_match, sha1_value
from ..od_repo import ItemRecordType, ItemRecordStatus


class MergeDirectoryTask(base.TaskBase):
    def __init__(self, repo, task_pool, rel_path, item_request):
        """
        :param onedrived.od_repo.OneDriveLocalRepository repo:
        :param onedrived.od_task.TaskPool task_pool:
        :param str rel_path: Path of the target item relative to repository root. Assume not ending with '/'.
        :param onedrivesdk.request.item_request_builder.ItemRequestBuilder item_request:
        """
        super().__init__(repo, task_pool)
        self.rel_path = rel_path
        self.item_request = item_request
        self.local_abspath = repo.local_root + rel_path

    def __repr__(self):
        return type(self).__name__ + '(%s)' % self.local_abspath

    def _list_local_names(self):
        """
        List all names under the task local directory. Try resolving naming conflict (same name case-INsensitive)
        as it goes.
        :return [str]: A list of entry names.
        """
        # TODO: This logic can be improved if remote info is provided.
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
        except (IOError, OSError) as e:
            logging.error('Error syncing "%s": %s.', self.local_abspath, e)
            return

        self.repo.context.watcher.rm_watch(self.local_abspath)

        try:
            all_remote_items = item_request_call(self.repo, self.item_request.children.get)
        except onedrivesdk.error.OneDriveError as e:
            logging.error('Encountered API Error: %s. Skip directory "%s".', e, self.rel_path)
            # Unmark the records under this dir so that they will not be swept in the next round.
            if self.rel_path == '':
                self.repo.mark_all_items(mark=ItemRecordStatus.OK)
            else:
                parent_relpath, dirname = os.path.split(self.rel_path)
                self.repo.unmark_items(item_name=dirname, parent_relpath=parent_relpath, is_folder=True)
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

        self.repo.context.watcher.add_watch(self.local_abspath)

    def _rename_local_and_download_remote(self, remote_item, all_local_items):
        all_local_items.add(self._rename_with_local_suffix(remote_item.name))
        self.task_pool.add_task(
            download_file.DownloadFileTask(self.repo, self.task_pool, remote_item, self.rel_path))

    def _handle_remote_file_with_record(self, remote_item, item_record, item_stat, item_local_abspath, all_local_items):
        """
        :param onedrivesdk.model.item.Item remote_item:
        :param onedrived.od_repo.ItemRecord item_record:
        :param posix.stat_result | None item_stat:
        :param str item_local_abspath:
        :param [str] all_local_items:
        """
        # In this case we have all three pieces of information -- remote item metadata, database record, and local inode
        # stats. The best case is that all of them agree, and the worst case is that they all disagree.

        if os.path.isdir(item_local_abspath):
            # Remote item is a file yet the local item is a folder.
            if item_record and item_record.type == ItemRecordType.FOLDER:
                # TODO: Use the logic in handle_local_folder to solve this.
                send2trash(item_local_abspath)
                self.repo.delete_item(remote_item.name, self.rel_path, True)
            else:
                # When db record does not exist or says the path is a file, then it does not agree with local inode
                # and the information is useless. We delete it and sync both remote and local items.
                if item_record:
                    self.repo.delete_item(remote_item.name, self.rel_path, False)
            return self._handle_remote_file_without_record(remote_item, None, item_local_abspath, all_local_items)

        remote_mtime, remote_mtime_w = get_item_modified_datetime(remote_item)
        local_mtime_ts = item_stat.st_mtime if item_stat else None
        remote_mtime_ts = datetime_to_timestamp(remote_mtime)
        record_mtime_ts = datetime_to_timestamp(item_record.modified_time)
        local_sha1_hash = None
        try:
            remote_sha1_hash = remote_item.file.hashes.sha1_hash
        except AttributeError:
            remote_sha1_hash = None

        def get_local_sha1_hash():
            nonlocal local_sha1_hash
            if local_sha1_hash is None:
                local_sha1_hash = sha1_value(item_local_abspath)
            return local_sha1_hash

        if (remote_item.id == item_record.item_id and remote_item.c_tag == item_record.c_tag or
                        remote_item.size == item_record.size and
                        diff_timestamps(remote_mtime_ts, record_mtime_ts) == 0):
            # The remote item metadata matches the database record. So this item has been synced before.
            if item_stat is None:
                # The local file was synced but now is gone. Delete remote one as well.
                logging.debug('Local file "%s" is gone but remote item matches db record. Delete remote item.',
                              item_local_abspath)
                self.task_pool.add_task(delete_item.DeleteRemoteItemTask(
                    self.repo, self.task_pool, self.rel_path, remote_item.name, remote_item.id, False))
            elif (item_stat.st_size == item_record.size_local and
                      (diff_timestamps(local_mtime_ts, record_mtime_ts) == 0 or
                               remote_sha1_hash and remote_sha1_hash == get_local_sha1_hash())):
                # If the local file matches the database record (i.e., same mtime timestamp or same content),
                # simply return. This is the best case.
                if diff_timestamps(local_mtime_ts, remote_mtime_ts) != 0:
                    logging.info('File "%s" seems to have same content but different timestamp (%f, %f). Fix it.',
                                 item_local_abspath, local_mtime_ts, remote_mtime_ts)
                    fix_owner_and_timestamp(item_local_abspath, self.repo.context.user_uid, remote_mtime_ts)
                    self.repo.update_item(remote_item, self.rel_path, item_stat.st_size)
                else:
                    self.repo.unmark_items(item_record.item_name, item_record.parent_path, is_folder=False)
            else:
                # Content of local file has changed. Because we assume the remote item was synced before, we overwrite
                # the remote item with local one.
                # API Issue: size field may not match file size.
                # Refer to https://github.com/OneDrive/onedrive-sdk-python/issues/88
                # Workaround -- storing both remote and local sizes.
                logging.debug('File "%s" was changed locally and the remote version is known old. Upload it.',
                              item_local_abspath)
                self.task_pool.add_task(upload_file.UploadFileTask(
                    self.repo, self.task_pool, self.item_request, self.rel_path, remote_item.name))
        else:
            # The remote file metadata and database record disagree.
            if item_stat is None:
                # If the remote file is the one on record, then the remote one is newer than the deleted local file
                # so it should be downloaded. If they are not the same, then the remote one should definitely
                # be kept. So the remote file needs to be kept and downloaded anyway.
                logging.debug('Local file "%s" is gone but remote item disagrees with db record. Download it.',
                              item_local_abspath)
                self.task_pool.add_task(
                    download_file.DownloadFileTask(self.repo, self.task_pool, remote_item, self.rel_path))
            elif item_stat.st_size == item_record.size_local and \
                    (diff_timestamps(local_mtime_ts, record_mtime_ts) == 0 or
                             item_record.sha1_hash and item_record.sha1_hash == get_local_sha1_hash()):
                # Local file agrees with database record. This means that the remote file is strictly newer.
                # The local file can be safely overwritten.
                logging.debug('Local file "%s" agrees with db record but remote item is different. Overwrite local.',
                              item_local_abspath)
                self.task_pool.add_task(
                    download_file.DownloadFileTask(self.repo, self.task_pool, remote_item, self.rel_path))
            else:
                # So both the local file and remote file have been changed after the record was created.
                equal_ts = diff_timestamps(local_mtime_ts, remote_mtime_ts) == 0
                if (item_stat.st_size == remote_item.size and (
                        (equal_ts or remote_sha1_hash and remote_sha1_hash == get_local_sha1_hash()))):
                    # Fortunately the two files seem to be the same.
                    # Here the logic is written as if there is no size mismatch issue.
                    logging.debug(
                        'Local file "%s" seems to have same content with remote but record disagrees. Fix db record.',
                        item_local_abspath)
                    if not equal_ts:
                        fix_owner_and_timestamp(item_local_abspath, self.repo.context.user_uid, remote_mtime_ts)
                    self.repo.update_item(remote_item, self.rel_path, item_stat.st_size)
                else:
                    # Worst case we keep both files.
                    logging.debug('Local file "%s" differs from db record and remote item. Keep both versions.',
                                  item_local_abspath)
                    self._rename_local_and_download_remote(remote_item, all_local_items)

    def _handle_remote_file_without_record(self, remote_item, item_stat, item_local_abspath, all_local_items):
        """
        Handle the case in which a remote item is not found in the database. The local item may or may not exist.
        :param onedrivesdk.model.item.Item remote_item:
        :param posix.stat_result | None item_stat:
        :param str item_local_abspath:
        :param [str] all_local_items:
        """
        if item_stat is None:
            # The file does not exist locally, and there is no record in database. The safest approach is probably
            # download the file and update record.
            self.task_pool.add_task(
                download_file.DownloadFileTask(self.repo, self.task_pool, remote_item, self.rel_path))
        elif os.path.isdir(item_local_abspath):
            # Remote path is file yet local path is a dir.
            logging.info('Path "%s" is a folder yet the remote item is a file. Keep both.', item_local_abspath)
            self._rename_local_and_download_remote(remote_item, all_local_items)
        else:
            # We first compare timestamp and size -- if both properties match then we think the items are identical
            # and just update the database record. Otherwise if sizes are equal, we calculate hash of local item to
            # determine if they are the same. If so we update timestamp of local item and update database record.
            # If the remote item has different hash, then we rename the local one and download the remote one so that no
            # information is lost.
            remote_mtime, remote_mtime_w = get_item_modified_datetime(remote_item)
            remote_mtime_ts = datetime_to_timestamp(remote_mtime)
            equal_ts = diff_timestamps(remote_mtime_ts, item_stat.st_mtime) == 0
            equal_attr = remote_item.size == item_stat.st_size and equal_ts
            # Because of the size mismatch issue, we can't use size not being equal as a shortcut for hash not being
            # equal. When the bug is fixed we can do it.
            if equal_attr or hash_match(item_local_abspath, remote_item):
                if not equal_ts:
                    logging.info('Local file "%s" has same content but wrong timestamp. '
                                 'Remote: mtime=%s, w=%s, ts=%s, size=%d. '
                                 'Local: ts=%s, size=%d. Fix it.',
                                 item_local_abspath,
                                 remote_mtime, remote_mtime_w, remote_mtime_ts, remote_item.size,
                                 item_stat.st_mtime, item_stat.st_size)
                    fix_owner_and_timestamp(item_local_abspath, self.repo.context.user_uid, remote_mtime_ts)
                self.repo.update_item(remote_item, self.rel_path, item_stat.st_size)
            else:
                self._rename_local_and_download_remote(remote_item, all_local_items)

    @staticmethod
    def _remote_dir_matches_record(remote_item, record):
        return record and record.type == ItemRecordType.FOLDER and record.c_tag == remote_item.c_tag and \
               record.e_tag == remote_item.e_tag and record.size == remote_item.size

    def _handle_remote_folder(self, remote_item, item_local_abspath, record, all_local_items):
        try:
            if os.path.isfile(item_local_abspath):
                # Remote item is a directory but local item is a file.
                if self._remote_dir_matches_record(remote_item, record):
                    # The remote item is very LIKELY to be outdated.
                    logging.warning('Local path "%s" is a file but its remote counterpart is a folder which seems to '
                                    'be synced before. Will delete the remote folder. To restore it, go to '
                                    'OneDrive.com and move the folder out of Recycle Bin.', item_local_abspath)
                    delete_item.DeleteRemoteItemTask(
                        self.repo, self.task_pool, self.rel_path, remote_item.name, remote_item.id, True).handle()
                    self.task_pool.add_task(upload_file.UploadFileTask(
                        self.repo, self.task_pool, self.item_request, self.rel_path, remote_item.name))
                    return
                # If the remote metadata doesn't agree with record, keep both by renaming the local file.
                all_local_items.add(self._rename_with_local_suffix(remote_item.name))

            if not os.path.exists(item_local_abspath):
                if self._remote_dir_matches_record(remote_item, record):
                    logging.debug('Local dir "%s" is gone but db record matches remote metadata. Delete remote dir.',
                                  item_local_abspath)
                    self.task_pool.add_task(delete_item.DeleteRemoteItemTask(
                        self.repo, self.task_pool, self.rel_path, remote_item.name, remote_item.id, True))
                    return
                # Local directory does not exist. Create it.
                logging.debug('Create missing directory "%s".', item_local_abspath)
                mkdir(item_local_abspath, uid=self.repo.context.user_uid, exist_ok=True)

            self.repo.update_item(remote_item, self.rel_path, 0)
            self.task_pool.add_task(MergeDirectoryTask(
                repo=self.repo, task_pool=self.task_pool, rel_path=self.rel_path + '/' + remote_item.name,
                item_request=self.repo.authenticator.client.item(drive=self.repo.drive.id, id=remote_item.id)))
        except OSError as e:
            logging.error('Error occurred when merging directory "%s": %s', item_local_abspath, e)

    @staticmethod
    def get_os_stat(path):
        try:
            return os.stat(path)
        except FileNotFoundError:
            return None

    def _handle_remote_item(self, remote_item, all_local_items):
        """
        :param onedrivesdk.model.item.Item remote_item:
        :param [str] all_local_items:
        """
        # So we have three pieces of information -- the remote item metadata, the record in database, and the inode
        # on local file system. For the case of handling a remote item, the last two may be missing.
        item_local_abspath = self.local_abspath + '/' + remote_item.name
        record = self.repo.get_item_by_path(item_name=remote_item.name, parent_relpath=self.rel_path)
        try:
            stat = self.get_os_stat(item_local_abspath)
        except OSError as e:
            logging.error('Error occurred when accessing path "%s": %s.', item_local_abspath, e)
            return

        if remote_item.folder is not None:
            return self._handle_remote_folder(remote_item, item_local_abspath, record, all_local_items)

        if remote_item.file is None:
            if remote_item.name in all_local_items:
                logging.info('Remote item "%s/%s" is neither a file nor a directory yet local counterpart exists. '
                             'Rename local item.', self.rel_path, remote_item.name)
                all_local_items.discard(remote_item.name)
                try:
                    new_name = self._rename_with_local_suffix(remote_item.name)
                    all_local_items.add(new_name)
                except OSError as e:
                    logging.error('Error renaming "%s/%s": %s. Skip this item due to unsolvable type conflict.',
                                  self.rel_path, remote_item.name, e)
            else:
                logging.info('Remote item "%s/%s" is neither a file nor a directory. Skip it.',
                             self.rel_path, remote_item.name)
            return

        if record is None:
            self._handle_remote_file_without_record(remote_item, stat, item_local_abspath, all_local_items)
        else:
            self._handle_remote_file_with_record(remote_item, record, stat, item_local_abspath, all_local_items)

    def _handle_local_folder(self, item_name, item_record, item_local_abspath):
        """
        :param str item_name:
        :param onedrived.od_repo.ItemRecord | None item_record:
        :param str item_local_abspath:
        """
        if item_record is not None and item_record.type == ItemRecordType.FOLDER:
            send2trash(item_local_abspath)
            self.repo.delete_item(item_name, self.rel_path, True)
            return
            # try:
            #     # If there is any file accessed after the time when the record was created, do not delete the dir.
            #     # Instead, upload it back.
            #     # As a note, the API will return HTTP 404 Not Found after the item was deleted. So we cannot know from
            #     # API when the item was deleted. Otherwise this deletion time should be the timestamp to use.
            #     # TODO: A second best timestamp is the latest timestamp of any children item under this dir.
            #     visited_files = subprocess.check_output(
            #         ['find', item_local_abspath, '-type', 'f',
            #         '(', '-newermt', item_record.record_time_str, '-o',
            #          '-newerat', item_record.record_time_str, ')', '-print'], universal_newlines=True)
            #     if visited_files == '':
            #         logging.info('Local item "%s" was deleted remotely and not used since %s. Delete it locally.',
            #                      item_local_abspath, item_record.record_time_str)
            #         send2trash(item_local_abspath)
            #         self.repo.delete_item(item_name, self.rel_path, True)
            #         return
            #     logging.info('Local directory "%s" was deleted remotely but locally used. Upload it back.')
            # except subprocess.CalledProcessError as e:
            #     logging.error('Error enumerating files in "%s" accessed after "%s": %s.',
            #                   item_local_abspath, item_record.record_time_str, e)
            # except OSError as e:
            #     logging.error('Error checking local folder "%s": %s.', item_local_abspath, e)

        if item_record:
            # Delete old records of this item and its children. Also delete if the record corrupts (i.e., says a file
            # instead of a directory).
            self.repo.delete_item(item_name, self.rel_path, True)

        # Either we decide to upload the item above, or the folder does not exist remotely and we have no reference
        # whether it existed remotely or not in the past. Better upload it back.
        logging.info('Local directory "%s" seems new. Upload it.', item_local_abspath)
        self.task_pool.add_task(create_folder.CreateFolderTask(
            self.repo, self.task_pool, item_name, self.rel_path, True, True))

    def _handle_local_file(self, item_name, item_record, item_stat, item_local_abspath):
        """
        :param str item_name:
        :param onedrived.od_repo.ItemRecord | None item_record:
        :param posix.stat_result | None item_stat:
        :param str item_local_abspath:
        """
        if item_stat is None:
            logging.info('Local-only file "%s" existed when scanning but is now gone. Skip it.', item_local_abspath)
            if item_record is not None:
                self.repo.delete_item(item_record.item_name, item_record.parent_path, False)
            return

        if item_record is not None and item_record.type == ItemRecordType.FILE:
            record_mtime_ts = datetime_to_timestamp(item_record.modified_time)
            if item_stat.st_size == item_record.size_local and \
                    (diff_timestamps(item_stat.st_mtime, record_mtime_ts) == 0 or
                             item_record.sha1_hash and item_record.sha1_hash == sha1_value(item_local_abspath)):
                logging.debug('Local file "%s" used to exist remotely but not found. Delete it.', item_local_abspath)
                send2trash(item_local_abspath)
                self.repo.delete_item(item_record.item_name, item_record.parent_path, False)
                return
            logging.debug('Local file "%s" is different from when it was last synced. Upload it.', item_local_abspath)
        else:
            logging.debug('Local file "%s" is new to OneDrive. Upload it.', item_local_abspath)

        self.task_pool.add_task(upload_file.UploadFileTask(
            self.repo, self.task_pool, self.item_request, self.rel_path, item_name))

    def _handle_local_item(self, item_name):
        item_local_abspath = self.local_abspath + '/' + item_name
        record = self.repo.get_item_by_path(item_name, self.rel_path)
        try:
            if os.path.isfile(item_local_abspath):
                # stat can be None because the function can be called long after dir is listed.
                stat = self.get_os_stat(item_local_abspath)
                self._handle_local_file(item_name, record, stat, item_local_abspath)
            elif os.path.isdir(item_local_abspath):
                self._handle_local_folder(item_name, record, item_local_abspath)
            else:
                logging.warning('Unsupported type of local item "%s". Skip it and remove record.', item_local_abspath)
                if record is not None:
                    self.repo.delete_item(record.item_name, record.parent_path, record.type == ItemRecordType.FOLDER)
        except OSError as e:
            logging.error('Error occurred when accessing path "%s": %s.', item_local_abspath, e)
