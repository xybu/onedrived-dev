import asyncio
import unittest

from onedrived import od_context, od_auth, od_repo

from tests import mock
from tests.test_models import get_sample_drive, get_sample_drive_config


class TestOneDriveLocalRepository(unittest.TestCase):

    def setUp(self):
        ctx = mock.MagicMock(spec=od_context.UserContext, config_dir='/tmp', loop=asyncio.get_event_loop())
        auth = mock.MagicMock(spec=od_auth.OneDriveAuthenticator, **{'refresh_session.return_value': None})
        drive = get_sample_drive()
        drive_dict, self.drive_config = get_sample_drive_config()
        self.repo = od_repo.OneDriveLocalRepository(ctx, auth, drive, self.drive_config)

    def test_properties(self):
        self.assertEqual(self.drive_config.localroot_path, self.repo.local_root)


if __name__ == '__main__':
    unittest.main()
