import json
import os
import sys
import unittest

import onedrivesdk

from onedrived import get_resource, od_models, od_dateutils


def get_sample_drive():
    drive_response = json.loads(get_resource('data/drive_response.json', 'tests'))
    return onedrivesdk.Drive(drive_response)


def get_sample_drive_config():
    drive_dict = json.loads(get_resource('data/drive_config_item.json', 'tests'))
    drive_dict['ignorefile_path'] = os.path.join(
        os.path.dirname(sys.modules['tests'].__file__), 'data/ignore_list.txt')
    return drive_dict, od_models.drive_config.LocalDriveConfig(**drive_dict)


class TestAccountProfile(unittest.TestCase):

    def setUp(self):
        self.data = json.loads(get_resource('data/me_profile_response.json', pkg_name='tests'))
        self.account = od_models.account_profile.OneDriveAccountProfile(self.data)

    def test_properties(self):
        self.assertEqual(self.data['id'], self.account.account_id)
        self.assertEqual(self.data['name'], self.account.account_name)
        self.assertEqual(self.data['emails']['account'], self.account.account_email)
        self.assertEqual(self.data['first_name'], self.account.account_firstname)
        self.assertEqual(self.data['last_name'], self.account.account_lastname)

    def test_to_string(self):
        self.assertIsInstance(str(self.account), str)


class TestPathFilter(unittest.TestCase):
    def setUp(self):
        self.rules = get_resource('data/ignore_list.txt', pkg_name='tests').splitlines()
        self.filter = od_models.path_filter.PathFilter(self.rules)

    def assert_cases(self, cases):
        """
        Test a batch of cases.
        :param [(str, True | False, True | False)] cases: List of tuples (path, is_dir, answer).
        """
        for c in cases:
            path, is_dir, answer = c
            self.assertEqual(answer, self.filter.should_ignore(path, is_dir), str(c) + ' failed.')

    def test_add_rules(self):
        r = '/i_am_new_rule'
        self.assertFalse(self.filter.should_ignore(r))
        self.filter.add_rules([r])
        self.assertTrue(self.filter.should_ignore(r))

    def test_hardcoded_cases(self):
        cases = [
            ('/.hehe', True, True),
            ('/' + self.filter.get_temp_name('hello.txt'), False, True),
            ('/he?he', False, True)
        ]
        self.assert_cases(cases)

    def test_ignore_in_root(self):
        # The following rules also test dir-only ignores.
        cases = [
            ('/foo', True, True),
            ('/foo', False, True),
            ('/bar', True, True),
            ('/bar', False, False),
            ('/a/foo', False, False)
        ]
        self.assert_cases(cases)

    def test_ignore_general(self):
        cases = [
            ('/.swp', False, True),
            ('/a.swp', False, True),
            ('/hello/world.swp', False, True),
            ('/.ignore', False, True),
            ('/baz/.ignore', True, True),
            ('/baz/dont.ignore', False, False),
            ('/build', True, True),  # This rule tests case-insensitiveness
            ('/tmp/build', True, True)  # because the rule is "BUILD/"
        ]
        self.assert_cases(cases)

    def test_ignore_path(self):
        cases = [
            ('/path/to/ignore/file.txt', False, True),  # If the rule specifies a path, it is
            ('/oops/path/to/ignore/file.txt', False, False),  # relative to repository root.
            ('/path/to/dont_ignore/file.txt', False, False)
        ]
        self.assert_cases(cases)

    def test_negations(self):
        cases = [
            ('/path-ignored/file', False, True),  # Files under this dir should be ignored.
            ('/path-ignored/content', False, False)  # This file is explicitly negated from ignore.
        ]
        self.assert_cases(cases)

    def test_special_patterns(self):
        self.assert_cases([
            ('/#test#', False, True),
            ('/Documents/xb/old/resume.txt', False, True)  # Test rule containing "**".
        ])

    def test_auto_correction(self):
        cases = [
            ('/bar/', False, True)  # path indicates dir but is_dir says the contrary
        ]
        self.assert_cases(cases)


class TestPrettyApi(unittest.TestCase):

    def test_pretty_print_bytes(self):
        self.assertEqual('0.000 B', od_models.pretty_api.pretty_print_bytes(size=0, precision=3))
        self.assertEqual('1.00 KB', od_models.pretty_api.pretty_print_bytes(size=1025, precision=2))
        self.assertEqual('1.0 MB', od_models.pretty_api.pretty_print_bytes(size=1048576, precision=1))
        self.assertEqual('1.50 GB', od_models.pretty_api.pretty_print_bytes(size=1610612736, precision=2))


class TestDriveConfig(unittest.TestCase):

    def setUp(self):
        self.drive_dict, self.drive_config = get_sample_drive_config()

    def test_properties(self):
        self.assertEqual(self.drive_dict['account_id'], self.drive_config.account_id)
        self.assertEqual(self.drive_dict['drive_id'], self.drive_config.drive_id)
        self.assertEqual(self.drive_dict['ignorefile_path'], self.drive_config.ignorefile_path)
        self.assertEqual(self.drive_dict['localroot_path'], self.drive_config.localroot_path)


class TestWebhookNotification(unittest.TestCase):

    def setUp(self):
        self.data = json.loads(get_resource('data/webhook_notification.json', 'tests'))

    def test_properties(self):
        notification = od_models.webhook_notification.WebhookNotification(self.data)
        self.assertEqual(self.data['context'], notification.context)
        self.assertEqual(self.data['resource'], notification.resource)
        self.assertEqual(self.data['subscriptionId'], notification.subscription_id)
        self.assertEqual(self.data['tenantId'], notification.tenant_id)
        self.assertEqual(self.data['userId'], notification.user_id)
        self.assertEqual(
            od_dateutils.str_to_datetime(self.data['expirationDateTime']), notification.expiration_datetime)

    def _assert_missing_property_none(self, data_key, property_key):
        del self.data[data_key]
        notification = od_models.webhook_notification.WebhookNotification(self.data)
        self.assertIsNone(getattr(notification, property_key))

    def test_properties_missing_tenant_id(self):
        self._assert_missing_property_none('tenantId', 'tenant_id')

    def test_properties_missing_context(self):
        self._assert_missing_property_none('context', 'context')


class TestBidict(unittest.TestCase):
    """
    Bidict is used in od_watcher for fd -> (repo, file_path) mapping.
    """
    def test_use(self):
        d = od_models.bidict.loosebidict()
        key, val = (123, 'abc')
        d[key] = val
        # Test ordinary operations.
        self.assertIn(key, d)
        self.assertEqual(val, d[key])
        # Test inv operations.
        self.assertIn(val, d.inv)
        self.assertEqual(key, d.inv[val])
        # Test inv removal.
        popped_key = d.inv.pop(val)
        self.assertNotIn(key, d)
        self.assertNotIn(val, d.inv)
        self.assertEqual(key, popped_key)


if __name__ == '__main__':
    unittest.main()
