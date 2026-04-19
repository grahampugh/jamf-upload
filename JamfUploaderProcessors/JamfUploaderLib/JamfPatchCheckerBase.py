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
Made by Jerker Adolfsson based on the other JamfUploader processors.
"""

import os.path
import sys

import xml.etree.ElementTree as ET

from autopkglib import (  # pylint: disable=import-error
    ProcessorError,
)

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderBase import (  # pylint: disable=import-error, wrong-import-position
    JamfUploaderBase,
)


class JamfPatchCheckerBase(JamfUploaderBase):
    """Class for functions used to check a patch policy in Jamf"""

    def handle_patch_pkg(
        self,
        api_url,
        patch_softwaretitle_name,
        patch_softwaretitle_id,
        pkg_version,
        pkg_name,
        token="",
        tenant_id="",
    ):
        """Checks for a patch softwaretitle including the linked pkg"""

        self.output("Linking pkg versions in patch softwaretitle...")

        # Get current softwaretitle
        object_type = "patch_software_title"
        endpoint = self.api_endpoints(object_type, tenant_id=tenant_id)
        url = (
            f"{api_url}/{endpoint}/id/{patch_softwaretitle_id}"
        )

        # No need to loop over curl function, since we only make a "GET" request.
        r = self.curl(
            api_type="classic",
            request="GET",
            url=url,
            token=token,
            endpoint_type="patch_software_title",
        )

        if r.status_code != 200:
            raise ProcessorError("ERROR: Could not fetch patch softwaretitle.")

        # Parse response as xml
        try:
            patch_softwaretitle_xml = ET.fromstring(r.output)
        except ET.ParseError as xml_error:
            raise ProcessorError from xml_error

        patch_version_found = False
        # Replace matching version string, with version string including package name
        for v in patch_softwaretitle_xml.findall("versions/version"):
            if v.find("software_version").text == pkg_version:
                patch_version_found = True
                # Remove old, probably empty package element
                v.remove(v.find("package"))
                # Create new package element including given pkg information
                pkg_element = ET.Element("package")
                pkg_element_name = ET.SubElement(pkg_element, "name")
                pkg_element_name.text = pkg_name
                # Inject package element into version element
                v.append(pkg_element)
                # Print new version element for debugging reasons
                self.output(
                    ET.tostring(v, encoding="unicode", method="xml"), verbose_level=3
                )
                self.env["patch_version_found"] = patch_version_found

        if not patch_version_found:
            # Get first match of all the versions listed in the
            # softwaretitle to report the 'latest version'.
            # That's helpful if e.g. AutoPKG uploaded a new version,
            # which is not yet listed in the patch softwaretitle list.
            latest_version = patch_softwaretitle_xml.find(
                "versions/version/software_version"
            ).text
            self.env["patch_version_found"] = patch_version_found
            self.output(
                "WARNING: Could not find matching version "
                + f"'{pkg_version}' in patch softwaretitle '{patch_softwaretitle_name}'. "
                + f"Latest reported version is '{latest_version}'."
            )
            return latest_version

    def execute(self):
        """Do the main thing here"""
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
        version = self.env.get("version")
        patch_softwaretitle = self.env.get("patch_softwaretitle")

        # Clear any pre-existing summary result
        if "jamfpatchchecker_summary_result" in self.env:
            del self.env["jamfpatchchecker_summary_result"]

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

        self.output(f"Checking for existing '{patch_softwaretitle}' on {api_url}")

        # Patch Softwaretitle
        patch_softwaretitle_id = self.get_api_object_id_from_name(
            api_url,
            object_type="patch_software_title",
            object_name=patch_softwaretitle,
            token=token,
            tenant_id=jamf_platform_gw_tenant_id,
        )

        if not patch_softwaretitle_id:
            raise ProcessorError(
                f"ERROR: Couldn't find patch softwaretitle with name '{patch_softwaretitle}'.",
                "You need to create the patch softwaretitle by hand in Jamf Pro.",
                "There is currently no way to create a patch softwaretitle via API.",
            )
        self.env["patch_softwaretitle_id"] = patch_softwaretitle_id

        # Patch Package Definition
        # Links the (AutoPKG) reported version with the reported pkg.
        if not version:
            raise ProcessorError(
                "ERROR: No variable 'version' was reported by AutoPKG."
            )

        latest_version = self.handle_patch_pkg(
            api_url,
            patch_softwaretitle,
            patch_softwaretitle_id,
            version,
            pkg_name,
            token,
            tenant_id=jamf_platform_gw_tenant_id,
        )

        # Prepare the base summary result structure
        summary_result = {
            "summary_text": "The following patch policies were checked in Jamf Pro:",
            "report_fields": [
                "patch_softwaretitle_id",
                "patch_softwaretitle",
                "package_version",
            ],
            "data": {
                "patch_softwaretitle_id": str(patch_softwaretitle_id),
                "patch_softwaretitle": patch_softwaretitle,
                "package_version": version,
            },
        }

        # Conditionally add the latest_version_found if set
        if latest_version:
            summary_result["report_fields"].append("latest_version_found")
            summary_result["data"]["latest_version_found"] = latest_version

        # Set the environment variable for summary result
        self.env["patch"] = patch_softwaretitle
        self.env["jamfpatchchecker_summary_result"] = summary_result
