"""
onedrive-d
A Microsoft OneDrive client for Linux.
:copyright: (c) Xiangyu Bu <xybu92@live.com>
:license: MIT
"""

import os
import pkgutil

__project__ = 'onedriveClient'
__author__ = 'Mario Apra'
__email__ = 'mariotapra@gmail.com'
__version__ = '2.0.1'
__homepage__ = 'https://github.com/derrix060/onedriveClient'


def mkdir(path, uid, mode=0o700, exist_ok=True):
    """Create a path and set up owner uid."""
    os.makedirs(path, mode, exist_ok=exist_ok)
    os.chown(path, uid, -1)


def fix_owner_and_timestamp(path, uid, t):
    """
    :param str path:
    :param int uid:
    :param int | float t:
    :return:
    """
    os.chown(path, uid, -1)
    os.utime(path, (t, t))


def get_resource(rel_path, pkg_name='onedrived', is_text=True):
    """
    Read a resource file in data/.
    :param str rel_path:
    :param str pkg_name:
    :param True | False is_text: True to indicate the text is UTF-8 encoded.
    :return str | bytes: Content of the file.
    """
    content = pkgutil.get_data(pkg_name, rel_path)
    if is_text:
        content = content.decode('utf-8')
    return content
