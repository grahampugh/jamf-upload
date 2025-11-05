#!/usr/local/autopkg/python
# pylint: disable=invalid-name

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

from time import sleep
from autopkglib import URLGetter, ProcessorError  # pylint: disable=import-error


__all__ = ["JamfUploaderTeamsNotifier"]


class JamfUploaderTeamsNotifier(URLGetter):
    description = (
        "A postprocessor for AutoPkg that will send details about a recipe run "
        "to a Microsoft Teams webhook based on the output of a "
        "JamfPolicyUploader process."
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
        "patch_name": {
            "required": False,
            "description": ("Name of Patch Policy being updated"),
        },
        "pkg_name": {"required": False, "description": ("Package in policy.")},
        "jamfpackageuploader_summary_result": {
            "required": False,
            "description": ("Summary results of package processors."),
        },
        "jamfpatchuploader_summary_result": {
            "required": False,
            "description": ("Summary results of patch processors."),
        },
        "jamfpolicyuploader_summary_result": {
            "required": False,
            "description": ("Summary results of policy processors."),
        },
        "teams_webhook_url": {"required": True, "description": ("Teams webhook.")},
        "teams_username": {
            "required": False,
            "description": ("Teams AdaptiveCard display name."),
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

    def teams_status_check(self, header):
        """Return a message dependent on the HTTP response"""
        http_result_code = int(header.get("http_result_code"))
        self.output(f"Response: {http_result_code}", verbose_level=2)
        if (
            http_result_code == 200
            or http_result_code == 201
            or http_result_code == 202
        ):
            self.output("Teams webhook sent successfully")
            return "break"
        self.output(
            f"WARNING: Teams webhook failed to send (status code {http_result_code})"
        )
        return None

    def main(self):
        """Do the main thing"""
        jss_url = self.env.get("JSS_URL")
        policy_category = self.env.get("POLICY_CATEGORY")
        category = self.env.get("PKG_CATEGORY")
        policy_name = self.env.get("policy_name")
        name = self.env.get("NAME")
        version = self.env.get("version")
        pkg_name = self.env.get("pkg_name")
        patch_name = self.env.get("patch_name")
        jamfpackageuploader_summary_result = self.env.get(
            "jamfpackageuploader_summary_result"
        )
        jamfpatchuploader_summary_result = self.env.get(
            "jamfpatchuploader_summary_result"
        )
        jamfpolicyuploader_summary_result = self.env.get(
            "jamfpolicyuploader_summary_result"
        )

        if not category and jamfpackageuploader_summary_result:
            category = jamfpackageuploader_summary_result["data"]["category"]

        teams_webhook_url = self.env.get("teams_webhook_url")
        teams_username = self.env.get("teams_username")
        teams_icon_url = (
            self.env.get("teams_icon_url")
            or "https://resources.jamf.com/images/logos/Jamf-Icon-color.png"
        )

        selfservice_policy_name = name
        self.output(f"JSS address: {jss_url}")
        self.output(f"Title: {selfservice_policy_name}")
        self.output(f"Policy: {policy_name}")
        self.output(f"Version: {version}")
        self.output(f"Package: {pkg_name}")
        self.output(f"Package Category: {category}")
        self.output(f"Policy Category: {policy_category}")

        webhook_text = {}
        webhook_text["type"] = "message"
        webhook_text["attachments"] = [{}]
        webhook_text["attachments"][0][
            "contentType"
        ] = "application/vnd.microsoft.card.adaptive"
        webhook_text["attachments"][0]["contentUrl"] = "null"
        webhook_text["attachments"][0]["content"] = {}
        webhook_text["attachments"][0]["content"]["type"] = "AdaptiveCard"
        webhook_text["attachments"][0]["content"][
            "$schema"
        ] = "http://adaptivecards.io/schemas/adaptive-card.json"
        webhook_text["attachments"][0]["content"]["version"] = "1.2"
        webhook_text["attachments"][0]["content"]["verticalContentAlignment"] = "Center"
        webhook_text["attachments"][0]["content"]["body"] = [
            {
                "type": "TextBlock",
                "size": "medium",
                "weight": "bolder",
                "text": "New Item Uploaded to Jamf Pro",
            },
            {
                "type": "ColumnSet",
                "columns": [
                    {
                        "type": "Column",
                        "items": [
                            {"type": "Image", "url": teams_icon_url, "size": "Small"}
                        ],
                        "width": "auto",
                    },
                    {
                        "type": "Column",
                        "items": [
                            {
                                "type": "TextBlock",
                                "weight": "Bolder",
                                "text": teams_username,
                                "wrap": True,
                            },
                            {
                                "type": "TextBlock",
                                "spacing": "None",
                                "text": jss_url,
                                "isSubtle": True,
                                "wrap": True,
                            },
                        ],
                        "width": "stretch",
                    },
                ],
            },
            {"type": "FactSet", "facts": []},
        ]

        if (
            jamfpackageuploader_summary_result
            and jamfpatchuploader_summary_result
            and jamfpolicyuploader_summary_result
        ):
            webhook_text["attachments"][0]["content"]["body"][2]["facts"] += [
                {"title": "Title", "value": selfservice_policy_name},
                {"title": "Version", "value": version},
                {"title": "Category", "value": category},
                {"title": "Policy Name", "value": policy_name},
                {"title": "Package", "value": pkg_name},
                {"title": "Patch Policy", "value": patch_name},
            ]

        elif jamfpackageuploader_summary_result and jamfpolicyuploader_summary_result:
            webhook_text["attachments"][0]["content"]["body"][2]["facts"] += [
                {"title": "Title", "value": selfservice_policy_name},
                {"title": "Version", "value": version},
                {"title": "Category", "value": category},
                {"title": "Policy Name", "value": policy_name},
                {"title": "Package", "value": pkg_name},
            ]

        elif jamfpackageuploader_summary_result and jamfpatchuploader_summary_result:
            webhook_text["attachments"][0]["content"]["body"][2]["facts"] += [
                {"title": "Title", "value": selfservice_policy_name},
                {"title": "Version", "value": version},
                {"title": "Category", "value": category},
                {"title": "Package", "value": pkg_name},
                {"title": "Patch Policy", "value": patch_name},
            ]

        elif jamfpolicyuploader_summary_result:
            webhook_text["attachments"][0]["content"]["body"][2]["facts"] += [
                {"title": "Title", "value": selfservice_policy_name},
                {"title": "Category", "value": category},
                {"title": "Policy Name", "value": policy_name},
            ]
            webhook_text["attachments"][0]["content"]["body"].append(
                {
                    "type": "TextBlock",
                    "text": "No new package uploaded.",
                    "wrap": True,
                    "separator": True,
                }
            )

        elif jamfpackageuploader_summary_result:
            webhook_text["attachments"][0]["content"]["body"][2]["facts"] += [
                {"title": "Version", "value": version},
                {"title": "Category", "value": category},
                {"title": "Package", "value": pkg_name},
            ]
            webhook_text["attachments"][0]["content"]["body"].append(
                {
                    "type": "TextBlock",
                    "text": "No new policy uploaded.",
                    "wrap": True,
                    "separator": True,
                }
            )

        else:
            print("Nothing to report to Teams")
            return

        teams_json = json.dumps(webhook_text)

        curl_cmd = [
            self.curl_binary(),
            "--silent",
            "--show-error",
            "--no-buffer",
            "--dump-header",
            "-",
            "--speed-time",
            "30",
            "--location",
            "--url",
            teams_webhook_url,
            "--request",
            "POST",
            "--data",
            teams_json,
        ]

        headers = {
            "Content-Type": "application/json",
        }

        self.add_curl_headers(curl_cmd, headers)

        count = 0
        while True:
            count += 1
            self.output(
                f"Teams webhook post attempt {count}",
                verbose_level=2,
            )
            
            proc_stdout, _, status_code = self.execute_curl(curl_cmd)
            self.output(f"Curl command: {curl_cmd}", verbose_level=4)
            header = self.parse_headers(proc_stdout)

            # check HTTP response
            if self.teams_status_check(header) == "break":
                break
            if count > 5:
                self.output("Teams webhook send did not succeed after 5 attempts")
                self.output(f"\nHTTP POST Response Code: {status_code}")
                raise ProcessorError("ERROR: Teams webhook failed to send")
            sleep(10)


if __name__ == "__main__":
    PROCESSOR = JamfUploaderTeamsNotifier()
    PROCESSOR.execute_shell()
