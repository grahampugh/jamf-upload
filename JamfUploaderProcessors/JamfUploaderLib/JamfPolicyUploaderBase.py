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
import xml.etree.ElementTree as ElementTree

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


class JamfPolicyUploaderBase(JamfUploaderBase):
    """Class for functions used to upload a policy to Jamf"""

    def prepare_policy_template(
        self, jamf_url, policy_template, obj_id, token, retain_scope=False
    ):
        """prepare the policy contents"""
        # import template from file and replace any keys in the template
        if os.path.exists(policy_template):
            with open(policy_template, "r", encoding="utf-8") as file:
                template_contents = file.read()
        else:
            raise ProcessorError("Template does not exist!")

        # substitute user-assignable keys
        template_contents = self.substitute_assignable_keys(
            template_contents, xml_escape=True
        )

        # get existing scope if --retain-existing-scope is set
        object_type = "policy"
        if retain_scope and obj_id > 0:
            self.output("Substituting existing scope into template", verbose_level=1)
            existing_scope = self.get_existing_scope(
                jamf_url, object_type, obj_id, token
            )
            # substitute pre-existing scope
            template_contents = self.replace_scope(template_contents, existing_scope)

        self.output("Policy data:", verbose_level=3)
        self.output(template_contents, verbose_level=3)

        # write the template to temp file
        template_xml = self.write_temp_file(jamf_url, template_contents)
        return template_xml

    def upload_policy(
        self,
        jamf_url,
        policy_name,
        template_xml,
        token,
        sleep_time,
        obj_id=0,
    ):
        """Upload policy"""

        self.output("Uploading Policy...")

        # if we find an object ID we put, if not, we post
        object_type = "policy"
        url = f"{jamf_url}/{self.api_endpoints(object_type)}/id/{obj_id}"

        count = 0
        while True:
            count += 1
            self.output(f"Policy upload attempt {count}", verbose_level=2)
            request = "PUT" if obj_id else "POST"
            r = self.curl(
                request=request,
                url=url,
                token=token,
                data=template_xml,
            )
            # check HTTP response
            if self.status_check(r, "Policy", policy_name, request) == "break":
                break
            if count > 5:
                self.output("WARNING: Policy upload did not succeed after 5 attempts")
                self.output(f"\nHTTP POST Response Code: {r.status_code}")
                raise ProcessorError("ERROR: Policy upload failed ")
            if int(sleep_time) > 30:
                sleep(int(sleep_time))
            else:
                sleep(30)
        return r

    def upload_policy_icon(
        self,
        jamf_url,
        policy_name,
        policy_icon_path,
        replace_icon,
        token,
        sleep_time,
        obj_id=None,
    ):
        """Upload an icon to the policy that was just created"""
        # check that the policy exists.
        # Use the obj_id if we have it, or use name if we don't have it yet
        # We may need a wait loop here for new policies
        if not obj_id:
            # check for existing policy
            self.output(f"\nChecking '{policy_name}' on {jamf_url}")
            obj_type = "policy"
            obj_name = policy_name
            obj_id = self.get_api_obj_id_from_name(
                jamf_url,
                obj_type,
                obj_name,
                token=token,
            )

            if not obj_id:
                raise ProcessorError(
                    f"ERROR: could not locate ID for policy '{policy_name}' so cannot upload icon"
                )

        # Now grab the name of the existing icon using the API
        existing_icon = self.get_api_obj_value_from_id(
            jamf_url,
            "policy",
            obj_id,
            "self_service/self_service_icon/filename",
            token=token,
        )
        if existing_icon:
            self.output(f"Existing policy icon is '{existing_icon}'", verbose_level=1)
        # If the icon naame matches that we already have, don't upload again
        # unless --replace-icon is set
        policy_icon_name = os.path.basename(policy_icon_path)
        if existing_icon == policy_icon_name:
            self.output(f"Policy icon '{existing_icon}' already exists: ID {obj_id}")

        if existing_icon != policy_icon_name or replace_icon:
            object_type = "policy_icon"
            url = f"{jamf_url}/{self.api_endpoints(object_type)}/id/{obj_id}"

            self.output("Uploading icon...")

            count = 0
            while True:
                count += 1
                self.output(f"Icon upload attempt {count}", verbose_level=2)
                request = "POST"
                r = self.curl(
                    request=request,
                    url=url,
                    token=token,
                    data=policy_icon_path,
                    endpoint_type="policy_icon",
                )

                # check HTTP response
                if self.status_check(r, "Icon", policy_icon_name, request) == "break":
                    break
                if count > 5:
                    print("WARNING: Icon upload did not succeed after 5 attempts")
                    print(f"\nHTTP POST Response Code: {r.status_code}")
                    raise ProcessorError("ERROR: Icon upload failed")
                if int(sleep_time) > 30:
                    sleep(int(sleep_time))
                else:
                    sleep(30)
        else:
            self.output("Not replacing icon. Set replace_icon='True' to enforce...")
        return policy_icon_name

    def execute(self):
        """Upload a policy"""
        jamf_url = self.env.get("JSS_URL").rstrip("/")
        jamf_user = self.env.get("API_USERNAME")
        jamf_password = self.env.get("API_PASSWORD")
        client_id = self.env.get("CLIENT_ID")
        client_secret = self.env.get("CLIENT_SECRET")
        policy_name = self.env.get("policy_name")
        policy_template = self.env.get("policy_template")
        icon = self.env.get("icon")
        replace_policy = self.to_bool(self.env.get("replace_policy"))
        retain_scope = self.to_bool(self.env.get("retain_scope"))
        sleep_time = self.env.get("sleep")
        replace_icon = self.to_bool(self.env.get("replace_icon"))
        policy_updated = False

        # clear any pre-existing summary result
        if "jamfpolicyuploader_summary_result" in self.env:
            del self.env["jamfpolicyuploader_summary_result"]

        # handle files with a relative path
        if not policy_template.startswith("/"):
            found_template = self.get_path_to_file(policy_template)
            if found_template:
                policy_template = found_template
            else:
                raise ProcessorError(f"ERROR: Policy file {policy_template} not found")

        # we need to substitute the values in the policy name and template now to
        # account for version strings in the name
        # substitute user-assignable keys
        policy_name = self.substitute_assignable_keys(policy_name)

        # now start the process of uploading the object
        self.output(f"Checking for existing '{policy_name}' on {jamf_url}")

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
        obj_type = "policy"
        obj_name = policy_name
        obj_id = self.get_api_obj_id_from_name(
            jamf_url,
            obj_name,
            obj_type,
            token=token,
        )

        # we need to substitute the values in the template now to
        # account for version strings in the name
        template_xml = self.prepare_policy_template(
            jamf_url, policy_template, obj_id, token, retain_scope
        )

        if obj_id:
            self.output(f"Policy '{policy_name}' already exists: ID {obj_id}")
            if replace_policy:
                self.output(
                    f"Replacing existing policy as 'replace_policy' is set to True",
                    verbose_level=1,
                )
            else:
                self.output(
                    "Not replacing existing policy. Use replace_policy='True' to enforce.",
                    verbose_level=1,
                )
                return

        # upload the policy
        r = self.upload_policy(
            jamf_url,
            policy_name,
            template_xml,
            token,
            sleep_time,
            obj_id=obj_id,
        )
        policy_updated = True

        # Set the changed_policy_id to the returned output's ID if and only
        # if it can be determined
        try:
            changed_policy_id = ElementTree.fromstring(r.output).findtext("id")
            self.env["changed_policy_id"] = str(changed_policy_id)
        except UnboundLocalError:
            self.env["changed_policy_id"] = "UNKNOWN_POLICY_ID"

        # now upload the icon to the policy if specified in the args
        policy_icon_name = ""
        if icon:
            # handle files with a relative path
            if not icon.startswith("/"):
                found_icon = self.get_path_to_file(icon)
                if found_icon:
                    icon = found_icon
                else:
                    raise ProcessorError(f"ERROR: Policy icon file {icon} not found")

            # get the policy_id returned from the HTTP response
            try:
                policy_id = ElementTree.fromstring(r.output).findtext("id")
                policy_icon_name = self.upload_policy_icon(
                    jamf_url,
                    policy_name,
                    icon,
                    replace_icon,
                    token,
                    sleep_time,
                    policy_id,
                )
            except UnboundLocalError:
                policy_icon_name = self.upload_policy_icon(
                    jamf_url,
                    policy_name,
                    icon,
                    replace_icon,
                    token,
                    sleep_time,
                )

        # output the summary
        self.env["policy_name"] = policy_name
        self.env["policy_updated"] = policy_updated
        if policy_updated:
            self.env["jamfpolicyuploader_summary_result"] = {
                "summary_text": "The following policies were created or updated in Jamf Pro:",
                "report_fields": ["policy", "template", "icon", "icon_path"],
                "data": {
                    "policy": policy_name,
                    "template": policy_template,
                    "icon": policy_icon_name,
                    "icon_path": icon,
                },
            }
