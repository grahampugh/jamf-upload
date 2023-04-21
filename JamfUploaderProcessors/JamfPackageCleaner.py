#!/usr/local/autopkg/python

"""
JamfPackageCleaner processor for removing old packages in Jamf Pro. Only keeping a set number of latest uploads.
    by Henrik Engström
"""

import json
import os.path
import sys

from time import sleep

from autopkglib import ProcessorError  # pylint: disable=import-error

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfUploaderBase import JamfUploaderBase  # noqa: E402

__all__ = ["JamfPackageCleaner"]


class JamfPackageCleaner(JamfUploaderBase):
    description = (
        "A processor for AutoPkg that will keep X number of a pkg matching a string"
    )
    input_variables = {
        "JSS_URL": {
            "required": True,
            "description": "URL to a Jamf Pro server that the API user has write access "
            "to, optionally set as a key in the com.github.autopkg "
            "preference file.",
        },
        "API_USERNAME": {
            "required": True,
            "description": "Username of account with appropriate access to "
            "jss, optionally set as a key in the com.github.autopkg "
            "preference file.",
        },
        "API_PASSWORD": {
            "required": True,
            "description": "Password of api user, optionally set as a key in "
            "the com.github.autopkg preference file.",
        },
        "pkg_name_match": {
            "required": False,
            "description": "The name at the beginning of the package. This is used as a base for cleaning. The default value is '%NAME%-', e.g. 'Google Chrome-'.",
            "default": "",
        },
        "versions_to_keep": {
            "required": False,
            "description": "The number of pkg_name_match values to keep in Jamf Pro. This is based on the package ID.",
            "default": 5,
        },
        "minimum_name_length": {
            "required": False,
            "description": "The minimum number of characters required in pkg_name_match. This is used as a failsafe.",
            "default": 3,
        },
        "maximum_allowed_packages_to_delete": {
            "required": False,
            "description": "The maximum number of packages that can be deleted. This is used as a failsafe.",
            "default": 20,
        },
    }

    output_variables = {
        "jamfpackagecleaner_summary_result": {
            "description": "Description of interesting results.",
        },
    }    
    
    def delete_package(self, jamf_url, obj_id, enc_creds="", token=""):
        """Cleaning Packages"""

        self.output("Deleteing package...")

        object_type = "package"
        url = "{}/{}/id/{}".format(jamf_url, self.api_endpoints(object_type), obj_id)

        count = 0
        while True:
            count += 1
            self.output("Package delete attempt {}".format(count), verbose_level=2)
            request = "DELETE"
            r = self.curl(request=request, url=url, enc_creds=enc_creds, token=token)

            # check HTTP response
            if self.status_check(r, "Package", obj_id, request) == "break":
                break
            if count > 5:
                self.output("WARNING: Package deletion did not succeed after 5 attempts")
                self.output("\nHTTP DELETE Response Code: {}".format(r.status_code))
                raise ProcessorError("ERROR: Package deletion failed ")
            sleep(30)
        return r

    def main(self):
        """Clean up old packages in Jamf Pro"""

        # Get the necessary environment variables
        self.jamf_url = self.env.get("JSS_URL")
        self.jamf_user = self.env.get("API_USERNAME")
        self.jamf_password = self.env.get("API_PASSWORD")
        self.pkg_name_match = self.env.get("pkg_name_match") or f"{self.env.get('NAME')}-"
        self.versions_to_keep = int(self.env.get("versions_to_keep"))
        self.minimum_name_length = int(self.env.get("minimum_name_length"))
        self.maximum_allowed_packages_to_delete = int(self.env.get("maximum_allowed_packages_to_delete"))

        # Clear any pre-existing summary result
        if "jamfpackagecleaner_summary_result" in self.env:
            del self.env["jamfpackagecleaner_summary_result"]

        # Abort if the package name match string is too short
        if len(self.pkg_name_match) < self.minimum_name_length:
            self.output(f"'pkg_name_match' argument ({self.pkg_name_match}) needs at least {self.minimum_name_length} characters. Override by changing the 'minimum_name_length' argument. Aborting.")    
            return
        
        # Get all packages from Jamf Pro as JSON object
        self.output(f"Getting all packages from {self.jamf_url}")
        token, send_creds, _ = self.handle_classic_auth(
            self.jamf_url, self.jamf_user, self.jamf_password
        )
        obj_type = "package"
        url = f"{self.jamf_url}/{self.api_endpoints(obj_type)}"
        r = self.curl(request="GET", url=url, token=token)
        jamf_packages = json.loads(r.output.decode('utf-8'))["packages"]

        # Find packages that match the name pattern
        found_packages = [item for item in jamf_packages if item["name"].startswith(self.pkg_name_match)]
        found_packages = sorted(found_packages, key=lambda item: item["id"], reverse=True)

        # If there are not enough versions to delete, log it will skip the deletion step
        if len(found_packages) <= self.versions_to_keep:
            self.output(f"No need to delete any packages. Only {len(found_packages)} found. Keeping up to {self.versions_to_keep} versions")
        
        # Divide the packages into those to keep and those to delete
        packages_to_keep = found_packages[:self.versions_to_keep]
        packages_to_delete = found_packages[self.versions_to_keep:]

        # Check that we're not going to delete too many packages
        if len(packages_to_delete) > self.maximum_allowed_packages_to_delete:
            self.output(f"Too many matches. Found {len(packages_to_delete)} to delete. Maximum allowed is {self.maximum_allowed_packages_to_delete}. Override by setting the 'maximum_allowed_packages_to_delete' argument. Aborting.")
            return

        # Print the packages to keep and delete
        for package in packages_to_keep:
            self.output(f"Keeping {package['name']}", verbose_level=2)
        
        for package in packages_to_delete:
            self.delete_package(jamf_url=self.jamf_url, obj_id=package["id"], token=token)
            self.output(f"Deleting {package['name']}", verbose_level=2)

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

if __name__ == "__main__":
    PROCESSOR = JamfPackageCleaner()
    PROCESSOR.execute_shell()
