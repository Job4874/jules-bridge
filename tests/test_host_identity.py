"""Tests for modules/host_identity.py."""

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from modules import host_identity


class TestHostIdentity(unittest.TestCase):
    def setUp(self):  # pylint: disable=invalid-name
        self._orig_env = os.environ.copy()

    def tearDown(self):  # pylint: disable=invalid-name
        os.environ.clear()
        os.environ.update(self._orig_env)

    def test_get_host_identity_uses_env_label(self):
        os.environ["JULES_IDENTITY"] = "School-64GB-Workstation-ID-64"
        os.environ["JULES_CONTEXT"] = "[SCHOOL_COMPUTE]"
        payload = host_identity.get_host_identity()
        self.assertEqual(payload["identity"], "School-64GB-Workstation-ID-64")
        self.assertEqual(payload["execution_context"], "[SCHOOL_COMPUTE]")

    def test_get_host_identity_reads_system_id_file(self):
        with patch.object(host_identity, "_read_system_id_file", return_value="School-PC-RAM-64-GB"):
            os.environ.pop("JULES_IDENTITY", None)
            payload = host_identity.get_host_identity()
        self.assertEqual(payload["system_id_file"], "School-PC-RAM-64-GB")
        self.assertEqual(payload["identity"], "School-PC-RAM-64-GB")

    def test_gpg_key_id_from_public_file(self):
        sample = Path(__file__).parent / "fixtures" / "sample_gpg_public.asc"
        sample.parent.mkdir(exist_ok=True)
        sample.write_text(
            "-----BEGIN PGP PUBLIC KEY BLOCK-----\n"
            "pub   rsa4096/D9BC48A619204DA7 2026-06-30\n"
            "-----END PGP PUBLIC KEY BLOCK-----\n",
            encoding="utf-8",
        )
        with patch.object(host_identity, "_GPG_PUBLIC_PATH", sample):
            payload = host_identity.get_host_identity()
        self.assertEqual(payload["gpg_key_id"], "D9BC48A619204DA7")
        self.assertTrue(payload["gpg_configured"])

    def test_get_gpg_public_payload_missing_key(self):
        with patch.object(host_identity, "_GPG_PUBLIC_PATH", Path("/tmp/missing-gpg.asc")):
            payload = host_identity.get_gpg_public_payload()
        self.assertFalse(payload["configured"])
        self.assertIsNone(payload["public_key"])

    def test_host_identity_fallback_and_normalization(self):
        # 1. Test normalization of unsupported JULES_CONTEXT values
        os.environ["JULES_IDENTITY"] = ""
        os.environ["JULES_CONTEXT"] = "[INVALID_CONTEXT]"
        with patch.object(host_identity, "_ram_gb", return_value=16.0):
            payload = host_identity.get_host_identity()
        # Normalizes to [LOCAL] because RAM is < 32
        self.assertEqual(payload["execution_context"], "[LOCAL]")

        with patch.object(host_identity, "_ram_gb", return_value=32.0):
            payload = host_identity.get_host_identity()
        # Normalizes to [SCHOOL_COMPUTE] because RAM is >= 32
        self.assertEqual(payload["execution_context"], "[SCHOOL_COMPUTE]")

        # 2. Test fallback label based on RAM size
        os.environ.pop("JULES_IDENTITY", None)
        with patch.object(host_identity, "_read_system_id_file", return_value=""), \
             patch.object(host_identity, "_ram_gb", return_value=16.0):
            payload = host_identity.get_host_identity()
        self.assertEqual(payload["identity"], "School-PC-RAM-16GB")

        with patch.object(host_identity, "_read_system_id_file", return_value=""), \
             patch.object(host_identity, "_ram_gb", return_value=64.0):
            payload = host_identity.get_host_identity()
        self.assertEqual(payload["identity"], "School-PC-RAM-64GB")

        # 3. Test RAM extraction from label file when other mechanisms return None
        # We mock os.name to "nt" to bypass the Linux return-None check in _ram_gb
        with patch.object(host_identity, "_read_system_id_file", return_value="My-Workstation-32GB-RAM"), \
             patch("os.name", "nt"), \
             patch("psutil.virtual_memory", side_effect=Exception("psutil unavailable")), \
             patch("subprocess.check_output", side_effect=Exception("powershell failed")):
            ram = host_identity._ram_gb()  # pylint: disable=protected-access
        self.assertEqual(ram, 32.0)



if __name__ == "__main__":
    unittest.main()
