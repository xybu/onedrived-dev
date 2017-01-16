import unittest

from onedrived import od_task
from onedrived.od_tasks.base import TaskBase


class TestTaskBase(unittest.TestCase):

    def test_task_base(self):
        p = '/home/xb/123'
        base = TaskBase(repo=None, task_pool=od_task.TaskPool())
        base.local_abspath = p
        self.assertEqual(p, base.local_abspath)


if __name__ == '__main__':
    unittest.main()
