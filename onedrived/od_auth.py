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
from onedrivesdk.helpers.resource_discovery import ResourceDiscoveryRequest
import os
import yaml

from . import od_api_session
from .od_models import account_profile

PATH = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
with open(os.path.join(PATH, 'onedrived', 'data', 'security_config.yml')) as config:
    SECURITY_CONFIG = yaml.load(config)


def get_authenticator_and_drives(context, account_id):
    # TODO: Ideally we should recursively get all drives because the API pages
    # them.
    account_type = context.config['accounts'][account_id]['account_type']
    if account_type == account_profile.AccountTypes.PERSONAL:
        authenticator = OneDriveAuthenticator()
    elif account_type == account_profile.AccountTypes.BUSINESS:
        endpoint = context.config['accounts'][account_id]['webUrl']
        endpoint = endpoint[:endpoint.find(
            '-my.sharepoint.com/')] + '-my.sharepoint.com/'
        authenticator = OneDriveBusinessAuthenticator(endpoint)
    else:
        logging.error("Error loading session: account_type don't exists")
        return

    try:
        authenticator.load_session(
            key=od_api_session.get_keyring_key(account_id))
        if account_type == account_profile.AccountTypes.BUSINESS:
            authenticator.refresh_session(account_id)
        drives = authenticator.client.drives.get()
    except (onedrivesdk.error.OneDriveError, RuntimeError) as e:
        logging.error('Error loading session: %s. Try refreshing token.', e)
        authenticator.refresh_session(account_id)
        drives = authenticator.client.drives.get()
    return authenticator, drives


class OneDriveBusinessAuthenticator:

    # This is to use OAuth v1
    APP_CLIENT_ID_BUSINESS = SECURITY_CONFIG['BUSINESS_V1']['CLIENT_ID']
    APP_CLIENT_SECRET_BUSINESS = SECURITY_CONFIG['BUSINESS_V1']['CLIENT_SECRET']
    APP_REDIRECT_URL = SECURITY_CONFIG['BUSINESS_V1']['REDIRECT']
    # This is to use OAuth v2 (Graph)
    APP_ID = SECURITY_CONFIG['BUSINESS_V2']['CLIENT_ID']
    APP_SECRET = SECURITY_CONFIG['BUSINESS_V2']['CLIENT_SECRET']
    REDIRECT_URL = SECURITY_CONFIG['BUSINESS_V2']['REDIRECT']

    ACCOUNT_TYPE = account_profile.AccountTypes.BUSINESS
    APP_DISCOVERY_URL_BUSINESS = 'https://api.office.com/discovery/'
    APP_AUTH_SERVER_URL_BUSINESS = 'https://login.microsoftonline.com/common/oauth2/authorize'
    APP_TOKEN_URL_BUSINESS = 'https://login.microsoftonline.com/common/oauth2/token'

    BASE_URL = 'https://graph.microsoft.com/v1.0/'
    ACCESS_TOKEN_URL = 'https://login.microsoftonline.com/common/oauth2/v2.0/token'
    AUTORIZE_URL = 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize'

    def __init__(self, endpoint=None):
        self.code = None
        proxies = getproxies()
        if len(proxies) == 0:
            self.http_provider = onedrivesdk.HttpProvider()
        else:
            from onedrivesdk.helpers.http_provider_with_proxy import HttpProviderWithProxy
            self.http_provider = HttpProviderWithProxy(
                proxies, verify_ssl=True)

        self.auth_provider = onedrivesdk.AuthProvider(
            self.http_provider,
            self.APP_CLIENT_ID_BUSINESS,
            session_type=od_api_session.OneDriveAPISession,
            auth_server_url=self.APP_AUTH_SERVER_URL_BUSINESS,
            auth_token_url=self.APP_TOKEN_URL_BUSINESS)

        if endpoint is not None:
            self.client = onedrivesdk.OneDriveClient(
                endpoint + '_api/v2.0/', self.auth_provider, self.http_provider)

    def get_auth_url(self):
        return self.auth_provider.get_auth_url(self.APP_REDIRECT_URL)

    def authenticate(self, code):
        print('Athenticating...')
        self.auth_provider.authenticate(
            code,
            self.APP_REDIRECT_URL,
            self.APP_CLIENT_SECRET_BUSINESS,
            resource=self.APP_DISCOVERY_URL_BUSINESS)

        # this step can be slow
        service_info = ResourceDiscoveryRequest().get_service_info(
            self.auth_provider.access_token)

        self.APP_ENDPOINT = str(service_info[0]).split()[1]

        print('Refreshing token...')
        self.auth_provider.redeem_refresh_token(self.APP_ENDPOINT)
        print('Updating client')
        self.client = onedrivesdk.OneDriveClient(
            self.APP_ENDPOINT + '_api/v2.0/',
            self.auth_provider,
            self.http_provider)
        print('Authenticated!')

    def get_profile(self):
        """
        Discover the OneDrive for Business resource URI
        reference: https://github.com/OneDrive/onedrive-api-docs/blob/master/auth/aad_oauth.md
        util link: https://github.com/OneDrive/onedrive-api-docs
        """
        # more detailed: ?$expand=children
        url = self.APP_ENDPOINT + '_api/v1.0/me/files/root'
        headers = {'Authorization': 'Bearer ' +
                   self.auth_provider.access_token}
        proxies = getproxies()
        if len(proxies) == 0:
            proxies = None
        response = requests.get(
            url,
            headers=headers,
            proxies=proxies,
            verify=True)
        data = response.json()
        if response.status_code != requests.codes.ok:
            raise ValueError(
                'Failed to read user profile:' +
                data['error']['message'])
        data['account_type'] = self.ACCOUNT_TYPE
        url = self.ACCESS_TOKEN_URL

        content = {
            'grant_type': 'authorization_code',
            'code': self.code,
            'redirect_uri': self.REDIRECT_URL,
            'scope': 'User.Read',
            'client_id': self.APP_ID,
            'client_secret': self.APP_SECRET
        }

        response = requests.post(url, content)
        resp = response.json()
        token = resp['access_token']
        data['refresh_token'] = token

        url = self.BASE_URL + 'me/'
        headers = {'Authorization': 'Bearer ' + token}

        response = requests.get(url, headers=headers)
        resp = response.json()

        data['name'] = resp['displayName']
        data['first_name'] = resp['givenName']
        data['last_name'] = resp['surname']
        data['emails'] = resp['mail']

        # End user information
        return account_profile.OneDriveAccountBusiness(data)

    @property
    def authentication_url(self):
        return "{auth_url}?client_id={app_id}&response_type=code" \
               "&redirect_uri={redirect_url}&scope=User.Read".format(
                   auth_url=self.AUTORIZE_URL,
                   app_id=self.APP_ID,
                   redirect_url=self.REDIRECT_URL)

    @property
    def session_expires_in_sec(self):
        # TODO: check this
        print('expires in: ' +
              str(self.client.auth_provider._session.expires_in_sec))
        return self.client.auth_provider._session.expires_in_sec

    def refresh_session(self, account_id):
        # TODO: check this
        self.client.auth_provider.refresh_token()
        self.save_session(key=od_api_session.get_keyring_key(account_id))
        print('session refreshed')

    def save_session(self, key):
        # TODO: check this
        args = {od_api_session.OneDriveAPISession.SESSION_ARG_KEYNAME: key}
        self.client.auth_provider.save_session(**args)
        # print('Business session saved!')

    def load_session(self, key):
        # TODO: check this
        args = {od_api_session.OneDriveAPISession.SESSION_ARG_KEYNAME: key}
        self.client.auth_provider.load_session(**args)
        print('session loaded')


class OneDriveAuthenticator:

    ACCOUNT_TYPE = account_profile.AccountTypes.PERSONAL
    APP_CLIENT_ID = SECURITY_CONFIG['PERSONAL']['CLIENT_ID']
    APP_CLIENT_SECRET = SECURITY_CONFIG['PERSONAL']['CLIENT_SECRET']
    APP_REDIRECT_URL = SECURITY_CONFIG['PERSONAL']['REDIRECT']

    APP_BASE_URL = 'https://api.onedrive.com/v1.0/'
    APP_SCOPES = [
        'wl.signin',
        'wl.emails',
        'wl.offline_access',
        'onedrive.readwrite']

    def __init__(self):
        proxies = getproxies()
        if len(proxies) == 0:
            http_provider = onedrivesdk.HttpProvider()
        else:
            from onedrivesdk.helpers.http_provider_with_proxy import HttpProviderWithProxy
            http_provider = HttpProviderWithProxy(proxies, verify_ssl=True)
        auth_provider = onedrivesdk.AuthProvider(
            http_provider=http_provider,
            client_id=self.APP_CLIENT_ID,
            session_type=od_api_session.OneDriveAPISession,
            scopes=self.APP_SCOPES)
        self.client = onedrivesdk.OneDriveClient(
            self.APP_BASE_URL, auth_provider, http_provider)

    def get_auth_url(self):
        return self.client.auth_provider.get_auth_url(self.APP_REDIRECT_URL)

    def authenticate(self, code):
        self.client.auth_provider.authenticate(
            code, self.APP_REDIRECT_URL, self.APP_CLIENT_SECRET)

    def get_profile(self, user_id='me'):
        """
        Fetch basic profile of the specified user (Live ID).
        :param str user_id: (Optional) ID of the target user.
        :return od_models.account_profile.OneDriveUserProfile:
            An OneDriveUserProfile object that od_models the user info.
        """
        url = 'https://apis.live.net/v5.0/' + user_id
        headers = {'Authorization': 'Bearer ' +
                   self.client.auth_provider.access_token}
        proxies = getproxies()
        if len(proxies) == 0:
            proxies = None
        response = requests.get(
            url,
            headers=headers,
            proxies=proxies,
            verify=True)
        if response.status_code != requests.codes.ok:
            raise ValueError('Failed to read user profile.')
        data = response.json()
        data['account_type'] = self.ACCOUNT_TYPE
        return account_profile.OneDriveAccountPersonal(data)

    @property
    def session_expires_in_sec(self):
        return self.client.auth_provider._session.expires_in_sec

    def refresh_session(self, account_id):
        self.client.auth_provider.refresh_token()
        self.save_session(key=od_api_session.get_keyring_key(account_id))

    def save_session(self, key):
        print('save_session Personal with key: ' + key)
        args = {od_api_session.OneDriveAPISession.SESSION_ARG_KEYNAME: key}
        self.client.auth_provider.save_session(**args)
        print('Personal session saved!')

    def load_session(self, key):
        args = {od_api_session.OneDriveAPISession.SESSION_ARG_KEYNAME: key}
        self.client.auth_provider.load_session(**args)
