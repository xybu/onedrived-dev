import json
import re
import tempfile
import unittest

import click
import requests_mock

from onedrived import get_resource, od_pref


class TestPrefCLI(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        click.get_app_dir = lambda x: self.tempdir.name + '/' + x
        od_pref.context = od_pref.load_context()
        od_pref.context._create_config_dir_if_missing()

    def tearDown(self):
        self.tempdir.cleanup()

    def test_config_set_valid(self):
        for arg in (('webhook_type', 'direct'), ('webhook_port', 0), ('logfile_path', self.tempdir.name + '/test.log')):
            try:
                od_pref.set_config(args=[str(v) for v in arg])
            except SystemExit:
                pass
            context = od_pref.load_context()
            self.assertEqual(arg[1], context.config[arg[0]])

    def test_config_set_invalid_str(self):
        for arg in (('webhook_type', 'whatever'), ('logfile_path', '/'),
                    ('webhook_port', 70000), ('num_workers', 0)):
            try:
                od_pref.set_config(args=[str(v) for v in arg])
            except SystemExit:
                pass
            context = od_pref.load_context()
            self.assertNotEqual(arg[1], context.config[arg[0]])

    def test_config_set_key_typo(self):
        try:
            od_pref.set_config(args=['webhook_typo', 'whatever'])
        except SystemExit:
            pass
        context = od_pref.load_context()
        self.assertNotIn('webhook_typo', context.config)

    def test_config_print(self):
        try:
            od_pref.print_config(args=[])
        except SystemExit:
            pass

    def _call_authenticate_account(self, mock, code, args):
        profile = json.loads(get_resource('data/me_profile_response.json', pkg_name='tests'))
        def callback_auth(request, context):
            self.assertIn('code=' + code, request.text)
            context.status_code = 200
            return json.loads(get_resource('data/session_response.json', pkg_name='tests'))
        def callback_profile(request, context):
            context.status_code = 200
            return profile
        mock.post(re.compile('//login\.live\.com\.*'), json=callback_auth)
        mock.get('https://apis.live.net/v5.0/me', json=callback_profile)
        try:
            od_pref.authenticate_account(args=args)
        except SystemExit:
            pass
        context = od_pref.load_context()
        self.assertIsNotNone(context.get_account(profile['id']))

    def test_authenticate_account_with_code(self):
        with requests_mock.Mocker() as mock:
            self._call_authenticate_account(mock=mock, code='foobar_code', args=('--code', 'foobar_code'))

    def test_authenticate_account_with_url(self):
        url = 'https://login.live.com/oauth20_desktop.srf?code=foobar_code&lc=1033'
        click.prompt = lambda x, type=str: url
        with requests_mock.Mocker() as mock:
            self._call_authenticate_account(mock=mock, code='foobar_code', args=())


if __name__ == '__main__':
    unittest.main()
