import os

from onedrive_client.od_models.dict_guard import exceptions


class DictEntryTypes:
    INT = 'integer'
    STR = 'string'


class StringSubTypes:
    FILE = 'file'


def _test_bool_option(schema, opt_key):
    return opt_key in schema and schema[opt_key] is True


def _test_str_subtype_file(key, value, schema):
    if not os.path.exists(value):
        if _test_bool_option(schema, 'create_if_missing'):
            with open(value, 'w'):
                pass
        else:
            raise exceptions.PathDoesNotExist(key, value)
    elif not os.path.isfile(value):
        raise exceptions.PathIsNotFile(key, value)
    elif 'permission' in schema:
        with open(value, schema['permission']):
            pass


class GuardedDict:

    def __init__(self, config_dict, config_schema_dict):
        self.config_dict = config_dict
        self.config_schema_dict = config_schema_dict

    def set_int(self, key, value, schema):
        try:
            value = int(value)
        except ValueError:
            raise exceptions.IntValueRequired(key, value)
        if 'minimum' in schema and value < schema['minimum']:
            raise exceptions.IntValueBelowMinimum(key, value, schema['minimum'])
        if 'maximum' in schema and value > schema['maximum']:
            raise exceptions.IntValueAboveMaximum(key, value, schema['maximum'])
        self.config_dict[key] = value

    def set_str_subtype(self, key, value, schema):
        if schema['subtype'] == StringSubTypes.FILE:
            if _test_bool_option(schema, 'to_abspath'):
                value = os.path.abspath(value)
            _test_str_subtype_file(key, value, schema)
        else:
            raise exceptions.UnsupportedSchemaType(schema['subtype'], schema)
        self.config_dict[key] = value

    def set_str(self, key, value, schema):
        if not isinstance(value, str):
            value = str(value)
        if _test_bool_option(schema, 'allow_empty') and value == '':
            self.config_dict[key] = ''
            return
        if 'starts_with' in schema and not value.startswith(schema['starts_with']):
            raise exceptions.StringNotStartsWith(key, value, schema['starts_with'])
        if 'choices' in schema and value not in schema['choices']:
            raise exceptions.StringInvalidChoice(key, value, schema['choices'])
        if 'subtype' in schema:
            return self.set_str_subtype(key, value, schema)
        self.config_dict[key] = value

    def __setitem__(self, key, value):
        if key not in self.config_schema_dict:
            raise exceptions.DictGuardKeyError(key)
        schema = self.config_schema_dict[key]
        if schema['type'] == DictEntryTypes.INT:
            return self.set_int(key, value, schema)
        elif schema['type'] == DictEntryTypes.STR:
            return self.set_str(key, value, schema)
        else:
            raise exceptions.UnsupportedSchemaType(schema['type'], schema)


class SchemaValidator:

    def __init__(self, config_schema_dict):
        self.config_schema_dict = config_schema_dict

    def validate(self):
        for key, spec in self.config_schema_dict.items():
            if not isinstance(spec, dict):
                raise TypeError('Schema for key "%s" must be of dict type.' % key)
            if 'type' not in spec:
                raise KeyError('Required field "type" is missing in key "%s".' % key)
            elif spec['type'] not in (DictEntryTypes.INT, DictEntryTypes.STR):
                raise ValueError('Unsupported type of key "%s": "%s".' % (key, spec['type']))
