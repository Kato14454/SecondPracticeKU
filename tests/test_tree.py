"""Tests for the ASCII tree output."""

import unittest

from depgraph.graph import build_graph
from depgraph.nuget import Dependency
from depgraph.testrepo import FileSource, parse_test_repository
from depgraph.tree import format_tree

DEEP_CHAIN_LENGTH = 1500


def graph_of(text, depth=5):
    """Build the graph of package A from the text of a test repository."""
    source = FileSource(parse_test_repository(text))
    return build_graph(source, "A", "", depth)


class ChainSource:
    """A chain of packages deeper than the recursion limit."""

    def dependencies(self, package, version):
        """Return the next package of the chain."""
        number = int(package[1:])
        if number >= DEEP_CHAIN_LENGTH:
            return []
        return [Dependency(f"n{number + 1}", "")]


class FormatTreeTest(unittest.TestCase):
    """Tests for format_tree."""

    def test_diamond_shows_shared_package_once_in_full(self):
        text = format_tree(graph_of("A: B C\nB: D\nC: D E\nD:\nE:\n"))
        self.assertEqual(
            text.splitlines(),
            [
                "A",
                "|-- B",
                "|   `-- D",
                "`-- C",
                "    |-- D (*)",
                "    `-- E",
                "Legend: (*) shown above",
            ],
        )

    def test_cycle_is_marked(self):
        text = format_tree(graph_of("A: B\nB: C\nC: A D\nD:\n"))
        self.assertIn("        |-- A (cycle)", text)
        self.assertIn("        `-- D", text)
        self.assertIn("(cycle) closes a dependency cycle", text)

    def test_depth_limit_is_marked(self):
        text = format_tree(graph_of("A: B\nB: C\nC:\n", depth=1))
        self.assertEqual(
            text.splitlines()[:2], ["A", "`-- B (...)"]
        )
        self.assertIn("(...) not expanded: depth limit", text)

    def test_package_without_dependencies(self):
        self.assertEqual(format_tree(graph_of("A:\n")), "A")

    def test_no_legend_without_marks(self):
        text = format_tree(graph_of("A: B\nB:\n"))
        self.assertNotIn("Legend", text)

    def test_deep_tree_does_not_hit_recursion_limit(self):
        graph = build_graph(ChainSource(), "n0", "", DEEP_CHAIN_LENGTH + 1)
        lines = format_tree(graph).splitlines()
        self.assertEqual(len(lines), DEEP_CHAIN_LENGTH + 1)