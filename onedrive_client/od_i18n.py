import json

from . import get_resource


class Translator:

    DEFAULT_LOCALE = 'en_US'

    def __init__(self, lang_resources, locale_str='en_US'):
        """
        :param [str] lang_resources: List of language resource files to load.
            Example: ['od_pref', 'configurator'] to load lang/od_pref
        :param str locale_str: Locale to load.
        """
        self.string_resources = dict()
        for lang in lang_resources:
            try:
                t = get_resource('lang/%s.%s.json' % (lang, locale_str), pkg_name='onedrive_client')
            except FileNotFoundError:
                t = get_resource('lang/%s.%s.json' % (lang, self.DEFAULT_LOCALE), pkg_name='onedrive_client')
            data = json.loads(t)
            self.string_resources.update(data)

    def __getitem__(self, item):
        return self.string_resources[item]
