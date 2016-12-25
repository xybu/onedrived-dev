from calendar import timegm
from datetime import datetime

from ciso8601 import parse_datetime


def datetime_to_str(d):
    """
    :param datetime.datetime d:
    :return str:
    """
    datetime_str = d.isoformat()
    if '+' in datetime_str:
        datetime_str = datetime_str[: datetime_str.index('+')]
    return datetime_str + 'Z'


def str_to_datetime(s):
    """
    :param str s:
    :return datetime.datetime:
    """
    return parse_datetime(s)


def datetime_to_timestamp(d):
    """
    :param datetime.datetime d: A datetime object.
    :return float: An equivalent UNIX timestamp.
    """
    return timegm(d.utctimetuple()) + d.microsecond / 1e6


def timestamp_to_datetime(t):
    """
    Convert a UNIX timestamp to a datetime object. Precision loss may occur.
    :param float t: A UNIX timestamp.
    :return datetime.datetime: An equivalent datetime object.
    """
    return datetime.utcfromtimestamp(t)


def compare_timestamps(t1, t2):
    if t1 - t2 > 0.001:
        return 1
    elif t2 - t1 > 0.001:
        return -1
    else:
        return 0
