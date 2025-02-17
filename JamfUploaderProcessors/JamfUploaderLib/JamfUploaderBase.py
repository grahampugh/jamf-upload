#!/usr/local/autopkg/python
# pylint: disable=invalid-name, too-many-lines

"""
Copyright 2023 Graham Pugh

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import json
import os
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET

from base64 import b64encode
from collections import abc, namedtuple
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from shutil import rmtree
from urllib.parse import quote, urlparse
from xml.sax.saxutils import escape

from autopkglib import (  # pylint: disable=import-error
    Processor,
    ProcessorError,
)


class JamfUploaderBase(Processor):
    """Common functions used by at least two JamfUploader processors."""

    # Global version
    __version__ = "2025.2.17.0"

    def api_endpoints(self, object_type):
        """Return the endpoint URL from the object type"""
        api_endpoints = {
            "account": "JSSResource/accounts",
            "api_client": "api/v1/api-integrations",
            "api_role": "api/v1/api-roles",
            "category": "api/v1/categories",
            "computer_extension_attribute": "api/v1/computer-extension-attributes",
            "computer_extension_attribute_classic": "JSSResource/computerextensionattributes",
            "computer_group": "JSSResource/computergroups",
            "computer_prestage": "api/v3/computer-prestages",
            "configuration_profile": "JSSResource/mobiledeviceconfigurationprofiles",
            "dock_item": "JSSResource/dockitems",
            "failover": "api/v1/sso/failover",
            "icon": "api/v1/icon",
            "jamf_pro_version": "api/v1/jamf-pro-version",
            "jcds": "api/v1/jcds",
            "logflush": "JSSResource/logflush",
            "ldap_server": "JSSResource/ldapservers",
            "mac_application": "JSSResource/macapplications",
            "mobile_device_application": "JSSResource/mobiledeviceapplications",
            "mobile_device_group": "JSSResource/mobiledevicegroups",
            "mobile_device_prestage": "api/v1/mobile-device-prestages",
            "package": "JSSResource/packages",
            "package_v1": "api/v1/packages",
            "package_upload": "dbfileupload",
            "patch_policy": "JSSResource/patchpolicies",
            "patch_software_title": "JSSResource/patchsoftwaretitles",
            "oauth": "api/oauth/token",
            "os_x_configuration_profile": "JSSResource/osxconfigurationprofiles",
            "policy": "JSSResource/policies",
            "policy_icon": "JSSResource/fileuploads/policies",
            "restricted_software": "JSSResource/restrictedsoftware",
            "script": "api/v1/scripts",
            "token": "api/v1/auth/token",
            "volume_purchasing_location": "api/v1/volume-purchasing-locations",
        }
        return api_endpoints[object_type]

    def object_types(self, object_type):
        """Return a URL object type from the object type"""
        object_types = {
            "package": "packages",
            "computer_group": "computergroups",
            "configuration_profile": "mobiledeviceconfigurationprofiles",
            "dock_item": "dockitems",
            "mobile_device_group": "mobiledevicegroups",
            "policy": "policies",
            "computer_extension_attribute": "computerextensionattributes",
            "restricted_software": "restrictedsoftware",
            "os_x_configuration_profile": "osxconfigurationprofiles",
        }
        return object_types[object_type]

    def object_list_types(self, object_type):
        """Return a XML dictionary type from the object type"""
        object_list_types = {
            "account": "accounts",
            "api_client": "api_clients",
            "api_role": "api_roles",
            "category": "categories",
            "computer_group": "computer_groups",
            "computer_prestage": "computer_prestages",
            "configuration_profile": "configuration_profiles",
            "dock_item": "dock_items",
            "computer_extension_attribute": "computer_extension_attributes",
            "ldap_server": "ldap_servers",
            "mac_application": "mac_applications",
            "mobile_device_application": "mobile_device_applications",
            "mobile_device_group": "mobile_device_groups",
            "mobile_device_prestage": "mobile_device_prestages",
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
        with open(tf, "w", encoding="utf-8") as fp:
            json.dump(data, fp)
        return tf

    def write_token_to_json_file(self, url, jamf_user, data):
        """dump the token, expiry, url and user as json to a temporary token file"""
        data["url"] = url
        data["user"] = jamf_user
        if not self.env.get("jamfupload_token_file"):
            self.env["jamfupload_token_file"] = self.init_temp_file(
                prefix="jamf_upload_token_"
            )
        with open(self.env["jamfupload_token_file"], "w", encoding="utf-8") as fp:
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
        with open(tf, "w", encoding="utf-8") as fp:
            fp.write(data)
        return tf

    def make_tmp_dir(self, tmp_dir="/tmp/jamf_upload_"):
        """make the tmp directory"""
        if not self.env.get("jamfupload_tmp_dir"):
            base_dir, dir_name = tmp_dir.rsplit("/", 1)
            self.env["jamfupload_tmp_dir"] = tempfile.mkdtemp(
                prefix=dir_name, dir=base_dir
            )
        return self.env["jamfupload_tmp_dir"]

    def init_temp_file(
        self, prefix="jamf_upload_", suffix=None, dir_name=None, text=True
    ):
        """dump some text to a temporary file"""
        return tempfile.mkstemp(
            prefix=prefix,
            suffix=suffix,
            dir=self.make_tmp_dir() if dir_name is None else dir_name,
            text=text,
        )[1]

    def get_enc_creds(self, user, password):
        """encode the username and password into a b64-encoded string"""
        credentials = f"{user}:{password}"
        enc_creds_bytes = b64encode(credentials.encode("utf-8"))
        enc_creds = str(enc_creds_bytes, "utf-8")
        return enc_creds

    def check_api_token(self, jamf_url, jamf_user):
        """Check validity of an existing token"""
        if self.env.get("jamfupload_token_file"):
            token_file = self.env["jamfupload_token_file"]
        else:
            token_file = ""
        if os.path.exists(token_file):
            with open(token_file, "rb") as file:
                data = json.load(file)
                # check that there is a 'token' key
                try:
                    self.output(
                        f"Checking {data['url']} against {jamf_url}", verbose_level=2
                    )
                    if data["url"] == jamf_url and data["user"] == jamf_user:
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
                                # expires = datetime.strptime(
                                #     data["expires"], "%Y-%m-%dT%H:%M:%S.%fZ"
                                # )
                                # if expires > datetime.now(timezone.utc):
                                #     self.output("Existing token is valid")
                                #     return data["token"]

                                expires_timestamp = datetime.strptime(
                                    data["expires"], "%Y-%m-%dT%H:%M:%S.%fZ"
                                ).timestamp()
                                if (
                                    expires_timestamp
                                    > datetime.now(timezone.utc).timestamp()
                                ):
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

    def get_api_token_from_oauth(self, jamf_url="", client_id="", client_secret=""):
        """get a token for the Jamf Pro API or Classic API using OAuth"""
        if client_id and client_secret:
            url = jamf_url + "/" + self.api_endpoints("oauth")
            additional_curl_opts = [
                "--data-urlencode",
                f"client_id={client_id}",
                "--data-urlencode",
                "grant_type=client_credentials",
                "--data-urlencode",
                f"client_secret={client_secret}",
            ]
            r = self.curl(
                request="POST",
                url=url,
                additional_curl_opts=additional_curl_opts,
                endpoint_type="oauth",
            )
            output = r.output
            if r.status_code == 200:
                try:
                    token = str(output["access_token"])
                    expires_in = output["expires_in"]
                    # convert "expires_in" value to a timestamp to match basic auth method
                    expires_timestamp = datetime.now(timezone.utc) + timedelta(
                        seconds=expires_in
                    )
                    expires_str = datetime.strptime(
                        str(expires_timestamp).removesuffix("+00:00"),
                        "%Y-%m-%d %H:%M:%S.%f",
                    )
                    expires = expires_str.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

                    # write the data to a file
                    self.write_token_to_json_file(jamf_url, client_id, output)
                    self.output("Session token received")
                    self.output(f"Token: {token}", verbose_level=2)
                    self.output(f"Expires: {expires}", verbose_level=2)
                    return token
                except KeyError:
                    self.output("ERROR: No token received")
            else:
                self.output("ERROR: No token received")
        else:
            self.output("ERROR: Insufficient credentials provided")

    def get_api_token_from_basic_auth(self, jamf_url="", jamf_user="", password=""):
        """get a token for the Jamf Pro API or Classic API using basic auth"""
        if jamf_user:
            enc_creds = self.get_enc_creds(jamf_user, password)
            url = jamf_url + "/" + self.api_endpoints("token")
            r = self.curl(
                request="POST",
                url=url,
                enc_creds=enc_creds,
            )
            output = r.output
            if r.status_code == 200:
                try:
                    token = str(output["token"])
                    expires = str(output["expires"])

                    # write the data to a file
                    self.write_token_to_json_file(jamf_url, jamf_user, output)
                    self.output("Session token received")
                    self.output(f"Token: {token}", verbose_level=2)
                    self.output(f"Expires: {expires}", verbose_level=2)
                    return token
                except KeyError:
                    self.output("ERROR: No token received")
            else:
                self.output("ERROR: No token received")
        else:
            raise ProcessorError("No credentials given, cannot continue")

    def handle_api_auth(self, jamf_url, jamf_user, password):
        """obtain token using basic auth"""
        # check for existing token
        self.output("Checking for existing authentication token", verbose_level=2)
        token = self.check_api_token(jamf_url, jamf_user)

        # if no valid token, get one
        if not token:
            self.output(
                "Getting an authentication token using Basic Auth", verbose_level=2
            )
            token = self.get_api_token_from_basic_auth(jamf_url, jamf_user, password)

        if not token:
            raise ProcessorError("No token found, cannot continue")

        # return token and classic creds
        return token

    def handle_oauth(self, jamf_url, client_id, client_secret):
        """obtain token"""
        # check for existing token using OAuth
        self.output("Checking for existing authentication token", verbose_level=2)
        token = self.check_api_token(jamf_url, client_id)

        # if no valid token, get one
        if not token:
            self.output("Getting an authentication token using OAuth", verbose_level=2)
            token = self.get_api_token_from_oauth(jamf_url, client_id, client_secret)

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
        additional_curl_opts="",
        endpoint_type="",
        accept_header="",
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

        # build the curl command based on supplied endpoint_types
        if url:
            curl_cmd = [
                "/usr/bin/curl",
                "--location",
                "--dump-header",
                headers_file,
                url,
            ]
        else:
            raise ProcessorError("No URL supplied")

        # set User-Agent
        user_agent = f"JamfUploader/{self.__version__}"
        curl_cmd.extend(["--header", f"User-Agent: {user_agent}"])

        # allow use of a self-signed certificate
        # insecure mode
        if self.env.get("insecure_mode"):
            curl_cmd.extend(["--insecure"])

        # add request type if specified
        if request:
            curl_cmd.extend(["--request", request])

        # all endpoints except the JCDS endpoint can be specified silent with show-error
        if endpoint_type != "jcds":
            curl_cmd.extend(["--silent", "--show-error"])

        # Jamf Pro API authentication headers
        if enc_creds:
            curl_cmd.extend(["--header", f"authorization: Basic {enc_creds}"])
        elif token:
            curl_cmd.extend(["--header", f"authorization: Bearer {token}"])

        # icon download
        if endpoint_type == "icon_get":
            output_file = os.path.join(tmp_dir, "icon_download.png")

        # 'Accept' for GET and DELETE requests
        # By default, we obtain json as its easier to parse. However,
        # some endpoints (For example the 'patchsoftwaretitle' endpoint)
        # do not return complete json, so we have to get the xml instead.
        elif (request == "GET" or request == "DELETE") and endpoint_type != "jcds":
            if endpoint_type == "patch_software_title" or accept_header == "xml":
                curl_cmd.extend(["--header", "Accept: application/xml"])
            else:
                curl_cmd.extend(["--header", "Accept: application/json"])
        # for uploading a package we need to return JSON
        elif request == "POST" and endpoint_type == "package":
            curl_cmd.extend(["--header", "Accept: application/json"])

        # icon upload (Jamf Pro API)
        elif endpoint_type == "package_v1":
            curl_cmd.extend(["--header", "Content-type: multipart/form-data"])
            curl_cmd.extend(["--form", f"file=@{data}"])

        # icon upload (Classic API)
        elif endpoint_type == "policy_icon":
            curl_cmd.extend(["--header", "Content-type: multipart/form-data"])
            curl_cmd.extend(["--form", f"name=@{data}"])

        # icon upload (Jamf Pro API)
        elif endpoint_type == "icon_upload":
            curl_cmd.extend(["--header", "Content-type: multipart/form-data"])
            curl_cmd.extend(["--form", f"file=@{data};type=image/png"])

        # Content-Type for POST/PUT
        elif request == "POST" or request == "PUT":
            if endpoint_type == "slack" or endpoint_type == "teams":
                # slack and teams require a data argument
                curl_cmd.extend(["--data", data])
                curl_cmd.extend(["--header", "Content-type: application/json"])
            elif data:
                # jamf data upload requires upload-file argument
                curl_cmd.extend(["--upload-file", data])

            if "JSSResource" in url:
                # Jamf Pro API and Slack posts json, but Classic API posts xml
                curl_cmd.extend(["--header", "Content-type: application/xml"])
            elif endpoint_type == "oauth":
                curl_cmd.extend(
                    ["--header", "Content-Type: application/x-www-form-urlencoded"]
                )
            elif "/api/" in url or "/uapi/" in url:
                curl_cmd.extend(["--header", "Content-type: application/json"])
            # note: other endpoints should supply their headers via 'additional_curl_opts'

        # fail other request types
        elif request != "GET" and request != "DELETE":
            self.output(f"WARNING: HTTP method {request} not supported")

        # direct output to a file
        curl_cmd.extend(["--output", output_file])
        self.output(f"Output file is:  {output_file}", verbose_level=3)

        # write session for jamf API requests
        if (
            "/api/" in url
            or "/uapi/" in url
            or "JSSResource" in url
            or endpoint_type == "package_upload"
            or endpoint_type == "jcds"
        ):
            curl_cmd.extend(["--cookie-jar", cookie_jar])

            # look for existing session
            if os.path.exists(cookie_jar):
                curl_cmd.extend(["--cookie", cookie_jar])
            else:
                self.output(
                    "No existing cookie found - starting new session", verbose_level=2
                )

        # additional headers for advanced requests
        if additional_curl_opts:
            curl_cmd.extend(additional_curl_opts)

        # add custom curl options specified
        if self.env.get("custom_curl_opts"):
            custom_curl_opts_list = self.env.get("custom_curl_opts").split()
            curl_cmd.extend(custom_curl_opts_list)

        self.output(f"curl command: {' '.join(curl_cmd)}", verbose_level=3)

        # now subprocess the curl command and build the r tuple which contains the
        # headers, status code and outputted data
        subprocess.check_output(curl_cmd)

        r = namedtuple(
            "r", ["headers", "status_code", "output"], defaults=(None, None, None)
        )
        try:
            with open(headers_file, "r", encoding="utf-8") as file:
                headers = file.readlines()
            r.headers = [x.strip() for x in headers]
            for header in r.headers:  # pylint: disable=not-an-iterable
                if re.match(r"HTTP/(1.1|2)", header) and "Continue" not in header:
                    r.status_code = int(header.split()[1])
        except IOError as exc:
            raise ProcessorError(f"WARNING: {headers_file} not found") from exc
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
        else:
            action = "unknown"

        self.output(f"HTTP response: {r.status_code}", verbose_level=2)
        if r.status_code < 400:
            if endpoint_type == "jcds":
                self.output("JCDS2 credentials successfully received", verbose_level=2)
            else:
                self.output(f"{endpoint_type} '{obj_name}' {action} successful")
            return "break"
        else:
            self.output("API response:", verbose_level=2)
            if isinstance(r.output, (bytes, bytearray)):
                self.output(r.output.decode("utf-8"), verbose_level=2)
            else:
                self.output(r.output, verbose_level=2)

            if r.status_code >= 400:
                raise ProcessorError(
                    f"ERROR: {endpoint_type} '{obj_name}' {action} failed - "
                    f"status code {r.status_code}"
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

    def get_api_obj_id_from_name(
        self, jamf_url, object_name, object_type, token, filter_name="name"
    ):
        """check if a Classic API object with the same name exists on the server"""
        # define the relationship between the object types and their URL
        if "JSSResource" in self.api_endpoints(object_type):
            # do XML stuff
            url = jamf_url + "/" + self.api_endpoints(object_type)
            r = self.curl(request="GET", url=url, token=token)

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
        else:
            # do JSON stuff
            url_filter = (
                f"?page=0&page-size=1000&sort=id&filter={filter_name}"
                f"%3D%3D%22{quote(object_name)}%22"
            )
            url = jamf_url + "/" + self.api_endpoints(object_type) + url_filter
            r = self.curl(request="GET", url=url, token=token)
            if r.status_code == 200:
                obj_id = 0
                output = r.output
                for obj in output["results"]:
                    self.output(
                        f"ID: {obj.get('id')} NAME: {obj.get(filter_name)}",
                        verbose_level=3,
                    )
                    if obj[filter_name] == object_name:
                        obj_id = obj["id"]
                        break
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
                        f"Replacing any instances of '{found_key}' with "
                        f"'{str(self.env.get(found_key))}'",
                        verbose_level=2,
                    )
                    if xml_escape and not isinstance(self.env.get(found_key), int):
                        replacement_key = escape(str(self.env.get(found_key)))
                    else:
                        replacement_key = self.env.get(found_key)
                    data = data.replace(f"%{found_key}%", str(replacement_key))
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
                    if xml_escape and not isinstance(self.env.get(found_key), int):
                        replacement_key = escape(cli_custom_keys[found_key])
                    else:
                        replacement_key = cli_custom_keys[found_key]
                    data = data.replace(f"%{found_key}%", str(replacement_key))
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

    def get_all_api_objects(self, jamf_url, object_type, token=""):
        """get a list of all objects of a particular type"""
        # Get all objects from Jamf Pro as JSON object
        self.output(f"Getting all {self.api_endpoints(object_type)} from {jamf_url}")

        # check for existing
        url = f"{jamf_url}/{self.api_endpoints(object_type)}"
        r = self.curl(request="GET", url=url, token=token)

        # for Classic API
        if "JSSResource" in url:
            object_list = json.loads(r.output)[self.object_list_types(object_type)]
            self.output(f"List of objects:\n{object_list}", verbose_level=3)

        # for Jamf Pro API
        else:
            object_list = r.output["results"]
            self.output(f"List of objects:\n{object_list}", verbose_level=3)

        return object_list

    def get_api_obj_contents_from_id(
        self, jamf_url, object_type, obj_id, obj_path="", token=""
    ):
        """get the full contents or the value of an item in a Classic or Jamf Pro API object"""
        # define the relationship between the object types and their URL
        if "JSSResource" in self.api_endpoints(object_type):
            # do XML stuff
            url = f"{jamf_url}/{self.api_endpoints(object_type)}/id/{obj_id}"
            request = "GET"
            r = self.curl(request=request, url=url, token=token, accept_header="xml")
            if r.status_code == 200:
                # Parse response as xml
                try:
                    obj_xml = ET.fromstring(r.output)
                except ET.ParseError as xml_error:
                    raise ProcessorError from xml_error
                if obj_path:
                    obj_content = obj_xml.find(obj_path)
                else:
                    ET.indent(obj_xml)
                    obj_content = ET.tostring(obj_xml, encoding="UTF-8")
                return obj_content.decode("UTF-8")
        else:
            # do JSON stuff
            url = f"{jamf_url}/{self.api_endpoints(object_type)}/{obj_id}"
            request = "GET"
            r = self.curl(request=request, url=url, token=token, accept_header="json")
            if r.status_code == 200:
                # Parse response as json
                # obj_content = json.loads(r.output)
                obj_content = r.output
                self.output(
                    obj_content,
                    verbose_level=4,
                )
                return obj_content

    def get_classic_api_obj_value_from_id(
        self, jamf_url, object_type, obj_id, obj_path, token
    ):
        """get the value of an item in a Classic API object"""
        # define the relationship between the object types and their URL
        # we could make this shorter with some regex but I think this way is clearer
        url = f"{jamf_url}/{self.api_endpoints(object_type)}/id/{obj_id}"
        request = "GET"
        r = self.curl(request=request, url=url, token=token)
        if r.status_code == 200:
            obj_content = json.loads(r.output)
            self.output(obj_content, verbose_level=4)

            # convert an xpath to json
            xpath_list = obj_path.split("/")
            value = obj_content[object_type]

            for _, xpath in enumerate(xpath_list):
                if xpath:
                    try:
                        value = value[xpath]
                        self.output(value, verbose_level=3)
                    except KeyError:
                        value = ""
                        break

            if value:
                self.output(f"Value of '{obj_path}': {value}", verbose_level=2)
            return value

    def pretty_print_xml(self, xml):
        """prettifies XML"""
        proc = subprocess.Popen(
            ["xmllint", "--format", "/dev/stdin"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        (output, _) = proc.communicate(xml)
        return output

    def get_existing_scope(self, jamf_url, obj_type, obj_id, token):
        """return the existing scope"""
        existing_scope_xml = self.get_api_obj_contents_from_id(
            jamf_url,
            obj_type,
            obj_id,
            "scope",
            token,
        )
        self.output("Existing scope:", verbose_level=2)
        self.output(existing_scope_xml, verbose_level=2)
        return existing_scope_xml

    def replace_scope(self, template_contents, existing_scope):
        """replace scope with scope from existing item"""
        self.output("Updating the scope in the template", verbose_level=2)

        # Parse response as xml
        try:
            template_contents_xml = ET.fromstring(template_contents)
        except ET.ParseError as xml_error:
            raise ProcessorError from xml_error

        if template_contents_xml.find("scope"):
            # Remove scope element
            template_contents_xml.remove(template_contents_xml.find("scope"))
        # Inject scope element into version element
        template_contents_xml.append(existing_scope)
        # write back to xml
        template_contents = ET.tostring(
            template_contents_xml, encoding="UTF-8", method="xml"
        )
        # convert to string
        template_contents = template_contents.decode("UTF-8")
        # Print new scope element for debugging
        self.output(template_contents, verbose_level=2)
        return template_contents

    def mount_smb(self, mount_share, mount_user, mount_pass):
        """Mount distribution point."""
        mount_cmd = [
            "/usr/bin/osascript",
            "-e",
            (
                f'mount volume "{mount_share}" as user name "{mount_user}" '
                f'with password "{mount_pass}"'
            ),
        ]
        self.output(
            f"Mount command: {' '.join(mount_cmd)}",
            verbose_level=4,
        )

        r = subprocess.check_output(mount_cmd)
        self.output(
            r.decode("ascii"),
            # r,
            verbose_level=4,
        )

    def umount_smb(self, mount_share):
        """Unmount distribution point."""
        path = f"/Volumes{urlparse(mount_share).path}"
        cmd = ["/usr/sbin/diskutil", "unmount", path]
        try:
            r = subprocess.check_output(cmd)
            self.output(
                r.decode("ascii"),
                verbose_level=2,
            )
        except subprocess.CalledProcessError:
            self.output("WARNING! Unmount failed.")

    def remove_elements_from_xml(self, object_xml, element):
        """removes all instances of an object from XML"""
        for parent in object_xml.findall(f".//{element}/.."):
            for elem in parent.findall(element):
                parent.remove(elem)

    def substitute_elements_in_xml(self, object_xml, element, replacement_value):
        """substitutes all instances of an object from XML with a provided replaceement value"""
        for parent in object_xml.findall(f".//{element}/.."):
            for elem in parent.findall(element):
                # parent.remove(elem)
                elem.text = replacement_value

    def parse_downloaded_api_object(self, existing_object, object_type):
        """Removes or replaces instance-specific items such as ID and computer objects"""
        # first determine if this object is using Classic API or Jamf Pro
        if "JSSResource" in self.api_endpoints(object_type):
            # do XML stuff
            # Parse response as xml
            parsed_xml = ""
            try:
                object_xml = ET.fromstring(existing_object)

                # remove any id tags
                self.remove_elements_from_xml(object_xml, "id")
                # remove any computer objects
                self.remove_elements_from_xml(object_xml, "computers")
                # remove any mobile device objects
                self.remove_elements_from_xml(object_xml, "mobile_devices")
                # remove any user-based objects
                self.remove_elements_from_xml(object_xml, "users")
                self.remove_elements_from_xml(object_xml, "user_groups")
                self.remove_elements_from_xml(object_xml, "limit_to_users")
                # remove any self service icons
                self.remove_elements_from_xml(object_xml, "self_service_icon")
                # for profiles ensure that they are redeployed to all
                self.substitute_elements_in_xml(object_xml, "redeploy_on_update", "All")

                parsed_xml = ET.tostring(object_xml, encoding="UTF-8")
            except ET.ParseError as xml_error:
                raise ProcessorError from xml_error
            return parsed_xml.decode("UTF-8")
        else:
            # do json stuff
            # remove any id-type tags
            if "id" in existing_object:
                existing_object.pop("id")
            if "categoryId" in existing_object:
                existing_object.pop("categoryId")
            if "deviceEnrollmentProgramInstanceId" in existing_object:
                existing_object.pop("deviceEnrollmentProgramInstanceId")
            # now go one deep and look for more id keys. Hopefully we don't have to go deeper!
            for elem in existing_object.values():
                elem_check = elem
                if isinstance(elem_check, abc.Mapping):
                    if "id" in elem:
                        elem.pop("id")
            return json.dumps(existing_object, indent=4)

    class ParseHTMLForError(HTMLParser):  # pylint: disable=abstract-method
        """Parses HTML output for the appropriate error"""

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
