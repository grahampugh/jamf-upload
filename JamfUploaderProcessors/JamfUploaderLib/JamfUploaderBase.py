#!/usr/local/autopkg/python

"""
JamfUploaderBase - used only as a template for copying into the JamfUploader processors
    by G Pugh
"""

import json
import os
import re
import subprocess
import tempfile
import xml.etree.cElementTree as ET

from base64 import b64encode
from collections import namedtuple
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from shutil import rmtree
from urllib.parse import quote
from xml.sax.saxutils import escape

# from time import sleep

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
            "account": "JSSResource/accounts",
            "category": "uapi/v1/categories",
            "extension_attribute": "JSSResource/computerextensionattributes",
            "computer_group": "JSSResource/computergroups",
            "dock_item": "JSSResource/dockitems",
            "failover": "api/v1/sso/failover",
            "icon": "api/v1/icon",
            "jamf_pro_version": "api/v1/jamf-pro-version",
            "logflush": "JSSResource/logflush",
            "ldap_server": "JSSResource/ldapservers",
            "mac_application": "JSSResource/macapplications",
            "package": "JSSResource/packages",
            "package_upload": "dbfileupload",
            "patch_policy": "JSSResource/patchpolicies",
            "patch_software_title": "JSSResource/patchsoftwaretitles",
            "os_x_configuration_profile": "JSSResource/osxconfigurationprofiles",
            "policy": "JSSResource/policies",
            "policy_icon": "JSSResource/fileuploads/policies",
            "restricted_software": "JSSResource/restrictedsoftware",
            "script": "uapi/v1/scripts",
            "token": "api/v1/auth/token",
            "volume_purchasing_locations": "api/v1/volume-purchasing-locations",
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
            "account": "accounts",
            "computer_group": "computer_groups",
            "dock_item": "dock_items",
            "extension_attribute": "computer_extension_attributes",
            "ldap_server": "ldap_servers",
            "mac_application": "mac_applications",
            "os_x_configuration_profile": "os_x_configuration_profiles",
            "package": "packages",
            "patch_policy": "patch_policies",
            "patch_software_title": "patch_software_titles",
            "policy": "policies",
            "restricted_software": "restricted_software",
            "script": "scripts",
        }
        return object_list_types[object_type]

    def write_json_file(self, data):
        """dump some json to a temporary file"""
        tf = self.init_temp_file(suffix=".json")
        with open(tf, "w") as fp:
            json.dump(data, fp)
        return tf

    def write_token_to_json_file(self, url, data):
        """dump the token, expiry, url and user as json to a temporary token file"""
        data["url"] = url
        data["user"] = self.jamf_user
        if not self.env.get("jamfupload_token"):
            self.env["jamfupload_token"] = self.init_temp_file(
                prefix="jamf_upload_token_"
            )
        with open(self.env["jamfupload_token"], "w") as fp:
            json.dump(data, fp)

    def write_xml_file(self, data):
        """dump some xml to a temporary file"""
        xml_tree = ET.ElementTree(data)
        tf = self.init_temp_file(suffix=".xml")
        xml_tree.write(tf)
        return tf

    def write_temp_file(self, data):
        """dump some text to a temporary file"""
        tf = self.init_temp_file(suffix=".txt")
        with open(tf, "w") as fp:
            fp.write(data)
        return tf

    def make_tmp_dir(self, tmp_dir="/tmp/jamf_upload_"):
        """make the tmp directory"""
        if not self.env.get("jamfupload_tmp_dir"):
            base_dir, dir = tmp_dir.rsplit("/", 1)
            self.env["jamfupload_tmp_dir"] = tempfile.mkdtemp(prefix=dir, dir=base_dir)
        return self.env["jamfupload_tmp_dir"]

    def init_temp_file(self, prefix="jamf_upload_", suffix=None, dir=None, text=True):
        """dump some text to a temporary file"""
        return tempfile.mkstemp(
            prefix=prefix,
            suffix=suffix,
            dir=self.make_tmp_dir() if dir is None else dir,
            text=text,
        )[1]

    def get_enc_creds(self, user, password):
        """encode the username and password into a b64-encoded string"""
        credentials = f"{user}:{password}"
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
                    if data["url"] == url and data["user"] == self.jamf_user:
                        self.output(
                            "URL and user for token matches current request",
                            verbose_level=2,
                        )
                        if data["token"]:
                            try:
                                # check if it's expired or not
                                # this may not always work due to inconsistent
                                # ISO 8601 time format in the expiry token,
                                # so we look for a ValueError
                                expires = datetime.strptime(
                                    data["expires"], "%Y-%m-%dT%H:%M:%S.%fZ"
                                )
                                if expires > datetime.utcnow():
                                    self.output("Existing token is valid")
                                    return data["token"]
                            except ValueError:
                                self.output(
                                    "Token expiry could not be parsed", verbose_level=2
                                )
                        else:
                            self.output("Token not found in file", verbose_level=2)
                    else:
                        self.output(
                            "URL or user do not match current token request",
                            verbose_level=2,
                        )
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
                self.output("Token auth will be used", verbose_level=2)
                send_creds = ""
            else:
                self.output("Basic auth will be used", verbose_level=2)
                send_creds = enc_creds
        else:
            self.output("No token found, basic auth will be used", verbose_level=2)
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
        self,
        request="",
        url="",
        token="",
        enc_creds="",
        data="",
        additional_headers="",
        force_xml=False,
    ):
        """
        Build a curl command based on request type (GET, POST, PUT, PATCH, DELETE).

        This function handles 6 different APIs:
        1. The Jamf Pro Classic API. These endpoints are under the 'JSSResource' URL.
        2. The Jamf Pro API. These endpoints are under the 'api'/'uapi' URL.
        3. The Jamf Pro dbfileupload endpoint, for uploading packages (v1).
        4. The Jamf Pro legacy/packages endpoint, for uploading packages (v3).
        5. Slack webhooks.
        6. Microsoft Teams webhooks.

        For the Jamf Pro API and Classic API, basic authentication is used to obtain a
        bearer token, which we write to a file along with its expiry datetime.
        Subsequent requests to the same URL use the bearer token until it expires.
        Jamf Pro versions older than 10.35 use basic auth for all Classic API requests.
        The dbfileupload endpoint also uses basic auth.
        The legacy/packages endpoint uses a session ID and separate authentication token.
        This is generated by the JamfPackageUploader processor.
        Authentication for the webhooks is achieved with a preconfigured token.
        """
        tmp_dir = self.make_tmp_dir()
        headers_file = os.path.join(tmp_dir, "curl_headers_from_jamf_upload.txt")
        output_file = self.init_temp_file(prefix="jamf_upload_", suffix=".txt")
        cookie_jar = os.path.join(tmp_dir, "curl_cookies_from_jamf_upload.txt")

        # build the curl command
        if url:
            curl_cmd = [
                "/usr/bin/curl",
                "--dump-header",
                headers_file,
                url,
            ]
        else:
            raise ProcessorError("No URL supplied")

        if request:
            curl_cmd.extend(["--request", request])

        if "legacy/packages" not in url and "api/file/v2" not in url:
            curl_cmd.extend(["--silent", "--show-error"])

        # Jamf Pro API authentication
        if enc_creds:
            curl_cmd.extend(["--header", f"authorization: Basic {enc_creds}"])
        elif token:
            curl_cmd.extend(["--header", f"authorization: Bearer {token}"])

        # icon download
        if request == "GET" and "ics.services.jamfcloud.com" in url:
            output_file = os.path.join(tmp_dir, "icon_download.png")

        # 'Accept' for GET and DELETE requests
        # By default, we obtain json as its easier to parse. However,
        # some endpoints (For example the 'patchsoftwaretitle' endpoint)
        # do not return complete json, so we have to get the xml instead.
        elif request == "GET" or request == "DELETE":
            if "legacy/packages" not in url:
                if force_xml:
                    curl_cmd.extend(["--header", "Accept: application/xml"])
                else:
                    curl_cmd.extend(["--header", "Accept: application/json"])

        # icon upload (Classic API) requires special method
        elif request == "POST" and self.api_endpoints("policy_icon") in url:
            curl_cmd.extend(["--header", "Content-type: multipart/form-data"])
            curl_cmd.extend(["--form", f"name=@{data}"])

        # icon upload (Jamf Pro API) requires special method
        elif request == "POST" and self.api_endpoints("icon") in url:
            curl_cmd.extend(["--header", "Content-type: multipart/form-data"])
            curl_cmd.extend(["--form", f"file=@{data};type=image/png"])

        # Content-Type for POST/PUT
        elif request == "POST" or request == "PUT":
            if data and "slack" in url or "webhook.office" in url:
                # slack and teams require a data argument
                curl_cmd.extend(["--data", data])
                curl_cmd.extend(["--header", "Content-type: application/json"])
            elif data:
                # jamf data upload requires upload-file argument
                curl_cmd.extend(["--upload-file", data])

            if "JSSResource" in url:
                # Jamf Pro API and Slack posts json, but Classic API posts xml
                curl_cmd.extend(["--header", "Content-type: application/xml"])
            elif ("/api/" in url or "/uapi/" in url) and "/file/v2/" not in url:
                curl_cmd.extend(["--header", "Content-type: application/json"])
            # note: other endpoints should supply their headers via 'additional_headers'
        elif request != "GET" and request != "DELETE":
            self.output(f"WARNING: HTTP method {request} not supported")

        self.output(f"Output file is:  {output_file}", verbose_level=3)
        curl_cmd.extend(["--output", output_file])

        # write session for jamf requests
        if (
            "/api/" in url
            or "/uapi/" in url
            or "JSSResource" in url
            or self.api_endpoints("package_upload") in url
            or "legacy/packages" in url
        ):
            curl_cmd.extend(["--cookie-jar", cookie_jar])

            # look for existing session
            if os.path.exists(cookie_jar):
                curl_cmd.extend(["--cookie", cookie_jar])
            else:
                self.output(
                    "No existing cookie found - starting new session", verbose_level=2
                )

        # allow use of a self-signed certificate

        # insecure mode
        if self.env.get("insecure_mode"):
            curl_cmd.insert(1, "--insecure")
        # additional headers for advanced requests
        if additional_headers:
            curl_cmd.extend(additional_headers)
        # add additional flags specified
        if self.env.get("custom_curl_opts"):
            curl_cmd.extend(self.env.get("custom_curl_opts"))

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
            if "ics.services.jamfcloud.com" in url:
                r.output = output_file
            else:
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
        elif request == "GET":
            action = "download"

        if r.status_code == 200 or r.status_code == 201:
            self.output(f"{endpoint_type} '{obj_name}' {action} successful")
            return "break"
        else:
            parser = self.ParseHTMLForError()
            parser.feed(r.output.decode())
            if parser.error:
                self.output(f"API {parser.error}", verbose_level=2)
            self.output(f"API response:\n{r.output}", verbose_level=3)
            if r.status_code == 409:
                raise ProcessorError(
                    f"WARNING: {endpoint_type} '{obj_name}' {action} failed due to the following "
                    f"conflict: {parser.error.replace('Error: ', '')}"
                )
            elif r.status_code == 400:
                raise ProcessorError(
                    f"WARNING: {endpoint_type} '{obj_name}' {action} failed due to the following "
                    f"{parser.data[6]}: {parser.data[8]}"
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
                self.output(
                    f"UNKNOWN ERROR: {endpoint_type} '{obj_name}' {action} failed. "
                    "Will try again."
                )

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
            except KeyError as error:
                self.output(f"ERROR: No version of Jamf Pro received.  Error:\n{error}")
                raise ProcessorError("No version of Jamf Pro received") from error

    def validate_jamf_pro_version(self, jamf_url, token):
        """return true if Jamf Pro version is 10.35 or greater"""
        jamf_pro_version = self.get_jamf_pro_version(jamf_url, token)
        try:
            if APLooseVersion(jamf_pro_version) >= APLooseVersion("10.35.0"):
                return True
            else:
                return False
        except AttributeError as error:
            self.output(
                f"ERROR: Unable to determine version of Jamf Pro.  Error:\n{error}"
            )
            raise ProcessorError("Unable to determine version of Jamf Pro") from error

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
        elif r.status_code == 401:
            raise ProcessorError(
                "ERROR: Jamf returned status code '401' - Access denied."
            )

    def substitute_assignable_keys(self, data, xml_escape=False):
        """substitutes any key in the inputted text using the %MY_KEY% nomenclature"""
        # if JSS_INVENTORY_NAME is not given, make it equivalent to %NAME%.app
        # (this is to allow use of legacy JSSImporter group templates)
        try:
            self.env["JSS_INVENTORY_NAME"]
        except KeyError:
            try:
                self.env["JSS_INVENTORY_NAME"] = self.env["NAME"] + ".app"
            except KeyError:
                pass

        # do a four-pass to ensure that all keys are substituted
        loop = 5
        while loop > 0:
            loop = loop - 1
            found_keys = re.findall(r"\%\w+\%", data)
            if not found_keys:
                break
            found_keys = [i.replace("%", "") for i in found_keys]
            for found_key in found_keys:
                if self.env.get(found_key) is not None:
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
                    raise ProcessorError(
                        f"Unsubstitutable key in template found: '{found_key}'"
                    )
        return data

    def substitute_limited_assignable_keys(
        self, data, cli_custom_keys, xml_escape=False
    ):
        """substitutes any key in the inputted text using the %MY_KEY% nomenclature, limited to
        an assigned set of replacement keys. This can be used in advance of using
        substitute_assignable_keys, to ensure that a specific set of keys are substituted in the
        right order.
        Whenever %MY_KEY% is found in the provided data, it is replaced with the assigned
        value of MY_KEY. A five-times pass-through is done to ensure that all keys are substituted.

        Optionally, if the xml_escape key is set, the value is escaped for XML special characters.
        This is designed primarily to account for ampersands in the substituted strings.
        """
        loop = 5
        while loop > 0:
            loop = loop - 1
            found_keys = re.findall(r"\%\w+\%", data)
            if not found_keys:
                break
            found_keys = [i.replace("%", "") for i in found_keys]
            for found_key in found_keys:
                if cli_custom_keys.get(found_key):
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
        return data

    def get_path_to_file(self, filename):
        """Find a file in a recipe without requiring a path. Looks in the following places
        in the following order:
        1. RecipeOverrides directory/ies
        2. Same directory as the recipe
        3. Same repo (recipe search directory) as the recipe
        4. Parent recipe's repo (recipe search directory) if recipe is an override
        Relative paths also work."""
        recipe_dir = self.env.get("RECIPE_DIR")
        recipe_dir_path = Path(os.path.expanduser(recipe_dir))
        filepath = os.path.join(recipe_dir, filename)
        matched_override_dir = ""

        # first, look in the overrides directory
        if self.env.get("RECIPE_OVERRIDE_DIRS"):
            matched_filepath = ""
            for d in self.env["RECIPE_OVERRIDE_DIRS"]:
                override_dir_path = Path(os.path.expanduser(d))
                if (
                    override_dir_path == recipe_dir_path
                    or override_dir_path in recipe_dir_path.parents
                ):
                    self.output(f"Matching dir: {override_dir_path}", verbose_level=3)
                    matched_override_dir = override_dir_path
                for path in Path(os.path.expanduser(d)).rglob(filename):
                    matched_filepath = str(path)
                    break
            if matched_filepath:
                self.output(f"File found at: {matched_filepath}")
                return matched_filepath

        # second, look in the same directory as the recipe
        self.output(f"Looking for {filename} in {recipe_dir}", verbose_level=3)
        if os.path.exists(filepath):
            self.output(f"File found at: {filepath}")
            return filepath

        # third, try to match the recipe's dir with one of the recipe search dirs
        if self.env.get("RECIPE_SEARCH_DIRS"):
            matched_filepath = ""
            for d in self.env["RECIPE_SEARCH_DIRS"]:
                search_dir_path = Path(os.path.expanduser(d))
                if (
                    search_dir_path == recipe_dir_path
                    or search_dir_path in recipe_dir_path.parents
                ):
                    # matching search dir, look for file in here
                    self.output(f"Matching dir: {search_dir_path}", verbose_level=3)
                    for path in Path(os.path.expanduser(d)).rglob(filename):
                        matched_filepath = str(path)
                        break
                if matched_filepath:
                    self.output(f"File found at: {matched_filepath}")
                    return matched_filepath

        # fourth, look in the parent recipe's directory if we are an override
        if matched_override_dir:
            if self.env.get("PARENT_RECIPES"):
                matched_filepath = ""
                parent = self.env["PARENT_RECIPES"][0]
                self.output(f"Parent Recipe: {parent}", verbose_level=2)
                parent_dir = os.path.dirname(parent)
                # grab the root of this repo
                parent_dir_path = Path(os.path.expanduser(parent_dir))
                for d in self.env["RECIPE_SEARCH_DIRS"]:
                    search_dir_path = Path(os.path.expanduser(d))
                    if (
                        search_dir_path == parent_dir_path
                        or search_dir_path in parent_dir_path.parents
                    ):
                        # matching parent dir, look for file in here
                        self.output(f"Matching dir: {search_dir_path}", verbose_level=3)
                        for path in Path(os.path.expanduser(d)).rglob(filename):
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

    def pretty_print_xml(self, xml):
        proc = subprocess.Popen(
            ["xmllint", "--format", "/dev/stdin"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        (output, _) = proc.communicate(xml)
        return output

    class ParseHTMLForError(HTMLParser):
        def __init__(self):
            HTMLParser.__init__(self)
            self.error = None
            self.data = []

        def handle_data(self, data):
            self.data.append(data)
            if "Error:" in data:
                self.error = data


if __name__ == "__main__":
    PROCESSOR = JamfUploaderBase()
    PROCESSOR.execute_shell()
