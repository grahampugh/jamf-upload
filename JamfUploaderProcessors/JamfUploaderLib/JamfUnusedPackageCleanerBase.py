#!/usr/local/autopkg/python
# pylint: disable=invalid-name

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

import csv
import json
import os.path
import pathlib
import sys

from time import sleep
from urllib.parse import urlparse

from autopkglib import (  # pylint: disable=import-error
    ProcessorError,
)

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderBase import (  # pylint: disable=import-error,wrong-import-position
    JamfUploaderBase,
)


class Bcolors:
    """Colours for print outs"""

    OKGREEN = "\033[92m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"


class JamfUnusedPackageCleanerBase(JamfUploaderBase):
    """Class for functions used removing unused packages from Jamf Pro"""

    def get_packages_in_policies(self, jamf_url, token):
        """get a list of all packages in all policies"""

        # get all policies
        policies = self.get_all_api_objects(jamf_url, "policy", token)

        # get all package objects from policies and add to a list
        if policies:
            # define a new list
            packages_in_policies = []
            self.output(
                (
                    "Please wait while we gather a list of all packages in all policies "
                    f"(total {len(policies)})..."
                ),
                verbose_level=1,
            )
            for policy in policies:
                generic_info = self.get_api_obj_value_from_id(
                    jamf_url, "policy", policy["id"], "", token
                )
                try:
                    pkgs = generic_info["package_configuration"]["packages"]
                    for x in pkgs:
                        pkg = x["name"]
                        if pkg not in packages_in_policies:
                            packages_in_policies.append(pkg)
                except IndexError:
                    pass
            return packages_in_policies

    def get_packages_in_patch_titles(self, jamf_url, token):
        """get a list of all packages in all patch software titles"""

        # get all patch software titles
        titles = self.get_all_api_objects(jamf_url, "patch_software_title", token)

        # get all package objects from patch titles and add to a list
        if titles:
            # define a new list
            packages_in_titles = []
            self.output(
                (
                    "Please wait while we gather a list of all packages in all patch titles "
                    f"(total {len(titles)})..."
                ),
                verbose_level=1,
            )
            for title in titles:
                versions = self.get_api_obj_value_from_id(
                    jamf_url, "patch_software_title", title["id"], "versions", token
                )
                try:
                    if len(versions) > 0:
                        for i in range(  # pylint: disable=consider-using-enumerate
                            len(versions)
                        ):
                            try:
                                pkg = versions[i]["package"]["name"]
                                if pkg:
                                    if pkg != "None" and pkg not in packages_in_titles:
                                        packages_in_titles.append(pkg)
                            except IndexError:
                                pass
                            except KeyError:
                                pass
                except IndexError:
                    pass
            return packages_in_titles

    def get_packages_in_prestages(self, jamf_url, token):
        """get a list of all packages in all PreStage Enrollments"""

        # get all prestages
        prestages = self.get_all_api_objects(jamf_url, "computer_prestage", token)

        # get all package objects from prestages and add to a list
        if prestages:
            packages_in_prestages = []
            self.output(
                (
                    "Please wait while we gather a list of all packages in all "
                    f"PreStage Enrollments (total {len(prestages)})..."
                ),
                verbose_level=1,
            )
            for _, prestage in enumerate(prestages):
                pkg_ids = prestage["customPackageIds"]
                if len(pkg_ids) > 0:
                    for pkg_id in pkg_ids:
                        pkg = self.get_api_obj_value_from_id(
                            jamf_url, "package", pkg_id, "name", token
                        )
                        if pkg:
                            if pkg not in packages_in_prestages:
                                packages_in_prestages.append(pkg)
            return packages_in_prestages

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
                    self.output(f"Error: {e.filename} - {e.strerror}.")
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
        url = f"{jamf_url}/{self.api_endpoints(object_type)}/id/{obj_id}"

        count = 0
        while True:
            count += 1
            self.output(f"Package delete attempt {count}", verbose_level=2)
            request = "DELETE"
            r = self.curl(request=request, url=url, token=token)

            # check HTTP response
            if self.status_check(r, "Package", obj_id, request) == "break":
                break
            if count > 5:
                self.output(
                    "WARNING: Package deletion did not succeed after 5 attempts"
                )
                self.output(f"\nHTTP DELETE Response Code: {r.status_code}")
                raise ProcessorError("ERROR: Package deletion failed")
            sleep(30)
        return r

    def write_csv_file(self, file, fields, data):
        """dump some text to a file"""
        with open(file, "w", encoding="utf-8") as csvfile:
            # creating a csv dict writer object
            writer = csv.DictWriter(csvfile, fieldnames=fields)

            # writing headers (field names)
            writer.writeheader()

            # writing data rows
            writer.writerows(data)

    def send_slack_notification(
        self,
        jamf_url,
        slack_webhook_url,
        api_xml_object,
        chosen_api_obj_name,
        api_obj_action,
        status_code,
    ):
        """Send a Slack notification"""

        if not slack_webhook_url:
            self.output("No Slack webhook URL provided")
            return

        slack_text = (
            f"*API {api_xml_object} {api_obj_action} action*\n"
            f"URL: {jamf_url}\n"
            f"Object Name: *{chosen_api_obj_name}*\n"
            f"HTTP Response: {status_code}"
        )

        self.output(slack_text, verbose_level=2)

        slack_data = {
            "text": slack_text,
            "username": jamf_url,
        }
        slack_json = json.dumps(slack_data)

        count = 0
        while True:
            count += 1
            self.output(
                f"Slack webhook post attempt {count}",
                verbose_level=2,
            )
            r = self.curl(
                request="POST",
                url=slack_webhook_url,
                data=slack_json,
                endpoint_type="slack",
            )
            # check HTTP response
            if self.slack_status_check(r) == "break":
                break
            if count > 5:
                self.output("Slack webhook send did not succeed after 5 attempts")
                self.output(f"\nHTTP POST Response Code: {r.status_code}")
                raise ProcessorError("ERROR: Slack webhook failed to send")
            sleep(10)

    def slack_status_check(self, r):
        """Return a message dependent on the HTTP response"""
        if r.status_code == 200 or r.status_code == 201:
            self.output("Slack webhook sent successfully")
            return "break"
        else:
            self.output("WARNING: Slack webhook failed to send")
            self.output(r.output, verbose_level=2)

    def execute(self):
        """Clean up old packages in Jamf Pro"""

        # Get the necessary environment variables
        jamf_url = self.env.get("JSS_URL").rstrip("/")
        jamf_user = self.env.get("API_USERNAME")
        jamf_password = self.env.get("API_PASSWORD")
        client_id = self.env.get("CLIENT_ID")
        client_secret = self.env.get("CLIENT_SECRET")
        dry_run = self.to_bool(self.env.get("dry_run"))
        output_dir = self.env.get("output_dir")
        slack_webhook_url = self.env.get("slack_webhook_url")

        object_type = "package"

        # Create a list of smb shares in tuples
        smb_shares = []
        if self.env.get("SMB_URL"):
            if not self.env.get("SMB_USERNAME") or not self.env.get("SMB_PASSWORD"):
                raise ProcessorError("SMB_URL defined but no credentials supplied.")
            self.output(
                f"DP 1: {self.env.get('SMB_URL')}, {self.env.get('SMB_USERNAME')}, "
                f"pass len: {len(self.env.get('SMB_PASSWORD'))}",
                verbose_level=2,
            )
            smb_shares.append(
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
                        "DP {}: {}, {}, pass len: {}".format(  # pylint: disable=consider-using-f-string
                            n,
                            self.env.get(f"SMB{n}_URL"),
                            self.env.get(f"SMB{n}_USERNAME"),
                            len(self.env.get(f"SMB{n}_PASSWORD")),
                        ),
                        verbose_level=2,
                    )
                    smb_shares.append(
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
                smb_shares.append(
                    (
                        share["SMB_URL"],
                        share["SMB_USERNAME"],
                        share["SMB_PASSWORD"],
                    )
                )

        # Clear any pre-existing summary result
        if "jamfunusedpackagecleaner_summary_result" in self.env:
            del self.env["jamfunusedpackagecleaner_summary_result"]

        # Get all packages from Jamf Pro as JSON object
        self.output(f"Getting all packages from {jamf_url}")

        # get token using oauth or basic auth depending on the credentials given
        if jamf_url:
            token = self.handle_api_auth(
                jamf_url,
                jamf_user=jamf_user,
                password=jamf_password,
                client_id=client_id,
                client_secret=client_secret,
            )
        else:
            raise ProcessorError("ERROR: Jamf Pro URL not supplied")

        # create empty dictionaries to hold used and unused packages
        unused_packages = {}
        used_packages = {}

        # get a list of packages in prestage enrollments
        packages_in_prestages = self.get_packages_in_prestages(jamf_url, token)
        # get a list of packages in patch software titles
        packages_in_titles = self.get_packages_in_patch_titles(jamf_url, token)
        # get a list of packages in policies
        packages_in_policies = self.get_packages_in_policies(jamf_url, token)

        # get a list of all packages in Jamf Pro
        packages = self.get_all_api_objects(jamf_url, "package", token)
        if packages:
            csv_fields = ["pkg_id", "pkg_name", "used"]
            csv_data = []

            for package in packages:
                # loop all the packages
                # see if the package is in any policies
                unused_in_policies = 0
                unused_in_titles = 0
                unused_in_prestages = 0
                if packages_in_policies:
                    if package["name"] not in packages_in_policies:
                        unused_in_policies = 1
                else:
                    unused_in_policies = 1
                if packages_in_titles:
                    if package["name"] not in packages_in_titles:
                        unused_in_titles = 1
                else:
                    unused_in_titles = 1
                if packages_in_prestages:
                    if package["name"] not in packages_in_prestages:
                        unused_in_prestages = 1
                else:
                    unused_in_prestages = 1
                if (
                    unused_in_policies == 1
                    and unused_in_titles == 1
                    and unused_in_prestages == 1
                ):
                    unused_packages[package["id"]] = package["name"]
                    csv_data.append(
                        {
                            "pkg_id": package["id"],
                            "pkg_name": package["name"],
                            "used": "false",
                        }
                    )
                elif package["name"] not in used_packages:
                    used_packages[package["id"]] = package["name"]
                    csv_data.append(
                        {
                            "pkg_id": package["id"],
                            "pkg_name": package["name"],
                            "used": "true",
                        }
                    )

            # create more specific output filename
            if output_dir:
                # get instance name from URL
                host = jamf_url.partition("://")[2]
                subdomain = host.partition(".")[0]
                output_filename = (
                    f"{subdomain}-{self.object_list_types(object_type)}.csv"
                )
                csv_write = os.path.join(
                    output_dir, "Packages", "Unused", output_filename
                )
                pathlib.Path(os.path.dirname(csv_write)).mkdir(
                    parents=True, exist_ok=True
                )
                self.write_csv_file(csv_write, csv_fields, csv_data)
                self.output(f"CSV file written to {csv_write}")

            # print the list of used packages
            self.output(
                (
                    "The following packages are found in at least one "
                    "policy, PreStage Enrollment, and/or patch title:"
                ),
                verbose_level=1,
            )
            for pkg_name in used_packages.values():
                self.output(
                    f"  {Bcolors.OKGREEN}{pkg_name}{Bcolors.ENDC}", verbose_level=1
                )

            # print the list of unused packages
            self.output(
                (
                    "The following packages are not used in any policies, "
                    "PreStage Enrollments, or patch titles:"
                ),
                verbose_level=1,
            )
            for pkg_name in unused_packages.values():
                self.output(
                    f"  {Bcolors.FAIL}{pkg_name}{Bcolors.ENDC}", verbose_level=1
                )

            deleted_count = 0
            if dry_run:
                self.output(
                    "Dry run mode enabled. No packages will be deleted.",
                    verbose_level=1,
                )
            else:
                # delete the packages
                for pkg_id, pkg_name in unused_packages.items():
                    self.output(f"Deleting {pkg_name}...")
                    status_code = self.delete_object(jamf_url, "package", pkg_id, token)
                    # Process for SMB shares if defined
                    if len(smb_shares) > 0:
                        self.output(
                            "Number of File Share DPs: " + str(len(smb_shares)),
                            verbose_level=2,
                        )
                    for smb_share in smb_shares:
                        smb_url, smb_user, smb_password = (
                            smb_share[0],
                            smb_share[1],
                            smb_share[2],
                        )
                        self.output(
                            f"Begin deleting from File Share DP {smb_url}",
                            verbose_level=1,
                        )
                        if "smb://" in smb_url:
                            # mount the share
                            self.mount_smb(smb_url, smb_user, smb_password)
                        # delete existing package from the local folder
                        self.delete_local_pkg(smb_url, pkg_name)
                        if "smb://" in smb_url:
                            # unmount the share
                            self.umount_smb(smb_url)

                    if status_code == 200:
                        self.output(
                            f"Package {pkg_name} deleted successfully",
                            verbose_level=1,
                        )
                        deleted_count += 1

                    # Send a Slack notification
                    self.send_slack_notification(
                        jamf_url,
                        slack_webhook_url,
                        "package",
                        pkg_name,
                        "delete",
                        status_code,
                    )

        # Save a summary of the package cleaning in the environment
        self.env["jamfunusedpackagecleaner_summary_result"] = {
            "summary_text": "The following package cleaning was performed in Jamf Pro:",
            "report_fields": [
                "used_packages",
                "unused_packages",
                "deleted",
            ],
            "data": {
                "used_packages": str(len(used_packages)),
                "unused_packages": str(len(unused_packages)),
                "deleted": str(deleted_count),
            },
        }
