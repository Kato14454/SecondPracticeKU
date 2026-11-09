"""Load order of dependencies: dependencies come before dependents."""

from typing import Iterator, List, Tuple

from depgraph.graph import Graph


def iter_children(graph: Graph, name: str) -> Iterator[str]:
    """Return an iterator over the dependencies of a package."""
    return iter(graph.edges.get(name, []))


def load_order(graph: Graph) -> List[str]:
    """Return packages in the order they must be loaded, without recursion.

    This is the post-order of a depth-first search: a package is listed
    after all of its dependencies, so the root package comes last. An edge
    that closes a cycle is ignored, so every package is listed once.
    """
    order: List[str] = []
    visited = {graph.root}
    stack: List[Tuple[str, Iterator[str]]] = [
        (graph.root, iter_children(graph, graph.root))
    ]
    while stack:
        name, children = stack[-1]
        child = next(children, None)
        if child is None:
            order.append(name)
            stack.pop()
        elif child not in visited:
            visited.add(child)
            stack.append((child, iter_children(graph, child)))
    return order