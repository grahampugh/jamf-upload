#!/usr/local/autopkg/python

"""
JamfComputerGroupUploader processor for uploading items to Jamf Pro using AutoPkg
    by G Pugh
"""

import os
import sys

from time import sleep
from autopkglib import ProcessorError  # pylint: disable=import-error

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfUploaderBase import JamfUploaderBase  # noqa: E402

__all__ = ["JamfComputerGroupUploader"]


class JamfComputerGroupUploader(JamfUploaderBase):
    description = (
        "A processor for AutoPkg that will upload a computer group (smart or "
        "static) to a Jamf Cloud or on-prem server."
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
        "computergroup_name": {
            "required": False,
            "description": "Computer Group name",
            "default": "",
        },
        "computergroup_template": {
            "required": False,
            "description": "Full path to the XML template",
        },
        "replace_group": {
            "required": False,
            "description": "Overwrite an existing Computer Group if True.",
            "default": False,
        },
        "sleep": {
            "required": False,
            "description": "Pause after running this processor for specified seconds.",
            "default": "0",
        },
    }

    output_variables = {
        "jamfcomputergroupuploader_summary_result": {
            "description": "Description of interesting results.",
        },
    }

    def upload_computergroup(
        self,
        jamf_url,
        computergroup_name,
        computergroup_template,
        obj_id=0,
        enc_creds="",
        token="",
    ):
        """Upload computer group"""

        # import template from file and replace any keys in the template
        if os.path.exists(computergroup_template):
            with open(computergroup_template, "r") as file:
                template_contents = file.read()
        else:
            raise ProcessorError("Template does not exist!")

        # if JSS_INVENTORY_NAME is not given, make it equivalent to %NAME%.app
        # (this is to allow use of legacy JSSImporter group templates)
        try:
            self.env["JSS_INVENTORY_NAME"]
        except KeyError:
            try:
                self.env["JSS_INVENTORY_NAME"] = self.env["NAME"] + ".app"
            except KeyError:
                pass

        # substitute user-assignable keys
        template_contents = self.substitute_assignable_keys(template_contents)

        self.output("Computer Group data:", verbose_level=2)
        self.output(template_contents, verbose_level=2)

        self.output("Uploading Computer Group...")
        # write the template to temp file
        template_xml = self.write_temp_file(template_contents)

        # if we find an object ID we put, if not, we post
        object_type = "computer_group"
        url = "{}/{}/id/{}".format(jamf_url, self.api_endpoints(object_type), obj_id)

        count = 0
        while True:
            count += 1
            self.output(f"Computer Group upload attempt {count}", verbose_level=2)
            request = "PUT" if obj_id else "POST"
            r = self.curl(
                request=request,
                url=url,
                enc_creds=enc_creds,
                token=token,
                data=template_xml,
            )

            # check HTTP response
            if (
                self.status_check(r, "Computer Group", computergroup_name, request)
                == "break"
            ):
                break
            if count > 5:
                self.output(
                    "WARNING: Computer Group upload did not succeed after 5 attempts"
                )
                self.output(f"\nHTTP POST Response Code: {r.status_code}")
                raise ProcessorError("ERROR: Computer Group upload failed ")
            if int(self.sleep) > 30:
                sleep(int(self.sleep))
            else:
                sleep(30)

    def main(self):
        """Do the main thing here"""
        self.jamf_url = self.env.get("JSS_URL")
        self.jamf_user = self.env.get("API_USERNAME")
        self.jamf_password = self.env.get("API_PASSWORD")
        self.computergroup_name = self.env.get("computergroup_name")
        self.computergroup_template = self.env.get("computergroup_template")
        self.replace = self.env.get("replace_group")
        self.sleep = self.env.get("sleep")
        # handle setting replace in overrides
        if not self.replace or self.replace == "False":
            self.replace = False

        # clear any pre-existing summary result
        if "jamfcomputergroupuploader_summary_result" in self.env:
            del self.env["jamfcomputergroupuploader_summary_result"]
        group_uploaded = False

        # handle files with a relative path
        if not self.computergroup_template.startswith("/"):
            found_template = self.get_path_to_file(self.computergroup_template)
            if found_template:
                self.computergroup_template = found_template
            else:
                raise ProcessorError(
                    f"ERROR: Computer Group file {self.computergroup_template} not found"
                )

        # now start the process of uploading the object
        self.output(
            f"Checking for existing '{self.computergroup_name}' on {self.jamf_url}"
        )

        # obtain the relevant credentials
        token, send_creds, _ = self.handle_classic_auth(
            self.jamf_url, self.jamf_user, self.jamf_password
        )

        # check for existing - requires obj_name
        obj_type = "computer_group"
        obj_name = self.computergroup_name
        obj_id = self.get_api_obj_id_from_name(
            self.jamf_url,
            obj_name,
            obj_type,
            enc_creds=send_creds,
            token=token,
        )

        if obj_id:
            self.output(
                f"Computer group '{self.computergroup_name}' already exists: ID {obj_id}"
            )
            if self.replace:
                self.output(
                    "Replacing existing Computer Group as 'replace_group' is set "
                    f"to {self.replace}",
                    verbose_level=1,
                )
            else:
                self.output(
                    "Not replacing existing Computer Group. Use replace_group='True' to enforce.",
                    verbose_level=1,
                )
                return

        # upload the group
        self.upload_computergroup(
            self.jamf_url,
            self.computergroup_name,
            self.computergroup_template,
            obj_id=obj_id,
            enc_creds=send_creds,
            token=token,
        )
        group_uploaded = True

        if int(self.sleep) > 0:
            sleep(int(self.sleep))

        # output the summary
        self.env["group_uploaded"] = group_uploaded
        if group_uploaded:
            self.env["jamfcomputergroupuploader_summary_result"] = {
                "summary_text": (
                    "The following computer groups were created or updated "
                    "in Jamf Pro:"
                ),
                "report_fields": ["group", "template"],
                "data": {
                    "group": self.computergroup_name,
                    "template": self.computergroup_template,
                },
            }


if __name__ == "__main__":
    PROCESSOR = JamfComputerGroupUploader()
    PROCESSOR.execute_shell()
