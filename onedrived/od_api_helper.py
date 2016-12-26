from . import od_dateutils


def get_item_modified_datetime(item):
    """
    :param onedrivesdk.model.item.Item item:
    :return [datetime.datetime, True | False]: Return a 2-tuple (datetime, bool) in which the bool indicates modifiable.
    """
    # SDK Bug: the API can return some non-standard datetime string that SDK can't handle.
    # https://github.com/OneDrive/onedrive-sdk-python/issues/89
    # Until the bug is fixed I'll avoid the SDK calls and use the value directly.
    try:
        return od_dateutils.str_to_datetime(item._prop_dict['fileSystemInfo']['lastModifiedDateTime']), True
    except AttributeError:
        # OneDrive for Business does not have FileSystemInfo facet. Fall back to read-only mtime attribute.
        return od_dateutils.str_to_datetime(item._prop_dict['lastModifiedDateTime']), False
