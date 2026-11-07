"""Tests for the test repository file format."""

import os
import tempfile
import unittest

from depgraph.nuget import Dependency, RepositoryError
from depgraph.testrepo import (
    FileSource,
    load_test_repository,
    parse_test_repository,
)

SAMPLE = """# a comment
A: B C   # trailing comment

B: C
C:
"""


class ParseTestRepositoryTest(unittest.TestCase):
    """Tests for parse_test_repository."""

    def test_comments_and_blank_lines_are_ignored(self):
        graph = parse_test_repository(SAMPLE)
        self.assertEqual(graph, {"A": ["B", "C"], "B": ["C"], "C": []})

    def test_lowercase_name_is_rejected(self):
        with self.assertRaises(RepositoryError):
            parse_test_repository("a: B\n")

    def test_line_without_colon_is_rejected(self):
        with self.assertRaises(RepositoryError):
            parse_test_repository("A B C\n")

    def test_error_mentions_line_number(self):
        with self.assertRaises(RepositoryError) as context:
            parse_test_repository("A: B\nbad line\n")
        self.assertIn("line 2", str(context.exception))

    def test_duplicate_definition_is_rejected(self):
        with self.assertRaises(RepositoryError):
            parse_test_repository("A: B\nA: C\n")


class FileSourceTest(unittest.TestCase):
    """Tests for FileSource and load_test_repository."""

    def test_dependencies_have_no_version_range(self):
        source = FileSource({"A": ["B"]})
        self.assertEqual(source.dependencies("A", ""), [Dependency("B", "")])

    def test_unknown_package_has_no_dependencies(self):
        self.assertEqual(FileSource({}).dependencies("Z", ""), [])

    def test_contains_package_mentioned_only_as_dependency(self):
        source = FileSource({"A": ["B"]})
        self.assertTrue(source.contains("B"))
        self.assertFalse(source.contains("Z"))

    def test_load_from_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "repo.txt")
            with open(path, "w", encoding="utf-8") as file:
                file.write("A: B\n")
            self.assertTrue(load_test_repository(path).contains("B"))

    def test_load_missing_file(self):
        with self.assertRaises(RepositoryError):
            load_test_repository("no_such_file.txt")