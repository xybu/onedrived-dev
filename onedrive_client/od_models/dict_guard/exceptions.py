class DictGuardError(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)


class DictGuardSchemaError(DictGuardError):
    def __init__(self, schema):
        super().__init__()
        self.bad_schema = schema


class UnsupportedSchemaType(DictGuardSchemaError):
    def __init__(self, schema_type, schema):
        super().__init__(schema)
        self.bad_schema_type = schema_type


class DictGuardKeyError(DictGuardError):
    def __init__(self, key):
        self.key = key


class DictGuardValueError(DictGuardError):
    def __init__(self, key, value):
        super().__init__()
        self.key = key
        self.value = value


class IntValueRequired(DictGuardValueError):
    pass


class IntValueBelowMinimum(DictGuardValueError):
    def __init__(self, key, value, minimum):
        super().__init__(key, value)
        self.minimum = minimum


class IntValueAboveMaximum(DictGuardValueError):
    def __init__(self, key, value, maximum):
        super().__init__(key, value)
        self.maximum = maximum


class StringNotStartsWith(DictGuardValueError):
    def __init__(self, key, value, expected_starts_with):
        super().__init__(key, value)
        self.expected_starts_with = expected_starts_with


class StringInvalidChoice(DictGuardValueError):
    def __init__(self, key, value, choices_allowed):
        super().__init__(key, value)
        self.choices_allowed = choices_allowed


class PathDoesNotExist(DictGuardValueError):
    pass


class PathIsNotFile(DictGuardValueError):
    pass
