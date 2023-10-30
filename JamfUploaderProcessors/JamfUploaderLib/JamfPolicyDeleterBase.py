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


class JamfPolicyDeleterBase(JamfUploaderBase):
    """Class for functions used to delete a policy from Jamf"""

    def delete_policy(self, jamf_url, obj_id, token):
        """Delete policy"""

        self.output("Deleting Policy...")

        object_type = "policy"
        url = "{}/{}/id/{}".format(jamf_url, self.api_endpoints(object_type), obj_id)

        count = 0
        while True:
            count += 1
            self.output("Policy delete attempt {}".format(count), verbose_level=2)
            request = "DELETE"
            r = self.curl(request=request, url=url, token=token)

            # check HTTP response
            if self.status_check(r, "Policy", obj_id, request) == "break":
                break
            if count > 5:
                self.output("WARNING: Policy deletion did not succeed after 5 attempts")
                self.output("\nHTTP POST Response Code: {}".format(r.status_code))
                raise ProcessorError("ERROR: Policy deletion failed ")
            sleep(30)
        return r

    def execute(self):
        """Delete a policy"""
        self.jamf_url = self.env.get("JSS_URL")
        self.jamf_user = self.env.get("API_USERNAME")
        self.jamf_password = self.env.get("API_PASSWORD")
        self.client_id = self.env.get("CLIENT_ID")
        self.client_secret = self.env.get("CLIENT_SECRET")
        self.policy_name = self.env.get("policy_name")

        # clear any pre-existing summary result
        if "jamfpolicydeleter_summary_result" in self.env:
            del self.env["jamfpolicydeleter_summary_result"]

        # now start the process of deleting the object
        self.output(f"Checking for existing '{self.policy_name}' on {self.jamf_url}")

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
        obj_type = "policy"
        obj_name = self.policy_name
        obj_id = self.get_api_obj_id_from_name(
            self.jamf_url,
            obj_name,
            obj_type,
            token,
        )

        if obj_id:
            self.output(f"Policy '{self.policy_name}' exists: ID {obj_id}")
            self.output(
                "Deleting existing policy",
                verbose_level=1,
            )
            self.delete_policy(
                self.jamf_url,
                obj_id,
                token,
            )
        else:
            self.output(
                f"Policy '{self.policy_name}' not found on {self.jamf_url}.",
                verbose_level=1,
            )
            return

        # output the summary
        self.env["jamfpolicydeleter_summary_result"] = {
            "summary_text": "The following policies were deleted from Jamf Pro:",
            "report_fields": ["policy"],
            "data": {"policy": self.policy_name},
        }
