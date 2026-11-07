"""Tests for the text output of a graph."""

import unittest

from depgraph.graph import build_graph
from depgraph.report import format_graph
from depgraph.testrepo import FileSource, parse_test_repository


def graph_of(text, depth):
    """Build the graph of package A from the text of a test repository."""
    source = FileSource(parse_test_repository(text))
    return build_graph(source, "A", "", depth)


class FormatGraphTest(unittest.TestCase):
    """Tests for format_graph."""

    def test_title_and_edges(self):
        text = format_graph(graph_of("A: B C\nB:\nC:\n", 3))
        lines = text.splitlines()
        self.assertEqual(
            lines[0],
            "Dependency graph of A (max depth 3): 3 packages, 2 dependencies",
        )
        self.assertIn("  A -> B, C", lines)
        self.assertIn("  B -> (none)", lines)

    def test_cycle_is_listed(self):
        text = format_graph(graph_of("A: B\nB: A\n", 5))
        self.assertIn("Cycles found:", text)
        self.assertIn("  A -> B -> A", text)

    def test_depth_limit_is_reported(self):
        text = format_graph(graph_of("A: B\nB: C\nC:\n", 1))
        self.assertIn("Depth limit reached, not expanded: B", text)

    def test_no_notes_for_plain_graph(self):
        text = format_graph(graph_of("A: B\nB:\n", 5))
        self.assertNotIn("Cycles", text)
        self.assertNotIn("Depth limit", text)