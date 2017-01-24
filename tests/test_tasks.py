import unittest

from onedrived import od_task
from onedrived.od_tasks.base import TaskBase
from onedrived.od_tasks.start_repo import StartRepositoryTask

from tests.test_repo import get_sample_repo


class TestTaskBase(unittest.TestCase):

    def test_task_base(self):
        p = '/home/xb/123'
        base = TaskBase(repo=None, task_pool=od_task.TaskPool())
        base.local_abspath = p
        self.assertEqual(p, base.local_abspath)


class TestStartRepositoryTask(unittest.TestCase):

    def setUp(self):
        self.task_pool = od_task.TaskPool()
        self.tempdir, self.drive_config, self.repo = get_sample_repo()

    def test_handle(self):
        task = StartRepositoryTask(self.repo, self.task_pool)
        task.handle()
        self.assertEqual(1, self.task_pool.outstanding_task_count)



if __name__ == '__main__':
    unittest.main()
