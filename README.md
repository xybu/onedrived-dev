# onedrived-dev

[![GitHub version](https://badge.fury.io/gh/xybu%2Fonedrived-dev.svg)](https://badge.fury.io/gh/xybu%2Fonedrived-dev)
[![Build Status](https://travis-ci.org/xybu/onedrived-dev.svg?branch=master)](https://travis-ci.org/xybu/onedrived-dev)
[![Dependency Status](https://www.versioneye.com/user/projects/587f9689452b83003d3c8fd3/badge.svg)](https://www.versioneye.com/user/projects/587f9689452b83003d3c8fd3)
[![License](https://img.shields.io/github/license/xybu/onedrived-dev.svg "MIT License")](LICENSE)
[![Coverage Status](https://coveralls.io/repos/github/xybu/onedrived-dev/badge.svg)](https://coveralls.io/github/xybu/onedrived-dev)
[![Code Climate](https://codeclimate.com/github/xybu/onedrived-dev/badges/gpa.svg)](https://codeclimate.com/github/xybu/onedrived-dev)

## Introduction

`onedrived` is a client program for [Microsoft OneDrive](https://onedrive.com)
for Linux. It enables you to sync local directories with remote OneDrive
repositories (a.k.a., _"Drive"_) of one or more OneDrive  Personal account
(OneDrive for Business accounts are not yet supported. See #1).

The program is written in Python3, and uses
[official OneDrive Python SDK](https://github.com/OneDrive/onedrive-sdk-python)
to communicate with OneDrive server,
[Keyring](https://pypi.python.org/pypi/keyring) to securely store account
credentials, and [Linux inotify API](https://linux.die.net/man/7/inotify) to
monitor file system changes.

**IN DEVELOPMENT. DO NOT USE.**

## Installation

To install `onedrived`, install all pre-requisite packages, make sure old
versions of `onedrived` are uninstalled, and lastly install `onedrived`.
Each of those steps will be addressed in following subsections.

The guide that follows will assume an environment with Python3 interpreter
installed. To check the version of your Python3 interpreter, run command

```bash
$ python3 --version
Python 3.5.2
```

If `python3` command is not found, or its version is below `3.3`, please
install the latest `python3` package. For example, on Ubuntu

```bash
$ sudo apt-get install python3
```

It's strongly suggested that you
[use the latest PIP](https://pip.pypa.io/en/stable/installing/#installing-with-get-pip-py)
to manage Python package dependencies. To get the latest `pip` from source,
run command

```bash
# Download pip installation script from official site using wget.
$ wget -O- https://bootstrap.pypa.io/get-pip.py | sudo python3
# Upgrade the components (e.g., setuptools) to latest version.
$ sudo pip3 install -U pip setuptools
```

### Pre-requisites

The use of low-level tools and APIs like `inotify` and `keyring` introduces
low-level dependencies that need to be installed manually. On Ubuntu the
following packages are needed:

* `gcc`
* `python3-dev`
* `libssl-dev`
* `inotify-tools`
* `python3-dbus` (or probably `libdbus-glib-1-dev`)

On other distros like Fedora names of those packages may vary.

Note that `keyring`, which provides secure local storage for OneDrive
credentials (the leak of which may result in total compromise of your OneDrive
data), may require additional packages (for example, D-Bus or FreeDesktop
Secret Service) depending on your Linux distro and desktop manager. Please
refer to its
[installation instructions](https://pypi.python.org/pypi/keyring#installation-instructions)
for more details.

To install those dependencies on Ubuntu, use `apt-get` command:

```bash
# Install gcc and other C-level pre-requisites.
$ sudo apt-get install build-essential python3-dev libssl-dev inotify-tools python3-dbus
```

Python-level pre-requisites are listed in `requirements.txt` and will be
installed automatically when installing `onedrived`.

### Uninstall older `onedrived`

If you have old versions of `onedrived` (also named `onedrive-d` in the
past) in system, please uninstall them before proceeding. The packages
can be easily removed with `pip`.

```bash
# Remove Python packages of older onedrive-d.
$ sudo pip3 uninstall onedrive_d onedrived

# Remove useless config files.
$ rm -rf ~/.onedrive ~/.onedrived
```

### Install `onedrived`

You can either install `onedrived` by `pip3` or pull the code and install
manually. Note that you may want to check out this repository regularly to
have the latest version installed, and run the included tests to see whether
`onedrived` can actually run on your setup.

#### Install from PyPI with `pip`

`onedrived` is not yet available on PyPI.

#### Install from source with `pip` (recommended)

To install latest `onedrived` from source with `pip3`, run the command below.

Notes:

1. `git` must be installed on the system.
2. To install onedrived system-wide (that is, make onedrived program available
to all users in the OS), remove argument `--user` from the command).

```bash
$ pip3 install --user git+https://github.com/xybu/onedrived-dev.git
```

#### Install from source manually

First pull the code from GitHub repository:

```bash
$ git clone https://github.com/xybu/onedrived-dev.git
$ cd onedrived-dev

```

You may want to run the included tests before installing with one of the
following commands:

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

`onedrived` exposes two commands -- `onedrived` and `onedrived-pref`. The
former is the "synchronizer" and the latter is the "configurator". If you
want to run it directly in code repository without installing the package, in
the following example commands replace `onedrived` with
`python3 -m onedrived.od_main` and replace `onedrived-pref` with
`python3 -m onedrived.od_pref`.

### Configure `onedrived`

Before running `onedrived` for the first time, or whenever you need to change
the configurations, you will need to use `onedrived-pref` command. The
subsections that follow introduces the basic usage scenarios. For more usage
scenarios, refer to "More Usages" section.

To read the complete usage of `onedrived-pref`, use argument `--help`:

```bash
$ onedrived-pref --help
Usage: od_pref.py [OPTIONS] COMMAND [ARGS]...

Options:
  --version   Show the version and exit.
  -h, --help  Show this message and exit.

Commands:
  account  Add new OneDrive account to onedrived, list all existing ones, or
           remove some.
  config   Modify config (e.g., proxies, intervals) for current user.
  drive    List all remote OneDrive repositories (Drives) of linked accounts,
           add new Drives to sync, edit configurations of existing Drives, or
           remove a Drive from local list.
```

#### Authorizing accounts

Operations related to configuring accounts can be listed by command
`onedrived-pref account`

```bash
$ onedrived-pref account --help
Usage: od_pref.py account [OPTIONS] COMMAND [ARGS]...

Options:
  -h, --help  Show this message and exit.

Commands:
  add   Add a new OneDrive account to onedrived.
  del   De-authorize and delete an existing account from onedrived.
  list  List all linked accounts.
```

To add an OneDrive account to `onedrived`, you will need command
`onedrived-pref account add`. Help message for this command is as follows:

```bash
$ onedrived-pref account add --help
Usage: od_pref.py account add [OPTIONS]

Options:
  -u, --get-auth-url  If set, print the authentication URL and exit.
  -c, --code TEXT     Skip interactions and try authenticating with the code
                      directly.
  -b, --for-business  If set, add an OneDrive for Business account.
  -h, --help          Show this message and exit.
```

More specifically, the CLI offers two modes to add an account -- _interactive
mode_, in which the CLI guides you step by step, and _command mode_, in which
you provide the information from command line arguments.

##### Interactive mode

In interactive mode, the program will provide you with an URL to visit. Open
this URL with a web browser (e.g., Chrome, Firefox), sign in with your
Microsoft Account and authorize `onedrived` to access your OneDrive data. The
web page will eventually land to a blank page whose URL starts with
"https://login.live.com/oauth20_desktop.srf". Paste this URL
(a.k.a., _callback URL_) back to the program.

Note that `onedrived` needs your basic account information (e.g., email
address) to distinguish different accounts (otherwise OneDrive returns
"tokens" from which you cannot tell which account they stand for).

```bash
$ onedrived-pref account add

NOTE: To better manage your OneDrive accounts, onedrived needs permission to access your account info (e.g., email
address to distinguish different accounts) and read/write your OneDrive files.

Paste this URL into your browser to sign in and authorize onedrived:

https://login.live.com/oauth20_authorize.srf?response_type=code&scope=wl.signin+wl.emails+wl.offline_access+
onedrive.readwrite&client_id=000000004010C916&redirect_uri=https%3A%2F%2Flogin.live.com%2Foauth20_desktop.srf

The authentication web page will finish with a blank page whose URL starts with
"https://login.live.com/oauth20_desktop.srf". Paste this URL here.
Paste URL here: https://login.live.com/oauth20_desktop.srf?code=<some_code_here>&lc=1033

Successfully authorized onedrived.
Successfully added account for Xiangyu Bu (xybu92@live.com, <account_id_token>)!

All OneDrive accounts associated with user "xb":

  #  Account ID          Owner Name    Email Address
---  ------------------  ------------  ---------------
  0  <account_id_token>  Xiangyu Bu    xybu92@live.com
```

##### Command mode

Instead of giving the sign-in URL and then prompting for the callback URL, use
the following command to get the sign-in URL:

```bash
$ onedrived-pref account add --get-auth-url
NOTE: To better manage your OneDrive accounts, onedrived needs permission to access your account info (e.g., email
address to distinguish different accounts) and read/write your OneDrive files.

Paste this URL into your browser to sign in and authorize onedrived:

https://login.live.com/oauth20_authorize.srf?response_type=code&client_id=000000004010C916&redirect_uri=https%3A%2F%2F
login.live.com%2Foauth20_desktop.srf&scope=wl.signin+wl.emails+wl.offline_access+onedrive.readwrite
```

Visit the URL and do the same steps as interactive mode until you get the
blank page. Copy the URL and copy the `code` parameter from the URL. For
example, in URL
`https://login.live.com/oauth20_desktop.srf?code=<some_code_here>&lc=1033`,
find the part `?code=<some_code_here>&` and the code is the part
`<some_code_here>`.

Use command `onedrived-pref account add --code <some_code_here>`, where
`<some_code_here>` is the code, to add your account.

#### Adding Drives to `onedrived`

### Run `onedrived` in debug mode

### Run `onedrived` as daemon

### More Usages

#### List all authorized OneDrive accounts

#### Remove an authorized account

#### List all remote Drives

#### Edit configuration of an existing Drive

#### Remove a Drive from `onedrived`

#### Adjusting parameters of `onedrived`

#### Check latest version of `onedrived`

## Uninstallation

Use `pip3` to uninstall `onedrived` from system:

```bash
$ pip3 uninstall onedrived
```

If `--user` argument was not used when installing (that is, `onedrived` was
installed as a system-level package), you will need root permission to run
the command above.

## License

MIT License.
