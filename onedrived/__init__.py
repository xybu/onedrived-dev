"""
onedrive-d
A Microsoft OneDrive client for Linux.
:copyright: (c) Xiangyu Bu <xybu92@live.com>
:license: MIT
"""

import os

__project__ = 'onedrived'
__author__ = 'Xiangyu Bu'
__email__ = 'xybu92@live.com'
__version__ = '2.0.0'
__homepage__ = 'https://github.com/xybu/onedrived-dev'


def mkdir(path, uid, mode=0o700, exist_ok=True):
    """Create a path and set up owner uid."""
    os.makedirs(path, mode, exist_ok=exist_ok)
    os.chown(path, uid, -1)
