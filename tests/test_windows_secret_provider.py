import sys
import ctypes
from ctypes import wintypes
import pytest
from unittest import mock

import modules.windows_secret_provider as wsp

def test_resolve_target():
    assert wsp._resolve_target("quantower_login") == "JulesBridge/quantower_login"
    assert wsp._resolve_target("unknown_target") == "unknown_target"

def test_build_windows_secret_provider():
    with mock.patch("modules.windows_secret_provider.sys.platform", "win32"):
        assert isinstance(wsp.build_windows_secret_provider(), wsp.WindowsSecretProvider)

    with mock.patch("modules.windows_secret_provider.sys.platform", "linux"):
        assert wsp.build_windows_secret_provider() is None

def test_read_windows_credential_wrong_platform():
    with mock.patch("modules.windows_secret_provider.sys.platform", "linux"):
        with pytest.raises(OSError, match="Windows Credential Manager is unavailable"):
            wsp._read_windows_credential("test_target")

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

@pytest.fixture
def mock_advapi32():
    with mock.patch("modules.windows_secret_provider.sys.platform", "win32"):
        with mock.patch("ctypes.windll", create=True) as mock_windll:
            yield mock_windll.advapi32

def test_read_windows_credential_not_found(mock_advapi32):
    mock_advapi32.CredReadW.return_value = False
    with pytest.raises(OSError, match="credential not found for target"):
        wsp._read_windows_credential("target")

def test_read_windows_credential_missing_blob_size(mock_advapi32):
    dummy = CREDENTIAL()
    dummy.UserName = "myuser"
    dummy.CredentialBlobSize = 0

    def mock_CredReadW(target, type_, flags, pcred_ref):
        ptr_ptr = ctypes.cast(pcred_ref, ctypes.POINTER(ctypes.c_void_p))
        ptr_ptr.contents.value = ctypes.addressof(dummy)
        return True

    mock_advapi32.CredReadW.side_effect = mock_CredReadW

    with pytest.raises(OSError, match="credential blob missing for target"):
        wsp._read_windows_credential("target")

def test_read_windows_credential_missing_blob_ptr(mock_advapi32):
    dummy = CREDENTIAL()
    dummy.UserName = "myuser"
    dummy.CredentialBlobSize = 10
    dummy.CredentialBlob = ctypes.cast(None, ctypes.POINTER(ctypes.c_char))

    def mock_CredReadW(target, type_, flags, pcred_ref):
        ptr_ptr = ctypes.cast(pcred_ref, ctypes.POINTER(ctypes.c_void_p))
        ptr_ptr.contents.value = ctypes.addressof(dummy)
        return True

    mock_advapi32.CredReadW.side_effect = mock_CredReadW

    with pytest.raises(OSError, match="credential blob missing for target"):
        wsp._read_windows_credential("target")

def test_read_windows_credential_missing_username(mock_advapi32):
    dummy = CREDENTIAL()
    dummy.UserName = None
    dummy.CredentialBlobSize = 10
    blob = ctypes.create_string_buffer(b"password")
    dummy.CredentialBlob = ctypes.cast(blob, ctypes.POINTER(ctypes.c_char))

    def mock_CredReadW(target, type_, flags, pcred_ref):
        ptr_ptr = ctypes.cast(pcred_ref, ctypes.POINTER(ctypes.c_void_p))
        ptr_ptr.contents.value = ctypes.addressof(dummy)
        return True

    mock_advapi32.CredReadW.side_effect = mock_CredReadW

    with mock.patch("ctypes.string_at") as mock_string_at:
        mock_string_at.return_value = "secretpassword".encode("utf-16-le")
        username, password = wsp._read_windows_credential("target")

        assert username == ""
        assert password == "secretpassword"

def test_read_windows_credential_success(mock_advapi32):
    dummy = CREDENTIAL()
    dummy.UserName = "myuser"
    dummy.CredentialBlobSize = 10
    blob = ctypes.create_string_buffer(b"password")
    dummy.CredentialBlob = ctypes.cast(blob, ctypes.POINTER(ctypes.c_char))

    def mock_CredReadW(target, type_, flags, pcred_ref):
        ptr_ptr = ctypes.cast(pcred_ref, ctypes.POINTER(ctypes.c_void_p))
        ptr_ptr.contents.value = ctypes.addressof(dummy)
        return True

    mock_advapi32.CredReadW.side_effect = mock_CredReadW

    with mock.patch("ctypes.string_at") as mock_string_at:
        mock_string_at.return_value = "secretpassword".encode("utf-16-le")
        username, password = wsp._read_windows_credential("target")

        assert username == "myuser"
        assert password == "secretpassword"

def test_get_secret(mock_advapi32):
    provider = wsp.WindowsSecretProvider()
    with mock.patch("modules.windows_secret_provider._read_windows_credential") as mock_read:
        mock_read.return_value = ("fakeuser", "fakepass")
        result = provider.get_secret("target")
        assert result == {"target": "target", "username": "fakeuser"}
        mock_read.assert_called_once_with("target")

def test_get_secret_with_alias(mock_advapi32):
    provider = wsp.WindowsSecretProvider()
    with mock.patch("modules.windows_secret_provider._read_windows_credential") as mock_read:
        mock_read.return_value = ("fakeuser", "fakepass")
        result = provider.get_secret("quantower_login")
        assert result == {"target": "quantower_login", "username": "fakeuser"}
        mock_read.assert_called_once_with("JulesBridge/quantower_login")

def test_type_password(mock_advapi32):
    provider = wsp.WindowsSecretProvider()
    with mock.patch("modules.windows_secret_provider._read_windows_credential") as mock_read:
        mock_read.return_value = ("fakeuser", "fakepass")

        type_func = mock.MagicMock()
        press_key_func = mock.MagicMock()

        provider.type_password("target", type_func, press_key_func)

        mock_read.assert_called_once_with("target")
        press_key_func.assert_called_once_with("tab")
        type_func.assert_called_once_with("fakepass")
