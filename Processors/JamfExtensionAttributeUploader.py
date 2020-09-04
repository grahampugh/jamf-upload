#!/usr/local/autopkg/python

"""
JamfExtensionAttributeUploader processor for uploading extension attributes 
to Jamf Pro using AutoPkg
    by G Pugh

"""

# import variables go here. Do not import unused modules
import json
import requests
import os.path
from base64 import b64encode
from pathlib import Path
from time import sleep
from requests_toolbelt.utils import dump
from xml.sax.saxutils import escape
from autopkglib import Processor, ProcessorError  # pylint: disable=import-error


class JamfExtensionAttributeUploader(Processor):
    """A processor for AutoPkg that will upload an item to a Jamf Cloud or on-prem server."""

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
    }

    output_variables = {
        "jamfextensionattributeuploader_summary_result": {
            "description": "Description of interesting results.",
        },
    }

    def check_api_obj_id_from_name(self, jamf_url, object_type, object_name, enc_creds):
        """check if a Classic API object with the same name exists on the server"""
        # define the relationship between the object types and their URL
        # we could make this shorter with some regex but I think this way is clearer
        object_types = {
            "package": "packages",
            "computer_group": "computergroups",
            "policy": "policies",
            "extension_attribute": "computerextensionattributes",
        }
        object_list_types = {
            "package": "packages",
            "computer_group": "computer_groups",
            "policy": "policies",
            "extension_attribute": "computer_extension_attributes",
        }
        headers = {
            "authorization": "Basic {}".format(enc_creds),
            "accept": "application/json",
        }
        url = "{}/JSSResource/{}".format(jamf_url, object_types[object_type])
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            object_list = json.loads(r.text)
            self.output(
                object_list, verbose_level=2,
            )
            obj_id = 0
            for obj in object_list[object_list_types[object_type]]:
                self.output(
                    obj, verbose_level=2,
                )
                # we need to check for a case-insensitive match
                if obj["name"].lower() == object_name.lower():
                    obj_id = obj["id"]
            return obj_id

    def substitute_assignable_keys(self, data):
        """substitutes any key in the inputted text using the %MY_KEY% nomenclature"""
        # whenever %MY_KEY% is found in a template, it is replaced with the assigned value of MY_KEY
        for custom_key in self.env:
            self.output(
                (
                    f"Replacing any instances of '{custom_key}' with",
                    f"'{str(self.env.get(custom_key))}'",
                ),
                verbose_level=2,
            )
            data = data.replace(f"%{custom_key}%", str(self.env.get(custom_key)))
        return data

    def logging_hook(self, response, *args, **kwargs):
        data = dump.dump_all(response)
        self.output(
            data, verbose_level=2,
        )

    def get_path_to_file(self, filename):
        """AutoPkg is not very good at finding dependent files. This function will look 
        inside the search directories for any supplied file """
        # if the supplied file is not a path, use the override directory or
        # ercipe dir if no override
        recipe_dir = self.env.get("RECIPE_DIR")
        filepath = os.path.join(recipe_dir, filename)
        if os.path.exists(filepath):
            self.output(f"File found at: {filepath}")
            return filepath

        # if not found, search RECIPE_SEARCH_DIRS to look for it
        search_dirs = self.env.get("RECIPE_SEARCH_DIRS")
        for d in search_dirs:
            for path in Path(d).rglob(filename):
                matched_filepath = str(path)
                break
        if matched_filepath:
            self.output(f"File found at: {matched_filepath}")
            return matched_filepath

    def upload_extatt(
        self, jamf_url, enc_creds, extatt_name, script_path, obj_id=None,
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

        #  XML-escape the script
        script_contents_escaped = escape(script_contents)

        # build the object
        extatt_data = (
            "<computer_extension_attribute>"
            + "<name>{}</name>".format(extatt_name)
            + "<enabled>true</enabled>"
            + "<description/>"
            + "<data_type>String</data_type>"
            + "<input_type>"
            + "  <type>script</type>"
            + "  <platform>Mac</platform>"
            + "  <script>{}</script>".format(script_contents_escaped)
            + "</input_type>"
            + "<inventory_display>Extension Attributes</inventory_display>"
            + "<recon_display>Extension Attributes</recon_display>"
            + "</computer_extension_attribute>"
        )
        headers = {
            "authorization": "Basic {}".format(enc_creds),
            "Accept": "application/xml",
            "Content-type": "application/xml",
        }
        # if we find an object ID we put, if not, we post
        if obj_id:
            url = "{}/JSSResource/computerextensionattributes/id/{}".format(
                jamf_url, obj_id
            )
        else:
            url = "{}/JSSResource/computerextensionattributes/id/0".format(jamf_url)

        http = requests.Session()
        http.hooks["response"] = [self.logging_hook]
        self.output(
            "Extension Attribute data:", verbose_level=2,
        )
        self.output(
            extatt_data, verbose_level=2,
        )

        self.output("Uploading Extension Attribute..")

        count = 0
        while True:
            count += 1
            self.output(
                "Extension Attribute upload attempt {}".format(count), verbose_level=2,
            )
            if obj_id:
                r = http.put(url, headers=headers, data=extatt_data, timeout=60)
            else:
                r = http.post(url, headers=headers, data=extatt_data, timeout=60)
            if r.status_code == 200 or r.status_code == 201:
                self.output("Extension Attribute uploaded successfully")
                break
            if r.status_code == 409:
                raise ProcessorError(
                    "ERROR: Extension Attribute upload failed due to a conflict"
                )
            if count > 5:
                self.output(
                    "ERROR: Extension Attribute upload did not succeed after 5 attempts"
                )
                self.output("\nHTTP POST Response Code: {}".format(r.status_code))
                raise ProcessorError("ERROR: Extension Attribute upload failed ")
            sleep(10)
        return r

    def main(self):
        """Do the main thing here"""
        self.jamf_url = self.env.get("JSS_URL")
        self.jamf_user = self.env.get("API_USERNAME")
        self.jamf_password = self.env.get("API_PASSWORD")
        self.ea_script_path = self.env.get("ea_script_path")
        self.ea_name = self.env.get("ea_name")
        self.replace = self.env.get("replace_ea")
        # handle setting replace in overrides
        if not self.replace or self.replace == "False":
            self.replace = False

        # clear any pre-existing summary result
        if "jamfextensionattributeuploader_summary_result" in self.env:
            del self.env["jamfextensionattributeuploader_summary_result"]

        # encode the username and password into a basic auth b64 encoded string
        credentials = f"{self.jamf_user}:{self.jamf_password}"
        enc_creds_bytes = b64encode(credentials.encode("utf-8"))
        enc_creds = str(enc_creds_bytes, "utf-8")

        # handle files with no path
        if "/" not in self.ea_script_path:
            self.ea_script_path = self.get_path_to_file(self.ea_script_path)

        # now start the process of uploading the object
        self.output(f"Checking '{self.ea_name}' on {self.jamf_url}")

        # check for existing - requires obj_name
        obj_type = "extension_attribute"
        obj_id = self.check_api_obj_id_from_name(
            self.jamf_url, obj_type, self.ea_name, enc_creds
        )

        if obj_id:
            self.output(
                "Extension Attribute '{}' already exists: ID {}".format(
                    self.ea_name, obj_id
                )
            )
            if self.replace:
                self.upload_extatt(
                    self.jamf_url, enc_creds, self.ea_name, self.ea_script_path, obj_id,
                )
            else:
                self.output(
                    "Not replacing existing Extension Attribute. Use --replace to enforce.",
                    verbose_level=1,
                )
                return
        else:
            # post the item
            self.upload_extatt(
                self.jamf_url, enc_creds, self.ea_name, self.ea_script_path,
            )

        # output the summary
        self.env["extension_attribute"] = self.ea_name
        self.env["jamfextensionattributeuploader_summary_result"] = {
            "summary_text": "The following extension attributes were created or updated in Jamf Pro:",
            "report_fields": ["name", "path"],
            "data": {"name": self.ea_name, "path": self.ea_script_path,},
        }


if __name__ == "__main__":
    PROCESSOR = JamfExtensionAttributeUploader()
    PROCESSOR.execute_shell()
