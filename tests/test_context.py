import unittest

from onedrived import od_context


class TestUserContext(unittest.TestCase):

    def setUp(self):
        self.ctx = od_context.UserContext(loop=None)

    def test_get_login_username(self):
        self.assertIsInstance(od_context.get_login_username(), str)


if __name__ == '__main__':
    unittest.main()
