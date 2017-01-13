import logging
import time

import onedrivesdk.error
import requests

from . import od_dateutils

THROTTLE_PAUSE_SEC = 60


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


def item_request_call(repo, request_func, *args, **kwargs):
    while True:
        try:
            return request_func(*args, **kwargs)
        except onedrivesdk.error.OneDriveError as e:
            logging.error('Encountered API Error: %s.', e)
            if e.code == onedrivesdk.error.ErrorCode.ActivityLimitReached:
                time.sleep(THROTTLE_PAUSE_SEC)
            elif e.code == onedrivesdk.error.ErrorCode.Unauthenticated:
                repo.authenticator.refresh_session(repo.account_id)
            else:
                raise e
        except requests.ConnectionError as e:
            logging.error('Encountered connection error: %s. Retry in %d sec.', e, THROTTLE_PAUSE_SEC)
            time.sleep(THROTTLE_PAUSE_SEC)
