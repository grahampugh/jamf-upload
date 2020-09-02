#!/usr/local/autopkg/python

"""
Template processor for uploading items to Jamf Pro using AutoPkg
    by G Pugh

This processor does not function. It is a basis for the other processors in this folder.

The processors in this folder are designed to function similarly to the standalone scripts in the jamf-upload repo. When compiled into a single recipe, they should be able to upload a package to Jamf Pro, and create a policy in a certain category which may contain the package, scripts and computer groups, and the computer groups may contain extension attrbiutes.
"""

# import variables go here. Do not import unused modules
import json
import requests
from autopkglib import Processor, ProcessorError  # pylint: disable=import-error


class TemplateUploader(Processor):
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
    }

    output_variables = {
        "templateuploader_summary_result": {
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

    def upload_ITEM(
        self, jamf_url, enc_creds, ITEM_name, obj_id=None,
    ):
        """Upload ITEM"""
        headers = {
            "authorization": "Basic {}".format(enc_creds),
            "Accept": "application/xml",
            "Content-type": "application/xml",
        }
        # if we find an object ID we put, if not, we post
        if obj_id:
            url = "{}/JSSResource/ITEM/id/{}".format(jamf_url, obj_id)
        else:
            url = "{}/JSSResource/ITEM/id/0".format(jamf_url)

        http = requests.Session()

        self.output("Uploading ITEM...")

        count = 0
        while True:
            count += 1
            self.output(
                "ITEM upload attempt {}".format(count), verbose_level=2,
            )
            if obj_id:
                r = http.put(url, headers=headers, data=template_contents, timeout=60)
            else:
                r = http.post(url, headers=headers, data=template_contents, timeout=60)
            if r.status_code == 200 or r.status_code == 201:
                self.output(f"ITEM '{obj_name}' uploaded successfully")
                break
            if r.status_code == 409:
                # TODO when using verbose mode we could get the reason for the conflict from the output
                self.output("WARNING: ITEM upload failed due to a conflict")
                break
            if count > 5:
                self.output("WARNING: ITEM upload did not succeed after 5 attempts")
                self.output("\nHTTP POST Response Code: {}".format(r.status_code))
                break
            sleep(30)

    def main(self):
        """Do the main thing here"""
        self.jamf_url = self.env.get("JSS_URL")
        self.jamf_user = self.env.get("API_USERNAME")
        self.jamf_password = self.env.get("API_PASSWORD")
        self.obj_name = self.env.get("NAME")  #  may not be the correct input variable

        # clear any pre-existing summary result
        if "templateuploader_summary_result" in self.env:
            del self.env["jamfpackageuploader_summary_result"]

        # encode the username and password into a basic auth b64 encoded string
        credentials = f"{self.jamf_user}:{self.jamf_password}"
        enc_creds_bytes = base64.b64encode(credentials.encode("utf-8"))
        enc_creds = str(enc_creds_bytes, "utf-8")

        # now start the process of uploading the object
        self.output(f"Checking '{self.obj_name}' on {self.jamf_url}")

        # check for existing - requires obj_name
        obj_type = "REPLACE_WITH_OBJECT_TYPE"
        obj_id = self.check_api_obj_id_from_name(
            self.jamf_url, obj_type, self.obj_name, enc_creds
        )

        if obj_id:
            self.output(
                "REPLACE_WITH_OBJECT_TYPE '{}' already exists: ID {}".format(
                    self.obj_name, obj_id
                )
            )
            self.upload_ITEM(
                self.jamf_url, enc_creds, self.obj_name, obj_id,
            )
        else:
            # post the item
            self.upload_ITEM(
                self.jamf_url, enc_creds, self.obj_name,
            )


if __name__ == "__main__":
    PROCESSOR = TemplateUploader()
    PROCESSOR.execute_shell()
