


import requests


app_id = '0e170d2c-0ac5-4a4f-9099-c6bb0fb52d0c'
app_secret = 'xdGsBCTOiCHxBWJcKyK2WpA'
base_url='https://graph.microsoft.com/v1.0/'
access_token_url='https://login.microsoftonline.com/common/oauth2/v2.0/token'
authorize_url='https://login.microsoftonline.com/common/oauth2/v2.0/authorize'


url = authorize_url + '?client_id=' + app_id + '&response_type=code&redirect_uri=https%3A%2F%2Fonedrivesite.mario-apra.tk%2F&scope=User.Read'
print(url)
code = input()

url = access_token_url

content = {
    'grant_type': 'authorization_code',
    'code': code,
    'redirect_uri': 'https://onedrivesite.mario-apra.tk/',
    'scope': 'User.Read',
    'client_id': app_id,
    'client_secret': app_secret
    }

response = requests.post(url, content)
data = response.json()

token = data['access_token']

url = base_url + 'me/'
headers = {'Authorization': 'Bearer ' + token}

response = requests.get(url, headers=headers)
data = response.json()

name = data['displayName']
givenName = data['givenName']
surName = data['surname']
email = data['mail']
id = data['id']



url += 'root/files/root/'
response = requests.get(url, headers=headers)
data = response.json()
print('data: \n' + str(data))


#response = requests.get(url)
#data = response.json
#print(data)