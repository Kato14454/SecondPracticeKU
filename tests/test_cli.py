"""Tests for the command-line interface."""

import io
import os
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

from depgraph.cli import (
    EXIT_CONFIG_ERROR,
    EXIT_OK,
    EXIT_RUNTIME_ERROR,
    main,
)
from depgraph.nuget import Dependency, RepositoryError

BASE_ARGS = [
    "--package", "Demo",
    "--repo", "https://example.org/index.json",
    "--package-version", "1.0.0",
]
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
TEST_REPO = os.path.join(DATA_DIR, "sample_repo.txt")
TARGET = "depgraph.cli.get_direct_dependencies"


def run_main(args):
    """Run main and return the exit code, stdout and stderr."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(args)
    return code, out.getvalue(), err.getvalue()


class MainTest(unittest.TestCase):
    """Tests for main."""

    def test_dependencies_are_printed(self):
        found = [Dependency("Alpha", "1.0.0"), Dependency("Beta", "[2.0, )")]
        with mock.patch(TARGET, return_value=found):
            code, out, _ = run_main(BASE_ARGS)
        self.assertEqual(code, EXIT_OK)
        self.assertIn("Direct dependencies of Demo 1.0.0:", out)
        self.assertIn("  Alpha 1.0.0", out)
        self.assertIn("  Beta [2.0, )", out)

    def test_empty_dependencies(self):
        with mock.patch(TARGET, return_value=[]):
            code, out, _ = run_main(BASE_ARGS)
        self.assertEqual(code, EXIT_OK)
        self.assertIn("(none)", out)

    def test_repository_error_returns_runtime_code(self):
        with mock.patch(TARGET, side_effect=RepositoryError("boom")):
            code, _, err = run_main(BASE_ARGS)
        self.assertEqual(code, EXIT_RUNTIME_ERROR)
        self.assertIn("boom", err)

    def test_invalid_depth_returns_config_code(self):
        code, _, err = run_main(BASE_ARGS + ["--max-depth", "0"])
        self.assertEqual(code, EXIT_CONFIG_ERROR)
        self.assertIn("max depth", err)

    def test_test_mode_is_not_available_yet(self):
        args = [
            "--package", "A", "--repo", TEST_REPO,
            "--test-mode", "--package-version", "1.0",
        ]
        code, _, err = run_main(args)
        self.assertEqual(code, EXIT_CONFIG_ERROR)
        self.assertIn("stage 3", err)