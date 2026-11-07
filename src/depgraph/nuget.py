"""Access to a NuGet repository using only the standard library."""

import json
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, List

PACKAGE_BASE_TYPE = "PackageBaseAddress"
REQUEST_TIMEOUT_SECONDS = 15
HTTP_NOT_FOUND = 404
USER_AGENT = "depgraph/0.3"
MIN_VERSION_PARTS = 3
MAX_VERSION_PARTS = 4
ZERO_PART = "0"


class RepositoryError(RuntimeError):
    """Raised when package data cannot be obtained or understood."""


@dataclass(frozen=True)
class Dependency:
    """A direct dependency: package name and its version range."""

    name: str
    version_range: str


def fetch(url: str) -> bytes:
    """Download a URL and return the response body."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    timeout = REQUEST_TIMEOUT_SECONDS
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        if error.code == HTTP_NOT_FOUND:
            raise RepositoryError(f"not found (HTTP 404): {url}") from error
        raise RepositoryError(f"HTTP {error.code} for {url}") from error
    except urllib.error.URLError as error:
        raise RepositoryError(f"cannot reach {url}: {error.reason}") from error


def find_package_base(index: bytes) -> str:
    """Find the address of package files in the repository index."""
    try:
        resources = json.loads(index)["resources"]
    except (ValueError, KeyError, TypeError) as error:
        raise RepositoryError("invalid repository index") from error
    for resource in resources:
        kind = str(resource.get("@type", ""))
        if kind.startswith(PACKAGE_BASE_TYPE) and resource.get("@id"):
            return resource["@id"].rstrip("/") + "/"
    raise RepositoryError("repository index has no PackageBaseAddress")


def normalize_version(version: str) -> str:
    """Convert a version to the form NuGet uses in repository addresses.

    Missing parts are filled with zeros ("1.0" -> "1.0.0"), a zero
    fourth part is dropped, build metadata is removed, letters are
    lowercased.
    """
    main = version.partition("+")[0]
    core, dash, suffix = main.partition("-")
    parts = [str(int(p)) if p.isdigit() else p for p in core.split(".")]
    while len(parts) < MIN_VERSION_PARTS:
        parts.append(ZERO_PART)
    if len(parts) == MAX_VERSION_PARTS and parts[-1] == ZERO_PART:
        parts.pop()
    return (".".join(parts) + dash + suffix).lower()


def resolve_version(version_range: str) -> str:
    """Pick a concrete version from a NuGet version range.

    The lower bound is used ("[1.0, 2.0)" -> "1.0"); if there is none,
    the upper bound is used. A plain version is returned unchanged.
    """
    text = version_range.strip().strip("[]()")
    for bound in text.split(","):
        if bound.strip():
            return bound.strip()
    return ""


def build_nuspec_url(base: str, package: str, version: str) -> str:
    """Build the address of the package description (.nuspec) file."""
    name = package.lower()
    return f"{base}{name}/{normalize_version(version)}/{name}.nuspec"


def local_name(tag: str) -> str:
    """Return an XML tag name without its namespace."""
    return tag.rsplit("}", 1)[-1]


def parse_dependencies(nuspec: bytes) -> List[Dependency]:
    """Extract direct dependencies from a .nuspec document.

    Dependencies of all target frameworks are merged; a package listed
    several times is reported once, with its first version range.
    """
    try:
        root = ET.fromstring(nuspec)
    except ET.ParseError as error:
        raise RepositoryError(f"invalid nuspec file: {error}") from error
    found: Dict[str, str] = {}
    for element in root.iter():
        name = element.get("id")
        if local_name(element.tag) == "dependency" and name:
            found.setdefault(name, element.get("version", ""))
    return [Dependency(name, rng) for name, rng in found.items()]


class NugetSource:
    """Package source backed by a NuGet repository."""

    def __init__(self, repo_url: str) -> None:
        """Read the repository index once and remember the files address."""
        self._base = find_package_base(fetch(repo_url))

    def dependencies(self, package: str, version: str) -> List[Dependency]:
        """Return direct dependencies of the given package version."""
        url = build_nuspec_url(self._base, package, version)
        return parse_dependencies(fetch(url))


def get_direct_dependencies(
    repo_url: str, package: str, version: str
) -> List[Dependency]:
    """Return direct dependencies of the given package version."""
    return NugetSource(repo_url).dependencies(package, version)