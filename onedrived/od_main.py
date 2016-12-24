#!/usr/bin/env python3

import logging
import os
import signal
import sys
import time

import click
import daemonocle.cli

from .od_auth import get_authenticator_and_drives
from .od_context import load_context
from . import tasks
from . import od_task
from . import od_threads
from . import od_repo


context = load_context()
pidfile = context.config_dir + '/onedrived.pid'
task_workers = []
task_pool = None


def shutdown_callback(msg, code):
    logging.info('Shutting down.')
    task_pool.close(len(task_workers))
    od_threads.TaskWorkerThread.exit()
    for w in task_workers:
        w.join()
    try:
        os.remove(pidfile)
    except:
        pass
    logging.shutdown()


def get_repo_table(context):
    """
    :param onedrived.od_context.UserContext context:
    :return dict[str, [od_repo.OneDriveLocalRepository]]:
    """
    all_accounts = {}
    all_account_ids = context.all_accounts()
    if len(all_account_ids) == 0:
        logging.critical('onedrived is not linked with any OneDrive account. Please configure onedrived first.')
        sys.exit(1)
    for account_id in all_account_ids:
        authenticator, drives = get_authenticator_and_drives(context, account_id)
        local_repos = [od_repo.OneDriveLocalRepository(context, authenticator, d, context.get_drive(d.id))
                       for d in drives if d.id in context.config['drives']]
        if len(local_repos) > 0:
            all_accounts[account_id] = local_repos
        else:
            profile = context.get_account(account_id)
            logging.info('No Drive associated with account "%s" (%s).', profile.account_email, account_id)
    return all_accounts


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

    # Start task pool and task worker.
    global task_pool
    task_pool = od_task.TaskPool()
    for i in range(context.config['num_workers']):
        w = od_threads.TaskWorkerThread(name='Worker-%d' % len(task_workers), task_pool=task_pool)
        w.start()
        task_workers.append(w)

    while True:
        for account_id, local_repos in all_accounts.items():
            for r in local_repos:
                logging.info('Scheduled deep-sync for Drive %s of account %s.', r.drive.id, account_id)
                task_pool.add_task(tasks.start_repo.StartRepositoryTask(r, task_pool))
        time.sleep(context.config['scan_interval_sec'])

if __name__ == '__main__':
    main()
