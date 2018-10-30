import json
import os
import tempfile
import unittest

from onedrive_client import get_resource
from onedrive_client.od_models.dict_guard import GuardedDict, DictEntryTypes, SchemaValidator, exceptions


class TestDictGuard(unittest.TestCase):

    def setUp(self):
        self.schema = json.loads(get_resource('data/sample_config_schema.json', pkg_name='tests'))
        self.config_dict = {k: v['@default_value'] for k, v in self.schema.items()}
        self.config_guard = GuardedDict(self.config_dict, self.schema)

    def _test_update_value(self, k, v):
        old_value = self.config_dict[k]
        self.assertNotEqual(old_value, v)
        self.config_guard[k] = v
        if self.schema[k]['type'] == DictEntryTypes.STR:
            v = str(v)
        self.assertEqual(v, self.config_dict[k])

    def test_set_arbitrary_key(self):
        ex_raised = False
        try:
            self.config_guard['whatever123'] = 4
        except exceptions.DictGuardKeyError as e:
            self.assertEqual('whatever123', e.key)
            ex_raised = True
        self.assertTrue(ex_raised)

    def test_set_int(self):
        self._test_update_value('webhook_port', self.schema['webhook_port']['minimum'])

    def test_set_str(self):
        self._test_update_value('webhook_host', 'blah')
        self._test_update_value('webhook_host', 123123123)
        self._test_update_value('webhook_type', 'ngrok')
        self._test_update_value('https_url', 'https://www.facebook.com')

    def test_set_str_to_int(self):
        ex_raised = False
        try:
            self.config_guard['webhook_port'] = 'bar'
        except exceptions.IntValueRequired as e:
            self.assertEqual('webhook_port', e.key)
            ex_raised = True
        self.assertTrue(ex_raised)
        self.assertEqual(self.schema['webhook_port']['@default_value'], self.config_dict['webhook_port'])

    def _test_set_int_boundary(self, k, v, attr, ex_type):
        ex_raised = False
        try:
            self.config_guard[k] = v
        except ex_type as e:
            self.assertEqual(k, e.key)
            self.assertEqual(v, e.value)
            self.assertEqual(self.schema[k][attr], getattr(e, attr))
            ex_raised = True
        self.assertTrue(ex_raised)
        self.assertEqual(self.schema[k]['@default_value'], self.config_dict[k])

    def test_set_int_below_min(self):
        self._test_set_int_boundary(
            'webhook_port', self.schema['webhook_port']['minimum'] - 1, 'minimum', exceptions.IntValueBelowMinimum)

    def test_set_int_above_max(self):
        self._test_set_int_boundary(
            'webhook_port', self.schema['webhook_port']['maximum'] + 1, 'maximum', exceptions.IntValueAboveMaximum)

    def test_set_str_out_of_choice(self):
        ex_raised = False
        choices = self.schema['webhook_type']['choices']
        self.assertNotIn('uuu', choices)
        try:
            self.config_guard['webhook_type'] = 'uuu'
        except exceptions.StringInvalidChoice as e:
            self.assertEqual('webhook_type', e.key)
            self.assertEqual('uuu', e.value)
            self.assertEqual(self.schema['webhook_type']['choices'], e.choices_allowed)
            ex_raised = True
        self.assertTrue(ex_raised)
        self.assertEqual(self.schema['webhook_type']['@default_value'], self.config_dict['webhook_type'])

    def test_set_str_empty(self):
        self._test_update_value('logfile_path', '')

    def test_set_str_create_file_if_missing(self):
        with tempfile.TemporaryDirectory() as td:
            path = td + '/' + 'test'
            self.config_guard['logfile_path'] = path
            self.assertTrue(os.path.isfile(path))
            self.assertEqual(self.config_dict['logfile_path'], path)

    def _test_set_str_file_with_val(self, val, excep):
        ex_raised = False
        try:
            self.config_guard['logfile_path'] = val
        except excep as e:
            self.assertEqual('logfile_path', e.key)
            self.assertEqual(val, e.value)
            ex_raised = True
        self.assertTrue(ex_raised)
        self.assertEqual(self.schema['logfile_path']['@default_value'], self.config_dict['logfile_path'])

    def test_set_str_with_non_file_path(self):
        self._test_set_str_file_with_val('/', exceptions.PathIsNotFile)
        del self.schema['logfile_path']['create_if_missing']
        self._test_set_str_file_with_val('/foo/bar/baz', exceptions.PathDoesNotExist)

    def test_set_str_with_permission_denied(self):
        ex_raised = False
        self.schema['logfile_path']['permission'] = 'w'
        try:
            self.config_guard['logfile_path'] = '/proc/1/stat'
        except OSError:
            ex_raised = True
        self.assertTrue(ex_raised)
        self.assertEqual(self.schema['logfile_path']['@default_value'], self.config_dict['logfile_path'])

    def test_str_with_permission_allowed(self):
        self.schema['logfile_path']['permission'] = 'r'
        self.config_guard['logfile_path'] = '/proc/1/stat'
        self.assertEqual('/proc/1/stat', self.config_dict['logfile_path'])

    def test_str_not_starts_with(self):
        ex_raised = False
        try:
            self.config_guard['https_url'] = 'http://www.facebook.com'
        except exceptions.StringNotStartsWith as e:
            self.assertEqual('https_url', e.key)
            self.assertEqual('http://www.facebook.com', e.value)
            ex_raised = True
        self.assertTrue(ex_raised)
        self.assertEqual(self.schema['https_url']['@default_value'], self.config_dict['https_url'])
        self.config_guard['https_url'] = ''
        self.assertEqual('', self.config_dict['https_url'])


class TestConfigSchema(unittest.TestCase):

    def test_config_schema(self):
        curr_config_schema = json.loads(get_resource('data/config_schema.json', pkg_name='onedrive_client'))
        SchemaValidator(curr_config_schema).validate()


if __name__ == '__main__':
    unittest.main()
