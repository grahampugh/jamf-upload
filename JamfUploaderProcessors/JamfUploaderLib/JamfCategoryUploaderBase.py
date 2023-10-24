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


class JamfCategoryUploaderBase(JamfUploaderBase):
    """Class for functions used to upload a category to Jamf"""

    def upload_category(self, jamf_url, category_name, priority, token, obj_id=0):
        """Update category metadata."""

        # build the object
        category_data = {"priority": int(priority), "name": category_name}

        self.output("Uploading category..")

        # if we find an object ID we put, if not, we post
        object_type = "category"
        if obj_id:
            url = "{}/{}/{}".format(jamf_url, self.api_endpoints(object_type), obj_id)
        else:
            url = "{}/{}".format(jamf_url, self.api_endpoints(object_type))

        # write the category.
        count = 0
        category_json = self.write_json_file(category_data)
        while True:
            count += 1
            self.output(
                f"Category upload attempt {count}",
                verbose_level=2,
            )
            request = "PUT" if obj_id else "POST"
            r = self.curl(request=request, url=url, token=token, data=category_json)

            # check HTTP response
            if self.status_check(r, "Category", category_name, request) == "break":
                break
            if count > 5:
                self.output("ERROR: Category creation did not succeed after 5 attempts")
                self.output(f"\nHTTP POST Response Code: {r.status_code}")
                raise ProcessorError("ERROR: Category upload failed ")
            if int(self.sleep) > 30:
                sleep(int(self.sleep))
            else:
                sleep(30)

    def execute(self):
        """Upload a category"""
        self.jamf_url = self.env.get("JSS_URL")
        self.jamf_user = self.env.get("API_USERNAME")
        self.jamf_password = self.env.get("API_PASSWORD")
        self.client_id = self.env.get("CLIENT_ID")
        self.client_secret = self.env.get("CLIENT_SECRET")
        self.category_name = self.env.get("category_name")
        self.category_priority = self.env.get("category_priority")
        self.replace = self.env.get("replace_category")
        self.sleep = self.env.get("sleep")
        # handle setting replace_pkg in overrides
        if not self.replace or self.replace == "False":
            self.replace = False

        # clear any pre-existing summary result
        if "jamfcategoryuploader_summary_result" in self.env:
            del self.env["jamfcategoryuploader_summary_result"]

        # get token using oauth or basic auth depending on the credentials given
        if self.jamf_url and self.client_id and self.client_secret:
            token = self.handle_oauth(self.jamf_url, self.client_id, self.client_secret)
        elif self.jamf_url and self.jamf_user and self.jamf_password:
            token = self.handle_api_auth(
                self.jamf_url, self.jamf_user, self.jamf_password
            )
        else:
            raise ProcessorError("ERROR: Credentials not supplied")

        # now process the category
        # check for existing category
        self.output(f"Checking for existing '{self.category_name}' on {self.jamf_url}")
        obj_type = "category"
        obj_name = self.category_name
        obj_id = self.get_uapi_obj_id_from_name(
            self.jamf_url,
            obj_type,
            obj_name,
            token,
        )

        if obj_id:
            self.output(f"Category '{self.category_name}' already exists: ID {obj_id}")
            if self.replace:
                self.output(
                    f"Replacing existing category as 'replace_category' is set to {self.replace}",
                    verbose_level=1,
                )
            else:
                self.output(
                    "Not replacing existing category. Use replace_category='True' to enforce.",
                    verbose_level=1,
                )
                return
        else:
            self.output(f"Category '{self.category_name}' not found: ID {obj_id}")

        # upload the category
        self.upload_category(
            self.jamf_url,
            self.category_name,
            self.category_priority,
            token,
            obj_id,
        )

        # output the summary
        self.env["category"] = self.category_name
        self.env["jamfcategoryuploader_summary_result"] = {
            "summary_text": "The following categories were created or updated in Jamf Pro:",
            "report_fields": ["category", "priority"],
            "data": {
                "category": self.category_name,
                "priority": str(self.category_priority),
            },
        }
