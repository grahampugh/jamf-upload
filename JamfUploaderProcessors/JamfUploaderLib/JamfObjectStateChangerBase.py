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

import json
import os.path
import sys

from time import sleep
from xml.etree import ElementTree as ET

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


class JamfObjectStateChangerBase(JamfUploaderBase):
    """Class for functions used to flush a policy in Jamf"""

    def set_object_state(
        self,
        jamf_url,
        api_type,
        object_type,
        obj_id,
        object_state,
        retain_data,
        sleep_time,
        token,
    ):
        """Send request to set object end state"""

        # first get the existing object
        self.output("Getting existing object...")

        accept_header = "json"
        if api_type == "classic":
            url = f"{jamf_url}/{self.api_endpoints(object_type)}/id/{obj_id}"
            accept_header = "xml"
        elif api_type == "jpapi":
            url = f"{jamf_url}/{self.api_endpoints(object_type)}/{obj_id}"
        else:
            raise ProcessorError(f"ERROR: API type {api_type} not supported")

        count = 0
        while True:
            count += 1
            self.output(f"Request attempt {count}", verbose_level=2)
            request = "GET"
            # need to receive XML for Classic API, JSON for JPAPI

            r = self.curl(
                api_type=api_type,
                request=request,
                url=url,
                token=token,
                accept_header=accept_header,
            )

            # check HTTP response
            if self.status_check(r, object_type, obj_id, request) == "break":
                break
            if count > 5:
                self.output(
                    f"WARNING: {object_type} request did not succeed after 5 attempts"
                )
                self.output(f"\nHTTP GET Response Code: {r.status_code}")
                raise ProcessorError(f"ERROR: {object_type} GET Request failed")
            if int(sleep_time) > 30:
                sleep(int(sleep_time))
            else:
                sleep(30)

        # now update the object state
        self.output(f"Setting {object_type} state to {object_state}...")
        if api_type == "classic":
            # classic API expects XML
            root = ET.fromstring(r.output)
            # Search for the enabled element anywhere in the XML structure
            state_element = root.find(".//enabled")
            if state_element is None:
                raise ProcessorError(
                    f"ERROR: 'enabled' element not found in {object_type} XML"
                )
            if object_state == "enable":
                state_element.text = "true"
            else:
                state_element.text = "false"
            output_file = self.init_temp_file(url, suffix=".xml")
            with open(output_file, "wb") as file:
                file.write(ET.tostring(root, encoding="utf-8"))
        elif api_type == "jpapi":
            # JPAPI expects JSON
            if isinstance(r.output, dict):
                obj_data = r.output
            else:
                obj_data = json.loads(r.output)
            if "enabled" not in obj_data:
                raise ProcessorError(
                    f"ERROR: 'enabled' field not found in {object_type} JSON"
                )
            if object_state == "enable":
                obj_data["enabled"] = True
            else:
                obj_data["enabled"] = False
            # for computer EAs, we also need to set the manageExistingData field to "RETAIN" or "DELETE" if disabling
            if (
                object_type == "computer_extension_attribute"
                and object_state == "disable"
            ):
                obj_data["manageExistingData"] = "RETAIN" if retain_data else "DELETE"
            output_file = self.init_temp_file(url, suffix=".json")
            with open(output_file, "wb") as file:
                file.write(json.dumps(obj_data).encode("utf-8"))
        else:
            raise ProcessorError(f"ERROR: API type {api_type} not supported")

        # if verbose_level is 3 or more, output the updated data (read from output_file)
        with open(output_file, "r", encoding="utf-8") as file:
            updated_data = file.read().encode("utf-8")
        self.output("Updated data to be sent:", verbose_level=3)
        self.output(updated_data.decode("utf-8"), verbose_level=3)

        # now upload the updated object
        count = 0
        while True:
            count += 1
            self.output(f"{object_type} update attempt {count}", verbose_level=2)
            request = "PUT"
            # Ensure token is a string if it's bytes
            token_str = token.decode("utf-8") if isinstance(token, bytes) else token
            r = self.curl(
                api_type=api_type,
                request=request,
                url=url,
                token=token_str,
                data=output_file,
            )

            # check HTTP response
            if self.status_check(r, object_type, obj_id, request) == "break":
                break
            if count > 5:
                self.output(
                    f"WARNING: {object_type} update did not succeed after 5 attempts"
                )
                self.output(f"\nHTTP PUT Response Code: {r.status_code}")
                raise ProcessorError(f"ERROR: {object_type} update failed ")
            if int(sleep_time) > 30:
                sleep(int(sleep_time))
            else:
                sleep(30)

    def execute(self):
        """Flush a policy log"""
        jamf_url = self.env.get("JSS_URL").rstrip("/")
        jamf_user = self.env.get("API_USERNAME")
        jamf_password = self.env.get("API_PASSWORD")
        client_id = self.env.get("CLIENT_ID")
        client_secret = self.env.get("CLIENT_SECRET")
        object_type = self.env.get("object_type")
        object_name = self.env.get("object_name")
        object_state = self.env.get("object_state")
        retain_data = self.to_bool(self.env.get("retain_data"))
        sleep_time = self.env.get("sleep")

        # object type must be one of policy, extension_attribute, mac_application,
        # mobile_device_application
        valid_object_types = [
            "policy",
            "computer_extension_attribute",
            "app_installers_deployment",
        ]
        if object_type not in valid_object_types:
            raise ProcessorError(
                f"ERROR: object_type must be one of: {', '.join(valid_object_types)}"
            )

        # end state must be one of enable, disable
        valid_object_states = ["enable", "disable"]
        if object_state not in valid_object_states:
            raise ProcessorError(
                f"ERROR: object_state must be one of: {', '.join(valid_object_states)}"
            )

        # clear any pre-existing summary result
        if "jamfobjectstatechanger_summary_result" in self.env:
            del self.env["jamfobjectstatechanger_summary_result"]

        # get api type
        api_type = self.api_type(object_type)

        # we need to substitute the values in the computer group name now to
        # account for version strings in the name
        # substitute user-assignable keys
        if object_name:
            object_name = self.substitute_assignable_keys(object_name)

        # now start the process of uploading the object
        self.output(f"Obtaining API token for {jamf_url}")

        # get token using oauth or basic auth depending on the credentials given
        if jamf_url:
            # determine which token we need based on object type. classic and jpapi types use handle_api_auth, platform type uses handle_platform_api_auth
            api_type = self.api_type(object_type)
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
        obj_id = self.get_api_obj_id_from_name(
            jamf_url,
            object_name,
            object_type,
            token=token,
        )

        if obj_id:
            self.output(f"{object_type} '{object_name}' exists: ID {obj_id}")
            self.output(
                f"Setting object state to {object_state}",
                verbose_level=1,
            )
            self.set_object_state(
                jamf_url,
                api_type,
                object_type,
                obj_id,
                object_state,
                retain_data,
                sleep_time,
                token=token,
            )
        else:
            self.output(
                f"{object_type} '{object_name}' not found on {jamf_url}.",
                verbose_level=1,
            )
            return

        # output the summary
        self.env["jamfobjectstatechanger_summary_result"] = {
            "summary_text": f"The following {object_type}s were updated in Jamf Pro:",
            "report_fields": ["object_type", "object_name", "object_state"],
            "data": {
                "object_type": object_type,
                "object_name": object_name,
                "object_state": object_state,
            },
        }
