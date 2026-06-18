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

from JamfPackageCleanerBase import (  # pylint: disable=import-error, wrong-import-position
    JamfPackageCleanerBase,
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

    def delete_package(self, api_url, object_id, token, max_tries, tenant_id=""):
        self.deleted.append(object_id)


def run_cleaner(packages, packages_in_use, exclude_in_use, versions_to_keep=2):
    """Run a stubbed clean and return (deleted_ids, usage_lookups, summary)."""
    proc = StubCleaner(packages, packages_in_use)
    proc.env = {
        "JSS_URL": "https://example.jamfcloud.com",
        "pkg_name_match": "Foo-",
        "versions_to_keep": str(versions_to_keep),
        "minimum_name_length": "3",
        "maximum_allowed_packages_to_delete": "20",
        "exclude_packages_in_use": exclude_in_use,
        "dry_run": False,
        "max_tries": "5",
        "skip_if": False,
    }
    proc.execute()
    return (
        proc.deleted,
        proc.usage_lookups,
        proc.env.get("jamfpackagecleaner_summary_result", {}).get("data", {}),
    )


# Five versions, oldest -> newest. Sorted by id descending, the two newest
# (Foo-5, Foo-4) are always kept; Foo-3, Foo-2, Foo-1 are deletion candidates.
PACKAGES = make_packages(["Foo-1", "Foo-2", "Foo-3", "Foo-4", "Foo-5"])

print("Testing JamfPackageCleaner exclude_packages_in_use option")

# 1. Default behaviour (flag off): all candidates deleted, no usage lookup.
deleted, lookups, summary = run_cleaner(PACKAGES, ["Foo-1"], exclude_in_use=False)
assert len(deleted) == 3, f"expected 3 deleted, got {len(deleted)}"
assert lookups == 0, f"usage lookup ran with flag off ({lookups} calls)"
assert summary.get("deleted") == "3", summary
assert summary.get("kept_in_use") == "0", summary
print("  default (flag off) deletes all candidates, no usage lookup: PASS")

# 2. Flag on, an old package is in use: it is spared, the rest are deleted.
deleted, lookups, summary = run_cleaner(PACKAGES, ["Foo-1"], exclude_in_use=True)
assert len(deleted) == 2, f"expected 2 deleted, got {len(deleted)}"
# Foo-1 has id "1" and must NOT be in the deleted list.
assert "1" not in deleted, f"in-use package was deleted: {deleted}"
assert summary.get("deleted") == "2", summary
assert summary.get("kept_in_use") == "1", summary
print("  flag on spares an in-use package: PASS")

# 3. Flag on but nothing in use: every candidate is still deleted.
deleted, lookups, summary = run_cleaner(PACKAGES, [], exclude_in_use=True)
assert len(deleted) == 3, f"expected 3 deleted, got {len(deleted)}"
assert lookups == 3, f"expected 3 usage lookups, got {lookups}"
assert summary.get("kept_in_use") == "0", summary
print("  flag on with no in-use packages deletes all candidates: PASS")

# 4. Performance guard: when nothing would be deleted, the usage lookup is
#    skipped entirely even with the flag on.
deleted, lookups, summary = run_cleaner(
    PACKAGES, ["Foo-1"], exclude_in_use=True, versions_to_keep=10
)
assert len(deleted) == 0, f"expected 0 deleted, got {len(deleted)}"
assert lookups == 0, f"usage lookup ran with nothing to delete ({lookups} calls)"
print("  performance guard skips usage lookup when nothing to delete: PASS")

print("\n=== All JamfPackageCleaner tests passed! ===")
