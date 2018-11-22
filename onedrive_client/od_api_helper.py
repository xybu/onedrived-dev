import json
import logging
import time

import onedrivesdk
import onedrivesdk.error
import requests

from onedrive_client import od_dateutils

THROTTLE_PAUSE_SEC = 60


def get_drive_request_builder(repo):
    return onedrivesdk.DriveRequestBuilder(
        request_url=repo.authenticator.client.base_url + 'drives/' + repo.drive.id,
        client=repo.authenticator.client)


def create_subscription(folder_item_request, repo, webhook_url, expiration_time):
    """
    :param onedrivesdk.ItemRequestBuilder folder_item_request:
    :param onedrive_client.od_repo.OneDriveLocalRepository repo:
    :param str webhook_url:
    :param datetime.datetime.datetime expiration_time:
    :return onedrivesdk.Subscription:
    """
    subscriptions_collection_req = folder_item_request.subscriptions
    subscription_req_builder = onedrivesdk.SubscriptionRequestBuilder(subscriptions_collection_req._request_url,
                                                                      subscriptions_collection_req._client)
    subscription_req = item_request_call(repo, subscription_req_builder.request)
    subscription_req.content_type = "application/json"
    subscription_req.method = "POST"
    subscription = onedrivesdk.Subscription()
    subscription.notification_url = webhook_url
    subscription.expiration_date_time = expiration_time
    return onedrivesdk.Subscription(json.loads(subscription_req.send(subscription).content))


def update_subscription(self, subscription):
    """ A temp patch for bug https://github.com/OneDrive/onedrive-sdk-python/issues/95. """
    self.content_type = "application/json"
    self.method = "PATCH"
    entity = onedrivesdk.Subscription(json.loads(self.send(subscription).content))
    return entity


onedrivesdk.SubscriptionRequest.update = update_subscription


def get_item_modified_datetime(item):
    """
    :param onedrivesdk.Item item:
    :return [arrow.Arrow, True | False]: Return a 2-tuple (datetime, bool) in which the bool indicates modifiable.
    """
    # SDK Bug: the API can return some non-standard datetime string that SDK can't handle.
    # https://github.com/OneDrive/onedrive-sdk-python/issues/89
    # Until the bug is fixed I'll avoid the SDK calls and use the value directly.
    try:
        return od_dateutils.str_to_datetime(item.file_system_info._prop_dict['lastModifiedDateTime']), True
    except AttributeError:
        # OneDrive for Business does not have FileSystemInfo facet. Fall back to read-only mtime attribute.
        return od_dateutils.str_to_datetime(item._prop_dict['lastModifiedDateTime']), False


def get_item_created_datetime(item):
    return od_dateutils.str_to_datetime(item._prop_dict['createdDateTime'])


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
