"""
od_auth.py
Core component for user authentication and authorization.
:copyright: (c) Xiangyu Bu <xybu92@live.com>
:license: MIT
"""

import logging
import requests
from requests.utils import getproxies
import onedrivesdk
import onedrivesdk.error
from onedrivesdk.helpers import GetAuthCodeServer
from onedrivesdk.helpers.resource_discovery import ResourceDiscoveryRequest


from onedrived import od_api_session
import od_models
from od_models import account_profile
from od_models import account_profile_business


def get_authenticator_and_drives(context, account_id):
    # TODO: Ideally we should recursively get all drives because the API pages them.
    authenticator = OneDriveAuthenticator()
    try:
        authenticator.load_session(key=od_api_session.get_keyring_key(account_id))
        drives = authenticator.client.drives.get()
    except (onedrivesdk.error.OneDriveError, RuntimeError) as e:
        logging.error('Error loading session: %s. Try refreshing token.', e)
        authenticator.refresh_session(account_id)
        drives = authenticator.client.drives.get()
    return authenticator, drives


class AccountTypes:
    PERSONAL = 0
    BUSINESS = 1


class OneDriveBusinessAuthenticator:
    
    APP_CLIENT_ID_BUSINESS = '6fdb55b4-c905-4612-bd23-306c3918217c'
    APP_CLIENT_SECRET_BUSINESS = 'HThkLCvKhqoxTDV9Y9uS+EvdQ72fbWr/Qrn2PFBZ/Ow='
    APP_REDIRECT_URL = 'https://od.cnbeining.com'

    ACCOUNT_TYPE = AccountTypes.BUSINESS
    APP_DISCOVERY_URL_BUSINESS = 'https://api.office.com/discovery/'
    APP_AUTH_SERVER_URL_BUSINESS = 'https://login.microsoftonline.com/common/oauth2/authorize'
    APP_TOKEN_URL_BUSINESS = 'https://login.microsoftonline.com/common/oauth2/token'
    APP_ENDPOINT = ''

    def __init__(self):
        proxies = getproxies()
        if len(proxies) == 0:
            self.http_provider = onedrivesdk.HttpProvider()
        else:
            from onedrivesdk.helpers.http_provider_with_proxy import HttpProviderWithProxy
            self.http_provider = HttpProviderWithProxy(proxies, verify_ssl=True)

        self.auth_provider = onedrivesdk.AuthProvider(self.http_provider,
                                                 self.APP_CLIENT_ID_BUSINESS,
                                                 auth_server_url=self.APP_AUTH_SERVER_URL_BUSINESS,
                                                 auth_token_url=self.APP_TOKEN_URL_BUSINESS)

        self.auth_url = self.auth_provider.get_auth_url(self.APP_REDIRECT_URL)


    def get_auth_url(self):
        return self.auth_url

    def authenticate(self, code):
        print('Athenticating...')
        self.auth_provider.authenticate(code, self.APP_REDIRECT_URL, self.APP_CLIENT_SECRET_BUSINESS, resource=self.APP_DISCOVERY_URL_BUSINESS)
        
        # this step can be slow
        service_info = ResourceDiscoveryRequest().get_service_info(self.auth_provider.access_token)
        self.APP_ENDPOINT = str(service_info[0]).split()[1]

        print('Refreshing token...')
        self.auth_provider.redeem_refresh_token(self.APP_ENDPOINT)#(service_info.serviceResourceId)
        print('Updating client')
        #TODO: check if can be api/v.1.0
        self.client = onedrivesdk.OneDriveClient(self.APP_ENDPOINT + '_api/v2.0/me', self.auth_provider, self.http_provider)
        print('Authenticated!')

    
    def get_profile(self, user_id='me'):
        """
        Discover the OneDrive for Business resource URI
        reference: https://github.com/OneDrive/onedrive-api-docs/blob/master/auth/aad_oauth.md
        util link: https://github.com/OneDrive/onedrive-api-docs
        """
        url = self.APP_ENDPOINT + '_api/v1.0/me/files/root' #more detailed: ?$expand=children
        headers = {'Authorization': 'Bearer ' + self.auth_provider.access_token}
        proxies = getproxies()
        if len(proxies) == 0:
            proxies = None
        response = requests.get(url, headers=headers, proxies=proxies, verify=True)
        data = response.json()
        if response.status_code != requests.codes.ok:
            raise ValueError('Failed to read user profile:' + data['error']['message'])
        data['account_type'] = self.ACCOUNT_TYPE
        return account_profile_business.OneDriveAccountBusinessProfile(data)

    @property
    def session_expires_in_sec(self):
        return self.client.auth_provider._session.expires_in_sec

    def refresh_session(self, account_id):
        self.client.auth_provider.refresh_token()
        self.save_session(key=od_api_session.get_keyring_key(account_id))

    def save_session(self, key):
        args = {od_api_session.OneDriveAPISession.SESSION_ARG_KEYNAME: key}
        self.client.auth_provider.save_session(**args)

    def load_session(self, key):
        args = {od_api_session.OneDriveAPISession.SESSION_ARG_KEYNAME: key}
        self.client.aut

class OneDriveAuthenticator:

    ACCOUNT_TYPE = AccountTypes.PERSONAL
    APP_CLIENT_ID = '000000004010C916'
    APP_CLIENT_SECRET = 'PimIrUibJfsKsMcd0SqwPBwMTV7NDgYi'
    APP_BASE_URL = 'https://api.onedrive.com/v1.0/'
    APP_REDIRECT_URL = 'https://login.live.com/oauth20_desktop.srf'
    APP_SCOPES = ['wl.signin', 'wl.emails', 'wl.offline_access', 'onedrive.readwrite']

    def __init__(self):
        proxies = getproxies()
        if len(proxies) == 0:
            http_provider = onedrivesdk.HttpProvider()
        else:
            from onedrivesdk.helpers.http_provider_with_proxy import HttpProviderWithProxy
            http_provider = HttpProviderWithProxy(proxies, verify_ssl=True)
        auth_provider = onedrivesdk.AuthProvider(http_provider=http_provider,
                                                 client_id=self.APP_CLIENT_ID,
                                                 session_type=od_api_session.OneDriveAPISession,
                                                 scopes=self.APP_SCOPES)
        self.client = onedrivesdk.OneDriveClient(self.APP_BASE_URL, auth_provider, http_provider)

    def get_auth_url(self):
        return self.client.auth_provider.get_auth_url(self.APP_REDIRECT_URL)

    def authenticate(self, code):
        self.client.auth_provider.authenticate(code, self.APP_REDIRECT_URL, self.APP_CLIENT_SECRET)

    def get_profile(self, user_id='me'):
        """
        Fetch basic profile of the specified user (Live ID).
        :param str user_id: (Optional) ID of the target user.
        :return od_models.account_profile.OneDriveUserProfile:
            An OneDriveUserProfile object that od_models the user info.
        """
        url = 'https://apis.live.net/v5.0/' + user_id
        headers = {'Authorization': 'Bearer ' + self.client.auth_provider.access_token}
        proxies = getproxies()
        if len(proxies) == 0:
            proxies = None
        response = requests.get(url, headers=headers, proxies=proxies, verify=True)
        if response.status_code != requests.codes.ok:
            raise ValueError('Failed to read user profile.')
        data = response.json()
        data['account_type'] = self.ACCOUNT_TYPE
        return account_profile.OneDriveAccountProfile(data)

    @property
    def session_expires_in_sec(self):
        return self.client.auth_provider._session.expires_in_sec

    def refresh_session(self, account_id):
        self.client.auth_provider.refresh_token()
        self.save_session(key=od_api_session.get_keyring_key(account_id))

    def save_session(self, key):
        args = {od_api_session.OneDriveAPISession.SESSION_ARG_KEYNAME: key}
        self.client.auth_provider.save_session(**args)

    def load_session(self, key):
        args = {od_api_session.OneDriveAPISession.SESSION_ARG_KEYNAME: key}
        self.client.auth_provider.load_session(**args)
