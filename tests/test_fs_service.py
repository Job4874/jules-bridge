# pylint: disable=import-outside-toplevel

"""Unit tests for modules/fs_service.py.

Tests at the module interface level — no Flask or HTTP involved.
"""

import os
import re
import tempfile
import unittest


class TestFsRead(unittest.TestCase):
    def setUp(self):
        from modules import fs_service
        self.fs = fs_service

    def _write_temp(self, content, suffix=".txt"):
        handle, path = tempfile.mkstemp(suffix=suffix)
        os.close(handle)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        self.addCleanup(os.unlink, path)
        return path

    def test_read_returns_content(self):
        path = self._write_temp("hello world")
        result = self.fs.read(path)
        self.assertEqual(result["content"], "hello world")
        self.assertEqual(result["data"], "hello world")
        self.assertEqual(result["path"], path)

    def test_read_offset_and_limit(self):
        path = self._write_temp("line1\nline2\nline3\n")
        result = self.fs.read(path, offset=1, limit=1)
        self.assertEqual(result["content"], "line2\n")

    def test_read_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            self.fs.read(r"C:\definitely\missing.txt")

    def test_read_directory_raises(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(IsADirectoryError):
                self.fs.read(d)


class TestFsWrite(unittest.TestCase):
    def setUp(self):
        from modules import fs_service
        self.fs = fs_service

    def test_write_creates_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "out.txt")
            result = self.fs.write(path, "test content")
            self.assertEqual(result["status"], "success")
            with open(path, "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), "test content")

    def test_write_empty_content(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "empty.txt")
            self.fs.write(path, "")
            self.assertTrue(os.path.exists(path))

    def test_write_creates_parent_directories(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "sub", "dir", "file.txt")
            self.fs.write(path, "nested")
            self.assertTrue(os.path.exists(path))


class TestFsTail(unittest.TestCase):
    def setUp(self):
        from modules import fs_service
        self.fs = fs_service

    def _write_temp(self, content):
        handle, path = tempfile.mkstemp(suffix=".txt")
        os.close(handle)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        self.addCleanup(os.unlink, path)
        return path

    def test_tail_returns_last_n_lines(self):
        path = self._write_temp("a\nb\nc\nd\ne\n")
        result = self.fs.tail(path, lines=2)
        self.assertEqual(result["content"], "d\ne\n")
        self.assertEqual(result["lines"], 2)

    def test_tail_fewer_lines_than_requested(self):
        path = self._write_temp("only\n")
        result = self.fs.tail(path, lines=10)
        self.assertEqual(result["lines"], 1)

    def test_tail_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            self.fs.tail(r"C:\missing.txt")

    def test_tail_directory_raises(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(IsADirectoryError):
                self.fs.tail(d)


class TestFsGrep(unittest.TestCase):
    def setUp(self):
        from modules import fs_service
        self.fs = fs_service

    def _write_temp(self, content):
        handle, path = tempfile.mkstemp(suffix=".txt")
        os.close(handle)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        self.addCleanup(os.unlink, path)
        return path

    def test_grep_finds_matches(self):
        path = self._write_temp("error on line 1\nall ok\nERROR again\n")
        result = self.fs.grep(path, pattern="error")
        self.assertEqual(len(result["matches"]), 2)
        self.assertEqual(result["matches"][0]["line"], 1)

    def test_grep_max_matches_limits_results(self):
        path = self._write_temp("x\n" * 100)
        result = self.fs.grep(path, pattern="x", max_matches=3)
        self.assertEqual(len(result["matches"]), 3)

    def test_grep_empty_pattern_matches_all(self):
        path = self._write_temp("a\nb\n")
        result = self.fs.grep(path, pattern="", max_matches=50)
        self.assertEqual(len(result["matches"]), 2)

    def test_grep_invalid_regex_raises(self):
        path = self._write_temp("abc\n")
        with self.assertRaises(re.error):
            self.fs.grep(path, pattern="[invalid")

    def test_grep_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            self.fs.grep(r"C:\missing.txt", pattern="error")

    def test_grep_directory_raises(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(IsADirectoryError):
                self.fs.grep(d, pattern="error")


class TestFsListDir(unittest.TestCase):
    def setUp(self):
        from modules import fs_service
        self.fs = fs_service

    def test_list_dir_returns_entries(self):
        with tempfile.TemporaryDirectory() as d:
            file_path = os.path.join(d, "file.txt")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("test content")
            subdir_path = os.path.join(d, "subdir")
            os.makedirs(subdir_path)
            entries = self.fs.list_dir(d)

            names = [e["name"] for e in entries]
            self.assertIn("file.txt", names)
            self.assertIn("subdir", names)

            # Find specific entries
            file_entry = next(e for e in entries if e["name"] == "file.txt")
            dir_entry = next(e for e in entries if e["name"] == "subdir")

            # Check directory entry attributes
            self.assertTrue(dir_entry["is_dir"])
            self.assertEqual(dir_entry["path"], subdir_path)
            self.assertIsNone(dir_entry["size"])

            # Check file entry attributes
            self.assertFalse(file_entry["is_dir"])
            self.assertEqual(file_entry["path"], file_path)
            self.assertEqual(file_entry["size"], 12) # length of "test content"

    def test_list_dir_dirs_sorted_first(self):
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "z_file.txt"), "w", encoding="utf-8").close()
            open(os.path.join(d, "a_file.txt"), "w", encoding="utf-8").close()
            os.makedirs(os.path.join(d, "z_dir"))
            os.makedirs(os.path.join(d, "a_dir"))

            entries = self.fs.list_dir(d)
            names = [e["name"] for e in entries]

            # Expected sort: dirs first (alpha), then files (alpha)
            expected_names = ["a_dir", "z_dir", "a_file.txt", "z_file.txt"]
            self.assertEqual(names, expected_names)

            self.assertTrue(entries[0]["is_dir"])
            self.assertTrue(entries[1]["is_dir"])
            self.assertFalse(entries[2]["is_dir"])
            self.assertFalse(entries[3]["is_dir"])

    def test_list_dir_missing_raises(self):
        with self.assertRaises(FileNotFoundError):
            self.fs.list_dir(r"C:\does\not\exist")

    def test_list_dir_file_path_raises(self):
        handle, path = tempfile.mkstemp()
        os.close(handle)
        self.addCleanup(os.unlink, path)
        with self.assertRaises(NotADirectoryError):
            self.fs.list_dir(path)


if __name__ == "__main__":
    unittest.main()
