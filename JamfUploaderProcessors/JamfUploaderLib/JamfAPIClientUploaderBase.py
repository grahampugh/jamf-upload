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


class JamfAPIClientUploaderBase(JamfUploaderBase):
    """Class for functions used to upload a script to Jamf"""

    def upload_object(
        self,
        jamf_url,
        object_name,
        object_type,
        object_data,
        token,
        sleep_time,
        obj_id=0,
    ):
        """Update API Client metadata."""

        template_file = self.write_json_file(jamf_url, object_data)

        self.output(f"Uploading {object_type}...")

        # if we find an object ID we put, if not, we post
        if obj_id:
            url = f"{jamf_url}/{self.api_endpoints(object_type)}/{obj_id}"
        else:
            url = f"{jamf_url}/{self.api_endpoints(object_type)}"

        count = 0
        while True:
            count += 1
            self.output(
                f"{object_type} upload attempt {count}",
                verbose_level=2,
            )
            request = "PUT" if obj_id else "POST"
            r = self.curl(request=request, url=url, token=token, data=template_file)
            # check HTTP response
            if self.status_check(r, object_type, object_name, request) == "break":
                break
            if count > 5:
                self.output(f"{object_type} upload did not succeed after 5 attempts")
                self.output(f"\nHTTP POST Response Code: {r.status_code}")
                raise ProcessorError(f"ERROR: {object_type} upload failed ")
            if int(sleep_time) > 30:
                sleep(int(sleep_time))
            else:
                sleep(30)
        return r

    def get_api_client_credentials(
        self, jamf_url, object_type, token, sleep_time, obj_id
    ):
        """Generate the API Client Credentials"""

        self.output("Getting API Client credentials...")

        url = (
            f"{jamf_url}/{self.api_endpoints(object_type)}/{obj_id}/client-credentials"
        )

        api_client_id = ""
        api_client_secret = ""

        count = 0
        while True:
            count += 1
            self.output(
                f"{object_type} upload attempt {count}",
                verbose_level=2,
            )
            request = "POST"
            r = self.curl(request=request, url=url, token=token)
            # check HTTP response
            if (
                self.status_check(r, object_type, "client secret request", request)
                == "break"
            ):
                break
            if count > 5:
                self.output(f"{object_type} upload did not succeed after 5 attempts")
                self.output(f"\nHTTP POST Response Code: {r.status_code}")
                raise ProcessorError(f"ERROR: {object_type} upload failed ")
            if int(sleep_time) > 30:
                sleep(int(sleep_time))
            else:
                sleep(30)

        # get the Client ID and Secret
        if r.status_code < 300:
            # Parse response as json
            obj_content = r.output
            self.output(
                obj_content,
                verbose_level=3,
            )
            api_client_id = obj_content["clientId"]
            api_client_secret = obj_content["clientSecret"]
        else:
            raise ProcessorError("ERROR: Could not obtain API Client information")

        return api_client_id, api_client_secret

    def execute(self):
        """Upload a script"""
        jamf_url = self.env.get("JSS_URL").rstrip("/")
        jamf_user = self.env.get("API_USERNAME")
        jamf_password = self.env.get("API_PASSWORD")
        client_id = self.env.get("CLIENT_ID")
        client_secret = self.env.get("CLIENT_SECRET")
        object_name = self.env.get("api_client_name")
        api_client_id = self.env.get("api_client_id")
        api_client_enabled = self.to_bool(self.env.get("api_client_enabled"))
        api_role_name = self.env.get("api_role_name")
        access_token_lifetime = self.env.get("access_token_lifetime")
        replace_object = self.to_bool(self.env.get("replace_api_client"))
        sleep_time = self.env.get("sleep")

        # clear any pre-existing summary result
        if "jamfapiclientuploader_summary_result" in self.env:
            del self.env["jamfapiclientuploader_summary_result"]
        object_uploaded = False

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

        # now start the process of uploading the object
        # check for existing object
        # prioritise checking for API Client ID before Display Name
        if api_client_id:
            self.output(f"Checking for existing '{object_name}' on {jamf_url}")
            object_type = "api_client"
            obj_id = self.get_api_obj_id_from_name(
                jamf_url, object_name, object_type, token, filter_name="clientId"
            )
        else:
            self.output(f"Checking for existing '{object_name}' on {jamf_url}")
            object_type = "api_client"
            obj_id = self.get_api_obj_id_from_name(
                jamf_url, object_name, object_type, token, filter_name="displayName"
            )

        if obj_id:
            if api_client_id:
                self.output(
                    f"{object_type} '{api_client_id}' already exists: ID {obj_id}"
                )
            else:
                self.output(
                    f"{object_type} '{object_name}' already exists: ID {obj_id}"
                )
            if replace_object:
                self.output(
                    f"Replacing existing {object_type} as 'replace_api_client' is set to True",
                    verbose_level=1,
                )
            else:
                self.output(
                    f"Not replacing existing {object_type}. Use replace_api_client='True' to enforce.",
                    verbose_level=1,
                )
                return

        # build the object
        object_data = {
            "authorizationScopes": [api_role_name],
            "enabled": api_client_enabled,
            "accessTokenLifetimeSeconds": int(access_token_lifetime),
        }

        # add either API client ID and/or Display Name
        # this should fail if both are provided and there's a conflict with either
        if api_client_id:
            object_data["clientId"] = api_client_id
        if object_name:
            object_data["displayName"] = object_name

        self.output(
            "Data:",
            verbose_level=2,
        )
        self.output(
            object_data,
            verbose_level=2,
        )

        # post the script
        r = self.upload_object(
            jamf_url,
            object_name,
            object_type,
            object_data,
            token,
            sleep_time,
            obj_id,
        )
        object_uploaded = True

        # get the Client ID and Secret
        if r.status_code < 300:
            # Parse response as json
            obj_content = r.output
            self.output(
                obj_content,
                verbose_level=3,
            )
            obj_id = obj_content["id"]
        else:
            raise ProcessorError("ERROR: Could not obtain API Client information")

        # now get the credentials (if enabled)
        api_client_id = ""
        api_client_secret = ""
        if api_client_enabled:
            api_client_id, api_client_secret = self.get_api_client_credentials(
                jamf_url, object_type, token, sleep_time, obj_id
            )
            self.output(f"Client ID: {api_client_id}")
            self.output(f"Client Secret: {api_client_secret}")
        else:
            self.output(
                "API Client is disabled. Set to enabled to obtain the API Client Secret"
            )

        # output the summary
        self.env["api_client_name"] = object_name
        self.env["api_client_id"] = api_client_id
        self.env["api_client_secret"] = api_client_secret
        self.env["object_uploaded"] = object_uploaded
        if object_uploaded:
            self.env["jamfapiclientuploader_summary_result"] = {
                "summary_text": "The following API clients were created or updated in Jamf Pro:",
                "report_fields": [
                    "name",
                    "api_client_id",
                ],
                "data": {
                    "name": object_name,
                    "api_client_id": api_client_id,
                },
            }
