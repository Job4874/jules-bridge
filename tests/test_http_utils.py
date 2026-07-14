"""Unit tests for modules/http_utils.py."""

from __future__ import annotations

import errno
import os
import re
import subprocess
import unittest
from flask import Flask

from modules.http_utils import route_errors

# We need the class name to match exactly
class ShellNotAvailableError(Exception):
    pass

class UnsupportedShellError(Exception):
    pass

class TestHttpUtils(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.testing = True

        @self.app.route('/generic_error')
        @route_errors
        def generic_error():
            raise Exception("Something went wrong")

        @self.app.route('/shell_not_available')
        @route_errors
        def shell_not_available():
            raise ShellNotAvailableError("Shell not found")

        @self.app.route('/unsupported_shell')
        @route_errors
        def unsupported_shell():
            raise UnsupportedShellError("Unsupported shell")

        @self.app.route('/is_a_directory')
        @route_errors
        def is_a_directory():
            raise IsADirectoryError("Is a directory")

        @self.app.route('/file_not_found')
        @route_errors
        def file_not_found():
            exc = FileNotFoundError("File not found")
            exc.filename = "test.txt"
            raise exc

        @self.app.route('/permission_error')
        @route_errors
        def permission_error():
            raise PermissionError("Access denied")

        @self.app.route('/regex_error')
        @route_errors
        def regex_error():
            raise re.error("Invalid regex")

        @self.app.route('/value_error')
        @route_errors
        def value_error():
            raise ValueError("Bad value")

        @self.app.route('/os_error_permission')
        @route_errors
        def os_error_permission():
            exc = OSError("Permission denied")
            exc.errno = errno.EACCES
            raise exc

        @self.app.route('/os_error_not_found')
        @route_errors
        def os_error_not_found():
            exc = OSError("No such file")
            exc.errno = errno.ENOENT
            exc.filename = "missing.txt"
            raise exc

        @self.app.route('/os_error_other')
        @route_errors
        def os_error_other():
            exc = OSError("Something else")
            exc.errno = 999
            raise exc

        @self.app.route('/timeout_error')
        @route_errors
        def timeout_error():
            exc = subprocess.TimeoutExpired(["sleep", "10"], 5)
            raise exc

        self.client = self.app.test_client()

    def test_generic_exception_returns_500(self):
        response = self.client.get('/generic_error')
        self.assertEqual(response.status_code, 500)
        data = response.get_json()
        self.assertEqual(data["error"], "Internal operational failure")

    def test_shell_not_available_returns_400(self):
        response = self.client.get('/shell_not_available')
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertEqual(data["error"], "Invalid input")
        self.assertEqual(data["details"], "Shell not found")

    def test_unsupported_shell_returns_400(self):
        response = self.client.get('/unsupported_shell')
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertEqual(data["error"], "Invalid input")
        self.assertEqual(data["details"], "Unsupported shell")

    def test_is_a_directory_returns_400(self):
        response = self.client.get('/is_a_directory')
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertEqual(data["error"], "Invalid input")
        self.assertEqual(data["details"], "Is a directory")

    def test_file_not_found_returns_404(self):
        response = self.client.get('/file_not_found')
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertEqual(data["error"], "Resource not found")
        self.assertEqual(data["path"], "test.txt")

    def test_permission_error_returns_403(self):
        response = self.client.get('/permission_error')
        self.assertEqual(response.status_code, 403)
        data = response.get_json()
        self.assertEqual(data["error"], "Access denied")
        self.assertEqual(data["reason"], "Insufficient permissions")

    def test_regex_error_returns_400(self):
        response = self.client.get('/regex_error')
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertEqual(data["error"], "Invalid input")
        self.assertTrue("Invalid regex" in data["details"])

    def test_value_error_returns_400(self):
        response = self.client.get('/value_error')
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertEqual(data["error"], "Invalid input")
        self.assertEqual(data["details"], "Bad value")

    def test_os_error_permission_returns_403(self):
        response = self.client.get('/os_error_permission')
        self.assertEqual(response.status_code, 403)
        data = response.get_json()
        self.assertEqual(data["error"], "Access denied")
        self.assertEqual(data["reason"], "Insufficient permissions")

    def test_os_error_not_found_returns_404(self):
        response = self.client.get('/os_error_not_found')
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertEqual(data["error"], "Resource not found")
        self.assertEqual(data["path"], "missing.txt")

    def test_os_error_other_returns_500(self):
        response = self.client.get('/os_error_other')
        self.assertEqual(response.status_code, 500)
        data = response.get_json()
        self.assertEqual(data["error"], "Internal operational failure")

    def test_timeout_error_returns_504(self):
        response = self.client.get('/timeout_error')
        self.assertEqual(response.status_code, 504)
        data = response.get_json()
        self.assertEqual(data["error"], "Execution timed out after 5 seconds")

if __name__ == '__main__':
    unittest.main()
