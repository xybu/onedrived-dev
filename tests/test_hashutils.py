import tempfile
import unittest

from onedrivesdk.model.item import Item
from onedrived import od_hashutils


class TestHashUtils(unittest.TestCase):

    TEST_CASES = [
        (b'Hello world!\n', '47a013e660d408619d894b20806b1d5086aab03b'.upper()),
        (b'Purdue University', 'a68b0321ef0a3ec9e7ffa2de22d70f79ac3e4dda'.upper())
    ]

    def setUp(self):
        self.TEST_FILES = []
        for t in self.TEST_CASES:
            tmpfile = tempfile.NamedTemporaryFile()
            tmpfile.write(t[0])
            tmpfile.flush()
            tmpfile.seek(0)
            self.TEST_FILES.append(tmpfile)

    def tearDown(self):
        for f in self.TEST_FILES:
            f.close()

    def test_hash(self):
        for i, (data, sha1) in enumerate(self.TEST_CASES):
            tmpname = self.TEST_FILES[i].name
            sha1_hash = od_hashutils.sha1_value(tmpname)
            self.assertEqual(sha1, sha1_hash)

    def _mock_item(self, sha1_hash=None):
        prop_dict = dict()
        if sha1_hash:
            prop_dict['sha1Hash'] = sha1_hash
        item = Item(prop_dict={'file': {'hashes': prop_dict}})
        self.assertEqual(sha1_hash, item.file.hashes.sha1_hash)
        return item

    def test_hash_match(self):
        tmpname = self.TEST_FILES[0].name
        self.assertTrue(
            od_hashutils.hash_match(tmpname, self._mock_item(sha1_hash=self.TEST_CASES[0][1])),
            'hash_match() should return True when only SHA1 hash is present and correct.')
        self.assertFalse(od_hashutils.hash_match(tmpname, self._mock_item(sha1_hash='BAR')))
        self.assertFalse(
            od_hashutils.hash_match(tmpname, self._mock_item()),
            'hash_match() should return False when SHA1 hash is missing.')


if __name__ == '__main__':
    unittest.main()
