#!/usr/local/autopkg/python

"""
JamfPolicyUploader processor for uploading policies to Jamf Pro using AutoPkg
    by G Pugh
"""

import json
import re
import os
import subprocess
import uuid
import xml.etree.ElementTree as ElementTree

from collections import namedtuple
from base64 import b64encode
from pathlib import Path
from shutil import rmtree
from time import sleep
from xml.sax.saxutils import escape

from autopkglib import Processor, ProcessorError  # pylint: disable=import-error


class JamfPolicyUploader(Processor):
    """A processor for AutoPkg that will upload a policy to a Jamf Cloud or on-prem
    server. Optionally, an icon can be uploaded and associated with the policy."""

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
        "policy_name": {
            "required": False,
            "description": "Policy name",
            "default": "",
        },
        "icon": {
            "required": False,
            "description": "Full path to Self Service icon",
            "default": "",
        },
        "policy_template": {
            "required": False,
            "description": "Full path to the XML template",
        },
        "replace_policy": {
            "required": False,
            "description": "Overwrite an existing policy if True.",
            "default": False,
        },
        "replace_icon": {
            "required": False,
            "description": "Overwrite an existing policy icon if True.",
            "default": False,
        },
    }

    output_variables = {
        "jamfpolicyuploader_summary_result": {
            "description": "Description of interesting results.",
        },
    }

    def write_json_file(self, data, tmp_dir="/tmp/jamf_upload"):
        """dump some json to a temporary file"""
        self.make_tmp_dir(tmp_dir)
        tf = os.path.join(tmp_dir, f"jamf_upload_{str(uuid.uuid4())}.json")
        with open(tf, "w") as fp:
            json.dump(data, fp)
        return tf

    def write_temp_file(self, data, tmp_dir="/tmp/jamf_upload"):
        """dump some text to a temporary file"""
        self.make_tmp_dir(tmp_dir)
        tf = os.path.join(tmp_dir, f"jamf_upload_{str(uuid.uuid4())}.txt")
        with open(tf, "w") as fp:
            fp.write(data)
        return tf

    def make_tmp_dir(self, tmp_dir="/tmp/jamf_upload"):
        """make the tmp directory"""
        if not os.path.exists(tmp_dir):
            os.mkdir(tmp_dir)
        return tmp_dir

    def clear_tmp_dir(self, tmp_dir="/tmp/jamf_upload"):
        """remove the tmp directory"""
        if os.path.exists(tmp_dir):
            rmtree(tmp_dir)
        return tmp_dir

    def curl(self, method, url, auth, data="", additional_headers=""):
        """
        build a curl command based on method (GET, PUT, POST, DELETE)
        If the URL contains 'uapi' then token should be passed to the auth variable,
        otherwise the enc_creds variable should be passed to the auth variable
        """
        tmp_dir = self.make_tmp_dir()
        headers_file = os.path.join(tmp_dir, "curl_headers_from_jamf_upload.txt")
        output_file = os.path.join(tmp_dir, "curl_output_from_jamf_upload.txt")
        cookie_jar = os.path.join(tmp_dir, "curl_cookies_from_jamf_upload.txt")

        # build the curl command
        curl_cmd = [
            "/usr/bin/curl",
            "-X",
            method,
            "-D",
            headers_file,
            "--output",
            output_file,
            url,
        ]

        # the authorisation is Basic unless we are using the uapi and already have a token
        if "uapi" in url and "tokens" not in url:
            curl_cmd.extend(["--header", f"authorization: Bearer {auth}"])
        else:
            curl_cmd.extend(["--header", f"authorization: Basic {auth}"])

        # set either Accept or Content-Type depending on method
        if method == "GET" or method == "DELETE":
            curl_cmd.extend(["--header", "Accept: application/json"])
        # icon upload requires special method
        elif method == "POST" and "fileuploads" in url:
            curl_cmd.extend(["--header", "Content-type: multipart/form-data"])
            curl_cmd.extend(["--form", f"name=@{data}"])
        elif method == "POST" or method == "PUT":
            if data:
                curl_cmd.extend(["--upload-file", data])
            # uapi sends json, classic API must send xml
            if "uapi" in url:
                curl_cmd.extend(["--header", "Content-type: application/json"])
            else:
                curl_cmd.extend(["--header", "Content-type: application/xml"])
        else:
            self.output(f"WARNING: HTTP method {method} not supported")

        # write session
        try:
            with open(headers_file, "r") as file:
                headers = file.readlines()
            existing_headers = [x.strip() for x in headers]
            for header in existing_headers:
                if "APBALANCEID" in header or "AWSALB" in header:
                    with open(cookie_jar, "w") as fp:
                        fp.write(header)
        except IOError:
            pass

        # look for existing session
        try:
            with open(cookie_jar, "r") as file:
                headers = file.readlines()
            existing_headers = [x.strip() for x in headers]
            for header in existing_headers:
                if "APBALANCEID" in header or "AWSALB" in header:
                    cookie = header.split()[1].rstrip(";")
                    self.output(f"Existing cookie found: {cookie}", verbose_level=2)
                    curl_cmd.extend(["--cookie", cookie])
        except IOError:
            self.output(
                "No existing cookie found - starting new session", verbose_level=2
            )

        # additional headers for advanced requests
        if additional_headers:
            curl_cmd.extend(additional_headers)

        self.output(f"curl command: {' '.join(curl_cmd)}", verbose_level=3)

        # now subprocess the curl command and build the r tuple which contains the
        # headers, status code and outputted data
        subprocess.check_output(curl_cmd)

        r = namedtuple(
            "r", ["headers", "status_code", "output"], defaults=(None, None, None)
        )
        try:
            with open(headers_file, "r") as file:
                headers = file.readlines()
            r.headers = [x.strip() for x in headers]
            for header in r.headers:  # pylint: disable=not-an-iterable
                if re.match(r"HTTP/(1.1|2)", header) and "Continue" not in header:
                    r.status_code = int(header.split()[1])
        except IOError:
            raise ProcessorError(f"WARNING: {headers_file} not found")
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            with open(output_file, "rb") as file:
                if "uapi" in url:
                    r.output = json.load(file)
                else:
                    r.output = file.read()
        else:
            self.output(f"No output from request ({output_file} not found or empty)")
        return r()

    def status_check(self, r, endpoint_type, obj_name):
        """Return a message dependent on the HTTP response"""
        if r.status_code == 200 or r.status_code == 201:
            self.output(f"{endpoint_type} '{obj_name}' uploaded successfully")
            return "break"
        elif r.status_code == 409:
            self.output(r.output, verbose_level=2)
            raise ProcessorError(
                f"WARNING: {endpoint_type} '{obj_name}' upload failed due to a conflict"
            )
        elif r.status_code == 401:
            raise ProcessorError(
                f"ERROR: {endpoint_type} '{obj_name}' upload failed due to permissions error"
            )
        else:
            self.output(f"WARNING: {endpoint_type} '{obj_name}' upload failed")
            self.output(r.output, verbose_level=2)

    def substitute_assignable_keys(self, data, xml_escape=False):
        """substitutes any key in the inputted text using the %MY_KEY% nomenclature"""
        # whenever %MY_KEY% is found in a template, it is replaced with the assigned value of MY_KEY
        # do a triple-pass to ensure that all keys are substituted
        loop = 5
        while loop > 0:
            loop = loop - 1
            found_keys = re.findall(r"\%\w+\%", data)
            if not found_keys:
                break
            found_keys = [i.replace("%", "") for i in found_keys]
            for found_key in found_keys:
                if self.env.get(found_key):
                    self.output(
                        (
                            f"Replacing any instances of '{found_key}' with",
                            f"'{str(self.env.get(found_key))}'",
                        ),
                        verbose_level=2,
                    )
                    if xml_escape:
                        replacement_key = escape(self.env.get(found_key))
                    else:
                        replacement_key = self.env.get(found_key)
                    data = data.replace(f"%{found_key}%", replacement_key)
                else:
                    self.output(f"WARNING: '{found_key}' has no replacement object!",)
                    raise ProcessorError("Unsubstituable key in template found")
        return data

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
        url = f"{jamf_url}/JSSResource/{object_types[object_type]}"
        r = self.curl("GET", url, enc_creds)

        if r.status_code == 200:
            object_list = json.loads(r.output)
            self.output(
                object_list, verbose_level=4,
            )
            obj_id = 0
            for obj in object_list[object_list_types[object_type]]:
                self.output(
                    obj, verbose_level=3,
                )
                # we need to check for a case-insensitive match
                if obj["name"].lower() == object_name.lower():
                    obj_id = obj["id"]
            return obj_id

    def get_path_to_file(self, filename):
        """AutoPkg is not very good at finding dependent files. This function
        will look inside the search directories for any supplied file """
        # if the supplied file is not a path, use the override directory or
        # recipe dir if no override
        recipe_dir = self.env.get("RECIPE_DIR")
        filepath = os.path.join(recipe_dir, filename)
        if os.path.exists(filepath):
            self.output(f"File found at: {filepath}")
            return filepath

        # if not found, search parent directories to look for it
        if self.env.get("PARENT_RECIPES"):
            # also look in the repos containing the parent recipes.
            parent_recipe_dirs = list(
                {os.path.dirname(item) for item in self.env["PARENT_RECIPES"]}
            )
            matched_filepath = ""
            for d in parent_recipe_dirs:
                # check if we are in the root of a parent repo, if not, ascend to the root
                # note that if the parents are not in a git repo, only the same
                # directory as the recipe will be searched for templates
                if not os.path.isdir(os.path.join(d, ".git")):
                    d = os.path.dirname(d)
                for path in Path(d).rglob(filename):
                    matched_filepath = str(path)
                    break
            if matched_filepath:
                self.output(f"File found at: {matched_filepath}")
                return matched_filepath

    def get_api_obj_value_from_id(
        self, jamf_url, object_type, obj_id, obj_path, enc_creds
    ):
        """get the value of an item in a Classic API object"""
        # define the relationship between the object types and their URL
        # we could make this shorter with some regex but I think this way is clearer
        object_types = {
            "package": "packages",
            "computer_group": "computergroups",
            "policy": "policies",
            "extension_attribute": "computerextensionattributes",
        }
        url = "{}/JSSResource/{}/id/{}".format(
            jamf_url, object_types[object_type], obj_id
        )
        r = self.curl("GET", url, enc_creds)
        if r.status_code == 200:
            obj_content = json.loads(r.output)
            self.output(obj_content, verbose_level=4)

            # convert an xpath to json
            xpath_list = obj_path.split("/")
            value = obj_content[object_type]
            for i in range(0, len(xpath_list)):
                if xpath_list[i]:
                    try:
                        value = value[xpath_list[i]]
                        self.output(value, verbose_level=3)
                    except KeyError:
                        value = ""
                        break
            if value:
                self.output(
                    "Value of '{}': {}".format(obj_path, value), verbose_level=2
                )
            return value

    def prepare_policy_template(self, policy_name, policy_template):
        """prepare the policy contents"""
        # import template from file and replace any keys in the template
        if os.path.exists(policy_template):
            with open(policy_template, "r") as file:
                template_contents = file.read()
        else:
            raise ProcessorError("Template does not exist!")

        # substitute user-assignable keys
        policy_name = self.substitute_assignable_keys(policy_name)
        template_contents = self.substitute_assignable_keys(
            template_contents, xml_escape=True
        )

        self.output("Policy data:", verbose_level=2)
        self.output(template_contents, verbose_level=2)

        # write the template to temp file
        template_xml = self.write_temp_file(template_contents)
        return policy_name, template_xml

    def upload_policy(
        self, jamf_url, enc_creds, policy_name, template_xml, obj_id=None
    ):
        """Upload policy"""
        # if we find an object ID we put, if not, we post
        if obj_id:
            url = "{}/JSSResource/policies/id/{}".format(jamf_url, obj_id)
        else:
            url = "{}/JSSResource/policies/id/0".format(jamf_url)

        self.output("Uploading Policy...")

        count = 0
        while True:
            count += 1
            self.output("Policy upload attempt {}".format(count), verbose_level=2)
            method = "PUT" if obj_id else "POST"
            r = self.curl(method, url, enc_creds, template_xml)
            # check HTTP response
            if self.status_check(r, "Policy", policy_name) == "break":
                break
            if count > 5:
                self.output("WARNING: Policy upload did not succeed after 5 attempts")
                self.output("\nHTTP POST Response Code: {}".format(r.status_code))
                raise ProcessorError("ERROR: Policy upload failed ")
            sleep(30)

        # clean up temp files
        self.clear_tmp_dir()

        return r

    def upload_policy_icon(
        self,
        jamf_url,
        enc_creds,
        policy_name,
        policy_icon_path,
        replace_icon,
        obj_id=None,
    ):
        """Upload an icon to the policy that was just created"""
        # check that the policy exists.
        # Use the obj_id if we have it, or use name if we don't have it yet
        # We may need a wait loop here for new policies
        if not obj_id:
            # check for existing policy
            self.output("\nChecking '{}' on {}".format(policy_name, jamf_url))
            obj_id = self.check_api_obj_id_from_name(
                jamf_url, "policy", policy_name, enc_creds
            )
            if not obj_id:
                raise ProcessorError(
                    "ERROR: could not locate ID for policy '{}' so cannot upload icon".format(
                        policy_name
                    )
                )

        # Now grab the name of the existing icon using the API
        existing_icon = self.get_api_obj_value_from_id(
            jamf_url,
            "policy",
            obj_id,
            "self_service/self_service_icon/filename",
            enc_creds,
        )
        if existing_icon:
            self.output(
                "Existing policy icon is '{}'".format(existing_icon), verbose_level=1
            )
        # If the icon naame matches that we already have, don't upload again
        # unless --replace-icon is set
        policy_icon_name = os.path.basename(policy_icon_path)
        if existing_icon == policy_icon_name:
            self.output(
                "Policy icon '{}' already exists: ID {}".format(existing_icon, obj_id)
            )

        if existing_icon != policy_icon_name or replace_icon:
            url = "{}/JSSResource/fileuploads/policies/id/{}".format(jamf_url, obj_id)

            self.output("Uploading icon...")

            count = 0
            while True:
                count += 1
                self.output("Icon upload attempt {}".format(count), verbose_level=2)
                r = self.curl("POST", url, enc_creds, policy_icon_path)
                # check HTTP response
                if self.status_check(r, "Icon", policy_icon_name) == "break":
                    break
                if count > 5:
                    print("WARNING: Icon upload did not succeed after 5 attempts")
                    print("\nHTTP POST Response Code: {}".format(r.status_code))
                    raise ProcessorError("ERROR: Icon upload failed")
                sleep(30)
        else:
            self.output("Not replacing icon. Set replace_icon='True' to enforce...")
        return policy_icon_name

    def main(self):
        """Do the main thing here"""
        self.jamf_url = self.env.get("JSS_URL")
        self.jamf_user = self.env.get("API_USERNAME")
        self.jamf_password = self.env.get("API_PASSWORD")
        self.policy_name = self.env.get("policy_name")
        self.policy_template = self.env.get("policy_template")
        self.icon = self.env.get("icon")
        self.replace = self.env.get("replace_policy")
        # handle setting replace in overrides
        if not self.replace or self.replace == "False":
            self.replace = False
        self.replace_icon = self.env.get("replace_icon")
        # handle setting replace in overrides
        if not self.replace_icon or self.replace_icon == "False":
            self.replace_icon = False
        self.policy_updated = False

        # clear any pre-existing summary result
        if "jamfpolicyuploader_summary_result" in self.env:
            del self.env["jamfpolicyuploader_summary_result"]

        # encode the username and password into a basic auth b64 encoded string
        credentials = f"{self.jamf_user}:{self.jamf_password}"
        enc_creds_bytes = b64encode(credentials.encode("utf-8"))
        enc_creds = str(enc_creds_bytes, "utf-8")

        # handle files with no path
        if "/" not in self.policy_template:
            found_template = self.get_path_to_file(self.policy_template)
            if found_template:
                self.policy_template = found_template
            else:
                raise ProcessorError(
                    f"ERROR: Policy file {self.policy_template} not found"
                )

        # we need to substitute the values in the policy name and template now to
        # account for version strings in the name
        self.policy_name, template_xml = self.prepare_policy_template(
            self.policy_name, self.policy_template
        )

        # now start the process of uploading the object
        self.output(f"Checking for existing '{self.policy_name}' on {self.jamf_url}")

        # check for existing - requires obj_name
        obj_type = "policy"
        obj_id = self.check_api_obj_id_from_name(
            self.jamf_url, obj_type, self.policy_name, enc_creds
        )

        if obj_id:
            self.output(
                "Policy '{}' already exists: ID {}".format(self.policy_name, obj_id)
            )
            if self.replace:
                self.output(
                    "Replacing existing policy as 'replace_policy' is set to {}".format(
                        self.replace
                    ),
                    verbose_level=1,
                )
                r = self.upload_policy(
                    self.jamf_url, enc_creds, self.policy_name, template_xml, obj_id,
                )
                self.policy_updated = True
            else:
                self.output(
                    "Not replacing existing policy. Use replace_policy='True' to enforce.",
                    verbose_level=1,
                )
                return
        else:
            # post the item
            r = self.upload_policy(
                self.jamf_url, enc_creds, self.policy_name, template_xml,
            )
            self.policy_updated = True

        # now upload the icon to the policy if specified in the args
        policy_icon_name = ""
        if self.icon:
            # handle files with no path
            if "/" not in self.icon:
                found_icon = self.get_path_to_file(self.icon)
                if found_icon:
                    self.icon = found_icon
                else:
                    raise ProcessorError(
                        f"ERROR: Policy icon file {self.icon} not found"
                    )

            # get the policy_id returned from the HTTP response
            try:
                policy_id = ElementTree.fromstring(r.output).findtext("id")
                policy_icon_name = self.upload_policy_icon(
                    self.jamf_url,
                    enc_creds,
                    self.policy_name,
                    self.icon,
                    self.replace_icon,
                    policy_id,
                )
            except UnboundLocalError:
                policy_icon_name = self.upload_policy_icon(
                    self.jamf_url,
                    enc_creds,
                    self.policy_name,
                    self.icon,
                    self.replace_icon,
                )

        # output the summary
        self.env["policy_name"] = self.policy_name
        self.env["policy_updated"] = self.policy_updated
        if self.policy_updated:
            self.env["jamfpolicyuploader_summary_result"] = {
                "summary_text": "The following policies were created or updated in Jamf Pro:",
                "report_fields": ["policy", "template", "icon"],
                "data": {
                    "policy": self.policy_name,
                    "template": self.policy_template,
                    "icon": policy_icon_name,
                },
            }


if __name__ == "__main__":
    PROCESSOR = JamfPolicyUploader()
    PROCESSOR.execute_shell()
