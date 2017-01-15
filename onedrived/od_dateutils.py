import arrow


def datetime_to_str(d):
    """
    :param arrow.Arrow d:
    :return str:
    """
    datetime_str = d.to('utc').isoformat()
    if datetime_str.endswith('+00:00'):
        datetime_str = datetime_str[:-6] + 'Z'
    return datetime_str


def str_to_datetime(s):
    """
    :param str s:
    :return arrow.Arrow:
    """
    return arrow.get(s)


def datetime_to_timestamp(d):
    """
    :param arrow.Arrow d: A datetime object.
    :return float: An equivalent UNIX timestamp.
    """
    return d.float_timestamp


def diff_timestamps(t1, t2):
    t1 = t1 - t2
    return 1 if t1 > 0.01 else -1 if t1 < -0.01 else 0
