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


class JamfObjectDeleterBase(JamfUploaderBase):
    """Class for functions used to delete an API object from Jamf"""

    def delete_object(self, jamf_url, object_type, obj_id, token):
        """Delete API object"""

        self.output(f"Deleting {object_type}...")

        if "JSSResource" in self.api_endpoints(object_type):
            # do XML stuff
            url = f"{jamf_url}/{self.api_endpoints(object_type)}/id/{obj_id}"
        else:
            url = f"{jamf_url}/{self.api_endpoints(object_type)}/{obj_id}"

        count = 0
        while True:
            count += 1
            self.output(f"{object_type} delete attempt {count}", verbose_level=2)
            request = "DELETE"
            r = self.curl(request=request, url=url, token=token)

            # check HTTP response
            if self.status_check(r, object_type, obj_id, request) == "break":
                break
            if count > 5:
                self.output(
                    f"WARNING: {object_type} deletion did not succeed after 5 attempts"
                )
                self.output(f"\nHTTP POST Response Code: {r.status_code}")
                raise ProcessorError(f"ERROR: {object_type} deletion failed ")
            sleep(30)
        return r

    def execute(self):
        """Delete an API object"""
        jamf_url = self.env.get("JSS_URL").rstrip("/")
        jamf_user = self.env.get("API_USERNAME")
        jamf_password = self.env.get("API_PASSWORD")
        client_id = self.env.get("CLIENT_ID")
        client_secret = self.env.get("CLIENT_SECRET")
        object_name = self.env.get("object_name")
        object_type = self.env.get("object_type")

        # clear any pre-existing summary result
        if "jamfobjectdeleter_summary_result" in self.env:
            del self.env["jamfobjectdeleter_summary_result"]

        # get token using oauth or basic auth depending on the credentials given
        if jamf_url and client_id and client_secret:
            token = self.handle_oauth(jamf_url, client_id, client_secret)
        elif jamf_url:
            token = self.handle_api_auth(jamf_url, jamf_user, jamf_password)
        else:
            raise ProcessorError("ERROR: Jamf Pro URL not supplied")

        if "_settings" in object_type:
            self.output(f"Object of type {object_type} cannot be deleted")
            return

        self.output(
            f"Checking for existing {object_type} '{object_name}' on {jamf_url}"
        )

        # declare name key
        name_key = "name"
        if (
            object_type == "computer_prestage"
            or object_type == "mobile_device_prestage"
            or object_type == "enrollment_customization"
        ):
            name_key = "displayName"

        obj_id = self.get_api_obj_id_from_name(
            jamf_url, object_name, object_type, token=token, filter_name=name_key
        )

        # check for existing - requires obj_name
        obj_id = self.get_api_obj_id_from_name(
            jamf_url,
            object_name,
            object_type,
            token,
        )

        if obj_id:
            self.output(f"{object_type} '{object_name}' exists: ID {obj_id}")
            self.output(
                f"Deleting existing {object_type}",
                verbose_level=1,
            )
            self.delete_object(
                jamf_url,
                object_type,
                obj_id,
                token,
            )
        else:
            self.output(
                f"{object_type} '{object_name}' not found on {jamf_url}.",
                verbose_level=1,
            )
            return

        # output the summary

        self.env["jamfobjectdeleter_summary_result"] = {
            "summary_text": "The following API objects were deleted from Jamf Pro:",
            "report_fields": ["type", "name"],
            "data": {"type": object_type, "name": object_name},
        }
