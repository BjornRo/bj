import json

data = {}
data['login'] = {
    'username': '',
    'password': ''
}

data['site'] = {
    'main': 'https://website.c',
    'sub': '/sub/'
}

with open('data.json', 'w') as f:
    json.dump(data, f, ensure_ascii=False)