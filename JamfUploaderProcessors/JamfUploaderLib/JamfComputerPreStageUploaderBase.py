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

import json
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


class JamfComputerPreStageUploaderBase(JamfUploaderBase):
    """Class for functions used to upload a generic API object to Jamf.
    Note: Individual processors in this repo for specific API endpoints should always
    be used if available"""

    def upload_prestage(
        self,
        jamf_url,
        object_type,
        template_file,
        sleep_time,
        token,
        object_name,
        obj_id=0,
    ):
        """Upload object"""

        self.output(f"Uploading {object_type}...")

        # if we find an object ID or it's an endpoint without IDs, we PUT or PATCH
        # if we're creating a new object, we POST
        if obj_id:
            url = f"{jamf_url}/{self.api_endpoints(object_type)}/{obj_id}"
        else:
            url = f"{jamf_url}/{self.api_endpoints(object_type)}"

        additional_curl_options = []
        if obj_id:
            request = "PUT"
        else:
            request = "POST"

        count = 0
        while True:
            count += 1
            self.output(f"{object_type} upload attempt {count}", verbose_level=2)
            r = self.curl(
                request=request,
                url=url,
                token=token,
                data=template_file,
                additional_curl_opts=additional_curl_options,
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
        object_type = "computer_prestage"

        jamf_url = self.env.get("JSS_URL").rstrip("/")
        jamf_user = self.env.get("API_USERNAME")
        jamf_password = self.env.get("API_PASSWORD")
        client_id = self.env.get("CLIENT_ID")
        client_secret = self.env.get("CLIENT_SECRET")
        prestage_name = self.env.get("prestage_name")
        prestage_template = self.env.get("prestage_template")
        replace_prestage = self.env.get("replace_prestage")
        sleep_time = self.env.get("sleep")
        # handle setting replace in overrides
        if not replace_prestage or replace_prestage == "False":
            replace_prestage = False
        prestage_updated = False

        # clear any pre-existing summary result
        if "jamfcomputerprestageuploader_summary_result" in self.env:
            del self.env["jamfcomputerprestageuploader_summary_result"]

        # now start the process of uploading the object
        self.output(f"Obtaining API token for {jamf_url}")

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

        # check for an existing object except for settings-related endpoints
        self.output(
            f"Checking for existing {object_type} '{prestage_name}' on {jamf_url}"
        )

        # declare name key
        namekey = self.get_namekey(object_type)
        namekey_path = self.get_namekey_path(object_type, namekey)

        # get the ID from the object bearing the supplied name
        obj_id = self.get_api_obj_id_from_name(
            jamf_url,
            prestage_name,
            object_type,
            token=token,
            filter_name=namekey,
        )

        if obj_id:
            self.output(f"{object_type} '{prestage_name}' already exists: ID {obj_id}")
            if replace_prestage:
                self.output(
                    f"Replacing existing {object_type} as replace_prestage is "
                    f"set to '{replace_prestage}'",
                    verbose_level=1,
                )
            else:
                self.output(
                    f"Not replacing existing {object_type}. Use "
                    f"replace_prestage='True' to enforce."
                )
                return

        # handle files with a relative path
        if not prestage_template.startswith("/"):
            found_template = self.get_path_to_file(prestage_template)
            if found_template:
                prestage_template = found_template
            else:
                raise ProcessorError(
                    f"ERROR: {object_type} file {prestage_template} not found"
                )

        # we need to substitute the values in the object name and template now to
        # account for version strings in the name
        elements_to_remove = []
        if obj_id:
            elements_to_remove = ["id"]

        xml_escape = False
        prestage_name, template_file = self.prepare_template(
            object_type,
            prestage_template,
            prestage_name,
            xml_escape=xml_escape,
            elements_to_remove=elements_to_remove,
            namekey_path=namekey_path,
        )

        if obj_id:
            # PreStages need to match any existing versionLock values
            self.substitute_existing_version_locks(
                jamf_url, object_type, obj_id, template_file, token
            )
        else:
            # new prestages need an id of -1
            if os.path.exists(template_file):
                with open(template_file, "r", encoding="utf-8") as file:
                    template_contents = file.read()
            else:
                raise ProcessorError("Template does not exist!")

            template_contents = self.replace_element(
                object_type, template_contents, "locationInformation/id", "-1"
            )
            template_contents = self.replace_element(
                object_type, template_contents, "purchasingInformation/id", "-1"
            )
            template_contents = self.replace_element(
                object_type, template_contents, "accountSettings/id", "-1"
            )

            with open(template_file, "w", encoding="utf-8") as file:
                file.write(template_contents)

        # upload the object
        self.upload_prestage(
            jamf_url,
            object_type,
            template_file,
            sleep_time,
            token=token,
            object_name=prestage_name,
            obj_id=obj_id,
        )
        prestage_updated = True

        # output the summary
        self.env["computer_prestage_name"] = prestage_name
        self.env["computer_prestage_updated"] = prestage_updated
        if prestage_updated:
            self.env["jamfcomputerprestageuploader_summary_result"] = {
                "summary_text": "The following computer prestages were updated in Jamf Pro:",
                "report_fields": ["computer_prestage_name", "template"],
                "data": {
                    "computer_prestage_name": prestage_name,
                    "template": prestage_template,
                },
            }
