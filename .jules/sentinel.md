## 2026-07-23 - Path Traversal in fs_service
**Vulnerability:** The `fs_service.py` functions accepted arbitrary file paths as input without path normalization or prefix validation. A caller could theoretically pass `../../etc/passwd` or absolute paths outside an intended directory.
**Learning:** This existed because the fs_service was built as a thin wrapper around native `os` filesystem calls. We need to implement defensive boundaries before accessing OS primitives.
**Prevention:** Always normalize incoming paths (`os.path.abspath`) and assert they start with an allowed base directory (`ALLOWED_BASE`) before executing any file operations.
