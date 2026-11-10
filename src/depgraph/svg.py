"""SVG image of a dependency graph, drawn without third-party libraries.

Packages are drawn as boxes in rows: the row is the distance from the root
package. Dependencies are curves with arrows. Edges that close a cycle are
red and dashed, packages that were not expanded have a dashed border.
"""

from dataclasses import dataclass
from typing import Dict, List, Set, Tuple
from xml.sax.saxutils import escape

from depgraph.graph import Graph
from depgraph.report import label

NODE_HEIGHT = 34
CHAR_WIDTH = 7.8
PADDING_X = 24
GAP_X = 30
GAP_Y = 80
MARGIN = 50
SIDE_ROOM = 120
SIDE_REACH = 36
SIDE_FACTOR = 0.12
LOOP_REACH = 30
LOOP_GAP = 6
FONT_SIZE = 13
EDGE_COLOR = "#555555"
CYCLE_COLOR = "#dc2626"
ARROW = "arrow"
ARROW_CYCLE = "arrow-cycle"
NODE_STYLES = {
    "root": 'fill="#dbeafe" stroke="#2563eb" stroke-width="2"',
    "normal": 'fill="#f3f4f6" stroke="#6b7280" stroke-width="1"',
    "limit": (
        'fill="#ffffff" stroke="#6b7280" stroke-width="1" '
        'stroke-dasharray="5 4"'
    ),
    "failed": 'fill="#fee2e2" stroke="#dc2626" stroke-width="1.5"',
}


@dataclass(frozen=True)
class Box:
    """A package box: horizontal center, top edge and width."""

    name: str
    x: float
    y: float
    width: float


def group_by_depth(graph: Graph) -> List[List[str]]:
    """Group packages into rows by their distance from the root."""
    rows: Dict[int, List[str]] = {}
    for name, depth in graph.depths.items():
        rows.setdefault(depth, []).append(name)
    return [rows[depth] for depth in sorted(rows)]


def box_width(graph: Graph, name: str) -> float:
    """Return the width of a box that fits the package label."""
    return len(label(graph, name)) * CHAR_WIDTH + 2 * PADDING_X


def row_width(graph: Graph, row: List[str]) -> float:
    """Return the total width of a row of boxes with gaps."""
    boxes = sum(box_width(graph, name) for name in row)
    return boxes + GAP_X * (len(row) - 1)


def layout(graph: Graph) -> Tuple[Dict[str, Box], float, float]:
    """Place the boxes; return them with the canvas width and height."""
    rows = group_by_depth(graph)
    widths = [row_width(graph, row) for row in rows]
    canvas_width = max(widths) + 2 * MARGIN
    boxes: Dict[str, Box] = {}
    for level, row in enumerate(rows):
        x = (canvas_width - widths[level]) / 2
        top = MARGIN + level * (NODE_HEIGHT + GAP_Y)
        for name in row:
            width = box_width(graph, name)
            boxes[name] = Box(name, x + width / 2, top, width)
            x += width + GAP_X
    levels = len(rows)
    height = 2 * MARGIN + levels * NODE_HEIGHT + (levels - 1) * GAP_Y
    return boxes, canvas_width, height


def down_path(parent: Box, child: Box) -> str:
    """Return a curve from the bottom of a box to the top of a lower box."""
    start_y = parent.y + NODE_HEIGHT
    middle = (start_y + child.y) / 2
    return (
        f"M {parent.x:.1f} {start_y:.1f} "
        f"C {parent.x:.1f} {middle:.1f} {child.x:.1f} {middle:.1f} "
        f"{child.x:.1f} {child.y:.1f}"
    )


def side_path(parent: Box, child: Box) -> str:
    """Return a curve along the right side for an edge that goes up."""
    start_x = parent.x + parent.width / 2
    end_x = child.x + child.width / 2
    start_y = parent.y + NODE_HEIGHT / 2
    end_y = child.y + NODE_HEIGHT / 2
    reach = SIDE_REACH + abs(end_y - start_y) * SIDE_FACTOR
    return (
        f"M {start_x:.1f} {start_y:.1f} "
        f"C {start_x + reach:.1f} {start_y:.1f} "
        f"{end_x + reach:.1f} {end_y:.1f} {end_x:.1f} {end_y:.1f}"
    )


def loop_path(box: Box) -> str:
    """Return a small loop for a package that depends on itself."""
    x = box.x + box.width / 2
    y = box.y + NODE_HEIGHT / 2
    return (
        f"M {x:.1f} {y - LOOP_GAP:.1f} "
        f"C {x + LOOP_REACH:.1f} {y - LOOP_REACH:.1f} "
        f"{x + LOOP_REACH:.1f} {y + LOOP_REACH:.1f} "
        f"{x:.1f} {y + LOOP_GAP:.1f}"
    )


def edge_path(parent: Box, child: Box) -> str:
    """Choose the curve for a dependency between two boxes."""
    if parent == child:
        return loop_path(parent)
    if child.y > parent.y:
        return down_path(parent, child)
    return side_path(parent, child)


def edge_element(parent: Box, child: Box, is_cycle: bool) -> str:
    """Return the SVG element of one dependency."""
    color, marker = EDGE_COLOR, ARROW
    dash = ""
    if is_cycle:
        color, marker = CYCLE_COLOR, ARROW_CYCLE
        dash = ' stroke-dasharray="6 4"'
    return (
        f'<path class="edge" d="{edge_path(parent, child)}" fill="none" '
        f'stroke="{color}" stroke-width="1.5"{dash} '
        f'marker-end="url(#{marker})"/>'
    )


def node_kind(graph: Graph, name: str, unexpanded: Set[str]) -> str:
    """Return the style name of a package box."""
    if name in graph.failed:
        return "failed"
    if name == graph.root:
        return "root"
    return "limit" if name in unexpanded else "normal"


def node_element(graph: Graph, box: Box, kind: str) -> str:
    """Return the SVG element of one package box with its label."""
    left = box.x - box.width / 2
    middle = box.y + NODE_HEIGHT / 2
    text = escape(label(graph, box.name))
    return (
        f'<g class="node {kind}">'
        f'<rect x="{left:.1f}" y="{box.y:.1f}" width="{box.width:.1f}" '
        f'height="{NODE_HEIGHT}" rx="6" {NODE_STYLES[kind]}/>'
        f'<text x="{box.x:.1f}" y="{middle:.1f}" text-anchor="middle" '
        f'dominant-baseline="central" fill="#111827">{text}</text></g>'
    )


def arrow_marker(name: str, color: str) -> str:
    """Return the definition of an arrow head."""
    return (
        f'<marker id="{name}" viewBox="0 0 10 10" refX="9" refY="5" '
        f'markerWidth="8" markerHeight="8" orient="auto">'
        f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{color}"/></marker>'
    )


def header(title: str, width: float, height: float) -> List[str]:
    """Return the opening lines of the SVG document."""
    total = width + SIDE_ROOM
    return [
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{total:.0f}" height="{height:.0f}" '
        f'viewBox="0 0 {total:.0f} {height:.0f}" '
        f'font-family="Consolas, Menlo, monospace" font-size="{FONT_SIZE}">',
        f"<title>{escape(title)}</title>",
        "<defs>",
        arrow_marker(ARROW, EDGE_COLOR),
        arrow_marker(ARROW_CYCLE, CYCLE_COLOR),
        "</defs>",
        '<rect width="100%" height="100%" fill="#ffffff"/>',
    ]


def cycle_edges(graph: Graph) -> Set[Tuple[str, str]]:
    """Return all edges that belong to found cycles."""
    pairs: Set[Tuple[str, str]] = set()
    for cycle in graph.cycles:
        pairs.update(zip(cycle, cycle[1:]))
    return pairs


def render_svg(graph: Graph) -> str:
    """Return the whole graph as the text of an SVG document."""
    boxes, width, height = layout(graph)
    cycles = cycle_edges(graph)
    unexpanded = set(graph.unexpanded)
    title = f"Dependencies of {label(graph, graph.root)}"
    lines = header(title, width, height)
    lines.append('<g class="edges">')
    for parent, children in graph.edges.items():
        for child in children:
            is_cycle = (parent, child) in cycles
            lines.append(edge_element(boxes[parent], boxes[child], is_cycle))
    lines.extend(["</g>", '<g class="nodes">'])
    for name, box in boxes.items():
        kind = node_kind(graph, name, unexpanded)
        lines.append(node_element(graph, box, kind))
    lines.extend(["</g>", "</svg>"])
    return "\n".join(lines)


def write_svg(path: str, graph: Graph) -> None:
    """Draw the graph and save it to an SVG file."""
    with open(path, "w", encoding="utf-8") as file:
        file.write(render_svg(graph))