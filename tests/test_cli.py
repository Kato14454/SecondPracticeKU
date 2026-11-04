"""Tests for the command-line interface."""

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout

from depgraph.cli import EXIT_CONFIG_ERROR, EXIT_OK, main

BASE_ARGS = [
    "--package", "Newtonsoft.Json",
    "--repo", "https://api.nuget.org/v3/index.json",
    "--package-version", "13.0.3",
]


class MainTest(unittest.TestCase):
    """Tests for main."""

    def test_valid_arguments_are_printed(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(BASE_ARGS)
        self.assertEqual(code, EXIT_OK)
        self.assertIn("package: Newtonsoft.Json", output.getvalue())

    def test_invalid_depth_returns_error_code(self):
        errors = io.StringIO()
        with redirect_stderr(errors):
            code = main(BASE_ARGS + ["--max-depth", "0"])
        self.assertEqual(code, EXIT_CONFIG_ERROR)
        self.assertIn("max depth", errors.getvalue())