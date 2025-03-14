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
from urllib.parse import quote

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


class JamfPolicyLogFlusherBase(JamfUploaderBase):
    """Class for functions used to flush a policy in Jamf"""

    def flush_policy(self, jamf_url, obj_id, interval, sleep_time, token):
        """Send policy log flush request"""

        self.output("Sending policy log flush request...")

        object_type = "logflush"
        url = f"{jamf_url}/{self.api_endpoints(object_type)}/policy/id/{obj_id}/interval/{quote(interval)}"

        count = 0
        while True:
            count += 1
            self.output(f"Log Flush Request attempt {count}", verbose_level=2)
            request = "DELETE"
            r = self.curl(
                request=request,
                url=url,
                token=token,
            )

            # check HTTP response
            if self.status_check(r, "Log Flush Request", obj_id, request) == "break":
                break
            if count > 5:
                self.output(
                    "WARNING: Log Flush Request did not succeed after 5 attempts"
                )
                self.output(f"\nHTTP POST Response Code: {r.status_code}")
                raise ProcessorError("ERROR: Log Flush Request failed")
            if int(sleep_time) > 30:
                sleep(int(sleep_time))
            else:
                sleep(30)
        return r

    def execute(self):
        """Flush a policy log"""
        jamf_url = self.env.get("JSS_URL").rstrip("/")
        jamf_user = self.env.get("API_USERNAME")
        jamf_password = self.env.get("API_PASSWORD")
        client_id = self.env.get("CLIENT_ID")
        client_secret = self.env.get("CLIENT_SECRET")
        policy_name = self.env.get("policy_name")
        logflush_interval = self.env.get("logflush_interval")
        sleep_time = self.env.get("sleep")

        # clear any pre-existing summary result
        if "jamfpolicylogflusher_summary_result" in self.env:
            del self.env["jamfpolicylogflusher_summary_result"]

        # now start the process of deleting the object
        self.output(f"Checking for existing '{policy_name}' on {jamf_url}")

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
        obj_type = "policy"
        obj_name = policy_name
        obj_id = self.get_api_obj_id_from_name(
            jamf_url,
            obj_name,
            obj_type,
            token=token,
        )

        if obj_id:
            self.output(f"Policy '{policy_name}' exists: ID {obj_id}")
            self.output(
                "Flushing existing policy",
                verbose_level=1,
            )
            self.flush_policy(
                jamf_url,
                obj_id,
                logflush_interval,
                sleep_time,
                token=token,
            )
        else:
            self.output(
                f"Policy '{policy_name}' not found on {jamf_url}.",
                verbose_level=1,
            )
            return

        # output the summary
        self.env["jamfpolicylogflusher_summary_result"] = {
            "summary_text": "The following policies were flushed in Jamf Pro:",
            "report_fields": ["policy"],
            "data": {"policy": policy_name},
        }
