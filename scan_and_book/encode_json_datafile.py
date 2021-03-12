import json

data = {}

data['login'] = {
    'username': '',
    'password': ''
}

data['site'] = {
    'protocol': 'https://',
    'hostname': 'site.this',
    'path': '/path',
    'query': "?value1=&value2="
}

data['cookies'] = {
    'first': ''
}

with open('data.json', 'w') as f:
    json.dump(data, f, ensure_ascii=False)