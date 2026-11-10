"""Tests for the SVG output."""

import os
import tempfile
import unittest
import xml.etree.ElementTree as ET

from depgraph.graph import build_graph
from depgraph.svg import layout, render_svg, write_svg
from depgraph.testrepo import FileSource, parse_test_repository

DIAMOND = "A: B C\nB: D\nC: D E\nD:\nE:\n"
SVG_NAMESPACE = "{http://www.w3.org/2000/svg}"


def graph_of(text, depth=5, root="A"):
    """Build the graph of a package from the text of a test repository."""
    source = FileSource(parse_test_repository(text))
    return build_graph(source, root, "", depth)


def elements(svg_text, tag, kind=None):
    """Return elements with a tag and, optionally, a class word."""
    root = ET.fromstring(svg_text)
    found = root.iter(SVG_NAMESPACE + tag)
    if kind is None:
        return list(found)
    return [item for item in found if kind in item.get("class", "").split()]


class RenderSvgTest(unittest.TestCase):
    """Tests for render_svg."""

    def test_result_is_valid_xml_with_svg_root(self):
        root = ET.fromstring(render_svg(graph_of(DIAMOND)))
        self.assertEqual(root.tag, SVG_NAMESPACE + "svg")

    def test_one_box_per_package_and_one_curve_per_dependency(self):
        text = render_svg(graph_of(DIAMOND))
        self.assertEqual(len(elements(text, "g", "node")), 5)
        self.assertEqual(len(elements(text, "path", "edge")), 5)

    def test_labels_are_written(self):
        text = render_svg(graph_of(DIAMOND))
        labels = sorted(item.text for item in elements(text, "text"))
        self.assertEqual(labels, ["A", "B", "C", "D", "E"])

    def test_special_characters_are_escaped(self):
        source = FileSource({"A": ["B"]})
        graph = build_graph(source, "A", "1<2&3", 3)
        text = render_svg(graph)
        self.assertIn("A 1&lt;2&amp;3", text)
        ET.fromstring(text)

    def test_root_and_unexpanded_boxes_have_their_own_style(self):
        text = render_svg(graph_of("A: B\nB: C\nC:\n", depth=1))
        self.assertEqual(len(elements(text, "g", "root")), 1)
        self.assertEqual(len(elements(text, "g", "limit")), 1)

    def test_cycle_edges_are_dashed(self):
        text = render_svg(graph_of("A: B\nB: A\n"))
        dashed = [
            item for item in elements(text, "path", "edge")
            if item.get("stroke-dasharray")
        ]
        self.assertEqual(len(dashed), 2)

    def test_self_dependency_is_drawn(self):
        text = render_svg(graph_of("A: A\n"))
        self.assertEqual(len(elements(text, "path", "edge")), 1)

    def test_single_package(self):
        text = render_svg(graph_of("A:\n"))
        self.assertEqual(len(elements(text, "g", "node")), 1)


class LayoutTest(unittest.TestCase):
    """Tests for layout."""

    def test_rows_follow_depth(self):
        boxes, _, _ = layout(graph_of(DIAMOND))
        self.assertLess(boxes["A"].y, boxes["B"].y)
        self.assertEqual(boxes["B"].y, boxes["C"].y)
        self.assertLess(boxes["C"].y, boxes["D"].y)

    def test_boxes_in_a_row_do_not_overlap(self):
        boxes, _, _ = layout(graph_of("A: B C D E\nB:\nC:\nD:\nE:\n"))
        row = sorted(
            (boxes[name] for name in "BCDE"), key=lambda box: box.x
        )
        for left, right in zip(row, row[1:]):
            self.assertLess(
                left.x + left.width / 2, right.x - right.width / 2
            )

    def test_boxes_are_inside_the_canvas(self):
        boxes, width, height = layout(graph_of(DIAMOND))
        for box in boxes.values():
            self.assertGreaterEqual(box.x - box.width / 2, 0)
            self.assertLessEqual(box.x + box.width / 2, width)
            self.assertLessEqual(box.y + 1, height)


class WriteSvgTest(unittest.TestCase):
    """Tests for write_svg."""

    def test_file_is_written(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "graph.svg")
            write_svg(path, graph_of(DIAMOND))
            with open(path, encoding="utf-8") as file:
                ET.fromstring(file.read())

    def test_unwritable_path_raises_os_error(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(OSError):
                write_svg(directory, graph_of(DIAMOND))