#!/usr/local/autopkg/python

"""
JamfPolicyUploader processor for uploading policies to Jamf Pro using AutoPkg
    by G Pugh
"""

import os
import sys
import xml.etree.ElementTree as ElementTree

from time import sleep
from autopkglib import ProcessorError  # pylint: disable=import-error

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfUploaderBase import JamfUploaderBase  # noqa: E402

__all__ = ["JamfPolicyUploader"]


class JamfPolicyUploader(JamfUploaderBase):
    description = (
        "A processor for AutoPkg that will upload a policy to a Jamf Cloud or "
        "on-prem server. Optionally, an icon can be uploaded and associated "
        "with the policy."
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
            "required": False,
            "description": "Policy name",
            "default": "",
        },
        "icon": {
            "required": False,
            "description": "Full path to Self Service icon",
            "default": "",
        },
        "policy_template": {
            "required": False,
            "description": "Full path to the XML template",
        },
        "replace_policy": {
            "required": False,
            "description": "Overwrite an existing policy if True.",
            "default": False,
        },
        "replace_icon": {
            "required": False,
            "description": "Overwrite an existing policy icon if True.",
            "default": False,
        },
        "sleep": {
            "required": False,
            "description": "Pause after running this processor for specified seconds.",
            "default": "0",
        },
    }

    output_variables = {
        "jamfpolicyuploader_summary_result": {
            "description": "Description of interesting results.",
        },
        "policy_name": {
            "description": "Jamf object name of the newly created or modified policy.",
        },
        "policy_updated": {
            "description": "Boolean - True if the policy was changed.",
        },
        "changed_policy_id": {
            "description": "Jamf object ID of the newly created or modified policy.",
        },
    }

    def prepare_policy_template(self, policy_name, policy_template):
        """prepare the policy contents"""
        # import template from file and replace any keys in the template
        if os.path.exists(policy_template):
            with open(policy_template, "r") as file:
                template_contents = file.read()
        else:
            raise ProcessorError("Template does not exist!")

        # substitute user-assignable keys
        policy_name = self.substitute_assignable_keys(policy_name)
        template_contents = self.substitute_assignable_keys(
            template_contents, xml_escape=True
        )

        self.output("Policy data:", verbose_level=2)
        self.output(template_contents, verbose_level=2)

        # write the template to temp file
        template_xml = self.write_temp_file(template_contents)
        return policy_name, template_xml

    def upload_policy(
        self,
        jamf_url,
        policy_name,
        template_xml,
        obj_id=0,
        enc_creds="",
        token="",
    ):
        """Upload policy"""

        self.output("Uploading Policy...")

        # if we find an object ID we put, if not, we post
        object_type = "policy"
        url = "{}/{}/id/{}".format(jamf_url, self.api_endpoints(object_type), obj_id)

        count = 0
        while True:
            count += 1
            self.output("Policy upload attempt {}".format(count), verbose_level=2)
            request = "PUT" if obj_id else "POST"
            r = self.curl(
                request=request,
                url=url,
                enc_creds=enc_creds,
                token=token,
                data=template_xml,
            )
            # check HTTP response
            if self.status_check(r, "Policy", policy_name, request) == "break":
                break
            if count > 5:
                self.output("WARNING: Policy upload did not succeed after 5 attempts")
                self.output("\nHTTP POST Response Code: {}".format(r.status_code))
                raise ProcessorError("ERROR: Policy upload failed ")
            if int(self.sleep) > 30:
                sleep(int(self.sleep))
            else:
                sleep(30)
        return r

    def upload_policy_icon(
        self,
        jamf_url,
        policy_name,
        policy_icon_path,
        replace_icon,
        obj_id=None,
        enc_creds="",
        token="",
    ):
        """Upload an icon to the policy that was just created"""
        # check that the policy exists.
        # Use the obj_id if we have it, or use name if we don't have it yet
        # We may need a wait loop here for new policies
        if not obj_id:
            # check for existing policy
            self.output("\nChecking '{}' on {}".format(policy_name, jamf_url))
            obj_type = "policy"
            obj_name = policy_name
            obj_id = self.get_api_obj_id_from_name(
                jamf_url,
                obj_type,
                obj_name,
                enc_creds=enc_creds,
                token=token,
            )

            if not obj_id:
                raise ProcessorError(
                    "ERROR: could not locate ID for policy '{}' so cannot upload icon".format(
                        policy_name
                    )
                )

        # Now grab the name of the existing icon using the API
        existing_icon = self.get_api_obj_value_from_id(
            jamf_url,
            "policy",
            obj_id,
            "self_service/self_service_icon/filename",
            enc_creds=enc_creds,
            token=token,
        )
        if existing_icon:
            self.output(
                "Existing policy icon is '{}'".format(existing_icon), verbose_level=1
            )
        # If the icon naame matches that we already have, don't upload again
        # unless --replace-icon is set
        policy_icon_name = os.path.basename(policy_icon_path)
        if existing_icon == policy_icon_name:
            self.output(
                "Policy icon '{}' already exists: ID {}".format(existing_icon, obj_id)
            )

        if existing_icon != policy_icon_name or replace_icon:
            object_type = "policy_icon"
            url = "{}/{}/id/{}".format(
                jamf_url, self.api_endpoints(object_type), obj_id
            )

            self.output("Uploading icon...")

            count = 0
            while True:
                count += 1
                self.output("Icon upload attempt {}".format(count), verbose_level=2)
                request = "POST"
                r = self.curl(
                    request=request,
                    url=url,
                    enc_creds=enc_creds,
                    token=token,
                    data=policy_icon_path,
                )

                # check HTTP response
                if self.status_check(r, "Icon", policy_icon_name, request) == "break":
                    break
                if count > 5:
                    print("WARNING: Icon upload did not succeed after 5 attempts")
                    print("\nHTTP POST Response Code: {}".format(r.status_code))
                    raise ProcessorError("ERROR: Icon upload failed")
                if int(self.sleep) > 30:
                    sleep(int(self.sleep))
                else:
                    sleep(30)
        else:
            self.output("Not replacing icon. Set replace_icon='True' to enforce...")
        return policy_icon_name

    def main(self):
        """Do the main thing here"""
        self.jamf_url = self.env.get("JSS_URL")
        self.jamf_user = self.env.get("API_USERNAME")
        self.jamf_password = self.env.get("API_PASSWORD")
        self.policy_name = self.env.get("policy_name")
        self.policy_template = self.env.get("policy_template")
        self.icon = self.env.get("icon")
        self.replace = self.env.get("replace_policy")
        self.sleep = self.env.get("sleep")
        # handle setting replace in overrides
        if not self.replace or self.replace == "False":
            self.replace = False
        self.replace_icon = self.env.get("replace_icon")
        # handle setting replace in overrides
        if not self.replace_icon or self.replace_icon == "False":
            self.replace_icon = False
        self.policy_updated = False

        # clear any pre-existing summary result
        if "jamfpolicyuploader_summary_result" in self.env:
            del self.env["jamfpolicyuploader_summary_result"]

        # handle files with a relative path
        if not self.policy_template.startswith("/"):
            found_template = self.get_path_to_file(self.policy_template)
            if found_template:
                self.policy_template = found_template
            else:
                raise ProcessorError(
                    f"ERROR: Policy file {self.policy_template} not found"
                )

        # we need to substitute the values in the policy name and template now to
        # account for version strings in the name
        self.policy_name, template_xml = self.prepare_policy_template(
            self.policy_name, self.policy_template
        )

        # now start the process of uploading the object
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
            self.output(
                "Policy '{}' already exists: ID {}".format(self.policy_name, obj_id)
            )
            if self.replace:
                self.output(
                    "Replacing existing policy as 'replace_policy' is set to {}".format(
                        self.replace
                    ),
                    verbose_level=1,
                )
            else:
                self.output(
                    "Not replacing existing policy. Use replace_policy='True' to enforce.",
                    verbose_level=1,
                )
                return

        # upload the policy
        r = self.upload_policy(
            self.jamf_url,
            self.policy_name,
            template_xml,
            obj_id=obj_id,
            enc_creds=send_creds,
            token=token,
        )
        self.policy_updated = True

        # Set the changed_policy_id to the returned output's ID if and only
        # if it can be determined
        try:
            changed_policy_id = ElementTree.fromstring(r.output).findtext("id")
            self.env["changed_policy_id"] = str(changed_policy_id)
        except UnboundLocalError:
            self.env["changed_policy_id"] = "UNKNOWN_POLICY_ID"

        # now upload the icon to the policy if specified in the args
        policy_icon_name = ""
        if self.icon:
            # handle files with a relative path
            if not self.icon.startswith("/"):
                found_icon = self.get_path_to_file(self.icon)
                if found_icon:
                    self.icon = found_icon
                else:
                    raise ProcessorError(
                        f"ERROR: Policy icon file {self.icon} not found"
                    )

            # get the policy_id returned from the HTTP response
            try:
                policy_id = ElementTree.fromstring(r.output).findtext("id")
                policy_icon_name = self.upload_policy_icon(
                    self.jamf_url,
                    self.policy_name,
                    self.icon,
                    self.replace_icon,
                    policy_id,
                    enc_creds=send_creds,
                    token=token,
                )
            except UnboundLocalError:
                policy_icon_name = self.upload_policy_icon(
                    self.jamf_url,
                    self.policy_name,
                    self.icon,
                    self.replace_icon,
                    enc_creds=send_creds,
                    token=token,
                )

        # output the summary
        self.env["policy_name"] = self.policy_name
        self.env["policy_updated"] = self.policy_updated
        if self.policy_updated:
            self.env["jamfpolicyuploader_summary_result"] = {
                "summary_text": "The following policies were created or updated in Jamf Pro:",
                "report_fields": ["policy", "template", "icon"],
                "data": {
                    "policy": self.policy_name,
                    "template": self.policy_template,
                    "icon": policy_icon_name,
                },
            }


if __name__ == "__main__":
    PROCESSOR = JamfPolicyUploader()
    PROCESSOR.execute_shell()
