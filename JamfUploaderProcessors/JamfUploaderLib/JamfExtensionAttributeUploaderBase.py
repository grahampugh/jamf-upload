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
"""

import os.path
import sys

from xml.sax.saxutils import escape
from time import sleep

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


class JamfExtensionAttributeUploaderBase(JamfUploaderBase):
    """Class for functions used to upload an extension attribute to Jamf"""

    def upload_ea(
        self,
        jamf_url,
        ea_name,
        ea_description,
        ea_data_type,
        ea_inventory_display,
        script_path,
        skip_script_key_substitution,
        sleep_time,
        token,
        obj_id=None,
    ):
        """Update extension attribute metadata."""
        # import script from file and replace any keys in the script
        if os.path.exists(script_path):
            with open(script_path, "r", encoding="utf-8") as file:
                script_contents = file.read()
        else:
            raise ProcessorError("Script does not exist!")

        if not skip_script_key_substitution:
            # substitute user-assignable keys
            script_contents = self.substitute_assignable_keys(script_contents)

        # format inventoryDisplayType & dataType correctly
        ea_inventory_display = ea_inventory_display.replace(" ", "_").upper()
        ea_data_type = ea_data_type.upper()

        self.output("Data type: " + type(ea_inventory_display), verbose_level=3)

        # build the object
        ea_data = {
            "name": ea_name,
            "enabled": True,
            "description": ea_description,
            "dataType": ea_data_type,
            "inventoryDisplayType": ea_inventory_display,
            "inputType": "script",
            "scriptContents": script_contents,
        }

        self.output(
            "Extension Attribute data:",
            verbose_level=2,
        )
        self.output(
            ea_data,
            verbose_level=2,
        )

        self.output("Uploading Extension Attribute...")
        ea_json = self.write_json_file(ea_data)

        # if we find an object ID we put, if not, we post
        object_type = "computer_extension_attribute"
        if obj_id:
            url = f"{jamf_url}/{self.api_endpoints(object_type)}/{obj_id}"
        else:
            url = "{}/{}".format(jamf_url, self.api_endpoints(object_type))

        count = 0
        while True:
            count += 1
            self.output(
                f"Extension Attribute upload attempt {count}",
                verbose_level=2,
            )
            request = "PUT" if obj_id else "POST"
            r = self.curl(request=request, url=url, token=token, data=ea_json)
            # check HTTP response
            if self.status_check(r, "Extension Attribute", ea_name, request) == "break":
                break
            if count > 5:
                self.output(
                    "ERROR: Extension Attribute upload did not succeed after 5 attempts"
                )
                self.output(f"\nHTTP POST Response Code: {r.status_code}")
                raise ProcessorError("ERROR: Extension Attribute upload failed ")
            if int(sleep_time) > 30:
                sleep(int(sleep_time))
            else:
                sleep(30)

    def execute(self):
        """Upload an extension attribute"""
        jamf_url = self.env.get("JSS_URL").rstrip("/")
        jamf_user = self.env.get("API_USERNAME")
        jamf_password = self.env.get("API_PASSWORD")
        client_id = self.env.get("CLIENT_ID")
        client_secret = self.env.get("CLIENT_SECRET")
        ea_script_path = self.env.get("ea_script_path")
        ea_name = self.env.get("ea_name")
        ea_description = self.env.get("ea_description")
        skip_script_key_substitution = self.env.get("skip_script_key_substitution")
        replace_ea = self.env.get("replace_ea")
        ea_data_type = self.env.get("ea_data_type")
        ea_inventory_display = self.env.get("ea_inventory_display")
        sleep_time = self.env.get("sleep")
        # handle setting replace in overrides
        if not replace_ea or replace_ea == "False":
            replace_ea = False
        if not skip_script_key_substitution or skip_script_key_substitution == "False":
            skip_script_key_substitution = False

        # clear any pre-existing summary result
        if "jamfextensionattributeuploader_summary_result" in self.env:
            del self.env["jamfextensionattributeuploader_summary_result"]
        ea_uploaded = False

        # handle files with a relative path
        if not ea_script_path.startswith("/"):
            found_template = self.get_path_to_file(ea_script_path)
            if found_template:
                ea_script_path = found_template
            else:
                raise ProcessorError(f"ERROR: EA file {ea_script_path} not found")

        # now start the process of uploading the object
        self.output(f"Checking for existing '{ea_name}' on {jamf_url}")

        # get token using oauth or basic auth depending on the credentials given
        if jamf_url and client_id and client_secret:
            token = self.handle_oauth(jamf_url, client_id, client_secret)
        elif jamf_url and jamf_user and jamf_password:
            token = self.handle_api_auth(jamf_url, jamf_user, jamf_password)
        else:
            raise ProcessorError("ERROR: Credentials not supplied")

        # check for existing - requires obj_name
        obj_type = "computer_extension_attribute"
        obj_name = ea_name
        obj_id = self.get_api_obj_id_from_name(
            jamf_url,
            obj_name,
            obj_type,
            token,
        )

        if obj_id:
            self.output(f"Extension Attribute '{ea_name}' already exists: ID {obj_id}")
            if replace_ea:
                self.output(
                    f"Replacing existing Extension Attribute as 'replace_ea' is set to {replace_ea}",
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
            jamf_url,
            ea_name,
            ea_description,
            ea_data_type,
            ea_inventory_display,
            ea_script_path,
            skip_script_key_substitution,
            sleep_time,
            token=token,
            obj_id=obj_id,
        )
        ea_uploaded = True

        # output the summary
        self.env["extension_attribute"] = ea_name
        self.env["ea_uploaded"] = ea_uploaded
        if ea_uploaded:
            self.env["jamfextensionattributeuploader_summary_result"] = {
                "summary_text": (
                    "The following extension attributes were created or "
                    "updated in Jamf Pro:"
                ),
                "report_fields": ["name", "path"],
                "data": {"name": ea_name, "path": ea_script_path},
            }
