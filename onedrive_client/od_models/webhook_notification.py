"""
webhook_notification.py

Implementation of the datatypes used in OneDrive webhook notification, which is absent
from official OneDrive Python SDK.

:copyright: (c) Xiangyu Bu <xybu92@live.com>
:license: MIT
"""

from onedrive_client import od_dateutils


class WebhookNotification:

    """ https://dev.onedrive.com/resources/webhookNotifiation.htm """

    def __init__(self, prop_dict):
        self._prop_dict = prop_dict

    @property
    def context(self):
        """
        :return str | None:
            An optional string value that is passed back in the notification message for this subscription.
        """
        try:
            return self._prop_dict['context']
        except KeyError:
            return None

    @property
    def expiration_datetime(self):
        """
        :return arrow.Arrow: The date and time when the subscription will expire if not updated or renewed.
        """
        return od_dateutils.str_to_datetime(self._prop_dict['expirationDateTime'])

    @property
    def resource(self):
        """
        :return str: URL to the item where the subscription is registered.
        """
        return self._prop_dict['resource']

    @property
    def subscription_id(self):
        """
        :return str: The unique identifier for the subscription resource.
        """
        return self._prop_dict['subscriptionId']

    @property
    def tenant_id(self):
        """
        :return str:
            Unique identifier for the tenant which generated this notification.
            This is only returned for OneDrive for Business and SharePoint.
        """
        try:
            return self._prop_dict['tenantId']
        except KeyError:
            return None

    @property
    def user_id(self):
        """
        :return str: Unique identifier for the drive which generated this notification.
        """
        return self._prop_dict['userId']
