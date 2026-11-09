"""Command-line interface of the dependency graph tool."""

import argparse
import sys
from typing import Optional, Sequence

from depgraph.config import Config, ConfigError, build_config
from depgraph.graph import Graph, Source, build_graph
from depgraph.nuget import NugetSource, RepositoryError
from depgraph.report import format_graph, format_load_order
from depgraph.testrepo import load_test_repository

DEFAULT_OUTPUT = "graph.svg"
DEFAULT_MAX_DEPTH = 3
EXIT_OK = 0
EXIT_RUNTIME_ERROR = 1
EXIT_CONFIG_ERROR = 2


def add_source_options(parser: argparse.ArgumentParser) -> None:
    """Add options that describe the analyzed package and repository."""
    parser.add_argument(
        "--package", required=True, help="name of the analyzed package"
    )
    parser.add_argument(
        "--repo",
        required=True,
        help="repository URL or path to a test repository file",
    )
    parser.add_argument(
        "--test-mode",
        action="store_true",
        help="treat --repo as a path to a test repository file",
    )
    parser.add_argument(
        "--package-version",
        help="version of the package (not needed in test mode)",
    )


def add_output_options(parser: argparse.ArgumentParser) -> None:
    """Add options that control analysis depth and result output."""
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help="name of the generated image file (default: %(default)s)",
    )
    parser.add_argument(
        "--ascii-tree",
        action="store_true",
        help="print dependencies as an ASCII tree",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=DEFAULT_MAX_DEPTH,
        help="maximum dependency analysis depth (default: %(default)s)",
    )
    parser.add_argument(
        "--load-order",
        action="store_true",
        help="print the order in which dependencies must be loaded",
    )


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser with all user-defined options."""
    parser = argparse.ArgumentParser(
        prog="depgraph",
        description="Visualize the dependency graph of a NuGet package.",
    )
    add_source_options(parser)
    add_output_options(parser)
    return parser


def create_source(config: Config) -> Source:
    """Return the package source selected by the configuration."""
    if not config.test_mode:
        return NugetSource(config.repo)
    source = load_test_repository(config.repo)
    if not source.contains(config.package):
        raise RepositoryError(
            f"package {config.package} is not in {config.repo}"
        )
    return source


def make_graph(config: Config) -> Graph:
    """Build the dependency graph described by the configuration."""
    return build_graph(
        create_source(config),
        config.package,
        config.version,
        config.max_depth,
    )


def render(config: Config, graph: Graph) -> str:
    """Return the text selected by the output mode."""
    if config.load_order:
        return format_load_order(graph)
    return format_graph(graph)


def report_error(message: object, code: int) -> int:
    """Print an error message to stderr and return the exit code."""
    print(f"depgraph: error: {message}", file=sys.stderr)
    return code


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the tool and return a process exit code."""
    args = create_parser().parse_args(argv)
    try:
        config = build_config(args)
    except ConfigError as error:
        return report_error(error, EXIT_CONFIG_ERROR)
    try:
        graph = make_graph(config)
    except RepositoryError as error:
        return report_error(error, EXIT_RUNTIME_ERROR)
    print(render(config, graph))
    return EXIT_OK