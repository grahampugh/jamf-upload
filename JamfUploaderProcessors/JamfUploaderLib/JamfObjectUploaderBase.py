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
            if "_settings" in object_type:
                # settings-style endpoints don't use IDs
                url = f"{jamf_url}/{self.api_endpoints(object_type)}"
            else:
                url = f"{jamf_url}/{self.api_endpoints(object_type)}/id/{obj_id}"
        else:
            if obj_id:
                url = f"{jamf_url}/{self.api_endpoints(object_type)}/{obj_id}"
            else:
                url = f"{jamf_url}/{self.api_endpoints(object_type)}"

        additional_curl_options = []
        # settings-style endpoints require special options
        if (
            object_type == "volume_purchasing_location"
            or object_type == "computer_inventory_collection_settings"
        ):
            request = "PATCH"
        elif object_type == "jamf_protect_register_settings":
            request = "POST"
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
                if object_type == "failover_generate_command":
                    output = r.output
                    failover_url = output.get("failoverUrl", "")
                    self.output(f"Failover URL: {failover_url}", verbose_level=1)
                    self.env["failover_url"] = failover_url
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
        obj_id = self.env.get("object_id")
        object_name = self.env.get("object_name")
        object_type = self.env.get("object_type")
        object_template = self.env.get("object_template")
        replace_object = self.to_bool(self.env.get("replace_object"))
        elements_to_remove = self.env.get("elements_to_remove")
        element_to_replace = self.env.get("element_to_replace")
        replacement_value = self.env.get("replacement_value")
        sleep_time = self.env.get("sleep")
        object_updated = False

        # clear any pre-existing summary result
        if "jamfobjectuploader_summary_result" in self.env:
            del self.env["jamfobjectuploader_summary_result"]

        # we need to substitute the values in the computer group name now to
        # account for version strings in the name
        # substitute user-assignable keys
        if object_name:
            object_name = self.substitute_assignable_keys(object_name)

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

        # declare name key
        namekey = self.get_namekey(object_type)
        namekey_path = self.get_namekey_path(object_type, namekey)

        # check for an existing object except for settings-related endpoints
        if not any(suffix in object_type for suffix in ("_settings", "_command")):
            if obj_id:
                # if an ID has been passed into the recipe, look for object based on ID
                # rather than name
                self.output(
                    f"Checking for existing {object_type} with ID '{obj_id}' on {jamf_url}"
                )

                existing_object_name = self.get_api_obj_value_from_id(
                    jamf_url, object_type, obj_id, obj_path=namekey_path, token=token
                )
                if existing_object_name:
                    self.output(
                        f"{object_type} '{obj_id}' already exists ('{existing_object_name}')"
                    )
                    if replace_object:
                        self.output(
                            f"Replacing existing {object_type} as replace_object is "
                            "set to True",
                            verbose_level=1,
                        )
                    else:
                        self.output(
                            f"Not replacing existing {object_type}. Use "
                            "replace_object='True' to enforce."
                        )
                        return
            else:
                # normal operation - look for object of the same name
                self.output(
                    f"Checking for existing {object_type} '{object_name}' on {jamf_url}"
                )

                # get the ID from the object bearing the supplied name
                obj_id = self.get_api_obj_id_from_name(
                    jamf_url,
                    object_name,
                    object_type,
                    token=token,
                    filter_name=namekey,
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

        if "_command" not in object_type:
            # handle files with a relative path
            if not object_template.startswith("/"):
                found_template = self.get_path_to_file(object_template)
                if found_template:
                    object_template = found_template
                else:
                    raise ProcessorError(
                        f"ERROR: {object_type} file {object_template} not found"
                    )

        else:
            object_name = ""
            obj_id = 0
            namekey_path = ""

        # we need to substitute the values in the object name and template now to
        # account for version strings in the name
        if "JSSResource" in self.api_endpoints(object_type):
            xml_escape = True
        else:
            xml_escape = False
        if "_settings" in object_type:
            _, template_file = self.prepare_template(
                jamf_url,
                object_type,
                object_template,
                object_name=None,
                xml_escape=xml_escape,
                elements_to_remove=elements_to_remove,
                element_to_replace=element_to_replace,
                replacement_value=replacement_value,
            )
        elif "_command" in object_type:
            template_file = ""
        else:
            object_name, template_file = self.prepare_template(
                jamf_url,
                object_type,
                object_template,
                object_name,
                xml_escape=xml_escape,
                elements_to_remove=elements_to_remove,
                element_to_replace=element_to_replace,
                replacement_value=replacement_value,
                namekey_path=namekey_path,
            )

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
        self.env["object_name"] = str(object_name)
        self.env["object_type"] = object_type
        self.env["object_updated"] = object_updated
        if object_updated:
            self.env["jamfobjectuploader_summary_result"] = {
                "summary_text": "The following objects were updated in Jamf Pro:",
                "report_fields": ["object_name", "object_type", "template"],
                "data": {
                    "object_type": object_type,
                    "object_name": str(object_name),
                    "template": object_template,
                },
            }
