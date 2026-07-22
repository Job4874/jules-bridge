import subprocess, time, sys

SESSION_ID = '8503583543641914961'
JULES_BIN = r'C:\Users\S02748217\.npm-packages\bin\jules.exe'

print(f'Continuing polling watcher for session {SESSION_ID}...')

start_time = time.time()
timeout_s = 600

while time.time() - start_time < timeout_s:
    try:
        res = subprocess.run([JULES_BIN, 'remote', 'list', '--session'], capture_output=True, text=True, check=True)
        lines = res.stdout.splitlines()
        target_status = None
        for line in lines:
            if SESSION_ID in line:
                target_status = line.strip().split()[-1]
                break
        
        elapsed = int(time.time() - start_time)
        print(f'[{elapsed}s] Session {SESSION_ID} status: {target_status}')
        
        if target_status in ('Completed', 'FAILED', 'Failed', 'Feedback'):
            print(f'Final session status reached: {target_status}')
            break
    except Exception as e:
        print('Error polling session status:', e)
    
    time.sleep(20)

