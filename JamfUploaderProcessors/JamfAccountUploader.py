#!/usr/local/autopkg/python

"""
JamfAccountUploader processor for uploading accounts (users and groups)
to Jamf Pro using AutoPkg
    by G Pugh
"""

import json
import os
import sys

from time import sleep
from autopkglib import ProcessorError  # pylint: disable=import-error

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfUploaderBase import JamfUploaderBase  # noqa: E402

__all__ = ["JamfAccountUploader"]


class JamfAccountUploader(JamfUploaderBase):
    description = (
        "A processor for AutoPkg that will create or update an account "
        "object on a Jamf Pro server."
        "'Jamf Pro User Accounts & Groups' CRU privileges are required by the API_USERNAME user."
    )
    input_variables = {
        "JSS_URL": {
            "required": True,
            "description": "URL to a Jamf Pro server that the API user has write access "
            "to, optionally set as a key in the com.github.autopkg "
            "preference file.",
        },
        "API_USERNAME": {
            "required": True,
            "description": "Username of account with appropriate access to "
            "jss, optionally set as a key in the com.github.autopkg "
            "preference file.",
        },
        "API_PASSWORD": {
            "required": True,
            "description": "Password of api user, optionally set as a key in "
            "the com.github.autopkg preference file.",
        },
        "account_name": {
            "required": True,
            "description": "account name",
            "default": "",
        },
        "account_type": {
            "required": True,
            "description": "account type - either 'user' or 'group",
            "default": "user",
        },
        "account_template": {
            "required": True,
            "description": "Full path to the XML template",
        },
        "replace_account": {
            "required": False,
            "description": "Overwrite an existing account if True.",
            "default": False,
        },
        "sleep": {
            "required": False,
            "description": "Pause after running this processor for specified seconds.",
            "default": "0",
        },
    }

    output_variables = {
        "jamfaccountuploader_summary_result": {
            "description": "Description of interesting results.",
        },
        "account_name": {
            "description": "Jamf object name of the newly created or modified account.",
        },
        "account_updated": {
            "description": "Boolean - True if the account was changed."
        },
        "changed_account_id": {
            "description": "Jamf object ID of the newly created or modified account.",
        },
    }

    def get_account_id_from_name(
        self, jamf_url, object_name, account_type, enc_creds="", token=""
    ):
        """check if an account with the same name exists on the server.
        This function is different to get_api_obj_id_from_name because we need to check inside
        users/groups"""
        # define the relationship between the object types and their URL
        object_type = "account"
        url = jamf_url + "/" + self.api_endpoints(object_type)
        r = self.curl(request="GET", url=url, enc_creds=enc_creds, token=token)

        if r.status_code == 200:
            object_list = json.loads(r.output)
            self.output(
                object_list,
                verbose_level=4,
            )
            obj_id = 0
            if account_type == "user":
                object_subtype = "users"
            elif account_type == "group":
                object_subtype = "groups"

            self.output(f"Object name: {object_name}")  # TEMP

            for obj in object_list[self.object_list_types(object_type)][object_subtype]:
                # we need to check for a case-insensitive match
                self.output(f"Object name in list: {obj['name']}")  # TEMP

                if obj["name"].lower() == object_name.lower():
                    obj_id = obj["id"]
            return obj_id
        elif r.status_code == 401:
            raise ProcessorError(
                "ERROR: Jamf returned status code '401' - Access denied."
            )

    def prepare_account_template(self, account_name, account_template):
        """prepare the account contents"""
        # import template from file and replace any keys in the template
        if os.path.exists(account_template):
            with open(account_template, "r") as file:
                template_contents = file.read()
        else:
            raise ProcessorError("Template does not exist!")

        # substitute user-assignable keys
        account_name = self.substitute_assignable_keys(account_name)
        template_contents = self.substitute_assignable_keys(
            template_contents, xml_escape=True
        )

        self.output("account data:", verbose_level=2)
        self.output(template_contents, verbose_level=2)

        # write the template to temp file
        template_xml = self.write_temp_file(template_contents)
        return account_name, template_xml

    def upload_account(
        self,
        jamf_url,
        account_name,
        object_type,
        template_xml,
        obj_id=0,
        enc_creds="",
        token="",
    ):
        """Upload account"""

        self.output(f"Uploading {object_type}...")

        # if we find an object ID we put, if not, we post
        url = "{}/JSSResource/accounts/{}id/{}".format(jamf_url, object_type, obj_id)

        count = 0
        while True:
            count += 1
            self.output(
                "{} upload attempt {}".format(object_type, count), verbose_level=2
            )
            request = "PUT" if obj_id else "POST"
            r = self.curl(
                request=request,
                url=url,
                enc_creds=enc_creds,
                token=token,
                data=template_xml,
            )
            # check HTTP response
            if self.status_check(r, object_type, account_name, request) == "break":
                break
            if count > 5:
                self.output(
                    f"WARNING: {object_type} upload did not succeed after 5 attempts"
                )
                self.output("\nHTTP POST Response Code: {}".format(r.status_code))
                raise ProcessorError(f"ERROR: {object_type} upload failed ")
            if int(self.sleep) > 30:
                sleep(int(self.sleep))
            else:
                sleep(30)
        return r

    def main(self):
        """Do the main thing here"""
        self.jamf_url = self.env.get("JSS_URL")
        self.jamf_user = self.env.get("API_USERNAME")
        self.jamf_password = self.env.get("API_PASSWORD")
        self.account_name = self.env.get("account_name")
        self.account_type = self.env.get("account_type")
        self.account_template = self.env.get("account_template")
        self.replace = self.env.get("replace_account")
        self.sleep = self.env.get("sleep")
        # handle setting replace in overrides
        if not self.replace or self.replace == "False":
            self.replace = False
        self.account_updated = False

        # clear any pre-existing summary result
        if "jamfaccountuploader_summary_result" in self.env:
            del self.env["jamfaccountuploader_summary_result"]

        # handle files with a relative path
        if not self.account_template.startswith("/"):
            found_template = self.get_path_to_file(self.account_template)
            if found_template:
                self.account_template = found_template
            else:
                raise ProcessorError(
                    f"ERROR: Policy file {self.account_template} not found"
                )

        # we need to substitute the values in the account name and template now to
        # account for version strings in the name
        self.account_name, template_xml = self.prepare_account_template(
            self.account_name, self.account_template
        )

        # now start the process of uploading the object
        self.output(f"Checking for existing '{self.account_name}' on {self.jamf_url}")

        token, send_creds, _ = self.handle_classic_auth(
            self.jamf_url, self.jamf_user, self.jamf_password
        )

        # check for existing - requires obj_name and account type
        obj_id = self.get_account_id_from_name(
            self.jamf_url,
            self.account_name,
            self.account_type,
            enc_creds=send_creds,
            token=token,
        )

        if obj_id:
            self.output(
                "account '{}' already exists: ID {}".format(self.account_name, obj_id)
            )
            if self.replace:
                self.output(
                    "Replacing existing account as 'replace_account' is set to {}".format(
                        self.replace
                    ),
                    verbose_level=1,
                )
            else:
                self.output(
                    "Not replacing existing account. Use replace_account='True' to enforce.",
                    verbose_level=1,
                )
                return

        # upload the account
        self.upload_account(
            self.jamf_url,
            self.account_name,
            self.account_type,
            template_xml,
            obj_id=obj_id,
            enc_creds=send_creds,
            token=token,
        )
        self.account_updated = True

        # output the summary
        self.env["account_name"] = self.account_name
        self.env["account_type"] = self.account_type
        self.env["account_updated"] = self.account_updated
        if self.account_updated:
            self.env["jamfaccountuploader_summary_result"] = {
                "summary_text": "The following accounts were updated in Jamf Pro:",
                "report_fields": ["account", "template"],
                "data": {
                    "account": self.account_name,
                    "template": self.account_template,
                },
            }


if __name__ == "__main__":
    PROCESSOR = JamfAccountUploader()
    PROCESSOR.execute_shell()
