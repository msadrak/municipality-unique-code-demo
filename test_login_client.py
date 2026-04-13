import sys
sys.path.append('.')
import traceback
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
try:
    response = client.post('/auth/login', json={'username': 'admin', 'password': 'admin'})
    print('STATUS:', response.status_code)
    print('JSON:', response.json())
except Exception as e:
    print('APP CRASHED:')
    traceback.print_exc()
