#!/usr/local/autopkg/python

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

import json

from time import sleep
from autopkglib import URLGetter, ProcessorError  # pylint: disable=import-error


__all__ = ["JamfUploaderJiraIssueCreator"]


class JamfUploaderJiraIssueCreator(URLGetter):
    description = (
        "A postprocessor for AutoPkg that will create a Jira issue based on the output of a "
        "JamfUploader process."
    )
    # pylint: disable=line-too-long
    input_variables = {
        "JSS_URL": {"required": False, "description": ("JSS_URL.")},
        "POLICY_CATEGORY": {"required": False, "description": ("Policy Category.")},
        "PKG_CATEGORY": {"required": False, "description": ("Package Category.")},
        "CATEGORY": {"required": False, "description": ("Category.")},
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
        "jira_url": {
            "required": True,
            "description": ("Jira URL (https://<subdomain>.atlassian.net)."),
        },
        "jira_username": {"required": True, "description": ("Jira account username.")},
        "jira_api_token": {
            "required": True,
            "description": (
                "Jira API token (generated in Jira - Account Settings - Security)."
            ),
        },
        "jira_project_id": {
            "required": True,
            "description": ("Jira Project ID."),
        },
        "jira_issuetype_id": {
            "required": False,
            "description": (
                "Jira Issue Type. Default is 'Story'. See "
                "https://support.atlassian.com/jira/kb/finding-the-id-for-issue-types-in-jira-server-or-data-center/"
            ),
            "default": "10001",
        },
        "jira_priority_id": {
            "required": False,
            "description": (
                "Jira Priority. Default is the lowest priority. See "
                "https://support.atlassian.com/jira/kb/find-the-id-numbers-of-jira-priority-field-values-in-jira-cloud/"
            ),
            "default": "5",
        },
        "max_tries": {
            "required": False,
            "description": (
                "Maximum number of attempts to upload the account. "
                "Must be an integer between 1 and 10."
            ),
            "default": "5",
        },
    }
    output_variables = {}

    __doc__ = description

    def jira_status_check(self, header):
        """Return a message dependent on the HTTP response"""
        http_result_code = int(header.get("http_result_code"))
        self.output(f"Response: {http_result_code}", verbose_level=2)
        if (
            http_result_code == 200
            or http_result_code == 201
            or http_result_code == 202
        ):
            self.output("Jira request sent successfully")
            return "break"
        self.output(
            f"WARNING: Jira request failed to send (status code {http_result_code})"
        )
        return None

    def main(self):
        """Do the main thing"""
        jss_url = self.env.get("JSS_URL")
        policy_category = self.env.get("POLICY_CATEGORY")
        pkg_category = self.env.get("PKG_CATEGORY")
        category = self.env.get("CATEGORY")
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
        max_tries = self.env.get("max_tries")

        # verify that max_tries is an integer greater than zero and less than 10
        try:
            max_tries = int(max_tries)
            if max_tries < 1 or max_tries > 10:
                raise ValueError
        except (ValueError, TypeError):
            max_tries = 5

        if policy_category and jamfpolicyuploader_summary_result:
            category = policy_category
        elif pkg_category and jamfpackageuploader_summary_result:
            category = pkg_category
        else:
            if not category and jamfpackageuploader_summary_result:
                category = jamfpackageuploader_summary_result["data"]["category"]

        jira_url = self.env.get("jira_url")
        jira_username = self.env.get("jira_username")
        jira_api_token = self.env.get("jira_api_token")
        jira_project_id = self.env.get("jira_project_id")
        jira_issuetype_id = self.env.get("jira_issuetype_id")
        jira_priority_id = self.env.get("jira_priority_id")

        selfservice_policy_name = name
        self.output(f"JSS address: {jss_url}")
        self.output(f"Title: {selfservice_policy_name}")
        self.output(f"Policy: {policy_name}")
        self.output(f"Version: {version}")
        self.output(f"Package: {pkg_name}")
        self.output(f"Category: {pkg_category}")
        self.output(f"Package Category: {pkg_category}")
        self.output(f"Policy Category: {policy_category}")

        summary = ""
        description = f"URL: {jss_url}\n"

        if not jira_url:
            raise ProcessorError("No Jira URL provided")
        if not jira_username:
            raise ProcessorError("No Jira username provided")
        if not jira_api_token:
            raise ProcessorError("No Jira API token provided")
        if not jira_project_id:
            raise ProcessorError("No Jira project ID provided")

        if pkg_name:
            description += f"Package: {pkg_name}\n"
            summary = pkg_name
        if selfservice_policy_name:
            description += f"Title: {selfservice_policy_name}\n"
            summary = selfservice_policy_name if not summary else summary
        if category:
            description += f"Category: {category}\n"
        if policy_category:
            description += f"Policy Category: {policy_category}\n"
        if policy_name:
            description += f"Policy Name: {policy_name}\n"
        if version:
            description += f"Version: {version}\n"
        if patch_name:
            description += f"Patch Policy: {patch_name}\n"

        if (
            jamfpatchuploader_summary_result
            and jamfpolicyuploader_summary_result
            and jamfpackageuploader_summary_result
        ):
            description += "Policy, Patch Policy and Package created or updated"
        elif jamfpolicyuploader_summary_result and jamfpackageuploader_summary_result:
            description += "Policy and Package created or updated"
        elif jamfpatchuploader_summary_result and jamfpackageuploader_summary_result:
            description += "Package and Patch Policy created or updated"
        elif jamfpolicyuploader_summary_result:
            description += "Policy created or updated"
        elif jamfpatchuploader_summary_result:
            description += "Patch Policy created or updated"
        elif jamfpackageuploader_summary_result:
            description += "Package uploaded"
        else:
            description += "Nothing created or updated"
            self.output("Nothing new to report to Jira")
            return

        if not description:
            self.output("Nothing to report to Jira")
            return

        template_text = {
            "fields": {
                "summary": summary,
                "issuetype": {"id": str(jira_issuetype_id)},
                "project": {"id": str(jira_project_id)},
                "priority": {"id": str(jira_priority_id)},
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"text": description, "type": "text"}],
                        }
                    ],
                },
            }
        }

        jira_json = json.dumps(template_text)

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
            jira_url + "/rest/api/3/issue/",
            "--request",
            "POST",
            "--data",
            jira_json,
            "--user",
            f"{jira_username}:{jira_api_token}",
        ]

        headers = {
            "Content-Type": "application/json",
        }

        self.add_curl_headers(curl_cmd, headers)

        count = 0
        while True:
            count += 1
            self.output(
                f"Jira API request post attempt {count}",
                verbose_level=2,
            )

            proc_stdout, _, status_code = self.execute_curl(curl_cmd)
            self.output(f"Curl command: {curl_cmd}", verbose_level=4)
            header = self.parse_headers(proc_stdout)

            # check HTTP response
            if self.jira_status_check(header) == "break":
                break
            if count >= max_tries:
                self.output(f"Jira request did not succeed after {max_tries} attempts")
                self.output(f"\nHTTP POST Response Code: {status_code}")
                raise ProcessorError("ERROR: Jira request failed to send")
            sleep(10)


if __name__ == "__main__":
    PROCESSOR = JamfUploaderJiraIssueCreator()
    PROCESSOR.execute_shell()
