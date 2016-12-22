import pkgutil

try:
    from unittest import mock
except:
    # noinspection PyUnresolvedReferences
    import mock


def get_resource(rel_path, pkg_name='tests', is_text=True):
    """
    Read a resource file in data/.
    :param str file_name:
    :param str pkg_name:
    :param True | False is_text: True to indicate the text is UTF-8 encoded.
    :return str | bytes: Content of the file.
    """
    content = pkgutil.get_data(pkg_name, rel_path)
    if is_text:
        content = content.decode('utf-8')
    return content
