import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from modules.http_utils import bool_field, BridgeHTTPError

class TestHttpUtils(unittest.TestCase):
    def test_bool_field_invalid_type(self):
        with self.assertRaises(BridgeHTTPError) as ctx:
            bool_field({"flag": "yes"}, "flag")

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.error, "Invalid input")
        self.assertEqual(ctx.exception.payload.get("details"), "flag must be a boolean")

if __name__ == "__main__":
    unittest.main()
