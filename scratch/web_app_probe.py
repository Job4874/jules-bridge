import urllib.request, json, os

results = {}

req = urllib.request.urlopen('http://127.0.0.1:5173/')
html = req.read().decode('utf-8')
results['vite_server_status'] = req.status
results['vite_html_length'] = len(html)
results['vite_contains_root_div'] = '<div id=" root\>' in html
results['vite_contains_main_jsx'] = 'src/main.jsx' in html

token = 'JULES-SECURE-999'
headers = {'Authorization': 'Bearer ' + token}
req2 = urllib.request.Request('http://127.0.0.1:5000/dashboard/status', headers=headers)
with urllib.request.urlopen(req2) as resp:
 dash_json = json.loads(resp.read().decode('utf-8'))
 results['bridge_dashboard_status_code'] = resp.status
 results['bridge_dashboard_online'] = dash_json.get('bridge', {}).get('status') == 'running'
 results['execution_context'] = dash_json.get('execution_context')
 results['quant_allowed'] = dash_json.get('quant_allowed')

dist_dir = 'dashboard-ui/dist'
if os.path.exists(dist_dir):
 assets = os.listdir(os.path.join(dist_dir, 'assets'))
 results['production_bundle_exists'] = True
 results['production_assets'] = assets
 results['dist_index_html_size'] = os.path.getsize(os.path.join(dist_dir, 'index.html'))

print(json.dumps(results, indent=2))
