#!/usr/local/autopkg/python

"""
JamfSoftwareRestrictionUploader processor for uploading computer restrictions
to Jamf Pro using AutoPkg
    by G Pugh
"""

import json
import re
import os
import subprocess
import uuid

from base64 import b64encode
from collections import namedtuple
from datetime import datetime
from pathlib import Path
from shutil import rmtree
from time import sleep
from xml.sax.saxutils import escape
from autopkglib import (
    APLooseVersion,
    Processor,
    ProcessorError,
)  # pylint: disable=import-error


class JamfSoftwareRestrictionUploader(Processor):
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
        "restriction_name": {
            "required": True,
            "description": "Software Restriction name",
            "default": "",
        },
        "restriction_template": {
            "required": True,
            "description": "Path to Software Restriction XML template file",
            "default": "RestrictionTemplate-no-scope.xml",
        },
        "restriction_computergroup": {
            "required": False,
            "description": "A single computer group to add to the scope.",
            "default": "",
        },
        "process_name": {
            "required": False,
            "description": "Process name to restrict",
        },
        "display_message": {
            "required": False,
            "description": "Message to display to users when the restriction is invoked",
        },
        "match_exact_process_name": {
            "required": False,
            "description": "Match only the exact process name if True",
            "default": False,
        },
        "restriction_send_notification": {
            "required": False,
            "description": "Send a notification when the restriction is invoked if True",
            "default": False,
        },
        "kill_process": {
            "required": False,
            "description": "Kill the process when the restriction is invoked if True",
            "default": False,
        },
        "delete_executable": {
            "required": False,
            "description": "Delete the executable when the restriction is invoked if True",
            "default": False,
        },
        "replace_restriction": {
            "required": False,
            "description": "overwrite an existing Software Restriction if True",
            "default": False,
        },
    }

    output_variables = {
        "jamfsoftwarerestriction_summary_result": {
            "description": "Description of interesting results.",
        },
    }

    # do not edit directly - copy from template
    def api_endpoints(self, object_type):
        """Return the endpoint URL from the object type"""
        api_endpoints = {
            "category": "api/v1/categories",
            "extension_attribute": "JSSResource/computerextensionattributes",
            "computer_group": "JSSResource/computergroups",
            "jamf_pro_version": "api/v1/jamf-pro-version",
            "package": "JSSResource/packages",
            "os_x_configuration_profile": "JSSResource/osxconfigurationprofiles",
            "policy": "JSSResource/policies",
            "policy_icon": "JSSResource/fileuploads/policies",
            "restricted_software": "JSSResource/restrictedsoftware",
            "script": "api/v1/scripts",
            "token": "api/v1/auth/token",
        }
        return api_endpoints[object_type]

    # do not edit directly - copy from template
    def object_list_types(self, object_type):
        """Return a XML dictionary type from the object type"""
        object_list_types = {
            "computer_group": "computer_groups",
            "extension_attribute": "computer_extension_attributes",
            "os_x_configuration_profile": "os_x_configuration_profiles",
            "package": "packages",
            "policy": "policies",
            "restricted_software": "restricted_software",
            "script": "scripts",
        }
        return object_list_types[object_type]

    # do not edit directly - copy from template
    def write_json_file(self, data, tmp_dir="/tmp/jamf_upload"):
        """dump some json to a temporary file"""
        self.make_tmp_dir(tmp_dir)
        tf = os.path.join(tmp_dir, f"jamf_upload_{str(uuid.uuid4())}.json")
        with open(tf, "w") as fp:
            json.dump(data, fp)
        return tf

    # do not edit directly - copy from template
    def write_temp_file(self, data, tmp_dir="/tmp/jamf_upload"):
        """dump some text to a temporary file"""
        self.make_tmp_dir(tmp_dir)
        tf = os.path.join(tmp_dir, f"jamf_upload_{str(uuid.uuid4())}.txt")
        with open(tf, "w") as fp:
            fp.write(data)
        return tf

    # do not edit directly - copy from template
    def make_tmp_dir(self, tmp_dir="/tmp/jamf_upload"):
        """make the tmp directory"""
        if not os.path.exists(tmp_dir):
            os.mkdir(tmp_dir)
        return tmp_dir

    # do not edit directly - copy from template
    def clear_tmp_dir(self, tmp_dir="/tmp/jamf_upload"):
        """remove the tmp directory"""
        if os.path.exists(tmp_dir):
            rmtree(tmp_dir)
        return tmp_dir

    # do not edit directly - copy from template
    def get_enc_creds(self, user, password):
        """encode the username and password into a b64-encoded string"""
        credentials = f"{self.jamf_user}:{self.jamf_password}"
        enc_creds_bytes = b64encode(credentials.encode("utf-8"))
        enc_creds = str(enc_creds_bytes, "utf-8")
        return enc_creds

    # do not edit directly - copy from template
    def check_api_token(self, token_file="/tmp/jamf_upload_token"):
        """Check validity of an existing token"""
        if os.path.exists(token_file):
            with open(token_file, "rb") as file:
                data = json.load(file)
                # check that there is a 'token' key
                if data["token"]:
                    # check if it's expired or not
                    expires = datetime.strptime(
                        data["expires"], "%Y-%m-%dT%H:%M:%S.%fZ"
                    )
                    if expires > datetime.utcnow():
                        self.output("Existing token is valid")
                        return data["token"]
                else:
                    self.output("Token not found in file", verbose_level=2)
        self.output("No existing valid token found", verbose_level=2)

    # do not edit directly - copy from template
    def write_token_to_json_file(self, data, token_file="/tmp/jamf_upload_token"):
        """dump the token and expiry as json to a temporary file"""
        with open(token_file, "w") as fp:
            json.dump(data, fp)

    # do not edit directly - copy from template
    def get_api_token(self, jamf_url, enc_creds):
        """get a token for the Jamf Pro API or Classic API for Jamf Pro 10.35+"""
        url = jamf_url + "/" + self.api_endpoints("token")
        r = self.curl(request="POST", url=url, enc_creds=enc_creds)
        if r.status_code == 200:
            try:
                self.output(r.output, verbose_level=2)
                token = str(r.output["token"])
                expires = str(r.output["expires"])

                # write the data to a file
                self.write_token_to_json_file(r.output)
                self.output("Session token received")
                self.output(f"Token: {token}", verbose_level=2)
                self.output(f"Expires: {expires}", verbose_level=2)
                return token
            except KeyError:
                self.output("ERROR: No token received in response")
        else:
            self.output(f"ERROR: No token received (response: {r.status_code})")

    # do not edit directly - copy from template
    def get_jamf_pro_version(self, jamf_url, token):
        """get the Jamf Pro version so that we can figure out which auth method to use for the
        Classic API"""
        url = jamf_url + "/" + self.api_endpoints("jamf_pro_version")
        r = self.curl(request="GET", url=url, token=token)
        if r.status_code == 200:
            try:
                jamf_pro_version = str(r.output["version"])
                self.output(f"Jamf Pro Version: {jamf_pro_version}")
                return jamf_pro_version
            except KeyError:
                self.output("ERROR: No version received")
                return

    # do not edit directly - copy from template
    def validate_jamf_pro_version(self, jamf_url, token):
        """return true if Jamf Pro version is 10.35 or greater"""
        jamf_pro_version = self.get_jamf_pro_version(jamf_url, token)
        if APLooseVersion(jamf_pro_version) >= APLooseVersion("10.35.0"):
            return True
        else:
            return False

    # do not edit directly - copy from template
    def curl(
        self, request="", url="", token="", enc_creds="", data="", additional_headers=""
    ):
        """
        build a curl command based on method (GET, PUT, POST, DELETE)
        If the URL contains 'api' then token should be passed to the auth variable,
        otherwise the enc_creds variable should be passed to the auth variable
        """
        tmp_dir = self.make_tmp_dir()
        headers_file = os.path.join(tmp_dir, "curl_headers_from_jamf_upload.txt")
        output_file = os.path.join(tmp_dir, "curl_output_from_jamf_upload.txt")
        cookie_jar = os.path.join(tmp_dir, "curl_cookies_from_jamf_upload.txt")

        # build the curl command
        if url:
            curl_cmd = [
                "/usr/bin/curl",
                "--silent",
                "--show-error",
                "-D",
                headers_file,
                "--output",
                output_file,
                url,
            ]
        else:
            raise ProcessorError("No URL supplied")

        if request:
            curl_cmd.extend(["--request", request])

        # authorisation if using Jamf Pro API or Classic API
        # if using Jamf Pro API, or Classic API on Jamf Pro 10.35+,
        # and we already have a token, then we use the token for authorization.
        # The Slack webhook doesn't have authentication
        if token:
            curl_cmd.extend(["--header", f"authorization: Bearer {token}"])
        # basic auth to obtain a token, or for classic API older than 10.35
        elif enc_creds:
            curl_cmd.extend(["--header", f"authorization: Basic {enc_creds}"])

        # set either Accept or Content-Type depending on method
        if request == "GET" or request == "DELETE":
            curl_cmd.extend(["--header", "Accept: application/json"])
        # icon upload requires special method
        elif request == "POST" and "fileuploads" in url:
            curl_cmd.extend(["--header", "Content-type: multipart/form-data"])
            curl_cmd.extend(["--form", f"name=@{data}"])
        elif request == "POST" or request == "PUT":
            if data:
                if "slack" in url:
                    # slack requires data argument
                    curl_cmd.extend(["--data", data])
                else:
                    # jamf data upload requires upload-file argument
                    curl_cmd.extend(["--upload-file", data])
            # Jamf Pro API and Slack accepts json, but Classic API accepts xml
            if "JSSResource" in url:
                curl_cmd.extend(["--header", "Content-type: application/xml"])
            else:
                curl_cmd.extend(["--header", "Content-type: application/json"])
        else:
            self.output(f"WARNING: HTTP method {request} not supported")

        # write session for jamf requests
        if "/api/" in url or "JSSResource" in url or "dbfileupload" in url:
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
                if "/api/" in url:
                    r.output = json.load(file)
                else:
                    r.output = file.read()
        else:
            self.output(f"No output from request ({output_file} not found or empty)")
        return r()

    # do not edit directly - copy from template
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
            raise ProcessorError(f"ERROR: {endpoint_type} '{obj_name}' upload failed")

    # do not edit directly - copy from template
    def get_path_to_file(self, filename):
        """AutoPkg is not very good at finding dependent files. This function
        will look inside the search directories for any supplied file"""
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

    # do not edit directly - copy from template
    def get_api_obj_id_from_name(
        self, jamf_url, object_name, object_type, enc_creds="", token=""
    ):
        """check if a Classic API object with the same name exists on the server"""
        # define the relationship between the object types and their URL
        url = jamf_url + "/" + self.api_endpoints(object_type)
        r = self.curl(request="GET", url=url, enc_creds=enc_creds, token=token)

        if r.status_code == 200:
            object_list = json.loads(r.output)
            self.output(
                object_list,
                verbose_level=4,
            )
            obj_id = 0
            for obj in object_list[self.object_list_types(object_type)]:
                self.output(
                    obj,
                    verbose_level=3,
                )
                # we need to check for a case-insensitive match
                if obj["name"].lower() == object_name.lower():
                    obj_id = obj["id"]
            return obj_id

    # do not edit directly - copy from template
    def get_api_obj_value_from_id(
        self, jamf_url, object_type, obj_id, obj_path, enc_creds="", token=""
    ):
        """get the value of an item in a Classic API object"""
        # define the relationship between the object types and their URL
        # we could make this shorter with some regex but I think this way is clearer
        url = "{}/{}/id/{}".format(jamf_url, self.api_endpoints(object_type), obj_id)
        r = self.curl(request="GET", url=url, enc_creds=enc_creds)
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

    # do not edit directly - copy from template
    def substitute_assignable_keys(self, data, xml_escape=False):
        """substitutes any key in the inputted text using the %MY_KEY% nomenclature"""
        # do a four-pass to ensure that all keys are substituted
        print(data)  # TEMP
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
                    self.output(
                        f"WARNING: '{found_key}' has no replacement object!",
                    )
                    raise ProcessorError("Unsubstitutable key in template found")
        return data

    def substitute_limited_assignable_keys(
        self, data, cli_custom_keys, xml_escape=False
    ):
        """substitutes any key in the inputted text using the %MY_KEY% nomenclature.
        Whenever %MY_KEY% is found in the provided data, it is replaced with the assigned
        value of MY_KEY. A five-times passa through is done to ensure that all keys are substituted.

        Optionally, if the xml_escape key is set, the value is escaped for XML special characters.
        This is designed primarily to account for ampersands in the substituted strings."""
        loop = 5
        while loop > 0:
            loop = loop - 1
            found_keys = re.findall(r"\%\w+\%", data)
            if not found_keys:
                break
            found_keys = [i.replace("%", "") for i in found_keys]
            for found_key in found_keys:
                if cli_custom_keys[found_key]:
                    self.output(
                        f"Replacing any instances of '{found_key}' with "
                        f"'{str(cli_custom_keys[found_key])}'",
                        verbose_level=2,
                    )
                    if xml_escape:
                        replacement_key = escape(cli_custom_keys[found_key])
                    else:
                        replacement_key = cli_custom_keys[found_key]
                    data = data.replace(f"%{found_key}%", replacement_key)
                else:
                    self.output(
                        f"WARNING: '{found_key}' has no replacement object!",
                    )
        return data

    def pretty_print_xml(self, xml):
        proc = subprocess.Popen(
            ["xmllint", "--format", "/dev/stdin"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        (output, _) = proc.communicate(xml)
        return output

    def upload_restriction(
        self,
        jamf_url,
        restriction_name,
        process_name,
        display_message,
        match_exact_process_name,
        send_notification,
        kill_process,
        delete_executable,
        computergroup_name,
        template_contents,
        obj_id=None,
        enc_creds="",
        token="",
    ):
        """Update Software Restriction metadata."""

        # substitute user-assignable keys
        replaceable_keys = {
            "restriction_name": restriction_name,
            "process_name": process_name,
            "display_message": display_message,
            "match_exact_process_name": match_exact_process_name,
            "send_notification": send_notification,
            "kill_process": kill_process,
            "delete_executable": delete_executable,
            "computergroup_name": computergroup_name,
        }

        # substitute user-assignable keys (escaping for XML)
        template_contents = self.substitute_limited_assignable_keys(
            template_contents, replaceable_keys, xml_escape=True
        )

        self.output("Software Restriction to be uploaded:", verbose_level=2)
        self.output(template_contents, verbose_level=2)

        self.output("Uploading Software Restriction...")

        # write the template to temp file
        template_xml = self.write_temp_file(template_contents)

        # if we find an object ID we put, if not, we post
        object_type = "restricted_software"
        if obj_id:
            url = "{}/{}/id/{}".format(
                jamf_url, self.api_endpoints(object_type), obj_id
            )
        else:
            url = "{}/{}/id/0".format(jamf_url, self.api_endpoints(object_type))

        count = 0
        while True:
            count += 1
            self.output(f"Software Restriction upload attempt {count}", verbose_level=1)
            request = "PUT" if obj_id else "POST"
            r = self.curl(
                request=request,
                url=url,
                enc_creds=enc_creds,
                token=token,
                data=template_xml,
            )

            # check HTTP response
            if (
                self.status_check(r, "Software Restriction", restriction_name)
                == "break"
            ):
                break
            if count > 5:
                self.output(
                    "ERROR: Software Restriction upload did not succeed after 5 attempts"
                )
                self.output(f"\nHTTP POST Response Code: {r.status_code}")
                break
            sleep(10)

        return r

    def main(self):
        """Do the main thing here"""
        self.jamf_url = self.env.get("JSS_URL")
        self.jamf_user = self.env.get("API_USERNAME")
        self.jamf_password = self.env.get("API_PASSWORD")
        self.restriction_name = self.env.get("restriction_name")
        self.process_name = self.env.get("process_name")
        self.template = self.env.get("restriction_template")
        # handle setting display_message in overrides
        self.display_message = self.env.get("display_message")
        if not self.display_message:
            self.display_message = "False"
        # handle setting match_exact_process_name in overrides
        self.match_exact_process_name = self.env.get("match_exact_process_name")
        if not self.match_exact_process_name:
            self.match_exact_process_name = "False"
        # handle setting send_notification in overrides
        self.restriction_send_notification = self.env.get(
            "restriction_send_notification"
        )
        if not self.restriction_send_notification:
            self.restriction_send_notification = "false"
        # handle setting kill_process in overrides
        self.kill_process = self.env.get("kill_process")
        if not self.kill_process:
            self.kill_process = "false"
        # handle setting delete_executable in overrides
        self.delete_executable = self.env.get("delete_executable")
        if not self.delete_executable:
            self.delete_executable = "false"
        self.restriction_computergroup = self.env.get("restriction_computergroup")
        self.replace = self.env.get("replace_restriction")
        # handle setting replace in overrides
        if not self.replace or self.replace == "False":
            self.replace = False

        # clear any pre-existing summary result
        if "jamfsoftwarerestrictionuploader_summary_result" in self.env:
            del self.env["jamfsoftwarerestrictionuploader_summary_result"]

        restriction_updated = False

        # handle files with no path
        if self.template and "/" not in self.template:
            found_template = self.get_path_to_file(self.template)
            if found_template:
                self.template = found_template
            else:
                raise ProcessorError(
                    f"ERROR: XML template file {self.template} not found"
                )

        # exit if essential values are not supplied
        if not self.restriction_name:
            raise ProcessorError(
                "ERROR: No software restriction name supplied - cannot import"
            )

        # import restriction template
        with open(self.template, "r") as file:
            template_contents = file.read()

        # check for existing Software Restriction
        self.output(
            f"Checking for existing '{self.restriction_name}' on {self.jamf_url}"
        )

        # check for existing token
        self.output("Checking for existing authentication token", verbose_level=2)
        token = self.check_api_token()

        # if no valid token, get one
        if not token:
            enc_creds = self.get_enc_creds(self.jamf_user, self.jamf_password)
            self.output("Getting an authentication token", verbose_level=2)
            token = self.get_api_token(self.jamf_url, enc_creds)

        # if token, verify Jamf Pro version
        if token:
            can_use_token = self.validate_jamf_pro_version(self.jamf_url, token)
            if can_use_token:
                self.output("Token auth will be used, ", verbose_level=2)
                send_creds = ""
            else:
                self.output("Basic auth will be used, ", verbose_level=2)
                send_creds = enc_creds
        else:
            can_use_token = False
            self.output("No token found, basic auth will be used, ", verbose_level=2)
            send_creds = enc_creds

        obj_type = "restricted_software"
        obj_id = self.get_api_obj_id_from_name(
            self.jamf_url,
            self.restriction_name,
            obj_type,
            enc_creds=send_creds,
            token=token,
        )
        if obj_id:
            self.output(
                f"Software Restriction '{self.restriction_name}' already exists: ID {obj_id}"
            )
            if self.replace:
                self.upload_restriction(
                    self.jamf_url,
                    self.restriction_name,
                    self.process_name,
                    self.display_message,
                    self.match_exact_process_name,
                    self.restriction_send_notification,
                    self.kill_process,
                    self.delete_executable,
                    self.restriction_computergroup,
                    template_contents,
                    obj_id=obj_id,
                    enc_creds=send_creds,
                    token=token,
                )
                restriction_updated = True
            else:
                self.output(
                    "Not replacing existing Software Restriction. "
                    "Override the replace_restriction key to True to enforce."
                )
        else:
            self.output(
                f"Software Restriction '{self.restriction_name}' not found - will create"
            )
            # now upload the mobileconfig by generating an XML template
            self.upload_restriction(
                self.jamf_url,
                self.restriction_name,
                self.process_name,
                self.display_message,
                self.match_exact_process_name,
                self.restriction_send_notification,
                self.kill_process,
                self.delete_executable,
                self.restriction_computergroup,
                template_contents,
                enc_creds=send_creds,
                token=token,
            )
            restriction_updated = True

        # output the summary
        self.env["restriction_name"] = self.restriction_name
        self.env["restriction_updated"] = restriction_updated
        if restriction_updated:
            self.env["jamfsoftwarerestrictionuploader_summary_result"] = {
                "summary_text": (
                    "The following software restrictions were uploaded to "
                    "or updated in Jamf Pro:"
                ),
                "report_fields": ["restriction_name"],
                "data": {
                    "mobileconfig_name": self.restriction_name,
                },
            }


if __name__ == "__main__":
    PROCESSOR = JamfSoftwareRestrictionUploader()
    PROCESSOR.execute_shell()
