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


class JamfMobileDeviceGroupUploaderBase(JamfUploaderBase):
    """Class for functions used to upload a mobile device group to Jamf"""

    def upload_mobiledevicegroup(
        self,
        jamf_url,
        mobiledevicegroup_name,
        mobiledevicegroup_template,
        sleep_time,
        token,
        obj_id=0,
    ):
        """Upload Mobile Device Group"""

        # import template from file and replace any keys in the template
        if os.path.exists(mobiledevicegroup_template):
            with open(mobiledevicegroup_template, "r", encoding="utf-8") as file:
                template_contents = file.read()
        else:
            raise ProcessorError("Template does not exist!")

        # substitute user-assignable keys
        template_contents = self.substitute_assignable_keys(template_contents)

        self.output("Mobile Device Group data:", verbose_level=2)
        self.output(template_contents, verbose_level=2)

        self.output("Uploading Mobile Device Group...")
        # write the template to temp file
        template_xml = self.write_temp_file(jamf_url, template_contents)

        # if we find an object ID we put, if not, we post
        object_type = "mobile_device_group"
        url = f"{jamf_url}/{self.api_endpoints(object_type)}/id/{obj_id}"

        count = 0
        while True:
            count += 1
            self.output(f"Mobile Device Group upload attempt {count}", verbose_level=2)
            request = "PUT" if obj_id else "POST"
            r = self.curl(
                request=request,
                url=url,
                token=token,
                data=template_xml,
            )

            # check HTTP response
            if (
                self.status_check(
                    r, "Mobile Device Group", mobiledevicegroup_name, request
                )
                == "break"
            ):
                break
            if count > 5:
                self.output(
                    "WARNING: Mobile Device Group upload did not succeed after 5 attempts"
                )
                self.output(f"\nHTTP POST Response Code: {r.status_code}")
                raise ProcessorError("ERROR: Mobile Device Group upload failed ")
            if int(sleep_time) > 30:
                sleep(int(sleep_time))
            else:
                sleep(30)

    def execute(self):
        """Upload a mobile device group"""
        jamf_url = self.env.get("JSS_URL").rstrip("/")
        jamf_user = self.env.get("API_USERNAME")
        jamf_password = self.env.get("API_PASSWORD")
        client_id = self.env.get("CLIENT_ID")
        client_secret = self.env.get("CLIENT_SECRET")
        mobiledevicegroup_name = self.env.get("mobiledevicegroup_name")
        mobiledevicegroup_template = self.env.get("mobiledevicegroup_template")
        replace_group = self.to_bool(self.env.get("replace_group"))
        sleep_time = self.env.get("sleep")
        group_uploaded = False

        # clear any pre-existing summary result
        if "JamfMobileDeviceGroupUploader_summary_result" in self.env:
            del self.env["JamfMobileDeviceGroupUploader_summary_result"]

        # we need to substitute the values in the computer group name now to
        # account for version strings in the name
        # substitute user-assignable keys
        mobiledevicegroup_name = self.substitute_assignable_keys(mobiledevicegroup_name)

        # handle files with a relative path
        if not mobiledevicegroup_template.startswith("/"):
            found_template = self.get_path_to_file(mobiledevicegroup_template)
            if found_template:
                mobiledevicegroup_template = found_template
            else:
                raise ProcessorError(
                    f"ERROR: Mobile Device Group file {mobiledevicegroup_template} not found"
                )

        # now start the process of uploading the object
        self.output(f"Checking for existing '{mobiledevicegroup_name}' on {jamf_url}")

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

        # check for existing - requires obj_name
        obj_type = "mobile_device_group"
        obj_name = mobiledevicegroup_name
        obj_id = self.get_api_obj_id_from_name(
            jamf_url,
            obj_name,
            obj_type,
            token=token,
        )

        if obj_id:
            self.output(
                f"Mobile Device Group '{mobiledevicegroup_name}' already exists: ID {obj_id}"
            )
            if replace_group:
                self.output(
                    "Replacing existing Mobile Device Group as 'replace_group' is set to True",
                    verbose_level=1,
                )
            else:
                self.output(
                    "Not replacing existing Mobile Device Group. "
                    "Use replace_group='True' to enforce.",
                    verbose_level=1,
                )
                return

        # upload the group
        self.upload_mobiledevicegroup(
            jamf_url,
            mobiledevicegroup_name,
            mobiledevicegroup_template,
            sleep_time,
            token=token,
            obj_id=obj_id,
        )
        group_uploaded = True

        if int(sleep_time) > 0:
            sleep(int(sleep_time))

        # output the summary
        self.env["group_uploaded"] = group_uploaded
        if group_uploaded:
            self.env["JamfMobileDeviceGroupUploader_summary_result"] = {
                "summary_text": (
                    "The following Mobile Device Groups were created or updated "
                    "in Jamf Pro:"
                ),
                "report_fields": ["group", "template"],
                "data": {
                    "group": mobiledevicegroup_name,
                    "template": mobiledevicegroup_template,
                },
            }
