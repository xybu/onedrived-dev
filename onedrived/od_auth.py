"""
od_auth.py
Core component for user authentication and authorization.
:copyright: (c) Xiangyu Bu <xybu92@live.com>
:license: MIT
"""

import requests
import onedrivesdk
import onedrivesdk.helpers.http_provider_with_proxy

import od_api_session
import od_account


class OneDriveAuthenticator:

    APP_CLIENT_ID = '000000004010C916'
    APP_CLIENT_SECRET = 'PimIrUibJfsKsMcd0SqwPBwMTV7NDgYi'
    APP_BASE_URL = 'https://api.onedrive.com/v1.0/'
    APP_REDIRECT_URL = 'https://login.live.com/oauth20_desktop.srf'
    APP_SCOPES = ['wl.signin', 'wl.offline_access', 'onedrive.readwrite']

    def __init__(self, proxies=None):
        """
        :param dict[str, str] proxies: A dict of proxies in format like "{'https': proxy1, 'http': proxy2}".
        """
        if proxies is None or not isinstance(proxies, dict) or len(proxies) == 0:
            http_provider = onedrivesdk.HttpProvider()
        else:
            http_provider = onedrivesdk.helpers.http_provider_with_proxy.HttpProviderWithProxy(proxies, verify_ssl=True)
        auth_provider = onedrivesdk.AuthProvider(http_provider=http_provider,
                                                 client_id=self.APP_CLIENT_ID,
                                                 session_type=od_api_session.OneDriveAPISession,
                                                 scopes=self.APP_SCOPES)
        self.client = onedrivesdk.OneDriveClient(self.APP_BASE_URL, auth_provider, http_provider)

    def get_auth_url(self):
        return self.client.auth_provider.get_auth_url(self.APP_REDIRECT_URL)

    def authenticate(self, code):
        self.client.auth_provider.authenticate(code, self.APP_REDIRECT_URL, self.APP_CLIENT_SECRET)

    def get_profile(self, user_id='me', proxies=None):
        """
        Fetch basic profile of the specified user (Live ID).
        :param str user_id: (Optional) ID of the target user.
        :param dict[str, str] proxies: (Optional) Proxies to issue the HTTP request.
        :return OneDriveUserProfile: An OneDriveUserProfile object that contains the basic user info.
        """
        url = 'https://apis.live.net/v5.0/' + user_id
        headers = {'Authorization': 'Bearer ' + self.client.auth_provider.access_token}
        response = requests.get(url, headers=headers, proxies=proxies, verify=True)
        if response.status_code != requests.codes.ok:
            raise ValueError('Failed to read user profile.')
        data = response.json()
        return od_account.OneDriveAccountProfile(user_id=data['id'], user_name=data['name'])

    def save_session(self, key):
        args = {od_api_session.OneDriveAPISession.SESSION_ARG_KEYNAME: key}
        self.client.auth_provider.save_session(**args)
