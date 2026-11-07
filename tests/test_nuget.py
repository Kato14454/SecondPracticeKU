"""Tests for NuGet repository access (no network required)."""

import json
import unittest
from unittest import mock

from depgraph import nuget
from depgraph.nuget import Dependency, RepositoryError

NUSPEC_GROUPS = b"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd">
  <metadata>
    <id>Demo</id>
    <dependencies>
      <group targetFramework=".NETStandard2.0">
        <dependency id="Alpha" version="1.2.3" />
        <dependency id="Beta" version="[2.0.0, )" />
      </group>
      <group targetFramework="net6.0">
        <dependency id="Alpha" version="1.2.3" />
        <dependency id="Gamma" version="4.0.0" />
      </group>
    </dependencies>
  </metadata>
</package>
"""

NUSPEC_FLAT = b"""<package><metadata><dependencies>
  <dependency id="Alpha" version="1.0.0" />
</dependencies></metadata></package>
"""

NUSPEC_EMPTY = b"<package><metadata><id>Demo</id></metadata></package>"

BASE = "https://example.org/flat/"
INDEX = json.dumps(
    {
        "resources": [
            {"@id": "https://example.org/search", "@type": "SearchQuery"},
            {"@id": BASE, "@type": "PackageBaseAddress/3.0.0"},
        ]
    }
).encode()


class ParseDependenciesTest(unittest.TestCase):
    """Tests for parse_dependencies."""

    def test_groups_are_merged_without_duplicates(self):
        result = nuget.parse_dependencies(NUSPEC_GROUPS)
        names = [dependency.name for dependency in result]
        self.assertEqual(names, ["Alpha", "Beta", "Gamma"])

    def test_version_range_is_kept(self):
        result = nuget.parse_dependencies(NUSPEC_GROUPS)
        self.assertEqual(result[1], Dependency("Beta", "[2.0.0, )"))

    def test_dependencies_without_groups(self):
        result = nuget.parse_dependencies(NUSPEC_FLAT)
        self.assertEqual(result, [Dependency("Alpha", "1.0.0")])

    def test_no_dependencies(self):
        self.assertEqual(nuget.parse_dependencies(NUSPEC_EMPTY), [])

    def test_broken_xml(self):
        with self.assertRaises(RepositoryError):
            nuget.parse_dependencies(b"<package>")


class FindPackageBaseTest(unittest.TestCase):
    """Tests for find_package_base."""

    def test_base_address_is_found(self):
        self.assertEqual(nuget.find_package_base(INDEX), BASE)

    def test_missing_resource(self):
        with self.assertRaises(RepositoryError):
            nuget.find_package_base(b'{"resources": []}')

    def test_broken_json(self):
        with self.assertRaises(RepositoryError):
            nuget.find_package_base(b"not json")


class BuildNuspecUrlTest(unittest.TestCase):
    """Tests for build_nuspec_url."""

    def test_name_and_version_are_lowercase(self):
        url = nuget.build_nuspec_url(BASE, "Newtonsoft.Json", "13.0.3-Beta")
        expected = f"{BASE}newtonsoft.json/13.0.3-beta/newtonsoft.json.nuspec"
        self.assertEqual(url, expected)


class GetDirectDependenciesTest(unittest.TestCase):
    """Tests for get_direct_dependencies."""

    def test_requests_index_then_nuspec(self):
        with mock.patch.object(nuget, "fetch") as fake_fetch:
            fake_fetch.side_effect = [INDEX, NUSPEC_FLAT]
            result = nuget.get_direct_dependencies(
                "https://example.org/index.json", "Demo", "1.0.0"
            )
        self.assertEqual(result, [Dependency("Alpha", "1.0.0")])
        urls = [call.args[0] for call in fake_fetch.call_args_list]
        self.assertEqual(
            urls,
            [
                "https://example.org/index.json",
                f"{BASE}demo/1.0.0/demo.nuspec",
            ],
        )