#!/usr/bin/env python3

import os
import sys
import click

from __init__ import __version__
import od_auth
import od_context


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


context = load_context()


@click.group(context_settings=dict(help_option_names=['-h', '--help']))
@click.version_option(__version__)
def main():
    pass


@click.command(name='auth', short_help='Add a new OneDrive account to onedrived.')
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
        code_bold_str = '"' + click.style("code=", bold=True) + '"'
        click.echo('When the address bar shows a URL containing ' + code_bold_str + ', paste the part after ' + code_bold_str + ' here.')
        code = click.prompt('Paste code here', type=str)
    click.echo(code)


@click.command(name='edit', short_help='Edit preferences for an existing account in onedrived.')
def edit_account():
    click.echo('edit!')


@click.command(name='del', short_help='De-authorize and delete an existing account from onedrived.')
def delete_account():
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
    main.add_command(authenticate_account)
    main.add_command(edit_account)
    main.add_command(delete_account)
    main.add_command(change_config)
    change_config.add_command(set_proxy)
    change_config.add_command(del_proxy)
    main()
