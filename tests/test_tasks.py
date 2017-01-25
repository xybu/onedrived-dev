import json
import unittest

import requests_mock

from onedrived import get_resource, od_task, od_webhook
from onedrived.od_tasks.base import TaskBase
from onedrived.od_tasks.start_repo import StartRepositoryTask
from onedrived.od_tasks.update_subscriptions import UpdateSubscriptionTask

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
        self.webhook_worker = od_webhook.WebhookWorkerThread('https://localhost')
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


if __name__ == '__main__':
    unittest.main()
