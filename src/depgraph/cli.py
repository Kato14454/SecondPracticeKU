"""Command-line interface of the dependency graph tool."""

import argparse
import sys
from typing import Optional, Sequence

from depgraph.config import Config, ConfigError, build_config
from depgraph.nuget import (
    Dependency,
    RepositoryError,
    get_direct_dependencies,
)

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
        "--package-version", required=True, help="version of the package"
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


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser with all user-defined options."""
    parser = argparse.ArgumentParser(
        prog="depgraph",
        description="Visualize the dependency graph of a NuGet package.",
    )
    add_source_options(parser)
    add_output_options(parser)
    return parser


def format_dependencies(
    config: Config, dependencies: Sequence[Dependency]
) -> str:
    """Return direct dependencies as text, one package per line."""
    lines = [f"Direct dependencies of {config.package} {config.version}:"]
    if not dependencies:
        lines.append("  (none)")
    for dependency in dependencies:
        lines.append(f"  {dependency.name} {dependency.version_range}")
    return "\n".join(lines)


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
    if config.test_mode:
        return report_error(
            "test mode is not available before stage 3", EXIT_CONFIG_ERROR
        )
    try:
        dependencies = get_direct_dependencies(
            config.repo, config.package, config.version
        )
    except RepositoryError as error:
        return report_error(error, EXIT_RUNTIME_ERROR)
    print(format_dependencies(config, dependencies))
    return EXIT_OK