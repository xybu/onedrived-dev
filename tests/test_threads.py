import threading
import unittest

from onedrived import od_threads, od_task
from onedrived.od_tasks.base import TaskBase


class DummyTest(TaskBase):

    def __init__(self, sem, repo=None, task_pool=None):
        super().__init__(repo, task_pool)
        self.sem = sem
        self.local_abspath = '/Dummy'

    def handle(self):
        self.sem.release()


class TestTaskWorkerThread(unittest.TestCase):

    def setUp(self):
        self.task_pool = od_task.TaskPool()

    def test_lifecycle(self):
        sem = threading.Semaphore(value=0)
        t = DummyTest(sem, None, self.task_pool)
        w = od_threads.TaskWorkerThread('DummyWorker', task_pool=self.task_pool)
        w.start()
        self.assertTrue(self.task_pool.add_task(t))
        self.assertTrue(sem.acquire(timeout=10))
        od_threads.TaskWorkerThread.exit()
        self.task_pool.close(1)
        w.join(timeout=10)


if __name__ == '__main__':
    unittest.main()
