#!/usr/local/autopkg/python
# pylint: disable=missing-function-docstring, unused-argument, arguments-differ
"""Test script for JamfPackageCleaner's exclude_packages_in_use option.

Exercises the real JamfPackageCleanerBase.execute() path with the network
seams (auth, API URL construction, package listing, usage lookups, and
deletion) stubbed out, so the package-selection logic can be validated
without a live Jamf Pro server.

Run with AutoPkg's Python:

    /usr/local/autopkg/python _tests/test_package_cleaner.py
"""

import os
import sys

# autopkglib lives in the AutoPkg install, and the base classes live alongside
# the processors. Add both to the path before importing.
sys.path.insert(0, "/Library/AutoPkg")
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "JamfUploaderProcessors",
        "JamfUploaderLib",
    ),
)

from autopkglib import ProcessorError  # pylint: disable=import-error
from JamfPackageCleanerBase import (  # pylint: disable=import-error, wrong-import-position
    JamfPackageCleanerBase,
)
from JamfUnusedPackageCleanerBase import (  # pylint: disable=import-error, wrong-import-position
    JamfUnusedPackageCleanerBase,
)
from JamfUploaderBase import (  # pylint: disable=import-error, wrong-import-position
    JamfUploaderBase,
)


def make_packages(names):
    """Build a fake Jamf package list (newest last so ids ascend by age)."""
    return [{"id": str(i + 1), "packageName": name} for i, name in enumerate(names)]


class StubCleaner(JamfPackageCleanerBase):
    """JamfPackageCleanerBase with every network call replaced by a stub."""

    def __init__(self, packages, packages_in_use):
        super().__init__()
        self._packages = packages
        self._packages_in_use = packages_in_use
        self.deleted = []
        self.usage_lookups = 0

    # --- stubbed network seams ------------------------------------------------

    def auth(self, *args, **kwargs):
        return ("token", "https://example.jamfcloud.com", "", "")

    def construct_api_url(self, *args, **kwargs):
        return "https://example.jamfcloud.com"

    def api_endpoints(self, *args, **kwargs):
        return "v1/packages"

    def paginated_get(self, *args, **kwargs):
        return list(self._packages)

    def get_packages_in_policies(self, *args, **kwargs):
        self.usage_lookups += 1
        return list(self._packages_in_use)

    def get_packages_in_patch_titles(self, *args, **kwargs):
        self.usage_lookups += 1
        return []

    def get_packages_in_prestages(self, *args, **kwargs):
        self.usage_lookups += 1
        return []

    def delete_package(
        self, api_url, object_id, token, max_tries, platform_level_id=""
    ):
        self.deleted.append(object_id)


def run_cleaner(
    packages, packages_in_use, exclude_in_use, versions_to_keep=2, dry_run=False
):
    """Run a stubbed clean and return its observable results."""
    proc = StubCleaner(packages, packages_in_use)
    proc.env = {
        "JSS_URL": "https://example.jamfcloud.com",
        "pkg_name_match": "Foo-",
        "versions_to_keep": str(versions_to_keep),
        "minimum_name_length": "3",
        "maximum_allowed_packages_to_delete": "20",
        "exclude_packages_in_use": exclude_in_use,
        "dry_run": dry_run,
        "max_tries": "5",
        "skip_if": False,
    }
    proc.execute()
    return (
        proc.deleted,
        proc.usage_lookups,
        proc.env.get("jamfpackagecleaner_summary_result", {}).get("data", {}),
        proc.env.get("packages_kept_in_use"),
    )


# Five versions, oldest -> newest. Sorted by id descending, the two newest
# (Foo-5, Foo-4) are always kept; Foo-3, Foo-2, Foo-1 are deletion candidates.
PACKAGES = make_packages(["Foo-1", "Foo-2", "Foo-3", "Foo-4", "Foo-5"])

print("Testing JamfPackageCleaner exclude_packages_in_use option")

# 1. Default behaviour (flag off): all candidates deleted, no usage lookup.
deleted, lookups, summary, kept_in_use = run_cleaner(
    PACKAGES, ["Foo-1"], exclude_in_use=False
)
assert len(deleted) == 3, f"expected 3 deleted, got {len(deleted)}"
assert lookups == 0, f"usage lookup ran with flag off ({lookups} calls)"
assert summary.get("deleted") == "3", summary
assert summary.get("kept_in_use") == "0", summary
assert kept_in_use == "0", kept_in_use
print("  default (flag off) deletes all candidates, no usage lookup: PASS")

# 2. Flag on, an old package is in use: it is spared, the rest are deleted.
deleted, lookups, summary, kept_in_use = run_cleaner(
    PACKAGES, ["Foo-1"], exclude_in_use=True
)
assert len(deleted) == 2, f"expected 2 deleted, got {len(deleted)}"
# Foo-1 has id "1" and must NOT be in the deleted list.
assert "1" not in deleted, f"in-use package was deleted: {deleted}"
assert summary.get("deleted") == "2", summary
assert summary.get("kept_in_use") == "1", summary
assert kept_in_use == "1", kept_in_use
print("  flag on spares an in-use package: PASS")

# 3. Flag on but nothing in use: every candidate is still deleted.
deleted, lookups, summary, kept_in_use = run_cleaner(
    PACKAGES, [], exclude_in_use=True
)
assert len(deleted) == 3, f"expected 3 deleted, got {len(deleted)}"
assert lookups == 3, f"expected 3 usage lookups, got {lookups}"
assert summary.get("kept_in_use") == "0", summary
assert kept_in_use == "0", kept_in_use
print("  flag on with no in-use packages deletes all candidates: PASS")

# 4. Performance guard: when nothing would be deleted, the usage lookup is
#    skipped entirely even with the flag on.
deleted, lookups, summary, kept_in_use = run_cleaner(
    PACKAGES, ["Foo-1"], exclude_in_use=True, versions_to_keep=10
)
assert len(deleted) == 0, f"expected 0 deleted, got {len(deleted)}"
assert lookups == 0, f"usage lookup ran with nothing to delete ({lookups} calls)"
assert kept_in_use == "0", kept_in_use
print("  performance guard skips usage lookup when nothing to delete: PASS")

_, _, _, kept_in_use = run_cleaner(
    PACKAGES, ["Foo-1"], exclude_in_use=True, dry_run=True
)
assert kept_in_use == "1", kept_in_use
print("  dry run exposes packages_kept_in_use output: PASS")


# 5. Usage getters must not crash on malformed/empty API objects. A single odd
#    object (a policy with no package_configuration, a patch title whose
#    versions come back null, a PreStage with no customPackageIds) must be
#    treated as "no packages", not abort the whole run. These exercise the real
#    getter bodies (not the StubCleaner overrides) against the shapes seen on
#    live servers.
class UsageGetterHarness(JamfUploaderBase):
    """Drives the real get_packages_in_* bodies with canned API responses."""

    def __init__(self, objects, value):
        super().__init__()
        self._objects = objects
        self._value = value

    def get_all_api_objects(self, *args, **kwargs):
        return self._objects

    def get_api_object_value_from_id(self, *args, **kwargs):
        return self._value

    def output(self, *args, **kwargs):
        pass


class FailingPatchTitleHarness(UsageGetterHarness):
    """Simulates an unavailable patch-title inventory endpoint."""

    def get_all_api_objects(self, *args, **kwargs):
        raise ProcessorError("patch titles unavailable")


# policy with no package_configuration -> [] (was KeyError)
assert (
    UsageGetterHarness([{"id": "1"}], {}).get_packages_in_policies("u", "t") == []
), "get_packages_in_policies crashed on a policy without package_configuration"
# a malformed package entry must not drop the well-formed entries beside it:
# [A, <no name>, B] must still yield both A and B, or B looks unused and is deleted
assert UsageGetterHarness(
    [{"id": "1"}],
    {"package_configuration": {"packages": [{"name": "A"}, {"id": 5}, {"name": "B"}]}},
).get_packages_in_policies("u", "t") == ["A", "B"], (
    "a malformed package entry dropped its well-formed siblings in the same policy"
)
# patch title whose versions come back null -> [] (was TypeError on len(None))
assert (
    UsageGetterHarness([{"id": "1"}], None).get_packages_in_patch_titles("u", "t")
    == []
), "get_packages_in_patch_titles crashed on null versions"
# patch title happy path: the package name is pulled out of versions[i].package.name
assert UsageGetterHarness(
    [{"id": "1"}], [{"package": {"name": "Foo-1"}}]
).get_packages_in_patch_titles("u", "t") == ["Foo-1"], (
    "get_packages_in_patch_titles did not extract the package name from versions"
)
# PreStage with a missing / null customPackageIds -> [] (was KeyError/TypeError)
assert (
    UsageGetterHarness([{"id": "1"}], None).get_packages_in_prestages("u", "t") == []
), "get_packages_in_prestages crashed on a PreStage without customPackageIds"
assert (
    UsageGetterHarness(
        [{"id": "1", "customPackageIds": None}], None
    ).get_packages_in_prestages("u", "t")
    == []
), "get_packages_in_prestages crashed on null customPackageIds"
# and the happy paths still return the package names
assert UsageGetterHarness(
    [{"id": "1"}], {"package_configuration": {"packages": [{"name": "Foo-1"}]}}
).get_packages_in_policies("u", "t") == ["Foo-1"]
assert UsageGetterHarness(
    [{"id": "1", "customPackageIds": ["10"]}], "Foo-1"
).get_packages_in_prestages("u", "t") == ["Foo-1"]
try:
    FailingPatchTitleHarness([], None).get_packages_in_patch_titles(
        "u", "t", fail_on_error=True
    )
except ProcessorError:
    pass
else:
    raise AssertionError("strict patch-title lookup did not stop deletion")
print("  usage getters tolerate malformed objects, keep happy path: PASS")


# 6. JamfUnusedPackageCleaner must call the shared usage getters with the
#    platform level identifier returned by authentication.
class StubUnusedCleaner(JamfUnusedPackageCleanerBase):
    """JamfUnusedPackageCleanerBase with network access replaced by canned data."""

    def __init__(self):
        super().__init__()
        self.platform_calls = []

    def auth(self, *args, **kwargs):
        return ("token", "https://example.jamfcloud.com", "", "environment")

    def construct_api_url(self, *args, **kwargs):
        return "https://example.jamfcloud.com"

    def get_all_api_objects(
        self, api_url, object_type, token, platform_level_id=""
    ):
        self.platform_calls.append((object_type, platform_level_id))
        if object_type == "package_v1":
            return [{"id": "1", "packageName": "Unused.pkg"}]
        return []

    def output(self, *args, **kwargs):
        pass


unused_cleaner = StubUnusedCleaner()
unused_cleaner.env = {
    "JSS_URL": "https://example.jamfcloud.com",
    "dry_run": True,
    "max_tries": "5",
    "skip_if": False,
}
unused_cleaner.execute()
assert unused_cleaner.env["jamfunusedpackagecleaner_summary_result"]["data"] == {
    "used_packages": "0",
    "unused_packages": "1",
    "deleted": "0",
}
assert unused_cleaner.platform_calls == [
    ("computer_prestage", "environment"),
    ("patch_software_title", "environment"),
    ("policy", "environment"),
    ("package_v1", "environment"),
]
print("  unused cleaner forwards the platform level identifier: PASS")

# 7. An early validation return must not leave a stale result in the environment.
early_return_cleaner = StubCleaner([], [])
early_return_cleaner.env = {
    "pkg_name_match": "F",
    "versions_to_keep": "2",
    "minimum_name_length": "3",
    "maximum_allowed_packages_to_delete": "20",
    "exclude_packages_in_use": False,
    "dry_run": False,
    "max_tries": "5",
    "skip_if": "TRUEPREDICATE",
    "packages_kept_in_use": "7",
    "jamfpackagecleaner_summary_result": {"stale": True},
    "dry_run_summary_result": {"stale": True},
}
early_return_cleaner.execute()
assert early_return_cleaner.env["packages_kept_in_use"] == "0"
assert "jamfpackagecleaner_summary_result" not in early_return_cleaner.env
assert "dry_run_summary_result" not in early_return_cleaner.env
print("  skipped run clears stale outputs: PASS")

print("\n=== All JamfPackageCleaner tests passed! ===")
