## 2024-05-18 - Avoid reading full files into memory
**Learning:** `Path.read_text().splitlines()` reads the entire file into memory before iterating over lines, creating memory overhead.
**Action:** Use `with Path.open() as f: for line in f:` to lazily stream and process file contents line by line.
