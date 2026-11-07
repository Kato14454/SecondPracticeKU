"""Tests for dependency graph construction."""

import unittest

from depgraph.graph import build_graph
from depgraph.nuget import Dependency, RepositoryError
from depgraph.testrepo import FileSource, parse_test_repository

DIAMOND = "A: B C\nB: D\nC: D E\nD:\nE:\n"
CHAIN = "A: B\nB: C\nC: D\nD: E\nE:\n"
SHORTCUT = "A: B D\nB: C\nC: D\nD: E\nE:\n"
CYCLE = "A: B\nB: C\nC: A D\nD:\n"
LONG_CHAIN_LENGTH = 3000


def source_from(text):
    """Build a package source from the text of a test repository."""
    return FileSource(parse_test_repository(text))


class ChainSource:
    """A very long chain of packages: n0 -> n1 -> n2 -> ..."""

    def dependencies(self, package, version):
        """Return the next package of the chain."""
        number = int(package[1:])
        if number >= LONG_CHAIN_LENGTH:
            return []
        return [Dependency(f"n{number + 1}", "")]


class BrokenSource:
    """A source where loading some packages fails."""

    def __init__(self, broken):
        self._broken = broken

    def dependencies(self, package, version):
        """Fail for broken packages, otherwise return a small tree."""
        if package in self._broken:
            raise RepositoryError(f"{package} is unavailable")
        return {"A": [Dependency("B", ""), Dependency("C", "")]}.get(
            package, []
        )


class BuildGraphTest(unittest.TestCase):
    """Tests for build_graph."""

    def test_diamond_has_shared_dependency_once(self):
        graph = build_graph(source_from(DIAMOND), "A", "", 5)
        self.assertEqual(graph.edges["A"], ["B", "C"])
        self.assertEqual(graph.edges["C"], ["D", "E"])
        self.assertEqual(sorted(graph.depths), ["A", "B", "C", "D", "E"])
        self.assertEqual(graph.depths["D"], 2)
        self.assertEqual(graph.cycles, [])

    def test_depth_one_shows_only_direct_dependencies(self):
        graph = build_graph(source_from(DIAMOND), "A", "", 1)
        self.assertEqual(sorted(graph.depths), ["A", "B", "C"])
        self.assertEqual(graph.unexpanded, ["B", "C"])

    def test_depth_limit_on_chain(self):
        graph = build_graph(source_from(CHAIN), "A", "", 2)
        self.assertEqual(sorted(graph.depths), ["A", "B", "C"])
        self.assertEqual(graph.unexpanded, ["C"])

    def test_package_close_to_root_is_expanded_again(self):
        graph = build_graph(source_from(SHORTCUT), "A", "", 3)
        self.assertEqual(graph.depths["D"], 1)
        self.assertEqual(graph.edges["D"], ["E"])
        self.assertIn("E", graph.depths)

    def test_cycle_is_found_and_analysis_stops(self):
        graph = build_graph(source_from(CYCLE), "A", "", 10)
        self.assertEqual(graph.cycles, [["A", "B", "C", "A"]])
        self.assertIn("D", graph.depths)

    def test_package_depending_on_itself(self):
        graph = build_graph(source_from("A: A\n"), "A", "", 5)
        self.assertEqual(graph.cycles, [["A", "A"]])

    def test_long_chain_does_not_hit_recursion_limit(self):
        graph = build_graph(ChainSource(), "n0", "", LONG_CHAIN_LENGTH + 1)
        self.assertEqual(len(graph.depths), LONG_CHAIN_LENGTH + 1)

    def test_failed_package_is_recorded_and_analysis_goes_on(self):
        graph = build_graph(BrokenSource({"B"}), "A", "", 3)
        self.assertIn("B", graph.failed)
        self.assertEqual(graph.edges["B"], [])
        self.assertEqual(graph.edges["C"], [])

    def test_failed_root_raises_error(self):
        with self.assertRaises(RepositoryError):
            build_graph(BrokenSource({"A"}), "A", "", 3)

    def test_version_of_first_encounter_is_kept(self):
        class Versioned:
            """A with two dependencies on the same package."""

            def dependencies(self, package, version):
                """Return different version ranges of package X."""
                if package == "A":
                    return [Dependency("X", "[1.0, 2.0)"), Dependency("Y", "")]
                if package == "Y":
                    return [Dependency("X", "3.0")]
                return []

        graph = build_graph(Versioned(), "A", "9.9", 5)
        self.assertEqual(graph.versions["X"], "1.0")
        self.assertEqual(graph.versions["A"], "9.9")