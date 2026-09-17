## 2026-09-17 - Path Traversal in File System Service
**Vulnerability:** The fs_service module exposed endpoints for read/write/tail/grep without any path traversal defense, allowing reading/writing files anywhere on the system (like ../../etc/passwd).
**Learning:** This existed because file paths were directly passed to Python file I/O operations without being validated against a base directory. Relying on API route layers for input validation failed as there are many direct internal consumers of fs_service.
**Prevention:** In the future, always validate absolute file paths using `pathlib.Path.is_relative_to(ALLOWED_BASE)` at the lowest possible data access tier to provide defense-in-depth against path traversal vulnerabilities.
