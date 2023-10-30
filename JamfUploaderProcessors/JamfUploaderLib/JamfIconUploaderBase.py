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

import os.path
import sys

from time import sleep

from autopkglib import (
    ProcessorError,
)  # pylint: disable=import-error

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderBase import JamfUploaderBase  # noqa: E402


class JamfIconUploaderBase(JamfUploaderBase):
    """Class for functions used to upload an icon to Jamf"""

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
            r = self.curl(request=request, url=icon_uri, endpoint_type="icon_get")
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
            r = self.curl(
                request=request,
                url=url,
                token=token,
                data=icon_file,
                endpoint_type="icon_upload",
            )

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

    def execute(self):
        """Upload an icone"""
        self.jamf_url = self.env.get("JSS_URL")
        self.jamf_user = self.env.get("API_USERNAME")
        self.jamf_password = self.env.get("API_PASSWORD")
        self.client_id = self.env.get("CLIENT_ID")
        self.client_secret = self.env.get("CLIENT_SECRET")
        self.icon_file = self.env.get("icon_file")
        self.icon_uri = self.env.get("icon_uri")
        self.sleep = self.env.get("sleep")

        # clear any pre-existing summary result
        if "jamficonuploader_summary_result" in self.env:
            del self.env["jamficonuploader_summary_result"]

        # get token using oauth or basic auth depending on the credentials given
        if self.jamf_url and self.client_id and self.client_secret:
            token = self.handle_oauth(self.jamf_url, self.client_id, self.client_secret)
        elif self.jamf_url and self.jamf_user and self.jamf_password:
            token = self.handle_api_auth(
                self.jamf_url, self.jamf_user, self.jamf_password
            )
        else:
            raise ProcessorError("ERROR: Credentials not supplied")

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
