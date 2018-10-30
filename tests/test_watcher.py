import unittest

import inotify_simple

from onedrive_client import od_task, od_watcher


class TestLocalRepositoryWatcher(unittest.TestCase):

    def setUp(self):
        self.watcher = od_watcher.LocalRepositoryWatcher(od_task.TaskPool, None)

    def test_recognize_event_patterns(self):
        events = [inotify_simple.Event(wd=1, mask=inotify_simple.flags.MOVED_FROM, cookie=233, name='fromA'),
                  inotify_simple.Event(wd=3, mask=inotify_simple.flags.MOVED_TO, cookie=233, name='toA'),
                  inotify_simple.Event(wd=5, mask=inotify_simple.flags.MOVED_FROM, cookie=234, name='from'),
                  inotify_simple.Event(wd=7, mask=inotify_simple.flags.MOVED_TO, cookie=235, name='to')]
        move_pairs, all_events = self.watcher._recognize_event_patterns(events)
        self.assertEqual(4, len(all_events))
        self.assertIn(233, move_pairs)
        self.assertNotIn(234, move_pairs)
        self.assertNotIn(235, move_pairs)
        (ev_a, flags_a), (ev_b, flags_b) = move_pairs[233]
        self.assertEqual([inotify_simple.flags.MOVED_FROM], flags_a)
        self.assertEqual('fromA', ev_a.name)
        self.assertEqual([inotify_simple.flags.MOVED_TO], flags_b)
        self.assertEqual('toA', ev_b.name)
        self.assertEqual((ev_b, flags_b), all_events[1])


if __name__ == '__main__':
    unittest.main()
