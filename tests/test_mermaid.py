"""Tests for the Mermaid output."""

import unittest

from depgraph.graph import build_graph
from depgraph.mermaid import format_mermaid
from depgraph.nuget import Dependency
from depgraph.testrepo import FileSource, parse_test_repository


def graph_of(text, depth=5):
    """Build the graph of package A from the text of a test repository."""
    source = FileSource(parse_test_repository(text))
    return build_graph(source, "A", "", depth)


class VersionedSource:
    """A source with versions and a quote in a package name."""

    def dependencies(self, package, version):
        """Return one dependency with a version range."""
        if package == "App":
            return [Dependency('Lib"X', "[2.0.0, )")]
        return []


class FormatMermaidTest(unittest.TestCase):
    """Tests for format_mermaid."""

    def test_diamond(self):
        text = format_mermaid(graph_of("A: B C\nB: D\nC: D E\nD:\nE:\n"))
        self.assertEqual(
            text.splitlines(),
            [
                "graph TD",
                '    n0["A"]',
                '    n1["B"]',
                '    n2["D"]',
                '    n3["C"]',
                '    n4["E"]',
                "    n0 --> n1",
                "    n0 --> n3",
                "    n1 --> n2",
                "    n3 --> n2",
                "    n3 --> n4",
            ],
        )

    def test_cycle_edge_is_present(self):
        text = format_mermaid(graph_of("A: B\nB: A\n"))
        self.assertIn("    n1 --> n0", text)

    def test_unexpanded_packages_are_dashed(self):
        text = format_mermaid(graph_of("A: B\nB: C\nC:\n", depth=1))
        self.assertIn("classDef limit stroke-dasharray: 4 4", text)
        self.assertIn("    class n1 limit", text)

    def test_no_style_without_depth_limit(self):
        text = format_mermaid(graph_of("A: B\nB:\n"))
        self.assertNotIn("classDef", text)

    def test_version_is_in_label_and_quote_is_escaped(self):
        graph = build_graph(VersionedSource(), "App", "1.0.0", 3)
        text = format_mermaid(graph)
        self.assertIn('n0["App 1.0.0"]', text)
        self.assertIn('n1["Lib#quot;X 2.0.0"]', text)