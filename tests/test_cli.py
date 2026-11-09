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

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DIAMOND = os.path.join(DATA_DIR, "diamond.txt")
CYCLE = os.path.join(DATA_DIR, "cycle.txt")
CHAIN = os.path.join(DATA_DIR, "chain.txt")
SHORTCUT = os.path.join(DATA_DIR, "shortcut.txt")
BROKEN = os.path.join(DATA_DIR, "broken.txt")
REAL_ARGS = [
    "--package", "Demo",
    "--repo", "https://example.org/index.json",
    "--package-version", "1.0.0",
]
NUGET_SOURCE = "depgraph.cli.NugetSource"


def run_main(args):
    """Run main and return the exit code, stdout and stderr."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(args)
    return code, out.getvalue(), err.getvalue()


def test_args(path, package="A", *extra):
    """Build arguments for a run on a test repository file."""
    return ["--package", package, "--repo", path, "--test-mode", *extra]


class TestModeTest(unittest.TestCase):
    """Tests of main in test repository mode."""

    def test_diamond(self):
        code, out, _ = run_main(test_args(DIAMOND))
        self.assertEqual(code, EXIT_OK)
        self.assertIn("5 packages, 5 dependencies", out)
        self.assertIn("  A -> B, C", out)
        self.assertIn("  C -> D, E", out)

    def test_cycle(self):
        code, out, _ = run_main(test_args(CYCLE))
        self.assertEqual(code, EXIT_OK)
        self.assertIn("  A -> B -> C -> A", out)

    def test_depth_limit(self):
        args = test_args(CHAIN, "A", "--max-depth", "2")
        code, out, _ = run_main(args)
        self.assertEqual(code, EXIT_OK)
        self.assertIn("Depth limit reached, not expanded: C", out)
        self.assertNotIn("C -> D", out)

    def test_shortcut_is_expanded(self):
        args = test_args(SHORTCUT, "A", "--max-depth", "3")
        code, out, _ = run_main(args)
        self.assertEqual(code, EXIT_OK)
        self.assertIn("  D -> E", out)

    def test_start_from_inner_package(self):
        code, out, _ = run_main(test_args(DIAMOND, "C"))
        self.assertEqual(code, EXIT_OK)
        self.assertIn("  C -> D, E", out)
        self.assertNotIn("  A ->", out)

    def test_unknown_package(self):
        code, _, err = run_main(test_args(DIAMOND, "Z"))
        self.assertEqual(code, EXIT_RUNTIME_ERROR)
        self.assertIn("package Z is not in", err)

    def test_broken_file(self):
        code, _, err = run_main(test_args(BROKEN))
        self.assertEqual(code, EXIT_RUNTIME_ERROR)
        self.assertIn("line 3", err)

    def test_missing_file(self):
        code, _, err = run_main(test_args("no_such_file.txt"))
        self.assertEqual(code, EXIT_CONFIG_ERROR)
        self.assertIn("not found", err)


class LoadOrderModeTest(unittest.TestCase):
    """Tests of main with the --load-order option."""

    def test_diamond_order(self):
        args = test_args(DIAMOND, "A", "--load-order")
        code, out, _ = run_main(args)
        self.assertEqual(code, EXIT_OK)
        expected = ["  1. D", "  2. B", "  3. E", "  4. C", "  5. A"]
        self.assertEqual(out.splitlines()[1:], expected)

    def test_graph_is_not_printed_in_this_mode(self):
        args = test_args(DIAMOND, "A", "--load-order")
        _, out, _ = run_main(args)
        self.assertNotIn("Dependency graph of", out)

    def test_cycle_is_reported(self):
        args = test_args(CYCLE, "A", "--load-order", "--max-depth", "5")
        code, out, _ = run_main(args)
        self.assertEqual(code, EXIT_OK)
        self.assertIn("  A -> B -> C -> A", out)
        self.assertIn("  4. A", out)

    def test_depth_limit_is_used(self):
        args = test_args(CHAIN, "A", "--load-order", "--max-depth", "2")
        _, out, _ = run_main(args)
        self.assertIn("  1. C", out)
        self.assertNotIn(". D", out)


class RealModeTest(unittest.TestCase):
    """Tests of main with a repository URL (the network is replaced)."""

    def fake_source(self, table):
        """Return a mock of NugetSource that answers from a table."""
        source = mock.Mock()
        source.dependencies.side_effect = (
            lambda name, version: table.get(name, [])
        )
        return mock.patch(NUGET_SOURCE, return_value=source)

    def test_versions_are_shown(self):
        table = {"Demo": [Dependency("Lib", "[2.0.0, )")]}
        with self.fake_source(table):
            code, out, _ = run_main(REAL_ARGS)
        self.assertEqual(code, EXIT_OK)
        self.assertIn("  Demo 1.0.0 -> Lib 2.0.0", out)

    def test_depth_option_is_used(self):
        table = {"Demo": [Dependency("Lib", "1.0.0")]}
        with self.fake_source(table):
            code, out, _ = run_main(REAL_ARGS + ["--max-depth", "1"])
        self.assertEqual(code, EXIT_OK)
        self.assertIn("not expanded: Lib", out)

    def test_repository_error_returns_runtime_code(self):
        with mock.patch(NUGET_SOURCE, side_effect=RepositoryError("boom")):
            code, _, err = run_main(REAL_ARGS)
        self.assertEqual(code, EXIT_RUNTIME_ERROR)
        self.assertIn("boom", err)


class ConfigErrorsTest(unittest.TestCase):
    """Tests of parameter errors reported by main."""

    def test_invalid_depth(self):
        code, _, err = run_main(REAL_ARGS + ["--max-depth", "0"])
        self.assertEqual(code, EXIT_CONFIG_ERROR)
        self.assertIn("max depth", err)

    def test_version_is_required_without_test_mode(self):
        args = ["--package", "Demo", "--repo", "https://example.org/i.json"]
        code, _, err = run_main(args)
        self.assertEqual(code, EXIT_CONFIG_ERROR)
        self.assertIn("version is required", err)