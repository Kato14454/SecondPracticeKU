"""Command-line interface of the dependency graph tool."""

import argparse
import sys
from dataclasses import asdict
from typing import Optional, Sequence

from depgraph.config import Config, ConfigError, build_config

DEFAULT_OUTPUT = "graph.svg"
DEFAULT_MAX_DEPTH = 3
EXIT_OK = 0
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


def format_config(config: Config) -> str:
    """Return the parameters as key-value lines."""
    lines = [f"{key}: {value}" for key, value in asdict(config).items()]
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the tool and return a process exit code."""
    args = create_parser().parse_args(argv)
    try:
        config = build_config(args)
    except ConfigError as error:
        print(f"depgraph: error: {error}", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    print(format_config(config))
    return EXIT_OK