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

        if "_settings" in object_type:
            self.output(f"Object of type {object_type} cannot be deleted")
            return

        self.output(
            f"Checking for existing {object_type} '{object_name}' on {jamf_url}"
        )

        # declare name key
        namekey = self.get_namekey(object_type)

        # get the ID from the object bearing the supplied name
        obj_id = self.get_api_obj_id_from_name(
            jamf_url, object_name, object_type, token=token, filter_name=namekey
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
