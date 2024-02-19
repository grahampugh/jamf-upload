#!/usr/local/autopkg/python

"""
JamfPatchChecker processor for checking if a patch definition exists for the given pkg name and version in Jamf Pro.
    Made by Jerker Adolfsson based on the great work in jamf-upload.
"""

import os.path
import sys

import xml.etree.ElementTree as ET

from autopkglib import ProcessorError  # pylint: disable=import-error

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfUploaderBase import JamfUploaderBase  # noqa: E402

__all__ = ["JamfPatchChecker"]


class JamfPatchChecker(JamfUploaderBase):
    description = (
        "A processor for AutoPkg that will upload a Patch Policy to a Jamf "
        "Cloud or on-prem server."
    )

    input_variables = {
        "JSS_URL": {
            "required": True,
            "description": "URL to a Jamf Pro server that the API user has write access "
                           "to, optionally set as a key in the com.github.autopkg "
                           "preference file.",
        },
        "API_USERNAME": {
            "required": False,
            "description": "Username of account with appropriate access to "
                           "jss, optionally set as a key in the com.github.autopkg "
                           "preference file.",
        },
        "API_PASSWORD": {
            "required": False,
            "description": "Password of api user, optionally set as a key in "
                           "the com.github.autopkg preference file.",
        },
        "CLIENT_ID": {
            "required": False,
            "description": "Client ID with access to "
                           "jss, optionally set as a key in the com.github.autopkg "
                           "preference file.",
        },
        "CLIENT_SECRET": {
            "required": False,
            "description": "Secret associated with the Client ID, optionally set as a key in "
                           "the com.github.autopkg preference file.",
        },
        "pkg_name": {
            "required": False,
            "description": "Name of package which should be used in the patch."
                           "Mostly provided by previous AutoPKG recipe/processor.",
            "default": "",
        },
        "version": {
            "required": False,
            "description": "Version string - provided by previous pkg recipe/processor.",
            "default": "",
        },
        "patch_softwaretitle": {
            "required": True,
            "description": (
                "Name of the patch softwaretitle (e.g. 'Mozilla Firefox') used in Jamf. "
                "You need to create the patch softwaretitle by hand, since there is "
                "currently no way to create these via the API."
            ),
            "default": "",
        },
        "sleep": {
            "required": False,
            "description": "Pause after running this processor for specified seconds.",
            "default": "0",
        },
    }

    output_variables = {
        "patch_version_found": {
            "description": "Returns True if the specified version is found in the patch software title, "
                           "False otherwise."
        },
        "jamfpatchchecker_summary_result": {"description": "Description of interesting results.",
                                            },
    }

    def handle_patch_pkg(
            self,
            jamf_url,
            patch_softwaretitle_name,
            patch_softwaretitle_id,
            pkg_version,
            pkg_name,
            token="",
    ):
        self.output("Linking pkg versions in patch softwaretitle...")

        # Get current softwaretitle
        object_type = "patch_software_title"
        url = "{}/{}/id/{}".format(
            jamf_url, self.api_endpoints(object_type), patch_softwaretitle_id
        )

        # No need to loop over curl function, since we only make a "GET" request.
        r = self.curl(
            request="GET", url=url, token=token, endpoint_type="patch_software_title"
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
                    ET.tostring(v, encoding="UTF-8", method="xml"), verbose_level=3
                )
                self.env["patch_version_found"] = patch_version_found

        if not patch_version_found:
            # Get first match of all the versions listed in the
            # softwaretitle to report the 'latest version'.
            # That's helpful if e.g. AutoPKG uploaded a new version,
            # which is not yet listed in the patch softwaretitle list.
            latest_version = patch_softwaretitle_xml.find("versions/version/software_version").text
            self.latest_version = latest_version  # Set as an attribute of the class
            self.env["patch_version_found"] = patch_version_found
            self.output(
                "WARNING: Could not find matching version "
                + f"'{pkg_version}' in patch softwaretitle '{patch_softwaretitle_name}'. "
                + f"Latest reported version is '{self.latest_version}'."
            )

    def main(self):
        """Do the main thing here"""
        self.jamf_url = self.env.get("JSS_URL")
        self.jamf_user = self.env.get("API_USERNAME")
        self.jamf_password = self.env.get("API_PASSWORD")
        self.client_id = self.env.get("CLIENT_ID")
        self.client_secret = self.env.get("CLIENT_SECRET")
        self.pkg_name = self.env.get("pkg_name")
        self.version = self.env.get("version")
        self.patch_softwaretitle = self.env.get("patch_softwaretitle")
        self.sleep = self.env.get("sleep")

        # Clear any pre-existing summary result
        if "jamfpatchchecker_summary_result" in self.env:
            del self.env["jamfpatchchecker_summary_result"]

        self.output(
            f"Checking for existing '{self.patch_softwaretitle}' on {self.jamf_url}"
        )

        # Get token using oauth or basic auth depending on the credentials given
        if self.jamf_url and self.client_id and self.client_secret:
            token = self.handle_oauth(self.jamf_url, self.client_id, self.client_secret)
        elif self.jamf_url and self.jamf_user and self.jamf_password:
            token = self.handle_api_auth(
                self.jamf_url, self.jamf_user, self.jamf_password
            )
        else:
            raise ProcessorError("ERROR: Credentials not supplied")

        # Patch Softwaretitle
        obj_type = "patch_software_title"
        obj_name = self.patch_softwaretitle
        self.patch_softwaretitle_id = self.get_api_obj_id_from_name(
            self.jamf_url,
            obj_name,
            obj_type,
            token=token,
        )

        if not self.patch_softwaretitle_id:
            raise ProcessorError(
                f"ERROR: Couldn't find patch softwaretitle with name '{self.patch_softwaretitle}'.",
                "You need to create the patch softwaretitle by hand in Jamf Pro.",
                "There is currently no way to create a patch softwaretitle via API.",
            )
        self.env["patch_softwaretitle_id"] = self.patch_softwaretitle_id

        # Patch Package Definition
        # Links the (AutoPKG) reported version with the reported pkg.
        if not self.version:
            raise ProcessorError(
                "ERROR: No variable 'version' was reported by AutoPKG."
            )

        self.handle_patch_pkg(
            self.jamf_url,
            self.patch_softwaretitle,
            self.patch_softwaretitle_id,
            self.version,
            self.pkg_name,
            token,
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
                "patch_softwaretitle_id": str(self.patch_softwaretitle_id),
                "patch_softwaretitle": self.patch_softwaretitle,
                "package_version": self.version,
            },
        }

        # Conditionally add the latest_version_found if set
        if hasattr(self, 'latest_version') and self.latest_version:
            summary_result["report_fields"].append("latest_version_found")
            summary_result["data"]["latest_version_found"] = self.latest_version

        # Set the environment variable for summary result
        self.env["patch"] = self.patch_softwaretitle
        self.env["jamfpatchchecker_summary_result"] = summary_result


if __name__ == "__main__":
    PROCESSOR = JamfPatchChecker()
    PROCESSOR.execute_shell()
