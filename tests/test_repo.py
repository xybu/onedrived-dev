import json
import tempfile
import unittest
try:
    from unittest import mock
except ImportError:
    import mock

import onedrivesdk

from onedrive_client import od_context, od_repo, od_api_helper, get_resource
from tests.test_auth import get_sample_authenticator
from tests.test_models import get_sample_drive, get_sample_drive_config


def get_sample_repo():
    temp_config_dir = tempfile.TemporaryDirectory()
    temp_repo_dir = tempfile.TemporaryDirectory()
    ctx = mock.MagicMock(spec=od_context.UserContext,
                         config=od_context.UserContext.DEFAULT_CONFIG,
                         config_dir=temp_config_dir.name,
                         host_name='hostname', loop=None)
    auth = get_sample_authenticator()
    drive = get_sample_drive()
    drive_dict, drive_config = get_sample_drive_config()
    drive_dict['localroot_path'] = temp_repo_dir.name
    drive_config = drive_config._replace(localroot_path=temp_repo_dir.name)
    repo = od_repo.OneDriveLocalRepository(ctx, auth, drive, drive_config)
    return temp_config_dir, temp_repo_dir, drive_config, repo


class TestOneDriveLocalRepository(unittest.TestCase):

    def setUp(self):
        self.temp_config_dir, self.temp_repo_dir, self.drive_config, self.repo = get_sample_repo()
        self.root_folder_item = onedrivesdk.Item(json.loads(get_resource('data/folder_item.json', pkg_name='tests')))
        self.root_subfolder_item = onedrivesdk.Item(json.loads(
            get_resource('data/subfolder_item.json', pkg_name='tests')))
        self.root_child_item = onedrivesdk.Item(json.loads(
            get_resource('data/folder_child_item.json', pkg_name='tests')))
        self.image_item = onedrivesdk.Item(json.loads(get_resource('data/image_item.json', pkg_name='tests')))
        self._add_all_items()

    def tearDown(self):
        self.temp_config_dir.cleanup()
        self.temp_repo_dir.cleanup()

    def _add_all_items(self):
        self.repo.update_item(self.root_folder_item, '', 0)
        self.repo.update_item(self.root_subfolder_item, '/' + self.root_folder_item.name, 0)
        self.repo.update_item(self.root_child_item, '/' + self.root_folder_item.name, self.root_child_item.size)
        self.repo.update_item(self.image_item, '', self.image_item.size)

    def _check_item_props(self, item, record, expected_type=od_repo.ItemRecordType.FILE):
        """
        :param onedrivesdk.Item item:
        :param onedrive_client.od_repo.ItemRecord record:
        """
        self.assertIsInstance(record, od_repo.ItemRecord)
        self.assertEqual(item.id, record.item_id)
        self.assertEqual(item.name, record.item_name)
        self.assertEqual(item.c_tag, record.c_tag)
        self.assertEqual(item.parent_reference.id, record.parent_id)
        self.assertEqual(od_api_helper.get_item_created_datetime(item), record.created_time)
        mtime, w = od_api_helper.get_item_modified_datetime(item)
        self.assertEqual(mtime, record.modified_time)
        self.assertEqual(expected_type, record.type)
        if expected_type == od_repo.ItemRecordType.FILE:
            self.assertEqual(item.size, record.size)
            self.assertEqual(item.file.hashes.sha1_hash, record.sha1_hash)

    def test_properties(self):
        self.assertEqual(self.drive_config.localroot_path, self.repo.local_root)
        self.assertEqual(self.drive_config.account_id, self.drive_config.account_id)

    def test_add_get_items(self):
        root_folder_item = self.repo.get_item_by_path(self.root_folder_item.name, '')
        self._check_item_props(self.root_folder_item, root_folder_item, od_repo.ItemRecordType.FOLDER)
        root_child_item = self.repo.get_item_by_path(self.root_child_item.name, '/' + self.root_folder_item.name)
        self._check_item_props(self.root_child_item, root_child_item, od_repo.ItemRecordType.FILE)

    def test_delete_folder(self):
        self.repo.delete_item(item_name=self.root_folder_item.name, parent_relpath='', is_folder=True)
        self.assertIsNone(self.repo.get_item_by_path(self.root_folder_item.name, ''))
        self.assertIsNone(self.repo.get_item_by_path(self.root_child_item.name, '/' + self.root_folder_item.name))
        self.assertIsNone(self.repo.get_item_by_path(self.root_subfolder_item.name, '/' + self.root_folder_item.name))
        self._check_item_props(
            self.image_item, self.repo.get_item_by_path(self.image_item.name, ''), od_repo.ItemRecordType.FILE)

    def test_delete_file(self):
        self.repo.delete_item(item_name=self.image_item.name, parent_relpath='', is_folder=False)
        self.assertIsNone(self.repo.get_item_by_path(self.image_item.name, ''))
        self.test_add_get_items()

    def test_move_item_down(self):
        self.repo.move_item(item_name=self.root_folder_item.name, parent_relpath='',
                            new_name='Public2', new_parent_relpath='/Test', is_folder=True)
        self.assertIsNone(self.repo.get_item_by_path(self.root_folder_item.name, ''))
        self.assertIsNone(self.repo.get_item_by_path(self.root_child_item.name, '/' + self.root_folder_item.name))
        self.assertIsNone(self.repo.get_item_by_path(self.root_subfolder_item.name, '/' + self.root_folder_item.name))
        self.root_folder_item.name = 'Public2'
        root_folder_item = self.repo.get_item_by_path('Public2', '/Test')
        self._check_item_props(self.root_folder_item, root_folder_item, od_repo.ItemRecordType.FOLDER)
        root_child_item = self.repo.get_item_by_path(self.root_child_item.name, '/Test/Public2')
        self._check_item_props(self.root_child_item, root_child_item, od_repo.ItemRecordType.FILE)
        root_subfolder_item = self.repo.get_item_by_path(self.root_subfolder_item.name, '/Test/Public2')
        self._check_item_props(self.root_subfolder_item, root_subfolder_item, od_repo.ItemRecordType.FOLDER)
        self._check_item_props(
            self.image_item, self.repo.get_item_by_path(self.image_item.name, ''), od_repo.ItemRecordType.FILE)

    def test_move_item_up(self):
        self.repo.move_item(item_name=self.image_item.name, parent_relpath='',
                            new_name=self.image_item.name, new_parent_relpath='/Public/foo 2', is_folder=False)
        self.repo.move_item(item_name=self.root_subfolder_item.name, parent_relpath='/' + self.root_folder_item.name,
                            new_name=self.root_subfolder_item.name, new_parent_relpath='', is_folder=True)
        self.assertIsNone(self.repo.get_item_by_path(self.image_item.name, ''))
        self.assertIsNone(self.repo.get_item_by_path(self.root_subfolder_item.name, '/Public'))
        self._check_item_props(
            self.root_subfolder_item, self.repo.get_item_by_path(self.root_subfolder_item.name, ''),
            od_repo.ItemRecordType.FOLDER)
        self._check_item_props(
            self.image_item, self.repo.get_item_by_path(self.image_item.name, '/foo 2'), od_repo.ItemRecordType.FILE)

    def _check_immediate_children(self, relpath, expected_records):
        records = self.repo.get_immediate_children_of_dir(relpath)
        self.assertEqual(len(expected_records), len(records))
        for r in expected_records:
            self.assertIn(r.name, records)
            expected_type = od_repo.ItemRecordType.FOLDER if r.folder else od_repo.ItemRecordType.FILE
            self._check_item_props(r, records[r.name], expected_type=expected_type)

    def test_get_immediate_children_of_root(self):
        self._check_immediate_children('', (self.image_item, self.root_folder_item))

    def test_get_immediate_children(self):
        self._check_immediate_children('/' + self.root_folder_item.name,
                                       (self.root_child_item, self.root_subfolder_item))


if __name__ == '__main__':
    unittest.main()
