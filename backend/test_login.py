import urllib.request
import urllib.error
import json

url = 'http://127.0.0.1:8000/api/auth/login'
data = json.dumps({
    'student_number': '2024001',
    'email': 'student1@ue.edu.ph',
    'access_code': 'ACCESS123',
    'antibot': 'HELLO',
}).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
try:
    with urllib.request.urlopen(req, timeout=10) as r:
        print('HTTP', r.status)
        print(r.read().decode())
except urllib.error.HTTPError as e:
    print('HTTPERROR', e.code)
    print(e.read().decode())
except Exception as e:
    print('ERROR', e)
