#!/usr/local/autopkg/python

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
import re
import os.path
import subprocess

from collections import namedtuple
from shutil import rmtree
from time import sleep
from autopkglib import Processor, ProcessorError  # pylint: disable=import-error


__all__ = ["JamfUploaderSlacker"]


class JamfUploaderSlacker(Processor):
    description = (
        "Posts to Slack via webhook based on output of a JamfPolicyUploader process. "
        "Takes elements from "
        "https://gist.github.com/devStepsize/b1b795309a217d24566dcc0ad136f784 "
        "and "
        "https://github.com/autopkg/nmcspadden-recipes/blob/master/PostProcessors/Yo.py"
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
        "version": {"required": True, "description": ("Product version.")},
        "pkg_name": {"required": True, "description": ("Package in policy.")},
        "jamfpackageuploader_summary_result": {
            "required": False,
            "description": ("Summary results of package processors."),
        },
        "jamfpolicyuploader_summary_result": {
            "required": False,
            "description": ("Summary results of policy processors."),
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
            "description": ("Slack channel (of overriding the default)."),
        },
        "slack_icon_emoji": {
            "required": False,
            "description": ("Slack display emoji markup."),
        },
    }
    output_variables = {}

    __doc__ = description

    def make_tmp_dir(self, tmp_dir="/tmp/jamf_upload"):
        """make the tmp directory"""
        if not os.path.exists(tmp_dir):
            os.mkdir(tmp_dir)
        return tmp_dir

    def clear_tmp_dir(self, tmp_dir="/tmp/jamf_upload"):
        """remove the tmp directory"""
        if os.path.exists(tmp_dir):
            rmtree(tmp_dir)
        return tmp_dir

    def curl(self, url, data):
        """
        build a curl command based on method (GET, PUT, POST, DELETE)
        If the URL contains 'uapi' then token should be passed to the auth variable,
        otherwise the enc_creds variable should be passed to the auth variable
        """
        tmp_dir = self.make_tmp_dir()
        headers_file = os.path.join(tmp_dir, "curl_headers_from_jamf_upload.txt")
        output_file = os.path.join(tmp_dir, "curl_output_from_jamf_upload.txt")

        # build the curl command
        curl_cmd = [
            "/usr/bin/curl",
            "-X",
            "POST",
            "-D",
            headers_file,
            "--output",
            output_file,
            url,
        ]

        if data:
            curl_cmd.extend(["--data", data])
            curl_cmd.extend(["--header", "Content-type: application/json"])

        self.output(f"curl command: {' '.join(curl_cmd)}", verbose_level=2)

        # now subprocess the curl command and build the r tuple which contains the
        # headers, status code and outputted data
        subprocess.check_output(curl_cmd)

        r = namedtuple(
            "r", ["headers", "status_code", "output"], defaults=(None, None, None)
        )
        try:
            with open(headers_file, "r") as file:
                headers = file.readlines()
            r.headers = [x.strip() for x in headers]
            for header in r.headers:  # pylint: disable=not-an-iterable
                if re.match(r"HTTP/(1.1|2)", header) and "Continue" not in header:
                    r.status_code = int(header.split()[1])
        except IOError:
            raise ProcessorError(f"WARNING: {headers_file} not found")
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            with open(output_file, "rb") as file:
                r.output = file.read()
        else:
            self.output(f"No output from request ({output_file} not found or empty)")
        return r()

    def status_check(self, r):
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

        slack_username = self.env.get("slack_username")
        slack_icon_url = self.env.get("slack_icon_url") or ""
        slack_webhook_url = self.env.get("slack_webhook_url")
        slack_channel = self.env.get("slack_channel") or ""
        slack_icon_emoji = self.env.get("slack_icon_emoji") or ""

        selfservice_policy_name = name
        self.output(f"JSS address: {jss_url}")
        self.output(f"Title: {selfservice_policy_name}")
        self.output(f"Policy: {policy_name}")
        self.output(f"Version: {version}")
        self.output(f"Package: {pkg_name}")
        self.output(f"Package Category: {category}")
        self.output(f"Policy Category: {policy_category}")

        if jamfpackageuploader_summary_result and jamfpolicyuploader_summary_result:
            slack_text = (
                "*New Item uploaded to Jamf Pro:*\n"
                + f"URL: {jss_url}\n"
                + f"Title: *{selfservice_policy_name}*\n"
                + f"Version: *{version}*\n"
                + f"Category: *{category}*\n"
                + f"Policy Name: *{policy_name}*\n"
                + f"Package: *{pkg_name}*"
            )
        elif jamfpolicyuploader_summary_result:
            slack_text = (
                "*New Item uploaded to Jamf Pro:*\n"
                + f"URL: {jss_url}\n"
                + f"Title: *{selfservice_policy_name}*\n"
                + f"Category: *{category}*\n"
                + f"Policy Name: *{policy_name}*\n"
                + "No new package uploaded"
            )
        elif jamfpackageuploader_summary_result:
            slack_text = (
                "*New Item uploaded to Jamf Pro:*\n"
                + f"URL: {jss_url}\n"
                + f"Version: *{version}*\n"
                + f"Category: *{category}*\n"
                + f"Package: *{pkg_name}*"
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
                "Slack webhook post attempt {}".format(count), verbose_level=2,
            )
            r = self.curl(slack_webhook_url, slack_json)
            # check HTTP response
            if self.status_check(r) == "break":
                break
            if count > 5:
                self.output("Slack webhook send did not succeed after 5 attempts")
                self.output("\nHTTP POST Response Code: {}".format(r.status_code))
                raise ProcessorError("ERROR: Slack webhook failed to send")
            sleep(10)

        # clean up temp files
        self.clear_tmp_dir()


if __name__ == "__main__":
    PROCESSOR = JamfUploaderSlacker()
    PROCESSOR.execute_shell()
