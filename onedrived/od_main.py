#!/usr/bin/env python3

import asyncio
import itertools
import logging
import os
import signal
import sys
import weakref

import click
import daemonocle.cli

from . import od_repo
from . import od_task
from . import od_threads
from . import od_webhook
from .od_tasks import start_repo, merge_dir, update_subscriptions
from .od_auth import get_authenticator_and_drives
from .od_context import load_context
from .od_watcher import LocalRepositoryWatcher


context = load_context(asyncio.get_event_loop())
pidfile = context.config_dir + '/onedrived.pid'
task_workers = weakref.WeakSet()
task_pool = None
webhook_server = None
webhook_worker = None


def shutdown_workers():
    if task_pool:
        task_pool.close(len(task_workers))
    od_threads.TaskWorkerThread.exit()
    for w in task_workers:
        if w:
            w.join()


def shutdown_webhook():
    if webhook_server:
        webhook_server.stop()
        webhook_server.join()


# noinspection PyUnusedLocal
def shutdown_callback(msg, code):
    logging.info('Shutting down.')
    asyncio.gather(*asyncio.Task.all_tasks()).cancel()
    context.loop.stop()
    shutdown_webhook()
    shutdown_workers()
    if context and context.watcher:
        context.watcher.close()
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


def update_subscription_for_repo(repo, subscription_id=None):
    """
    :param onedrived.od_repo.OneDriveLocalRepository repo:
    :param str | None subscription_id:
    :return onedrivesdk.Subscription | None:
    """
    if webhook_server and webhook_worker:
        task = update_subscriptions.UpdateSubscriptionTask(repo, task_pool, webhook_worker, subscription_id)
        subscription = task.handle()
        if subscription:
            context.loop.call_later(int(context.config['webhook_renew_interval_sec'] * 0.75),
                                    update_subscription_for_repo, repo, subscription.id)
        return subscription
    return None


def gen_start_repo_tasks(all_accounts, task_pool):
    """
    :param dict[str, [onedrived.od_repo.OneDriveLocalRepository]] all_accounts:
    :param onedrived.od_task.TaskPool task_pool:
    """
    if task_pool.outstanding_task_count == 0:
        for repo in itertools.chain.from_iterable(all_accounts.values()):
            task_pool.add_task(start_repo.StartRepositoryTask(repo, task_pool))
            logging.info('Scheduled sync task for Drive %s of account %s.', repo.drive.id, repo.account_id)
            if update_subscription_for_repo(repo) is None:
                logging.warning('Failed to create webhook. Will deep sync again in %d sec.',
                                context.config['scan_interval_sec'])
                context.loop.call_later(context.config['scan_interval_sec'],
                                        gen_start_repo_tasks, all_accounts, task_pool)
            else:
                logging.info('Will use webhook to trigger sync events.')


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


def init_task_pool_and_workers():
    global task_pool
    task_pool = od_task.TaskPool()
    for i in range(context.config['num_workers']):
        w = od_threads.TaskWorkerThread(name='Worker-%d' % len(task_workers), task_pool=task_pool)
        w.start()
        task_workers.add(w)


def repo_updated_callback(repo):
    global task_pool, webhook_server
    if task_pool:
        item_request = repo.authenticator.client.item(drive=repo.drive.id, path='/')
        task_pool.add_task(merge_dir.MergeDirectoryTask(
            repo=repo, task_pool=task_pool, rel_path='', item_request=item_request,
            assume_remote_unchanged=True, parent_remote_unchanged=False))
        logging.info('Added task to check delta update for Drive %s.', repo.drive.id)
    else:
        logging.error('Uninitialized task pool reference.')


@click.command(cls=daemonocle.cli.DaemonCLI,
               daemon_params={
                   'uid': context.user_uid,
                   'pidfile': pidfile,
                   'shutdown_callback': shutdown_callback,
                   'workdir': os.getcwd()
               })
def main():
    global task_pool, webhook_server, webhook_worker

    # Exit program when receiving SIGTERM or SIGINT.
    signal.signal(signal.SIGTERM, shutdown_callback)

    # When debugging, print to stdout.
    if '--debug' in sys.argv:
        context.set_logger(min_level=logging.DEBUG, path=None)
        context.loop.set_debug(True)
    else:
        context.set_logger(min_level=logging.INFO, path=context.config[context.KEY_LOGFILE_PATH])

    if context.config['start_delay_sec'] > 0:
        logging.info('Wait for %d seconds before starting.', context.config['start_delay_sec'])
        import time
        time.sleep(context.config['start_delay_sec'])

    # Initialize account information.
    all_accounts = get_repo_table(context)
    delete_temp_files(all_accounts)

    # Start task pool and task worker.
    init_task_pool_and_workers()

    # Start webhook.
    webhook_server = od_webhook.get_webhook_server(context)
    webhook_worker = od_webhook.WebhookWorkerThread(webhook_url=webhook_server.webhook_url)
    webhook_worker.set_callback_func(repo_updated_callback)
    webhook_server.set_worker(webhook_worker)
    webhook_worker.start()
    webhook_server.start()

    context.watcher = LocalRepositoryWatcher(task_pool=task_pool, loop=context.loop)
    for repo in itertools.chain.from_iterable(all_accounts.values()):
        context.watcher.add_repo(repo)

    try:
        context.loop.call_soon(gen_start_repo_tasks, all_accounts, task_pool)
        context.loop.run_forever()
    finally:
        context.loop.close()


if __name__ == '__main__':
    main()
