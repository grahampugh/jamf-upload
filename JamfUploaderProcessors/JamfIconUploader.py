#!/usr/local/autopkg/python

"""
JamfIconUploader processor for uploading a category to Jamf Pro using AutoPkg
    by G Pugh
"""

import os.path
import sys

from time import sleep
from autopkglib import ProcessorError

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfUploaderBase import JamfUploaderBase  # noqa: E402

__all__ = ["JamfIconUploader"]


class JamfIconUploader(JamfUploaderBase):
    """A processor for AutoPkg that will upload an icon to a Jamf Cloud or on-prem server.
    Note that an icon can only be successsfully injected into a Mac App Store app item if
    Cloud Services Connection is enabled."""

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
        "icon_file": {
            "required": False,
            "description": "An icon to upload",
            "default": "",
        },
        "icon_uri": {
            "required": False,
            "description": "An icon to upload directly from a Jamf Cloud URI",
            "default": "",
        },
        "sleep": {
            "required": False,
            "description": "Pause after running this processor for specified seconds.",
            "default": "0",
        },
    }

    output_variables = {
        "selfservice_icon_uri": {"description": "The uploaded icon's URI."},
        "icon_id": {"description": "The cuploaded icon's ID."},
        "jamficonuploader_summary_result": {
            "description": "Description of interesting results.",
        },
    }

    def get_icon(self, icon_uri):
        """download an icon file"""

        self.output(f"Downloading icon from {icon_uri}...", verbose_level=2)
        # download the icon
        count = 0
        while True:
            count += 1
            self.output(
                f"Icon download attempt {count}",
                verbose_level=2,
            )
            request = "GET"
            r = self.curl(request=request, url=icon_uri)
            # check HTTP response
            if self.status_check(r, "Icon", icon_uri, request) == "break":
                break
            if count > 5:
                self.output("ERROR: Icon download did not succeed after 5 attempts")
                self.output(f"\nHTTP POST Response Code: {r.status_code}")
                raise ProcessorError("ERROR: Icon download failed ")
            if int(self.sleep) > 30:
                sleep(int(self.sleep))
            else:
                sleep(30)
        return r

    def upload_icon(self, jamf_url, icon_file, token):
        """Upload icon."""

        self.output("Uploading icon...")

        # if we find an object ID we put, if not, we post
        object_type = "icon"
        url = "{}/{}".format(jamf_url, self.api_endpoints(object_type))

        # upload the icon
        count = 0
        while True:
            count += 1
            self.output(
                f"Icon upload attempt {count}",
                verbose_level=2,
            )
            request = "POST"
            r = self.curl(request=request, url=url, token=token, data=icon_file)

            # check HTTP response
            if self.status_check(r, "Icon", icon_file, request) == "break":
                break
            if count > 5:
                self.output("ERROR: Icon upload did not succeed after 5 attempts")
                self.output(f"\nHTTP POST Response Code: {r.status_code}")
                raise ProcessorError("ERROR: Icon upload failed ")
            if int(self.sleep) > 30:
                sleep(int(self.sleep))
            else:
                sleep(30)
        return r

    def main(self):
        """Do the main thing here"""
        self.jamf_url = self.env.get("JSS_URL")
        self.jamf_user = self.env.get("API_USERNAME")
        self.jamf_password = self.env.get("API_PASSWORD")
        self.icon_file = self.env.get("icon_file")
        self.icon_uri = self.env.get("icon_uri")
        self.sleep = self.env.get("sleep")

        # clear any pre-existing summary result
        if "jamficonuploader_summary_result" in self.env:
            del self.env["jamficonuploader_summary_result"]

        # obtain the relevant credentials
        token = self.handle_uapi_auth(self.jamf_url, self.jamf_user, self.jamf_password)

        # obtain the icon from the URI if no file path provided
        if (
            "https://ics.services.jamfcloud.com/icon" in self.icon_uri
            and not self.icon_file
        ):
            r = self.get_icon(self.icon_uri)
            self.icon_file = r.output

        if not self.icon_file:
            raise ProcessorError("ERROR: Icon not found")

        # upload the icon
        r = self.upload_icon(
            self.jamf_url,
            self.icon_file,
            token,
        )

        # get the uri from the output
        self.selfservice_icon_uri = r.output["url"]
        self.icon_id = r.output["id"]

        # output the summary
        self.env["selfservice_icon_uri"] = self.selfservice_icon_uri
        self.env["icon_id"] = str(self.icon_id)
        self.env["jamficonuploader_summary_result"] = {
            "summary_text": "The following icons were uploaded in Jamf Pro:",
            "report_fields": ["selfservice_icon_uri", "icon_id"],
            "data": {
                "selfservice_icon_uri": self.selfservice_icon_uri,
                "icon_id": str(self.icon_id),
            },
        }


if __name__ == "__main__":
    PROCESSOR = JamfIconUploader()
    PROCESSOR.execute_shell()
