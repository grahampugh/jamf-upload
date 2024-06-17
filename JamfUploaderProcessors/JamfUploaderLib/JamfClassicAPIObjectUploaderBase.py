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


class JamfClassicAPIObjectUploaderBase(JamfUploaderBase):
    """Class for functions used to upload a generic API object to Jamf"""

    def prepare_template(self, object_name, object_template):
        """prepare the object contents"""
        # import template from file and replace any keys in the template
        if os.path.exists(object_template):
            with open(object_template, "r") as file:
                template_contents = file.read()
        else:
            raise ProcessorError("Template does not exist!")

        # substitute user-assignable keys
        object_name = self.substitute_assignable_keys(object_name)
        template_contents = self.substitute_assignable_keys(
            template_contents, xml_escape=True
        )

        self.output("object data:", verbose_level=2)
        self.output(template_contents, verbose_level=2)

        # write the template to temp file
        template_xml = self.write_temp_file(template_contents)
        return object_name, template_xml

    def upload_object(
        self,
        jamf_url,
        object_name,
        object_type,
        template_xml,
        token,
        obj_id=0,
    ):
        """Upload object"""

        self.output(f"Uploading {object_type}...")

        # if we find an object ID we put, if not, we post
        url = "{}/{}/id/{}".format(jamf_url, self.api_endpoints(object_type), obj_id)

        count = 0
        while True:
            count += 1
            self.output(
                "{} upload attempt {}".format(object_type, count), verbose_level=2
            )
            request = "PUT" if obj_id else "POST"
            r = self.curl(
                request=request,
                url=url,
                token=token,
                data=template_xml,
            )
            # check HTTP response
            if self.status_check(r, object_type, object_name, request) == "break":
                break
            if count > 5:
                self.output(
                    f"WARNING: {object_type} upload did not succeed after 5 attempts"
                )
                self.output("\nHTTP POST Response Code: {}".format(r.status_code))
                raise ProcessorError(f"ERROR: {object_type} upload failed ")
            if int(self.sleep) > 30:
                sleep(int(self.sleep))
            else:
                sleep(30)
        return r

    def execute(self):
        """Upload an API object"""
        self.jamf_url = self.env.get("JSS_URL")
        self.jamf_user = self.env.get("API_USERNAME")
        self.jamf_password = self.env.get("API_PASSWORD")
        self.client_id = self.env.get("CLIENT_ID")
        self.client_secret = self.env.get("CLIENT_SECRET")
        self.object_name = self.env.get("object_name")
        self.object_type = self.env.get("object_type")
        self.object_template = self.env.get("object_template")
        self.replace = self.env.get("replace_object")
        self.sleep = self.env.get("sleep")
        # handle setting replace in overrides
        if not self.replace or self.replace == "False":
            self.replace = False
        self.object_updated = False

        # clear any pre-existing summary result
        if "jamfclassicapiobjectuploader_summary_result" in self.env:
            del self.env["jamfclassicapiobjectuploader_summary_result"]

        # handle files with a relative path
        if not self.object_template.startswith("/"):
            found_template = self.get_path_to_file(self.object_template)
            if found_template:
                self.object_template = found_template
            else:
                raise ProcessorError(
                    f"ERROR: Policy file {self.object_template} not found"
                )

        # we need to substitute the values in the object name and template now to
        # account for version strings in the name
        self.object_name, template_xml = self.prepare_template(
            self.object_name, self.object_template
        )

        # now start the process of uploading the object
        self.output(f"Checking for existing '{self.object_name}' on {self.jamf_url}")

        # get token using oauth or basic auth depending on the credentials given
        if self.jamf_url and self.client_id and self.client_secret:
            token = self.handle_oauth(self.jamf_url, self.client_id, self.client_secret)
        elif self.jamf_url and self.jamf_user and self.jamf_password:
            token = self.handle_api_auth(
                self.jamf_url, self.jamf_user, self.jamf_password
            )
        else:
            raise ProcessorError("ERROR: Credentials not supplied")

        # Check for existing item
        self.output(f"Checking for existing '{self.object_name}' on {self.jamf_url}")

        obj_id = self.get_api_obj_id_from_name(
            self.jamf_url,
            self.object_name,
            self.object_type,
            token=token,
        )

        if obj_id:
            self.output(
                f"{self.object_type} '{self.object_name}' already exists: ID {obj_id}"
            )
            if self.replace:
                self.output(
                    f"Replacing existing {self.object_type} as replace_object is "
                    f"set to '{self.replace}'",
                    verbose_level=1,
                )
            else:
                self.output(
                    f"Not replacing existing {self.object_type}. Use "
                    f"replace_object='True' to enforce."
                )
                return

        # upload the object
        self.upload_object(
            self.jamf_url,
            self.object_name,
            self.object_type,
            template_xml,
            token=token,
            obj_id=obj_id,
        )
        self.object_updated = True

        # output the summary
        self.env["object_name"] = self.object_name
        self.env["object_type"] = self.object_type
        self.env["object_updated"] = self.object_updated
        if self.object_updated:
            self.env["jamfclassicapiobjectuploader_summary_result"] = {
                "summary_text": "The following objects were updated in Jamf Pro:",
                "report_fields": [self.object_type, "template"],
                "data": {
                    self.object_type: self.object_name,
                    "template": self.object_template,
                },
            }
