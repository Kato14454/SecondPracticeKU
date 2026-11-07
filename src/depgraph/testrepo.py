"""Test repository: a text file that describes a package graph.

Format: one package per line, "A: B C" means A depends on B and C.
Package names are capital Latin letters. "#" starts a comment.
"""

import re
from typing import Dict, List, Set

from depgraph.nuget import Dependency, RepositoryError

LINE_PATTERN = re.compile(r"([A-Z]+)\s*:\s*([A-Z\s]*)")
COMMENT_MARK = "#"


class FileSource:
    """Package source backed by a parsed test repository."""

    def __init__(self, graph: Dict[str, List[str]]) -> None:
        """Remember the graph and the set of all package names in it."""
        self._graph = graph
        self._known: Set[str] = set(graph)
        for names in graph.values():
            self._known.update(names)

    def contains(self, package: str) -> bool:
        """Tell whether the package is mentioned in the repository."""
        return package in self._known

    def dependencies(self, package: str, version: str) -> List[Dependency]:
        """Return direct dependencies; the version is not used."""
        return [Dependency(name, "") for name in self._graph.get(package, [])]


def parse_line(line: str, number: int) -> List[str]:
    """Split a non-empty line into the package name and its dependencies."""
    match = LINE_PATTERN.fullmatch(line)
    if match is None:
        raise RepositoryError(f"line {number}: invalid format: {line!r}")
    return [match.group(1)] + match.group(2).split()


def parse_test_repository(text: str) -> Dict[str, List[str]]:
    """Parse the text of a test repository into an adjacency dictionary."""
    graph: Dict[str, List[str]] = {}
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.split(COMMENT_MARK, 1)[0].strip()
        if not line:
            continue
        name, *dependencies = parse_line(line, number)
        if name in graph:
            raise RepositoryError(f"line {number}: {name} is defined twice")
        graph[name] = dependencies
    return graph


def load_test_repository(path: str) -> FileSource:
    """Read a test repository file and return a package source."""
    try:
        with open(path, encoding="utf-8") as file:
            text = file.read()
    except OSError as error:
        raise RepositoryError(f"cannot read {path}: {error}") from error
    return FileSource(parse_test_repository(text))
