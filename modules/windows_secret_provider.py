"""Windows Credential Manager-backed secret provider for Local Node execution."""

from __future__ import annotations

import sys
from collections.abc import Callable
from typing import Any

TARGET_ALIASES = {
    "quantower_login": "JulesBridge/quantower_login",
}


class WindowsSecretProvider:
    """Read operator secrets from Windows Credential Manager.

    Plaintext secrets never leave the provider boundary except through
    injected UI action callbacks (``type_func`` / ``press_key_func``).
    """

    def get_secret(self, target: str) -> dict[str, str]:
        username, _password = _read_windows_credential(_resolve_target(target))
        return {"target": target, "username": username}

    def type_password(
        self,
        target: str,
        type_func: Callable[[str], Any],
        press_key_func: Callable[[str], Any],
    ) -> None:
        _username, password = _read_windows_credential(_resolve_target(target))
        press_key_func("tab")
        type_func(password)


def _resolve_target(target: str) -> str:
    return TARGET_ALIASES.get(target, target)


def _read_windows_credential(target: str) -> tuple[str, str]:
    if sys.platform != "win32":
        raise OSError("Windows Credential Manager is unavailable on this platform")

    import ctypes
    from ctypes import wintypes

    advapi32 = ctypes.windll.advapi32

    class CREDENTIAL(ctypes.Structure):
        _fields_ = [
            ("Flags", wintypes.DWORD),
            ("Type", wintypes.DWORD),
            ("TargetName", wintypes.LPWSTR),
            ("Comment", wintypes.LPWSTR),
            ("LastWritten", wintypes.FILETIME),
            ("CredentialBlobSize", wintypes.DWORD),
            ("CredentialBlob", ctypes.POINTER(ctypes.c_char)),
            ("Persist", wintypes.DWORD),
            ("AttributeCount", wintypes.DWORD),
            ("Attributes", ctypes.c_void_p),
            ("TargetAlias", wintypes.LPWSTR),
            ("UserName", wintypes.LPWSTR),
        ]

    pcred = ctypes.POINTER(CREDENTIAL)()
    if not advapi32.CredReadW(target, 1, 0, ctypes.byref(pcred)):
        raise OSError(f"credential not found for target {target!r}")

    try:
        username = pcred.contents.UserName or ""
        blob_size = int(pcred.contents.CredentialBlobSize)
        if blob_size <= 0 or not pcred.contents.CredentialBlob:
            raise OSError(f"credential blob missing for target {target!r}")
        raw = ctypes.string_at(pcred.contents.CredentialBlob, blob_size)
        password = raw.decode("utf-16-le")
        return username, password
    finally:
        advapi32.CredFree(pcred)


def build_windows_secret_provider() -> WindowsSecretProvider | None:
    if sys.platform != "win32":
        return None
    return WindowsSecretProvider()
