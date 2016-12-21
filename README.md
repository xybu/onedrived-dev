# onedrived-dev

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

`onedrived`, written in Python 3, uses [`Keyring](https://pypi.python.org/pypi/keyring) to store
account credentials, and [inotifytools](https://github.com/rvoicilas/inotify-tools/wiki) to
monitor file system changes. This requires that your Linux has the following non-Python packages
installed (assuming Ubuntu; names may vary on other distros):

```
gcc
python3-dev
libssl-dev
inotify-tools
```

Keyring provides secure storage for your OneDrive credentials (the leak of which may result in
total compromise of your OneDrive data), but may require additional packages (for example, D-Bus
or FreeDesktop Secret Service) depending on your Linux distro and desktop manager. Please refer
to its [installation instructions](https://pypi.python.org/pypi/keyring#installation-instructions)
for more details.

## License

MIT License.
