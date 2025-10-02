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


class JamfCategoryUploaderBase(JamfUploaderBase):
    """Class for functions used to upload a category to Jamf"""

    def upload_category(
        self, jamf_url, category_name, priority, token, sleep_time, obj_id=0
    ):
        """Update category metadata."""

        # build the object
        category_data = {"priority": int(priority), "name": category_name}

        self.output("Uploading category..")

        # if we find an object ID we put, if not, we post
        object_type = "category"
        if obj_id:
            url = f"{jamf_url}/{self.api_endpoints(object_type)}/{obj_id}"
        else:
            url = f"{jamf_url}/{self.api_endpoints(object_type)}"

        # write the category.
        count = 0
        category_json = self.write_json_file(jamf_url, category_data)
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
            if int(sleep_time) > 30:
                sleep(int(sleep_time))
            else:
                sleep(30)

            # output the ID of the new or updated object
        if not obj_id:
            obj_id = r.output["id"]
        if obj_id:
            self.output(f"Category '{category_name}' has ID {obj_id}")
        return obj_id

    def execute(self):
        """Upload a category"""
        jamf_url = self.env.get("JSS_URL").rstrip("/")
        jamf_user = self.env.get("API_USERNAME")
        jamf_password = self.env.get("API_PASSWORD")
        client_id = self.env.get("CLIENT_ID")
        client_secret = self.env.get("CLIENT_SECRET")
        category_name = self.env.get("category_name")
        category_priority = self.env.get("category_priority")
        replace_category = self.to_bool(self.env.get("replace_category"))
        sleep_time = self.env.get("sleep")

        # clear any pre-existing summary result
        if "jamfcategoryuploader_summary_result" in self.env:
            del self.env["jamfcategoryuploader_summary_result"]

        # we need to substitute the values in the computer group name now to
        # account for version strings in the name
        # substitute user-assignable keys
        category_name = self.substitute_assignable_keys(category_name)

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

        # now process the category
        # check for existing category
        self.output(f"Checking for existing '{category_name}' on {jamf_url}")
        obj_type = "category"
        obj_name = category_name
        obj_id = self.get_api_obj_id_from_name(
            jamf_url,
            obj_name,
            obj_type,
            token,
        )

        if obj_id:
            self.output(f"Category '{category_name}' already exists: ID {obj_id}")
            if replace_category:
                self.output(
                    "Replacing existing category as 'replace_category' is set to True",
                    verbose_level=1,
                )
            else:
                self.output(
                    "Not replacing existing category. Use replace_category='True' to enforce.",
                    verbose_level=1,
                )
                self.env["category_id"] = obj_id
                return
        else:
            self.output(f"Category '{category_name}' not found: ID {obj_id}")

        # upload the category
        category_id = self.upload_category(
            jamf_url,
            category_name,
            category_priority,
            token,
            sleep_time,
            obj_id,
        )

        # output the summary
        self.env["category"] = category_name
        self.env["category_id"] = category_id
        self.env["jamfcategoryuploader_summary_result"] = {
            "summary_text": "The following categories were created or updated in Jamf Pro:",
            "report_fields": ["category", "id", "priority"],
            "data": {
                "category": category_name,
                "id": str(obj_id),
                "priority": str(category_priority),
            },
        }
