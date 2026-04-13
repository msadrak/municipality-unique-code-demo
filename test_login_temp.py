import urllib.request, json
try:
    req = urllib.request.Request(
        'http://127.0.0.1:8000/auth/login',
        method='POST',
        data=b'{"username":"admin", "password":"admin"}',
        headers={'Content-Type': 'application/json', 'Accept': 'application/json'}
    )
    res = urllib.request.urlopen(req)
    print('SUCCESS:', res.read().decode('utf-8'))
except Exception as e:
    print('HTTP ERROR:', e)
    if hasattr(e, 'read'):
        print('BODY:', e.read().decode('utf-8', errors='ignore'))
