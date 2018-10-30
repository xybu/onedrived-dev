# onedrive_client-dev

[![GitHub version](https://badge.fury.io/gh/derrix060%2FonedriveClient.svg)](https://badge.fury.io/gh/derrix060%2FonedriveClient)
[![Build Status](https://travis-ci.org/derrix060/onedriveClient.svg?branch=master)](https://travis-ci.org/derrix060/onedriveClient)
[![Dependency Status](https://www.versioneye.com/user/projects/5acb32c50fb24f39e74fbb7d/badge.svg?style=flat-square)](https://www.versioneye.com/user/projects/5acb32c50fb24f39e74fbb7d)
[![License](https://img.shields.io/github/license/derrix060/onedriveClient.svg "MIT License")](LICENSE)
[![codecov](https://codecov.io/gh/derrix060/onedriveClient/branch/master/graph/badge.svg)](https://codecov.io/gh/derrix060/onedriveClient)
[![Coverage Status](https://coveralls.io/repos/github/derrix060/onedriveClient/badge.svg)](https://coveralls.io/github/derrix060/onedriveClient)
[![Code Climate](https://codeclimate.com/github/derrix060/onedriveClient/badges/gpa.svg)](https://codeclimate.com/github/derrix060/onedriveClient)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/9c0ff0f7b1e64120bcd66dc2e72f932e)](https://www.codacy.com/app/derrix060/onedriveClient?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=derrix060/onedriveClient&amp;utm_campaign=Badge_Grade)



## Introduction

`onedrive_client` is a client program for [Microsoft OneDrive](https://onedrive.com)
for Linux. It enables you to sync local directories with remote OneDrive
repositories (a.k.a., _"Drive"_) of one or more OneDrive  Personal account
(OneDrive for Business accounts are in beta tests, use with caution!).

The program is written in Python3, and uses
[official OneDrive Python SDK](https://github.com/OneDrive/onedrive-sdk-python)
to communicate with OneDrive server,
[Keyring](https://pypi.python.org/pypi/keyring) to securely store account
credentials, and [Linux inotify API](https://linux.die.net/man/7/inotify) to
monitor file system changes.

**IN DEVELOPMENT. USE WITH CAUTION.**

## Installation

To install `onedrive_client`, install all pre-requisite packages, make sure old
versions of `onedrive_client` are uninstalled, and lastly install `onedrive_client`.
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

To run on Raspbery PI 3, is necessary add more packages.
```bash
$ sudo apt-get install python3 build-essential python3-dev libssl-dev inotify-tools python3-dbus libffi-dev dbus-devel libdbus-glib-1-dev -y
$ sudo pip3 install pydbus
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

On other distros like Fedora, names of those packages may vary.

Note that `keyring`, which provides secure local storage for OneDrive
credentials (the leak of which may result in total compromise of your OneDrive
data), may require additional packages (for example, D-Bus or FreeDesktop
Secret Service) depending on your Linux distro and desktop manager. Please
refer to its
[installation instructions](https://pypi.python.org/pypi/keyring#installation-instructions)
for more details. If your environment requires `keyring.alt` package, make
sure to use the latest version (`sudo pip3 install -U keyrings.alt`).

To install those dependencies on Ubuntu, use `apt-get` command:

 ```bash
 # Install gcc and other C-level pre-requisites.
 $ sudo apt install build-essential python3-dev libssl-dev inotify-tools python3-dbus libdbus-1-dev libdbus-glib-1-dev
 
 # Install keyring to store the passwords
 $ sudo apt install gnome-keyring
 $ eval `gnome-keyring-daemon`
 $ eval `dbus-launch`

 # install ngrok from own website (ngrok.com) and install in /usr/local/bin
 # Don't install ngrok with sudo apt-get install ngrok-client, it does not install the 'good' ngrok!
 ```

Python-level pre-requisites are listed in `requirements.txt` and will be
installed automatically when installing `onedrive_client`.

### Uninstall older `onedrive_client`

If you have old versions of `onedrive_client` (also named `onedrive-d` in the
past) in system, please uninstall them before proceeding. The packages
can be easily removed with `pip`.

```bash
# Remove Python packages of older onedrive-d.
$ sudo pip3 uninstall onedrive_d onedrive_client

# Remove useless config files.
$ rm -rf ~/.onedrive ~/.onedrive_client
```

### Install `onedrive_client`

You can either install `onedrive_client` by `pip3` or pull the code and install
manually. Note that you may want to check out this repository regularly to
have the latest version installed, and run the included tests to see whether
`onedrive_client` can actually run on your setup.

#### Install from PyPI with `pip`

`onedrive_client` is not yet available on PyPI.

#### Install from source with `pip` (recommended)

To install latest `onedrive_client` from source with `pip3`, run the command below.

Notes:

1. `git` must be installed on the system.
2. To install onedrive_client system-wide (that is, make onedrive_client program available
to all users in the OS), remove argument `--user` from the command).

```bash
$ pip3 install --user git+https://github.com/derrix060/onedriveClient.git
```

#### Install from source manually

First pull the code from GitHub repository:

```bash
$ git clone https://github.com/derrix060/onedriveClient.git
$ cd onedrive_client-dev

```

You may want to run the included tests before installing with one of the
following commands:

```bash
# Use the built-in test driver of Python.
$ python3 ./setup.py test

# Or use py.test if you have it installed.
$ python3 -m pytest
```

Then install `onedrive_client` with one of the following command:

```bash
# Use pip to install onedrive_client.
$ pip3 install -e .

# Or use the built-in setuptools package from Python.
$ python3 ./setup.py install --user
```

## Usage

`onedrive_client` exposes two commands -- `onedrive_client` and `onedrive_client-pref`. The
former is the "synchronizer" and the latter is the "configurator". If you
want to run it directly in code repository without installing the package, in
the following example commands replace `onedrive_client` with
`python3 -m onedrive_client.od_main` and replace `onedrive_client-pref` with
`python3 -m onedrive_client.od_pref`.

### Configure `onedrive_client`

Before running `onedrive_client` for the first time, or whenever you need to change
the configurations, you will need to use `onedrive_client-pref` command. The
subsections that follow introduces the basic usage scenarios. For more usage
scenarios, refer to "More Usages" section.

To read the complete usage of `onedrive_client-pref`, use argument `--help`:

```bash
$ onedrive_client-pref --help
Usage: od_pref.py [OPTIONS] COMMAND [ARGS]...

Options:
  --version   Show the version and exit.
  -h, --help  Show this message and exit.

Commands:
  account  Add new OneDrive account to onedrive_client, list all existing ones, or
           remove some.
  config   Modify config (e.g., proxies, intervals) for current user.
  drive    List all remote OneDrive repositories (Drives) of linked accounts,
           add new Drives to sync, edit configurations of existing Drives, or
           remove a Drive from local list.
```

#### Authorizing accounts

Operations related to configuring accounts can be listed by command
`onedrive_client-pref account`

```bash
$ onedrive_client-pref account --help
Usage: od_pref.py account [OPTIONS] COMMAND [ARGS]...

Options:
  -h, --help  Show this message and exit.

Commands:
  add   Add a new OneDrive account to onedrive_client.
  del   De-authorize and delete an existing account from onedrive_client.
  list  List all linked accounts.
```

To add an OneDrive account to `onedrive_client`, you will need command
`onedrive_client-pref account add`. Help message for this command is as follows:

```bash
$ onedrive_client-pref account add --help
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
Microsoft Account and authorize `onedrive_client` to access your OneDrive data. The
web page will eventually land to a blank page whose URL starts with
"https://login.live.com/oauth20_desktop.srf". Paste this URL
(a.k.a., _callback URL_) back to the program.

Note that `onedrive_client` needs your basic account information (e.g., email
address) to distinguish different accounts (otherwise OneDrive returns
"tokens" from which you cannot tell which account they stand for).

```bash
$ onedrive_client-pref account add

NOTE: To better manage your OneDrive accounts, onedrive_client needs permission to access your account info (e.g., email
address to distinguish different accounts) and read/write your OneDrive files.

Paste this URL into your browser to sign in and authorize onedrive_client:

https://login.live.com/oauth20_authorize.srf?response_type=code&scope=wl.signin+wl.emails+wl.offline_access+
onedrive.readwrite&client_id=000000004010C916&redirect_uri=https%3A%2F%2Flogin.live.com%2Foauth20_desktop.srf

The authentication web page will finish with a blank page whose URL starts with
"https://login.live.com/oauth20_desktop.srf". Paste this URL here.
Paste URL here: https://login.live.com/oauth20_desktop.srf?code=<some_code_here>&lc=1033

Successfully authorized onedrive_client.
Successfully added account for Xiangyu Bu (xybu92@live.com, <account_id_token>)!

All OneDrive accounts associated with user "xb":

  #  Account ID          Owner Name    Email Address
---  ------------------  ------------  ---------------
  0  <account_id_token>  Xiangyu Bu    xybu92@live.com
```

###### One Drive for Business Support
Be careful, it's still on beta test. As explained before, the onedrive needs some informations. In case of Business, it needs to use 2 different services, one of them to do the background tasks (add, remove, rename some item) and another one just to get your name and email. That's why you need to authenticate in two different services.

To add a business account, just insert the tag '-b' at end:

```bash
$ onedrive_client-pref account add -b
```

As happen in normal account, you need to click on link showed and copy the entire link (not only the code!!), but as explained before, you need to do this twice (one for each service).

##### Command mode

Instead of giving the sign-in URL and then prompting for the callback URL, use
the following command to get the sign-in URL:

```bash
$ onedrive_client-pref account add --get-auth-url
NOTE: To better manage your OneDrive accounts, onedrive_client needs permission to access your account info (e.g., email
address to distinguish different accounts) and read/write your OneDrive files.

Paste this URL into your browser to sign in and authorize onedrive_client:

https://login.live.com/oauth20_authorize.srf?response_type=code&client_id=000000004010C916&redirect_uri=https%3A%2F%2F
login.live.com%2Foauth20_desktop.srf&scope=wl.signin+wl.emails+wl.offline_access+onedrive.readwrite
```

Visit the URL and do the same steps as interactive mode until you get the
blank page. Copy the URL and copy the `code` parameter from the URL. For
example, in URL
`https://login.live.com/oauth20_desktop.srf?code=<some_code_here>&lc=1033`,
find the part `?code=<some_code_here>&` and the code is the part
`<some_code_here>`.

Use command `onedrive_client-pref account add --code <some_code_here>`, where
`<some_code_here>` is the code, to add your account.

#### Adding Drives to `onedrive_client`

After you authorize `onedrive_client` to access your OneDrive data, you are now able
to add Drives. Each OneDrive account has one or more Drive associated, and
`onedrive_client` allows you to choose which Drive to sync. Similar to the step of
authorizing `onedrive_client`, the CLI provides both interactive mode and command
mode.

#### Interactive mode

```bash
$ onedrive_client-pref drive set
Reading drives information from OneDrive server...

All available Drives of authorized accounts:

  #  Account Email    Drive ID          Type      Quota                        Status
---  ---------------  ----------------  --------  ---------------------------  --------
  0  <some_email>     <some_drive_id>   personal  5.3 GB Used / 33.0 GB Total  active

Please enter row number of the Drive to add or modify (CTRL+C to abort): 0

Going to add/edit Drive "<some_drive_id>" of account "<some_email>"...
Enter the directory path to sync with this Drive [/home/xb/OneDrive]:  
Syncing with directory "/home/xb/OneDrive"? [y/N]: y
Enter the path to ignore file for this Drive [/home/xb/.config/onedrive_client/ignore_v2.txt]: 

Successfully configured Drive <some_drive_id> of account <some_email> (<some_user_id>):
  Local directory: /home/xb/OneDrive
  Ignore file path: /home/xb/.config/onedrive_client/ignore_v2.txt
```

If you have more than one account authorized, all drives of all authorized
accounts will appear in the table.

#### Command mode

Please find the available command-line arguments from help message using
command `onedrive_client-pref drive set --help`. 

### Set up webhook

#### Webhook explained

For now, refer to issue #19. More details TBA.

#### Using `ngrok`-based webhook

Download and install [ngrok](https://ngrok.com).

By default, `onedrive_client` will look for `ngrok` binary from `PATH`. To specify
path to the binary manually, set up environment variable `NGROK` when running
`onedrive_client`. For example, `NGROK=~/utils/ngrok onedrive_client start --debug`.

To use a custom config file for `ngrok`, set environment variable
`NGROK_CONFIG_FILE` to path of your desired config file. Note that `onedrive_client`
will create a HTTPS tunnel automatically and there is no need to specify
tunnels. The purpose of using a custom `ngrok` config file should be to adjust
resource usage, or link `ngrok` process with your paid `ngrok` account. The
default `ngrok` config file shipped with `onedrive_client` turns off terminal output
of `ngrok` and disables inspection database.

#### Using direct connection

TBA. Not applicable to most end-user machines.

### Run `onedrive_client` in debug mode

Use argument `--debug` so that `onedrive_client` runs in debug mode, using
debug-level log verbosity and printing log to `stderr`.

```bash
onedrive_client start --debug
```

To stop `onedrive_client` process which is running in debug mode, send `SIGINT` to
the process or hitting CTRL+C if it runs in a terminal.

### Run `onedrive_client` as daemon

It's suggested that you set up a log file before running in daemon mode:

```
$ onedrive_client-pref config set logfile_path PATH_TO_SOME_WRITABLE_FILE
```

To start the program as daemon,

```bash
onedrive_client start
```

To stop the daemon,

```bash
onedrive_client stop
```

or send `SIGTERM` to the process (Ctrl + C).

### More Usages

#### Run `onedrive_client` with proxies

`onedrive_client` follows behavior of standard Python library function
[`getproxies()`](https://docs.python.org/3/library/urllib.request.html#urllib.request.getproxies)
to read proxies information from the OS. That is, run the command with
environment variable `HTTP_PROXY` (or `http_proxy`) to set up a HTTP proxy, and
variable `HTTPS_PROXY` (or `https_proxy`) to set up a HTTPS proxy. For example,

```bash
$ HTTPS_PROXY=https://user:pass@host:port/some_path onedrive_client start --debug
```

A HTTPS proxy must have a verifiable SSL certificate.

#### List all authorized OneDrive accounts

#### Remove an authorized account

#### List all remote Drives

#### Edit configuration of an existing Drive

#### Edit ignore list (selective sync)

#### Remove a Drive from `onedrive_client`

##### Interactive mode

```bash
$ onedrive_client-pref drive del
Drives that have been set up:

 #0 - Drive "<some_drive_id_here>":
   Account:     <some_account_email> (<some_user_id_here>)
   Local root:  /home/xb/OneDrive
   Ignore file: /home/xb/.config/onedrive_client/ignore_v2.txt

Please enter the # number of the Drive to delete (CTRL+C to abort): 0
Continue to delete Drive "<some_drive_id_here>" (its local directory will NOT be deleted)? [y/N]: y
Successfully deleted Drive "<some_drive_id_here>" from onedrive_client.
```

##### Command mode

The command-mode equivalent is:

```bash
onedrive_client-pref drive del --drive-id <some_drive_id_here> [--yes]
```

If argument `--yes` is used, the specified Drive, if already added, will be
deleted without confirmation. 

#### Adjusting parameters of `onedrive_client`

#### Check latest version of `onedrive_client`

## Uninstallation

Use `pip3` to uninstall `onedrive_client` from system:

```bash
$ pip3 uninstall onedrive_client
```

If `--user` argument was not used when installing (that is, `onedrive_client` was
installed as a system-level package), you will need root permission to run
the command above.

## License

MIT License.
