import unittest

from onedrived import od_task
from onedrived.tasks.base import TaskBase


class TestTaskPool(unittest.TestCase):

    def _get_dummy_task(self, local_abspath=None):
        t = TaskBase(repo=None, task_pool=self.task_pool)
        t.local_abspath = local_abspath
        return t

    def setUp(self):
        self.task_pool = od_task.TaskPool()

    def test_add_and_pop(self):
        ts = [self._get_dummy_task(local_abspath='/1'), self._get_dummy_task(local_abspath='/2')]
        for i, t in enumerate(ts):
            self.assertEqual(i, self.task_pool.outstanding_task_count)
            self.assertTrue(self.task_pool.add_task(t))
        self.assertEqual(2, self.task_pool.outstanding_task_count)
        self.assertFalse(self.task_pool.add_task(self._get_dummy_task(local_abspath='/1')))
        for i, t in enumerate(ts):
            self.assertIs(t, self.task_pool.pop_task())
            self.assertEqual(len(ts) - i - 1, self.task_pool.outstanding_task_count)
        self.assertEqual(0, self.task_pool.outstanding_task_count)

    def test_has_pending_task(self):
        self.task_pool.add_task(self._get_dummy_task(local_abspath='/foo/bar'))
        self.assertTrue(self.task_pool.has_pending_task('/foo/bar'))
        for s in ('/foo/ba', '/foo/barz', '/foo/bar/baz', '/foo'):
            self.assertFalse(self.task_pool.has_pending_task(s))

    def test_remove_children_tasks(self):
        for s in ('/foo', '/foo2', '/foo/bar', '/foo2/bar', '/foo/bar/baz'):
            self.task_pool.add_task(self._get_dummy_task(local_abspath=s))
        self.task_pool.remove_children_tasks(local_parent_path='/foo')
        self.assertEqual(2, self.task_pool.outstanding_task_count)
        self.assertEqual('/foo2', self.task_pool.pop_task().local_abspath)
        self.assertEqual('/foo2/bar', self.task_pool.pop_task().local_abspath)


if __name__ == '__main__':
    unittest.main()
