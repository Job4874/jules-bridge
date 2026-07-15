# pylint: disable=invalid-name

"""write_vm_env.py — write VM environment variables."""
import re
import socket

env = open(r'C:\Users\abdul\.jules\.env', encoding='utf-8').read()
gk = re.search(r'GEMINI_API_KEY=([^\r\n]+)', env).group(1).strip()
ork_m = re.search(r'OPENROUTER_API_KEY=([^\r\n]+)', env)
ork = ork_m.group(1).strip() if ork_m else ''

# Get LAN IP
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))
ip = s.getsockname()[0]
s.close()

content = f"GEMINI_API_KEY={gk}\nOPENROUTER_API_KEY={ork}\nLOCAL_BRIDGE_URL=http://{ip}:5000\nLOCAL_BRIDGE_TOKEN=JULES-SECURE-999\n"
with open(r'C:\Users\abdul\.jules\scratch\vm.env', 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Written: GEMINI={gk[:12]}... OR={ork[:12]}... LAN={ip}")
