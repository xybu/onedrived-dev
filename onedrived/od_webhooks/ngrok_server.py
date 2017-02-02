import logging
import os
import subprocess
import time
import shutil

import psutil
import requests

from . import http_server


class WebhookConfig(http_server.WebhookConfig):

    def __init__(self, port=0, ngrok_config_path=None):
        super().__init__(port=port)
        self.ngrok_path = os.getenv('NGROK_PATH', 'ngrok')
        ngrok_config_path = os.getenv('NGROK_CONFIG_FILE', ngrok_config_path)
        if isinstance(ngrok_config_path, str):
            self.ngrok_config_path = ngrok_config_path


def _append_cmd_arg(config, prop, arg, cmd):
    if hasattr(config, prop):
        cmd.append(arg)
        cmd.append(getattr(config, prop))


class WebhookListener(http_server.WebhookListener):

    POLL_TUNNELS_MAX_TRIES = 3

    def __init__(self, config, handler_class):
        super().__init__(config, handler_class)
        if shutil.which(config.ngrok_path) is None:
            raise RuntimeError('Did not find ngrok executable "%s".' % config.ngrok_path)
        cmd = [config.ngrok_path, 'http', str(self.server.server_port)]
        _append_cmd_arg(config, 'ngrok_config_path', '--config', cmd)
        self._start_ngrok_process(cmd)
        self._read_ngrok_tunnels()

    @property
    def ngrok_api_url(self):
        return self._api_url

    @property
    def webhook_url(self):
        return self._webhook_url

    def stop(self):
        try:
            self.ngrok_proc.terminate()
            self.ngrok_proc.wait(timeout=1)
        except subprocess.TimeoutExpired:
            self.ngrok_proc.kill()
        super().stop()

    def run(self):
        logging.info('Local webhook server listening on port %d.', self.server.server_port)
        super().run()

    def _start_ngrok_process(self, cmd):
        try:
            self.ngrok_proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.ngrok_proc.wait(timeout=1)
            logging.critical('ngrok process (pid %d) terminated early with return code %d. Command: "%s".',
                             self.ngrok_proc.pid, self.ngrok_proc.returncode, ' '.join(cmd))
            raise RuntimeError('Ngrok process exited early.')
        except subprocess.TimeoutExpired:
            pass

    def _find_ngrok_inspection_port(self):
        """
        :return (str, int):
        """
        for c in psutil.Process(self.ngrok_proc.pid).connections():
            if c.laddr[0] == '127.0.0.1' and c.raddr == () and c.status == psutil.CONN_LISTEN:
                return c.laddr
        raise RuntimeError('Did not find inspection interface of ngrok.')

    def _read_ngrok_tunnels(self):
        webhook_urls = dict()
        self._api_url = 'http://%s:%d/api' % self._find_ngrok_inspection_port()
        logging.info('Local ngrok API url: %s', self._api_url)
        for _ in range(0, self.POLL_TUNNELS_MAX_TRIES):
            try:
                data = requests.get(self._api_url + '/tunnels').json()
                if 'tunnels' not in data or len(data['tunnels']) == 0:
                    raise ValueError('ngrok API did not return any tunnel.')
                for tunnel in data['tunnels']:
                    if tunnel['config']['addr'].endswith(':' + str(self.server.server_port)):
                        webhook_urls[tunnel['proto']] = tunnel['public_url']
                break
            except (requests.ConnectionError, ValueError) as e:
                logging.error('Error reading ngrok API: %s. Retry in 1sec.', e)
                time.sleep(1)
        if 'https' in webhook_urls:
            self._webhook_url = webhook_urls['https'] + '/' + self.server.session_token
        else:
            raise RuntimeError('Did not receive any HTTPS tunnel from ngrok API.')
