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


class JamfComputerGroupDeleterBase(JamfUploaderBase):
    """
    Class for functions used to delete a computer group from Jamf.
    Note that it is not possible to delete a computer group if any groups or
    other objects depend on it.
    """

    def delete_computer_group(self, jamf_url, obj_id, token):
        """Delete computer group"""

        self.output("Deleting Computer Group...")

        object_type = "computer_group"
        url = f"{jamf_url}/{self.api_endpoints(object_type)}/id/{obj_id}"

        count = 0
        while True:
            count += 1
            self.output(f"Computer Group delete attempt {count}", verbose_level=2)
            request = "DELETE"
            r = self.curl(request=request, url=url, token=token)

            # check HTTP response
            if self.status_check(r, "Computer Group", obj_id, request) == "break":
                break
            if count > 5:
                self.output(
                    "WARNING: Computer Group deletion did not succeed after 5 attempts"
                )
                self.output(f"\nHTTP POST Response Code: {r.status_code}")
                raise ProcessorError("ERROR: Computer Group deletion failed ")
            sleep(30)
        return r

    def execute(self):
        """Delete a computer group"""
        jamf_url = self.env.get("JSS_URL").rstrip("/")
        jamf_user = self.env.get("API_USERNAME")
        jamf_password = self.env.get("API_PASSWORD")
        client_id = self.env.get("CLIENT_ID")
        client_secret = self.env.get("CLIENT_SECRET")
        computergroup_name = self.env.get("computergroup_name")

        # clear any pre-existing summary result
        if "jamfcomputergroupdeleter_summary_result" in self.env:
            del self.env["jamfcomputergroupdeleter_summary_result"]

        # now start the process of deleting the object
        self.output(f"Checking for existing '{computergroup_name}' on {jamf_url}")

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
        obj_type = "computer_group"
        obj_name = computergroup_name
        obj_id = self.get_api_obj_id_from_name(
            jamf_url,
            obj_name,
            obj_type,
            token,
        )

        if obj_id:
            self.output(f"Computer Group '{computergroup_name}' exists: ID {obj_id}")
            self.output(
                "Deleting existing computer group",
                verbose_level=1,
            )
            self.delete_computer_group(
                jamf_url,
                obj_id,
                token,
            )
        else:
            self.output(
                f"Computer Group '{computergroup_name}' not found on {jamf_url}.",
                verbose_level=1,
            )
            return

        # output the summary
        self.env["jamfcomputergroupdeleter_summary_result"] = {
            "summary_text": "The following computer groups were deleted from Jamf Pro:",
            "report_fields": ["computer_group"],
            "data": {"computer_group": computergroup_name},
        }
