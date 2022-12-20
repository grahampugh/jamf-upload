#!/usr/local/autopkg/python

"""
JamfExtensionAttributeUploader processor for uploading extension attributes
to Jamf Pro using AutoPkg
    by G Pugh
"""

import os
import sys
from time import sleep
from xml.sax.saxutils import escape
from autopkglib import ProcessorError  # pylint: disable=import-error

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfUploaderBase import JamfUploaderBase  # noqa: E402

__all__ = ["JamfExtensionAttributeUploader"]


class JamfExtensionAttributeUploader(JamfUploaderBase):
    description = (
        "A processor for AutoPkg that will upload an Extension Attribute item to a "
        "Jamf Cloud or on-prem server."
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
        "ea_name": {
            "required": False,
            "description": "Extension Attribute name",
            "default": "",
        },
        "ea_script_path": {
            "required": False,
            "description": "Full path to the script to be uploaded",
        },
        "replace_ea": {
            "required": False,
            "description": "Overwrite an existing category if True.",
            "default": False,
        },
        "ea_data_type": {
            "required": False,
            "description": "Data type for the EA. One of String, Integer or Date.",
            "default": "String",
        },
        "sleep": {
            "required": False,
            "description": "Pause after running this processor for specified seconds.",
            "default": "0",
        },
    }

    output_variables = {
        "jamfextensionattributeuploader_summary_result": {
            "description": "Description of interesting results.",
        },
    }

    def upload_ea(
        self,
        jamf_url,
        ea_name,
        ea_data_type,
        script_path,
        obj_id=None,
        enc_creds="",
        token="",
    ):
        """Update extension attribute metadata."""
        # import script from file and replace any keys in the script
        if os.path.exists(script_path):
            with open(script_path, "r") as file:
                script_contents = file.read()
        else:
            raise ProcessorError("Script does not exist!")

        # substitute user-assignable keys
        script_contents = self.substitute_assignable_keys(script_contents)

        # XML-escape the script
        script_contents_escaped = escape(script_contents)

        # build the object
        ea_data = (
            "<computer_extension_attribute>"
            + "<name>{}</name>".format(ea_name)
            + "<enabled>true</enabled>"
            + "<description/>"
            + "<data_type>{}</data_type>".format(ea_data_type)
            + "<input_type>"
            + "  <type>script</type>"
            + "  <platform>Mac</platform>"
            + "  <script>{}</script>".format(script_contents_escaped)
            + "</input_type>"
            + "<inventory_display>Extension Attributes</inventory_display>"
            + "<recon_display>Extension Attributes</recon_display>"
            + "</computer_extension_attribute>"
        )
        self.output(
            "Extension Attribute data:",
            verbose_level=2,
        )
        self.output(
            ea_data,
            verbose_level=2,
        )

        self.output("Uploading Extension Attribute..")
        # write the template to temp file
        template_xml = self.write_temp_file(ea_data)

        # if we find an object ID we put, if not, we post
        object_type = "extension_attribute"
        url = "{}/{}/id/{}".format(jamf_url, self.api_endpoints(object_type), obj_id)

        count = 0
        while True:
            count += 1
            self.output(
                "Extension Attribute upload attempt {}".format(count),
                verbose_level=2,
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
            if self.status_check(r, "Extension Attribute", ea_name, request) == "break":
                break
            if count > 5:
                self.output(
                    "ERROR: Extension Attribute upload did not succeed after 5 attempts"
                )
                self.output("\nHTTP POST Response Code: {}".format(r.status_code))
                raise ProcessorError("ERROR: Extension Attribute upload failed ")
            if int(self.sleep) > 30:
                sleep(int(self.sleep))
            else:
                sleep(30)

    def main(self):
        """Do the main thing here"""
        self.jamf_url = self.env.get("JSS_URL")
        self.jamf_user = self.env.get("API_USERNAME")
        self.jamf_password = self.env.get("API_PASSWORD")
        self.ea_script_path = self.env.get("ea_script_path")
        self.ea_name = self.env.get("ea_name")
        self.replace = self.env.get("replace_ea")
        self.ea_data_type = self.env.get("ea_data_type")
        self.sleep = self.env.get("sleep")
        # handle setting replace in overrides
        if not self.replace or self.replace == "False":
            self.replace = False

        # clear any pre-existing summary result
        if "jamfextensionattributeuploader_summary_result" in self.env:
            del self.env["jamfextensionattributeuploader_summary_result"]
        ea_uploaded = False

        # handle files with a relative path
        if not self.ea_script_path.startswith("/"):
            found_template = self.get_path_to_file(self.ea_script_path)
            if found_template:
                self.ea_script_path = found_template
            else:
                raise ProcessorError(f"ERROR: EA file {self.ea_script_path} not found")

        # now start the process of uploading the object
        self.output(f"Checking for existing '{self.ea_name}' on {self.jamf_url}")

        # obtain the relevant credentials
        token, send_creds, _ = self.handle_classic_auth(
            self.jamf_url, self.jamf_user, self.jamf_password
        )

        # check for existing - requires obj_name
        obj_type = "extension_attribute"
        obj_name = self.ea_name
        obj_id = self.get_api_obj_id_from_name(
            self.jamf_url,
            obj_name,
            obj_type,
            enc_creds=send_creds,
            token=token,
        )

        if obj_id:
            self.output(
                "Extension Attribute '{}' already exists: ID {}".format(
                    self.ea_name, obj_id
                )
            )
            if self.replace:
                self.output(
                    "Replacing existing Extension Attribute as 'replace_ea' is set to {}".format(
                        self.replace
                    ),
                    verbose_level=1,
                )
            else:
                self.output(
                    "Not replacing existing Extension Attribute. Use replace_ea='True' to enforce.",
                    verbose_level=1,
                )
                return

        # upload the EA
        self.upload_ea(
            self.jamf_url,
            self.ea_name,
            self.ea_data_type,
            self.ea_script_path,
            obj_id=obj_id,
            enc_creds=send_creds,
            token=token,
        )
        ea_uploaded = True

        # output the summary
        self.env["extension_attribute"] = self.ea_name
        self.env["ea_uploaded"] = ea_uploaded
        if ea_uploaded:
            self.env["jamfextensionattributeuploader_summary_result"] = {
                "summary_text": (
                    "The following extension attributes were created or "
                    "updated in Jamf Pro:"
                ),
                "report_fields": ["name", "path"],
                "data": {"name": self.ea_name, "path": self.ea_script_path},
            }


if __name__ == "__main__":
    PROCESSOR = JamfExtensionAttributeUploader()
    PROCESSOR.execute_shell()
