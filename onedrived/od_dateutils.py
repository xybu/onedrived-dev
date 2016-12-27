from calendar import timegm
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


def diff_timestamps(t1, t2):
    t1 = t1 - t2
    return 1 if t1 > 0.01 else -1 if t1 < -0.01 else 0
