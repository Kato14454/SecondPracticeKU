"""User parameters of the tool and their validation."""

import argparse
import os
import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

PACKAGE_NAME_PATTERN = re.compile(r"[A-Za-z0-9_.\-]+")
VERSION_PATTERN = re.compile(
    r"\d+(\.\d+){1,3}(-[0-9A-Za-z.\-]+)?(\+[0-9A-Za-z.\-]+)?"
)
ALLOWED_SCHEMES = ("http", "https")
IMAGE_EXTENSION = ".svg"
MIN_DEPTH = 1


class ConfigError(ValueError):
    """Raised when a user-supplied parameter is invalid."""


@dataclass(frozen=True)
class Config:
    """Validated user parameters."""

    package: str
    repo: str
    test_mode: bool
    version: str
    output: str
    ascii_tree: bool
    max_depth: int
    load_order: bool = False


def validate_package(name: str) -> str:
    """Check the package name and return it unchanged."""
    if not PACKAGE_NAME_PATTERN.fullmatch(name):
        raise ConfigError(
            f"invalid package name: {name!r} "
            "(allowed: letters, digits, '.', '_', '-')"
        )
    return name


def validate_repo(repo: str, test_mode: bool) -> str:
    """Check the repository URL or the test repository file path."""
    if test_mode:
        if not os.path.isfile(repo):
            raise ConfigError(f"test repository file not found: {repo}")
        return repo
    parsed = urlparse(repo)
    if parsed.scheme not in ALLOWED_SCHEMES or not parsed.netloc:
        raise ConfigError(f"invalid repository URL: {repo!r}")
    return repo


def validate_version(version: Optional[str], test_mode: bool = False) -> str:
    """Check the package version; it may be omitted in test mode."""
    if version is None:
        if test_mode:
            return ""
        raise ConfigError("package version is required: --package-version")
    if not VERSION_PATTERN.fullmatch(version):
        raise ConfigError(f"invalid package version: {version!r}")
    return version


def validate_output(output: str) -> str:
    """Check the image file name: extension and existing directory."""
    if not output.lower().endswith(IMAGE_EXTENSION):
        raise ConfigError(
            f"output file must have {IMAGE_EXTENSION} extension: {output!r}"
        )
    directory = os.path.dirname(output) or os.curdir
    if not os.path.isdir(directory):
        raise ConfigError(f"output directory does not exist: {directory}")
    return output


def validate_max_depth(depth: int) -> int:
    """Check the maximum analysis depth and return it unchanged."""
    if depth < MIN_DEPTH:
        raise ConfigError(f"max depth must be at least {MIN_DEPTH}: {depth}")
    return depth


def build_config(args: argparse.Namespace) -> Config:
    """Validate parsed arguments and build a Config."""
    return Config(
        package=validate_package(args.package),
        repo=validate_repo(args.repo, args.test_mode),
        test_mode=args.test_mode,
        version=validate_version(args.package_version, args.test_mode),
        output=validate_output(args.output),
        ascii_tree=args.ascii_tree,
        max_depth=validate_max_depth(args.max_depth),
        load_order=args.load_order,
    )