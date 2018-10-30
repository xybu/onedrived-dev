from datetime import datetime, timedelta
import logging

import onedrivesdk
import onedrivesdk.error

from .base import TaskBase
from .. import od_api_helper


class UpdateSubscriptionTask(TaskBase):

    def __init__(self, repo, task_pool, webhook_worker, subscription_id=None):
        """
        :param onedrive_client.od_repo.OneDriveLocalRepository repo:
        :param onedrive_client.od_task.TaskPool | None task_pool:
        :param onedrive_client.od_webhook.WebhookWorkerThread webhook_worker:
        :param str | None subscription_id:
        """
        super().__init__(repo, task_pool)
        self.webhook_worker = webhook_worker
        self.subscription_id = subscription_id

    def handle(self):
        logging.info('Updating webhook for Drive %s.', self.repo.drive.id)
        item_request = self.repo.authenticator.client.item(drive=self.repo.drive.id, path='/')
        expiration_time = datetime.utcnow() + timedelta(seconds=self.repo.context.config['webhook_renew_interval_sec'])
        try:
            if self.subscription_id is None:
                subscription = od_api_helper.create_subscription(
                    item_request, self.repo, self.webhook_worker.webhook_url, expiration_time)
            else:
                subscription = onedrivesdk.Subscription()
                subscription.id = self.subscription_id
                subscription.notification_url = self.webhook_worker.webhook_url
                subscription.expiration_date_time = expiration_time
                subscription = od_api_helper.item_request_call(
                    self.repo, item_request.subscriptions[self.subscription_id].update, subscription)
            self.webhook_worker.add_subscription(subscription, self.repo)
            logging.info('Webhook for Drive %s updated.', self.repo.drive.id)
            return subscription
        except onedrivesdk.error.OneDriveError as e:
            logging.error('Error: %s', e)
        return None
