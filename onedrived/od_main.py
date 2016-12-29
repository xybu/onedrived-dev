#!/usr/bin/env python3

import asyncio
import itertools
import logging
import os
import signal
import sys

import click
import daemonocle.cli

from . import od_repo
from . import od_task
from . import od_threads
from . import tasks
from .od_auth import get_authenticator_and_drives
from .od_context import load_context

context = load_context(asyncio.get_event_loop())
pidfile = context.config_dir + '/onedrived.pid'
task_workers = []
task_pool = None


# noinspection PyUnusedLocal
def shutdown_callback(msg, code):
    logging.info('Shutting down.')
    context.loop.stop()
    task_pool.close(len(task_workers))
    od_threads.TaskWorkerThread.exit()
    for w in task_workers:
        w.join()
    try:
        os.remove(pidfile)
    except OSError:
        pass
    logging.shutdown()


def get_repo_table(ctx):
    """
    :param onedrived.od_context.UserContext ctx:
    :return dict[str, [onedrived.od_repo.OneDriveLocalRepository]]:
    """
    all_accounts = {}
    all_account_ids = ctx.all_accounts()
    if len(all_account_ids) == 0:
        logging.critical('onedrived is not linked with any OneDrive account. Please configure onedrived first.')
        sys.exit(1)
    for account_id in all_account_ids:
        authenticator, drives = get_authenticator_and_drives(ctx, account_id)
        local_repos = [od_repo.OneDriveLocalRepository(ctx, authenticator, d, ctx.get_drive(d.id))
                       for d in drives if d.id in ctx.config['drives']]
        if len(local_repos) > 0:
            all_accounts[account_id] = local_repos
        else:
            profile = ctx.get_account(account_id)
            logging.info('No Drive associated with account "%s" (%s).', profile.account_email, account_id)
    return all_accounts


def gen_start_repo_tasks(all_accounts, task_pool):
    """
    :param dict[str, [onedrived.od_repo.OneDriveLocalRepository]] all_accounts:
    :param onedrived.od_task.TaskPool task_pool:
    """
    if task_pool.outstanding_task_count == 0:
        for repo in itertools.chain.from_iterable(all_accounts.values()):
            task_pool.add_task(tasks.start_repo.StartRepositoryTask(repo, task_pool))
            logging.info('Scheduled deep-sync for Drive %s of account %s.', repo.drive.id, repo.account_id)
    context.loop.call_later(context.config['scan_interval_sec'], gen_start_repo_tasks, all_accounts, task_pool)


def delete_temp_files(all_accounts):
    """
    Delete all onedrived temporary files from repository.
    :param dict[str, [onedrived.od_repo.OneDriveLocalRepository]] all_accounts:
    :return:
    """
    logging.info('Sweeping onedrived temporary files from local repositories.')
    for repo in itertools.chain.from_iterable(all_accounts.values()):
        if os.path.isdir(repo.local_root):
            os.system('find "%s" -type f -name "%s" -delete' % (repo.local_root, repo.path_filter.get_temp_name('*')))


@click.command(cls=daemonocle.cli.DaemonCLI,
               daemon_params={
                   'uid': context.user_uid,
                   'pidfile': pidfile,
                   'shutdown_callback': shutdown_callback,
               })
def main():
    # Exit program when receiving SIGTERM or SIGINT.
    signal.signal(signal.SIGTERM, shutdown_callback)

    # When debugging, print to stdout.
    if '--debug' in sys.argv:
        context.set_logger(min_level=logging.DEBUG, path=None)
    else:
        context.set_logger(min_level=logging.INFO, path=context.config[context.KEY_LOGFILE_PATH])

    # Initialize account information.
    all_accounts = get_repo_table(context)
    delete_temp_files(all_accounts)

    # Start task pool and task worker.
    global task_pool
    task_pool = od_task.TaskPool()
    for i in range(context.config['num_workers']):
        w = od_threads.TaskWorkerThread(name='Worker-%d' % len(task_workers), task_pool=task_pool)
        w.start()
        task_workers.append(w)

    context.loop.call_soon(gen_start_repo_tasks, all_accounts, task_pool)
    try:
        context.loop.run_forever()
    finally:
        context.loop.close()

if __name__ == '__main__':
    main()
