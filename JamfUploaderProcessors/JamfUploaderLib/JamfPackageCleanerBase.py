#!/usr/local/autopkg/python

"""
Copyright 2023 Graham Pugh

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import json
import os.path
import sys

from time import sleep
from urllib.parse import urlparse

from autopkglib import (
    ProcessorError,
)  # pylint: disable=import-error

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderBase import JamfUploaderBase  # noqa: E402


class JamfPackageCleanerBase(JamfUploaderBase):
    """Class for functions used removing old packages from Jamf Pro"""

    def delete_local_pkg(self, mount_share, pkg_name):
        """Delete existing package from local DP or mounted share"""
        dirname = f"/Volumes{urlparse(mount_share).path}"
        if os.path.isdir(dirname):
            existing_pkg_path = os.path.join(dirname, "Packages", pkg_name)
            if os.path.isfile(existing_pkg_path):
                self.output(f"Deleting existing package: {existing_pkg_path}")
                try:
                    os.remove(existing_pkg_path)
                except OSError as e:
                    # If it fails, inform the user.
                    print(f"Error: {e.filename} - {e.strerror}.")
            else:
                self.output("No existing package found")
                self.output(
                    f"Expected path: {existing_pkg_path}",
                    verbose_level=2,
                )
        else:
            self.output(
                f"Expected path not found!: {dirname}",
                verbose_level=2,
            )

    def delete_package(self, jamf_url, obj_id, token):
        """Cleaning Packages"""

        self.output("Deleting package...")

        object_type = "package"
        url = "{}/{}/id/{}".format(jamf_url, self.api_endpoints(object_type), obj_id)

        count = 0
        while True:
            count += 1
            self.output("Package delete attempt {}".format(count), verbose_level=2)
            request = "DELETE"
            r = self.curl(request=request, url=url, token=token)

            # check HTTP response
            if self.status_check(r, "Package", obj_id, request) == "break":
                break
            if count > 5:
                self.output(
                    "WARNING: Package deletion did not succeed after 5 attempts"
                )
                self.output("\nHTTP DELETE Response Code: {}".format(r.status_code))
                raise ProcessorError("ERROR: Package deletion failed ")
            sleep(30)
        return r

    def execute(self):
        """Clean up old packages in Jamf Pro"""

        # Get the necessary environment variables
        self.jamf_url = self.env.get("JSS_URL")
        self.jamf_user = self.env.get("API_USERNAME")
        self.jamf_password = self.env.get("API_PASSWORD")
        self.client_id = self.env.get("CLIENT_ID")
        self.client_secret = self.env.get("CLIENT_SECRET")
        self.pkg_name_match = (
            self.env.get("pkg_name_match") or f"{self.env.get('NAME')}-"
        )
        self.versions_to_keep = int(self.env.get("versions_to_keep"))
        self.minimum_name_length = int(self.env.get("minimum_name_length"))
        self.maximum_allowed_packages_to_delete = int(
            self.env.get("maximum_allowed_packages_to_delete")
        )
        self.dry_run = self.env.get("dry_run")

        # Create a list of smb shares in tuples
        self.smb_shares = []
        if self.env.get("SMB_URL"):
            if not self.env.get("SMB_USERNAME") or not self.env.get("SMB_PASSWORD"):
                raise ProcessorError("SMB_URL defined but no credentials supplied.")
            self.output(
                "DP 1: {}, {}, pass len: {}".format(
                    self.env.get("SMB_URL"),
                    self.env.get("SMB_USERNAME"),
                    len(self.env.get("SMB_PASSWORD")),
                ),
                verbose_level=2,
            )
            self.smb_shares.append(
                (
                    self.env.get("SMB_URL"),
                    self.env.get("SMB_USERNAME"),
                    self.env.get("SMB_PASSWORD"),
                )
            )
            n = 2
            while n > 0:
                if self.env.get(f"SMB{n}_URL"):
                    if not self.env.get(f"SMB{n}_USERNAME") or not self.env.get(
                        f"SMB{n}_PASSWORD"
                    ):
                        raise ProcessorError(
                            f"SMB{n}_URL defined but no credentials supplied."
                        )
                    self.output(
                        "DP {}: {}, {}, pass len: {}".format(
                            n,
                            self.env.get(f"SMB{n}_URL"),
                            self.env.get(f"SMB{n}_USERNAME"),
                            len(self.env.get(f"SMB{n}_PASSWORD")),
                        ),
                        verbose_level=2,
                    )
                    self.smb_shares.append(
                        (
                            self.env.get(f"SMB{n}_URL"),
                            self.env.get(f"SMB{n}_USERNAME"),
                            self.env.get(f"SMB{n}_PASSWORD"),
                        )
                    )
                    n = n + 1
                else:
                    self.output(f"DP {n}: not defined", verbose_level=3)
                    n = 0
        elif self.env.get("SMB_SHARES"):
            smb_share_array = self.env.get("SMB_SHARES")
            for share in smb_share_array:
                if (
                    not share["SMB_URL"]
                    or not share["SMB_USERNAME"]
                    or not share["SMB_PASSWORD"]
                ):
                    raise ProcessorError("Incorrect SMB credentials supplied.")
                self.smb_shares.append(
                    (
                        share["SMB_URL"],
                        share["SMB_USERNAME"],
                        share["SMB_PASSWORD"],
                    )
                )

        # Clear any pre-existing summary result
        if "jamfpackagecleaner_summary_result" in self.env:
            del self.env["jamfpackagecleaner_summary_result"]

        # Abort if the package name match string is too short
        if len(self.pkg_name_match) < self.minimum_name_length:
            self.output(
                f"'pkg_name_match' argument ({self.pkg_name_match}) needs at least "
                f"{self.minimum_name_length} characters. "
                "Override by changing the 'minimum_name_length' argument. Aborting."
            )
            return

        # Get all packages from Jamf Pro as JSON object
        self.output(f"Getting all packages from {self.jamf_url}")

        # get token using oauth or basic auth depending on the credentials given
        if self.jamf_url and self.client_id and self.client_secret:
            token = self.handle_oauth(self.jamf_url, self.client_id, self.client_secret)
        elif self.jamf_url and self.jamf_user and self.jamf_password:
            token = self.handle_api_auth(
                self.jamf_url, self.jamf_user, self.jamf_password
            )
        else:
            raise ProcessorError("ERROR: Credentials not supplied")

        # check for existing
        obj_type = "package"
        url = f"{self.jamf_url}/{self.api_endpoints(obj_type)}"
        r = self.curl(request="GET", url=url, token=token)
        jamf_packages = json.loads(r.output.decode("utf-8"))["packages"]

        # Find packages that match the name pattern
        found_packages = [
            item
            for item in jamf_packages
            if item["name"].startswith(self.pkg_name_match)
        ]
        found_packages = sorted(
            found_packages, key=lambda item: item["id"], reverse=True
        )

        # If there are not enough versions to delete, log it will skip the deletion step
        if len(found_packages) <= self.versions_to_keep:
            self.output(
                f"No need to delete any packages. Only {len(found_packages)} found. "
                f"Keeping up to {self.versions_to_keep} versions"
            )

        # Divide the packages into those to keep and those to delete
        packages_to_keep = found_packages[: self.versions_to_keep]
        packages_to_delete = found_packages[self.versions_to_keep :]  # noqa: E203

        # Check that we're not going to delete too many packages
        if len(packages_to_delete) > self.maximum_allowed_packages_to_delete:
            self.output(
                f"Too many matches. Found {len(packages_to_delete)} to delete. "
                f"Maximum allowed is {self.maximum_allowed_packages_to_delete}. "
                "Override by setting the 'maximum_allowed_packages_to_delete' argument. Aborting."
            )
            return

        #  Print the packages to keep and delete
        self.output(
            f"Found {len(packages_to_keep)} packages to keep "
            f"and {len(packages_to_delete)} to delete",
            verbose_level=1,
        )

        for package in packages_to_keep:
            self.output(f"✅ {package['name']}", verbose_level=2)

        for package in packages_to_delete:
            self.output(f"❌ {package['name']} (will be deleted)", verbose_level=2)

        # If performing a dry_run, print intentions and abort.
        if self.dry_run:
            self.output(
                "INFO: Argument 'dry_run' is set to True. Nothing will be deleted. "
                "Use '-vv' to see detailed information. "
                "Aborting."
            )
            return

        for package in packages_to_delete:
            # package deletion could take time, so we check the token before each deletion
            token = self.handle_api_auth(
                self.jamf_url, self.jamf_user, self.jamf_password
            )
            self.delete_package(
                jamf_url=self.jamf_url, obj_id=package["id"], token=token
            )
            self.output(f"Deleting {package['name']}", verbose_level=2)

            # Process for SMB shares if defined
            if len(self.smb_shares) > 0:
                self.output(
                    "Number of File Share DPs: " + str(len(self.smb_shares)),
                    verbose_level=2,
                )
                pkg_name = package["name"]
            for smb_share in self.smb_shares:
                smb_url, smb_user, smb_password = (
                    smb_share[0],
                    smb_share[1],
                    smb_share[2],
                )
                self.output(
                    f"Begin deleting from File Share DP {smb_url}", verbose_level=1
                )
                if "smb://" in smb_url:
                    # mount the share
                    self.mount_smb(smb_url, smb_user, smb_password)
                # delete existing package from the local folder
                self.delete_local_pkg(smb_url, pkg_name)
                if "smb://" in smb_url:
                    # unmount the share
                    self.umount_smb(smb_url)

        # Save a summary of the package cleaning in the environment
        self.env["jamfpackagecleaner_summary_result"] = {
            "summary_text": "The following package cleaning was performed in Jamf Pro:",
            "report_fields": [
                "pkg_name_match",
                "found_matches",
                "versions_to_keep",
                "deleted",
            ],
            "data": {
                "pkg_name_match": self.pkg_name_match,
                "found_matches": str(len(found_packages)),
                "versions_to_keep": str(self.versions_to_keep),
                "deleted": str(len(packages_to_delete)),
            },
        }
