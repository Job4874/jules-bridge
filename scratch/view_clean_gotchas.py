import subprocess

commit = "2c8d0c8"
try:
    res = subprocess.run(
        ["git", "show", f"{commit}:context/05_gotchas.md"],
        capture_output=True,
        check=True
    )
    content = res.stdout.decode("utf-8")
    print("Content length:", len(content))
    print("Contains 'memory/quantower.md'?", "memory/quantower.md" in content)
    
    with open("scratch/gotchas_clean.md", "w", encoding="utf-8") as f:
        f.write(content)
    print("Wrote clean gotchas to scratch/gotchas_clean.md")
except Exception as e:
    print("Failed:", e)
