import json
import unittest

from tests import get_resource

from onedrived import models


class TestAccountProfile(unittest.TestCase):
    def test_properties(self):
        data = json.loads(get_resource('data/me_profile_response.json', pkg_name='tests'))
        account = models.account_profile.OneDriveAccountProfile(data)
        self.assertEqual(data['id'], account.account_id)
        self.assertEqual(data['name'], account.account_name)
        self.assertEqual(data['emails']['account'], account.account_email)


class TestPathFilter(unittest.TestCase):
    def setUp(self):
        self.rules = get_resource('data/ignore_list.txt', pkg_name='tests').splitlines()
        self.filter = models.path_filter.PathFilter(self.rules)

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


if __name__ == '__main__':
    unittest.main()
