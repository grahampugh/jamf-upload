#!/usr/local/autopkg/python

"""
JamfPolicyDeleter processor for deleting policies from Jamf Pro using AutoPkg
    by G Pugh
"""

import os.path
import sys

from time import sleep

from autopkglib import ProcessorError  # pylint: disable=import-error

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfUploaderBase import JamfUploaderBase  # noqa: E402

__all__ = ["JamfPolicyDeleter"]


class JamfPolicyDeleter(JamfUploaderBase):
    description = (
        "A processor for AutoPkg that will delete a policy from a Jamf Cloud "
        "or on-prem server."
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
            "description": "Policy to delete",
            "default": "",
        },
    }

    output_variables = {
        "jamfpolicydeleter_summary_result": {
            "description": "Description of interesting results.",
        },
    }

    def delete_policy(self, jamf_url, obj_id, enc_creds="", token=""):
        """Delete policy"""

        self.output("Deleting Policy...")

        object_type = "policy"
        url = "{}/{}/id/{}".format(jamf_url, self.api_endpoints(object_type), obj_id)

        count = 0
        while True:
            count += 1
            self.output("Policy delete attempt {}".format(count), verbose_level=2)
            request = "DELETE"
            r = self.curl(request=request, url=url, enc_creds=enc_creds, token=token)

            # check HTTP response
            if self.status_check(r, "Policy", obj_id, request) == "break":
                break
            if count > 5:
                self.output("WARNING: Policy deletion did not succeed after 5 attempts")
                self.output("\nHTTP POST Response Code: {}".format(r.status_code))
                raise ProcessorError("ERROR: Policy deletion failed ")
            sleep(30)
        return r

    def main(self):
        """Do the main thing here"""
        self.jamf_url = self.env.get("JSS_URL")
        self.jamf_user = self.env.get("API_USERNAME")
        self.jamf_password = self.env.get("API_PASSWORD")
        self.policy_name = self.env.get("policy_name")

        # clear any pre-existing summary result
        if "jamfpolicydeleter_summary_result" in self.env:
            del self.env["jamfpolicydeleter_summary_result"]

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
                "Deleting existing policy",
                verbose_level=1,
            )
            self.delete_policy(
                self.jamf_url,
                obj_id,
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
        self.env["jamfpolicydeleter_summary_result"] = {
            "summary_text": "The following policies were deleted from Jamf Pro:",
            "report_fields": ["policy"],
            "data": {"policy": self.policy_name},
        }


if __name__ == "__main__":
    PROCESSOR = JamfPolicyDeleter()
    PROCESSOR.execute_shell()
