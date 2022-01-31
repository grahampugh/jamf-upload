#!/usr/local/autopkg/python

"""
JamfUploaderBase - used only as a template for copying into the JamfUploader processors
    by G Pugh
"""

import json
import os
import re
import subprocess
import uuid
import xml.etree.cElementTree as ET

from base64 import b64encode
from collections import namedtuple
from datetime import datetime
from pathlib import Path
from shutil import rmtree
from urllib.parse import quote
from xml.sax.saxutils import escape

# from base64 import b64encode
# from time import sleep
# from urllib.parse import quote

from autopkglib import (
    APLooseVersion,
    Processor,
    ProcessorError,
)  # pylint: disable=import-error


class JamfUploaderBase(Processor):
    """A processor for AutoPkg that will upload a category to a Jamf Cloud or on-prem server."""

    def api_endpoints(self, object_type):
        """Return the endpoint URL from the object type"""
        api_endpoints = {
            "category": "uapi/v1/categories",
            "extension_attribute": "JSSResource/computerextensionattributes",
            "computer_group": "JSSResource/computergroups",
            "dock_item": "JSSResource/dockitems",
            "jamf_pro_version": "api/v1/jamf-pro-version",
            "package": "JSSResource/packages",
            "package_upload": "dbfileupload",
            "os_x_configuration_profile": "JSSResource/osxconfigurationprofiles",
            "policy": "JSSResource/policies",
            "policy_icon": "JSSResource/fileuploads/policies",
            "restricted_software": "JSSResource/restrictedsoftware",
            "script": "uapi/v1/scripts",
            "token": "api/v1/auth/token",
        }
        return api_endpoints[object_type]

    def object_types(self, object_type):
        """Return a URL object type from the object type"""
        object_types = {
            "package": "packages",
            "computer_group": "computergroups",
            "dock_item": "dockitems",
            "policy": "policies",
            "extension_attribute": "computerextensionattributes",
            "restricted_software": "restrictedsoftware",
            "os_x_configuration_profile": "osxconfigurationprofiles",
        }
        return object_types[object_type]

    def object_list_types(self, object_type):
        """Return a XML dictionary type from the object type"""
        object_list_types = {
            "computer_group": "computer_groups",
            "dock_item": "dock_items",
            "extension_attribute": "computer_extension_attributes",
            "os_x_configuration_profile": "os_x_configuration_profiles",
            "package": "packages",
            "policy": "policies",
            "restricted_software": "restricted_software",
            "script": "scripts",
        }
        return object_list_types[object_type]

    def write_json_file(self, data, tmp_dir="/tmp/jamf_upload"):
        """dump some json to a temporary file"""
        self.make_tmp_dir(tmp_dir)
        tf = os.path.join(tmp_dir, f"jamf_upload_{str(uuid.uuid4())}.json")
        with open(tf, "w") as fp:
            json.dump(data, fp)
        return tf

    def write_token_to_json_file(self, url, data, token_file="/tmp/jamf_upload_token"):
        """dump the token and expiry as json to a temporary file"""
        data["url"] = url
        with open(token_file, "w") as fp:
            json.dump(data, fp)

    def write_xml_file(self, data, tmp_dir="/tmp/jamf_upload"):
        """dump some xml to a temporary file"""
        self.make_tmp_dir(tmp_dir)
        xml_tree = ET.ElementTree(data)
        tf = os.path.join(tmp_dir, f"jamf_upload_{str(uuid.uuid4())}.xml")
        xml_tree.write(tf)
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

    def get_enc_creds(self, user, password):
        """encode the username and password into a b64-encoded string"""
        credentials = f"{self.jamf_user}:{self.jamf_password}"
        enc_creds_bytes = b64encode(credentials.encode("utf-8"))
        enc_creds = str(enc_creds_bytes, "utf-8")
        return enc_creds

    def check_api_token(self, url, token_file="/tmp/jamf_upload_token"):
        """Check validity of an existing token"""
        if os.path.exists(token_file):
            with open(token_file, "rb") as file:
                data = json.load(file)
                # check that there is a 'token' key
                try:
                    self.output(
                        f"Checking {data['url']} against {url}", verbose_level=2
                    )
                    if data["url"] == url:
                        self.output(
                            "URL for token matches current request", verbose_level=2
                        )
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
                except KeyError:
                    pass
        self.output("No existing valid token found", verbose_level=2)

    def get_api_token(self, jamf_url, enc_creds):
        """get a token for the Jamf Pro API or Classic API for Jamf Pro 10.35+"""
        url = jamf_url + "/" + self.api_endpoints("token")
        r = self.curl(request="POST", url=url, enc_creds=enc_creds)
        output = r.output
        if r.status_code == 200:
            try:
                token = str(output["token"])
                expires = str(output["expires"])

                # write the data to a file
                self.write_token_to_json_file(jamf_url, output)
                self.output("Session token received")
                self.output(f"Token: {token}", verbose_level=2)
                self.output(f"Expires: {expires}", verbose_level=2)
                return token
            except KeyError:
                self.output("ERROR: No token received")
        else:
            self.output("ERROR: No token received")

    def handle_classic_auth(self, url, user, password):
        """figure out which auth to use"""
        # check for existing token
        self.output("Checking for existing authentication token", verbose_level=2)
        token = self.check_api_token(url)

        enc_creds = self.get_enc_creds(user, password)

        # if no valid token, get one
        if not token:
            self.output("Getting an authentication token", verbose_level=2)
            token = self.get_api_token(url, enc_creds)

        # if token, verify Jamf Pro version
        if token:
            if self.validate_jamf_pro_version(url, token):
                self.output("Token auth will be used, ", verbose_level=2)
                send_creds = ""
            else:
                self.output("Basic auth will be used, ", verbose_level=2)
                send_creds = enc_creds
        else:
            self.output("No token found, basic auth will be used, ", verbose_level=2)
            send_creds = enc_creds

        # return token and classic creds
        return token, send_creds, enc_creds

    def handle_uapi_auth(self, url, user, password):
        """obtain token"""
        # check for existing token
        self.output("Checking for existing authentication token", verbose_level=2)
        token = self.check_api_token(url)

        # if no valid token, get one
        if not token:
            enc_creds = self.get_enc_creds(user, password)
            self.output("Getting an authentication token", verbose_level=2)
            token = self.get_api_token(url, enc_creds)

        if not token:
            raise ProcessorError("No token found, cannot continue")

        # return token and classic creds
        return token

    def clear_tmp_dir(self, tmp_dir="/tmp/jamf_upload"):
        """remove the tmp directory"""
        if os.path.exists(tmp_dir):
            rmtree(tmp_dir)
        return tmp_dir

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

        # Accept for GET requests
        if request == "GET" or request == "DELETE":
            curl_cmd.extend(["--header", "Accept: application/json"])

        # icon upload requires special method
        elif request == "POST" and "fileuploads" in url:
            curl_cmd.extend(["--header", "Content-type: multipart/form-data"])
            curl_cmd.extend(["--form", f"name=@{data}"])

        # Content-Type for POST/PUT
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
            elif "dbfileupload" in url:
                curl_cmd.extend(["--header", "Accept: application/xml"])
            else:
                curl_cmd.extend(["--header", "Content-type: application/json"])
        else:
            self.output(f"WARNING: HTTP method {request} not supported")

        # write session for jamf requests
        if (
            "/api/" in url
            or "/uapi/" in url
            or "JSSResource" in url
            or "dbfileupload" in url
        ):
            try:
                with open(headers_file, "r") as file:
                    headers = file.readlines()
                existing_headers = [x.strip() for x in headers]
                for header in existing_headers:
                    if "APBALANCEID" in header:
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
                    if "APBALANCEID" in header:
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
                if "/api/" in url or "/uapi/" in url:
                    r.output = json.load(file)
                else:
                    r.output = file.read()
        else:
            self.output(f"No output from request ({output_file} not found or empty)")
        return r()

    def status_check(self, r, endpoint_type, obj_name, request):
        """Return a message dependent on the HTTP response"""
        if request == "DELETE":
            action = "deletion"
        elif request == "PUT":
            action = "update"
        elif request == "POST":
            action = "upload"

        if r.status_code == 200 or r.status_code == 201:
            self.output(f"{endpoint_type} '{obj_name}' {action} successful")
            return "break"
        elif r.status_code == 409:
            self.output(r.output, verbose_level=2)
            raise ProcessorError(
                f"WARNING: {endpoint_type} '{obj_name}' {action} failed due to a conflict"
            )
        elif r.status_code == 401:
            raise ProcessorError(
                f"ERROR: {endpoint_type} '{obj_name}' {action} failed due to permissions error"
            )
        elif r.status_code == 405:
            raise ProcessorError(
                f"ERROR: {endpoint_type} '{obj_name}' {action} failed due to a "
                "'method not allowed' error"
            )
        elif r.status_code == 500:
            raise ProcessorError(
                f"ERROR: {endpoint_type} '{obj_name}' {action} failed due to an "
                "internal server error"
            )
        else:
            self.output(f"WARNING: {endpoint_type} '{obj_name}' {action} failed")
            self.output(r.output, verbose_level=2)

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

    def validate_jamf_pro_version(self, jamf_url, token):
        """return true if Jamf Pro version is 10.35 or greater"""
        jamf_pro_version = self.get_jamf_pro_version(jamf_url, token)
        if APLooseVersion(jamf_pro_version) >= APLooseVersion("10.35.0"):
            return True
        else:
            return False

    def get_uapi_obj_id_from_name(self, jamf_url, object_type, object_name, token):
        """Get the Jamf Pro API object by name. This requires use of RSQL filtering"""
        url_filter = f"?page=0&page-size=1000&sort=id&filter=name%3D%3D%22{quote(object_name)}%22"
        url = jamf_url + "/" + self.api_endpoints(object_type) + url_filter
        r = self.curl(request="GET", url=url, token=token)
        if r.status_code == 200:
            obj_id = 0
            # output = json.loads(r.output)
            output = r.output
            for obj in output["results"]:
                self.output(f"ID: {obj['id']} NAME: {obj['name']}", verbose_level=3)
                if obj["name"] == object_name:
                    obj_id = obj["id"]
            return obj_id

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
                    verbose_level=4,
                )
                # we need to check for a case-insensitive match
                if obj["name"].lower() == object_name.lower():
                    obj_id = obj["id"]
            return obj_id

    def substitute_assignable_keys(self, data, xml_escape=False):
        """substitutes any key in the inputted text using the %MY_KEY% nomenclature"""
        # do a four-pass to ensure that all keys are substituted
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

    def get_api_obj_value_from_id(
        self, jamf_url, object_type, obj_id, obj_path, enc_creds="", token=""
    ):
        """get the value of an item in a Classic API object"""
        # define the relationship between the object types and their URL
        # we could make this shorter with some regex but I think this way is clearer
        url = "{}/{}/id/{}".format(jamf_url, self.api_endpoints(object_type), obj_id)
        request = "GET"
        r = self.curl(request=request, url=url, enc_creds=enc_creds, token=token)
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


if __name__ == "__main__":
    PROCESSOR = JamfUploaderBase()
    PROCESSOR.execute_shell()
