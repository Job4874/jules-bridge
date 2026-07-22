import urllib.request, json, time, sys

BASE_URL = 'http://127.0.0.1:5000'
TOKEN = 'JULES-SECURE-999'
HEADERS = {'Authorization': 'Bearer ' + TOKEN, 'Content-Type': 'application/json'}

def post(endpoint, data):
    t0 = time.perf_counter()
    req = urllib.request.Request(BASE_URL + endpoint, data=json.dumps(data).encode('utf-8'), headers=HEADERS)
    with urllib.request.urlopen(req) as resp:
        body = json.loads(resp.read().decode('utf-8'))
        dt = (time.perf_counter() - t0) * 1000
        return resp.status, dt, body

def get(endpoint):
    t0 = time.perf_counter()
    req = urllib.request.Request(BASE_URL + endpoint, headers=HEADERS)
    with urllib.request.urlopen(req) as resp:
        body = json.loads(resp.read().decode('utf-8'))
        dt = (time.perf_counter() - t0) * 1000
        return resp.status, dt, body

benchmark = {}

# Workflow 1: Liveness & Identity
status, dt1, body1 = get('/health')
status, dt2, body2 = get('/ping')
benchmark['workflow_1_diagnostics_ms'] = round(dt1 + dt2, 2)
benchmark['host_identity'] = body2.get('identity')

# Workflow 2: File System & Knowledge
status, dt3, body3 = post('/fs/list', {'path': '.'})
status, dt4, body4 = get('/akc/readiness')
benchmark['workflow_2_file_and_akc_ms'] = round(dt3 + dt4, 2)
benchmark['akc_status'] = body4.get('checkpoint_status')

# Workflow 3: Shell Execution
status, dt5, body5 = post('/shell', {'command': 'echo EndUserBenchmarkOK', 'shell': 'cmd'})
benchmark['workflow_3_shell_ms'] = round(dt5, 2)
benchmark['shell_output'] = body5.get('stdout', '').strip()

# Workflow 4: Dashboard Telemetry & Resource Check
status, dt6, body6 = get('/dashboard/status')
status, dt7, body7 = post('/vm/resource_pressure', {})
benchmark['workflow_4_dashboard_ms'] = round(dt6 + dt7, 2)
benchmark['execution_context'] = body6.get('execution_context')

# Workflow 5: Reasoning & Task Dispatch
status, dt8, body8 = post('/reasoning/plan', {'problem': 'End-user automated benchmark plan', 'model': 'stub'})
status, dt9, body9 = post('/jules/cycle', {'dry_run': True})
benchmark['workflow_5_reasoning_ms'] = round(dt8 + dt9, 2)
benchmark['reasoning_steps'] = len(body8.get('plan', {}).get('steps', []))

# Summary
total_time_ms = sum([
    benchmark['workflow_1_diagnostics_ms'],
    benchmark['workflow_2_file_and_akc_ms'],
    benchmark['workflow_3_shell_ms'],
    benchmark['workflow_4_dashboard_ms'],
    benchmark['workflow_5_reasoning_ms']
])
benchmark['total_end_to_end_user_session_ms'] = round(total_time_ms, 2)

print(json.dumps(benchmark, indent=2))
