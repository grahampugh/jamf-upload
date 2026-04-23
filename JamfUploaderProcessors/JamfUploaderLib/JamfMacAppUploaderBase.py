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

import json
import os.path
import re
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


class JamfMacAppUploaderBase(JamfUploaderBase):
    """Class for functions used to upload a mac app to Jamf"""

    def prepare_macapp_template(self, api_url, macapp_name, macapp_template):
        """prepare the macapp contents"""
        # import template from file and replace any keys in the template
        if os.path.exists(macapp_template):
            with open(macapp_template, "r", encoding="utf-8") as file:
                template_contents = file.read()
        else:
            raise ProcessorError("Template does not exist!")

        # substitute user-assignable keys
        macapp_name = self.substitute_assignable_keys(macapp_name)
        template_contents = self.substitute_assignable_keys(
            template_contents, xml_escape=True
        )

        self.output("MAS app data:", verbose_level=2)
        self.output(template_contents, verbose_level=2)

        # write the template to temp file
        template_xml = self.write_temp_file(api_url, template_contents)
        return macapp_name, template_xml

    def upload_macapp(
        self,
        api_url,
        object_name,
        object_template,
        sleep_time,
        token,
        max_tries,
        object_id=0,
        tenant_id="",
    ):
        """Upload MAS app"""

        self.output("Uploading MAS app...")

        object_type = "mac_application"
        endpoint = self.api_endpoints(object_type, tenant_id=tenant_id)
        # if we find an object ID we put, if not, we post
        url = f"{api_url}/{endpoint}/id/{object_id}"

        count = 0
        while True:
            count += 1
            self.output(f"MAS app upload attempt {count}", verbose_level=2)
            request = "PUT" if object_id else "POST"
            r = self.curl(
                api_type="classic",
                request=request,
                url=url,
                token=token,
                data=object_template,
            )
            # check HTTP response
            if self.status_check(r, "mac_application", object_name, request) == "break":
                break
            if count >= max_tries:
                self.output(
                    f"WARNING: MAS app upload did not succeed after {max_tries} attempts"
                )
                self.output(f"\nHTTP POST Response Code: {r.status_code}")
                raise ProcessorError("ERROR: Mac app upload failed ")
            if int(sleep_time) > 10:
                sleep(int(sleep_time))
            else:
                sleep(10)
        return r

    def execute(self):
        """Upload a mac app"""
        jamf_url = (self.env.get("JSS_URL") or "").rstrip("/")
        jamf_user = self.env.get("API_USERNAME")
        jamf_password = self.env.get("API_PASSWORD")
        jamf_platform_gw_region = self.env.get("PLATFORM_API_REGION")
        jamf_platform_gw_tenant_id = self.env.get("PLATFORM_API_TENANT_ID")
        client_id = self.env.get("CLIENT_ID")
        client_secret = self.env.get("CLIENT_SECRET")
        bearer_token = self.env.get("BEARER_TOKEN")
        jamf_cli_profile = self.env.get("JAMF_CLI_PROFILE")
        macapp_name = self.env.get("macapp_name")
        clone_from = self.env.get("clone_from")
        selfservice_icon_uri = self.env.get("selfservice_icon_uri")
        macapp_template = self.env.get("macapp_template")
        preferred_vpp_location = self.env.get("preferred_volume_purchase_location")
        replace_macapp = self.to_bool(self.env.get("replace_macapp"))
        sleep_time = self.env.get("sleep")
        macapp_updated = False
        max_tries = self.env.get("max_tries")

        # verify that max_tries is an integer greater than zero and less than 10
        try:
            max_tries = int(max_tries)
            if max_tries < 1 or max_tries > 10:
                raise ValueError
        except (ValueError, TypeError):
            max_tries = 5

        # clear any pre-existing summary result
        if "jamfmacappuploader_summary_result" in self.env:
            del self.env["jamfmacappuploader_summary_result"]

        # handle files with a relative path
        if not macapp_template.startswith("/"):
            found_template = self.get_path_to_file(macapp_template)
            if found_template:
                macapp_template = found_template
            else:
                raise ProcessorError(f"ERROR: Policy file {macapp_template} not found")

        # now start the process of uploading the object
        self.output(f"Checking for existing '{macapp_name}' on {jamf_url}")

        # get token using oauth or basic auth depending on the credentials given
        if jamf_url:
            token, jamf_url, jamf_platform_gw_region, jamf_platform_gw_tenant_id = (
                self.auth(
                    jamf_url,
                    jamf_user=jamf_user,
                    password=jamf_password,
                    client_id=client_id,
                    client_secret=client_secret,
                    token=bearer_token,
                    jamf_cli_profile=jamf_cli_profile,
                )
            )
        else:
            raise ProcessorError("ERROR: Jamf Pro URL not supplied")

        # construct the api_url based on the API type
        api_url = self.construct_api_url(
            jamf_url=jamf_url, region=jamf_platform_gw_region
        )
        self.output(f"API URL is {api_url}", verbose_level=3)

        # check for existing - requires object_name
        object_id = self.get_api_object_id_from_name(
            api_url,
            object_type="mac_application",
            object_name=macapp_name,
            token=token,
            tenant_id=jamf_platform_gw_tenant_id,
        )

        if object_id:
            self.output(f"MAS app '{macapp_name}' already exists: ID {object_id}")
            if replace_macapp:
                self.output(
                    "Replacing existing MAS app as 'replace_macapp' is set to True",
                    verbose_level=1,
                )

                # obtain the MAS app bundleid
                bundleid = self.get_api_object_value_from_id(
                    api_url,
                    object_type="mac_application",
                    object_id=object_id,
                    object_path="general/bundle_id",
                    token=token,
                    tenant_id=jamf_platform_gw_tenant_id,
                )
                if bundleid:
                    self.output(f"Existing bundle ID is '{bundleid}'", verbose_level=1)
                # obtain the MAS app version
                macapp_version = self.get_api_object_value_from_id(
                    api_url,
                    object_type="mac_application",
                    object_id=object_id,
                    object_path="general/version",
                    token=token,
                    tenant_id=jamf_platform_gw_tenant_id,
                )
                if macapp_version:
                    self.output(
                        f"Existing MAS app version is '{macapp_version}'",
                        verbose_level=1,
                    )
                # obtain the MAS app free status
                macapp_is_free = self.get_api_object_value_from_id(
                    api_url,
                    object_type="mac_application",
                    object_id=object_id,
                    object_path="general/is_free",
                    token=token,
                    tenant_id=jamf_platform_gw_tenant_id,
                )
                if macapp_is_free:
                    self.output(
                        f"Existing MAS app free status is '{macapp_is_free}'",
                        verbose_level=1,
                    )
                # obtain the MAS app URL
                appstore_url = self.get_api_object_value_from_id(
                    api_url,
                    object_type="mac_application",
                    object_id=object_id,
                    object_path="general/url",
                    token=token,
                    tenant_id=jamf_platform_gw_tenant_id,
                )
                if appstore_url:
                    self.output(
                        f"Existing MAS URL is '{appstore_url}'", verbose_level=1
                    )
                # obtain the MAS app icon
                if not selfservice_icon_uri:
                    selfservice_icon_uri = self.get_api_object_value_from_id(
                        api_url,
                        object_type="mac_application",
                        object_id=object_id,
                        object_path="self_service/self_service_icon/uri",
                        token=token,
                        tenant_id=jamf_platform_gw_tenant_id,
                    )
                    if selfservice_icon_uri:
                        self.output(
                            f"Existing Self Service icon is '{selfservice_icon_uri}'",
                            verbose_level=1,
                        )
                # obtain the VPP location
                self.output("Obtaining VPP ID", verbose_level=2)
                vpp_id = self.get_vpp_id(
                    api_url,
                    token,
                    store_url=appstore_url,
                    preferred_location=preferred_vpp_location,
                    tenant_id=jamf_platform_gw_tenant_id,
                )
                if vpp_id:
                    self.output(
                        f"Existing VPP ID is '{vpp_id}'",
                        verbose_level=1,
                    )
                else:
                    self.output("Didn't retrieve a VPP ID", verbose_level=2)
                    adam_id = self._extract_adam_id(appstore_url)
                    preferred_note = (
                        f" matching '{preferred_vpp_location}'"
                        if preferred_vpp_location
                        else ""
                    )
                    detail = (
                        f"for adam ID '{adam_id}'"
                        if adam_id
                        else "for the supplied app"
                    )
                    raise ProcessorError(
                        "ERROR: No Volume Purchasing content found "
                        f"{detail}{preferred_note}."
                    )

                # we need to substitute the values in the MAS app name and template now to
                # account for URL and Bundle ID
                self.env["macapp_name"] = macapp_name
                self.env["macapp_version"] = macapp_version
                self.env["macapp_is_free"] = str(macapp_is_free)
                self.env["bundleid"] = bundleid
                self.env["appstore_url"] = appstore_url
                self.env["selfservice_icon_uri"] = selfservice_icon_uri
                self.env["vpp_id"] = vpp_id
                macapp_name, template_xml = self.prepare_macapp_template(
                    jamf_url, macapp_name, macapp_template
                )

                # upload the macapp
                self.upload_macapp(
                    api_url,
                    object_name=macapp_name,
                    object_template=template_xml,
                    sleep_time=sleep_time,
                    token=token,
                    max_tries=max_tries,
                    object_id=object_id,
                    tenant_id=jamf_platform_gw_tenant_id,
                )
                macapp_updated = True

                # output the summary
                self.env["macapp_name"] = macapp_name
                self.env["macapp_updated"] = macapp_updated
                if macapp_updated:
                    self.env["jamfmacappuploader_summary_result"] = {
                        "summary_text": "The following MAS apps were updated in Jamf Pro:",
                        "report_fields": ["macapp", "template"],
                        "data": {
                            "macapp": macapp_name,
                            "template": macapp_template,
                        },
                    }
            else:
                self.output(
                    "Not replacing existing MAS app. Use replace_macapp='True' to enforce.",
                    verbose_level=1,
                )
                return
        elif clone_from:
            # check for existing - requires object_name
            object_id = self.get_api_object_id_from_name(
                api_url,
                object_type="mac_application",
                object_name=clone_from,
                token=token,
                tenant_id=jamf_platform_gw_tenant_id,
            )
            if object_id:
                self.output(f"MAS app '{clone_from}' already exists: ID {object_id}")

                # obtain the MAS app bundleid
                bundleid = self.get_api_object_value_from_id(
                    api_url,
                    object_type="mac_application",
                    object_id=object_id,
                    object_path="general/bundle_id",
                    token=token,
                    tenant_id=jamf_platform_gw_tenant_id,
                )
                if bundleid:
                    self.output(f"Existing bundle ID is '{bundleid}'", verbose_level=1)
                # obtain the MAS app version
                macapp_version = self.get_api_object_value_from_id(
                    api_url,
                    object_type="mac_application",
                    object_id=object_id,
                    object_path="general/version",
                    token=token,
                    tenant_id=jamf_platform_gw_tenant_id,
                )
                if macapp_version:
                    self.output(
                        f"Existing MAS app version is '{macapp_version}'",
                        verbose_level=1,
                    )
                # obtain the MAS app free status
                macapp_is_free = self.get_api_object_value_from_id(
                    api_url,
                    object_type="mac_application",
                    object_id=object_id,
                    object_path="general/is_free",
                    token=token,
                    tenant_id=jamf_platform_gw_tenant_id,
                )
                if macapp_is_free:
                    self.output(
                        f"Existing MAS app free status is '{macapp_is_free}'",
                        verbose_level=1,
                    )
                # obtain the MAS app URL
                appstore_url = self.get_api_object_value_from_id(
                    api_url,
                    object_type="mac_application",
                    object_id=object_id,
                    object_path="general/url",
                    token=token,
                    tenant_id=jamf_platform_gw_tenant_id,
                )
                if appstore_url:
                    self.output(
                        f"Existing MAS URL is '{appstore_url}'", verbose_level=1
                    )
                # obtain the MAS app icon
                if not selfservice_icon_uri:
                    selfservice_icon_uri = self.get_api_object_value_from_id(
                        api_url,
                        object_type="mac_application",
                        object_id=object_id,
                        object_path="self_service/self_service_icon/uri",
                        token=token,
                        tenant_id=jamf_platform_gw_tenant_id,
                    )
                    if selfservice_icon_uri:
                        self.output(
                            f"Existing Self Service icon is '{selfservice_icon_uri}'",
                            verbose_level=1,
                        )

                # obtain the VPP location
                self.output("Obtaining VPP ID", verbose_level=2)
                vpp_id = self.get_vpp_id(
                    api_url,
                    token,
                    store_url=appstore_url,
                    preferred_location=preferred_vpp_location,
                    tenant_id=jamf_platform_gw_tenant_id,
                )
                if vpp_id:
                    self.output(
                        f"Existing VPP ID is '{vpp_id}'",
                        verbose_level=1,
                    )
                else:
                    self.output("Didn't retrieve a VPP ID", verbose_level=2)
                    adam_id = self._extract_adam_id(appstore_url)
                    preferred_note = (
                        f" matching '{preferred_vpp_location}'"
                        if preferred_vpp_location
                        else ""
                    )
                    detail = (
                        f"for adam ID '{adam_id}'"
                        if adam_id
                        else "for the supplied app"
                    )
                    raise ProcessorError(
                        "ERROR: No Volume Purchasing content found "
                        f"{detail}{preferred_note}."
                    )

                # we need to substitute the values in the MAS app name and template now to
                # account for URL and Bundle ID
                self.env["macapp_name"] = macapp_name
                self.env["macapp_version"] = macapp_version
                self.env["macapp_is_free"] = str(macapp_is_free)
                self.env["bundleid"] = bundleid
                self.env["appstore_url"] = appstore_url
                self.env["selfservice_icon_uri"] = selfservice_icon_uri
                self.env["vpp_id"] = vpp_id
                macapp_name, template_xml = self.prepare_macapp_template(
                    jamf_url, macapp_name, macapp_template
                )

                # upload the macapp
                self.upload_macapp(
                    api_url,
                    object_name=macapp_name,
                    object_template=template_xml,
                    sleep_time=sleep_time,
                    token=token,
                    max_tries=max_tries,
                    object_id=0,
                    tenant_id=jamf_platform_gw_tenant_id,
                )
                macapp_updated = True

                # output the summary
                self.env["macapp_name"] = macapp_name
                self.env["macapp_updated"] = macapp_updated
                if macapp_updated:
                    self.env["jamfmacappuploader_summary_result"] = {
                        "summary_text": "The following MAS apps were updated in Jamf Pro:",
                        "report_fields": ["macapp", "template"],
                        "data": {
                            "macapp": macapp_name,
                            "template": macapp_template,
                        },
                    }
            else:
                self.output(
                    "No existing MAS app item in Jamf from which to clone.",
                    verbose_level=1,
                )
                return

        else:
            self.output(
                "No existing MAS app item in Jamf. This must be assigned in Apple "
                "Business Manager or Apple School Manager",
                verbose_level=1,
            )
            return
