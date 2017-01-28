class ConfiguratorError(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)


class ConfiguratorSchemaError(ConfiguratorError):
    def __init__(self, schema):
        super().__init__()
        self.bad_schema = schema


class UnsupportedSchemaType(ConfiguratorSchemaError):
    def __init__(self, schema_type, schema):
        super().__init__(schema)
        self.bad_schema_type = schema_type


class ConfiguratorKeyError(ConfiguratorError):
    def __init__(self, key):
        self.key = key


class ConfiguratorValueError(ConfiguratorError):
    def __init__(self, key, value):
        super().__init__()
        self.key = key
        self.value = value


class IntValueRequired(ConfiguratorValueError):
    pass


class IntValueBelowMinimum(ConfiguratorValueError):
    def __init__(self, key, value, minimum):
        super().__init__(key, value)
        self.minimum = minimum


class IntValueAboveMaximum(ConfiguratorValueError):
    def __init__(self, key, value, maximum):
        super().__init__(key, value)
        self.maximum = maximum


class StringNotStartsWith(ConfiguratorValueError):
    def __init__(self, key, value, expected_starts_with):
        super().__init__(key, value)
        self.expected_starts_with = expected_starts_with


class StringInvalidChoice(ConfiguratorValueError):
    def __init__(self, key, value, choices_allowed):
        super().__init__(key, value)
        self.choices_allowed = choices_allowed


class PathDoesNotExist(ConfiguratorValueError):
    pass


class PathIsNotFile(ConfiguratorValueError):
    pass
