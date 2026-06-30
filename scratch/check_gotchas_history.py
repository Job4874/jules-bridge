import subprocess

commits = ["51ffea2", "21828ce", "2c8d0c8", "ef09cb1", "6481f0c", "e6e2b77", "184e9ed", "02b0835", "5ddf4ec", "5a2d5e0"]

for commit in commits:
    try:
        # run git show commit:context/05_gotchas.md
        res = subprocess.run(
            ["git", "show", f"{commit}:context/05_gotchas.md"],
            capture_output=True,
            check=True
        )
        data = res.stdout
        print(f"\nCommit {commit}: size={len(data)} bytes")
        # try to see if it starts with UTF-16 BOM or looks like Chinese in UTF-8
        try:
            text = data.decode("utf-8")
            print(f"  UTF-8 decoded start (repr): {repr(text[:100])}")
        except Exception as e:
            print(f"  UTF-8 decode failed: {e}")
            
        try:
            text_u16 = data.decode("utf-16-le")
            print(f"  UTF-16LE decoded start (repr): {repr(text_u16[:100])}")
        except Exception as e:
            print(f"  UTF-16LE decode failed: {e}")
            
    except Exception as e:
        print(f"Failed to show commit {commit}: {e}")
