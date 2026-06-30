import os

with open('bridge.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'secret_provider=' not in content:
    content = content.replace(
        'allow_secret_use=allow_secret_use,',
        'allow_secret_use=allow_secret_use,\n        secret_provider=type("LocalProvider", (), {"get_secret": lambda self, t: {"username": "ABDUL487417@Icloud.com"}})(),'
    )
    with open('bridge.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("[+] Bridge patched successfully! Local secret provider injected.")
else:
    print("Bridge is already patched.")
