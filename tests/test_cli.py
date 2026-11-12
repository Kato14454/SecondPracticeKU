"""Tests for the command-line interface."""

import io
import os
import tempfile
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

DATA_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "data")
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
    """Run main in a temporary folder; return the code, stdout and stderr.

    The folder keeps the SVG file that main writes by default out of
    the project.
    """
    out, err = io.StringIO(), io.StringIO()
    previous = os.getcwd()
    with tempfile.TemporaryDirectory() as directory:
        os.chdir(directory)
        try:
            with redirect_stdout(out), redirect_stderr(err):
                code = main(args)
        finally:
            os.chdir(previous)
    return code, out.getvalue(), err.getvalue()


def make_args(path, package="A", *extra):
    """Build arguments for a run on a test repository file."""
    return ["--package", package, "--repo", path, "--test-mode", *extra]


class TestModeTest(unittest.TestCase):
    """Tests of main in test repository mode."""

    def test_diamond(self):
        code, out, _ = run_main(make_args(DIAMOND))
        self.assertEqual(code, EXIT_OK)
        self.assertIn("5 packages, 5 dependencies", out)
        self.assertIn("  A -> B, C", out)
        self.assertIn("  C -> D, E", out)

    def test_cycle(self):
        code, out, _ = run_main(make_args(CYCLE))
        self.assertEqual(code, EXIT_OK)
        self.assertIn("  A -> B -> C -> A", out)

    def test_depth_limit(self):
        args = make_args(CHAIN, "A", "--max-depth", "2")
        code, out, _ = run_main(args)
        self.assertEqual(code, EXIT_OK)
        self.assertIn("Depth limit reached, not expanded: C", out)
        self.assertNotIn("C -> D", out)

    def test_shortcut_is_expanded(self):
        args = make_args(SHORTCUT, "A", "--max-depth", "3")
        code, out, _ = run_main(args)
        self.assertEqual(code, EXIT_OK)
        self.assertIn("  D -> E", out)

    def test_start_from_inner_package(self):
        code, out, _ = run_main(make_args(DIAMOND, "C"))
        self.assertEqual(code, EXIT_OK)
        self.assertIn("  C -> D, E", out)
        self.assertNotIn("  A ->", out)

    def test_unknown_package(self):
        code, _, err = run_main(make_args(DIAMOND, "Z"))
        self.assertEqual(code, EXIT_RUNTIME_ERROR)
        self.assertIn("package Z is not in", err)

    def test_broken_file(self):
        code, _, err = run_main(make_args(BROKEN))
        self.assertEqual(code, EXIT_RUNTIME_ERROR)
        self.assertIn("line 3", err)

    def test_missing_file(self):
        code, _, err = run_main(make_args("no_such_file.txt"))
        self.assertEqual(code, EXIT_CONFIG_ERROR)
        self.assertIn("not found", err)


class LoadOrderModeTest(unittest.TestCase):
    """Tests of main with the --load-order option."""

    def test_diamond_order(self):
        args = make_args(DIAMOND, "A", "--load-order")
        code, out, _ = run_main(args)
        self.assertEqual(code, EXIT_OK)
        expected = ["  1. D", "  2. B", "  3. E", "  4. C", "  5. A"]
        self.assertEqual(out.splitlines()[1:], expected)

    def test_graph_is_not_printed_in_this_mode(self):
        args = make_args(DIAMOND, "A", "--load-order")
        _, out, _ = run_main(args)
        self.assertNotIn("Dependency graph of", out)

    def test_cycle_is_reported(self):
        args = make_args(CYCLE, "A", "--load-order", "--max-depth", "5")
        code, out, _ = run_main(args)
        self.assertEqual(code, EXIT_OK)
        self.assertIn("  A -> B -> C -> A", out)
        self.assertIn("  4. A", out)

    def test_depth_limit_is_used(self):
        args = make_args(CHAIN, "A", "--load-order", "--max-depth", "2")
        _, out, _ = run_main(args)
        self.assertIn("  1. C", out)
        self.assertNotIn(". D", out)


class VisualizationTest(unittest.TestCase):
    """Tests of the ASCII tree, Mermaid and SVG output."""

    def test_mermaid_is_printed(self):
        code, out, _ = run_main(make_args(DIAMOND))
        self.assertEqual(code, EXIT_OK)
        self.assertIn("Mermaid:\ngraph TD", out)
        self.assertIn("    n0 --> n1", out)

    def test_ascii_tree_only_with_option(self):
        _, plain, _ = run_main(make_args(DIAMOND))
        _, tree, _ = run_main(make_args(DIAMOND, "A", "--ascii-tree"))
        self.assertNotIn("ASCII tree:", plain)
        self.assertIn("ASCII tree:\nA\n|-- B", tree)
        self.assertIn("    |-- D (*)", tree)

    def test_svg_is_saved_to_the_given_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "result.svg")
            args = make_args(DIAMOND, "A", "--output", path)
            code, out, _ = run_main(args)
            self.assertEqual(code, EXIT_OK)
            self.assertIn(f"SVG saved: {path}", out)
            with open(path, encoding="utf-8") as file:
                self.assertTrue(file.read().startswith("<svg"))

    def test_load_order_mode_does_not_write_a_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "result.svg")
            args = make_args(DIAMOND, "A", "--load-order", "--output", path)
            code, out, _ = run_main(args)
            self.assertEqual(code, EXIT_OK)
            self.assertNotIn("SVG saved", out)
            self.assertFalse(os.path.exists(path))

    def test_unwritable_output_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "folder.svg")
            os.mkdir(path)
            code, _, err = run_main(make_args(DIAMOND, "A", "--output", path))
            self.assertEqual(code, EXIT_RUNTIME_ERROR)
            self.assertIn("cannot write", err)


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