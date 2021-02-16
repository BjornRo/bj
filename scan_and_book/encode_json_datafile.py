import json

data = {}

data['login'] = []
data['login'].append({
    'username': '',
    'password': ''
})

data['site'] = []
data['site'].append({
    'main': 'https://website.c',
    'sub': '/sub/'
})

with open('data.json', 'w') as f:
    json.dump(data, f, ensure_ascii=False)