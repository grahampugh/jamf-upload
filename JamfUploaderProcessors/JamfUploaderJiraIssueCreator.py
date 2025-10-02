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


__all__ = ["JamfUploaderJiraIssueCreator"]


class JamfUploaderJiraIssueCreator(JamfUploaderBase):
    description = (
        "A postprocessor for AutoPkg that will create a Jira issue based on the output of a "
        "JamfUploader process."
    )
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
                "Jira Issue Type. Default is 'Story'. See https://support.atlassian.com/jira/kb/finding-the-id-for-issue-types-in-jira-server-or-data-center/"
            ),
            "default": "10001",
        },
        "jira_priority_id": {
            "required": False,
            "description": (
                "Jira Priority. Default is the lowest priority. See https://support.atlassian.com/jira/kb/find-the-id-numbers-of-jira-priority-field-values-in-jira-cloud/"
            ),
            "default": "5",
        },
    }
    output_variables = {}

    __doc__ = description

    def jira_status_check(self, r):
        """Return a message dependent on the HTTP response"""
        if r.status_code == 200 or r.status_code == 201 or r.status_code == 202:
            self.output("Jira request sent successfully")
            return "break"
        self.output("WARNING: Jira request failed to send")
        self.output(r.output, verbose_level=2)

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

        enc_creds = self.get_enc_creds(jira_username, jira_api_token)

        count = 0
        while True:
            count += 1
            self.output(
                f"Jira API request post attempt {count}",
                verbose_level=2,
            )
            r = self.curl(
                request="POST",
                url=f"{jira_url}/rest/api/3/issue/",
                enc_creds=enc_creds,
                data=jira_json,
                endpoint_type="jira",
            )
            # check HTTP response
            if self.jira_status_check(r) == "break":
                break
            if count > 5:
                self.output("Jira request did not succeed after 5 attempts")
                self.output(f"\nHTTP POST Response Code: {r.status_code}")
                raise ProcessorError("ERROR: Jira request failed to send")
            sleep(10)


if __name__ == "__main__":
    PROCESSOR = JamfUploaderJiraIssueCreator()
    PROCESSOR.execute_shell()
