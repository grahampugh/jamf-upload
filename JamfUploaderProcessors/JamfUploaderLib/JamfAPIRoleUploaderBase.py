#!/usr/local/autopkg/python
# pylint: disable=invalid-name

"""
Copyright 2025 Graham Pugh

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


class JamfAPIRoleUploaderBase(JamfUploaderBase):
    """Class for functions used to upload an API Role object to Jamf."""

    def upload_object(
        self,
        jamf_url,
        object_name,
        object_type,
        template_file,
        sleep_time,
        token,
        obj_id=0,
    ):
        """Upload object"""

        self.output(f"Uploading {object_type}...")

        # if we find an object ID we put, if not, we post
        if obj_id:
            url = f"{jamf_url}/{self.api_endpoints(object_type)}/{obj_id}"
        else:
            url = f"{jamf_url}/{self.api_endpoints(object_type)}"

        count = 0
        while True:
            count += 1
            self.output(f"{object_type} upload attempt {count}", verbose_level=2)
            request = "PUT" if obj_id else "POST"
            r = self.curl(
                request=request,
                url=url,
                token=token,
                data=template_file,
            )
            # check HTTP response
            if self.status_check(r, object_type, object_name, request) == "break":
                break
            if count > 5:
                self.output(
                    f"WARNING: {object_type} upload did not succeed after 5 attempts"
                )
                self.output(f"\nHTTP POST Response Code: {r.status_code}")
                raise ProcessorError(f"ERROR: {object_type} upload failed ")
            if int(sleep_time) > 30:
                sleep(int(sleep_time))
            else:
                sleep(30)
        return r

    def execute(self):
        """Upload an API object"""
        jamf_url = self.env.get("JSS_URL").rstrip("/")
        jamf_user = self.env.get("API_USERNAME")
        jamf_password = self.env.get("API_PASSWORD")
        client_id = self.env.get("CLIENT_ID")
        client_secret = self.env.get("CLIENT_SECRET")
        object_name = self.env.get("api_role_name")
        object_template = self.env.get("api_role_template")
        replace_object = self.to_bool(self.env.get("replace_api_role"))
        sleep_time = self.env.get("sleep")
        object_updated = False

        object_type = "api_role"

        # clear any pre-existing summary result
        if "jamfapiroleuploader_summary_result" in self.env:
            del self.env["jamfapiroleuploader_summary_result"]

        # handle files with a relative path
        if not object_template.startswith("/"):
            found_template = self.get_path_to_file(object_template)
            if found_template:
                object_template = found_template
            else:
                raise ProcessorError(f"ERROR: Policy file {object_template} not found")

        # we need to substitute the values in the object name and template now to
        # account for version strings in the name
        object_name, template_file = self.prepare_template(
            jamf_url, object_type, object_template, object_name
        )

        # now start the process of uploading the object
        self.output(f"Checking for existing '{object_name}' on {jamf_url}")

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

        # Check for existing item
        self.output(f"Checking for existing '{object_name}' on {jamf_url}")

        obj_id = self.get_api_obj_id_from_name(
            jamf_url, object_name, object_type, token=token, filter_name="displayName"
        )

        if obj_id:
            self.output(f"{object_type} '{object_name}' already exists: ID {obj_id}")
            if replace_object:
                self.output(
                    f"Replacing existing {object_type} as replace_object is set to True",
                    verbose_level=1,
                )
            else:
                self.output(
                    f"Not replacing existing {object_type}. Use "
                    "replace_object='True' to enforce."
                )
                return

        # upload the object
        self.upload_object(
            jamf_url,
            object_name,
            object_type,
            template_file,
            sleep_time,
            token=token,
            obj_id=obj_id,
        )
        object_updated = True

        # output the summary
        self.env["api_role_name"] = object_name
        self.env["api_role_updated"] = object_updated
        if object_updated:
            self.env["jamfapiroleuploader_summary_result"] = {
                "summary_text": "The following objects were updated in Jamf Pro:",
                "report_fields": ["api_role_name", "template"],
                "data": {
                    "api_role_name": object_name,
                    "template": object_template,
                },
            }
