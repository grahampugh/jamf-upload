#!/usr/local/autopkg/python

"""
JamfCategoryUploader processor for uploading a category to Jamf Pro using AutoPkg
    by G Pugh
"""

import os.path
import sys

from time import sleep
from autopkglib import ProcessorError

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfUploaderBase import JamfUploaderBase  # noqa: E402

__all__ = ["JamfCategoryUploader"]


class JamfCategoryUploader(JamfUploaderBase):
    description = (
        "A processor for AutoPkg that will upload a category to a Jamf Cloud "
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
        "category_name": {"required": False, "description": "Category", "default": ""},
        "category_priority": {
            "required": False,
            "description": "Category priority",
            "default": "10",
        },
        "replace_category": {
            "required": False,
            "description": "Overwrite an existing category if True.",
            "default": False,
        },
        "sleep": {
            "required": False,
            "description": "Pause after running this processor for specified seconds.",
            "default": "0",
        },
    }

    output_variables = {
        "category": {"description": "The created/updated category."},
        "jamfcategoryuploader_summary_result": {
            "description": "Description of interesting results.",
        },
    }

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

    def main(self):
        """Do the main thing here"""
        self.jamf_url = self.env.get("JSS_URL")
        self.jamf_user = self.env.get("API_USERNAME")
        self.jamf_password = self.env.get("API_PASSWORD")
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

        # obtain the relevant credentials
        token = self.handle_uapi_auth(self.jamf_url, self.jamf_user, self.jamf_password)

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


if __name__ == "__main__":
    PROCESSOR = JamfCategoryUploader()
    PROCESSOR.execute_shell()
