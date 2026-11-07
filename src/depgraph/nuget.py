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
USER_AGENT = "depgraph/0.2"


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


def build_nuspec_url(base: str, package: str, version: str) -> str:
    """Build the address of the package description (.nuspec) file."""
    name = package.lower()
    return f"{base}{name}/{version.lower()}/{name}.nuspec"


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


def get_direct_dependencies(
        repo_url: str, package: str, version: str
) -> List[Dependency]:
    """Return direct dependencies of the given package version."""
    base = find_package_base(fetch(repo_url))
    nuspec = fetch(build_nuspec_url(base, package, version))
    return parse_dependencies(nuspec)
