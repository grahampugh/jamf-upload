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


class JamfPolicyDeleterBase(JamfUploaderBase):
    """Class for functions used to delete a policy from Jamf"""

    def delete_policy(self, api_url, object_id, token, max_tries, tenant_id=""):
        """Delete policy"""

        self.output("Deleting Policy...")

        object_type = "policy"
        endpoint = self.api_endpoints(object_type, tenant_id=tenant_id)
        url = f"{api_url}/{endpoint}/id/{object_id}"

        count = 0
        while True:
            count += 1
            self.output(f"Policy delete attempt {count}", verbose_level=2)
            request = "DELETE"
            r = self.curl(api_type="classic", request=request, url=url, token=token)

            # check HTTP response
            if self.status_check(r, "Policy", object_id, request) == "break":
                break
            if count >= max_tries:
                self.output(
                    f"WARNING: Policy deletion did not succeed after {max_tries} attempts"
                )
                self.output(f"\nHTTP POST Response Code: {r.status_code}")
                raise ProcessorError("ERROR: Policy deletion failed ")
            sleep(10)
        return r

    def execute(self):
        """Delete a policy"""
        jamf_url = self.env.get("JSS_URL").rstrip("/")
        jamf_user = self.env.get("API_USERNAME")
        jamf_password = self.env.get("API_PASSWORD")
        jamf_platform_gw_region = self.env.get("PLATFORM_API_REGION")
        jamf_platform_gw_tenant_id = self.env.get("PLATFORM_API_TENANT_ID")
        client_id = self.env.get("CLIENT_ID")
        client_secret = self.env.get("CLIENT_SECRET")
        bearer_token = self.env.get("BEARER_TOKEN")
        jamf_cli_profile = self.env.get("JAMF_CLI_PROFILE")
        policy_name = self.env.get("policy_name")
        max_tries = self.env.get("max_tries")

        # verify that max_tries is an integer greater than zero and less than 10
        try:
            max_tries = int(max_tries)
            if max_tries < 1 or max_tries > 10:
                raise ValueError
        except (ValueError, TypeError):
            max_tries = 5

        # clear any pre-existing summary result
        if "jamfpolicydeleter_summary_result" in self.env:
            del self.env["jamfpolicydeleter_summary_result"]

        # get a token
        token = self.auth(
            jamf_url=jamf_url,
            jamf_user=jamf_user,
            password=jamf_password,
            region=jamf_platform_gw_region,
            tenant_id=jamf_platform_gw_tenant_id,
            client_id=client_id,
            client_secret=client_secret,
            token=bearer_token,
            jamf_cli_profile=jamf_cli_profile,
        )

        # construct the api_url based on the API type
        api_url = self.construct_api_url(
            jamf_url=jamf_url, region=jamf_platform_gw_region
        )
        self.output(f"API URL is {api_url}", verbose_level=3)

        # now start the process of deleting the object
        self.output(f"Checking for existing '{policy_name}' on {api_url}")

        # check for existing - requires object_name
        object_id = self.get_api_object_id_from_name(
            api_url,
            object_type="policy",
            object_name=policy_name,
            token=token,
            tenant_id=jamf_platform_gw_tenant_id,
        )

        if object_id:
            self.output(f"Policy '{policy_name}' exists: ID {object_id}")
            self.output(
                "Deleting existing policy",
                verbose_level=1,
            )
            self.delete_policy(
                api_url,
                object_id,
                token,
                max_tries,
                tenant_id=jamf_platform_gw_tenant_id,
            )
        else:
            self.output(
                f"Policy '{policy_name}' not found on {api_url}.",
                verbose_level=1,
            )
            return

        # output the summary
        self.env["jamfpolicydeleter_summary_result"] = {
            "summary_text": "The following policies were deleted from Jamf Pro:",
            "report_fields": ["policy"],
            "data": {"policy": policy_name},
        }
