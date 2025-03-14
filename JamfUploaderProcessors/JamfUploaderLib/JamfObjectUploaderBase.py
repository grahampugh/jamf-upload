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


class JamfObjectUploaderBase(JamfUploaderBase):
    """Class for functions used to upload a generic API object to Jamf.
    Note: Individual processors in this repo for specific API endpoints should always
    be used if available"""

    def upload_object(
        self,
        jamf_url,
        object_type,
        template_file,
        sleep_time,
        token,
        object_name=None,
        obj_id=0,
    ):
        """Upload object"""

        self.output(f"Uploading {object_type}...")

        # if we find an object ID or it's an endpoint without IDs, we PUT or PATCH
        # if we're creating a new object, we POST
        if "JSSResource" in self.api_endpoints(object_type):
            # do XML stuff
            url = f"{jamf_url}/{self.api_endpoints(object_type)}/id/{obj_id}"
        else:
            if obj_id:
                url = f"{jamf_url}/{self.api_endpoints(object_type)}/{obj_id}"
            else:
                url = f"{jamf_url}/{self.api_endpoints(object_type)}"

        additional_curl_options = []
        # PATCH endpoints require special options
        if object_type == "volume_purchasing_location":
            request = "PATCH"
            additional_curl_options = [
                "--header",
                "Content-type: application/merge-patch+json",
            ]
        elif object_type == "computer_inventory_collection_settings":
            request = "PATCH"
            additional_curl_options = [
                "--header",
                "Content-type: application/json",
            ]
        elif obj_id or "_settings" in object_type:
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
        jamf_url = self.env.get("JSS_URL").rstrip("/")
        jamf_user = self.env.get("API_USERNAME")
        jamf_password = self.env.get("API_PASSWORD")
        client_id = self.env.get("CLIENT_ID")
        client_secret = self.env.get("CLIENT_SECRET")
        object_name = self.env.get("object_name")
        object_type = self.env.get("object_type")
        object_template = self.env.get("object_template")
        replace_object = self.env.get("replace_object")
        elements_to_remove = self.env.get("elements_to_remove")
        sleep_time = self.env.get("sleep")
        # handle setting replace in overrides
        if not replace_object or replace_object == "False":
            replace_object = False
        object_updated = False

        # clear any pre-existing summary result
        if "jamfapiobjectuploader_summary_result" in self.env:
            del self.env["jamfapiobjectuploader_summary_result"]

        # handle files with a relative path
        if not object_template.startswith("/"):
            found_template = self.get_path_to_file(object_template)
            if found_template:
                object_template = found_template
            else:
                raise ProcessorError(
                    f"ERROR: {object_type} file {object_template} not found"
                )

        # we need to substitute the values in the object name and template now to
        # account for version strings in the name
        if "JSSResource" in self.api_endpoints(object_type):
            xml_escape = True
        else:
            xml_escape = False
        if "_settigns" in object_type:
            _, template_file = self.prepare_template(
                object_type,
                object_template,
                object_name=None,
                xml_escape=xml_escape,
                elements_to_remove=elements_to_remove,
            )
        else:
            object_name, template_file = self.prepare_template(
                object_type,
                object_template,
                object_name,
                xml_escape=xml_escape,
                elements_to_remove=elements_to_remove,
            )

        # now start the process of uploading the object
        self.output(f"Obtaining API token for {jamf_url}")
        # get token using oauth or basic auth depending on the credentials given
        if jamf_url and client_id and client_secret:
            token = self.handle_oauth(jamf_url, client_id, client_secret)
        elif jamf_url:
            token = self.handle_api_auth(jamf_url, jamf_user, jamf_password)
        else:
            raise ProcessorError("ERROR: Jamf Pro URL not supplied")
        # check for an existing object except for settings-related endpoints
        if "_settings" not in object_type:
            self.output(f"Checking for existing '{object_name}' on {jamf_url}")

            # declare name key
            name_key = "name"
            if (
                object_type == "computer_prestage"
                or object_type == "mobile_device_prestage"
                or object_type == "enrollment_customization"
            ):
                name_key = "displayName"

            obj_id = self.get_api_obj_id_from_name(
                jamf_url, object_name, object_type, token=token, filter_name=name_key
            )

            if obj_id:
                self.output(
                    f"{object_type} '{object_name}' already exists: ID {obj_id}"
                )
                if replace_object:
                    self.output(
                        f"Replacing existing {object_type} as replace_object is "
                        f"set to '{replace_object}'",
                        verbose_level=1,
                    )
                else:
                    self.output(
                        f"Not replacing existing {object_type}. Use "
                        f"replace_object='True' to enforce."
                    )
                    return
        else:
            object_name = ""
            obj_id = 0

        # upload the object
        self.upload_object(
            jamf_url,
            object_type,
            template_file,
            sleep_time,
            token=token,
            object_name=object_name,
            obj_id=obj_id,
        )
        object_updated = True

        # output the summary
        self.env["object_name"] = object_name
        self.env["object_type"] = object_type
        self.env["object_updated"] = object_updated
        if object_updated:
            self.env["jamfobjectuploader_summary_result"] = {
                "summary_text": "The following objects were updated in Jamf Pro:",
                "report_fields": ["object_name", "object_type", "template"],
                "data": {
                    "object_type": object_type,
                    "object_name": object_name,
                    "template": object_template,
                },
            }
