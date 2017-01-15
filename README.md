# onedrived-dev

[![Build Status](https://travis-ci.org/xybu/onedrived-dev.svg?branch=master)](https://travis-ci.org/xybu/onedrived-dev)
[![License](https://img.shields.io/github/license/xybu/onedrived-dev.svg "MIT License")](LICENSE)
[![Coverage Status](https://coveralls.io/repos/github/xybu/onedrived-dev/badge.svg)](https://coveralls.io/github/xybu/onedrived-dev)
[![Code Climate](https://codeclimate.com/github/xybu/onedrived-dev/badges/gpa.svg)](https://codeclimate.com/github/xybu/onedrived-dev)

## Introduction

IN DEVELOPMENT. DO NOT USE.

## Pre-requisites

It's strongly recommended that you
[install the latest PIP](https://pip.pypa.io/en/stable/installing/#installing-with-get-pip-py)
so that `onedrived` and its Python dependencies can be installed and removed with ease:

```bash
# Assuming you already have Python 3.x installed.

# Check the version of your Python3 interpreter.
$ python3 --version

# Download and install PIP from source.
$ wget -O- https://bootstrap.pypa.io/get-pip.py | sudo python3

# Upgrade PIP and its dependencies (e.g., setuptools).
$ sudo pip3 -U install pip
```

`onedrived`, written in Python 3, uses [Keyring](https://pypi.python.org/pypi/keyring) to store
account credentials, and [inotifytools](https://github.com/rvoicilas/inotify-tools/wiki) to
monitor file system changes. This requires that your Linux has the following non-Python packages
installed (assuming Ubuntu; names may vary on other distros):

```
gcc
python3-dev
libssl-dev
inotifytools
```

Keyring provides secure storage for your OneDrive credentials (the leak of which may result in
total compromise of your OneDrive data), but may require additional packages (for example, D-Bus
or FreeDesktop Secret Service) depending on your Linux distro and desktop manager. Please refer
to its [installation instructions](https://pypi.python.org/pypi/keyring#installation-instructions)
for more details.

Python-based pre-requisites are listed in `requirements.txt` and can be easily installed by PIP.

## Installation

To install `onedrived`, make sure old versions of `onedrived` are uninstalled, then install all pre-requisite packages
and install `onedrived` using PIP3. The following instructions assume Ubuntu 16.04.

### Uninstall old `onedrived`

If you have old versions of `onedrived` in system, please uninstall it before proceeding:

```bash
$ sudo pip3 uninstall onedrive_d
$ rm -rf ~/.onedrive ~/.onedrived
```

### Install Pre-requisites

```bash
# Install gcc and other C-level pre-requisites.
$ sudo apt install build-essential python3-dev libssl-dev inotifytools

# Install pip3.
$ wget -O- https://bootstrap.pypa.io/get-pip.py | sudo python3
```

### Install `onedrived`

You can either install `onedrived` by `pip3` or pull the code and install manually.

To install latest `onedrived` from source with `pip3`:

```bash
# Remove "--user" to install onedrived system-wide.
$ pip3 install --user git+ssh://git@github.com/xybu/onedrived-dev.git
```

OR you can manually pull the code and install it:

```bash
$ git clone https://github.com/xybu/onedrived-dev.git
$ cd onedrived-dev
$ ./setup.py install --user
```

## Usage

Not usable yet.

## Uninstallation

Use `pip3` to uninstall `onedrived` from system:

```bash
$ pip3 uninstall onedrived
```

If `--user` argument was not used when installing (that is, `onedrived` was installed as a system-level package), you
will need root permission to run the command above.

## License

MIT License.
