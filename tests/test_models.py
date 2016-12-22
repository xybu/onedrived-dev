import json
import unittest

from tests import get_resource

from onedrived import models


class TestAccountProfile(unittest.TestCase):
    def test_properties(self):
        data = json.loads(get_resource('json_data/me_profile_response.json'))
        account = models.account_profile.OneDriveAccountProfile(data)
        self.assertEqual(data['id'], account.account_id)
        self.assertEqual(data['name'], account.account_name)
        self.assertEqual(data['emails']['account'], account.account_email)


if __name__ == '__main__':
    unittest.main()
