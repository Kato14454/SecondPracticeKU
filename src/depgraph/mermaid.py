"""Mermaid text representation of a dependency graph."""

from typing import Dict, List

from depgraph.graph import Graph
from depgraph.report import label

QUOTE_ESCAPE = "#quot;"
LIMIT_CLASS = "limit"
INDENT = "    "


def mermaid_label(text: str) -> str:
    """Make a text safe to put inside a quoted Mermaid node label."""
    return text.replace('"', QUOTE_ESCAPE)


def node_ids(graph: Graph) -> Dict[str, str]:
    """Give every package a short identifier: n0, n1, ..."""
    return {name: f"n{index}" for index, name in enumerate(graph.depths)}


def limit_styles(graph: Graph, ids: Dict[str, str]) -> List[str]:
    """Return lines that draw not expanded packages with a dashed border."""
    if not graph.unexpanded:
        return []
    names = ",".join(ids[name] for name in graph.unexpanded)
    return [
        f"{INDENT}classDef {LIMIT_CLASS} stroke-dasharray: 4 4",
        f"{INDENT}class {names} {LIMIT_CLASS}",
    ]


def format_mermaid(graph: Graph) -> str:
    """Return the graph as a Mermaid flowchart (top to bottom)."""
    ids = node_ids(graph)
    lines = ["graph TD"]
    for name, node_id in ids.items():
        text = mermaid_label(label(graph, name))
        lines.append(f'{INDENT}{node_id}["{text}"]')
    for parent, children in graph.edges.items():
        for child in children:
            lines.append(f"{INDENT}{ids[parent]} --> {ids[child]}")
    lines.extend(limit_styles(graph, ids))
    return "\n".join(lines)