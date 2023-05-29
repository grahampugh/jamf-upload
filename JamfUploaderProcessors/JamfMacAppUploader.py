#!/usr/local/autopkg/python

"""
JamfMacAppUploader processor for uploading Mac App Store apps to Jamf Pro using AutoPkg
    by G Pugh
"""

import os
import sys

from time import sleep
from autopkglib import ProcessorError  # pylint: disable=import-error

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfUploaderBase import JamfUploaderBase  # noqa: E402

__all__ = ["JamfMacAppUploader"]


class JamfMacAppUploader(JamfUploaderBase):
    description = (
        "A processor for AutoPkg that will update or clone a Mac App Store app "
        "object on a Jamf Pro server."
        "Note that an icon can only be successsfully injected into a Mac App Store app "
        "item if Cloud Services Connection is enabled."
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
        "macapp_name": {
            "required": False,
            "description": "Mac App Store app name",
            "default": "",
        },
        "clone_from": {
            "required": False,
            "description": "Mac App Store app name from which to clone this entry",
            "default": "",
        },
        "selfservice_icon_uri": {
            "required": False,
            "description": "Mac App Store app icon URI",
            "default": "",
        },
        "macapp_template": {
            "required": False,
            "description": "Full path to the XML template",
        },
        "replace_macapp": {
            "required": False,
            "description": "Overwrite an existing Mac App Store app if True.",
            "default": False,
        },
        "sleep": {
            "required": False,
            "description": "Pause after running this processor for specified seconds.",
            "default": "0",
        },
        "template_escape_xml": {
            "required": False,
            "description": "Disable xml escaping during substitution for the template if False.",
            "default": True,
        },
    }

    output_variables = {
        "jamfmacappuploader_summary_result": {
            "description": "Description of interesting results.",
        },
        "macapp_name": {
            "description": "Jamf object name of the newly created or modified macapp.",
        },
        "macapp_updated": {"description": "Boolean - True if the macapp was changed."},
        "changed_macapp_id": {
            "description": "Jamf object ID of the newly created or modified macapp.",
        },
    }

    def get_vpp_id(self, jamf_url, token):
        """Get the first Volume Purchasing Location ID."""
        url_filter = "?page=0&page-size=1000&sort=id"
        object_type = "volume_purchasing_locations"
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

    def prepare_macapp_template(self, macapp_name, macapp_template):
        """prepare the macapp contents"""
        # import template from file and replace any keys in the template
        if os.path.exists(macapp_template):
            with open(macapp_template, "r") as file:
                template_contents = file.read()
        else:
            raise ProcessorError("Template does not exist!")

        # substitute user-assignable keys
        macapp_name = self.substitute_assignable_keys(macapp_name)
        template_contents = self.substitute_assignable_keys(
            template_contents, xml_escape=self.template_escape_xml
        )

        self.output("MAS app data:", verbose_level=2)
        self.output(template_contents, verbose_level=2)

        # write the template to temp file
        template_xml = self.write_temp_file(template_contents)
        return macapp_name, template_xml

    def upload_macapp(
        self,
        jamf_url,
        macapp_name,
        template_xml,
        obj_id=0,
        enc_creds="",
        token="",
    ):
        """Upload MAS app"""

        self.output("Uploading MAS app...")

        # if we find an object ID we put, if not, we post
        object_type = "mac_application"
        url = "{}/{}/id/{}".format(jamf_url, self.api_endpoints(object_type), obj_id)

        count = 0
        while True:
            count += 1
            self.output("MAS app upload attempt {}".format(count), verbose_level=2)
            request = "PUT" if obj_id else "POST"
            r = self.curl(
                request=request,
                url=url,
                enc_creds=enc_creds,
                token=token,
                data=template_xml,
            )
            # check HTTP response
            if self.status_check(r, "mac_application", macapp_name, request) == "break":
                break
            if count > 5:
                self.output("WARNING: MAS app upload did not succeed after 5 attempts")
                self.output("\nHTTP POST Response Code: {}".format(r.status_code))
                raise ProcessorError("ERROR: Policy upload failed ")
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
        self.macapp_name = self.env.get("macapp_name")
        self.clone_from = self.env.get("clone_from")
        self.selfservice_icon_uri = self.env.get("selfservice_icon_uri")
        self.macapp_template = self.env.get("macapp_template")
        self.replace = self.env.get("replace_macapp")
        self.sleep = self.env.get("sleep")
        self.template_escape_xml = self.env.get("template_escape_xml")
        # handle setting replace in overrides
        if not self.replace or self.replace == "False":
            self.replace = False
        self.macapp_updated = False
        # handle escaping xml in overrides
        if self.template_escape_xml == False or self.template_escape_xml == "False":
            self.template_escape_xml = False
        else:
            self.template_escape_xml = True

        # clear any pre-existing summary result
        if "jamfmacappuploader_summary_result" in self.env:
            del self.env["jamfmacappuploader_summary_result"]

        # handle files with a relative path
        if not self.macapp_template.startswith("/"):
            found_template = self.get_path_to_file(self.macapp_template)
            if found_template:
                self.macapp_template = found_template
            else:
                raise ProcessorError(
                    f"ERROR: Policy file {self.macapp_template} not found"
                )

        # now start the process of uploading the object
        self.output(f"Checking for existing '{self.macapp_name}' on {self.jamf_url}")

        token, send_creds, _ = self.handle_classic_auth(
            self.jamf_url, self.jamf_user, self.jamf_password
        )

        # check for existing - requires obj_name
        obj_type = "mac_application"
        obj_name = self.macapp_name
        obj_id = self.get_api_obj_id_from_name(
            self.jamf_url,
            obj_name,
            obj_type,
            enc_creds=send_creds,
            token=token,
        )

        if obj_id:
            self.output(
                "MAS app '{}' already exists: ID {}".format(self.macapp_name, obj_id)
            )
            if self.replace:
                self.output(
                    "Replacing existing MAS app as 'replace_macapp' is set to {}".format(
                        self.replace
                    ),
                    verbose_level=1,
                )

                # obtain the MAS app bundleid
                bundleid = self.get_api_obj_value_from_id(
                    self.jamf_url,
                    "mac_application",
                    obj_id,
                    "general/bundle_id",
                    enc_creds=send_creds,
                    token=token,
                )
                if bundleid:
                    self.output(
                        "Existing bundle ID is '{}'".format(bundleid), verbose_level=1
                    )
                # obtain the MAS app version
                macapp_version = self.get_api_obj_value_from_id(
                    self.jamf_url,
                    "mac_application",
                    obj_id,
                    "general/version",
                    enc_creds=send_creds,
                    token=token,
                )
                if macapp_version:
                    self.output(
                        "Existing MAS app version is '{}'".format(macapp_version),
                        verbose_level=1,
                    )
                # obtain the MAS app free status
                macapp_is_free = self.get_api_obj_value_from_id(
                    self.jamf_url,
                    "mac_application",
                    obj_id,
                    "general/is_free",
                    enc_creds=send_creds,
                    token=token,
                )
                if macapp_is_free:
                    self.output(
                        "Existing MAS app free status is '{}'".format(macapp_is_free),
                        verbose_level=1,
                    )
                # obtain the MAS app URL
                appstore_url = self.get_api_obj_value_from_id(
                    self.jamf_url,
                    "mac_application",
                    obj_id,
                    "general/url",
                    enc_creds=send_creds,
                    token=token,
                )
                if appstore_url:
                    self.output(
                        "Existing MAS URL is '{}'".format(appstore_url), verbose_level=1
                    )
                # obtain the MAS app icon
                if not self.selfservice_icon_uri:
                    self.selfservice_icon_uri = self.get_api_obj_value_from_id(
                        self.jamf_url,
                        "mac_application",
                        obj_id,
                        "self_service/self_service_icon/uri",
                        enc_creds=send_creds,
                        token=token,
                    )
                    if self.selfservice_icon_uri:
                        self.output(
                            "Existing Self Service icon is '{}'".format(
                                self.selfservice_icon_uri
                            ),
                            verbose_level=1,
                        )
                # obtain the VPP location
                vpp_id = self.get_vpp_id(self.jamf_url, token)
                if vpp_id:
                    self.output(
                        "Existing VPP ID is '{}'".format(vpp_id),
                        verbose_level=1,
                    )

                # we need to substitute the values in the MAS app name and template now to
                # account for URL and Bundle ID
                self.env["macapp_name"] = self.macapp_name
                self.env["macapp_version"] = macapp_version
                self.env["macapp_is_free"] = str(macapp_is_free)
                self.env["bundleid"] = bundleid
                self.env["appstore_url"] = appstore_url
                self.env["selfservice_icon_uri"] = self.selfservice_icon_uri
                self.env["vpp_id"] = vpp_id
                self.macapp_name, template_xml = self.prepare_macapp_template(
                    self.macapp_name, self.macapp_template
                )

                # upload the macapp
                self.upload_macapp(
                    self.jamf_url,
                    self.macapp_name,
                    template_xml,
                    obj_id=obj_id,
                    enc_creds=send_creds,
                    token=token,
                )
                self.macapp_updated = True

                # output the summary
                self.env["macapp_name"] = self.macapp_name
                self.env["macapp_updated"] = self.macapp_updated
                if self.macapp_updated:
                    self.env["jamfmacappuploader_summary_result"] = {
                        "summary_text": "The following MAS apps were updated in Jamf Pro:",
                        "report_fields": ["macapp", "template"],
                        "data": {
                            "macapp": self.macapp_name,
                            "template": self.macapp_template,
                        },
                    }
            else:
                self.output(
                    "Not replacing existing MAS app. Use replace_macapp='True' to enforce.",
                    verbose_level=1,
                )
                return
        elif self.clone_from:
            # check for existing - requires obj_name
            obj_type = "mac_application"
            obj_name = self.clone_from
            obj_id = self.get_api_obj_id_from_name(
                self.jamf_url,
                obj_name,
                obj_type,
                enc_creds=send_creds,
                token=token,
            )
            if obj_id:
                self.output(
                    "MAS app '{}' already exists: ID {}".format(self.clone_from, obj_id)
                )

                # obtain the MAS app bundleid
                bundleid = self.get_api_obj_value_from_id(
                    self.jamf_url,
                    "mac_application",
                    obj_id,
                    "general/bundle_id",
                    enc_creds=send_creds,
                    token=token,
                )
                if bundleid:
                    self.output(
                        "Existing bundle ID is '{}'".format(bundleid), verbose_level=1
                    )
                # obtain the MAS app version
                macapp_version = self.get_api_obj_value_from_id(
                    self.jamf_url,
                    "mac_application",
                    obj_id,
                    "general/version",
                    enc_creds=send_creds,
                    token=token,
                )
                if macapp_version:
                    self.output(
                        "Existing MAS app version is '{}'".format(macapp_version),
                        verbose_level=1,
                    )
                # obtain the MAS app free status
                macapp_is_free = self.get_api_obj_value_from_id(
                    self.jamf_url,
                    "mac_application",
                    obj_id,
                    "general/is_free",
                    enc_creds=send_creds,
                    token=token,
                )
                if macapp_is_free:
                    self.output(
                        "Existing MAS app free status is '{}'".format(macapp_is_free),
                        verbose_level=1,
                    )
                # obtain the MAS app URL
                appstore_url = self.get_api_obj_value_from_id(
                    self.jamf_url,
                    "mac_application",
                    obj_id,
                    "general/url",
                    enc_creds=send_creds,
                    token=token,
                )
                if appstore_url:
                    self.output(
                        "Existing MAS URL is '{}'".format(appstore_url), verbose_level=1
                    )
                # obtain the MAS app icon
                if not self.selfservice_icon_uri:
                    self.selfservice_icon_uri = self.get_api_obj_value_from_id(
                        self.jamf_url,
                        "mac_application",
                        obj_id,
                        "self_service/self_service_icon/uri",
                        enc_creds=send_creds,
                        token=token,
                    )
                    if self.selfservice_icon_uri:
                        self.output(
                            "Existing Self Service icon is '{}'".format(
                                self.selfservice_icon_uri
                            ),
                            verbose_level=1,
                        )

                # we need to substitute the values in the MAS app name and template now to
                # account for URL and Bundle ID
                self.env["macapp_name"] = self.macapp_name
                self.env["macapp_version"] = macapp_version
                self.env["macapp_is_free"] = str(macapp_is_free)
                self.env["bundleid"] = bundleid
                self.env["appstore_url"] = appstore_url
                self.env["selfservice_icon_uri"] = self.selfservice_icon_uri
                self.macapp_name, template_xml = self.prepare_macapp_template(
                    self.macapp_name, self.macapp_template
                )

                # upload the macapp
                self.upload_macapp(
                    self.jamf_url,
                    self.macapp_name,
                    template_xml,
                    obj_id=0,
                    enc_creds=send_creds,
                    token=token,
                )
                self.macapp_updated = True

                # output the summary
                self.env["macapp_name"] = self.macapp_name
                self.env["macapp_updated"] = self.macapp_updated
                if self.macapp_updated:
                    self.env["jamfmacappuploader_summary_result"] = {
                        "summary_text": "The following MAS apps were updated in Jamf Pro:",
                        "report_fields": ["macapp", "template"],
                        "data": {
                            "macapp": self.macapp_name,
                            "template": self.macapp_template,
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


if __name__ == "__main__":
    PROCESSOR = JamfMacAppUploader()
    PROCESSOR.execute_shell()
