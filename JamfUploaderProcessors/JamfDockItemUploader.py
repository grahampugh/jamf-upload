#!/usr/local/autopkg/python

"""
JamfDockItemUploader processor for uploading a dock item to Jamf Pro using AutoPkg
    by Marcel Keßler based on G Pugh's great work
"""

import os.path
import sys
import xml.etree.cElementTree as ET

from time import sleep
from autopkglib import ProcessorError  # pylint: disable=import-error

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfUploaderBase import JamfUploaderBase  # noqa: E402

__all__ = ["JamfDockItemUploader"]


class JamfDockItemUploader(JamfUploaderBase):
    description = (
        "A processor for AutoPkg that will upload a Dock item to a Jamf Cloud "
        "or on-prem server."
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
        "dock_item_name": {
            "required": True,
            "description": "Name of Dock Item",
            "default": "",
        },
        "dock_item_type": {
            "required": True,
            "description": "Type of Dock Item - either 'App', 'File' or 'Folder'",
            "default": "App",
        },
        "dock_item_path": {
            "required": True,
            "description": "Path of Dock Item - e.g. 'file:///Applications/Safari.app/'",
            "default": "",
        },
        "replace_dock_item": {
            "required": False,
            "description": "Overwrite an existing dock item if True.",
            "default": False,
        },
        "sleep": {
            "required": False,
            "description": "Pause after running this processor for specified seconds.",
            "default": "0",
        },
    }

    output_variables = {
        "dock_item": {"description": "The created/updated dock item."},
        "jamfdockitemuploader_summary_result": {
            "description": "Description of interesting results.",
        },
    }

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

    def main(self):
        """Do the main thing here"""
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


if __name__ == "__main__":
    PROCESSOR = JamfDockItemUploader()
    PROCESSOR.execute_shell()
