import unittest

from onedrive_client import od_stringutils


class TestStringUtils(unittest.TestCase):

    INCREMENTED_FILE_NAMES = (('Folder', 'Folder 1'), ('Folder 1', 'Folder 2'),
                              ('file.txt', 'file 1.txt'), ('file 1.txt', 'file 2.txt'),
                              ('Folder 0', 'Folder 0 1'))

    def test_get_filename_with_incremented_count(self):
        for orig, exp in self.INCREMENTED_FILE_NAMES:
            self.assertEqual(exp, od_stringutils.get_filename_with_incremented_count(orig))


if __name__ == '__main__':
    unittest.main()
