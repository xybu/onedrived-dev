import tempfile
import unittest

import click

from onedrived import od_pref


class TestPrefCLI(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        click.get_app_dir = lambda x: self.tempdir.name + '/' + x
        od_pref.context = od_pref.load_context()

    def tearDown(self):
        self.tempdir.cleanup()

    def test_config_set_valid(self):
        try:
            od_pref.set_config(args=['webhook_type', 'direct'])
        except SystemExit:
            pass

    def test_config_set_invalid(self):
        for arg in (('webhook_type', 'whatever'),):
            try:
                od_pref.set_config(args=arg)
            except SystemExit:
                pass
            context = od_pref.load_context()
            self.assertNotEqual(arg[1], context.config[arg[0]])

    def test_config_print(self):
        try:
            od_pref.print_config(args=[])
        except SystemExit:
            pass


if __name__ == '__main__':
    unittest.main()
