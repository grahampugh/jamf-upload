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

NOTES:
Written by Marcel Keßler based on G Pugh's work
"""

import os.path
import sys

import xml.etree.ElementTree as ET

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


class JamfPatchUploaderBase(JamfUploaderBase):
    """Class for functions used to upload a patch policy to Jamf"""

    def prepare_patch_template(self, jamf_url, patch_name, patch_template):
        """
        Prepares the patch template. Mostly copied from the policy processor.
        """
        if os.path.exists(patch_template):
            with open(patch_template, "r", encoding="utf-8") as file:
                template_contents = file.read()
        else:
            raise ProcessorError("Patch template does not exist!")

        patch_name = self.substitute_assignable_keys(patch_name)
        self.env["patch_name"] = patch_name
        template_contents = self.substitute_assignable_keys(
            template_contents, xml_escape=True
        )

        self.output("Patch data:", verbose_level=2)
        self.output(template_contents, verbose_level=2)

        # write the template to temp file
        template_xml = self.write_temp_file(jamf_url, template_contents)
        return patch_name, template_xml

    def handle_patch_pkg(
        self,
        jamf_url,
        patch_softwaretitle_name,
        patch_softwaretitle_id,
        pkg_version,
        pkg_name,
        sleep_time,
        token="",
    ):
        """Uploads an updated patch softwaretitle including the linked pkg"""
        self.output("Linking pkg versions in patch softwaretitle...")

        # Get package id from jamf. Try it three times, since
        # in some cases a recently uploaded package can not be found.
        count = 0
        while True:
            count += 1
            self.output(
                f"Attempt '{count}' of fetching package id of '{pkg_name}'.",
                verbose_level=2,
            )
            obj_type = "package"
            obj_name = pkg_name
            pkg_id = self.get_api_obj_id_from_name(
                jamf_url,
                obj_name,
                obj_type,
                token=token,
            )
            if pkg_id:
                self.output(f"Found id '{pkg_id}' for package '{pkg_name}'.")
                break
            if count > 3:
                raise ProcessorError(
                    f"ERROR: Couldn't fetch package id for package '{pkg_name}'."
                )
            sleep(10)

        # Get current softwaretitle
        object_type = "patch_software_title"
        url = (
            f"{jamf_url}/{self.api_endpoints(object_type)}/id/{patch_softwaretitle_id}"
        )

        # No need to loop over curl function, since we only make a "GET" request.
        r = self.curl(
            request="GET", url=url, token=token, endpoint_type="patch_software_title"
        )

        if r.status_code != 200:
            raise ProcessorError("ERROR: Could not fetch patch softwaretitle.")

        # Parse response as xml
        try:
            patch_softwaretitle_xml = ET.fromstring(r.output)
        except ET.ParseError as xml_error:
            raise ProcessorError from xml_error

        version_found = False
        # Replace matching version string, with version string including package name
        for v in patch_softwaretitle_xml.findall("versions/version"):
            if v.find("software_version").text == pkg_version:
                version_found = True
                # Remove old, probably empty package element
                v.remove(v.find("package"))
                # Create new package element including given pkg information
                pkg_element = ET.Element("package")
                pkg_element_id = ET.SubElement(pkg_element, "id")
                pkg_element_id.text = str(pkg_id)
                pkg_element_name = ET.SubElement(pkg_element, "name")
                pkg_element_name.text = pkg_name
                # Inject package element into version element
                v.append(pkg_element)
                # Print new version element for debugging reasons
                self.output(
                    ET.tostring(v, encoding="UTF-8", method="xml"), verbose_level=3
                )

        if not version_found:
            # Get first match of all the versions listed in the
            # softwaretitle to report the 'latest version'.
            # That's helpful if e.g. AutoPKG uploaded a new version,
            # which is not yet listed in the patch softwaretitle list.
            latest_version = patch_softwaretitle_xml.find(
                "versions/version/software_version"
            ).text
            raise ProcessorError(
                "ERROR: Could not find matching version "
                + f"'{pkg_version}' in patch softwaretitle '{patch_softwaretitle_name}'. "
                + f"Latest reported version is '{latest_version}'."
            )

        # Write xml file
        patch_softwaretitle_xml_file = self.write_xml_file(
            jamf_url, patch_softwaretitle_xml
        )

        # Upload the 'updated' patch softwaretitle
        count = 0
        while True:
            count += 1
            self.output(f"Patch Softwaretitle upload attempt {count}.", verbose_level=2)
            r = self.curl(
                request="PUT",
                url=url,  # Unchanged url from the request earlier
                token=token,
                data=patch_softwaretitle_xml_file,
            )
            # Check HTTP Status
            if (
                self.status_check(
                    r, "Patch Softwaretitle", patch_softwaretitle_name, "PUT"
                )
                == "break"
            ):
                break
            if count > 5:
                self.output(
                    "ERROR: Uploading updated Patch Softwaretitle did not succeed after 5 attempts."
                )
                raise ProcessorError("ERROR: Patch Softwaretitle upload failed.")
            if int(sleep_time) > 30:
                sleep(int(sleep_time))
            else:
                sleep(30)

    def upload_patch(
        self,
        jamf_url,
        patch_name,
        patch_softwaretitle_id,
        sleep_time,
        token,
        patch_template,
        patch_id=0,
    ):
        """Uploads the patch policy"""
        self.output("Uploading Patch policy...")

        # For patch policies the url differs when creating a new one or updating one.
        object_type = "patch_policy"
        if patch_id:
            url = f"{jamf_url}/{self.api_endpoints(object_type)}/id/{patch_id}"
        else:
            url = (
                f"{jamf_url}/{self.api_endpoints(object_type)}/softwaretitleconfig"
                f"/id/{patch_softwaretitle_id}"
            )

        count = 0
        while True:
            count += 1
            self.output(f"Patch upload attempt {count}", verbose_level=2)
            request = "PUT" if patch_id else "POST"
            r = self.curl(
                request=request,
                url=url,
                token=token,
                data=patch_template,
            )
            # check HTTP response
            if self.status_check(r, "Patch", patch_name, request) == "break":
                break
            if count > 5:
                self.output(
                    "WARNING: Patch policy upload did not succeed after 5 attempts"
                )
                self.output(f"\nHTTP POST Response Code: {r.status_code}")
                raise ProcessorError("ERROR: Policy upload failed.")
            if int(sleep_time) > 30:
                sleep(int(sleep_time))
            else:
                sleep(30)
        return r

    def execute(self):
        """Upload a patch policy"""
        jamf_url = self.env.get("JSS_URL").rstrip("/")
        jamf_user = self.env.get("API_USERNAME")
        jamf_password = self.env.get("API_PASSWORD")
        client_id = self.env.get("CLIENT_ID")
        client_secret = self.env.get("CLIENT_SECRET")
        pkg_name = self.env.get("pkg_name")
        version = self.env.get("version")
        patch_softwaretitle = self.env.get("patch_softwaretitle")
        patch_name = self.env.get("patch_name")
        patch_template = self.env.get("patch_template")
        patch_icon_policy_name = self.env.get("patch_icon_policy_name")
        replace_patchpolicy = self.to_bool(self.env.get("replace_patch"))
        sleep_time = self.env.get("sleep")

        # clear any pre-existing summary result
        if "jamfpatchuploader_summary_result" in self.env:
            del self.env["jamfpatchuploader_summary_result"]

        if patch_template:
            patch_policy_enabled = True
            if not patch_template.startswith("/"):
                found_template = self.get_path_to_file(patch_template)
                if found_template:
                    patch_template = found_template
                    self.output(f"Patch template: {patch_template}", verbose_level=2)
                else:
                    raise ProcessorError(
                        f"ERROR: Patch Template file {patch_template} not found"
                    )
        else:
            patch_policy_enabled = False
            self.output(
                "No patch template provided. Patch policy will be skipped and only installer will "
                "be linked."
            )

        self.output(f"Checking for existing '{patch_softwaretitle}' on {jamf_url}")

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

        # Patch Icon:
        # Sadly there is currently no (reasonable) way to upload an icon for a patch policy.
        # We can only upload icons for non-patch policies, and use them in patch policies
        # afterwards.
        # Since most AutoPKG workflows include a policy (incl. an icon), we simply provide a way
        # to extract the icon from a specified policy (if desired).

        if patch_icon_policy_name:
            obj_type = "policy"
            obj_name = patch_icon_policy_name
            patch_icon_policy_id = self.get_api_obj_id_from_name(
                jamf_url,
                obj_name,
                obj_type,
                token=token,
            )
            if patch_icon_policy_id:
                # Only try to extract an icon, if a policy with the given name was found.
                obj_type = "policy"
                obj_id = patch_icon_policy_id
                obj_path = "self_service/self_service_icon/id"
                patch_icon_id = self.get_api_obj_value_from_id(
                    jamf_url,
                    obj_type,
                    obj_id,
                    obj_path,
                    token=token,
                )
                if patch_icon_id:
                    # Icon id could be extracted
                    self.output(
                        f"Set 'patch_icon_id' to '{patch_icon_id}'.",
                        verbose_level=2,
                    )
                    # Convert int to str to avoid errors while mapping the template later on
                    self.env["patch_icon_id"] = str(patch_icon_id)
                else:
                    # Found policy by name, but no icon id could  be extracted
                    self.output(
                        f"WARNING: No icon found in given policy '{patch_icon_policy_name}'!"
                    )
            else:
                # Name was given, but no matching id could be found
                self.output(
                    (
                        f"No policy with the given name '{patch_icon_policy_name}' was found. "
                        "Not able to extract an icon. Continuing..."
                    )
                )
        else:
            patch_icon_policy_id = 0
            self.env["patch_icon_id"] = "0"
            self.output(
                "No 'patch_icon_policy_name' was provided. Skipping icon extraction...",
                verbose_level=1,
            )

        # Patch Softwaretitle
        obj_type = "patch_software_title"
        obj_name = patch_softwaretitle
        patch_softwaretitle_id = self.get_api_obj_id_from_name(
            jamf_url,
            obj_name,
            obj_type,
            token=token,
        )

        if not patch_softwaretitle_id:
            raise ProcessorError(
                f"ERROR: Couldn't find patch softwaretitle with name '{patch_softwaretitle}'.",
                "You need to create the patch softwaretitle by hand in Jamf Pro.",
                "There is currently no way to create a patch softwaretitle via API.",
            )
        self.env["patch_softwaretitle_id"] = patch_softwaretitle_id

        # Patch Package Definition
        # Links the (AutoPKG) reported version with the reported pkg.
        if not version:
            raise ProcessorError(
                "ERROR: No variable 'version' was reported by AutoPKG."
            )

        self.handle_patch_pkg(
            jamf_url,
            patch_softwaretitle,
            patch_softwaretitle_id,
            version,
            pkg_name,
            sleep_time,
            token,
        )

        # Patch Policy
        if patch_policy_enabled:
            if not patch_name:
                patch_name = patch_softwaretitle + " - " + version
                self.output(
                    f"Set `patch_name` to '{patch_name}' since no name was provided."
                )

            patch_name, patch_template_xml = self.prepare_patch_template(
                jamf_url, patch_name, patch_template
            )

            obj_type = "patch_policy"
            obj_name = patch_name
            patch_id = self.get_api_obj_id_from_name(
                jamf_url,
                obj_name,
                obj_type,
                token=token,
            )

            if patch_id:
                self.output(f"Patch '{patch_name}' already exists: ID {patch_id}")
                if replace_patchpolicy:
                    self.output(
                        ("Replacing existing patch as 'replace_patch' is set to True"),
                        verbose_level=1,
                    )
                else:
                    self.output(
                        "Not replacing existing patch. Use replace_patch='True' to enforce.",
                        verbose_level=1,
                    )
                    return

            # Upload the patch
            r = self.upload_patch(
                jamf_url,
                patch_name,
                patch_softwaretitle_id,
                sleep_time,
                token,
                patch_template=patch_template_xml,
                patch_id=patch_id,
            )

            # Parse xml output to get patch id of freshly created patch policy.
            try:
                patch_xml = ET.fromstring(r.output)
                patch_id = patch_xml.find("id").text
            except ET.ParseError as xml_error:
                raise ProcessorError from xml_error
        else:
            patch_name = "Not created - missing template"
            patch_id = 0

        # Summary
        self.env["patch"] = patch_name
        self.env["jamfpatchuploader_summary_result"] = {
            "summary_text": "The following patch policies were created or updated in Jamf Pro:",
            "report_fields": [
                "patch_id",
                "patch_policy_name",
                "patch_softwaretitle",
                "patch_version",
            ],
            "data": {
                "patch_id": str(patch_id),
                "patch_policy_name": patch_name,
                "patch_softwaretitle": patch_softwaretitle,
                "patch_version": version,
            },
        }
