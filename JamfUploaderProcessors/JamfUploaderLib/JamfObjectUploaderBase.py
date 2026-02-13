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
        api_type,
        object_type,
        object_template,
        sleep_time,
        token,
        max_tries,
        object_name=None,
        object_id=0,
    ):
        """Upload object"""

        self.output(f"Uploading {object_type}...")

        # if we find an object ID or it's an endpoint without IDs, we PUT or PATCH
        # if we're creating a new object, we POST

        if api_type == "classic":
            if "_settings" in object_type:
                # settings-style endpoints don't use IDs
                url = f"{jamf_url}/{self.api_endpoints(object_type)}"
            else:
                url = f"{jamf_url}/{self.api_endpoints(object_type)}/id/{object_id}"
        elif api_type == "jpapi" or api_type == "platform":
            if (
                object_type
                in ("blueprint_deploy_command", "blueprint_undeploy_command")
                and object_id
            ):
                url = f"{jamf_url}/{self.api_endpoints(object_type, uuid=object_id)}"
            elif object_id:
                url = f"{jamf_url}/{self.api_endpoints(object_type)}/{object_id}"
            else:
                url = f"{jamf_url}/{self.api_endpoints(object_type)}"
        else:
            raise ProcessorError(f"ERROR: API type {api_type} not supported")

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
        elif object_id and object_type == "blueprint":
            request = "PATCH"
        elif object_id and object_type in (
            "blueprint_deploy_command",
            "blueprint_undeploy_command",
        ):
            request = "POST"
        elif object_type == "cloud_distribution_point":
            get_r = self.curl(
                api_type=api_type,
                request="GET",
                url=url,
                token=token,
            )
            if get_r.status_code == 200 and isinstance(get_r.output, dict):
                cdn_type = get_r.output.get("cdnType")
                if cdn_type and cdn_type != "NONE":
                    request = "PATCH"
                else:
                    request = "POST"
            else:
                request = "POST"
        elif object_id or "_settings" in object_type:
            request = "PUT"
        else:
            request = "POST"

        # temp output template file path
        # self.output(
        #     f"Prepared {object_type} template file '{template_file}' for upload",
        #     verbose_level=2,
        # )

        count = 0
        while True:
            count += 1
            self.output(f"{object_type} upload attempt {count}", verbose_level=2)
            r = self.curl(
                api_type=api_type,
                request=request,
                url=url,
                token=token,
                data=object_template,
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
            if count >= max_tries:
                self.output(
                    f"WARNING: {object_type} upload did not succeed after {max_tries} attempts"
                )
                self.output(f"\nHTTP POST Response Code: {r.status_code}")
                raise ProcessorError(f"ERROR: {object_type} upload failed ")
            if int(sleep_time) > 10:
                sleep(int(sleep_time))
            else:
                sleep(10)
        return r

    def execute(self):
        """Upload an API object"""
        jamf_url = self.env.get("JSS_URL").rstrip("/")
        jamf_user = self.env.get("API_USERNAME")
        jamf_password = self.env.get("API_PASSWORD")
        client_id = self.env.get("CLIENT_ID")
        client_secret = self.env.get("CLIENT_SECRET")
        object_id = self.env.get("object_id")
        object_name = self.env.get("object_name")
        object_type = self.env.get("object_type")
        object_template = self.env.get("object_template")
        replace_object = self.to_bool(self.env.get("replace_object"))
        elements_to_remove = self.env.get("elements_to_remove")
        element_to_replace = self.env.get("element_to_replace")
        replacement_value = self.env.get("replacement_value")
        sleep_time = self.env.get("sleep")
        max_tries = self.env.get("max_tries")

        # verify that max_tries is an integer greater than zero and less than 10
        try:
            max_tries = int(max_tries)
            if max_tries < 1 or max_tries > 10:
                raise ValueError
        except (ValueError, TypeError):
            max_tries = 5

        object_updated = False

        # clear any pre-existing summary result
        if "jamfobjectuploader_summary_result" in self.env:
            del self.env["jamfobjectuploader_summary_result"]

        # get api type
        api_type = self.api_type(object_type)

        # we need to substitute the values in the computer group name now to
        # account for version strings in the name
        # substitute user-assignable keys
        if object_name:
            object_name = self.substitute_assignable_keys(object_name)

        # now start the process of uploading the object
        self.output(f"Obtaining API token for {jamf_url}")

        # get token using oauth or basic auth depending on the credentials given
        if jamf_url:
            # determine which token we need based on object type.
            # classic and jpapi types use handle_api_auth,
            # platform type uses handle_platform_api_auth
            api_type = self.api_type(object_type)
            self.output(f"API type for {object_type} is {api_type}", verbose_level=3)
            if api_type == "platform":
                token = self.handle_platform_api_auth(
                    jamf_url,
                    client_id=client_id,
                    client_secret=client_secret,
                )
            else:
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

        # check for an existing object except for settings-related endpoints and cloud_distribution_point
        if (
            not any(suffix in object_type for suffix in ("_settings", "_command"))
            and object_type != "cloud_distribution_point"
        ):
            if object_id:
                # if an ID has been passed into the recipe, look for object based on ID
                # rather than name
                self.output(
                    f"Checking for existing {object_type} with ID '{object_id}' on {jamf_url}"
                )

                existing_object_name = self.get_api_object_value_from_id(
                    jamf_url,
                    object_type=object_type,
                    object_id=object_id,
                    object_path=namekey_path,
                    token=token,
                )
                if existing_object_name:
                    self.output(
                        f"{object_type} '{object_id}' already exists ('{existing_object_name}')"
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
                # the group object type has a different ID key
                id_key = self.get_idkey(object_type)

                object_id = self.get_api_object_id_from_name(
                    jamf_url,
                    object_type=object_type,
                    object_name=object_name,
                    token=token,
                    filter_name=namekey,
                    id_key=id_key,
                )

                if object_id:
                    self.output(
                        f"{object_type} '{object_name}' already exists: ID {object_id}"
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
            namekey_path = ""
            if object_type not in (
                "blueprint_deploy_command",
                "blueprint_undeploy_command",
            ):
                object_id = 0

        # we need to substitute the values in the object name and template now to
        # account for version strings in the name
        if api_type == "classic":
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
            api_type=api_type,
            object_type=object_type,
            object_template=template_file,
            sleep_time=sleep_time,
            token=token,
            max_tries=max_tries,
            object_name=object_name,
            object_id=object_id,
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
