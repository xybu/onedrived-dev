"""
Some formatter functions for onedrive-python-sdk API objects.
"""


def pretty_print_bytes(size, precision=2):
    suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    index = 0
    while size >= 1024:
        index += 1  # increment the index of the suffix
        size /= 1024.0  # apply the division
    return "%.*f %s" % (precision, size, suffixes[index])


def pretty_quota(q):
    """
    Return a string for Quota object.
    :param onedrivesdk.model.Quota q:
    :return:
    """
    return '%s Used / %s Total' % (pretty_print_bytes(q.used, precision=1), pretty_print_bytes(q.total, precision=1))
