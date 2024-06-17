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

NOTES:
Written by Marcel Keßler based on G Pugh's work
"""

import os.path
import sys
import xml.etree.cElementTree as ET

from time import sleep

from autopkglib import (
    ProcessorError,
)  # pylint: disable=import-error

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderBase import JamfUploaderBase  # noqa: E402


class JamfDockItemUploaderBase(JamfUploaderBase):
    """Class for functions used to upload a dock item to Jamf"""

    def upload_dock_item(
        self,
        jamf_url,
        dock_item_name,
        dock_item_type,
        dock_item_path,
        token,
        obj_id=0,
    ):
        """Update dock item metadata."""

        # Build the xml object
        dock_item_xml_root = ET.Element("dock_item")
        # Converted integer to text, to avoid TypeError while xml dumping
        ET.SubElement(dock_item_xml_root, "id").text = str(obj_id)
        ET.SubElement(dock_item_xml_root, "name").text = dock_item_name
        ET.SubElement(dock_item_xml_root, "type").text = dock_item_type
        ET.SubElement(dock_item_xml_root, "path").text = dock_item_path

        dock_item_xml = self.write_xml_file(dock_item_xml_root)

        self.output("Uploading dock item..")

        object_type = "dock_item"
        url = "{}/{}/id/{}".format(jamf_url, self.api_endpoints(object_type), obj_id)

        count = 0
        while True:
            count += 1
            self.output(
                f"Dock Item upload attempt {count}",
                verbose_level=2,
            )
            request = "PUT" if obj_id else "POST"
            r = self.curl(
                request=request,
                url=url,
                token=token,
                data=dock_item_xml,
            )
            # check HTTP response
            if self.status_check(r, "Dock Item", dock_item_name, request) == "break":
                break
            if count > 5:
                self.output(
                    "ERROR: Temporary dock item update did not succeed after 5 attempts"
                )
                self.output(f"\nHTTP POST Response Code: {r.status_code}")
                raise ProcessorError("ERROR: dock item upload failed ")
            if int(self.sleep) > 30:
                sleep(int(self.sleep))
            else:
                sleep(30)

    def execute(self):
        """Upload a dock item"""
        self.jamf_url = self.env.get("JSS_URL")
        self.jamf_user = self.env.get("API_USERNAME")
        self.jamf_password = self.env.get("API_PASSWORD")
        self.client_id = self.env.get("CLIENT_ID")
        self.client_secret = self.env.get("CLIENT_SECRET")
        self.dock_item_name = self.env.get("dock_item_name")
        self.dock_item_type = self.env.get("dock_item_type")
        self.dock_item_path = self.env.get("dock_item_path")
        self.replace = self.env.get("replace_dock_item")
        self.sleep = self.env.get("sleep")
        # handle setting replace_pkg in overrides
        if not self.replace or self.replace == "False":
            self.replace = False

        # clear any pre-existing summary result
        if "jamfdockitemuploader_summary_result" in self.env:
            del self.env["jamfdockitemuploader_summary_result"]

        # Now process the dock item

        # get token using oauth or basic auth depending on the credentials given
        if self.jamf_url and self.client_id and self.client_secret:
            token = self.handle_oauth(self.jamf_url, self.client_id, self.client_secret)
        elif self.jamf_url and self.jamf_user and self.jamf_password:
            token = self.handle_api_auth(
                self.jamf_url, self.jamf_user, self.jamf_password
            )
        else:
            raise ProcessorError("ERROR: Credentials not supplied")

        # Check for existing dock item
        self.output(f"Checking for existing '{self.dock_item_name}' on {self.jamf_url}")

        obj_type = "dock_item"
        obj_name = self.dock_item_name
        obj_id = self.get_api_obj_id_from_name(
            self.jamf_url,
            obj_name,
            obj_type,
            token=token,
        )

        if obj_id:
            self.output(
                f"Dock Item '{self.dock_item_name}' already exists: ID {obj_id}"
            )
            if self.replace:
                self.output(
                    f"Replacing existing dock item as 'replace_dock_item' is set to {self.replace}",
                    verbose_level=1,
                )
            else:
                self.output(
                    "Not replacing existing dock item. Use replace_dock_item='True' to enforce."
                )
                return

        # Upload the dock item
        self.upload_dock_item(
            self.jamf_url,
            self.dock_item_name,
            self.dock_item_type,
            self.dock_item_path,
            token,
            obj_id=obj_id,
        )

        # output the summary
        self.env["dock_item"] = self.dock_item_name
        self.env["jamfdockitemuploader_summary_result"] = {
            "summary_text": "The following dock items were created or updated in Jamf Pro:",
            "report_fields": [
                "dock_item_id",
                "dock_item_name",
                "dock_item_type",
                "dock_item_path",
            ],
            "data": {
                "dock_item_id": str(obj_id),
                "dock_item_name": self.dock_item_name,
                "dock_item_type": self.dock_item_type,
                "dock_item_path": self.dock_item_path,
            },
        }
