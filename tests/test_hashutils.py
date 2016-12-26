import tempfile
import unittest

from onedrived import od_hashutils


class TestHashUtils(unittest.TestCase):

    def setUp(self):
        self.tmpfile = tempfile.NamedTemporaryFile()
        self.tmpfile.write(b'Hello world!\n')
        self.tmpfile.flush()
        self.tmpfile.seek(0)

    def tearDown(self):
        self.tmpfile.close()

    def test_sha1_hash(self):
        hash = od_hashutils.hash_value(self.tmpfile.name)
        self.assertEqual('47a013e660d408619d894b20806b1d5086aab03b'.upper(), hash)

    def test_crc32_hash(self):
        hash = od_hashutils.crc32_value(self.tmpfile.name)
        self.assertEqual('b2a9e441'.upper(), hash)


if __name__ == '__main__':
    unittest.main()
