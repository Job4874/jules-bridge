import urllib.request
import json

headers={'Authorization': 'Bearer JULES-SECURE-999', 'Content-Type': 'application/json', 'Accept': 'application/json'}
body = {
    'command': 'Select-String -Path "C:\\Quantower\\Logs\\Serilog\\*.slog" -Pattern "BROKER_SUBMISSION_BLOCKED_DRY_RUN" -ErrorAction SilentlyContinue | Select-Object -First 10',
    'shell': 'powershell'
}
req = urllib.request.Request('http://127.0.0.1:5000/shell', data=json.dumps(body).encode(), headers=headers, method='POST')
try:
    print(urllib.request.urlopen(req).read().decode())
except Exception as e:
    print(e)
