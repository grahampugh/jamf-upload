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


class JamfComputerGroupUploaderBase(JamfUploaderBase):
    """Class for functions used to upload a computer group to Jamf"""

    def upload_computergroup(
        self,
        jamf_url,
        computergroup_name,
        computergroup_template,
        token,
        obj_id=0,
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

    def execute(self):
        """Upload a computer group"""
        self.jamf_url = self.env.get("JSS_URL")
        self.jamf_user = self.env.get("API_USERNAME")
        self.jamf_password = self.env.get("API_PASSWORD")
        self.client_id = self.env.get("CLIENT_ID")
        self.client_secret = self.env.get("CLIENT_SECRET")
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
        obj_type = "computer_group"
        obj_name = self.computergroup_name
        obj_id = self.get_api_obj_id_from_name(
            self.jamf_url,
            obj_name,
            obj_type,
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
            token=token,
            obj_id=obj_id,
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
