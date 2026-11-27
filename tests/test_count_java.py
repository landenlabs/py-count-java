#!/usr/bin/env python3
# ----------------------------------------------------------------------
# Copyright (c) 2026 LanDen Labs - Dennis Lang
# https://landenlabs.com
# ----------------------------------------------------------------------
"""Unit tests for py-count-java.py, using the sample files under tests/samples/.

Run with:
    python3 -m unittest discover -s tests -v
or:
    python3 tests/test_count_java.py
"""

import importlib.util
import os
import subprocess
import sys
import unittest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(TESTS_DIR)
SAMPLES_DIR = os.path.join(TESTS_DIR, "samples")
SCRIPT_PATH = os.path.join(PROJECT_DIR, "py-count-java.py")

spec = importlib.util.spec_from_file_location("py_count_java", SCRIPT_PATH)
pcj = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pcj)


def read(*parts):
    with open(os.path.join(SAMPLES_DIR, *parts), "r", encoding="utf-8") as f:
        return f.read()


class TestCountCodeLines(unittest.TestCase):
    """Verifies count_code_lines()/count_physical_lines() against hand-counted
    samples -- each expected value was cross-checked with `wc -l` and a manual
    tally of terminal semicolons/braces before being hardcoded here."""

    def test_locjava_wiki_example(self):
        # The exact example from https://sourceforge.net/p/locjava/wiki/Home/ :
        # 4 semicolons + 2 right braces = 6.
        text = read("basic", "Snoopy.java")
        self.assertEqual(pcj.count_code_lines(text), 6)
        self.assertEqual(pcj.count_physical_lines(text), 9)

    def test_for_header_semicolons_excluded(self):
        # Both semicolons inside for(int i=0, j=helper(1,2); i<10; i++) are
        # excluded, even with a nested function-call paren in the header.
        text = read("basic", "ForLoop.java")
        self.assertEqual(pcj.count_code_lines(text), 8)
        self.assertEqual(pcj.count_physical_lines(text), 14)

    def test_comments_are_ignored(self):
        # Semicolons/braces inside //, /* */ comments (including one on the
        # same line as real code) must not be counted.
        text = read("basic", "Comments.java")
        self.assertEqual(pcj.count_code_lines(text), 7)
        self.assertEqual(pcj.count_physical_lines(text), 15)

    def test_string_and_char_literals_are_skipped(self):
        # ';' and '}' inside string/char literals and a """ text block must
        # not be counted -- including a bare '}' char literal, which is the
        # easiest case to accidentally double-count as a right brace.
        text = read("basic", "Strings.java")
        self.assertEqual(pcj.count_code_lines(text), 7)
        self.assertEqual(pcj.count_physical_lines(text), 12)

    def test_nested_for_and_if_blocks(self):
        text = read("nested", "Nested.java")
        self.assertEqual(pcj.count_code_lines(text), 7)
        self.assertEqual(pcj.count_physical_lines(text), 12)

    def test_non_java_text_still_gets_a_count(self):
        # Not valid Java, but the scanner never parses -- it just counts
        # tokens, so plain text still produces a result.
        text = read("NotJava.txt")
        self.assertEqual(pcj.count_code_lines(text), 2)
        self.assertEqual(pcj.count_physical_lines(text), 1)

    def test_empty_text_has_no_lines_or_code(self):
        self.assertEqual(pcj.count_code_lines(""), 0)
        self.assertEqual(pcj.count_physical_lines(""), 0)


class TestFindFiles(unittest.TestCase):
    """Verifies file/directory resolution and extension filtering."""

    def test_directory_scan_is_recursive_and_filters_by_extension(self):
        found = pcj.find_files([SAMPLES_DIR], {".java"})
        names = sorted(os.path.basename(p) for p in found)
        self.assertEqual(
            names, ["Comments.java", "ForLoop.java", "Nested.java", "Snoopy.java", "Strings.java"]
        )

    def test_explicit_file_is_counted_regardless_of_extension(self):
        not_java = os.path.join(SAMPLES_DIR, "NotJava.txt")
        found = pcj.find_files([not_java], {".java"})
        self.assertEqual(found, [not_java])

    def test_missing_path_is_skipped_not_raised(self):
        missing = os.path.join(SAMPLES_DIR, "does-not-exist.java")
        found = pcj.find_files([missing], {".java"})
        self.assertEqual(found, [])


class TestCli(unittest.TestCase):
    """End-to-end check that main() aggregates per-file counts correctly."""

    def test_summary_totals_across_sample_directory(self):
        result = subprocess.run(
            [sys.executable, SCRIPT_PATH, SAMPLES_DIR],
            capture_output=True, text=True, check=True,
        )
        # files=5, lines=62 (9+14+15+12+12), code=35 (6+8+7+7+7)
        self.assertIn("Java", result.stdout)
        java_line = next(line for line in result.stdout.splitlines() if line.startswith("Java"))
        self.assertEqual(java_line.split(), ["Java", "5", "62", "35"])

    def test_missing_path_exits_nonzero(self):
        result = subprocess.run(
            [sys.executable, SCRIPT_PATH, os.path.join(SAMPLES_DIR, "nope")],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 1)


if __name__ == "__main__":
    unittest.main()
