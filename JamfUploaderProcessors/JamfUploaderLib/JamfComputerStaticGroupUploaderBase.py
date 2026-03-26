#!/usr/local/autopkg/python
# pylint: disable=invalid-name

"""
Copyright 2026 Graham Pugh

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


class JamfComputerStaticGroupUploaderBase(JamfUploaderBase):
    """Class for functions used to upload a computer group to Jamf"""

    def get_existing_assignments(self, jamf_url, object_id, token):
        """return the existing members of the static group to ensure we don't overwrite"""
        # first grab the payload from the json object
        existing_assignments_key = self.get_api_object_value_from_id(
            jamf_url,
            object_type="computer_group",
            object_id=object_id,
            object_path="computers",
            token=token,
        )

        self.output(
            f"Existing members (type: {type(existing_assignments_key)}):",
            verbose_level=3,
        )
        self.output(existing_assignments_key, verbose_level=3)

        # now extract the IDs of the members from the existing payload
        # an example of the payload is:
        # [{'id': 2, 'name': 'ZHVD0LQ3JP', 'mac_address': '8E:B7:33:74:82:8F', 'alt_mac_address': 'D6:1E:0D:2C:6D:8B', 'serial_number': 'ZHVD0LQ3JP'}, {'id': 6, 'name': 'test’s Virtual Machine', 'mac_address': 'E2:CE:B2:9C:FC:FD', 'alt_mac_address': '7E:DC:DD:DA:15:BE', 'serial_number': 'ZLWQ0Y744L'}, {'id': 7, 'name': 'test’s Virtual Machine', 'mac_address': '5A:0F:0D:31:36:E0', 'alt_mac_address': '4A:02:9E:6C:CF:90', 'serial_number': 'Z3K3XHCPQ7'}, {'id': 41, 'name': 'VDHG9W59FC', 'mac_address': 'F8:4D:89:83:A1:D6', 'alt_mac_address': '36:2D:4D:39:8B:40', 'serial_number': 'VDHG9W59FC'}]
        existing_assignments = [member["id"] for member in existing_assignments_key]
        self.output("Imported assignments", verbose_level=2)
        self.output(existing_assignments, verbose_level=2)

        return existing_assignments

    def upload_object(
        self,
        jamf_url,
        object_name,
        description,
        assignments,
        sleep_time,
        token,
        max_tries,
        object_id=0,
    ):
        """Upload computer group"""

        # build the object
        object_data = {
            "name": object_name,
            "description": description,
            "assignments": assignments,
        }

        self.output("Computer Group data:", verbose_level=2)
        self.output(object_data, verbose_level=2)

        self.output("Uploading Computer Group...")
        # if we find an object ID we put, if not, we post
        object_type = "static_computer_group"
        if object_id:
            url = f"{jamf_url}/{self.api_endpoints(object_type)}/{object_id}"
        else:
            url = f"{jamf_url}/{self.api_endpoints(object_type)}"

        count = 0
        object_json = self.write_json_file(jamf_url, object_data)
        while True:
            count += 1
            self.output(f"Computer Group upload attempt {count}", verbose_level=2)
            request = "PUT" if object_id else "POST"
            r = self.curl(
                api_type="jpapi",
                request=request,
                url=url,
                token=token,
                data=object_json,
            )

            # check HTTP response
            if self.status_check(r, "Computer Group", object_name, request) == "break":
                break
            if count >= max_tries:
                self.output(
                    f"WARNING: Computer Group upload did not succeed after {max_tries} attempts"
                )
                self.output(f"\nHTTP POST Response Code: {r.status_code}")
                raise ProcessorError("ERROR: Computer Group upload failed ")
            if int(sleep_time) > 10:
                sleep(int(sleep_time))
            else:
                sleep(10)

    def execute(self):
        """Upload a static computer group"""
        jamf_url = self.env.get("JSS_URL").rstrip("/")
        jamf_user = self.env.get("API_USERNAME")
        jamf_password = self.env.get("API_PASSWORD")
        client_id = self.env.get("CLIENT_ID")
        client_secret = self.env.get("CLIENT_SECRET")
        bearer_token = self.env.get("BEARER_TOKEN")
        use_jcm = self.to_bool(self.env.get("jamf_credentials_manager"))
        computergroup_name = self.env.get("computergroup_name")
        group_description = self.env.get("group_description")
        replace_group = self.to_bool(self.env.get("replace_group"))
        clear_assignments = self.to_bool(self.env.get("clear_assignments"))
        sleep_time = self.env.get("sleep")
        max_tries = self.env.get("max_tries")

        # verify that max_tries is an integer greater than zero and less than 10
        try:
            max_tries = int(max_tries)
            if max_tries < 1 or max_tries > 10:
                raise ValueError
        except (ValueError, TypeError):
            max_tries = 5

        # clear any pre-existing summary result
        if "jamfcomputerstaticgroupuploader_summary_result" in self.env:
            del self.env["jamfcomputerstaticgroupuploader_summary_result"]
        group_uploaded = False

        # we need to substitute the values in the computer group name now to
        # account for version strings in the name
        # substitute user-assignable keys
        computergroup_name = self.substitute_assignable_keys(computergroup_name)

        # now start the process of uploading the object
        self.output(f"Checking for existing '{computergroup_name}' on {jamf_url}")

        # get token using oauth or basic auth depending on the credentials given
        if jamf_url:
            token = self.handle_api_auth(
                jamf_url,
                jamf_user=jamf_user,
                password=jamf_password,
                client_id=client_id,
                client_secret=client_secret,
                token=bearer_token,
                use_jamf_credentials_manager=use_jcm,
            )
        else:
            raise ProcessorError("ERROR: Jamf Pro URL not supplied")

        # check for existing - requires object_name
        object_id = self.get_api_object_id_from_name(
            jamf_url,
            object_type="static_computer_group",
            object_name=computergroup_name,
            token=token,
        )

        existing_assignments = []
        if object_id:
            self.output(
                f"Computer group '{computergroup_name}' already exists: ID {object_id}"
            )
            if replace_group:
                self.output(
                    "Replacing existing Computer Group as 'replace_group' is set to True",
                    verbose_level=1,
                )
            else:
                self.output(
                    "Not replacing existing Computer Group. Use replace_group='True' to enforce.",
                    verbose_level=1,
                )
                return
            # now get any existing assignments
            if not clear_assignments:
                existing_assignments = self.get_existing_assignments(
                    jamf_url, object_id, token
                )

        # upload the group
        self.upload_object(
            jamf_url,
            object_name=computergroup_name,
            description=group_description,
            assignments=existing_assignments,
            sleep_time=sleep_time,
            token=token,
            max_tries=max_tries,
            object_id=object_id,
        )
        group_uploaded = True

        if int(sleep_time) > 0:
            sleep(int(sleep_time))

        # output the summary
        self.env["group_uploaded"] = group_uploaded
        if group_uploaded:
            self.env["jamfcomputerstaticgroupuploader_summary_result"] = {
                "summary_text": (
                    "The following computer groups were created or updated "
                    "in Jamf Pro:"
                ),
                "report_fields": ["group"],
                "data": {
                    "group": computergroup_name,
                },
            }
