import asyncio
import unittest

from onedrived import od_context


def get_sample_context():
    return od_context.UserContext(loop=asyncio.get_event_loop())


class TestUserContext(unittest.TestCase):

    def setUp(self):
        self.ctx = get_sample_context()

    def test_get_login_username(self):
        self.assertIsInstance(od_context.get_login_username(), str)


if __name__ == '__main__':
    unittest.main()
