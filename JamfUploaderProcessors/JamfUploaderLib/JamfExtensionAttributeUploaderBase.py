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

from xml.sax.saxutils import escape
from time import sleep

from autopkglib import (
    ProcessorError,
)  # pylint: disable=import-error

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderBase import JamfUploaderBase  # noqa: E402


class JamfExtensionAttributeUploaderBase(JamfUploaderBase):
    """Class for functions used to upload an extension attribute to Jamf"""

    def upload_ea(
        self,
        jamf_url,
        ea_name,
        ea_data_type,
        ea_inventory_display,
        script_path,
        token,
        obj_id=None,
    ):
        """Update extension attribute metadata."""
        # import script from file and replace any keys in the script
        if os.path.exists(script_path):
            with open(script_path, "r") as file:
                script_contents = file.read()
        else:
            raise ProcessorError("Script does not exist!")

        # substitute user-assignable keys
        script_contents = self.substitute_assignable_keys(script_contents)

        # XML-escape the script
        script_contents_escaped = escape(script_contents)

        # build the object
        ea_data = (
            "<computer_extension_attribute>"
            + "<name>{}</name>".format(ea_name)
            + "<enabled>true</enabled>"
            + "<description/>"
            + "<data_type>{}</data_type>".format(ea_data_type)
            + "<input_type>"
            + "  <type>script</type>"
            + "  <platform>Mac</platform>"
            + "  <script>{}</script>".format(script_contents_escaped)
            + "</input_type>"
            + "<inventory_display>{}</inventory_display>".format(ea_inventory_display)
            + "<recon_display>Extension Attributes</recon_display>"
            + "</computer_extension_attribute>"
        )
        self.output(
            "Extension Attribute data:",
            verbose_level=2,
        )
        self.output(
            ea_data,
            verbose_level=2,
        )

        self.output("Uploading Extension Attribute..")
        # write the template to temp file
        template_xml = self.write_temp_file(ea_data)

        # if we find an object ID we put, if not, we post
        object_type = "extension_attribute"
        url = "{}/{}/id/{}".format(jamf_url, self.api_endpoints(object_type), obj_id)

        count = 0
        while True:
            count += 1
            self.output(
                "Extension Attribute upload attempt {}".format(count),
                verbose_level=2,
            )
            request = "PUT" if obj_id else "POST"
            r = self.curl(
                request=request,
                url=url,
                token=token,
                data=template_xml,
            )

            # check HTTP response
            if self.status_check(r, "Extension Attribute", ea_name, request) == "break":
                break
            if count > 5:
                self.output(
                    "ERROR: Extension Attribute upload did not succeed after 5 attempts"
                )
                self.output("\nHTTP POST Response Code: {}".format(r.status_code))
                raise ProcessorError("ERROR: Extension Attribute upload failed ")
            if int(self.sleep) > 30:
                sleep(int(self.sleep))
            else:
                sleep(30)

    def execute(self):
        """Upload an extension attribute"""
        self.jamf_url = self.env.get("JSS_URL")
        self.jamf_user = self.env.get("API_USERNAME")
        self.jamf_password = self.env.get("API_PASSWORD")
        self.client_id = self.env.get("CLIENT_ID")
        self.client_secret = self.env.get("CLIENT_SECRET")
        self.ea_script_path = self.env.get("ea_script_path")
        self.ea_name = self.env.get("ea_name")
        self.replace = self.env.get("replace_ea")
        self.ea_data_type = self.env.get("ea_data_type")
        self.ea_inventory_display = self.env.get("ea_inventory_display")
        self.sleep = self.env.get("sleep")
        # handle setting replace in overrides
        if not self.replace or self.replace == "False":
            self.replace = False

        # clear any pre-existing summary result
        if "jamfextensionattributeuploader_summary_result" in self.env:
            del self.env["jamfextensionattributeuploader_summary_result"]
        ea_uploaded = False

        # handle files with a relative path
        if not self.ea_script_path.startswith("/"):
            found_template = self.get_path_to_file(self.ea_script_path)
            if found_template:
                self.ea_script_path = found_template
            else:
                raise ProcessorError(f"ERROR: EA file {self.ea_script_path} not found")

        # now start the process of uploading the object
        self.output(f"Checking for existing '{self.ea_name}' on {self.jamf_url}")

        # get token using oauth or basic auth depending on the credentials given
        if self.jamf_url and self.client_id and self.client_secret:
            token = self.handle_oauth(self.jamf_url, self.client_id, self.client_secret)
        elif self.jamf_url and self.jamf_user and self.jamf_password:
            token = self.handle_api_auth(
                self.jamf_url, self.jamf_user, self.jamf_password
            )
        else:
            raise ProcessorError("ERROR: Credentials not supplied")

        # check for existing - requires obj_name
        obj_type = "extension_attribute"
        obj_name = self.ea_name
        obj_id = self.get_api_obj_id_from_name(
            self.jamf_url,
            obj_name,
            obj_type,
            token,
        )

        if obj_id:
            self.output(
                "Extension Attribute '{}' already exists: ID {}".format(
                    self.ea_name, obj_id
                )
            )
            if self.replace:
                self.output(
                    "Replacing existing Extension Attribute as 'replace_ea' is set to {}".format(
                        self.replace
                    ),
                    verbose_level=1,
                )
            else:
                self.output(
                    "Not replacing existing Extension Attribute. Use replace_ea='True' to enforce.",
                    verbose_level=1,
                )
                return

        # upload the EA
        self.upload_ea(
            self.jamf_url,
            self.ea_name,
            self.ea_data_type,
            self.ea_inventory_display,
            self.ea_script_path,
            token=token,
            obj_id=obj_id,
        )
        ea_uploaded = True

        # output the summary
        self.env["extension_attribute"] = self.ea_name
        self.env["ea_uploaded"] = ea_uploaded
        if ea_uploaded:
            self.env["jamfextensionattributeuploader_summary_result"] = {
                "summary_text": (
                    "The following extension attributes were created or "
                    "updated in Jamf Pro:"
                ),
                "report_fields": ["name", "path"],
                "data": {"name": self.ea_name, "path": self.ea_script_path},
            }
