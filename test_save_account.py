



import onedrivesdk
from onedrivesdk.helpers import GetAuthCodeServer
from onedrivesdk.helpers.resource_discovery import ResourceDiscoveryRequest

redirect_uri = 'http://localhost:8080'
client_id = your_client_id
client_secret = your_client_secret
discovery_uri = 'https://api.office.com/discovery/'
auth_server_url='https://login.microsoftonline.com/common/oauth2/authorize'
auth_token_url='https://login.microsoftonline.com/common/oauth2/token'

http = onedrivesdk.HttpProvider()
auth = onedrivesdk.AuthProvider(http,
                                client_id,
                                auth_server_url=auth_server_url,
                                auth_token_url=auth_token_url)
auth_url = auth.get_auth_url(redirect_uri)
code = GetAuthCodeServer.get_auth_code(auth_url, redirect_uri)
auth.authenticate(code, redirect_uri, client_secret, resource=discovery_uri)
# If you have access to more than one service, you'll need to decide
# which ServiceInfo to use instead of just using the first one, as below.
service_info = ResourceDiscoveryRequest().get_service_info(auth.access_token)[0]
auth.redeem_refresh_token(service_info.service_resource_id)
client = onedrivesdk.OneDriveClient(service_info.service_resource_id + '/_api/v2.0/', auth, http)

"""
from onedrived import od_api_session

key = '01EHFUNW56Y2GOVW7725BZO354PWSELRRZ'
args = {od_api_session.OneDriveAPISession.SESSION_ARG_KEYNAME: key}
dt = od_api_session.OneDriveAPISession.load_session(**args)
"""





"""
app_id = '0e170d2c-0ac5-4a4f-9099-c6bb0fb52d0c'
app_secret = 'xdGsBCTOiCHxBWJcKyK2WpA'
base_url='https://graph.microsoft.com/v1.0/'
access_token_url='https://login.microsoftonline.com/common/oauth2/v2.0/token'
authorize_url='https://login.microsoftonline.com/common/oauth2/v2.0/authorize'
redirect_url = 'https://onedrivesite.mario-apra.tk/'
scopes = 'offline_access openid User.Read Files.ReadWrite.All'

auth_url = authorize_url + '?client_id=' + app_id + '&response_type=code&redirect_uri=https%3A%2F%2Fonedrivesite.mario-apra.tk%2F&scope=' + scopes.replace(' ', '%20')

code = input()

url = access_token_url

content = {
    'grant_type': 'authorization_code',
    'code': code,
    'redirect_uri': redirect_url,
    'scope': 'User.Read',
    'client_id': app_id,
    'client_secret': app_secret
    }

response = requests.post(url, content)
resp = response.json()

token = resp['access_token']

url = base_url + 'me/'
headers = {'Authorization': 'Bearer ' + token}

response = requests.get(url, headers=headers)
resp = response.json()

data['name'] = resp['displayName']
data['first_name'] = resp['givenName']
data['last_name'] = resp['surname']
data['emails'] = resp['mail']
"""