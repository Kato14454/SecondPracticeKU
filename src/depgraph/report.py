"""Text output of a dependency graph."""

from typing import List

from depgraph.graph import Graph
from depgraph.order import load_order


def label(graph: Graph, name: str) -> str:
    """Return the package name with its version, if it has one."""
    version = graph.versions.get(name, "")
    return f"{name} {version}" if version else name


def format_edges(graph: Graph) -> List[str]:
    """Return one line per expanded package with its dependencies."""
    lines = []
    for name, children in graph.edges.items():
        targets = ", ".join(label(graph, child) for child in children)
        lines.append(f"  {label(graph, name)} -> {targets or '(none)'}")
    return lines


def format_notes(graph: Graph) -> List[str]:
    """Return lines about cycles, depth limit and loading errors."""
    lines = []
    if graph.cycles:
        lines.append("Cycles found:")
        for cycle in graph.cycles:
            lines.append("  " + " -> ".join(cycle))
    if graph.unexpanded:
        names = ", ".join(graph.unexpanded)
        lines.append(f"Depth limit reached, not expanded: {names}")
    if graph.failed:
        lines.append("Could not load:")
        for name, reason in graph.failed.items():
            lines.append(f"  {name}: {reason}")
    return lines


def format_graph(graph: Graph) -> str:
    """Return the whole graph as text."""
    count = sum(len(children) for children in graph.edges.values())
    title = (
        f"Dependency graph of {label(graph, graph.root)} "
        f"(max depth {graph.max_depth}): "
        f"{len(graph.depths)} packages, {count} dependencies"
    )
    return "\n".join([title] + format_edges(graph) + format_notes(graph))


def format_load_order(graph: Graph) -> str:
    """Return the load order of dependencies as text."""
    order = load_order(graph)
    title = (
        f"Load order of {label(graph, graph.root)} "
        f"(dependencies first, max depth {graph.max_depth}): "
        f"{len(order)} packages"
    )
    lines = [
        f"  {number}. {label(graph, name)}"
        for number, name in enumerate(order, start=1)
    ]
    notes = format_notes(graph)
    if graph.cycles:
        notes.append("Edges that close cycles were ignored in the order.")
    return "\n".join([title] + lines + notes)