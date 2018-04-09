import unittest
try:
    from unittest import mock
except ImportError:
    import mock

import arrow
import requests
from onedrivesdk import Item, FileSystemInfo, error

from onedrived import od_api_helper


class TestApiHelper(unittest.TestCase):

    SAMPLE_ARROW_OBJ = arrow.utcnow()

    def dummy_api_call(self, excep):
        if self.count == 0:
            self.count = 1
            raise excep
        elif self.count > 1:
            raise ValueError('Dummy counter exceeds expected value 1.')

    def setUp(self):
        self.count = 0
        self.item = Item()

    def test_get_item_modified_datetime_modifiable(self):
        fs = FileSystemInfo()
        fs.last_modified_date_time = self.SAMPLE_ARROW_OBJ.datetime
        self.item.file_system_info = fs
        t, w = od_api_helper.get_item_modified_datetime(self.item)
        self.assertTrue(w, 'fileSystemInfo.lastModifiedDateTime should be modifiable.')
        self.assertEqual(self.SAMPLE_ARROW_OBJ, t)

    def test_get_item_modified_datetime_unmodifiable(self):
        self.item.last_modified_date_time = self.SAMPLE_ARROW_OBJ.datetime
        t, w = od_api_helper.get_item_modified_datetime(self.item)
        self.assertFalse(w, 'lastModifiedDateTime should be immutable.')
        self.assertEqual(self.SAMPLE_ARROW_OBJ, t)

    def test_get_item_created_datetime(self):
        self.item.created_date_time = self.SAMPLE_ARROW_OBJ.datetime
        self.assertEqual(self.SAMPLE_ARROW_OBJ, od_api_helper.get_item_created_datetime(self.item))

    @mock.patch('time.sleep')
    def test_item_request_call_on_connection_error(self, mock_sleep):
        od_api_helper.item_request_call(None, self.dummy_api_call, requests.ConnectionError())
        mock_sleep.assert_called_once_with(od_api_helper.THROTTLE_PAUSE_SEC)

    def test_item_request_call_on_unauthorized_error(self):
        account_id = 'dummy_acct'
        mock_repo = mock.MagicMock(account_id=account_id,
                                   **{'authenticator.refresh_session.return_value': 0, 'other.side_effect': KeyError})
        od_api_helper.item_request_call(
            mock_repo, self.dummy_api_call,
            error.OneDriveError(prop_dict={'code': error.ErrorCode.Unauthenticated, 'message': 'dummy'},
                                status_code=requests.codes.unauthorized))
        self.assertEqual(1, len(mock_repo.mock_calls))
        name, args, _ = mock_repo.method_calls[0]
        self.assertEqual('authenticator.refresh_session', name)
        self.assertEqual((account_id,), args)


if __name__ == '__main__':
    unittest.main()
