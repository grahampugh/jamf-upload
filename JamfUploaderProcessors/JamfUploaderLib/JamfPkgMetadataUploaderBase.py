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

NOTES:
Requirements for uploading to the AWS S3 API endpoint:
- boto3

To resolve the dependencies, run: /usr/local/autopkg/python -m pip install boto3
"""

import json
import os.path
import sys

from time import sleep
from urllib.parse import quote

from autopkglib import ProcessorError, APLooseVersion  # pylint: disable=import-error

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderBase import (  # pylint: disable=import-error, wrong-import-position # noqa: E402
    JamfUploaderBase,
)


class JamfPkgMetadataUploaderBase(JamfUploaderBase):
    """Class for functions used to upload package metadata without a package to Jamf"""

    def check_pkg(self, pkg_name, api_url, token, tenant_id=""):
        """check if a package with the same name exists in the repo
        note that it is possible to have more than one with the same name
        which could mess things up"""

        object_type = "package_v1"
        filter_name = "packageName"
        object_id = self.get_api_object_id_from_name(
            api_url,
            object_type=object_type,
            object_name=pkg_name,
            token=token,
            filter_name=filter_name,
            tenant_id=tenant_id,
        )

        if object_id:
            return str(object_id)
        else:
            return "-1"

    def get_category_id(self, api_url, category_name, token="", tenant_id=""):
        """Get the category ID from the name, or abort if ID not found"""
        # check for existing category
        self.output(f"Checking for '{category_name}' on {api_url}")
        object_id = self.get_api_object_id_from_name(
            api_url,
            object_type="category",
            object_name=category_name,
            token=token,
            tenant_id=tenant_id,
        )

        if object_id:
            self.output(f"Category '{category_name}' exists: ID {object_id}")
            return object_id
        else:
            self.output(f"Category '{category_name}' not found")
            raise ProcessorError("Supplied package category does not exist")

    def update_pkg_metadata(  # pylint: disable=too-many-arguments, too-many-locals
        self,
        api_url,
        pkg_name,
        pkg_display_name,
        pkg_metadata,
        sleep_time,
        token,
        max_tries,
        pkg_id=0,
        tenant_id="",
    ):
        """Update package metadata using v1/packages endpoint."""

        # get category ID
        if pkg_metadata["category"]:
            category_id = self.get_category_id(
                api_url, pkg_metadata["category"], token, tenant_id=tenant_id
            )
        else:
            category_id = "-1"

        # build the package record JSON
        pkg_data = {
            "packageName": pkg_display_name,
            "fileName": pkg_name,
            "info": pkg_metadata["info"],
            "notes": pkg_metadata["notes"],
            "categoryId": category_id,
            "priority": pkg_metadata["priority"],
            "fillUserTemplate": 0,
            "uninstall": 0,
            "rebootRequired": pkg_metadata["reboot_required"],
            "osInstall": 0,
            "osRequirements": pkg_metadata["os_requirements"],
            "suppressUpdates": 0,
            "suppressFromDock": 0,
            "suppressEula": 0,
            "suppressRegistration": 0,
        }

        self.output(
            "Package metadata:",
            verbose_level=2,
        )
        self.output(
            pkg_data,
            verbose_level=2,
        )

        pkg_json = self.write_json_file(api_url, pkg_data)

        # if we find a pkg ID we put, if not, we post
        object_type = "package_v1"
        endpoint = self.api_endpoints(object_type, tenant_id=tenant_id)
        if int(pkg_id) > 0:
            url = f"{api_url}/{endpoint}/{pkg_id}"
        else:
            url = f"{api_url}/{endpoint}"

        count = 0
        while True:
            count += 1
            self.output(
                f"Package metadata upload attempt {count}",
                verbose_level=2,
            )
            request = "PUT" if pkg_id else "POST"
            r = self.curl(
                api_type="jpapi", request=request, url=url, token=token, data=pkg_json
            )
            # check HTTP response
            if self.status_check(r, "Package Metadata", pkg_name, request) == "break":
                break
            if count >= max_tries:
                self.output(
                    f"Package metadata upload did not succeed after {max_tries} attempts"
                )
                self.output(f"\nHTTP POST Response Code: {r.status_code}")
                raise ProcessorError("ERROR: Package metadata upload failed ")
            if int(sleep_time) > 10:
                sleep(int(sleep_time))
            else:
                sleep(10)
        if r.status_code == 201:
            obj = json.loads(json.dumps(r.output))
            self.output(
                obj,
                verbose_level=4,
            )

            try:
                object_id = obj["id"]
            except KeyError:
                object_id = "-1"
        else:
            object_id = "-1"
        return object_id

    # main function
    def execute(
        self,
    ):  # pylint: disable=too-many-branches, too-many-locals, too-many-statements
        """Perform the metadata upload"""

        jamf_url = (self.env.get("JSS_URL") or "").rstrip("/")
        jamf_user = self.env.get("API_USERNAME")
        jamf_password = self.env.get("API_PASSWORD")
        jamf_platform_gw_region = self.env.get("PLATFORM_API_REGION")
        jamf_platform_gw_tenant_id = self.env.get("PLATFORM_API_TENANT_ID")
        client_id = self.env.get("CLIENT_ID")
        client_secret = self.env.get("CLIENT_SECRET")
        bearer_token = self.env.get("BEARER_TOKEN")
        jamf_cli_profile = self.env.get("JAMF_CLI_PROFILE")
        pkg_name = self.env.get("pkg_name")
        pkg_display_name = self.env.get("pkg_display_name")
        pkg_category = self.env.get("pkg_category")
        pkg_info = self.env.get("pkg_info")
        notes = self.env.get("pkg_notes")
        priority = self.env.get("pkg_priority")
        os_requirements = self.env.get("os_requirements")
        required_processor = self.env.get("required_processor")
        reboot_required = self.to_bool(self.env.get("reboot_required"))
        send_notification = self.to_bool(self.env.get("send_notification"))
        sleep_time = self.env.get("sleep")
        max_tries = self.env.get("max_tries")
        skip_and_proceed = self.to_bool(self.env.get("skip_and_proceed"))

        # verify that max_tries is an integer greater than zero and less than 10
        try:
            max_tries = int(max_tries)
            if max_tries < 1 or max_tries > 10:
                raise ValueError
        except (ValueError, TypeError):
            max_tries = 5

        pkg_metadata_updated = False

        # allow passing a pkg path to extract the name
        if "/" in pkg_name:
            pkg_name = os.path.basename(pkg_name)

        pkg_metadata = {
            "category": pkg_category,
            "info": pkg_info,
            "notes": notes,
            "reboot_required": reboot_required,
            "priority": priority,
            "os_requirements": os_requirements,
            "required_processor": required_processor,
            "send_notification": send_notification,
        }

        # we need to ensure that a zipped package's display name matches the new pkg_name for
        # comparison with an existing package
        if not pkg_display_name:
            pkg_display_name = pkg_name

        # clear any pre-existing summary result
        if "jamfpkgmetadatauploader_summary_result" in self.env:
            del self.env["jamfpkgmetadatauploader_summary_result"]

        process_skipped = False

        # skip the process if skip_and_proceed is True
        if skip_and_proceed:
            self.output(
                "Skipping pkg metadata to next process as skip_and_proceed is set to True"
            )
            process_skipped = True
            self.env["process_skipped"] = process_skipped
            return

        # now start the process of uploading the package
        self.output(f"Checking for existing metadata '{pkg_name}' on {jamf_url}")

        # get a token
        token, jamf_url, jamf_platform_gw_region, jamf_platform_gw_tenant_id = self.auth(
            jamf_url=jamf_url,
            jamf_user=jamf_user,
            password=jamf_password,
            region=jamf_platform_gw_region,
            tenant_id=jamf_platform_gw_tenant_id,
            client_id=client_id,
            client_secret=client_secret,
            token=bearer_token,
            jamf_cli_profile=jamf_cli_profile,
        )

        # construct the api_url based on the API type
        api_url = self.construct_api_url(
            jamf_url=jamf_url, region=jamf_platform_gw_region
        )
        self.output(f"API URL is {api_url}", verbose_level=3)

        jamf_pro_version = self.get_jamf_pro_version(api_url, token, tenant_id=jamf_platform_gw_tenant_id)

        if APLooseVersion(jamf_pro_version) < APLooseVersion("11.4"):
            raise ProcessorError(
                "this processor uses the new packages endpoint so only works on 11.4+"
            )

        # check for existing pkg
        object_id = self.check_pkg(pkg_name, api_url, token=token, tenant_id=jamf_platform_gw_tenant_id)
        self.output(f"ID: {object_id}", verbose_level=3)  # TEMP
        if object_id != "-1":
            self.output(f"Package '{pkg_name}' already exists: ID {object_id}")
            pkg_id = object_id  # assign pkg_id for smb runs - JCDS runs get it from the pkg upload
        else:
            self.output(f"Package '{pkg_name}' not found on server")
            pkg_id = 0

        # now process the package metadata
        if int(pkg_id) > 0:
            # replace existing package metadata
            self.output(
                f"Updating package metadata for {pkg_id}",
                verbose_level=1,
            )
            self.update_pkg_metadata(
                api_url,
                pkg_name,
                pkg_display_name,
                pkg_metadata,
                sleep_time,
                token=token,
                max_tries=max_tries,
                pkg_id=pkg_id,
                tenant_id=jamf_platform_gw_tenant_id,
            )
            pkg_metadata_updated = True
        else:
            # create new package metadata object
            self.output(
                "Creating package metadata",
                verbose_level=1,
            )
            self.update_pkg_metadata(
                api_url,
                pkg_name,
                pkg_display_name,
                pkg_metadata,
                sleep_time,
                token=token,
                max_tries=max_tries,
                pkg_id=pkg_id,
                tenant_id=jamf_platform_gw_tenant_id,
            )
            pkg_metadata_updated = True

        # output the summary
        self.env["pkg_name"] = pkg_name
        self.env["pkg_display_name"] = pkg_display_name
        self.env["pkg_metadata_updated"] = pkg_metadata_updated
        if pkg_metadata_updated:
            self.env["jamfpkgmetadatauploader_summary_result"] = {
                "summary_text": "The following packages were uploaded to or updated in Jamf Pro:",
                "report_fields": [
                    "category",
                    "name",
                    "pkg_name",
                    "pkg_display_name",
                ],
                "data": {
                    "category": pkg_category,
                    "name": str(self.env.get("NAME")),
                    "pkg_name": pkg_name,
                    "pkg_display_name": pkg_display_name,
                },
            }
        self.env["process_skipped"] = process_skipped
