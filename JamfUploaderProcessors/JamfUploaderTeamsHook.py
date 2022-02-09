#!/usr/local/autopkg/python

"""
Copyright 2022 Graham Pugh, Jacob Burley

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
from autopkglib import ProcessorError  # pylint: disable=import-error

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfUploaderBase import JamfUploaderBase  # noqa: E402


__all__ = ["JamfUploaderTeamsHook"]


class JamfUploaderTeamsHook(JamfUploaderBase):
    description = (
        "Posts to Teams via webhook based on output of a JamfPolicyUploader process. "
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
        "jamfpackageuploader_summary_result": {
            "required": False,
            "description": ("Summary results of package processors."),
        },
        "jamfpolicyuploader_summary_result": {
            "required": False,
            "description": ("Summary results of policy processors."),
        },
        "teams_webhook_url": {
            "required": True, 
            "description": ("Teams webhook.")
        },
        "teams_username": {
            "required": False,
            "description": ("Teams MessageCard display name."),
            "default": "AutoPkg",
        },
        "teams_icon_url": {
            "required": False,
            "description": ("Teams display icon URL."),
            "default": "https://resources.jamf.com/images/logos/Jamf-Icon-color.png",
        },
    }
    output_variables = {}

    __doc__ = description


    def teams_status_check(self, r):
        """Return a message dependent on the HTTP response"""
        if r.status_code == 200 or r.status_code == 201:
            self.output("Teams webhook sent successfully")
            return "break"
        else:
            self.output("WARNING: Teams webhook failed to send")
            self.output(r.output, verbose_level=2)

    def main(self):
        """Do the main thing"""
        jss_url = self.env.get("JSS_URL")
        policy_category = self.env.get("POLICY_CATEGORY")
        category = self.env.get("PKG_CATEGORY")
        policy_name = self.env.get("policy_name")
        name = self.env.get("NAME")
        version = self.env.get("version")
        pkg_name = self.env.get("pkg_name")
        jamfpackageuploader_summary_result = self.env.get(
            "jamfpackageuploader_summary_result"
        )
        jamfpolicyuploader_summary_result = self.env.get(
            "jamfpolicyuploader_summary_result"
        )

        webhook_template = json.loads('{"type": "message", "attachments" : [{"contentType": "application/vnd.microsoft.teams.card.o365connector", "content": {"type": "MessageCard", "$schema": "https://schema.org/extensions", "summary": "New item uploaded to Jamf Pro", "themeColor": "778eb1", "title": "New item uploaded to Jamf Pro", "sections": [{"activityTitle": "", "activityImage": "", "facts": [] } ] } } ] }')
        teams_webhook_url = self.env.get("teams_webhook_url")
        teams_username = self.env.get("teams_username")
        teams_icon_url = self.env.get("teams_icon_url") or "https://resources.jamf.com/images/logos/Jamf-Icon-color.png"

        selfservice_policy_name = name
        self.output(f"JSS address: {jss_url}")
        self.output(f"Title: {selfservice_policy_name}")
        self.output(f"Policy: {policy_name}")
        self.output(f"Version: {version}")
        self.output(f"Package: {pkg_name}")
        self.output(f"Package Category: {category}")
        self.output(f"Policy Category: {policy_category}")

        if jamfpackageuploader_summary_result and jamfpolicyuploader_summary_result:
            
            webhook_template["attachments"][0]["content"]["sections"][0]["facts"] += [{
                "name": "Title",
                "value": selfservice_policy_name
            },
            {
                "name": "Version",
                "value": version
            },
            {
                "name": "Category",
                "value": category
            },
            {
                "name": "Policy Name",
                "value": policy_name
            },
            {
                "name": "Package",
                "value": pkg_name
            }]

        elif jamfpolicyuploader_summary_result:
            
            webhook_template["attachments"][0]["content"]["sections"][0]["facts"] += [{
                "name": "Title",
                "value": selfservice_policy_name
            },
            {
                "name": "Category",
                "value": category
            },
            {
                "name": "Policy Name",
                "value": policy_name
            }]

            webhook_template["attachments"][0]["content"]["sections"] +=[{
                "text": "No new package uploaded."
            }]

        elif jamfpackageuploader_summary_result:
            webhook_template["attachments"][0]["content"]["sections"][0]["facts"] += [{
                "name": "Version",
                "value": version
            },
            {
                "name": "Category",
                "value": category
            },
            {
                "name": "Package",
                "value": pkg_name
            }]

            webhook_template["attachments"][0]["content"]["sections"] +=[{
                "text": "No new package uploaded."
            }]

        else:
            self.output("Nothing to report to Teams")
            return

        webhook_template["attachments"][0]["content"]["sections"][0]["activityTitle"] = teams_username
        webhook_template["attachments"][0]["content"]["sections"][0]["activitySubtitle"] = jss_url

        if teams_icon_url:
            webhook_template["attachments"][0]["content"]["sections"][0]["activityImage"] = teams_icon_url

        teams_json = json.dumps(webhook_template)

        count = 0
        while True:
            count += 1
            self.output(
                "Teams webhook post attempt {}".format(count), verbose_level=2,
            )
            r = self.curl(request="POST", url=teams_webhook_url, data=teams_json)
            # check HTTP response
            if self.teams_status_check(r) == "break":
                break
            if count > 5:
                self.output("Teams webhook send did not succeed after 5 attempts")
                self.output("\nHTTP POST Response Code: {}".format(r.status_code))
                raise ProcessorError("ERROR: Teams webhook failed to send")
            sleep(10)


if __name__ == "__main__":
    PROCESSOR = JamfUploaderTeamsHook()
    PROCESSOR.execute_shell()
