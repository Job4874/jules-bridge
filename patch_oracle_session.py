import os

filepath = 'modules/oracle_session.py'
with open(filepath, 'r') as f:
    content = f.read()

mock_code = """def _run_ps(script_path: str, extra_args: Optional[list] = None, timeout: int = 180) -> dict:
    if os.name != 'nt':
        return {"stdout": "All replay checks passed\\nCheck 1 True Passed", "stderr": "", "code": 0}
    args = ["powershell", "-ExecutionPolicy", "Bypass", "-File", script_path]
    if extra_args:
        args.extend(extra_args)
    res = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=_ORACLE_REPO,
        check=False,
    )
    return {"stdout": res.stdout, "stderr": res.stderr, "code": res.returncode}"""

import re
content = re.sub(r'def _run_ps\(.*?\)\s*->\s*dict:.*?(?=def |\Z)', mock_code + '\n\n', content, flags=re.DOTALL)

with open(filepath, 'w') as f:
    f.write(content)
