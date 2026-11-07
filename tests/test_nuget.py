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


class NormalizeVersionTest(unittest.TestCase):
    """Tests for normalize_version."""

    def test_missing_parts_are_filled(self):
        self.assertEqual(nuget.normalize_version("1.0"), "1.0.0")
        self.assertEqual(nuget.normalize_version("2"), "2.0.0")

    def test_zero_fourth_part_is_dropped(self):
        self.assertEqual(nuget.normalize_version("1.2.3.0"), "1.2.3")

    def test_nonzero_fourth_part_is_kept(self):
        self.assertEqual(nuget.normalize_version("1.2.3.4"), "1.2.3.4")

    def test_leading_zeros_are_removed(self):
        self.assertEqual(nuget.normalize_version("01.02.003"), "1.2.3")

    def test_prerelease_is_lowercase_and_metadata_removed(self):
        version = nuget.normalize_version("1.0.0-Beta.1+Build5")
        self.assertEqual(version, "1.0.0-beta.1")


class ResolveVersionTest(unittest.TestCase):
    """Tests for resolve_version."""

    def test_plain_version(self):
        self.assertEqual(nuget.resolve_version("4.3.0"), "4.3.0")

    def test_minimum_version(self):
        self.assertEqual(nuget.resolve_version("[2.0.0, )"), "2.0.0")

    def test_range_uses_lower_bound(self):
        self.assertEqual(nuget.resolve_version("[1.0, 2.0)"), "1.0")

    def test_only_upper_bound(self):
        self.assertEqual(nuget.resolve_version("(, 2.0]"), "2.0")

    def test_empty_range(self):
        self.assertEqual(nuget.resolve_version(""), "")


class NugetSourceTest(unittest.TestCase):
    """Tests for NugetSource."""

    def test_index_is_read_once(self):
        with mock.patch.object(nuget, "fetch") as fake_fetch:
            fake_fetch.side_effect = [INDEX, NUSPEC_FLAT, NUSPEC_EMPTY]
            source = nuget.NugetSource("https://example.org/index.json")
            first = source.dependencies("Demo", "1.0")
            second = source.dependencies("Other", "2.0.0")
        self.assertEqual(first, [Dependency("Alpha", "1.0.0")])
        self.assertEqual(second, [])
        urls = [call.args[0] for call in fake_fetch.call_args_list]
        self.assertEqual(urls[1], f"{BASE}demo/1.0.0/demo.nuspec")
        self.assertEqual(urls[2], f"{BASE}other/2.0.0/other.nuspec")


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
