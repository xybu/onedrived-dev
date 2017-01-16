"""
od_task.py
Core component for OneDrive server-client interaction management.
:copyright: (c) Xiangyu Bu <xybu92@live.com>
:license: MIT
"""

import logging
import threading


class TaskPool:
    """
    An in-memory storage for tasks.

    Some notes:
      (1) Tried to let worker threads and inotify watcher communicate by reading/writing a "working path set" but
          because workers tend to delete path before watcher can read it.
    """

    def __init__(self):
        self.tasks_by_path = {}
        self.queued_tasks = []
        self.semaphore = threading.Semaphore(0)
        self._lock = threading.Lock()

    def close(self, n=1):
        for i in range(n):
            self.semaphore.release()

    def add_task(self, task):
        """
        Add a task to internal storage. It will not add if there is already a task on the path.
        :param onedrived.tasks.base.TaskBase task: The task to add.
        """
        logging.debug('Adding task %s...' % task)
        with self._lock:
            if task.local_abspath in self.tasks_by_path:
                return False
            self.queued_tasks.append(task)
            self.tasks_by_path[task.local_abspath] = task
        self.semaphore.release()
        return True

    def pop_task(self):
        """
        Pop the oldest task. It's required that the caller first acquire the semaphore.
        :return onedrived.tasks.base.TaskBase | None: The first qualified task, or None.
        """
        # logging.debug('Getting task...')
        with self._lock:
            ret = None
            if len(self.queued_tasks):
                ret = self.queued_tasks.pop(0)
                del self.tasks_by_path[ret.local_abspath]
            return ret

    @property
    def outstanding_task_count(self):
        with self._lock:
            return len(self.queued_tasks)

    def has_pending_task(self, local_path):
        with self._lock:
            return local_path in self.tasks_by_path

    def remove_children_tasks(self, local_parent_path):
        p = local_parent_path + '/'
        with self._lock:
            for t in self.queued_tasks[:]:
                if t.local_abspath.startswith(p) or t.local_abspath == local_parent_path:
                    self.queued_tasks.remove(t)
                    del self.tasks_by_path[t.local_abspath]
