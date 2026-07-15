import sys
import re
import os

def insert_pylint_disable(path, disable_string):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    if 'pylint: disable=' + disable_string not in content:
        content = f'# pylint: disable={disable_string}\n\n' + content
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

# tests/test_bridge_routes.py
path = r'c:\Users\abdul\.jules\tests\test_bridge_routes.py'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()
c = c.replace('def test_shell_invalid_git_bash(self, mock_which):', 'def test_shell_invalid_git_bash(self, _mock_which):')
with open(path, 'w', encoding='utf-8') as f:
    f.write(c)

# tests/test_fs_service.py
path = r'c:\Users\abdul\.jules\tests\test_fs_service.py'
insert_pylint_disable(path, 'import-outside-toplevel')
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()
c = c.replace('open(path, "r")', 'open(path, "r", encoding="utf-8")')
c = c.replace('open(os.path.join(d, "file.txt"), "w")', 'open(os.path.join(d, "file.txt"), "w", encoding="utf-8")')
c = c.replace('open(os.path.join(d, "z_file.txt"), "w")', 'open(os.path.join(d, "z_file.txt"), "w", encoding="utf-8")')
with open(path, 'w', encoding='utf-8') as f:
    f.write(c)

# tests/test_inbox_service.py
path = r'c:\Users\abdul\.jules\tests\test_inbox_service.py'
insert_pylint_disable(path, 'import-outside-toplevel, unused-variable')
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()
c = c.replace('open(path, "w")', 'open(path, "w", encoding="utf-8")')
c = c.replace('open(os.path.join(d, "OTHER.md"), "w")', 'open(os.path.join(d, "OTHER.md"), "w", encoding="utf-8")')
c = c.replace('open(os.path.join(d, "safe.md"), "w")', 'open(os.path.join(d, "safe.md"), "w", encoding="utf-8")')
c = c.replace('open(path, "r")', 'open(path, "r", encoding="utf-8")')
with open(path, 'w', encoding='utf-8') as f:
    f.write(c)

# tests/test_oracle_session.py
path = r'c:\Users\abdul\.jules\tests\test_oracle_session.py'
insert_pylint_disable(path, 'import-outside-toplevel')
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()
lines = c.splitlines()
lines = [l for l in lines if 'import subprocess' not in l and 'MagicMock' not in l]
c = '\n'.join(lines)
c = c.replace('open(os.path.join(d, "a.md"), "w")', 'open(os.path.join(d, "a.md"), "w", encoding="utf-8")')
c = c.replace('open(os.path.join(d, "b.md"), "w")', 'open(os.path.join(d, "b.md"), "w", encoding="utf-8")')
with open(path, 'w', encoding='utf-8') as f:
    f.write(c)

# tests/test_ui_automation.py
path = r'c:\Users\abdul\.jules\tests\test_ui_automation.py'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()
c = c.replace('import tempfile as _tmp  # pylint: disable=import-outside-toplevel', 'import tempfile as _tmp  # pylint: disable=import-outside-toplevel, reimported')
with open(path, 'w', encoding='utf-8') as f:
    f.write(c)

# tests/test_shell_executor.py
path = r'c:\Users\abdul\.jules\tests\test_shell_executor.py'
insert_pylint_disable(path, 'import-outside-toplevel')

# modules/ui_automation.py
path = r'c:\Users\abdul\.jules\modules\ui_automation.py'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()
c = c.replace('import pyautogui as _pag  # noqa: PLC0415', 'import pyautogui as _pag  # noqa: PLC0415  # pylint: disable=import-outside-toplevel')
with open(path, 'w', encoding='utf-8') as f:
    f.write(c)

# modules/vm_relay.py
path = r'c:\Users\abdul\.jules\modules\vm_relay.py'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()
c = c.replace('import requests as _req', 'import requests as _req  # pylint: disable=import-outside-toplevel')
with open(path, 'w', encoding='utf-8') as f:
    f.write(c)

print('Done test fixes')
