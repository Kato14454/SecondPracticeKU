"""Tests for validation of user parameters."""

import os
import tempfile
import unittest

from depgraph.config import (
    ConfigError,
    validate_max_depth,
    validate_output,
    validate_package,
    validate_repo,
    validate_version,
)

VALID_URL = "https://api.nuget.org/v3/index.json"


class ValidatePackageTest(unittest.TestCase):
    """Tests for validate_package."""

    def test_valid_name(self):
        name = "Newtonsoft.Json"
        self.assertEqual(validate_package(name), name)

    def test_empty_name(self):
        with self.assertRaises(ConfigError):
            validate_package("")

    def test_name_with_space(self):
        with self.assertRaises(ConfigError):
            validate_package("bad name")


class ValidateRepoTest(unittest.TestCase):
    """Tests for validate_repo."""

    def test_valid_url(self):
        self.assertEqual(validate_repo(VALID_URL, False), VALID_URL)

    def test_invalid_url(self):
        with self.assertRaises(ConfigError):
            validate_repo("not-a-url", False)

    def test_missing_test_file(self):
        with self.assertRaises(ConfigError):
            validate_repo("missing_file.txt", True)

    def test_existing_test_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "repo.txt")
            with open(path, "w", encoding="utf-8") as file:
                file.write("A: B\n")
            self.assertEqual(validate_repo(path, True), path)


class ValidateVersionTest(unittest.TestCase):
    """Tests for validate_version."""

    def test_valid_versions(self):
        for version in ("13.0.3", "1.0", "1.0.0-beta.1"):
            self.assertEqual(validate_version(version), version)

    def test_invalid_versions(self):
        for version in ("", "abc", "1", "1.x.0"):
            with self.assertRaises(ConfigError):
                validate_version(version)
    def test_missing_version_is_an_error(self):
        with self.assertRaises(ConfigError):
            validate_version(None)

    def test_missing_version_is_allowed_in_test_mode(self):
        self.assertEqual(validate_version(None, test_mode=True), "")


class ValidateOutputTest(unittest.TestCase):
    """Tests for validate_output."""

    def test_valid_output(self):
        self.assertEqual(validate_output("graph.svg"), "graph.svg")

    def test_wrong_extension(self):
        with self.assertRaises(ConfigError):
            validate_output("graph.png")

    def test_missing_directory(self):
        with self.assertRaises(ConfigError):
            validate_output("no_such_dir/graph.svg")


class ValidateMaxDepthTest(unittest.TestCase):
    """Tests for validate_max_depth."""

    def test_valid_depth(self):
        self.assertEqual(validate_max_depth(1), 1)

    def test_zero_depth(self):
        with self.assertRaises(ConfigError):
            validate_max_depth(0)

    def test_negative_depth(self):
        with self.assertRaises(ConfigError):
            validate_max_depth(-5)