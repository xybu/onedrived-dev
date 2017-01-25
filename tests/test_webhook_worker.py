import json
import threading
import unittest

import onedrivesdk

from onedrived import get_resource, od_webhook

from tests.test_repo import get_sample_repo


class TestWebhookWorker(unittest.TestCase):

    def setUp(self):
        od_webhook.WebhookWorkerThread.MAX_PER_ITEM_DELAY_SEC = 0
        self.temp_config_dir, self.temp_repo_dir, self.drive_config, self.repo = get_sample_repo()
        self.worker = od_webhook.WebhookWorkerThread('https://localhost:12345')
        self.callback_called_sem = threading.Semaphore(value=0)
        self.callback_repos = []
        self.callback_count = 0

    def tearDown(self):
        self.temp_config_dir.cleanup()
        self.temp_repo_dir.cleanup()

    def _dummy_webhook_callback(self, repo):
        self.callback_repos.append(repo)
        self.callback_count += 1
        self.callback_called_sem.release()

    def test_execution(self):
        self.worker.set_callback_func(self._dummy_webhook_callback)
        self.worker.start()
        notification_data = json.loads(get_resource('data/webhook_notification.json', pkg_name='tests'))
        subscription = onedrivesdk.Subscription()
        subscription.id = notification_data['subscriptionId']
        self.worker.add_subscription(subscription, self.repo)
        # Send a notification.
        self.worker.queue_input(json.dumps({'value': [notification_data]}).encode('utf-8'))
        # Duplicate notifications should be ignored.
        self.worker.queue_input(json.dumps(notification_data).encode('utf-8'))
        # Unknown subscriptions should be ignored.
        notification_data['subscriptionId'] = '233'
        self.worker.queue_input(json.dumps(notification_data).encode('utf-8'))
        self.assertTrue(self.callback_called_sem.acquire(timeout=3))
        self.assertFalse(self.callback_called_sem.acquire(timeout=1))
        self.assertEqual([self.repo], self.callback_repos)
        self.assertEqual(1, self.callback_count)


if __name__ == '__main__':
    unittest.main()
