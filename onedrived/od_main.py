#!/usr/bin/env python3

import logging

import click
import keyring
import tabulate

from .od_pref import load_context, save_context, get_keyring_key


context = load_context()


def verbosity_to_log_level(v):
    return max(logging.NOTSET, logging.WARNING - 10 * v)


@click.command()
@click.option('-v', '--verbose', count=True)
def main(verbose):
    print(verbosity_to_log_level(verbose))


if __name__ == '__main__':
    main()
