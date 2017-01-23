"""
http_server.py

A webhook listener that directly accepts notifications from OneDrive server.
"""

import logging
import os
import random
import string
import threading
import http.server
import ssl

import requests


def resolve_public_ip():
    response = requests.get('https://api.ipify.org/?format=json').json()
    return response['ip']


def gen_random_token():
    return ''.join(random.sample(string.ascii_letters + string.digits, random.randrange(6, 12)))


# TODO: OneDrive only accepts HTTPS webhook.


class WebhookConfig:

    def __init__(self, host='', port=0):
        https_keyfile = os.getenv('WEBHOOK_KEY_FILE')
        https_certfile = os.getenv('WEBHOOK_CERT_FILE')
        if isinstance(https_keyfile, str) and isinstance(https_certfile, str):
            self.use_https = True
            self.https_keyfile = https_keyfile
            self.https_certfile = https_certfile
        else:
            self.use_https = False
        self.host = host
        self.port = port


class WebhookHTTPServer(http.server.HTTPServer):

    def init_props(self):
        self._session_token = gen_random_token()
        self.worker_thread = None

    @property
    def session_token(self):
        return self._session_token


class WebhookListener(threading.Thread):

    def __init__(self, config, handler_class):
        super().__init__(name='Webhook', daemon=False)
        self.config = config
        if self.config.use_https:
            self.server = WebhookHTTPServer((self.config.host, self.config.port), handler_class)
            self.server.socket = ssl.wrap_socket(self.server.socket.socket,
                                                 keyfile=config.https_keyfile,
                                                 certfile=config.https_certfile,
                                                 server_side=True)
        else:
            self.server = WebhookHTTPServer((self.config.host, self.config.port), handler_class)
        self.server.init_props()

    @property
    def webhook_url(self):
        if not hasattr(self, '_webhook_url'):
            self.hostname = self.config.host if self.config.host != '' else resolve_public_ip()
            self._webhook_url = '%s://%s:%d/%s' % (
                'https' if self.config.use_https else 'http',
                self.hostname, self.server.server_port, self.server.session_token)
        return self._webhook_url

    def set_worker(self, worker):
        self.server.worker_thread = worker

    def stop(self):
        self.server.shutdown()

    def run(self):
        logging.info('Webhook server listening on %s.', self.webhook_url)
        self.server.serve_forever()
        logging.info('Webhook server stopped.')
