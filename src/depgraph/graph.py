"""Dependency graph construction with an iterative depth-first search."""

from dataclasses import dataclass, field
from typing import Dict, List, Protocol, Tuple

from depgraph.nuget import Dependency, RepositoryError, resolve_version

GRAY = 1
BLACK = 2


class Source(Protocol):
    """Anything that can list direct dependencies of a package."""

    def dependencies(self, package: str, version: str) -> List[Dependency]:
        """Return direct dependencies of the package."""


@dataclass
class Graph:
    """Dependency graph built from a root package.

    edges: expanded packages and their dependencies, in order of expansion;
    depths: shortest known distance from the root for every package;
    versions: the version used for every package (first one met);
    failed: packages whose data could not be loaded, with the reason;
    cycles: dependency cycles, each as a path that ends where it started.
    """

    root: str
    max_depth: int
    edges: Dict[str, List[str]] = field(default_factory=dict)
    depths: Dict[str, int] = field(default_factory=dict)
    versions: Dict[str, str] = field(default_factory=dict)
    failed: Dict[str, str] = field(default_factory=dict)
    cycles: List[List[str]] = field(default_factory=list)

    @property
    def unexpanded(self) -> List[str]:
        """Packages where the depth limit stopped the analysis."""
        return [name for name in self.depths if name not in self.edges]


def expand(graph: Graph, source: Source, name: str) -> List[str]:
    """Return dependencies of a package, loading them from the source once.

    An error for a package other than the root does not stop the analysis:
    the package is recorded as failed and treated as having no dependencies.
    """
    if name in graph.edges:
        return graph.edges[name]
    try:
        found = source.dependencies(name, graph.versions[name])
    except RepositoryError as error:
        if name == graph.root:
            raise
        graph.failed[name] = str(error)
        found = []
    children: List[str] = []
    for dependency in found:
        version = resolve_version(dependency.version_range)
        graph.versions.setdefault(dependency.name, version)
        if dependency.name not in children:
            children.append(dependency.name)
    graph.edges[name] = children
    return children


def find_cycles(graph: Graph) -> List[List[str]]:
    """Find dependency cycles reachable from the root, without recursion.

    Every edge that leads back to a package on the current path closes
    one cycle.
    """
    cycles: List[List[str]] = []
    color = {graph.root: GRAY}
    path = [graph.root]
    iterators = [iter(graph.edges.get(graph.root, []))]
    while iterators:
        child = next(iterators[-1], None)
        if child is None:
            color[path.pop()] = BLACK
            iterators.pop()
        elif color.get(child) == GRAY:
            cycles.append(path[path.index(child):] + [child])
        elif child not in color:
            color[child] = GRAY
            path.append(child)
            iterators.append(iter(graph.edges.get(child, [])))
    return cycles


def build_graph(
    source: Source, root: str, root_version: str, max_depth: int
) -> Graph:
    """Build the dependency graph of a package with an iterative DFS.

    The stack holds (package, depth) pairs. A package met again at the
    same or a greater depth is skipped, which also stops cycles. A package
    met at a smaller depth is processed again, so the depth limit never
    hides packages that are close to the root.
    """
    graph = Graph(root, max_depth)
    graph.versions[root] = root_version
    stack: List[Tuple[str, int]] = [(root, 0)]
    while stack:
        name, depth = stack.pop()
        if name in graph.depths and graph.depths[name] <= depth:
            continue
        graph.depths[name] = depth
        if depth >= max_depth:
            continue
        for child in reversed(expand(graph, source, name)):
            stack.append((child, depth + 1))
    graph.cycles = find_cycles(graph)
    return graph