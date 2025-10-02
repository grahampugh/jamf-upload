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

from datetime import datetime, timedelta
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


class JamfMSUPlanUploaderBase(JamfUploaderBase):
    """Class for functions used to upload a generic API object to Jamf.
    Note: Individual processors in this repo for specific API endpoints should always
    be used if available"""

    def check_feature_toggle(
        self,
        jamf_url,
        token,
    ):
        """Check if the feature toggle is enabled and raise processor error if toggle is set to false"""
        object_type = "managed_software_updates_feature_toggle_settings"
        object_content = self.get_settings_object(jamf_url, object_type, token)
        if object_content:
            self.output(
                f"{object_type} content on {jamf_url}: {object_content}",
                verbose_level=3,
            )
            toggle_value = object_content["toggle"]
        else:
            raise ProcessorError(f"{object_type} has no content on {jamf_url}")

        return toggle_value

    def days_from_now_to_end_of_day(self, days):
        """calculate the timestamp from a number of days in the future"""
        days = int(days)
        if not isinstance(days, (int, float)):
            raise TypeError("Input must be a number.")

        # Add the number of days to today
        future_date = datetime.now() + timedelta(days=days)

        # Create a datetime object for the end of that day
        end_of_day = future_date.replace(hour=23, minute=59, second=59, microsecond=0)

        return end_of_day.strftime("%Y-%m-%dT%H:%M:%S")

    def prepare_template(
        self,
        jamf_url,
        device_type,
        group_id,
        version_type,
        specific_version,
        days,
    ):
        """prepare the template contents"""
        # generate the template from inputs

        # calculate the timestamp
        force_install_local_datetime = self.days_from_now_to_end_of_day(days)
        self.env["force_install_local_datetime"] = force_install_local_datetime

        # validate the version type, must be one of LATEST_MAJOR, LATEST_MINOR, SPECIFIC_VERSION

        # the specific version will have to come from a different processor

        template_contents = {
            "group": {"objectType": f"{device_type}_GROUP", "groupId": group_id},
            "config": {
                "updateAction": "DOWNLOAD_INSTALL_SCHEDULE",
                "versionType": version_type,
                "forceInstallLocalDateTime": force_install_local_datetime,
            },
        }

        if specific_version is not None:
            template_contents["config"]["specificVersion"] = specific_version

        self.output(template_contents, verbose_level=2)

        # write the template to temp file
        template_file = self.write_json_file(jamf_url, template_contents)
        return template_file

    def upload_object(
        self,
        jamf_url,
        object_type,
        template_file,
        sleep_time,
        token,
        object_name=None,
    ):
        """Upload object"""

        self.output(f"Uploading {object_type}...")

        # if we find an object ID or it's an endpoint without IDs, we PUT or PATCH
        # if we're creating a new object, we POST
        url = f"{jamf_url}/{self.api_endpoints(object_type)}"
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
        """Upload an Managed Software Update Plan object"""
        jamf_url = self.env.get("JSS_URL").rstrip("/")
        jamf_user = self.env.get("API_USERNAME")
        jamf_password = self.env.get("API_PASSWORD")
        client_id = self.env.get("CLIENT_ID")
        client_secret = self.env.get("CLIENT_SECRET")
        device_type = self.env.get("device_type")
        version = self.env.get("version")
        days_until_force_install = self.env.get("days_until_force_install")
        group_name = self.env.get("group_name")
        sleep_time = self.env.get("sleep")
        object_updated = False

        # set device type to upper case
        if "computer" in device_type.lower():
            device_type = "COMPUTER"
            object_type = "computer_group"
        elif "mobile" in device_type.lower():
            device_type = "MOBILE-DEVICE"
            object_type = "mobile_device_group"
        elif "tv" in device_type.lower():
            device_type = "APPLE-TV"
            object_type = "mobile_device_group"
        else:
            raise ProcessorError(
                "ERROR: Invalid device type supplied."
                "Must be one of 'computer', 'mobile-device', 'apple-tv'"
            )

        # clear any pre-existing summary result
        if "jamfmsuplanuploader_summary_result" in self.env:
            del self.env["jamfmsuplanuploader_summary_result"]

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

        # check if managed software update feature toggle is enabled - this
        # processor requires it to be enabled
        toggle_value = self.check_feature_toggle(jamf_url, token)
        if toggle_value:
            self.output("Software Update Feature is enabled.")
        else:
            raise ProcessorError(
                "ERROR: Software Update Feature is disabled. Please enable and retry."
            )

        # get the group ID from the group name
        group_id = ""
        group_id = self.get_api_obj_id_from_name(
            jamf_url, group_name, object_type, token
        )
        if not group_id:
            raise ProcessorError(f"ERROR: Group {group_name} not found")

        # set either specific version, latest minor or latest major
        specific_version = None
        if "minor" in version.lower():
            version_type = "LATEST_MINOR"
        elif "major" in version.lower():
            version_type = "LATEST_MAJOR"
        elif "any" in version.lower():
            version_type = "LATEST_ANY"
        elif "." in version:
            version_type = "SPECIFIC_VERSION"
            specific_version = version
        else:
            raise ProcessorError(
                "ERROR: Invalid version supplied. Must be either 'latest-major', "
                "'latest-minor', 'latest-any', or a specific version "
                "containing at least one dot, e.g. 15.1"
            )

        # we need to substitute the values in the object name and template now to
        # account for version strings in the name
        template_file = self.prepare_template(
            jamf_url,
            device_type,
            group_id,
            version_type,
            specific_version,
            days_until_force_install,
        )

        # check for an existing object except for settings-related endpoints
        object_type = "managed_software_updates_plans_group_settings"

        # upload the object
        self.upload_object(
            jamf_url,
            object_type,
            template_file,
            sleep_time,
            token=token,
        )
        object_updated = True

        # output the summary
        if object_updated:
            self.env["jamfmsuplanuploader_summary_result"] = {
                "summary_text": "The following objects were updated in Jamf Pro:",
                "report_fields": [
                    "device_type",
                    "group_name",
                    "version_type",
                    "specific_version",
                    "force_install_local_datetime",
                ],
                "data": {
                    "device_type": device_type,
                    "group_name": group_name,
                    "version_type": version_type,
                    "specific_version": str(specific_version),
                    "force_install_local_datetime": str(
                        self.env["force_install_local_datetime"]
                    ),
                },
            }
