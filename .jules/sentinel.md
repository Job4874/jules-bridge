## 2026-07-23 - Path Traversal Vulnerability in fs_service
**Vulnerability:** The fs_service module functions (`read`, `write`, `tail`, `grep`, `list_dir`) accept arbitrary file paths without normalization or prefix validation, allowing potential access outside intended directories (e.g., via `../../`).
**Learning:** Relying solely on `os.path.exists()` or expecting HTTP boundary checks is insufficient. Path traversal defenses must explicitly resolve paths and restrict them to a known secure base to provide defense-in-depth at the filesystem operation layer.
**Prevention:** Use `pathlib.Path(os.path.abspath(path)).is_relative_to(ALLOWED_BASE)` to rigorously validate that the resolved absolute path falls safely within the permitted base directory, preventing string prefix bypasses.
