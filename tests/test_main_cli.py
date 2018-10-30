import tempfile
import unittest

import click

from onedrive_client import od_main


class TestMainCLI(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        click.get_app_dir = lambda x: self.tempdir.name + '/' + x
        od_main.context = od_main.load_context()
        od_main.context._create_config_dir_if_missing()

    def tearDown(self):
        self.tempdir.cleanup()

    def test_init_and_shutdown_task_workers(self):
        od_main.init_task_pool_and_workers()
        od_main.shutdown_workers()


if __name__ == '__main__':
    unittest.main()
