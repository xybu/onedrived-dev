from datetime import datetime, timezone, timedelta
import unittest

from onedrived import od_dateutils


class TestDateUtils(unittest.TestCase):

    DT_OFFSET = timedelta(hours=1)
    DT_STR = '2015-08-06T18:45:20.260000Z'
    DT_TS = 1438886720.26
    DT_OBJ = datetime(year=2015, month=8, day=6, hour=18, minute=45, second=20, microsecond=260000)
    DT_UTC_OBJ = DT_OBJ.replace(tzinfo=timezone.utc)
    DT_NONUTC_OBJ = DT_UTC_OBJ.replace(tzinfo=timezone(offset=DT_OFFSET))

    def test_str_to_datetime(self):
        self.assertEqual(self.DT_UTC_OBJ, od_dateutils.str_to_datetime(self.DT_STR))

    def test_datetime_to_str(self):
        self.assertEqual(self.DT_STR, od_dateutils.datetime_to_str(self.DT_UTC_OBJ))

    def test_datetime_to_timestamp_explicit_utc(self):
        ts = od_dateutils.datetime_to_timestamp(self.DT_UTC_OBJ)
        self.assertEqual(self.DT_UTC_OBJ.timestamp(), ts)
        self.assertEqual(self.DT_TS, ts)

    def test_datetime_to_timestamp_implicit_utc(self):
        """
        onedrivesdk-python returns datetime objects that do not have tzinfo but onedrived wants it to be explicit.
        This test case check if the machine and program can handle implicit UTC.
        """
        self.assertEqual(self.DT_UTC_OBJ.timestamp(), od_dateutils.datetime_to_timestamp(self.DT_OBJ))

    def test_datetime_to_timestamp_non_utc(self):
        ts = od_dateutils.datetime_to_timestamp(self.DT_NONUTC_OBJ)
        self.assertEqual(self.DT_UTC_OBJ.timestamp() - self.DT_OFFSET.total_seconds(), ts)
        self.assertEqual(self.DT_NONUTC_OBJ.timestamp(), ts)


if __name__ == '__main__':
    unittest.main()
