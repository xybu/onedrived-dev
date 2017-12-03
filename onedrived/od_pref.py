#!/usr/bin/env python3

import json
import locale
import os
import urllib.parse

import click
import keyring
import tabulate

from . import __version__
from . import mkdir, get_resource, od_auth, od_i18n
from .od_models import pretty_api, drive_config
from .od_api_session import OneDriveAPISession, get_keyring_key
from .od_models.dict_guard import GuardedDict, exceptions as guard_errors
from .od_context import load_context, save_context
from .od_repo import get_drive_db_path


context = load_context()
translator = od_i18n.Translator(('od_pref', ), locale_str=str(locale.getlocale()[0]))
config_schema = json.loads(get_resource('data/config_schema.json', pkg_name='onedrived'))
config_guard = GuardedDict(config_dict=context.config, config_schema_dict=config_schema)


def error(s):
    click.secho(s, fg='red')


def warning(s):
    click.secho(s, fg='yellow')


def success(s):
    click.secho(s, fg='green')


def quota_short_str(q):
    """
    Return a string for Quota object.
    :param onedrivesdk.model.Quota q:
    :return:
    """
    return translator['api.drive.quota.short_format'].format(
        used=pretty_api.pretty_print_bytes(q.used, precision=1),
        total=pretty_api.pretty_print_bytes(q.total, precision=1))


def print_all_accounts(ctx):
    all_accounts = []
    all_account_ids = ctx.all_accounts()
    for i, account_id in enumerate(all_account_ids):
        account = ctx.get_account(account_id)
        all_accounts.append((str(i), account_id, account.account_name, account.account_email))
    click.echo(tabulate.tabulate(all_accounts, headers=('#', 'Account ID', 'Owner Name', 'Email Address')))
    return all_account_ids


def email_to_account_id(ctx, email, all_account_ids=None):
    if all_account_ids is None:
        all_account_ids = ctx.all_accounts()
    for s in all_account_ids:
        account = ctx.get_account(s)
        if account.account_email == email:
            return s
    raise ValueError('Did not find existing account with email address "%s".' % email)


def extract_qs_param(url, key):
    if url is not None and '?' in url:
        qs_dict = urllib.parse.parse_qs(url.split('?')[1])
        if key in qs_dict:
            return qs_dict[key]
    return None


def main():
    command_map = {
        main_cmd: (change_account, change_config, change_drive),
        change_account: (authenticate_account, list_accounts, delete_account),
        change_config: (set_config, print_config),
        change_drive: (list_drives, set_drive, delete_drive)
    }
    for cmd, subcmds in command_map.items():
        for c in subcmds:
            cmd.add_command(c)
    main_cmd()


@click.group(context_settings=dict(help_option_names=['-h', '--help']))
@click.version_option(__version__)
def main_cmd():
    pass


@click.group(name='account', short_help=translator['od_pref.account.submain.short_help'])
def change_account():
    pass


def save_account(authenticator):
    try:
        account_profile = authenticator.get_profile()
        authenticator.save_session(key=get_keyring_key(account_profile.account_id))
        context.add_account(account_profile)
        save_context(context)
        success(translator['od_pref.save_account.success'].format(profile=account_profile))
        click.echo()
        click.echo(translator['od_pref.save_account.print_header'].format(context=context))
        click.echo()
        print_all_accounts(context)
    except Exception as e:
        error(translator['od_pref.save_account.error'].format(error_message=str(e)))


@click.command(name='add', short_help=translator['od_pref.authenticate_account.short_help'])
@click.option('--get-auth-url', '-u', is_flag=True, default=False, required=False,
              help=translator['od_pref.authenticate_account.get_auth_url.help'])
@click.option('--code', '-c', type=str, required=False, default=None,
              help=translator['od_pref.authenticate_account.code.help'])
@click.option('--for-business', '-b', is_flag=True, default=False, required=False,
              help=translator['od_pref.authenticate_account.for_business.help'])
def authenticate_account(get_auth_url=False, code=None, for_business=False):
    if for_business:
        error(translator['od_pref.authenticate_account.for_business_unsupported'])
        return
    authenticator = od_auth.OneDriveAuthenticator()
    click.echo(translator['od_pref.authenticate_account.permission_note'])
    if code is None:
        click.echo(translator['od_pref.authenticate_account.paste_url_note'])
        click.echo('\n' + click.style(authenticator.get_auth_url(), underline=True) + '\n')
        if get_auth_url:
            return
        click.echo(translator['od_pref.authenticate_account.paste_url_instruction'].format(
            redirect_url=click.style(authenticator.APP_REDIRECT_URL, bold=True)))
        url = click.prompt(translator['od_pref.authenticate_account.paste_url_prompt'], type=str)
        code = extract_qs_param(url, 'code')
        if code is None:
            error(translator['od_pref.authenticate_account.error.code_not_found_in_url'])
            return

    try:
        authenticator.authenticate(code)
        success(translator['od_pref.authenticate_account.success.authorized'])
        save_account(authenticator)
    except Exception as e:
        error(translator['od_pref.authenticate_account.error.authorization'].format(error_message=str(e)))


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
        if isinstance(index, int) and 0 <= index < len(all_account_ids):
            account_id = all_account_ids[index]
        else:
            error('Index is not a valid row number.')
            return

    if email is not None:
        try:
            account_id = email_to_account_id(context, email, all_account_ids)
        except Exception as e:
            error(str(e))
            return

    if account_id is not None:
        if account_id not in all_account_ids:
            error('Account ID "%s" is not found.' % account_id)
            return
        account = context.get_account(account_id)
        prompt_text = 'Are you sure to delete account %s?' % account
        if yes or click.confirm(prompt_text):
            context.delete_account(account_id)
            keyring.delete_password(OneDriveAPISession.KEYRING_SERVICE_NAME, get_keyring_key(account_id))
            save_context(context)
            success('Successfully deleted account from onedrived.')
        else:
            click.echo('Operation canceled.')


@click.group(name='drive', short_help=translator['od_pref.drive.submain.short_help'])
def change_drive():
    pass


def print_all_drives():
    click.echo(translator['od_pref.print_all_drives.fetching_drives.note'])
    click.echo()
    all_drives = {}
    drive_table = []
    for i in context.all_accounts():
        drive_objs = []
        profile = context.get_account(i)
        authenticator, drives = od_auth.get_authenticator_and_drives(context, i)
        for d in drives:
            drive_objs.append(d)
            drive_table.append((str(len(drive_table)), profile.account_email,
                                d.id, d.drive_type, quota_short_str(d.quota), d.status.state))
        all_drives[i] = (profile, authenticator, drive_objs)
    click.secho(translator['od_pref.print_all_drives.all_drives_table.note'], bold=True)
    click.echo()
    click.echo(tabulate.tabulate(drive_table, headers=(
        translator['od_pref.print_all_drives.all_drives_table.header.index'],
        translator['od_pref.print_all_drives.all_drives_table.header.account_email'],
        translator['od_pref.print_all_drives.all_drives_table.header.drive_id'],
        translator['od_pref.print_all_drives.all_drives_table.header.type'],
        translator['od_pref.print_all_drives.all_drives_table.header.quota'],
        translator['od_pref.print_all_drives.all_drives_table.header.status'])))
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
    if isinstance(index, int) and 0 <= index < len(drive_table):
        email = drive_table[index][1]  # Plus one to offset the header row.
        drive_id = drive_table[index][2]
        return email, drive_id
    raise ValueError('Index is not a valid row number.')


@click.command(name='list', short_help=translator['od_pref.list_drive.short_help'])
def list_drives():
    try:
        print_all_drives()
        click.echo()
        print_saved_drives()
    except Exception as e:
        error('Error: %s.' % e)


def read_drive_config_interactively(drive_exists, curr_drive_config):
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
                    error('OSError: %s' % e)
                    local_root = None
        elif not os.path.isdir(local_root):
            error('Path "%s" should be a directory.' % local_root)
            local_root = None
        elif not click.confirm('Syncing with directory "%s"?' % local_root):
            local_root = None
    while ignore_file is None:
        ignore_file = click.prompt('Enter the path to ignore file for this Drive',
                                   type=str, default=ignore_file_default)
        ignore_file = os.path.abspath(ignore_file)
        if not os.path.isfile(ignore_file):
            error('Path "%s" is not a file.' % ignore_file)
            ignore_file = None
    return local_root, ignore_file


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
        error('Error: %s.' % e)
        return

    interactive = drive_id is None or email is None
    if interactive:
        # Interactive mode to ask for which drive to add.
        index = click.prompt('Please enter row number of the Drive to add or modify (CTRL+C to abort)', type=int)
        try:
            email, drive_id = index_to_drive_table_row(index, drive_table)
        except ValueError as e:
            error(str(e))
            return

    try:
        account_id = email_to_account_id(context, email)
    except Exception as e:
        error(str(e))
        return

    # Traverse the Drive objects and see if Drive exists.
    found_drive = False
    for d in all_drives[account_id][2]:
        if drive_id == d.id:
            found_drive = True
            break
    if not found_drive:
        error('Did not find Drive "%s".' % drive_id)
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
        'Going to add/edit Drive "%s" of account "%s"...' % (drive_id, account_profile.account_email), fg='cyan'))

    if interactive:
        local_root, ignore_file = read_drive_config_interactively(drive_exists, curr_drive_config)
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
                click.secho('Warning: ignore file path does not point to a file. Use default.', fg='yellow')
                ignore_file = context.config_dir + '/' + context.DEFAULT_IGNORE_FILENAME
            if (drive_exists and
                local_root == curr_drive_config.localroot_path and
                    ignore_file == curr_drive_config.ignorefile_path):
                click.secho('No parameter was changed. Skipped operation.', fg='yellow')
                return
        except ValueError as e:
            error(str(e))
            return

    d = context.add_drive(drive_config.LocalDriveConfig(drive_id, account_id, ignore_file, local_root))
    save_context(context)
    success('\nSuccessfully configured Drive %s of account %s (%s):' % (
        d.drive_id, account_profile.account_email, d.account_id))
    click.echo('  Local directory: ' + d.localroot_path)
    click.echo('  Ignore file path: ' + d.ignorefile_path)


@click.command(name='del', short_help=translator['od_pref.del_drive.short_help'])
@click.option('--drive-id', '-d', type=str, required=False, default=None,
              help='ID of the Drive.')
@click.option('--yes', '-y', is_flag=True, default=False, required=False,
              help='If set, quietly delete the Drive if existing without confirmation.')
def delete_drive(drive_id=None, yes=False):
    all_drive_ids = print_saved_drives()

    if len(all_drive_ids) == 0:
        return

    if drive_id is None:
        if yes:
            error(translator['od_pref.del_drive.specify_drive_to_delete'])
            return
        index = click.prompt(translator['od_pref.del_drive.choose_index'], type=int)
        if isinstance(index, int) and 0 <= index < len(all_drive_ids):
            drive_id = all_drive_ids[index]
        else:
            error('Error: "%s" is not a valid # number.' % str(index))
            return

    if drive_id not in all_drive_ids:
        error('Error: Drive "%s" is not setup locally.' % drive_id)
        return

    if yes or click.confirm('Continue to delete Drive "%s" (its local directory will NOT be deleted)?' % drive_id,
                            abort=True):
        try:
            os.unlink(get_drive_db_path(context.config_dir, drive_id))
        except Exception as e:
            warning(translator['od_pref.del_drive.error_del_db_file'].format(error=str(e)))
        context.delete_drive(drive_id)
        save_context(context)
        success('Successfully deleted Drive "%s" from onedrived.' % drive_id)
    else:
        click.echo('Operation canceled.')


@click.group(name='config', short_help=translator['od_pref.config.submain.short_help'])
def change_config():
    pass


@click.command(name='print', short_help=translator['od_pref.print_config.short_help'])
def print_config():
    for key in sorted(config_schema.keys()):
        description = config_schema[key]['description']
        if description.startswith('@lang[\'') and description.endswith('\']'):
            description = translator[description[7:-2]]
        click.echo('# %s' % description)
        click.echo('%s = %s\n' % (key, str(context.config[key])))


@click.command(name='set', short_help=translator['od_pref.set_config.short_help'])
@click.argument('key', type=click.Choice(sorted(config_schema.keys())))
@click.argument('value')
def set_config(key, value):
    try:
        config_guard[key] = value
        save_context(context)
        click.echo('config.%s = %s' % (key, str(context.config[key])))
    except guard_errors.DictGuardKeyError as e:
        error(translator['configurator.error_invalid_key'].format(key=e.key))
    except guard_errors.IntValueRequired as e:
        error(translator['configurator.error_int_value_required'].format(key=e.key, value=e.value))
    except guard_errors.IntValueBelowMinimum as e:
        error(translator['configurator.error_int_below_minimum'].format(key=e.key, value=e.value, minimum=e.minimum))
    except guard_errors.IntValueAboveMaximum as e:
        error(translator['configurator.error_int_above_maximum'].format(key=e.key, value=e.value, maximum=e.maximum))
    except guard_errors.StringInvalidChoice as e:
        error(translator['configurator.error_str_invalid_choice'].format(
            key=e.key, value=e.value, choices=', '.join(e.choices_allowed)))
    except guard_errors.StringNotStartsWith as e:
        error(translator['configurator.error_str_not_startswith'].format(
            key=e.key, value=e.value, starts_with=e.expected_starts_with))
    except (guard_errors.PathDoesNotExist, guard_errors.PathIsNotFile) as e:
        if isinstance(e, guard_errors.PathIsNotFile):
            str_key = 'configurator.error_path_not_file'
        else:
            str_key = 'configurator.error_path_not_exist'
        error(translator[str_key].format(key=e.key, path=e.value))
    except OSError as e:
        error(translator['configurator.error_generic'].format(key=key, error_message=str(e)))
    except:
        raise


if __name__ == '__main__':
    main()
