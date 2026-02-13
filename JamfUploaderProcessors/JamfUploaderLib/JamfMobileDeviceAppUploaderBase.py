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


class JamfMobileDeviceAppUploaderBase(JamfUploaderBase):
    """Class for functions used to upload a mobile device app to Jamf"""

    def _extract_adam_id(self, itunes_store_url):
        """Return the adamId component from an iTunes Store URL."""
        if not itunes_store_url:
            return None
        match = re.search(r"id(\d+)", itunes_store_url)
        if match:
            return match.group(1)
        cleaned_value = itunes_store_url.strip()
        return cleaned_value or None

    def _prioritize_vpp_locations(self, locations, preferred_location):
        """Return the locations list with preferred location matches first."""
        if not preferred_location:
            return locations
        preferred_lower = preferred_location.lower()
        for index, location in enumerate(locations):
            location_name = location.get("locationName") or location.get("name", "")
            if preferred_lower in location_name.lower():
                return [location] + locations[:index] + locations[index + 1 :]
        return locations

    def _get_volume_purchasing_locations(self, jamf_url, token):
        """Retrieve all Volume Purchasing Locations from Jamf Pro."""
        url_filter = "?page=0&page-size=200&sort=id"
        object_type = "volume_purchasing_location"
        url = jamf_url + "/" + self.api_endpoints(object_type) + url_filter
        r = self.curl(api_type="jpapi", request="GET", url=url, token=token)
        if r.status_code != 200:
            self.output(
                f"Unable to retrieve VPP locations (status {r.status_code})",
                verbose_level=2,
            )
            return []
        if isinstance(r.output, dict):
            output = r.output
        else:
            output = json.loads(r.output)
        locations = output.get("results", [])
        for obj in locations:
            location_name = obj.get("locationName") or obj.get("name")
            self.output(
                f"VPP Location ID: {obj.get('id')} NAME: {location_name}",
                verbose_level=3,
            )
        return locations

    def _location_contains_app_content(
        self, jamf_url, token, location_id, target_adam_id
    ):
        """Return True if the supplied location contains content for the adam ID."""
        if not location_id or not target_adam_id:
            return False
        object_type = "volume_purchasing_location"
        endpoint = f"{jamf_url}/{self.api_endpoints(object_type)}/{location_id}/content"
        url = f"{endpoint}?page=0&page-size=200"
        r = self.curl(api_type="jpapi", request="GET", url=url, token=token)
        if r.status_code != 200:
            self.output(
                f"Unable to retrieve VPP content for location {location_id} (status {r.status_code})",
                verbose_level=2,
            )
            return False
        if isinstance(r.output, dict):
            output = r.output
        else:
            output = json.loads(r.output)
        for content_item in output.get("results", []):
            adam_id = str(content_item.get("adamId") or "").strip()
            if not adam_id:
                continue
            if (
                adam_id == target_adam_id
                or adam_id in target_adam_id
                or target_adam_id in adam_id
            ):
                self.output(
                    f"Matched adam ID {target_adam_id} in location {location_id}",
                    verbose_level=2,
                )
                return True
        return False

    def get_vpp_id(
        self, jamf_url, token, itunes_store_url=None, preferred_location=None
    ):
        """Determine the Volume Purchasing Location ID that hosts the app's content."""
        locations = self._get_volume_purchasing_locations(jamf_url, token)
        if not locations:
            return None
        ordered_locations = self._prioritize_vpp_locations(
            locations, preferred_location
        )
        target_adam_id = self._extract_adam_id(itunes_store_url)
        if not target_adam_id:
            self.output(
                "Unable to determine adam ID from iTunes Store URL; skipping VPP match",
                verbose_level=2,
            )
            return None
        for location in ordered_locations:
            location_id = location.get("id")
            location_name = location.get("name")
            self.output(
                f"Checking VPP location '{location_name}' (ID {location_id}) for adam ID {target_adam_id}",
                verbose_level=3,
            )
            if self._location_contains_app_content(
                jamf_url, token, location_id, target_adam_id
            ):
                return location_id
        self.output(
            f"No VPP location contains content for adam ID '{target_adam_id}'",
            verbose_level=2,
        )
        return None

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
        object_name,
        object_template,
        sleep_time,
        token,
        max_tries,
        object_id=0,
    ):
        """Upload Mobile device app"""

        self.output("Uploading Mobile device app...")

        # if we find an object ID we put, if not, we post
        object_type = "mobile_device_application"
        url = f"{jamf_url}/{self.api_endpoints(object_type)}/id/{object_id}"

        count = 0
        while True:
            count += 1
            self.output(f"Mobile device app upload attempt {count}", verbose_level=2)
            request = "PUT" if object_id else "POST"
            r = self.curl(
                api_type="classic",
                request=request,
                url=url,
                token=token,
                data=object_template,
            )
            # check HTTP response
            if (
                self.status_check(r, "mobile_device_application", object_name, request)
                == "break"
            ):
                break
            if count >= max_tries:
                self.output(
                    f"WARNING: Mobile device app upload did not succeed after {max_tries} attempts"
                )
                self.output(f"\nHTTP POST Response Code: {r.status_code}")
                raise ProcessorError("ERROR: Mobile device app upload failed ")
            if int(sleep_time) > 10:
                sleep(int(sleep_time))
            else:
                sleep(10)
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
        preferred_vpp_location = self.env.get(
            "preferred_volume_purchase_location"
        )
        replace_mobiledeviceapp = self.to_bool(self.env.get("replace_mobiledeviceapp"))
        sleep_time = self.env.get("sleep")
        mobiledeviceapp_updated = False
        max_tries = self.env.get("max_tries")

        # verify that max_tries is an integer greater than zero and less than 10
        try:
            max_tries = int(max_tries)
            if max_tries < 1 or max_tries > 10:
                raise ValueError
        except (ValueError, TypeError):
            max_tries = 5

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

        # check for existing - requires object_name
        object_id = self.get_api_object_id_from_name(
            jamf_url,
            object_type="mobile_device_application",
            object_name=mobiledeviceapp_name,
            token=token,
        )

        if object_id:
            self.output(
                f"Mobile device app '{mobiledeviceapp_name}' already exists: ID {object_id}"
            )
            if replace_mobiledeviceapp:
                self.output(
                    "Replacing existing Mobile device app as 'replace_mobiledeviceapp' "
                    "is set to True",
                    verbose_level=1,
                )

                # obtain the Mobile device app bundleid
                bundleid = self.get_api_object_value_from_id(
                    jamf_url,
                    object_type="mobile_device_application",
                    object_id=object_id,
                    object_path="general/bundle_id",
                    token=token,
                )
                if bundleid:
                    self.output(f"Existing bundle ID is '{bundleid}'", verbose_level=1)
                # obtain the Mobile device app version
                mobiledeviceapp_version = self.get_api_object_value_from_id(
                    jamf_url,
                    object_type="mobile_device_application",
                    object_id=object_id,
                    object_path="general/version",
                    token=token,
                )
                if mobiledeviceapp_version:
                    self.output(
                        f"Existing Mobile device app version is '{mobiledeviceapp_version}'",
                        verbose_level=1,
                    )
                # obtain the Mobile device app free status
                mobiledeviceapp_free = self.get_api_object_value_from_id(
                    jamf_url,
                    object_type="mobile_device_application",
                    object_id=object_id,
                    object_path="general/free",
                    token=token,
                )
                if mobiledeviceapp_free:
                    self.output(
                        f"Existing Mobile device app free status is '{mobiledeviceapp_free}'",
                        verbose_level=1,
                    )
                # obtain the Mobile device app URL
                itunes_store_url = self.get_api_object_value_from_id(
                    jamf_url,
                    object_type="mobile_device_application",
                    object_id=object_id,
                    object_path="general/itunes_store_url",
                    token=token,
                )
                if itunes_store_url:
                    self.output(
                        f"Existing Mobile device URL is '{itunes_store_url}'",
                        verbose_level=1,
                    )
                # obtain the Mobile device app icon
                if not selfservice_icon_uri:
                    selfservice_icon_uri = self.get_api_object_value_from_id(
                        jamf_url,
                        object_type="mobile_device_application",
                        object_id=object_id,
                        object_path="self_service/self_service_icon/uri",
                        token=token,
                    )
                    if selfservice_icon_uri:
                        self.output(
                            f"Existing Self Service icon is '{selfservice_icon_uri}'",
                            verbose_level=1,
                        )
                # obtain the VPP location
                self.output("Obtaining VPP ID", verbose_level=2)
                vpp_id = self.get_vpp_id(
                    jamf_url,
                    token,
                    itunes_store_url=itunes_store_url,
                    preferred_location=preferred_vpp_location,
                )
                if vpp_id:
                    self.output(
                        f"Existing VPP ID is '{vpp_id}'",
                        verbose_level=1,
                    )
                else:
                    self.output("Didn't retrieve a VPP ID", verbose_level=2)
                    adam_id = self._extract_adam_id(itunes_store_url)
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
                        "ERROR: No Volume Purchasing license found "
                        f"{detail}{preferred_note}."
                    )
                # obtain appconfig
                appconfig = ""
                if appconfig_template:
                    appconfig = self.make_escaped_appconfig_from_template(
                        appconfig_template
                    )
                else:
                    appconfig = self.get_api_object_value_from_id(
                        jamf_url,
                        object_type="mobile_device_application",
                        object_id=object_id,
                        object_path="app_configuration/preferences",
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
                    object_name=mobiledeviceapp_name,
                    object_template=template_xml,
                    sleep_time=sleep_time,
                    token=token,
                    max_tries=max_tries,
                    object_id=object_id,
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
            # check for existing - requires object_name
            object_id = self.get_api_object_id_from_name(
                jamf_url,
                object_type="mobile_device_application",
                object_name=clone_from,
                token=token,
            )
            if object_id:
                self.output(
                    f"Mobile device app '{clone_from}' already exists: ID {object_id}"
                )

                # obtain the Mobile device app bundleid
                bundleid = self.get_api_object_value_from_id(
                    jamf_url,
                    object_type="mobile_device_application",
                    object_id=object_id,
                    object_path="general/bundle_id",
                    token=token,
                )
                if bundleid:
                    self.output(f"Existing bundle ID is '{bundleid}'", verbose_level=1)
                # obtain the Mobile device app version
                mobiledeviceapp_version = self.get_api_object_value_from_id(
                    jamf_url,
                    object_type="mobile_device_application",
                    object_id=object_id,
                    object_path="general/version",
                    token=token,
                )
                if mobiledeviceapp_version:
                    self.output(
                        f"Existing Mobile device app version is '{mobiledeviceapp_version}'",
                        verbose_level=1,
                    )
                # obtain the Mobile device app free status
                mobiledeviceapp_free = self.get_api_object_value_from_id(
                    jamf_url,
                    object_type="mobile_device_application",
                    object_id=object_id,
                    object_path="general/free",
                    token=token,
                )
                if mobiledeviceapp_free:
                    self.output(
                        f"Existing Mobile device app free status is '{mobiledeviceapp_free}'",
                        verbose_level=1,
                    )
                # obtain the Mobile device app URL
                itunes_store_url = self.get_api_object_value_from_id(
                    jamf_url,
                    object_type="mobile_device_application",
                    object_id=object_id,
                    object_path="general/itunes_store_url",
                    token=token,
                )
                if itunes_store_url:
                    self.output(
                        f"Existing Mobile device URL is '{itunes_store_url}'",
                        verbose_level=1,
                    )
                # obtain the Mobile device app icon
                if not selfservice_icon_uri:
                    selfservice_icon_uri = self.get_api_object_value_from_id(
                        jamf_url,
                        object_type="mobile_device_application",
                        object_id=object_id,
                        object_path="self_service/self_service_icon/uri",
                        token=token,
                    )
                    if selfservice_icon_uri:
                        self.output(
                            f"Existing Self Service icon is '{selfservice_icon_uri}'",
                            verbose_level=1,
                        )

                # obtain the VPP location
                self.output("Obtaining VPP ID", verbose_level=2)
                vpp_id = self.get_vpp_id(
                    jamf_url,
                    token,
                    itunes_store_url=itunes_store_url,
                    preferred_location=preferred_vpp_location,
                )
                if vpp_id:
                    self.output(
                        f"Existing VPP ID is '{vpp_id}'",
                        verbose_level=1,
                    )
                else:
                    self.output("Didn't retrieve a VPP ID", verbose_level=2)
                    adam_id = self._extract_adam_id(itunes_store_url)
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
                        "ERROR: No Volume Purchasing license found "
                        f"{detail}{preferred_note}."
                    )
                # obtain appconfig
                if not appconfig_template:
                    appconfig = self.get_api_object_value_from_id(
                        jamf_url,
                        object_type="mobile_device_application",
                        object_id=object_id,
                        object_path="app_configuration/preferences",
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
                    object_name=mobiledeviceapp_name,
                    object_template=template_xml,
                    sleep_time=sleep_time,
                    token=token,
                    max_tries=max_tries,
                    object_id=0,
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
