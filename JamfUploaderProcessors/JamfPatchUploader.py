#!/usr/local/autopkg/python

"""
JamfPatchUploader processor for uploading a patch policy to Jamf Pro using AutoPkg
    by Marcel Keßler based on G Pugh's great work
"""

import os.path
import sys

import xml.etree.ElementTree as ET

from time import sleep
from autopkglib import ProcessorError  # pylint: disable=import-error

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfUploaderBase import JamfUploaderBase  # noqa: E402

__all__ = ["JamfPatchUploader"]


class JamfPatchUploader(JamfUploaderBase):
    description = (
        "A processor for AutoPkg that will upload a Patch Policy to a Jamf "
        "Cloud or on-prem server."
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
        "pkg_name": {
            "required": False,
            "description": "Name of package which should be used in the patch."
            "Mostly provided by previous AutoPKG recipe/processor.",
            "default": "",
        },
        "version": {
            "required": False,
            "description": "Version string - provided by previous pkg recipe/processor.",
            "default": "",
        },
        "patch_softwaretitle": {
            "required": True,
            "description": (
                "Name of the patch softwaretitle (e.g. 'Mozilla Firefox') used in Jamf. "
                "You need to create the patch softwaretitle by hand, since there is "
                "currently no way to create these via the API."
            ),
            "default": "",
        },
        "patch_name": {
            "required": False,
            "description": (
                "Name of the patch policy (e.g. 'Mozilla Firefox - 93.02.10'). "
                "If no name is provided defaults to '%patch_softwaretitle% - %version%'."
            ),
            "default": "",
        },
        "patch_template": {
            "required": False,
            "description": (
                "XML-Template used for the patch policy. If none is provided, only the "
                "installer will be linked to the corresponding version."
            ),
            "default": "",
        },
        "patch_icon_policy_name": {
            "required": False,
            "description": (
                "Name of an already existing (!) policy (not a patch policy). "
                "The icon of this policy will be extracted and can be used in the patch template "
                "with the variable %patch_icon_id%. There is currently no reasonable "
                "way to upload a custom icon for patch policies."
            ),
            "default": "",
        },
        "replace_patch": {
            "required": False,
            "description": "Overwrite an existing patch policy if True.",
            "default": False,
        },
        "sleep": {
            "required": False,
            "description": "Pause after running this processor for specified seconds.",
            "default": "0",
        },
    }

    output_variables = {
        "patch": {"description": "The created/updated patch definition."},
        "jamfpatchuploader_summary_result": {
            "description": "Description of interesting results.",
        },
    }

    def prepare_patch_template(self, patch_name, patch_template):
        """
        Prepares the patch template. Mostly copied from the policy processor.
        """
        if os.path.exists(patch_template):
            with open(patch_template, "r") as file:
                template_contents = file.read()
        else:
            raise ProcessorError("Patch template does not exist!")

        patch_name = self.substitute_assignable_keys(patch_name)
        self.env["patch_name"] = self.patch_name
        template_contents = self.substitute_assignable_keys(
            template_contents, xml_escape=True
        )

        self.output("Patch data:", verbose_level=2)
        self.output(template_contents, verbose_level=2)

        # write the template to temp file
        template_xml = self.write_temp_file(template_contents)
        return patch_name, template_xml

    def handle_patch_pkg(
        self,
        jamf_url,
        patch_softwaretitle_name,
        patch_softwaretitle_id,
        pkg_version,
        pkg_name,
        enc_creds="",
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
                self.jamf_url,
                obj_name,
                obj_type,
                enc_creds=enc_creds,
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
        url = "{}/{}/id/{}".format(
            jamf_url, self.api_endpoints(object_type), patch_softwaretitle_id
        )

        # No need to loop over curl function, since we only make a "GET" request.
        r = self.curl(
            request="GET", url=url, enc_creds=enc_creds, token=token, force_xml=True
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
        patch_softwaretitle_xml_file = self.write_xml_file(patch_softwaretitle_xml)

        # Upload the 'updated' patch softwaretitle
        count = 0
        while True:
            count += 1
            self.output(f"Patch Softwaretitle upload attempt {count}.", verbose_level=2)
            r = self.curl(
                request="PUT",
                url=url,  # Unchanged url from the request earlier
                enc_creds=enc_creds,
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
            if int(self.sleep) > 30:
                sleep(int(self.sleep))
            else:
                sleep(30)

    def upload_patch(
        self,
        jamf_url,
        patch_name,
        patch_softwaretitle_id,
        patch_template,
        patch_id=0,
        enc_creds="",
        token="",
    ):
        """Uploads the patch policy"""
        self.output("Uploading Patch policy...")

        # For patch policies the url differs when creating a new one or updating one.
        object_type = "patch_policy"
        if patch_id:
            url = "{}/{}/id/{}".format(
                jamf_url, self.api_endpoints(object_type), patch_id
            )
        else:
            url = "{}/{}/softwaretitleconfig/id/{}".format(
                jamf_url, self.api_endpoints(object_type), patch_softwaretitle_id
            )

        count = 0
        while True:
            count += 1
            self.output("Patch upload attempt {}".format(count), verbose_level=2)
            request = "PUT" if patch_id else "POST"
            r = self.curl(
                request=request,
                url=url,
                enc_creds=enc_creds,
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
                self.output("\nHTTP POST Response Code: {}".format(r.status_code))
                raise ProcessorError("ERROR: Policy upload failed.")
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
        self.pkg_name = self.env.get("pkg_name")
        self.version = self.env.get("version")
        self.patch_softwaretitle = self.env.get("patch_softwaretitle")
        self.patch_name = self.env.get("patch_name")
        self.patch_template = self.env.get("patch_template")
        self.patch_icon_policy_name = self.env.get("patch_icon_policy_name")
        self.replace = self.env.get("replace_patch")
        self.sleep = self.env.get("sleep")
        if not self.replace or self.replace == "False":
            self.replace = False

        # clear any pre-existing summary result
        if "jamfpatchuploader_summary_result" in self.env:
            del self.env["jamfpatchuploader_summary_result"]

        if self.patch_template:
            patch_policy_enabled = True
            if not self.patch_template.startswith("/"):
                found_template = self.get_path_to_file(self.patch_template)
                if found_template:
                    self.patch_template = found_template
                    self.output(
                        f"Patch template: {self.patch_template}", verbose_level=2
                    )
                else:
                    raise ProcessorError(
                        f"ERROR: Patch Template file {self.patch_template} not found"
                    )
        else:
            patch_policy_enabled = False
            self.output(
                "No patch template provided. Patch policy will be skipped and only installer will "
                "be linked."
            )

        self.output(
            f"Checking for existing '{self.patch_softwaretitle}' on {self.jamf_url}"
        )

        # obtain the relevant credentials
        token, send_creds, _ = self.handle_classic_auth(
            self.jamf_url, self.jamf_user, self.jamf_password
        )

        # Patch Icon:
        # Sadly there is currently no (reasonable) way to upload an icon for a patch policy.
        # We can only upload icons for non-patch policies, and use them in patch policies
        # afterwards.
        # Since most AutoPKG workflows include a policy (incl. an icon), we simply provide a way
        # to extract the icon from a specified policy (if desired).

        if self.patch_icon_policy_name:
            obj_type = "policy"
            obj_name = self.patch_icon_policy_name
            self.patch_icon_policy_id = self.get_api_obj_id_from_name(
                self.jamf_url,
                obj_name,
                obj_type,
                enc_creds=send_creds,
                token=token,
            )
            if self.patch_icon_policy_id:
                # Only try to extract an icon, if a policy with the given name was found.
                obj_type = "policy"
                obj_id = self.patch_icon_policy_id
                obj_path = "self_service/self_service_icon/id"
                self.patch_icon_id = self.get_api_obj_value_from_id(
                    self.jamf_url,
                    obj_type,
                    obj_id,
                    obj_path,
                    enc_creds=send_creds,
                    token=token,
                )
                if self.patch_icon_id:
                    # Icon id could be extracted
                    self.output(
                        f"Set 'patch_icon_id' to '{self.patch_icon_id}'.",
                        verbose_level=2,
                    )
                    # Convert int to str to avoid errors while mapping the template later on
                    self.env["patch_icon_id"] = str(self.patch_icon_id)
                else:
                    # Found policy by name, but no icon id could  be extracted
                    self.output(
                        f"WARNING: No icon found in given policy '{self.patch_icon_policy_name}'!"
                    )
            else:
                # Name was given, but no matching id could be found
                self.output(
                    (
                        f"No policy with the given name '{self.patch_icon_policy_name}' was found."
                        "Not able to extract an icon. Continuing..."
                    )
                )
        else:
            self.patch_icon_policy_id = 0
            self.env["patch_icon_id"] = "0"
            self.output(
                "No 'patch_icon_policy_name' was provided. Skipping icon extraction...",
                verbose_level=1,
            )

        # Patch Softwaretitle
        obj_type = "patch_software_title"
        obj_name = self.patch_softwaretitle
        self.patch_softwaretitle_id = self.get_api_obj_id_from_name(
            self.jamf_url,
            obj_name,
            obj_type,
            enc_creds=send_creds,
            token=token,
        )

        if not self.patch_softwaretitle_id:
            raise ProcessorError(
                f"ERROR: Couldn't find patch softwaretitle with name '{self.patch_softwaretitle}'.",
                "You need to create the patch softwaretitle by hand in Jamf Pro.",
                "There is currently no way to create a patch softwaretitle via API.",
            )
        self.env["patch_softwaretitle_id"] = self.patch_softwaretitle_id

        # Patch Package Definition
        # Links the (AutoPKG) reported version with the reported pkg.
        if not self.version:
            raise ProcessorError(
                "ERROR: No variable 'version' was reported by AutoPKG."
            )

        self.handle_patch_pkg(
            self.jamf_url,
            self.patch_softwaretitle,
            self.patch_softwaretitle_id,
            self.version,
            self.pkg_name,
            send_creds,
            token,
        )

        # Patch Policy
        if patch_policy_enabled:
            if not self.patch_name:
                self.patch_name = self.patch_softwaretitle + " - " + self.version
                self.output(
                    f"Set `patch_name` to '{self.patch_name}' since no name was provided."
                )

            self.patch_name, patch_template_xml = self.prepare_patch_template(
                self.patch_name, self.patch_template
            )

            obj_type = "patch_policy"
            obj_name = self.patch_name
            patch_id = self.get_api_obj_id_from_name(
                self.jamf_url,
                obj_name,
                obj_type,
                enc_creds=send_creds,
                token=token,
            )

            if patch_id:
                self.output(
                    "Patch '{}' already exists: ID {}".format(self.patch_name, patch_id)
                )
                if self.replace:
                    self.output(
                        "Replacing existing patch as 'replace_patch' is set to {}".format(
                            self.replace
                        ),
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
                self.jamf_url,
                self.patch_name,
                self.patch_softwaretitle_id,
                patch_template=patch_template_xml,
                patch_id=patch_id,
                enc_creds=send_creds,
                token=token,
            )

            # Parse xml output to get patch id of freshly created patch policy.
            try:
                patch_xml = ET.fromstring(r.output)
                patch_id = patch_xml.find("id").text
            except ET.ParseError as xml_error:
                raise ProcessorError from xml_error
        else:
            self.patch_name = "Not created - missing template"
            patch_id = 0

        # Summary
        self.env["patch"] = self.patch_name
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
                "patch_policy_name": self.patch_name,
                "patch_softwaretitle": self.patch_softwaretitle,
                "patch_version": self.version,
            },
        }


if __name__ == "__main__":
    PROCESSOR = JamfPatchUploader()
    PROCESSOR.execute_shell()
