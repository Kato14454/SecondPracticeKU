"""Tests for the load order of dependencies."""

import unittest

from depgraph.graph import build_graph
from depgraph.nuget import Dependency
from depgraph.order import load_order
from depgraph.testrepo import FileSource, parse_test_repository

DIAMOND = "A: B C\nB: D\nC: D E\nD:\nE:\n"
CHAIN = "A: B\nB: C\nC: D\nD: E\nE:\n"
SHORTCUT = "A: B D\nB: C\nC: D\nD: E\nE:\n"
CYCLE = "A: B\nB: C\nC: A D\nD:\n"
LONG_CHAIN_LENGTH = 3000


def graph_of(text, depth=10):
    """Build the graph of package A from the text of a test repository."""
    source = FileSource(parse_test_repository(text))
    return build_graph(source, "A", "", depth)


class ChainSource:
    """A very long chain of packages: n0 -> n1 -> n2 -> ..."""

    def dependencies(self, package, version):
        """Return the next package of the chain."""
        number = int(package[1:])
        if number >= LONG_CHAIN_LENGTH:
            return []
        return [Dependency(f"n{number + 1}", "")]


class LoadOrderTest(unittest.TestCase):
    """Tests for load_order."""

    def test_chain_is_loaded_from_the_end(self):
        order = load_order(graph_of(CHAIN))
        self.assertEqual(order, ["E", "D", "C", "B", "A"])

    def test_diamond_order(self):
        order = load_order(graph_of(DIAMOND))
        self.assertEqual(order, ["D", "B", "E", "C", "A"])

    def test_package_without_dependencies(self):
        self.assertEqual(load_order(graph_of("A:\n")), ["A"])

    def test_every_dependency_comes_before_its_dependent(self):
        for text in (DIAMOND, CHAIN, SHORTCUT):
            graph = graph_of(text)
            position = {n: i for i, n in enumerate(load_order(graph))}
            for name, children in graph.edges.items():
                for child in children:
                    self.assertLess(position[child], position[name])

    def test_root_is_last_and_each_package_once(self):
        order = load_order(graph_of(DIAMOND))
        self.assertEqual(order[-1], "A")
        self.assertEqual(len(order), len(set(order)))

    def test_cycle_does_not_hang_and_lists_every_package_once(self):
        order = load_order(graph_of(CYCLE))
        self.assertEqual(sorted(order), ["A", "B", "C", "D"])
        self.assertEqual(order[-1], "A")

    def test_packages_at_depth_limit_are_included(self):
        order = load_order(graph_of(CHAIN, depth=2))
        self.assertEqual(order, ["C", "B", "A"])

    def test_long_chain_does_not_hit_recursion_limit(self):
        graph = build_graph(ChainSource(), "n0", "", LONG_CHAIN_LENGTH + 1)
        order = load_order(graph)
        self.assertEqual(len(order), LONG_CHAIN_LENGTH + 1)
        self.assertEqual(order[0], f"n{LONG_CHAIN_LENGTH}")