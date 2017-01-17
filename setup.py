#!/usr/bin/python3

"""
onedrive-d
A Microsoft OneDrive client for Linux.
:copyright: (c) Xiangyu Bu
:license: MIT
"""

import sys

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

from onedrived import __author__, __email__, __homepage__, __project__, __version__


with open('requirements.txt', 'r') as f:
    install_requires = f.readlines()

test_requires = [
    'requests-mock',
]

with open('README.md', 'r') as f:
    readme = f.read()

python_version = sys.version_info

if python_version < (3, 3):
    raise Exception('%s %s only supports Python 3.3 and newer.' % (__project__, __version__))

setup(
    name=__project__,
    version=__version__,
    author=__author__,
    author_email=__email__,
    url=__homepage__,
    description='A Microsoft OneDrive client for Linux written in Python 3.',
    license='MIT',
    long_description=readme,
    packages=['onedrived'],
    include_package_data=True,
    package_data={
            'onedrived': ['data/*']
    },
    package_dir={'onedrived': 'onedrived'},
    entry_points={
        'console_scripts': [
            'onedrived = onedrived.od_main:main',
            'onedrived-pref = onedrived.od_pref:main'
        ],
        'gui_scripts': []
    },
    install_requires=install_requires,
    tests_require=test_requires,
    test_suite='tests',
    zip_safe=False
)
