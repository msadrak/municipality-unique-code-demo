import requests

session = requests.Session()
login = session.post('http://localhost:8000/auth/login', data={
    'username': 'contractor',
    'password': '123456'
})
print(f'Login: {login.status_code}')

resp = session.get('http://localhost:8000/portal/user/allowed-activities')
print(f'API: {resp.status_code}')

data = resp.json()
subs = data.get('allowed_subsystems', [])
print(f'Subsystems: {len(subs)}')
for s in subs:
    print(f"  {s['id']}: {s['title']} - {len(s['activities'])} activities")
