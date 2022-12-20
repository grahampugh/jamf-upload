#!/usr/local/autopkg/python

"""
JamfPolicyLogFlusher processor for flushing policies from Jamf Pro using AutoPkg
    by G Pugh
"""

import os.path
import sys

from time import sleep
from urllib.parse import quote

from autopkglib import ProcessorError  # pylint: disable=import-error

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfUploaderBase import JamfUploaderBase  # noqa: E402

__all__ = ["JamfPolicyLogFlusher"]


class JamfPolicyLogFlusher(JamfUploaderBase):
    description = (
        "A processor for AutoPkg that will flush logs for a policy on a Jamf "
        "Cloud or on-prem server."
    )
    input_variables = {
        "JSS_URL": {
            "required": True,
            "description": "URL to a Jamf Pro server that the API user has write access "
            "to, optionally set as a key in the com.github.autopkg "
            "preference file.",
        },
        "API_USERNAME": {
            "required": True,
            "description": "Username of account with appropriate access to "
            "jss, optionally set as a key in the com.github.autopkg "
            "preference file.",
        },
        "API_PASSWORD": {
            "required": True,
            "description": "Password of api user, optionally set as a key in "
            "the com.github.autopkg preference file.",
        },
        "policy_name": {
            "required": True,
            "description": "Policy whose log is to be flushed",
            "default": "",
        },
        "logflush_interval": {
            "required": False,
            "description": "Log interval to be flushed",
            "default": "Zero Days",
        },
    }

    output_variables = {
        "jamfpolicylogflusher_summary_result": {
            "description": "Description of interesting results.",
        },
    }

    def flush_policy(self, jamf_url, obj_id, interval, enc_creds="", token=""):
        """Send policy log flush request"""

        self.output("Sending policy log flush request...")

        object_type = "logflush"
        url = "{}/{}/policy/id/{}/interval/{}".format(
            jamf_url, self.api_endpoints(object_type), obj_id, quote(interval)
        )

        count = 0
        while True:
            count += 1
            self.output("Log Flush Request attempt {}".format(count), verbose_level=2)
            request = "DELETE"
            r = self.curl(
                request=request,
                url=url,
                enc_creds=enc_creds,
                token=token,
            )

            # check HTTP response
            if self.status_check(r, "Log Flush Request", obj_id, request) == "break":
                break
            if count > 5:
                self.output(
                    "WARNING: Log Flush Request did not succeed after 5 attempts"
                )
                self.output("\nHTTP POST Response Code: {}".format(r.status_code))
                raise ProcessorError("ERROR: Log Flush Request failed ")
            sleep(30)
        return r

    def main(self):
        """Do the main thing here"""
        self.jamf_url = self.env.get("JSS_URL")
        self.jamf_user = self.env.get("API_USERNAME")
        self.jamf_password = self.env.get("API_PASSWORD")
        self.policy_name = self.env.get("policy_name")
        self.logflush_interval = self.env.get("logflush_interval")

        # clear any pre-existing summary result
        if "jamfpolicylogflusher_summary_result" in self.env:
            del self.env["jamfpolicylogflusher_summary_result"]

        # now start the process of deleting the object
        self.output(f"Checking for existing '{self.policy_name}' on {self.jamf_url}")

        token, send_creds, _ = self.handle_classic_auth(
            self.jamf_url, self.jamf_user, self.jamf_password
        )

        # check for existing - requires obj_name
        obj_type = "policy"
        obj_name = self.policy_name
        obj_id = self.get_api_obj_id_from_name(
            self.jamf_url,
            obj_name,
            obj_type,
            enc_creds=send_creds,
            token=token,
        )

        if obj_id:
            self.output(f"Policy '{self.policy_name}' exists: ID {obj_id}")
            self.output(
                "Flushing existing policy",
                verbose_level=1,
            )
            self.flush_policy(
                self.jamf_url,
                obj_id,
                self.logflush_interval,
                enc_creds=send_creds,
                token=token,
            )
        else:
            self.output(
                f"Policy '{self.policy_name}' not found on {self.jamf_url}.",
                verbose_level=1,
            )
            return

        # output the summary
        self.env["jamfpolicylogflusher_summary_result"] = {
            "summary_text": "The following policies were flushed in Jamf Pro:",
            "report_fields": ["policy"],
            "data": {"policy": self.policy_name},
        }


if __name__ == "__main__":
    PROCESSOR = JamfPolicyLogFlusher()
    PROCESSOR.execute_shell()
