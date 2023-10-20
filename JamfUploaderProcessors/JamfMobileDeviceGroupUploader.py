#!/usr/local/autopkg/python

"""
JamfMobileDeviceGroupUploader processor for uploading items to Jamf Pro using AutoPkg
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

__all__ = ["JamfMobileDeviceGroupUploader"]


class JamfMobileDeviceGroupUploader(JamfUploaderBase):
    description = (
        "A processor for AutoPkg that will upload a mobile device group (smart or "
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
            "required": False,
            "description": "Username of account with appropriate access to "
            "jss, optionally set as a key in the com.github.autopkg "
            "preference file.",
        },
        "API_PASSWORD": {
            "required": False,
            "description": "Password of api user, optionally set as a key in "
            "the com.github.autopkg preference file.",
        },
        "CLIENT_ID": {
            "required": False,
            "description": "Client ID with access to "
            "jss, optionally set as a key in the com.github.autopkg "
            "preference file.",
        },
        "CLIENT_SECRET": {
            "required": False,
            "description": "Secret associated with the Client ID, optionally set as a key in "
            "the com.github.autopkg preference file.",
        },
        "mobiledevicegroup_name": {
            "required": False,
            "description": "Mobile Device Group name",
            "default": "",
        },
        "mobiledevicegroup_template": {
            "required": False,
            "description": "Full path to the XML template",
        },
        "replace_group": {
            "required": False,
            "description": "Overwrite an existing Mobile Device Group if True.",
            "default": False,
        },
        "sleep": {
            "required": False,
            "description": "Pause after running this processor for specified seconds.",
            "default": "0",
        },
    }

    output_variables = {
        "JamfMobileDeviceGroupUploader_summary_result": {
            "description": "Description of interesting results.",
        },
    }

    def upload_mobiledevicegroup(
        self,
        jamf_url,
        mobiledevicegroup_name,
        mobiledevicegroup_template,
        token,
        obj_id=0,
    ):
        """Upload Mobile Device Group"""

        # import template from file and replace any keys in the template
        if os.path.exists(mobiledevicegroup_template):
            with open(mobiledevicegroup_template, "r") as file:
                template_contents = file.read()
        else:
            raise ProcessorError("Template does not exist!")

        # substitute user-assignable keys
        template_contents = self.substitute_assignable_keys(template_contents)

        self.output("Mobile Device Group data:", verbose_level=2)
        self.output(template_contents, verbose_level=2)

        self.output("Uploading Mobile Device Group...")
        # write the template to temp file
        template_xml = self.write_temp_file(template_contents)

        # if we find an object ID we put, if not, we post
        object_type = "mobile_device_group"
        url = "{}/{}/id/{}".format(jamf_url, self.api_endpoints(object_type), obj_id)

        count = 0
        while True:
            count += 1
            self.output(f"Mobile Device Group upload attempt {count}", verbose_level=2)
            request = "PUT" if obj_id else "POST"
            r = self.curl(
                request=request,
                url=url,
                token=token,
                data=template_xml,
            )

            # check HTTP response
            if (
                self.status_check(
                    r, "Mobile Device Group", mobiledevicegroup_name, request
                )
                == "break"
            ):
                break
            if count > 5:
                self.output(
                    "WARNING: Mobile Device Group upload did not succeed after 5 attempts"
                )
                self.output(f"\nHTTP POST Response Code: {r.status_code}")
                raise ProcessorError("ERROR: Mobile Device Group upload failed ")
            if int(self.sleep) > 30:
                sleep(int(self.sleep))
            else:
                sleep(30)

    def main(self):
        """Do the main thing here"""
        self.jamf_url = self.env.get("JSS_URL")
        self.jamf_user = self.env.get("API_USERNAME")
        self.jamf_password = self.env.get("API_PASSWORD")
        self.client_id = self.env.get("CLIENT_ID")
        self.client_secret = self.env.get("CLIENT_SECRET")
        self.mobiledevicegroup_name = self.env.get("mobiledevicegroup_name")
        self.mobiledevicegroup_template = self.env.get("mobiledevicegroup_template")
        self.replace = self.env.get("replace_group")
        self.sleep = self.env.get("sleep")
        # handle setting replace in overrides
        if not self.replace or self.replace == "False":
            self.replace = False

        # clear any pre-existing summary result
        if "JamfMobileDeviceGroupUploader_summary_result" in self.env:
            del self.env["JamfMobileDeviceGroupUploader_summary_result"]
        group_uploaded = False

        # handle files with a relative path
        if not self.mobiledevicegroup_template.startswith("/"):
            found_template = self.get_path_to_file(self.mobiledevicegroup_template)
            if found_template:
                self.mobiledevicegroup_template = found_template
            else:
                raise ProcessorError(
                    f"ERROR: Mobile Device Group file {self.mobiledevicegroup_template} not found"
                )

        # now start the process of uploading the object
        self.output(
            f"Checking for existing '{self.mobiledevicegroup_name}' on {self.jamf_url}"
        )

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
        obj_type = "mobile_device_group"
        obj_name = self.mobiledevicegroup_name
        obj_id = self.get_api_obj_id_from_name(
            self.jamf_url,
            obj_name,
            obj_type,
            token=token,
        )

        if obj_id:
            self.output(
                f"Mobile Device Group '{self.mobiledevicegroup_name}' already exists: ID {obj_id}"
            )
            if self.replace:
                self.output(
                    "Replacing existing Mobile Device Group as 'replace_group' is set "
                    f"to {self.replace}",
                    verbose_level=1,
                )
            else:
                self.output(
                    "Not replacing existing Mobile Device Group. "
                    "Use replace_group='True' to enforce.",
                    verbose_level=1,
                )
                return

        # upload the group
        self.upload_mobiledevicegroup(
            self.jamf_url,
            self.mobiledevicegroup_name,
            self.mobiledevicegroup_template,
            token=token,
            obj_id=obj_id,
        )
        group_uploaded = True

        if int(self.sleep) > 0:
            sleep(int(self.sleep))

        # output the summary
        self.env["group_uploaded"] = group_uploaded
        if group_uploaded:
            self.env["JamfMobileDeviceGroupUploader_summary_result"] = {
                "summary_text": (
                    "The following Mobile Device Groups were created or updated "
                    "in Jamf Pro:"
                ),
                "report_fields": ["group", "template"],
                "data": {
                    "group": self.mobiledevicegroup_name,
                    "template": self.mobiledevicegroup_template,
                },
            }


if __name__ == "__main__":
    PROCESSOR = JamfMobileDeviceGroupUploader()
    PROCESSOR.execute_shell()
