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

    def delete_computer_group(self, api_url, object_id, token, max_tries, tenant_id=""):
        """Delete computer group"""

        self.output("Deleting Computer Group...")

        object_type = "computer_group"
        endpoint = self.api_endpoints(object_type, tenant_id=tenant_id)
        url = f"{api_url}/{endpoint}/id/{object_id}"

        count = 0
        while True:
            count += 1
            self.output(f"Computer Group delete attempt {count}", verbose_level=2)
            request = "DELETE"
            r = self.curl(api_type="classic", request=request, url=url, token=token)

            # check HTTP response
            if self.status_check(r, "Computer Group", object_id, request) == "break":
                break
            if count >= max_tries:
                self.output(
                    f"WARNING: Computer Group deletion did not succeed after {max_tries} attempts"
                )
                self.output(f"\nHTTP POST Response Code: {r.status_code}")
                raise ProcessorError("ERROR: Computer Group deletion failed ")
            sleep(10)
        return r

    def execute(self):
        """Delete a computer group"""
        jamf_url = self.env.get("JSS_URL").rstrip("/")
        jamf_user = self.env.get("API_USERNAME")
        jamf_password = self.env.get("API_PASSWORD")
        jamf_platform_gw_region = self.env.get("PLATFORM_API_REGION")
        jamf_platform_gw_tenant_id = self.env.get("PLATFORM_API_TENANT_ID")
        client_id = self.env.get("CLIENT_ID")
        client_secret = self.env.get("CLIENT_SECRET")
        bearer_token = self.env.get("BEARER_TOKEN")
        jamf_cli_profile = self.env.get("JAMF_CLI_PROFILE")
        computergroup_name = self.env.get("computergroup_name")
        max_tries = self.env.get("max_tries")

        # verify that max_tries is an integer greater than zero and less than 10
        try:
            max_tries = int(max_tries)
            if max_tries < 1 or max_tries > 10:
                raise ValueError
        except (ValueError, TypeError):
            max_tries = 5

        # clear any pre-existing summary result
        if "jamfcomputergroupdeleter_summary_result" in self.env:
            del self.env["jamfcomputergroupdeleter_summary_result"]

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
        self.output(f"Checking for existing '{computergroup_name}' on {api_url}")

        # check for existing - requires object_name
        object_id = self.get_api_object_id_from_name(
            api_url,
            object_type="computer_group",
            object_name=computergroup_name,
            token=token,
            tenant_id=jamf_platform_gw_tenant_id,
        )

        if object_id:
            self.output(f"Computer Group '{computergroup_name}' exists: ID {object_id}")
            self.output(
                "Deleting existing computer group",
                verbose_level=1,
            )
            self.delete_computer_group(
                api_url,
                object_id,
                token,
                max_tries,
                tenant_id=jamf_platform_gw_tenant_id,
            )
        else:
            self.output(
                f"Computer Group '{computergroup_name}' not found on {api_url}.",
                verbose_level=1,
            )
            return

        # output the summary
        self.env["jamfcomputergroupdeleter_summary_result"] = {
            "summary_text": "The following computer groups were deleted from Jamf Pro:",
            "report_fields": ["computer_group"],
            "data": {"computer_group": computergroup_name},
        }
