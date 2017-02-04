import json
import os
import unittest

import onedrivesdk
import requests_mock

from onedrived import get_resource, od_task, od_webhook
from onedrived.od_tasks.base import TaskBase
from onedrived.od_tasks.start_repo import StartRepositoryTask
from onedrived.od_tasks.update_subscriptions import UpdateSubscriptionTask
import onedrived.od_tasks.merge_dir as merge_dir

from tests.test_repo import get_sample_repo


class TestTaskBase(unittest.TestCase):

    def test_task_base(self):
        p = '/home/xb/123'
        base = TaskBase(repo=None, task_pool=od_task.TaskPool())
        base.local_abspath = p
        self.assertEqual(p, base.local_abspath)


class TasksTestCaseBase(unittest.TestCase):

    def setUp(self):
        self.task_pool = od_task.TaskPool()
        self.temp_config_dir, self.temp_repo_dir, self.drive_config, self.repo = get_sample_repo()

    def tearDown(self):
        self.temp_config_dir.cleanup()
        self.temp_repo_dir.cleanup()


class TestStartRepositoryTask(TasksTestCaseBase):

    def test_handle(self):
        task = StartRepositoryTask(self.repo, self.task_pool)
        task.handle()
        self.assertEqual(1, self.task_pool.outstanding_task_count)


class TestUpdateSubscriptionTask(TasksTestCaseBase):

    def setUp(self):
        super().setUp()
        self.webhook_worker = od_webhook.WebhookWorkerThread('https://localhost', callback_func=None)
        self.data = json.loads(get_resource('data/subscription_response.json', pkg_name='tests'))

    def assert_subscription(self, subscription):
        self.assertEqual(self.data['id'], subscription.id)
        self.assertEqual(self.data['resource'], subscription.resource)

    @requests_mock.mock()
    def test_handle_create(self, m):
        m.post('%sdrives/%s/root:/:/subscriptions' % (self.repo.authenticator.client.base_url, self.repo.drive.id),
               json=self.data)
        task = UpdateSubscriptionTask(self.repo, self.task_pool, self.webhook_worker)
        subscription = task.handle()
        self.assert_subscription(subscription)

    @requests_mock.mock()
    def test_handle_update(self, m):
        m.patch('%sdrives/%s/root:/:/subscriptions/%s' % (
            self.repo.authenticator.client.base_url, self.repo.drive.id, self.data['id']), json=self.data)
        task = UpdateSubscriptionTask(self.repo, self.task_pool, self.webhook_worker, subscription_id=self.data['id'])
        subscription = task.handle()
        self.assert_subscription(subscription)


class TestMergeDirTask(TasksTestCaseBase):

    def test_remote_dir_matches_record(self):
        item = onedrivesdk.Item(json.loads(get_resource('data/folder_item.json', pkg_name='tests')))
        self.repo.update_item(item, '', size_local=0)
        record = self.repo.get_item_by_path(item.name, '')
        merge_dir.MergeDirectoryTask._remote_dir_matches_record(item, record)

    def _generate_random_files(self, filenames):
        with open('/dev/urandom', 'rb') as rf:
            for filename in filenames:
                with open(self.repo.local_root + '/' + filename, 'wb') as f:
                    f.write(rf.read(4))

    def test_rename_with_suffix(self):
        self._generate_random_files(('foo',))
        merge_dir.rename_with_suffix(self.repo.local_root, 'foo', 'hostname')
        self.assertTrue(os.path.isfile(self.repo.local_root + '/foo (hostname)'))

    def test_rename_with_suffix_and_count(self):
        self._generate_random_files(('foo.txt', 'foo (hostname).txt', 'foo 2 (hostname).txt'))

        merge_dir.rename_with_suffix(self.repo.local_root, 'foo.txt', 'hostname')
        self.assertFalse(os.path.exists(self.repo.local_root + '/foo.txt'))
        self.assertTrue(os.path.isfile(self.repo.local_root + '/foo 1 (hostname).txt'))

        merge_dir.rename_with_suffix(self.repo.local_root, 'foo 1 (hostname).txt', 'hostname')
        self.assertFalse(os.path.exists(self.repo.local_root + '/foo 1 (hostname).txt'))
        self.assertTrue(os.path.isfile(self.repo.local_root + '/foo 3 (hostname).txt'))

    def test_get_os_stat(self):
        self.assertIsNone(merge_dir.get_os_stat('/foo/bar/baz/blah'))
        self.assertIsNotNone(merge_dir.get_os_stat('/'))


if __name__ == '__main__':
    unittest.main()
