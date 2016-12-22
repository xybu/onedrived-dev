#!/usr/bin/env python3

import os
import sys
import urllib
import click
import tabulate

from __init__ import __version__
import od_auth
import od_context
from od_api_session import OneDriveAPISession


def get_keyring_key(account_id):
    return OneDriveAPISession.KEYRING_ACCOUNT_KEY_PREFIX + account_id


def load_context():
    context = od_context.UserContext()
    try:
        context.load_config(context.DEFAULT_CONFIG_FILENAME)
    except OSError as e:
        context.logger.error('Failed to load config file: %s.' % str(e))
    return context


def save_context(context):
    try:
        context.save_config(context.DEFAULT_CONFIG_FILENAME)
    except OSError as e:
        context.logger.error('Failed to save config file: %s. Changes were discarded.' % str(e))


def print_all_accounts(context):
    all_accounts = [('#', 'Account ID', 'Owner Name')]
    for i, account_id in enumerate(context.all_accounts()):
        all_accounts.append((click.style(str(i), bold=True), account_id, context.get_account(account_id)))
    print(tabulate.tabulate(all_accounts, headers='firstrow'))


context = load_context()


@click.group(context_settings=dict(help_option_names=['-h', '--help']))
@click.version_option(__version__)
def main():
    pass


@click.group(name='account',
             short_help='Add new OneDrive account to onedrived, list all existing ones, or remove some.')
def change_account():
    pass


@click.command(name='add', short_help='Add a new OneDrive account to onedrived.')
@click.option('--get-auth-url', '-u', is_flag=True, default=False, required=False,
              help='If set, print the authentication URL and exit.')
@click.option('--code', '-c', type=str, required=False, default=None,
              help='Skip interactions and try authenticating with the code directly.')
@click.option('--for-business', '-b', is_flag=True, default=False, required=False,
              help='If set, add an OneDrive for Business account.')
def authenticate_account(get_auth_url=False, code=None, for_business=False):
    if for_business:
        click.echo(click.style('OneDrive for Business is not yet supported.', fg='red'))
        return
    authenticator = od_auth.OneDriveAuthenticator(proxies=context.config['proxies'])
    if code is None:
        click.echo('Paste this URL into your browser to sign in and approve onedrived to access your files:')
        click.echo('\n' + click.style(authenticator.get_auth_url(), underline=True) + '\n')
        if get_auth_url:
            return
        click.echo('The authentication web page will finish with a blank page whose URL starts with ' +
                   '"' + click.style(authenticator.APP_REDIRECT_URL, bold=True) + '". Paste this URL here.')
        url = click.prompt('Paste URL here', type=str)
        if url is not None and '?' in url:
            qs_dict = urllib.parse.parse_qs(url.split('?')[1])
            if 'code' in qs_dict:
                code = qs_dict['code']
        if code is None:
            click.echo(click.style('Error: did not find authorization code in URL.', fg='red'))
            return
    try:
        authenticator.authenticate(code)
        click.echo(click.style('Successfully authenticated onedrived.', fg='green'))
    except Exception as e:
        click.echo(click.style('Failed to authorize onedrived: %s. ' % str(e), fg='red'))
    try:
        account_profile = authenticator.get_profile()
        authenticator.save_session(key=get_keyring_key(account_profile.user_id))
        context.add_account(account_profile.user_id, account_profile.user_name)
        save_context(context)
        click.echo(click.style(
            'Successfully added account for %s (%s)!' % (account_profile.user_name, account_profile.user_id),
            fg='green'))
    except Exception as e:
        click.echo(click.style('Failed to save account info: %s. ' % str(e), fg='red'))

@click.command(name='list', short_help='List all linked accounts.')
def list_accounts():
    click.echo('All OneDrive accounts associated with user "%s":\n' % context.user_name)
    print_all_accounts(context)


@click.command(name='del', short_help='De-authorize and delete an existing account from onedrived.')
@click.option('--yes', '-y', is_flag=True, default=False, required=False,
              help='If set, do not ask for confirmation but simply delete if account exists.')
@click.option('--index', '-i', type=int, required=False, default=None,
              help='Specify the account to delete by row index in account list table.')
@click.option('--account-id', '-u', type=str, required=False, default=None,
              help='Specify the account to delete by account ID shown in account list table.')
def delete_account(yes=False, index=None, account_id=None):
    click.echo('del!')


@click.group(name='config', short_help='Modify config (e.g., proxies, intervals) for current user.')
def change_config():
    pass


@click.command(name='set-proxy',
               short_help='Use proxy to connect to OneDrive server. ' +
                          'If a proxy of the same protocol has been set, the old proxy will be replaced.' +
                          'Specify proxy by URLs such as "https://localhost:8888".')
@click.argument('url', type=str)
def set_proxy(url):
    if '://' not in url:
        click.echo(click.style('Invalid proxy URL. Use format like "https://localhost:8888".', fg='red'))
    else:
        protocol, host = url.split('://', maxsplit=1)
        protocol = protocol.lower()
        if protocol not in context.SUPPORTED_PROXY_PROTOCOLS:
            click.echo(click.style('Unsupported proxy protocol: "%s". ' % protocol, fg='red'))
            click.echo(click.style('Supported protocols are: %s.' % context.SUPPORTED_PROXY_PROTOCOLS, fg='red'))
        else:
            context.config['proxies'][protocol] = url
            click.echo(click.style('Successfully saved proxy "%s".' % url, fg='green'))
            save_context(context)


@click.command(name='del-proxy',
               short_help='Delete a previously added proxy from config. For example, to delete ' +
                          'proxy "https://localhost:8888", use "https" in argument "protocol".')
@click.argument('protocol', type=click.Choice((context.SUPPORTED_PROXY_PROTOCOLS)))
def del_proxy(protocol):
    if protocol.lower() in context.config['proxies']:
        del context.config['proxies'][protocol.lower()]
        click.echo(click.style('Successfully deleted proxy for protocol "%s"' % protocol, fg='green'))
        save_context(context)
    else:
        click.echo(click.style('Proxy for protocol "%s" is not set.' % protocol, fg='red'))


if __name__ == '__main__':
    change_account.add_command(authenticate_account)
    change_account.add_command(list_accounts)
    change_account.add_command(delete_account)
    change_config.add_command(set_proxy)
    change_config.add_command(del_proxy)
    main.add_command(change_account)
    main.add_command(change_config)
    main()
