from fastapi.testclient import TestClient
from app.main import app
import pathlib, json

client = TestClient(app)

print('--- POST consent ---')
r = client.post('/api/auth/consent', json={'session_id':'test123','consent_given':True})
print(r.status_code, r.json())

path = pathlib.Path('logs/consents.json')
print('consents exists', path.exists())
if path.exists():
    print(path.read_text())

print('--- POST virtual agent ---')
r2 = client.post('/virtual-agent', json={'message':'hello session','session_id':'test123'})
print(r2.status_code, r2.json())

p2 = pathlib.Path('logs/interactions.json')
print('interactions exists', p2.exists())
if p2.exists():
    print(p2.read_text())
