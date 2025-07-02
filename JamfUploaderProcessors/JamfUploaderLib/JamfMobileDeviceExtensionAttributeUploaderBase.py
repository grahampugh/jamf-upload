#!/usr/local/autopkg/python
# pylint: disable=invalid-name

"""
Copyright 2025 Graham Pugh

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


class JamfMobileDeviceExtensionAttributeUploaderBase(JamfUploaderBase):
    """Class for functions used to upload a mobile device extension attribute to Jamf"""

    def upload_ea(
        self,
        jamf_url,
        ea_name,
        ea_description,
        ea_data_type,
        ea_input_type,
        ea_popup_choices,
        ea_directory_service_attribute_mapping,
        ea_inventory_display,
        sleep_time,
        token,
        obj_id=None,
    ):
        """Update extension attribute metadata."""

        if ea_input_type == "popup":
            ea_xml_type = "Pop-up Menu"
        elif ea_input_type == "text":
            ea_xml_type = "Text Field"
        elif ea_input_type == "ldap":
            ea_xml_type = "Directory Service Attribute Mapping"
        else:
            raise ProcessorError(f"ERROR: EA input type {ea_input_type} not supported")

        # build the object
        ea_data = (
            "<mobile_device_extension_attribute>"
            + f"<name>{ea_name}</name>"
            + "<enabled>true</enabled>"
            + f"<description>{ea_description}</description>"
            + f"<data_type>{ea_data_type}</data_type>"
            + f"<inventory_display>{ea_inventory_display}</inventory_display>"
            + "<recon_display>Extension Attributes</recon_display>"
            + "<input_type>"
            + f"<type>{ea_xml_type}</type>"
        )
        if ea_input_type == "popup":
            ea_data += "<popup_choices>"
            for choice in ea_popup_choices:
                ea_data += f"<choice>{choice}</choice>"
            ea_data += "</popup_choices>"
        elif ea_input_type == "ldap":
            ea_data += f"<attribute_mapping>{ea_directory_service_attribute_mapping}</attribute_mapping>"
        ea_data += "</input_type>" + "</mobile_device_extension_attribute>"

        self.output("Uploading Extension Attribute...")
        # write the template to temp file
        template_xml = self.write_temp_file(ea_data)

        # if we find an object ID we put, if not, we post
        object_type = "mobile_device_extension_attribute"
        url = f"{jamf_url}/{self.api_endpoints(object_type)}/id/{obj_id}"

        self.output(
            "Extension Attribute data:",
            verbose_level=2,
        )
        self.output(
            ea_data,
            verbose_level=2,
        )

        count = 0
        while True:
            count += 1
            self.output(
                f"Extension Attribute upload attempt {count}",
                verbose_level=2,
            )
            request = "PUT" if obj_id else "POST"
            r = self.curl(request=request, url=url, token=token, data=template_xml)
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
        ea_name = self.env.get("ea_name")
        ea_description = self.env.get("ea_description")
        ea_input_type = self.env.get("ea_input_type")
        ea_data_type = self.env.get("ea_data_type")
        ea_inventory_display = self.env.get("ea_inventory_display")
        ea_popup_choices = self.env.get("ea_popup_choices")
        ea_directory_service_attribute_mapping = self.env.get(
            "ea_directory_service_attribute_mapping"
        )
        replace_ea = self.to_bool(self.env.get("replace_ea"))
        sleep_time = self.env.get("sleep")
        ea_uploaded = False

        # convert popup choices to list
        if ea_popup_choices:
            ea_popup_choices = ea_popup_choices.split(",")

        # clear any pre-existing summary result
        if "jamfmobiledeviceextensionattributeuploader_summary_result" in self.env:
            del self.env["jamfmobiledeviceextensionattributeuploader_summary_result"]

        # determine input type
        if ea_input_type != "popup" and ea_input_type != "ldap":
            raise ProcessorError(f"ERROR: EA input type {ea_input_type} not supported")

        # now start the process of uploading the object
        self.output(f"Checking for existing '{ea_name}' on {jamf_url}")

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

        # check for existing - requires obj_name
        obj_type = "mobile_device_extension_attribute"
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
                    (
                        "Replacing existing Extension Attribute as 'replace_ea' is set to True"
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
            jamf_url,
            ea_name,
            ea_description,
            ea_data_type,
            ea_input_type,
            ea_popup_choices,
            ea_directory_service_attribute_mapping,
            ea_inventory_display,
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
                "report_fields": ["name", "input_type"],
                "data": {
                    "name": ea_name,
                    "input_type": ea_input_type,
                },
            }
