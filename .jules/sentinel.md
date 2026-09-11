## 2026-07-23 - Path Traversal Vulnerability
**Vulnerability:** fs_service operations lack path confinement, enabling directory traversal
**Learning:** Path traversal is a common vulnerability when reading files based on unsanitized inputs, even with `os.path.abspath` if no boundary is enforced.
**Prevention:** Always restrict resolved paths to an explicit `ALLOWED_BASE` directory using `is_relative_to()`.
