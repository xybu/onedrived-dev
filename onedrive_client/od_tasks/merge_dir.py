import itertools
import logging
import os
import shutil

import onedrivesdk.error
from onedrivesdk import Item, Folder, ChildrenCollectionRequest
from send2trash import send2trash

from onedrive_client.od_tasks import base, delete_item, download_file, upload_file
from onedrive_client import mkdir, fix_owner_and_timestamp
from onedrive_client.od_api_helper import (
    get_item_modified_datetime,
    item_request_call,
)
from onedrive_client.od_dateutils import datetime_to_timestamp, diff_timestamps
from onedrive_client.od_hashutils import hash_match, sha1_value
from onedrive_client.od_repo import ItemRecordType


def rename_with_suffix(parent_abspath, name, host_name):
    suffix = ' (' + host_name + ')'
    parent_abspath = parent_abspath + '/'

    # Calculate the file name without suffix.
    ent_name, ent_ext = os.path.splitext(name)
    if ent_name.endswith(suffix):
        ent_name = ent_name[:-len(suffix)]

    new_name = ent_name + suffix + ent_ext
    if os.path.exists(parent_abspath + new_name):
        count = 1
        if ' ' in ent_name:
            ent_name, count_str = ent_name.rsplit(' ', maxsplit=1)
            if count_str.isdigit() and count_str[0] != '0':
                count = int(count_str) + 1
        new_name = ent_name + ' ' + str(count) + suffix + ent_ext
        while os.path.exists(parent_abspath + new_name):
            count += 1
            new_name = ent_name + ' ' + str(count) + suffix + ent_ext
    shutil.move(parent_abspath + name, parent_abspath + new_name)
    return new_name


def get_os_stat(path):
    try:
        return os.stat(path)
    except FileNotFoundError:
        return None


class MergeDirectoryTask(base.TaskBase):

    def __init__(self, repo, task_pool, rel_path, item_request, deep_merge=True,
                 assume_remote_unchanged=False, parent_remote_unchanged=False):
        """
        :param onedrive_client.od_repo.OneDriveLocalRepository repo:
        :param onedrive_client.od_task.TaskPool task_pool:
        :param str rel_path: Path of the target item relative to repository root. Assume not ending with '/'.
        :param onedrivesdk.request.item_request_builder.ItemRequestBuilder item_request:
        :param True | False deep_merge: If False, only sync files under the specified directory.
        :param True | False assume_remote_unchanged: If True, assume there is no change in remote repository.
            Can be set True if ctag and etag of the folder Item match its database record.
        :param True | False parent_remote_unchanged: If parent remote dir item wasn't changed.
        """
        super().__init__(repo, task_pool)
        self.rel_path = rel_path
        self.item_request = item_request
        self.local_abspath = repo.local_root + rel_path
        self.deep_merge = deep_merge
        self.assume_remote_unchanged = assume_remote_unchanged
        self.parent_remote_unchanged = parent_remote_unchanged

    def __repr__(self):
        return type(self).__name__ + '(%s, deep=%s, remote_unchanged=%s, parent_remote_unchanged=%s)' % (
            self.local_abspath, self.deep_merge, self.assume_remote_unchanged, self.parent_remote_unchanged)

    def list_local_names(self):
        """
        List all names under the task local directory.
        Try resolving naming conflict (same name case-INsensitive) as it goes.
        :return [str]: A list of entry names.
        """
        # TODO: This logic can be improved if remote info is provided.
        ents_orig = os.listdir(self.local_abspath)
        ents_lower = [s.lower() for s in ents_orig]
        ents_lower_uniq = set(ents_lower)
        if len(ents_orig) == len(ents_lower_uniq):
            return set(ents_orig)
        ents_ret = set()
        ents_ret_lower = set()
        for ent, ent_lower in zip(ents_orig, ents_lower):
            ent_abspath = self.local_abspath + '/' + ent
            if ent_lower in ents_ret_lower:
                ent_name, ent_ext = os.path.splitext(ent)
                count = 1
                new_ent = ent_name + ' ' + str(count) + ent_ext
                new_ent_lower = new_ent.lower()
                while new_ent_lower in ents_ret_lower or new_ent_lower in ents_lower_uniq:
                    count += 1
                    new_ent = ent_name + ' ' + str(count) + ent_ext
                    new_ent_lower = new_ent.lower()
                try:
                    shutil.move(ent_abspath, self.local_abspath + '/' + new_ent)
                    ents_ret.add(new_ent)
                    ents_ret_lower.add(new_ent_lower)
                except (IOError, OSError) as e:
                    logging.error('Error occurred when solving name conflict of "%s": %s.', ent_abspath, e)
                    continue
            else:
                ents_ret.add(ent)
                ents_ret_lower.add(ent_lower)
        return ents_ret

    def handle(self):
        if not os.path.isdir(self.local_abspath):
            logging.error('Error: Local path "%s" is not a directory.' % self.local_abspath)
            return

        self.repo.context.watcher.rm_watch(self.repo, self.local_abspath)

        try:
            all_local_items = self.list_local_names()
        except (IOError, OSError) as e:
            logging.error('Error merging dir "%s": %s.', self.local_abspath, e)
            return

        all_records = self.repo.get_immediate_children_of_dir(self.rel_path)

        if not self.assume_remote_unchanged or not self.parent_remote_unchanged:
            try:
                remote_item_page = item_request_call(self.repo, self.item_request.children.get)
                all_remote_items = remote_item_page

                while True:
                    # HACK: ChildrenCollectionPage is not guaranteed to have
                    # the _next_page_link attribute and
                    # ChildrenCollectionPage.get_next_page_request doesn't
                    # implement the check correctly
                    if not hasattr(remote_item_page, '_next_page_link'):
                        break

                    logging.debug('Paging for more items: %s', self.rel_path)
                    remote_item_page = item_request_call(
                        self.repo,
                        ChildrenCollectionRequest.get_next_page_request(
                            remote_item_page,
                            self.repo.authenticator.client).get)
                    all_remote_items = itertools.chain(
                        all_remote_items, remote_item_page)
            except onedrivesdk.error.OneDriveError as e:
                logging.error('Encountered API Error: %s. Skip directory "%s".', e, self.rel_path)
                return

            for remote_item in all_remote_items:
                remote_is_folder = remote_item.folder is not None
                all_local_items.discard(remote_item.name)  # Remove remote item from untouched list.
                if not self.repo.path_filter.should_ignore(self.rel_path + '/' + remote_item.name, remote_is_folder):
                    self._handle_remote_item(remote_item, all_local_items, all_records)
                else:
                    logging.debug('Ignored remote path "%s/%s".', self.rel_path, remote_item.name)

        for n in all_local_items:
            self._handle_local_item(n, all_records)

        for rec_name, rec in all_records.items():
            logging.info('Record for item %s (%s/%s) is dead. Delete it it.', rec.item_id, rec.parent_path, rec_name)
            self.repo.delete_item(rec_name, rec.parent_path, is_folder=rec.type == ItemRecordType.FOLDER)

        self.repo.context.watcher.add_watch(self.repo, self.local_abspath)

    def _rename_local_and_download_remote(self, remote_item, all_local_items):
        all_local_items.add(rename_with_suffix(self.local_abspath, remote_item.name, self.repo.context.host_name))
        self.task_pool.add_task(
            download_file.DownloadFileTask(self.repo, self.task_pool, remote_item, self.rel_path))

    def _handle_remote_file_with_record(self, remote_item, item_record, item_stat, item_local_abspath, all_local_items):
        """
        :param onedrivesdk.model.item.Item remote_item:
        :param onedrive_client.od_repo.ItemRecord item_record:
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

        remote_mtime, _ = get_item_modified_datetime(remote_item)
        local_mtime_ts = item_stat.st_mtime if item_stat else None
        remote_mtime_ts = datetime_to_timestamp(remote_mtime)
        record_mtime_ts = datetime_to_timestamp(item_record.modified_time)
        try:
            remote_sha1_hash = remote_item.file.hashes.sha1_hash
        except AttributeError:
            remote_sha1_hash = None

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
                   remote_sha1_hash and remote_sha1_hash == sha1_value(item_local_abspath))):
                # If the local file matches the database record (i.e., same mtime timestamp or same content),
                # simply return. This is the best case.
                if diff_timestamps(local_mtime_ts, remote_mtime_ts) != 0:
                    logging.info('File "%s" seems to have same content but different timestamp (%f, %f). Fix it.',
                                 item_local_abspath, local_mtime_ts, remote_mtime_ts)
                    fix_owner_and_timestamp(item_local_abspath, self.repo.context.user_uid, remote_mtime_ts)
                    self.repo.update_item(remote_item, self.rel_path, item_stat.st_size)
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
                     item_record.sha1_hash and item_record.sha1_hash == sha1_value(item_local_abspath)):
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
                        (equal_ts or remote_sha1_hash and remote_sha1_hash == sha1_value(item_local_abspath)))):
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
        return record and record.type == ItemRecordType.FOLDER and record.size == remote_item.size and \
            record.c_tag == remote_item.c_tag and record.e_tag == remote_item.e_tag

    def _handle_remote_folder(self, remote_item, item_local_abspath, record, all_local_items):
        if not self.deep_merge:
            return
        try:
            remote_dir_matches_record = self._remote_dir_matches_record(remote_item, record)
            if os.path.isfile(item_local_abspath):
                # Remote item is a directory but local item is a file.
                if remote_dir_matches_record:
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
                all_local_items.add(
                    rename_with_suffix(self.local_abspath, remote_item.name, self.repo.context.host_name))

            if not os.path.exists(item_local_abspath):
                if remote_dir_matches_record:
                    logging.debug('Local dir "%s" is gone but db record matches remote metadata. Delete remote dir.',
                                  item_local_abspath)
                    self.task_pool.add_task(delete_item.DeleteRemoteItemTask(
                        self.repo, self.task_pool, self.rel_path, remote_item.name, remote_item.id, True))
                    return
                # Local directory does not exist. Create it.
                logging.debug('Create missing directory "%s".', item_local_abspath)
                mkdir(item_local_abspath, uid=self.repo.context.user_uid, exist_ok=True)

            # The database is temporarily corrupted until the whole dir is merged. But unfortunately we returned early.
            self.repo.update_item(remote_item, self.rel_path, 0)
            self.task_pool.add_task(MergeDirectoryTask(
                repo=self.repo, task_pool=self.task_pool, rel_path=self.rel_path + '/' + remote_item.name,
                item_request=self.repo.authenticator.client.item(drive=self.repo.drive.id, id=remote_item.id),
                assume_remote_unchanged=remote_dir_matches_record,
                parent_remote_unchanged=self.assume_remote_unchanged))
        except OSError as e:
            logging.error('Error occurred when merging directory "%s": %s', item_local_abspath, e)

    def _handle_remote_item(self, remote_item, all_local_items, all_records):
        """
        :param onedrivesdk.model.item.Item remote_item:
        :param [str] all_local_items:
        :param dict(str, onedrive_client.od_repo.ItemRecord) all_records:
        """
        # So we have three pieces of information -- the remote item metadata, the record in database, and the inode
        # on local file system. For the case of handling a remote item, the last two may be missing.
        item_local_abspath = self.local_abspath + '/' + remote_item.name
        record = all_records.pop(remote_item.name, None)

        try:
            stat = get_os_stat(item_local_abspath)
        except OSError as e:
            logging.error('Error occurred when accessing path "%s": %s.', item_local_abspath, e)
            return

        if remote_item.folder is not None:
            return self._handle_remote_folder(remote_item, item_local_abspath, record, all_local_items)

        if remote_item.file is None:
            if stat:
                logging.info('Remote item "%s/%s" is neither a file nor a directory yet local counterpart exists. '
                             'Rename local item.', self.rel_path, remote_item.name)
                try:
                    new_name = rename_with_suffix(self.local_abspath, remote_item.name, self.repo.context.host_name)
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
        :param onedrive_client.od_repo.ItemRecord | None item_record:
        :param str item_local_abspath:
        """
        if not self.deep_merge:
            return

        if self.repo.path_filter.should_ignore(self.rel_path + '/' + item_name, True):
            logging.debug('Ignored local directory "%s/%s".', self.rel_path, item_name)
            return

        if item_record is not None and item_record.type == ItemRecordType.FOLDER:
            if self.assume_remote_unchanged:
                rel_path = self.rel_path + '/' + item_name
                self.task_pool.add_task(MergeDirectoryTask(
                    repo=self.repo, task_pool=self.task_pool, rel_path=rel_path,
                    item_request=self.repo.authenticator.client.item(drive=self.repo.drive.id, path=rel_path),
                    assume_remote_unchanged=True, parent_remote_unchanged=self.assume_remote_unchanged))
            else:
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
        elif item_record is not None:
            if self.assume_remote_unchanged:
                logging.info('Remote item for local dir "%s" is a file that has been deleted locally. '
                             'Delete the remote item and upload the file.', item_local_abspath)
                if not delete_item.DeleteRemoteItemTask(
                        repo=self.repo, task_pool=self.task_pool, parent_relpath=self.rel_path,
                        item_name=item_name, item_id=item_record.item_id, is_folder=False).handle():
                    logging.error('Failed to delete outdated remote directory "%s/%s" of Drive %s.',
                                  self.rel_path, item_name, self.repo.drive.id)
                    # Keep the record so that the branch can be revisited next time.
                    return

        # Either we decide to upload the item above, or the folder does not exist remotely and we have no reference
        # whether it existed remotely or not in the past. Better upload it back.
        logging.info('Local directory "%s" seems new. Upload it.', item_local_abspath)
        self.task_pool.add_task(CreateFolderTask(
            self.repo, self.task_pool, item_name, self.rel_path, True, True))

    def _handle_local_file(self, item_name, item_record, item_stat, item_local_abspath):
        """
        :param str item_name:
        :param onedrive_client.od_repo.ItemRecord | None item_record:
        :param posix.stat_result | None item_stat:
        :param str item_local_abspath:
        """
        if self.repo.path_filter.should_ignore(self.rel_path + '/' + item_name, False):
            logging.debug('Ignored local file "%s/%s".', self.rel_path, item_name)
            return

        if item_stat is None:
            logging.info('Local-only file "%s" existed when scanning but is now gone. Skip it.', item_local_abspath)
            if item_record is not None:
                self.repo.delete_item(item_record.item_name, item_record.parent_path, False)
                if self.assume_remote_unchanged:
                    self.task_pool.add_task(delete_item.DeleteRemoteItemTask(
                        repo=self.repo, task_pool=self.task_pool, parent_relpath=self.rel_path,
                        item_name=item_name, item_id=item_record.item_id, is_folder=False))
            return

        if item_record is not None and item_record.type == ItemRecordType.FILE:
            record_ts = datetime_to_timestamp(item_record.modified_time)
            equal_ts = diff_timestamps(item_stat.st_mtime, record_ts) == 0
            if item_stat.st_size == item_record.size_local and \
                    (equal_ts or item_record.sha1_hash and item_record.sha1_hash == sha1_value(item_local_abspath)):
                # Local file matches record.
                if self.assume_remote_unchanged:
                    if not equal_ts:
                        fix_owner_and_timestamp(item_local_abspath, self.repo.context.user_uid, record_ts)
                else:
                    logging.debug('Local file "%s" used to exist remotely but not found. Delete it.',
                                  item_local_abspath)
                    send2trash(item_local_abspath)
                    self.repo.delete_item(item_record.item_name, item_record.parent_path, False)
                return
            logging.debug('Local file "%s" is different from when it was last synced. Upload it.', item_local_abspath)
        elif item_record is not None:
            # Record is a dir but local entry is a file.
            if self.assume_remote_unchanged:
                logging.info('Remote item for local file "%s" is a directory that has been deleted locally. '
                             'Delete the remote item and upload the file.', item_local_abspath)
                if not delete_item.DeleteRemoteItemTask(
                        repo=self.repo, task_pool=self.task_pool, parent_relpath=self.rel_path,
                        item_name=item_name, item_id=item_record.item_id, is_folder=True).handle():
                    logging.error('Failed to delete outdated remote directory "%s/%s" of Drive %s.',
                                  self.rel_path, item_name, self.repo.drive.id)
                    # Keep the record so that the branch can be revisited next time.
                    return
            logging.debug('Local file "%s" is new to OneDrive. Upload it.', item_local_abspath)

        self.task_pool.add_task(upload_file.UploadFileTask(
            self.repo, self.task_pool, self.item_request, self.rel_path, item_name))

    def _handle_local_item(self, item_name, all_records):
        """
        :param str item_name:
        :param dict(str, onedrive_client.od_repo.ItemRecord) all_records:
        :return:
        """
        item_local_abspath = self.local_abspath + '/' + item_name
        record = all_records.pop(item_name, None)
        try:
            if os.path.isfile(item_local_abspath):
                # stat can be None because the function can be called long after dir is listed.
                stat = get_os_stat(item_local_abspath)
                self._handle_local_file(item_name, record, stat, item_local_abspath)
            elif os.path.isdir(item_local_abspath):
                self._handle_local_folder(item_name, record, item_local_abspath)
            else:
                logging.warning('Unsupported type of local item "%s". Skip it and remove record.', item_local_abspath)
                if record is not None:
                    self.repo.delete_item(record.item_name, record.parent_path, record.type == ItemRecordType.FOLDER)
        except OSError as e:
            logging.error('Error occurred when accessing path "%s": %s.', item_local_abspath, e)


class CreateFolderTask(base.TaskBase):

    def __init__(self, repo, task_pool, item_name, parent_relpath, upload_if_success=True, abort_if_local_gone=True):
        """
        :param onedrive_client.od_repo.OneDriveLocalRepository repo:
        :param onedrive_client.od_task.TaskPool task_pool:
        :param str item_name:
        :param str parent_relpath:
        :param True | False upload_if_success:
        :param True | False abort_if_local_gone:
        """
        super().__init__(repo, task_pool)
        self.item_name = item_name
        self.parent_relpath = parent_relpath
        self.local_abspath = repo.local_root + parent_relpath + '/' + item_name
        self.upload_if_success = upload_if_success
        self.abort_if_local_gone = abort_if_local_gone

    def __repr__(self):
        return type(self).__name__ + '(%s, upload=%s)' % (self.local_abspath, self.upload_if_success)

    @staticmethod
    def _get_folder_pseudo_item(item_name):
        item = Item()
        item.name = item_name
        item.folder = Folder()
        return item

    def _get_item_request(self):
        if self.parent_relpath == '':
            return self.repo.authenticator.client.item(drive=self.repo.drive.id, id='root')
        else:
            return self.repo.authenticator.client.item(drive=self.repo.drive.id, path=self.parent_relpath)

    def handle(self):
        logging.info('Creating remote item for local dir "%s".', self.local_abspath)
        try:
            if self.abort_if_local_gone and not os.path.isdir(self.local_abspath):
                logging.warning('Local dir "%s" is gone. Skip creating remote item for it.', self.local_abspath)
                return
            item = self._get_folder_pseudo_item(self.item_name)
            item_request = self._get_item_request()
            item = item_request_call(self.repo, item_request.children.add, item)
            self.repo.update_item(item, self.parent_relpath, 0)
            logging.info('Created remote item for local dir "%s".', self.local_abspath)
            if self.upload_if_success:
                logging.info('Adding task to merge "%s" after remote item was created.', self.local_abspath)
                self.task_pool.add_task(MergeDirectoryTask(
                    self.repo, self.task_pool, self.parent_relpath + '/' + self.item_name,
                    self.repo.authenticator.client.item(drive=self.repo.drive.id, id=item.id)))
            return True
        except (onedrivesdk.error.OneDriveError, OSError) as e:
            logging.error('Error when creating remote dir of "%s": %s.', self.local_abspath, e)
            return False
