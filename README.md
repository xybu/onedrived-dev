# onedrived-dev

[![Build Status](https://travis-ci.org/xybu/onedrived-dev.svg?branch=master)](https://travis-ci.org/xybu/onedrived-dev)
[![License](https://img.shields.io/github/license/xybu/onedrived-dev.svg "MIT License")](LICENSE)
[![Coverage Status](https://coveralls.io/repos/github/xybu/onedrived-dev/badge.svg)](https://coveralls.io/github/xybu/onedrived-dev)
[![Code Climate](https://codeclimate.com/github/xybu/onedrived-dev/badges/gpa.svg)](https://codeclimate.com/github/xybu/onedrived-dev)

## Introduction

`onedrived` is a client program for [Microsoft OneDrive](https://onedrive.com) for Linux. It enables you to sync local directories with remote OneDrive repositories (aka., "Drive") of one or more OneDrive  Personal account (OneDrive for Business accounts are not yet supported. See #1).

The program is written in Python3, and uses [official OneDrive Python SDK](https://github.com/OneDrive/onedrive-sdk-python) to communicate with OneDrive server, [Keyring](https://pypi.python.org/pypi/keyring) to securely store account credentials, and [Linux inotify API](https://linux.die.net/man/7/inotify) to monitor file system changes.

**IN DEVELOPMENT. DO NOT USE.**

## Installation

To install `onedrived`, install all pre-requisite packages, make sure old versions of `onedrived` are uninstalled, and lastly install `onedrived`. Each of those steps will be addressed in following subsections.

The guide that follows will assume an environment with Python3 interpreter installed. To check the version of your Python3 interpreter, run command

```bash
$ python3 --version
```

If `python3` command is not found, or its version is below `3.3`, please install the latest `python3` package.
For example, on Ubuntu

```bash
$ sudo apt-get install python3
```

It's strongly suggested that you [use the latest PIP](https://pip.pypa.io/en/stable/installing/#installing-with-get-pip-py) to manage Python package dependencies. To get the latest `pip` from source, run command

```bash
# Download pip installation script from official site using wget.
$ wget -O- https://bootstrap.pypa.io/get-pip.py | sudo python3
# Upgrade the components (e.g., setuptools) to latest version.
$ sudo pip3 install -U pip setuptools
```

### Pre-requisites

The use of low-level tools and APIs like `inotify` and `keyring` introduces low-level dependencies that need to be installed manually. On Ubuntu the following packages are needed:

* `gcc`
* `python3-dev`
* `libssl-dev`
* `inotify-tools`
* `python3-dbus` (or probably `libdbus-glib-1-dev`)

On other distros like Fedora names of those packages may vary.

Note that `keyring`, which provides secure local storage for OneDrive credentials (the leak of which may result in total compromise of your OneDrive data), may require additional packages (for example, D-Bus
or FreeDesktop Secret Service) depending on your Linux distro and desktop manager. Please refer to its [installation instructions](https://pypi.python.org/pypi/keyring#installation-instructions) for more details.

To install those dependencies on Ubuntu, use `apt-get` command:

```bash
# Install gcc and other C-level pre-requisites.
$ sudo apt-get install build-essential python3-dev libssl-dev inotify-tools python3-dbus
```

Python-level pre-requisites are listed in `requirements.txt` and will be installed automatically when installing `onedrived`.

### Uninstall older `onedrived`

If you have old versions of `onedrived` (also named `onedrive-d` in the past) in system, please uninstall them before proceeding. The packages can be easily removed with `pip`.

```bash
# Remove Python packages of older onedrive-d.
$ sudo pip3 uninstall onedrive_d onedrived

# Remove useless config files.
$ rm -rf ~/.onedrive ~/.onedrived
```

### Install `onedrived`

You can either install `onedrived` by `pip3` or pull the code and install manually.
Note that you may want to check out this repository regularly to have the latest version installed, and run
the included tests to see whether `onedrived` can actually run on your setup.

#### Install from PyPI with `pip`

`onedrived` is not yet available on PyPI.

#### Install from source with `pip` (recommended)

To install latest `onedrived` from source with `pip3`, run the command below.

Notes:

 1. `git` must be installed on the system.
 2. To install onedrived system-wide (that is, make onedrived program available to all users in the OS), remove argument `--user` from the command).

```bash
$ pip3 install --user git+https://github.com/xybu/onedrived-dev.git
```

#### Install from source manually

First pull the code from GitHub repository:

```bash
$ git clone https://github.com/xybu/onedrived-dev.git
$ cd onedrived-dev

```

You may want to run the included tests before installing with one of the following commands:

```bash
# Use the built-in test driver of Python.
$ python3 ./setup.py test

# Or use py.test if you have it installed.
$ python3 -m pytest
```

Then install `onedrived` with one of the following command:

```bash
# Use pip to install onedrived.
$ pip3 install -e .

# Or use the built-in setuptools package from Python.
$ python3 ./setup.py install --user
```

## Usage

Not usable yet.

### Configure `onedrived`

#### Authorizing accounts

#### Adding Drives to `onedrived`

#### Adjusting parameters of `onedrived`

### Run `onedrived` in debug mode

### Run `onedrived` as daemon

## Uninstallation

Use `pip3` to uninstall `onedrived` from system:

```bash
$ pip3 uninstall onedrived
```

If `--user` argument was not used when installing (that is, `onedrived` was installed as a system-level package), you
will need root permission to run the command above.

## License

MIT License.
