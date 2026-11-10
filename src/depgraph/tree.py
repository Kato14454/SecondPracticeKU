"""ASCII tree output of a dependency graph."""

from typing import List, Set

from depgraph.graph import Graph
from depgraph.report import label

BRANCH = "|-- "
LAST = "`-- "
PIPE = "|   "
SPACE = "    "
MARK_NONE = ""
MARK_CYCLE = " (cycle)"
MARK_SHOWN = " (*)"
MARK_LIMIT = " (...)"
LEGEND = {
    MARK_SHOWN: "(*) shown above",
    MARK_LIMIT: "(...) not expanded: depth limit",
    MARK_CYCLE: "(cycle) closes a dependency cycle",
}


def child_mark(
    graph: Graph, child: str, shown: Set[str], path: List[str]
) -> str:
    """Return the mark that tells how a package is shown in the tree."""
    if child in path:
        return MARK_CYCLE
    if child in shown:
        return MARK_SHOWN
    if child not in graph.edges:
        return MARK_LIMIT
    return MARK_NONE


def legend(used: Set[str]) -> List[str]:
    """Return a legend line for the marks that appear in the tree."""
    notes = [text for mark, text in LEGEND.items() if mark in used]
    return ["Legend: " + "; ".join(notes)] if notes else []


def format_tree(graph: Graph) -> str:
    """Return the graph as an ASCII tree, without recursion.

    A package is expanded only where it is first met; later it is shown
    with a mark. A package that is already on the current path closes a
    cycle and is not expanded either.
    """
    lines = [label(graph, graph.root)]
    used: Set[str] = set()
    shown = {graph.root}
    path = [graph.root]
    stack = [[graph.edges.get(graph.root, []), 0, ""]]
    while stack:
        children, index, prefix = stack[-1]
        if index >= len(children):
            stack.pop()
            path.pop()
            continue
        stack[-1][1] += 1
        child = children[index]
        is_last = index == len(children) - 1
        mark = child_mark(graph, child, shown, path)
        used.add(mark)
        shown.add(child)
        connector = LAST if is_last else BRANCH
        lines.append(prefix + connector + label(graph, child) + mark)
        if mark == MARK_NONE:
            path.append(child)
            deeper = prefix + (SPACE if is_last else PIPE)
            stack.append([graph.edges[child], 0, deeper])
    return "\n".join(lines + legend(used))