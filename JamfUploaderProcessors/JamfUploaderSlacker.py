#!/usr/local/autopkg/python
# pylint: disable=invalid-name

"""
Copyright 2020 Graham Pugh

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

NOTES:
Set the webhook_url to the one provided by Slack when you create the webhook at
https://my.slack.com/services/new/incoming-webhook/
"""

import json
import os.path
import sys

from time import sleep
from autopkglib import ProcessorError  # pylint: disable=import-error

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfUploaderBase import (  # pylint: disable=import-error, wrong-import-position
    JamfUploaderBase,
)


__all__ = ["JamfUploaderSlacker"]


class JamfUploaderSlacker(JamfUploaderBase):
    """A class for sending details about a recipe run
    to a Slack webhook based on the output of a JamfPolicyUploader
    process.
    """

    description = (
        "A postprocessor for AutoPkg that will send details about a recipe run "
        "to a Slack webhook based on the output of a JamfPolicyUploader "
        "process."
        "Takes elements from "
        "https://gist.github.com/devStepsize/b1b795309a217d24566dcc0ad136f784 "
        "and "
        "https://github.com/autopkg/nmcspadden-recipes/blob/master/PostProcessors/Yo.py."
    )
    input_variables = {
        "JSS_URL": {"required": False, "description": ("JSS_URL.")},
        "POLICY_CATEGORY": {"required": False, "description": ("Policy Category.")},
        "PKG_CATEGORY": {"required": False, "description": ("Package Category.")},
        "policy_name": {
            "required": False,
            "description": ("Untested product name from a jamf recipe."),
        },
        "NAME": {"required": False, "description": ("Generic product name.")},
        "pkg_name": {"required": False, "description": ("Package in policy.")},
        "PROFILE_NAME": {"required": False, "description": ("Profile name.")},
        "PROFILE_CATEGORY": {"required": False, "description": ("Profile category.")},
        "version": {
            "required": False,
            "description": ("Package version."),
        },
        "jamfpackageuploader_summary_result": {
            "required": False,
            "description": ("Summary results of package processors."),
        },
        "jamfpkgmetadatauploader_summary_result": {
            "required": False,
            "description": ("Summary results of package metadata processors."),
        },
        "jamfpolicyuploader_summary_result": {
            "required": False,
            "description": ("Summary results of policy processors."),
        },
        "jamfcomputerprofileuploader_summary_result": {
            "required": False,
            "description": ("Summary results of computer profile processors."),
        },
        "jamfmobiledeviceprofilepploader_summary_result": {
            "required": False,
            "description": ("Summary results of mobile device profile processors."),
        },
        "jamfmacappuploader_summary_result": {
            "required": False,
            "description": ("Summary results of Mac App Store App processors."),
        },
        "jamfmobiledeviceappuploader_summary_result": {
            "required": False,
            "description": (
                "Summary results of Mobile Device App Store App processors."
            ),
        },
        "jamfmsuplanuploader_summary_result": {
            "required": False,
            "description": ("Summary results of MSU Plan processors."),
        },
        "jamfobjectuploader_summary_result": {
            "required": False,
            "description": ("Summary results of generic object uploader processors."),
        },
        "slack_webhook_url": {"required": True, "description": ("Slack webhook.")},
        "slack_username": {
            "required": False,
            "description": ("Slack message display name."),
            "default": "AutoPkg",
        },
        "slack_icon_url": {
            "required": False,
            "description": ("Slack display icon URL."),
            "default": "",
        },
        "slack_channel": {
            "required": False,
            "description": ("Slack channel (for overriding the default)."),
        },
        "slack_icon_emoji": {
            "required": False,
            "description": ("Slack display emoji markup."),
        },
    }
    output_variables = {}

    __doc__ = description

    def slack_status_check(self, r):
        """Return a message dependent on the HTTP response"""
        if r.status_code == 200 or r.status_code == 201:
            self.output("Slack webhook sent successfully")
            return "break"
        else:
            self.output("WARNING: Slack webhook failed to send")
            self.output(r.output, verbose_level=2)

    def main(self):
        """Do the main thing"""
        jss_url = self.env.get("JSS_URL")
        failover_url = self.env.get("failover_url")
        policy_category = self.env.get("POLICY_CATEGORY")
        category = self.env.get("PKG_CATEGORY")
        policy_name = self.env.get("policy_name")
        name = self.env.get("NAME")
        version = self.env.get("version")
        pkg_name = self.env.get("pkg_name")
        macapp_name = self.env.get("macapp_name")
        mobiledeviceapp_name = self.env.get("mobiledeviceapp_name")
        profile_name = self.env.get("PROFILE_NAME")
        profile_category = self.env.get("PROFILE_CATEGORY")
        object_name = self.env.get("object_name")
        object_type = self.env.get("object_type")
        jamfpackageuploader_summary_result = self.env.get(
            "jamfpackageuploader_summary_result"
        )
        jamfpkgmetadatauploader_summary_result = self.env.get(
            "jamfpkgmetadatauploader_summary_result"
        )
        jamfpolicyuploader_summary_result = self.env.get(
            "jamfpolicyuploader_summary_result"
        )
        jamfcomputerprofileuploader_summary_result = self.env.get(
            "jamfcomputerprofileuploader_summary_result"
        )
        jamfmobiledeviceprofilepploader_summary_result = self.env.get(
            "jamfmobiledeviceprofilepploader_summary_result"
        )
        jamfmacappuploader_summary_result = self.env.get(
            "jamfmacappuploader_summary_result"
        )
        jamfmobiledeviceappuploader_summary_result = self.env.get(
            "jamfmobiledeviceappuploader_summary_result"
        )
        jamfmsuplanuploader_summary_result = self.env.get(
            "jamfmsuplanuploader_summary_result"
        )
        jamfobjectuploader_summary_result = self.env.get(
            "jamfobjectuploader_summary_result"
        )

        slack_username = self.env.get("slack_username")
        slack_icon_url = self.env.get("slack_icon_url") or ""
        slack_webhook_url = self.env.get("slack_webhook_url")
        slack_channel = self.env.get("slack_channel") or ""
        slack_icon_emoji = self.env.get("slack_icon_emoji") or ""

        if not category and jamfpackageuploader_summary_result:
            category = jamfpackageuploader_summary_result["data"]["category"]

        selfservice_policy_name = name
        self.output(f"JSS address: {jss_url}")
        if selfservice_policy_name:
            self.output(f"Title: {selfservice_policy_name}", verbose_level=2)
        if policy_name:
            self.output(f"Policy: {policy_name}", verbose_level=2)
        if version:
            self.output(f"Version: {version}", verbose_level=2)
        if pkg_name:
            self.output(f"Package: {pkg_name}", verbose_level=2)
        if profile_name:
            self.output(f"Profile: {profile_name}", verbose_level=2)
        if macapp_name:
            self.output(f"Mac App: {macapp_name}", verbose_level=2)
        if mobiledeviceapp_name:
            self.output(f"Mobile Device App: {pkg_name}", verbose_level=2)
        if category:
            self.output(f"Package Category: {category}", verbose_level=2)
        if policy_category:
            self.output(f"Policy Category: {policy_category}", verbose_level=2)
        if profile_category:
            self.output(f"Profile Category: {profile_category}", verbose_level=2)
        if object_name:
            self.output(f"Object Type: {object_name}", verbose_level=2)
        if object_type:
            self.output(f"Object Type: {object_type}", verbose_level=2)

        if jamfpackageuploader_summary_result and jamfpolicyuploader_summary_result:
            slack_text = (
                "*New Policy and Package uploaded to Jamf Pro:*\n"
                + f"URL: {jss_url}\n"
                + f"Title: *{selfservice_policy_name}*\n"
                + f"Version: *{version}*\n"
                + f"Category: *{policy_category}*\n"
                + f"Policy Name: *{policy_name}*\n"
                + f"Package: *{pkg_name}*"
            )
        elif jamfpolicyuploader_summary_result:
            slack_text = (
                "*New Policy uploaded to Jamf Pro:*\n"
                + f"URL: {jss_url}\n"
                + f"Title: *{selfservice_policy_name}*\n"
                + f"Category: *{policy_category}*\n"
                + f"Policy Name: *{policy_name}*\n"
                + "No new package uploaded"
            )
        elif (
            jamfpackageuploader_summary_result or jamfpkgmetadatauploader_summary_result
        ):
            slack_text = (
                "*New Package uploaded to Jamf Pro:*\n"
                + f"URL: {jss_url}\n"
                + f"Version: *{version}*\n"
                + f"Category: *{category}*\n"
                + f"Package: *{pkg_name}*"
            )
        elif jamfcomputerprofileuploader_summary_result:
            slack_text = (
                "*New Computer Profile uploaded to Jamf Pro:*\n"
                + f"URL: {jss_url}\n"
                + f"Category: *{profile_category}*\n"
                + f"Profile: *{profile_name}*"
            )
        elif jamfmobiledeviceprofilepploader_summary_result:
            slack_text = (
                "*New Mobile Device Profile uploaded to Jamf Pro:*\n"
                + f"URL: {jss_url}\n"
                + f"Category: *{profile_category}*\n"
                + f"Profile: *{profile_name}*"
            )
        elif jamfmobiledeviceappuploader_summary_result:
            slack_text = (
                "*New Mobile Device Profile uploaded to Jamf Pro:*\n"
                + f"URL: {jss_url}\n"
                + f"Category: *{profile_category}*\n"
                + f"Profile: *{profile_name}*"
            )
        elif jamfmacappuploader_summary_result:
            slack_text = (
                "*Mac App configuration uploaded to Jamf Pro:*\n"
                + f"URL: {jss_url}\n"
                + f"App: *{macapp_name}*"
            )
        elif jamfmobiledeviceappuploader_summary_result:
            slack_text = (
                "*Mobile Device App configuration uploaded to Jamf Pro:*\n"
                + f"URL: {jss_url}\n"
                + f"App: *{mobiledeviceapp_name}*"
            )
        elif jamfobjectuploader_summary_result:
            slack_text = f"*{object_type} uploaded to Jamf Pro:*" + f"\nURL: {jss_url}"
            if object_name:
                slack_text += f"\nName: *{object_name}*"
            if failover_url:
                slack_text += f"\nFailover URL: {failover_url}"
        elif jamfmsuplanuploader_summary_result:
            slack_text = (
                "*Managed Software Update plan uploaded to Jamf Pro:*\n"
                + f"URL: {jss_url}\n"
                + "Device Type: "
                + jamfmsuplanuploader_summary_result["data"]["device_type"].lower()
                + "\nGroup Name: "
                + jamfmsuplanuploader_summary_result["data"]["group_name"]
                + "\nForce Install Date: "
                + jamfmsuplanuploader_summary_result["data"][
                    "force_install_local_datetime"
                ]
                + "\nVersion Type: "
                + jamfmsuplanuploader_summary_result["data"]["version_type"].lower()
            )
            if jamfmsuplanuploader_summary_result["data"]["specific_version"]:
                slack_text += (
                    "\nSpecific Version: "
                    f"{jamfmsuplanuploader_summary_result['data']['specific_version']}"
                )
        else:
            self.output("Nothing to report to Slack")
            return

        slack_data = {
            "text": slack_text,
            "username": slack_username,
        }
        if slack_icon_url:
            slack_data["icon_url"] = slack_icon_url
        if slack_channel:
            slack_data["channel"] = slack_channel
        if slack_icon_emoji:
            slack_data["icon_emoji"] = slack_icon_emoji

        slack_json = json.dumps(slack_data)

        count = 0
        while True:
            count += 1
            self.output(
                f"Slack webhook post attempt {count}",
                verbose_level=2,
            )
            r = self.curl(
                request="POST",
                url=slack_webhook_url,
                data=slack_json,
                endpoint_type="slack",
            )
            # check HTTP response
            if self.slack_status_check(r) == "break":
                break
            if count > 5:
                self.output("Slack webhook send did not succeed after 5 attempts")
                self.output(f"\nHTTP POST Response Code: {r.status_code}")
                raise ProcessorError("ERROR: Slack webhook failed to send")
            sleep(10)


if __name__ == "__main__":
    PROCESSOR = JamfUploaderSlacker()
    PROCESSOR.execute_shell()
