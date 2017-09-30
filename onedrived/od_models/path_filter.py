import zgitignore


class PathFilter(zgitignore.ZgitIgnore):
    """
    PathFilter parses a gitignore-like file to an ignore list, and then allows for other components to query if a
    specific path should be ignored.
    """

    TMP_PREFIX = '.'
    TMP_SUFFIX = '.odtemp!'

    def __init__(self, rules):
        """
        Initialize the filter with a list of (case-INsensitive) gitignore rules.
        :param [str] rules: List of gitignore rules.
        """
        super().__init__(rules, ignore_case=True)
        self.add_patterns((self.TMP_PREFIX + '*' + self.TMP_SUFFIX, '*[<>?*:"|]*'))

    def add_rules(self, rules):
        """
        Add a new (case-INsensitive) gitignore rule.
        :param [str] rules: The rule to add.
        """
        self.add_patterns(rules)

    def should_ignore(self, path, is_dir=False):
        """
        Determine if a path should be ignored.
        :param str path: Path relative to repository root.
        :param True | False is_dir: Whether or not the path is a folder.
        :return True | False: Whether or not the path should be ignored.
        """
        if path[-1] == '/':
            is_dir = True
        return self.is_ignored(path, is_directory=is_dir)

    @classmethod
    def get_temp_name(cls, name):
        return cls.TMP_PREFIX + name + cls.TMP_SUFFIX
