#!/usr/bin/env python3

import os
import sys
import urllib
import click
import keyring
import tabulate

from . import __version__
from . import mkdir
from . import od_auth
from . import od_context
from .od_api_session import OneDriveAPISession
from .models import pretty_api
from .models import drive_config


def get_keyring_key(account_id):
    return OneDriveAPISession.KEYRING_ACCOUNT_KEY_PREFIX + account_id


def load_context():
    context = od_context.UserContext()
    try:
        context.load_config(context.DEFAULT_CONFIG_FILENAME)
    except OSError as e:
        context.logger.error('Failed to load config file: %s. Use default.' % e)
    return context


def save_context(context):
    try:
        context.save_config(context.DEFAULT_CONFIG_FILENAME)
    except OSError as e:
        context.logger.error('Failed to save config file: %s. Changes were discarded.' % str(e))


def print_all_accounts(context):
    all_accounts = [('#', 'Account ID', 'Owner Name', 'Email Address')]
    all_account_ids = context.all_accounts()
    for i, account_id in enumerate(all_account_ids):
        account = context.get_account(account_id)
        all_accounts.append((i, account_id, account.account_name, account.account_email))
    click.echo(tabulate.tabulate(all_accounts, headers='firstrow'))
    return all_account_ids


def email_to_account_id(context, email, all_account_ids=None):
    if all_account_ids is None:
        all_account_ids = context.all_accounts()
    for s in all_account_ids:
        account = context.get_account(s)
        if account.account_email == email:
            return s
    raise ValueError('Did not find existing account with email address "%s".' % email)


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
    click.echo('NOTE: To better manage your OneDrive accounts, onedrived needs permission to access your account info '
               '(e.g., email address to distinguish different accounts) and read/write your OneDrive files.\n')
    if code is None:
        click.echo('Paste this URL into your browser to sign in and authorize onedrived:')
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
        click.echo(click.style('Successfully authorized onedrived.', fg='green'))
    except Exception as e:
        click.echo(click.style('Failed to authorize onedrived: %s. ' % str(e), fg='red'))
    try:
        account_profile = authenticator.get_profile(proxies=context.config['proxies'])
        authenticator.save_session(key=get_keyring_key(account_profile.account_id))
        context.add_account(account_profile)
        save_context(context)
        click.echo(click.style('Successfully added account for %s!' % account_profile, fg='green'))
        click.echo('\nAll OneDrive accounts associated with user "%s":\n' % context.user_name)
        print_all_accounts(context)
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
@click.option('--email', '-e', type=str, required=False, default=None,
              help='Specify the account to delete by email address.')
@click.option('--account-id', '-u', type=str, required=False, default=None,
              help='Specify the account to delete by account ID shown in account list table.')
def delete_account(yes=False, index=None, email=None, account_id=None):
    click.echo('All OneDrive accounts associated with user "%s":\n' % context.user_name)
    all_account_ids = print_all_accounts(context)
    click.echo()

    if index is None and email is None and account_id is None:
        # Print account table and ask which account to delete.
        index = click.prompt('Please enter row number of the account to delete (CTRL+C to abort)', type=int)

    if index is not None:
        if isinstance(index, int) and index >= 0 and index < len(all_account_ids):
            account_id = all_account_ids[index]
        else:
            click.echo(click.style('Index is not a valid row number.', fg='red'))
            return

    if email is not None:
        try:
            account_id = email_to_account_id(context, email, all_account_ids)
        except Exception as e:
            click.echo(click.style(e, fg='red'))
            return

    if account_id is not None:
        if account_id not in all_account_ids:
            click.echo(click.style('Account ID "%s" is not found.' % account_id, fg='red'))
            return
        account = context.get_account(account_id)
        prompt_text = 'Are you sure to delete account %s?' % account
        if yes or click.confirm(prompt_text):
            context.delete_account(account_id)
            keyring.delete_password(OneDriveAPISession.KEYRING_SERVICE_NAME, get_keyring_key(account_id))
            save_context(context)
            click.echo(click.style('Successfully deleted account from onedrived.', fg='green'))
        else:
            click.echo('Operation canceled.')


@click.group(name='drive',
             short_help='List all remote OneDrive repositories (Drives) of linked accounts, add new Drives to sync, '
                        'edit configurations of existing Drives, or remove a Drive from local list.')
def change_drive():
    pass


def print_all_drives():
    click.echo('Reading drives information from OneDrive server...\n')
    all_drives = {}
    drive_table = [('#', 'Account Email', 'Drive ID', 'Type', 'Quota', 'Status')]
    for i in context.all_accounts():
        drive_objs = []
        profile = context.get_account(i)
        authenticator = od_auth.OneDriveAuthenticator(proxies=context.config['proxies'])
        try:
            authenticator.load_session(key=get_keyring_key(i))
            drives = authenticator.client.drives.get()
        except RuntimeError:
            # Try to refresh the session.
            authenticator.client.auth_provider.refresh_token()
            authenticator.save_session(key=get_keyring_key(i))
            drives = authenticator.client.drives.get()
        for d in drives:
            drive_objs.append(d)
            drive_table.append((len(drive_table) - 1, profile.account_email,
                                d.id, d.drive_type, pretty_api.pretty_quota(d.quota), d.status.state))
        all_drives[i] = (profile, authenticator, drive_objs)
    click.echo(click.style('All available Drives of authorized accounts:\n', bold=True))
    click.echo(tabulate.tabulate(drive_table, headers='firstrow'))
    return all_drives, drive_table


def print_saved_drives():
    click.echo(click.style('Drives that have been set up:', bold=True))
    all_drive_ids = context.all_drives()
    if len(all_drive_ids) > 0:
        click.echo()
        for i, drive_id in enumerate(all_drive_ids):
            curr_drive_config = context.get_drive(drive_id)
            curr_account = context.get_account(curr_drive_config.account_id)
            click.echo(' ' + click.style('#%d - Drive "%s":' % (i, curr_drive_config.drive_id), underline=True))
            click.echo('   Account:     %s (%s)' % (curr_account.account_email, curr_drive_config.account_id))
            click.echo('   Local root:  %s' % curr_drive_config.localroot_path)
            click.echo('   Ignore file: %s' % curr_drive_config.ignorefile_path)
            click.echo()
    else:
        click.echo(' No Drive has been setup with onedrived.\n')
    return all_drive_ids


def index_to_drive_table_row(index, drive_table):
    if isinstance(index, int) and index >= 0 and index < len(drive_table):
        email = drive_table[index + 1][2]  # Plus one to offset the header row.
        drive_id = drive_table[index + 1][3]
        return email, drive_id
    raise ValueError('Index is not a valid row number.')


@click.command(name='list', short_help='List all available Drives.')
def list_drives():
    try:
        print_all_drives()
        click.echo()
        print_saved_drives()
    except Exception as e:
        click.echo(click.style('Error: %s.' % e, fg='red'))
        return

@click.command(name='set', short_help='Add a remote Drive to sync with local directory or modify an existing one. '
                                      'If either --drive-id or --email is missing, use interactive mode.')
@click.option('--drive-id', '-d', type=str, required=False, default=None,
              help='ID of the Drive.')
@click.option('--email', '-e', type=str, required=False, default=None,
              help='Email of an authorized account.')
@click.option('--local-root', type=str, required=False, default=None,
              help='Path to a local directory to sync with the Drive.')
@click.option('--ignore-file', type=str, required=False, default=None,
              help='Path to an ignore file specific to the Drive.')
def set_drive(drive_id=None, email=None, local_root=None, ignore_file=None):
    try:
        all_drives, drive_table = print_all_drives()
        click.echo()
    except Exception as e:
        click.echo(click.style('Error: %s.' % e, fg='red'))
        return

    interactive = drive_id is None or email is None
    if interactive:
        # Interactive mode to ask for which drive to add.
        index = click.prompt('Please enter row number of the Drive to add or modify (CTRL+C to abort)', type=int)
        try:
            email, drive_id = index_to_drive_table_row(index, drive_table)
        except ValueError as e:
            click.echo(click.style('%s' % e, fg='red'))
            return

    try:
        account_id = email_to_account_id(context, email)
    except Exception as e:
        click.echo(click.style(e, fg='red'))
        return

    # Traverse the Drive objects and see if Drive exists.
    found_drive = False
    for d in all_drives[account_id][2]:
        if drive_id == d.id:
            found_drive = True
            break
    if not found_drive:
        click.echo(click.style('Did not find Drive "%s".' % drive_id, fg='red'))
        return

    # Confirm if Drive already exists.
    drive_exists = drive_id in context.all_drives()
    curr_drive_config = None
    if drive_exists:
        if interactive:
            click.confirm('Drive "%s" is already set. Overwrite its existing configuration?' % drive_id, abort=True)
        curr_drive_config = context.get_drive(drive_id)

    click.echo()
    account_profile = all_drives[account_id][0]
    click.echo(click.style(
        'Going to add/edit Drive "%s" of account "%s"...' %(drive_id, account_profile.account_email), fg='cyan'))

    if interactive:
        local_root = None
        ignore_file = None
        if drive_exists:
            local_root_default = curr_drive_config.localroot_path
            ignore_file_default = curr_drive_config.ignorefile_path
        else:
            local_root_default = context.user_home + '/OneDrive'
            ignore_file_default = context.config_dir + '/' + context.DEFAULT_IGNORE_FILENAME
        while local_root is None:
            local_root = click.prompt('Enter the directory path to sync with this Drive',
                                      type=str, default=local_root_default)
            local_root = os.path.abspath(local_root)
            if not os.path.exists(local_root):
                if click.confirm('Directory "%s" does not exist. Create it?' % local_root):
                    try:
                        mkdir(local_root, context.user_uid)
                    except OSError as e:
                        click.echo(click.style('OSError: %s' % e, fg='red'))
                        local_root = None
            elif not os.path.isdir(local_root):
                click.echo(click.style('Path "%s" should be a directory.' % local_root, fg='red'))
                local_root = None
            elif not click.confirm('Syncing with directory "%s"?' % local_root):
                local_root = None
        while ignore_file is None:
            ignore_file = click.prompt('Enter the path to ignore file for this Drive',
                                       type=str, default=ignore_file_default)
            ignore_file = os.path.abspath(ignore_file)
            if not os.path.isfile(ignore_file):
                click.echo(click.style('Path "%s" is not a file.' % ignore_file, fg='red'))
                ignore_file = None
    else:
        # Non-interactive mode. The drive may or may not exist in config, and the cmdline args may or may not be
        # specified. If drive exists in config, use existing values for missing args. If drive does not exist,
        # local root is required and ignore file is optional (use default if missing).
        try:
            if local_root is None:
                if drive_exists:
                    local_root = curr_drive_config.localroot_path
                else:
                    raise ValueError('Please specify the local directory for the Drive with "--local-root" argument.')
            local_root = os.path.abspath(local_root)
            if not os.path.isdir(local_root):
                raise ValueError('Path "%s" should be an existing directory.' % local_root)
            if ignore_file is None and drive_exists:
                ignore_file = curr_drive_config.ignorefile_path
            if ignore_file is None or not os.path.isfile(ignore_file):
                click.echo(click.style('Warning: ignore file path does not point to a file. Use default.', fg='yellow'))
                ignore_file = context.config_dir + '/' + context.DEFAULT_IGNORE_FILENAME
            if drive_exists and local_root == curr_drive_config.localroot_path and \
                    ignore_file == curr_drive_config.ignorefile_path:
                click.echo(click.style('No parameter was changed. Skipped operation.', fg='yellow'))
                return
        except ValueError as e:
            click.echo(click.style(str(e), fg='red'))
            return

    d = context.add_drive(drive_config.LocalDriveConfig(drive_id, account_id, ignore_file, local_root))
    save_context(context)
    click.echo(click.style('\nSuccessfully configured Drive %s of account %s (%s):' % (
        d.drive_id, account_profile.account_email, d.account_id), fg='green'))
    click.echo('  Local directory: ' + d.localroot_path)
    click.echo('  Ignore file path: ' + d.ignorefile_path)


@click.command(name='del', short_help='Stop syncing a Drive with local directory.')
@click.option('--drive-id', '-d', type=str, required=False, default=None,
              help='ID of the Drive.')
@click.option('--yes', '-y', is_flag=True, default=False, required=False,
              help='If set, quietly delete the Drive if existing without confirmation.')
def delete_drive(drive_id=None, yes=False):
    all_drive_ids = print_saved_drives()

    if drive_id is None:
        if yes:
            click.echo(click.style('Please specify the Drive ID to delete.', fg='red'))
            return
        index = click.prompt('Please enter the # number of the Drive to delete (CTRL+C to abort)', type=int)
        if isinstance(index, int) and index >= 0 and index < len(all_drive_ids):
            drive_id = all_drive_ids[index]
        else:
            click.echo(click.style('Error: "%s" is not a valid # number.' % str(index), fg='red'))
            return

    if drive_id not in all_drive_ids:
        click.echo(click.style('Error: Drive "%s" is not setup locally.' % drive_id, fg='red'))
        return

    if yes or click.confirm('Continue to delete Drive "%s" (its local directory will NOT be deleted)?' % drive_id,
                            abort=True):
        context.delete_drive(drive_id)
        save_context(context)
        click.echo(click.style('Successfully deleted Drive "%s" from onedrived.' % drive_id, fg='green'))
    else:
        click.echo('Operation canceled.')


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
    change_drive.add_command(list_drives)
    change_drive.add_command(set_drive)
    change_drive.add_command(delete_drive)
    main.add_command(change_account)
    main.add_command(change_config)
    main.add_command(change_drive)
    main()
