#!/usr/local/autopkg/python

"""
JamfScriptUploader processor for uploading items to Jamf Pro using AutoPkg
    by G Pugh

"""

# import variables go here. Do not import unused modules
import json
import requests
import os.path
from pathlib import Path
from base64 import b64encode
from time import sleep
from requests_toolbelt.utils import dump
from autopkglib import Processor, ProcessorError  # pylint: disable=import-error


class JamfScriptUploader(Processor):
    """A processor for AutoPkg that will upload a script to a Jamf Cloud or on-prem server."""

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
        "script_path": {
            "required": False,
            "description": "Full path to the script to be uploaded",
        },
        "script_category": {
            "required": False,
            "description": "Script category",
            "default": "",
        },
        "script_priority": {
            "required": False,
            "description": "Script priority (BEFORE or AFTER)",
            "default": "AFTER",
        },
        "osrequirements": {
            "required": False,
            "description": "Script OS requirements",
            "default": "",
        },
        "script_info": {
            "required": False,
            "description": "Script info field",
            "default": "",
        },
        "script_notes": {
            "required": False,
            "description": "Script notes field",
            "default": "",
        },
        "script_parameter4": {
            "required": False,
            "description": "Script parameter 4 title",
            "default": "",
        },
        "script_parameter5": {
            "required": False,
            "description": "Script parameter 5 title",
            "default": "",
        },
        "script_parameter6": {
            "required": False,
            "description": "Script parameter 6 title",
            "default": "",
        },
        "script_parameter7": {
            "required": False,
            "description": "Script parameter 7 title",
            "default": "",
        },
        "script_parameter8": {
            "required": False,
            "description": "Script parameter 8 title",
            "default": "",
        },
        "script_parameter9": {
            "required": False,
            "description": "Script parameter 9 title",
            "default": "",
        },
        "script_parameter10": {
            "required": False,
            "description": "Script parameter 10 title",
            "default": "",
        },
        "script_parameter11": {
            "required": False,
            "description": "Script parameter 11 title",
            "default": "",
        },
        "replace_script": {
            "required": False,
            "description": "Overwrite an existing category if True.",
            "default": False,
        },
    }

    output_variables = {
        "script_name": {
            "required": False,
            "description": "Name of the uploaded script",
        },
        "jamfscriptuploader_summary_result": {
            "description": "Description of interesting results.",
        },
    }

    def get_uapi_token(self, jamf_url, enc_creds):
        """get a token for the Jamf Pro API"""
        headers = {
            "authorization": "Basic {}".format(enc_creds),
            "content-type": "application/json",
            "accept": "application/json",
        }
        url = "{}/uapi/auth/tokens".format(jamf_url)
        http = requests.Session()
        r = http.post(url, headers=headers)
        self.output(
            r.content, verbose_level=2,
        )
        if r.status_code == 200:
            obj = json.loads(r.text)
            try:
                token = str(obj["token"])
                self.output("Session token received")
                return token
            except KeyError:
                self.output("ERROR: No token received")
                return
        else:
            self.output("ERROR: No token received")
            return

    def get_uapi_obj_id_from_name(self, jamf_url, object_type, object_name, token):
        """The UAPI doesn't have a name object, so we have to get the list of scripts 
        and parse the name to get the id """
        headers = {
            "authorization": "Bearer {}".format(token),
            "accept": "application/json",
        }
        url = "{}/uapi/v1/{}".format(jamf_url, object_type)
        http = requests.Session()

        r = http.get(url, headers=headers)
        if r.status_code == 200:
            object_list = json.loads(r.text)
            obj_id = 0
            for obj in object_list["results"]:
                self.output(
                    obj, verbose_level=2,
                )
                if obj["name"] == object_name:
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

    def upload_script(
        self,
        jamf_url,
        script_name,
        script_path,
        category_id,
        script_category,
        script_info,
        script_notes,
        script_priority,
        script_parameter4,
        script_parameter5,
        script_parameter6,
        script_parameter7,
        script_parameter8,
        script_parameter9,
        script_parameter10,
        script_parameter11,
        script_os_requirements,
        token,
        obj_id=None,
    ):
        """Update script metadata."""

        # import script from file and replace any keys in the script
        if os.path.exists(script_path):
            with open(script_path, "r") as file:
                script_contents = file.read()
        else:
            raise ProcessorError("Script does not exist!")

        # substitute user-assignable keys
        script_contents = self.substitute_assignable_keys(script_contents)

        # build the object
        script_data = {
            "name": script_name,
            "info": script_info,
            "notes": script_notes,
            "priority": script_priority,
            "categoryId": category_id,
            "categoryName": script_category,
            "parameter4": script_parameter4,
            "parameter5": script_parameter5,
            "parameter6": script_parameter6,
            "parameter7": script_parameter7,
            "parameter8": script_parameter8,
            "parameter9": script_parameter9,
            "parameter10": script_parameter10,
            "parameter11": script_parameter11,
            "osRequirements": script_os_requirements,
            "scriptContents": script_contents,
        }
        headers = {
            "authorization": "Bearer {}".format(token),
            "content-type": "application/json",
            "accept": "application/json",
        }
        # ideally we upload to the object ID but if we didn't get a good response
        # we fall back to the name
        if obj_id:
            url = "{}/uapi/v1/scripts/{}".format(jamf_url, obj_id)
            script_data["id"] = obj_id
        else:
            url = "{}/uapi/v1/scripts".format(jamf_url)

        http = requests.Session()
        http.hooks["response"] = [self.logging_hook]
        self.output(
            "Script data:", verbose_level=2,
        )
        self.output(
            script_data, verbose_level=2,
        )

        self.output("Uploading script..")

        count = 0
        script_json = json.dumps(script_data)
        while True:
            count += 1
            self.output(
                "Script upload attempt {}".format(count), verbose_level=2,
            )
            if obj_id:
                r = http.put(url, headers=headers, data=script_json, timeout=60)
            else:
                r = http.post(url, headers=headers, data=script_json, timeout=60)
            if r.status_code == 200 or r.status_code == 201:
                self.output("Script uploaded successfully")
                break
            if r.status_code == 409:
                raise ProcessorError("ERROR: Script upload failed due to a conflict")
            if count > 5:
                self.output("Script upload did not succeed after 5 attempts")
                self.output("\nHTTP POST Response Code: {}".format(r.status_code))
                raise ProcessorError("ERROR: Script upload failed ")
            sleep(10)
        return r

    def main(self):
        """Do the main thing here"""
        self.jamf_url = self.env.get("JSS_URL")
        self.jamf_user = self.env.get("API_USERNAME")
        self.jamf_password = self.env.get("API_PASSWORD")
        self.script_path = self.env.get("script_path")
        self.script_category = self.env.get("script_category")
        self.script_priority = self.env.get("script_priority")
        self.osrequirements = self.env.get("osrequirements")
        self.script_info = self.env.get("script_info")
        self.script_notes = self.env.get("script_notes")
        self.script_parameter4 = self.env.get("script_parameter4")
        self.script_parameter5 = self.env.get("script_parameter5")
        self.script_parameter6 = self.env.get("script_parameter6")
        self.script_parameter7 = self.env.get("script_parameter7")
        self.script_parameter8 = self.env.get("script_parameter8")
        self.script_parameter9 = self.env.get("script_parameter9")
        self.script_parameter10 = self.env.get("script_parameter10")
        self.script_parameter11 = self.env.get("script_parameter11")
        self.replace = self.env.get("replace_script")
        # handle setting replace in overrides
        if not self.replace or self.replace == "False":
            self.replace = False

        # clear any pre-existing summary result
        if "jamfscriptuploader_summary_result" in self.env:
            del self.env["jamfscriptuploader_summary_result"]

        # encode the username and password into a basic auth b64 encoded string
        credentials = f"{self.jamf_user}:{self.jamf_password}"
        enc_creds_bytes = b64encode(credentials.encode("utf-8"))
        enc_creds = str(enc_creds_bytes, "utf-8")

        # now get the session token
        token = self.get_uapi_token(self.jamf_url, enc_creds)

        # get the id for a category if supplied
        if self.script_category:
            self.output("Checking categories for {}".format(self.script_category))
            category_id = self.get_uapi_obj_id_from_name(
                self.jamf_url, "categories", self.script_category, token
            )
            if not category_id:
                self.output("WARNING: Category not found!")
                category_id = "-1"
            else:
                self.output(
                    "Category {} found: ID={}".format(self.script_category, category_id)
                )
        else:
            self.script_category = ""

        # handle files with no path
        if "/" not in self.script_path:
            self.script_path = self.get_path_to_file(self.script_path)

        # now start the process of uploading the object
        script_name = os.path.basename(self.script_path)

        # check for existing script
        self.output("Checking '{}' on {}".format(script_name, self.jamf_url))
        self.output(
            "Full path: {}".format(self.script_path), verbose_level=2,
        )
        obj_id = self.get_uapi_obj_id_from_name(
            self.jamf_url, "scripts", script_name, token
        )

        if obj_id:
            self.output("Script '{}' already exists: ID {}".format(script_name, obj_id))
            if not self.replace:
                self.output(
                    "Not replacing existing script. Use --replace to enforce.",
                    verbose_level=1,
                )
                return

        # post the script
        self.upload_script(
            self.jamf_url,
            script_name,
            self.script_path,
            category_id,
            self.script_category,
            self.script_info,
            self.script_notes,
            self.script_priority,
            self.script_parameter4,
            self.script_parameter5,
            self.script_parameter6,
            self.script_parameter7,
            self.script_parameter8,
            self.script_parameter9,
            self.script_parameter10,
            self.script_parameter11,
            self.osrequirements,
            token,
            obj_id,
        )

        # output the summary
        self.env["script_name"] = script_name
        self.env["jamfscriptuploader_summary_result"] = {
            "summary_text": "The following scripts were created or updated in Jamf Pro:",
            "report_fields": [
                "script",
                "path",
                "category",
                "priority",
                "os_req",
                "info",
                "notes",
                "P4",
                "P5",
                "P6",
                "P7",
                "P8",
                "P9",
                "P10",
                "P11",
            ],
            "data": {
                "script": script_name,
                "path": self.script_path,
                "category": self.script_category,
                "priority": str(self.script_priority),
                "info": self.script_info,
                "os_req": self.osrequirements,
                "notes": self.script_notes,
                "P4": self.script_parameter4,
                "P5": self.script_parameter5,
                "P6": self.script_parameter6,
                "P7": self.script_parameter7,
                "P8": self.script_parameter8,
                "P9": self.script_parameter9,
                "P10": self.script_parameter10,
                "P11": self.script_parameter11,
            },
        }


if __name__ == "__main__":
    PROCESSOR = JamfScriptUploader()
    PROCESSOR.execute_shell()
