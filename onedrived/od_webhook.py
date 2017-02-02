import http.server
import json
import logging
import os
import threading
import queue
import urllib.parse

from .od_models.webhook_notification import WebhookNotification


def get_webhook_server(context):
    """
    :param onedrived.od_context.UserContext context:
    """
    if context.config['webhook_type'] == 'direct':
        from .od_webhooks.http_server import WebhookConfig, WebhookListener
        wh_config = WebhookConfig(host=context.config['webhook_host'], port=context.config['webhook_port'])
    elif context.config['webhook_type'] == 'ngrok':
        from .od_webhooks.ngrok_server import WebhookConfig, WebhookListener
        ngrok_config_file = context.config_dir + '/' + context.DEFAULT_NGROK_CONF_FILENAME
        if not os.path.isfile(ngrok_config_file):
            ngrok_config_file = None
        wh_config = WebhookConfig(port=context.config['webhook_port'], ngrok_config_path=ngrok_config_file)
    else:
        raise ValueError('Unsupported webhook type: "%s".' % context.config['webhook_type'])
    return WebhookListener(wh_config, OneDriveWebhookHandler)


def parse_notification_body(body):
    try:
        data = json.loads(body.decode('utf-8'))
        if 'value' in data:
            subscription_ids = set([WebhookNotification(v).subscription_id for v in data['value']])
        else:
            subscription_ids = (WebhookNotification(data).subscription_id,)
        return subscription_ids
    except (UnicodeError, json.JSONDecodeError, KeyError) as e:
        logging.error(e)
    except Exception as e:
        logging.error(e)
    return None


class WebhookWorkerThread(threading.Thread):

    MAX_PER_ITEM_DELAY_SEC = 10

    def __init__(self, webhook_url):
        super().__init__(name='WebhookWorker', daemon=True)
        self._callback_func = None
        self.webhook_url = webhook_url
        self._raw_input_queue = queue.Queue()
        self._registered_subscriptions = dict()

    def set_callback_func(self, func):
        self._callback_func = func
        logging.debug('Set callback function for webhook to %s.', str(func))

    def queue_input(self, raw_bytes):
        self._raw_input_queue.put(raw_bytes, block=False)

    def add_subscription(self, subscription, repo):
        """
        :param onedrivesdk.Subscription subscription:
        :param onedrived.od_repo.OneDriveLocalRepository repo:
        """
        self._registered_subscriptions[subscription.id] = repo
        logging.debug('Subscribed to root updates of drive %s. Subscription ID: %s.',
                      repo.drive.id, subscription.id)

    def schedule_callback(self, subscription_ids):
        for subscription_id in subscription_ids:
            if subscription_id in self._registered_subscriptions:
                repo = self._registered_subscriptions[subscription_id]
                self._callback_func(repo)
            else:
                logging.error('Unknown subscription ID "%s".', subscription_id)

    @staticmethod
    def parse_and_update_set(body, set_buffer):
        subscription_ids = parse_notification_body(body)
        if subscription_ids is not None:
            set_buffer.update(subscription_ids)

    def run(self):
        subscription_ids_buf = set()
        if self._callback_func is None:
            raise RuntimeError('Callback function for webhook notification is not set.')
        logging.debug('Started.')
        while True:
            raw_bytes = self._raw_input_queue.get()
            self._raw_input_queue.task_done()
            self.parse_and_update_set(raw_bytes, subscription_ids_buf)
            del raw_bytes
            try:
                while True:
                    more_bytes = self._raw_input_queue.get(block=True, timeout=self.MAX_PER_ITEM_DELAY_SEC)
                    self._raw_input_queue.task_done()
                    self.parse_and_update_set(more_bytes, subscription_ids_buf)
                    del more_bytes
            except queue.Empty:
                pass
            self.schedule_callback(subscription_ids_buf)
            subscription_ids_buf.clear()


class OneDriveWebhookHandler(http.server.BaseHTTPRequestHandler):

    VALIDATION_REQUEST_QUERY = 'validationtoken'

    protocol_version = 'HTTP/1.1'

    def echo(self, s):
        """
        :param str s:
        """
        s = s.encode('utf-8')
        self.send_response(http.server.HTTPStatus.OK)
        self.send_header('Content-Type', 'text/plain')
        self.send_header('Content-Length', str(len(s)))
        self.end_headers()
        self.wfile.write(s)

    # noinspection PyPep8Naming
    def do_POST(self):
        url = urllib.parse.urlparse(self.path)

        # Some basic validation.
        if url.path != '/' + self.server.session_token:
            return self.send_error(http.server.HTTPStatus.UNAUTHORIZED)

        # Handle webhook validation request.
        query = urllib.parse.parse_qs(url.query)
        if self.VALIDATION_REQUEST_QUERY in query and len(query) == 1:
            return self.echo(query[self.VALIDATION_REQUEST_QUERY][0])

        # Handle notifications.
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        self.send_response(http.server.HTTPStatus.OK)
        self.send_header('Content-Type', 'text/plain')
        self.send_header('Content-Length', '0')
        self.end_headers()
        logging.info(self.raw_requestline)
        self.server.worker_thread.queue_input(body)
