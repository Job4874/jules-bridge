import requests

try:
    resp = requests.get('http://127.0.0.1:5000/remote/screen')
    print("Status code:", resp.status_code)
except Exception as e:
    print(e)
