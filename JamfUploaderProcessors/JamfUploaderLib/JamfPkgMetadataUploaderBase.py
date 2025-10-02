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

    def check_pkg(self, pkg_name, jamf_url, token):
        """check if a package with the same name exists in the repo
        note that it is possible to have more than one with the same name
        which could mess things up"""

        object_type = "package"
        url = f"{jamf_url}/{self.api_endpoints(object_type)}/name/{quote(pkg_name)}"

        request = "GET"
        r = self.curl(
            request=request,
            url=url,
            token=token,
        )

        if r.status_code == 200:
            obj = json.loads(r.output)
            try:
                obj_id = str(obj["package"]["id"])
            except KeyError:
                obj_id = "-1"
        else:
            obj_id = "-1"
        return obj_id

    def get_category_id(self, jamf_url, category_name, token=""):
        """Get the category ID from the name, or abort if ID not found"""
        # check for existing category
        self.output(f"Checking for '{category_name}' on {jamf_url}")
        obj_type = "category"
        obj_name = category_name
        obj_id = self.get_api_obj_id_from_name(
            jamf_url,
            obj_name,
            obj_type,
            token,
        )

        if obj_id:
            self.output(f"Category '{category_name}' exists: ID {obj_id}")
            return obj_id
        else:
            self.output(f"Category '{category_name}' not found")
            raise ProcessorError("Supplied package category does not exist")

    def update_pkg_metadata_api(  # pylint: disable=too-many-arguments, too-many-locals
        self,
        jamf_url,
        pkg_name,
        pkg_display_name,
        pkg_metadata,
        sleep_time,
        pkg_id=0,
        token="",
    ):
        """Update package metadata using v1/packages endpoint."""

        # get category ID
        if pkg_metadata["category"]:
            category_id = self.get_category_id(
                jamf_url, pkg_metadata["category"], token
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

        pkg_json = self.write_json_file(jamf_url, pkg_data)

        # if we find a pkg ID we put, if not, we post
        object_type = "package_v1"
        if int(pkg_id) > 0:
            url = f"{jamf_url}/{self.api_endpoints(object_type)}/{pkg_id}"
        else:
            url = f"{jamf_url}/{self.api_endpoints(object_type)}"

        count = 0
        while True:
            count += 1
            self.output(
                f"Package metadata upload attempt {count}",
                verbose_level=2,
            )
            request = "PUT" if pkg_id else "POST"
            r = self.curl(request=request, url=url, token=token, data=pkg_json)
            # check HTTP response
            if self.status_check(r, "Package Metadata", pkg_name, request) == "break":
                break
            if count > 5:
                self.output("Package metadata upload did not succeed after 5 attempts")
                self.output(f"\nHTTP POST Response Code: {r.status_code}")
                raise ProcessorError("ERROR: Package metadata upload failed ")
            if int(sleep_time) > 30:
                sleep(int(sleep_time))
            else:
                sleep(30)
        if r.status_code == 201:
            obj = json.loads(json.dumps(r.output))
            self.output(
                obj,
                verbose_level=4,
            )

            try:
                obj_id = obj["id"]
            except KeyError:
                obj_id = "-1"
        else:
            obj_id = "-1"
        return obj_id

    # main function
    def execute(
        self,
    ):  # pylint: disable=too-many-branches, too-many-locals, too-many-statements
        """Perform the metadata upload"""

        jamf_url = self.env.get("JSS_URL").rstrip("/")
        jamf_user = self.env.get("API_USERNAME")
        jamf_password = self.env.get("API_PASSWORD")
        client_id = self.env.get("CLIENT_ID")
        client_secret = self.env.get("CLIENT_SECRET")
        pkg_name = self.env.get("pkg_name")
        pkg_display_name = self.env.get("pkg_display_name")
        replace_metadata = self.to_bool(self.env.get("replace_pkg_metadata"))
        sleep_time = self.env.get("sleep")
        pkg_metadata_updated = False

        # create a dictionary of package metadata from the inputs
        pkg_category = self.env.get("pkg_category")
        pkg_info = self.env.get("pkg_info")
        notes = self.env.get("pkg_notes")
        priority = self.env.get("pkg_priority")
        os_requirements = self.env.get("os_requirements")
        required_processor = self.env.get("required_processor")
        reboot_required = self.to_bool(self.env.get("reboot_required"))
        send_notification = self.to_bool(self.env.get("send_notification"))

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

        # now start the process of uploading the package
        self.output(f"Checking for existing metadata '{pkg_name}' on {jamf_url}")

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

        jamf_pro_version = self.get_jamf_pro_version(jamf_url, token)

        if APLooseVersion(jamf_pro_version) < APLooseVersion("11.4"):
            raise ProcessorError(
                "this processor uses the new packages endpoint so only works on 11.4+"
            )

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

        # check for existing pkg
        obj_id = self.check_pkg(pkg_name, jamf_url, token=token)
        self.output(f"ID: {obj_id}", verbose_level=3)  # TEMP
        if obj_id != "-1":
            self.output(f"Package '{pkg_name}' already exists: ID {obj_id}")
            pkg_id = obj_id  # assign pkg_id for smb runs - JCDS runs get it from the pkg upload
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
            self.update_pkg_metadata_api(
                jamf_url,
                pkg_name,
                pkg_display_name,
                pkg_metadata,
                sleep_time,
                pkg_id=pkg_id,
                token=token,
            )
            pkg_metadata_updated = True
        else:
            # create new package metadata object
            self.output(
                "Creating package metadata",
                verbose_level=1,
            )
            obj_id = self.update_pkg_metadata_api(
                jamf_url,
                pkg_name,
                pkg_display_name,
                pkg_metadata,
                sleep_time,
                pkg_id=pkg_id,
                token=token,
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
