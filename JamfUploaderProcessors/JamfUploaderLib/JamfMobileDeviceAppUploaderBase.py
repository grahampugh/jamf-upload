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


class JamfMobileDeviceAppUploaderBase(JamfUploaderBase):
    """Class for functions used to upload a mobile device app to Jamf"""

    def get_vpp_id(self, jamf_url, token):
        """Get the first Volume Purchasing Location ID."""
        url_filter = "?page=0&page-size=100&sort=id"
        object_type = "volume_purchasing_location"
        url = jamf_url + "/" + self.api_endpoints(object_type) + url_filter
        r = self.curl(request="GET", url=url, token=token)
        if r.status_code == 200:
            obj_id = 0
            # output = json.loads(r.output)
            output = r.output
            for obj in output["results"]:
                self.output(f"ID: {obj['id']} NAME: {obj['name']}", verbose_level=3)
                obj_id = obj["id"]
            return obj_id
        else:
            self.output(f"Return code: {r.status_code}", verbose_level=2)

    def make_escaped_appconfig_from_template(self, appconfig_template):
        """create xml escaped appconfig data using a template file"""
        if not appconfig_template.startswith("/"):
            found_template = self.get_path_to_file(appconfig_template)
            if found_template:
                appconfig_template = found_template
                with open(appconfig_template, "r", encoding="utf-8") as file:
                    appconfig_xml = file.read()

                # substitute user assignable keys and escape XML
                appconfig = self.substitute_assignable_keys(
                    appconfig_xml, xml_escape=True
                )
                self.output("AppConfig written into template")
                return appconfig
            else:
                raise ProcessorError(
                    f"ERROR: AppConfig XML file {appconfig_template} not found"
                )

    def prepare_mobiledeviceapp_template(
        self, jamf_url, mobiledeviceapp_name, mobiledeviceapp_template
    ):
        """prepare the mobiledeviceapp contents"""
        # import template from file and replace any keys in the template
        if os.path.exists(mobiledeviceapp_template):
            with open(mobiledeviceapp_template, "r", encoding="utf-8") as file:
                template_contents = file.read()
        else:
            raise ProcessorError("Template does not exist!")

        # substitute user-assignable keys
        mobiledeviceapp_name = self.substitute_assignable_keys(mobiledeviceapp_name)
        template_contents = self.substitute_assignable_keys(
            template_contents, xml_escape=True
        )

        self.output("Mobile device app data:", verbose_level=2)
        self.output(template_contents, verbose_level=2)

        # write the template to temp file
        template_xml = self.write_temp_file(jamf_url, template_contents)
        return mobiledeviceapp_name, template_xml

    def upload_mobiledeviceapp(
        self,
        jamf_url,
        mobiledeviceapp_name,
        template_xml,
        sleep_time,
        token,
        obj_id=0,
    ):
        """Upload Mobile device app"""

        self.output("Uploading Mobile device app...")

        # if we find an object ID we put, if not, we post
        object_type = "mobile_device_application"
        url = f"{jamf_url}/{self.api_endpoints(object_type)}/id/{obj_id}"

        count = 0
        while True:
            count += 1
            self.output(f"Mobile device app upload attempt {count}", verbose_level=2)
            request = "PUT" if obj_id else "POST"
            r = self.curl(
                request=request,
                url=url,
                token=token,
                data=template_xml,
            )
            # check HTTP response
            if (
                self.status_check(
                    r, "mobile_device_application", mobiledeviceapp_name, request
                )
                == "break"
            ):
                break
            if count > 5:
                self.output(
                    "WARNING: Mobile device app upload did not succeed after 5 attempts"
                )
                self.output(f"\nHTTP POST Response Code: {r.status_code}")
                raise ProcessorError("ERROR: Mobile device app upload failed ")
            if int(sleep_time) > 30:
                sleep(int(sleep_time))
            else:
                sleep(30)
        return r

    def execute(self):
        """Upload a mobile device app"""
        jamf_url = self.env.get("JSS_URL").rstrip("/")
        jamf_user = self.env.get("API_USERNAME")
        jamf_password = self.env.get("API_PASSWORD")
        client_id = self.env.get("CLIENT_ID")
        client_secret = self.env.get("CLIENT_SECRET")
        mobiledeviceapp_name = self.env.get("mobiledeviceapp_name")
        clone_from = self.env.get("clone_from")
        selfservice_icon_uri = self.env.get("selfservice_icon_uri")
        mobiledeviceapp_template = self.env.get("mobiledeviceapp_template")
        appconfig_template = self.env.get("appconfig_template")
        replace_mobiledeviceapp = self.to_bool(self.env.get("replace_mobiledeviceapp"))
        sleep_time = self.env.get("sleep")
        mobiledeviceapp_updated = False

        # clear any pre-existing summary result
        if "jamfmobiledeviceappuploader_summary_result" in self.env:
            del self.env["jamfmobiledeviceappuploader_summary_result"]

        # handle files with a relative path
        if not mobiledeviceapp_template.startswith("/"):
            found_template = self.get_path_to_file(mobiledeviceapp_template)
            if found_template:
                mobiledeviceapp_template = found_template
            else:
                raise ProcessorError(
                    f"ERROR: Mobile device app file {mobiledeviceapp_template} not found"
                )

        # now start the process of uploading the object
        self.output(f"Checking for existing '{mobiledeviceapp_name}' on {jamf_url}")

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
        obj_type = "mobile_device_application"
        obj_name = mobiledeviceapp_name
        obj_id = self.get_api_obj_id_from_name(
            jamf_url,
            obj_name,
            obj_type,
            token=token,
        )

        if obj_id:
            self.output(
                f"Mobile device app '{mobiledeviceapp_name}' already exists: ID {obj_id}"
            )
            if replace_mobiledeviceapp:
                self.output(
                    f"Replacing existing Mobile device app as 'replace_mobiledeviceapp' "
                    f"is set to True",
                    verbose_level=1,
                )

                # obtain the Mobile device app bundleid
                bundleid = self.get_api_obj_value_from_id(
                    jamf_url,
                    "mobile_device_application",
                    obj_id,
                    "general/bundle_id",
                    token=token,
                )
                if bundleid:
                    self.output(f"Existing bundle ID is '{bundleid}'", verbose_level=1)
                # obtain the Mobile device app version
                mobiledeviceapp_version = self.get_api_obj_value_from_id(
                    jamf_url,
                    "mobile_device_application",
                    obj_id,
                    "general/version",
                    token=token,
                )
                if mobiledeviceapp_version:
                    self.output(
                        f"Existing Mobile device app version is '{mobiledeviceapp_version}'",
                        verbose_level=1,
                    )
                # obtain the Mobile device app free status
                mobiledeviceapp_free = self.get_api_obj_value_from_id(
                    jamf_url,
                    "mobile_device_application",
                    obj_id,
                    "general/free",
                    token=token,
                )
                if mobiledeviceapp_free:
                    self.output(
                        f"Existing Mobile device app free status is '{mobiledeviceapp_free}'",
                        verbose_level=1,
                    )
                # obtain the Mobile device app URL
                itunes_store_url = self.get_api_obj_value_from_id(
                    jamf_url,
                    "mobile_device_application",
                    obj_id,
                    "general/itunes_store_url",
                    token=token,
                )
                if itunes_store_url:
                    self.output(
                        f"Existing Mobile device URL is '{itunes_store_url}'",
                        verbose_level=1,
                    )
                # obtain the Mobile device app icon
                if not selfservice_icon_uri:
                    selfservice_icon_uri = self.get_api_obj_value_from_id(
                        jamf_url,
                        "mobile_device_application",
                        obj_id,
                        "self_service/self_service_icon/uri",
                        token=token,
                    )
                    if selfservice_icon_uri:
                        self.output(
                            f"Existing Self Service icon is '{selfservice_icon_uri}'",
                            verbose_level=1,
                        )
                # obtain the VPP location
                self.output("Obtaining VPP ID", verbose_level=2)
                vpp_id = self.get_vpp_id(jamf_url, token)
                if vpp_id:
                    self.output(
                        f"Existing VPP ID is '{vpp_id}'",
                        verbose_level=1,
                    )
                else:
                    self.output("Didn't retrieve a VPP ID", verbose_level=2)
                # obtain appconfig
                appconfig = ""
                if appconfig_template:
                    appconfig = self.make_escaped_appconfig_from_template(
                        appconfig_template
                    )
                else:
                    appconfig = self.get_api_obj_value_from_id(
                        jamf_url,
                        "mobile_device_application",
                        obj_id,
                        "app_configuration/preferences",
                        token=token,
                    )

                # we need to substitute the values in the Mobile device app name and template now to
                # account for URL and Bundle ID
                self.env["mobiledeviceapp_name"] = mobiledeviceapp_name
                self.env["mobiledeviceapp_version"] = mobiledeviceapp_version
                self.env["mobiledeviceapp_free"] = str(mobiledeviceapp_free)
                self.env["bundleid"] = bundleid
                self.env["itunes_store_url"] = itunes_store_url
                self.env["selfservice_icon_uri"] = selfservice_icon_uri
                self.env["vpp_id"] = vpp_id
                self.env["appconfig"] = appconfig
                mobiledeviceapp_name, template_xml = (
                    self.prepare_mobiledeviceapp_template(
                        jamf_url, mobiledeviceapp_name, mobiledeviceapp_template
                    )
                )

                # upload the mobiledeviceapp
                self.upload_mobiledeviceapp(
                    jamf_url,
                    mobiledeviceapp_name,
                    template_xml,
                    sleep_time,
                    token,
                    obj_id=obj_id,
                )
                mobiledeviceapp_updated = True

                # output the summary
                self.env["mobiledeviceapp_name"] = mobiledeviceapp_name
                self.env["mobiledeviceapp_updated"] = mobiledeviceapp_updated
                if mobiledeviceapp_updated:
                    self.env["jamfmobiledeviceappuploader_summary_result"] = {
                        "summary_text": (
                            "The following Mobile device apps were updated in "
                            "Jamf Pro:"
                        ),
                        "report_fields": ["mobiledeviceapp", "template"],
                        "data": {
                            "mobiledeviceapp": mobiledeviceapp_name,
                            "template": mobiledeviceapp_template,
                        },
                    }
            else:
                self.output(
                    "Not replacing existing Mobile device app. "
                    "Use replace_mobiledeviceapp='True' to enforce.",
                    verbose_level=1,
                )
                return
        elif clone_from:
            # check for existing - requires obj_name
            obj_type = "mobile_device_application"
            obj_name = clone_from
            obj_id = self.get_api_obj_id_from_name(
                jamf_url,
                obj_name,
                obj_type,
                token=token,
            )
            if obj_id:
                self.output(
                    f"Mobile device app '{clone_from}' already exists: ID {obj_id}"
                )

                # obtain the Mobile device app bundleid
                bundleid = self.get_api_obj_value_from_id(
                    jamf_url,
                    "mobile_device_application",
                    obj_id,
                    "general/bundle_id",
                    token=token,
                )
                if bundleid:
                    self.output(f"Existing bundle ID is '{bundleid}'", verbose_level=1)
                # obtain the Mobile device app version
                mobiledeviceapp_version = self.get_api_obj_value_from_id(
                    jamf_url,
                    "mobile_device_application",
                    obj_id,
                    "general/version",
                    token=token,
                )
                if mobiledeviceapp_version:
                    self.output(
                        f"Existing Mobile device app version is '{mobiledeviceapp_version}'",
                        verbose_level=1,
                    )
                # obtain the Mobile device app free status
                mobiledeviceapp_free = self.get_api_obj_value_from_id(
                    jamf_url,
                    "mobile_device_application",
                    obj_id,
                    "general/free",
                    token=token,
                )
                if mobiledeviceapp_free:
                    self.output(
                        f"Existing Mobile device app free status is '{mobiledeviceapp_free}'",
                        verbose_level=1,
                    )
                # obtain the Mobile device app URL
                itunes_store_url = self.get_api_obj_value_from_id(
                    jamf_url,
                    "mobile_device_application",
                    obj_id,
                    "general/itunes_store_url",
                    token=token,
                )
                if itunes_store_url:
                    self.output(
                        f"Existing Mobile device URL is '{itunes_store_url}'",
                        verbose_level=1,
                    )
                # obtain the Mobile device app icon
                if not selfservice_icon_uri:
                    selfservice_icon_uri = self.get_api_obj_value_from_id(
                        jamf_url,
                        "mobile_device_application",
                        obj_id,
                        "self_service/self_service_icon/uri",
                        token=token,
                    )
                    if selfservice_icon_uri:
                        self.output(
                            f"Existing Self Service icon is '{selfservice_icon_uri}'",
                            verbose_level=1,
                        )

                # obtain the VPP location
                self.output("Obtaining VPP ID", verbose_level=2)
                vpp_id = self.get_vpp_id(jamf_url, token)
                if vpp_id:
                    self.output(
                        f"Existing VPP ID is '{vpp_id}'",
                        verbose_level=1,
                    )
                else:
                    self.output("Didn't retrieve a VPP ID", verbose_level=2)
                # obtain appconfig
                if not appconfig_template:
                    appconfig = self.get_api_obj_value_from_id(
                        jamf_url,
                        "mobile_device_application",
                        obj_id,
                        "app_configuration/preferences",
                        token=token,
                    )
                if appconfig_template:
                    appconfig = self.make_escaped_appconfig_from_template(
                        appconfig_template
                    )

                # we need to substitute the values in the Mobile device app name and template now to
                # account for URL and Bundle ID
                self.env["mobiledeviceapp_name"] = mobiledeviceapp_name
                self.env["mobiledeviceapp_version"] = mobiledeviceapp_version
                self.env["mobiledeviceapp_free"] = str(mobiledeviceapp_free)
                self.env["bundleid"] = bundleid
                self.env["itunes_store_url"] = itunes_store_url
                self.env["selfservice_icon_uri"] = selfservice_icon_uri
                self.env["vpp_id"] = vpp_id
                self.env["appconfig"] = appconfig
                mobiledeviceapp_name, template_xml = (
                    self.prepare_mobiledeviceapp_template(
                        jamf_url, mobiledeviceapp_name, mobiledeviceapp_template
                    )
                )

                # upload the mobiledeviceapp
                self.upload_mobiledeviceapp(
                    jamf_url,
                    mobiledeviceapp_name,
                    template_xml,
                    sleep_time,
                    token,
                    obj_id=0,
                )
                mobiledeviceapp_updated = True

                # output the summary
                self.env["mobiledeviceapp_name"] = mobiledeviceapp_name
                self.env["mobiledeviceapp_updated"] = mobiledeviceapp_updated
                if mobiledeviceapp_updated:
                    self.env["jamfmobiledeviceappuploader_summary_result"] = {
                        "summary_text": (
                            "The following Mobile device apps were updated "
                            "in Jamf Pro:"
                        ),
                        "report_fields": ["mobiledeviceapp", "template"],
                        "data": {
                            "mobiledeviceapp": mobiledeviceapp_name,
                            "template": mobiledeviceapp_template,
                        },
                    }
            else:
                self.output(
                    "No existing Mobile device app item in Jamf from which to clone.",
                    verbose_level=1,
                )
                return

        else:
            self.output(
                "No existing Mobile device app item in Jamf. This must be assigned in Apple "
                "Business Manager or Apple School Manager",
                verbose_level=1,
            )
            return
