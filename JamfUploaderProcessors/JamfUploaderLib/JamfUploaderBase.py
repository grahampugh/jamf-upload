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
import time
import xml.etree.ElementTree as ET

from base64 import b64encode
from collections import abc, namedtuple
from datetime import datetime, timedelta, timezone
from pathlib import Path
from shutil import rmtree
from time import sleep
from urllib.parse import quote, urlparse
from uuid import UUID
from xml.sax.saxutils import escape

from autopkglib import (  # pylint: disable=import-error
    Processor,
    ProcessorError,
)


class JamfUploaderBase(Processor):
    """Common functions used by at least two JamfUploader processors."""

    # Global version
    __version__ = "2025.10.2.0"

    def api_endpoints(self, object_type, uuid=""):
        """Return the endpoint URL from the object type"""
        api_endpoints = {
            "account": "JSSResource/accounts",
            "account_user": "JSSResource/accounts",
            "account_group": "JSSResource/accounts",
            "activation_code_settings": "JSSResource/activationcode",
            "advanced_computer_search": "JSSResource/advancedcomputersearches",
            "advanced_mobile_device_search": "JSSResource/advancedmobiledevicesearches",
            "api_client": "api/v1/api-integrations",
            "api_role": "api/v1/api-roles",
            "app_installers_deployment": "api/v1/app-installers/deployments",
            "app_installers_title": "api/v1/app-installers/titles",
            "app_installers_t_and_c_settings": (
                "api/v1/app-installers/terms-and-conditions"
            ),
            "app_installers_accept_t_and_c_command": (
                "api/v1/app-installers/terms-and-conditions/accept"
            ),
            "category": "api/v1/categories",
            "check_in_settings": "api/v3/check-in",
            "cloud_ldap": "api/v2/cloud-ldaps",
            "computer": "api/preview/computers",
            "computer_extension_attribute": "api/v1/computer-extension-attributes",
            "computer_group": "JSSResource/computergroups",
            "computer_inventory_collection_settings": (
                "api/v1/computer-inventory-collection-settings"
            ),
            "computer_prestage": "api/v3/computer-prestages",
            "configuration_profile": "JSSResource/mobiledeviceconfigurationprofiles",
            "distribution_point": "JSSResource/distributionpoints",
            "dock_item": "JSSResource/dockitems",
            "enrollment_settings": "api/v4/enrollment",
            "enrollment_customization": "api/v2/enrollment-customizations",
            "failover": "api/v1/sso/failover",
            "failover_generate_command": "api/v1/sso/failover/generate",
            "icon": "api/v1/icon",
            "jamf_pro_version_settings": "api/v1/jamf-pro-version",
            "jamf_protect_plans_sync_command": "api/v1/jamf-protect/plans/sync",
            "jamf_protect_register_settings": "api/v1/jamf-protect/register",
            "jamf_protect_settings": "api/v1/jamf-protect",
            "jcds": "api/v1/jcds",
            "laps_settings": "api/v2/local-admin-password/settings",
            "logflush": "JSSResource/logflush",
            "ldap_server": "JSSResource/ldapservers",
            "mac_application": "JSSResource/macapplications",
            "managed_software_updates_available_updates": (
                "api/v1/managed-software-updates/available-updates"
            ),
            "managed_software_updates_feature_toggle_settings": (
                "api/v1/managed-software-updates/plans/feature-toggle"
            ),
            "managed_software_updates_plans": "api/v1/managed-software-updates/plans",
            "managed_software_updates_plans_events": f"api/v1/managed-software-updates/plans/{uuid}/events",
            "managed_software_updates_plans_group_settings": (
                "api/v1/managed-software-updates/plans/group"
            ),
            "managed_software_updates_update_statuses": (
                "api/v1/managed-software-updates/update-statuses"
            ),
            "mobile_device": "api/v2/mobile-devices",
            "mobile_device_application": "JSSResource/mobiledeviceapplications",
            "mobile_device_extension_attribute": "JSSResource/mobiledeviceextensionattributes",
            "mobile_device_extension_attribute_v1": "api/v1/mobile-device-extension-attributes",
            "mobile_device_group": "JSSResource/mobiledevicegroups",
            "mobile_device_prestage": "api/v1/mobile-device-prestages",
            "network_segment": "JSSResource/networksegments",
            "package": "JSSResource/packages",
            "package_v1": "api/v1/packages",
            "package_upload": "dbfileupload",
            "patch_policy": "JSSResource/patchpolicies",
            "patch_software_title": "JSSResource/patchsoftwaretitles",
            "oauth": "api/oauth/token",
            "os_x_configuration_profile": "JSSResource/osxconfigurationprofiles",
            "policy": "JSSResource/policies",
            "policy_icon": "JSSResource/fileuploads/policies",
            "policy_properties_settings": "api/v1/policy-properties",
            "restricted_software": "JSSResource/restrictedsoftware",
            "self_service_settings": "api/v1/self-service/settings",
            "self_service_plus_settings": "api/v1/self-service-plus/settings",
            "script": "api/v1/scripts",
            "smart_computer_group_membership": "api/v2/computer-groups/smart-group-membership",
            "smtp_server_settings": "api/v2/smtp-server",
            "sso_cert_command": "api/v2/sso/cert",
            "sso_settings": "api/v3/sso",
            "token": "api/v1/auth/token",
            "volume_purchasing_location": "api/v1/volume-purchasing-locations",
        }
        return api_endpoints[object_type]

    def object_types(self, object_type):
        """Return a URL object type from the object type"""
        object_types = {
            "advanced_computer_search": "advancedcomputersearches",
            "advanced_mobile_device_search": "advancedmobiledevicesearches",
            "package": "packages",
            "computer_group": "computergroups",
            "configuration_profile": "mobiledeviceconfigurationprofiles",
            "distribution_point": "distributionpoints",
            "dock_item": "dockitems",
            "mobile_device_group": "mobiledevicegroups",
            "network_segment": "networksegments",
            "policy": "policies",
            "computer_extension_attribute": "computerextensionattributes",
            "mobile_device_extension_attribute": "mobiledeviceextensionattributes",
            "mobile_device_extension_attribute_v1": "mobiledeviceextensionattributes",
            "restricted_software": "restrictedsoftware",
            "os_x_configuration_profile": "osxconfigurationprofiles",
        }
        return object_types[object_type]

    def object_list_types(self, object_type):
        """Return a XML dictionary type from the object type"""
        object_list_types = {
            "account": "accounts",
            "account_user": "users",
            "account_group": "groups",
            "advanced_computer_search": "advanced_computer_searches",
            "advanced_mobile_device_search": "advanced_mobile_device_searches",
            "api_client": "api_clients",
            "api_role": "api_roles",
            "category": "categories",
            "computer": "computers",
            "computer_group": "computer_groups",
            "computer_prestage": "computer_prestages",
            "configuration_profile": "configuration_profiles",
            "dock_item": "dock_items",
            "distribution_point": "distribution_points",
            "computer_extension_attribute": "computer_extension_attributes",
            "ldap_server": "ldap_servers",
            "mac_application": "mac_applications",
            "mobile_device": "mobile_devices",
            "mobile_device_application": "mobile_device_applications",
            "mobile_device_extension_attribute": "mobile_device_extension_attributes",
            "mobile_device_extension_attribute_v1": "mobile_device_extension_attributes",
            "mobile_device_group": "mobile_device_groups",
            "mobile_device_prestage": "mobile_device_prestages",
            "network_segment": "network_segments",
            "os_x_configuration_profile": "os_x_configuration_profiles",
            "package": "packages",
            "patch_policy": "patch_policies",
            "patch_software_title": "patch_software_titles",
            "policy": "policies",
            "script": "scripts",
            "smart_computer_group_membership": "smart_computer_group_membership",
        }
        if object_type in object_list_types:
            return object_list_types[object_type]
        # if the object type is not in the list, return the object type itself
        return object_type

    def to_bool(self, value):
        """Convert a value to a boolean"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() == "true"
        raise ValueError(f"Cannot convert {value!r} to boolean")

    def get_namekey(self, object_type):
        """Return the name key that identifies the object"""
        object_type_namekeys = {
            "api_client": "displayName",
            "computer_prestage": "displayName",
            "mobile_device_prestage": "displayName",
            "enrollment_customization": "displayName",
            "app_installers_title": "titleName",
            "managed_software_updates_available_updates": "availableUpdates",
            "managed_software_updates_plans": "planUuid",
            "managed_software_updates_plans_events": "id",
        }

        if object_type in object_type_namekeys:
            namekey = object_type_namekeys[object_type]
        else:
            namekey = "name"
        return namekey

    def get_namekey_path(self, object_type, namekey):
        """Return the namekey path in Xpath format"""
        # define xpath for name based on object type
        if object_type in (
            "policy",
            "os_x_configuration_profile",
            "configuration_profile",
            "mac_application",
            "mobile_device_application",
            "patch_policy",
            "restricted_software",
        ):
            namekey_path = f"general/{namekey}"
        else:
            namekey_path = namekey
        return namekey_path

    def write_json_file(self, jamf_url, data):
        """dump some json to a temporary file"""
        tf = self.init_temp_file(jamf_url, suffix=".json")
        with open(tf, "w", encoding="utf-8") as fp:
            json.dump(data, fp)
        return tf

    def write_token_to_json_file(self, jamf_url, jamf_user, data):
        """dump the token, expiry, url and user as json to an instance-specific token file"""
        tmp_dir = self.make_tmp_dir(jamf_url)
        token_file = os.path.join(tmp_dir, "token_from_jamf_upload.txt")
        data["url"] = jamf_url
        data["user"] = jamf_user
        with open(token_file, "w", encoding="utf-8") as fp:
            json.dump(data, fp)

    def write_xml_file(self, jamf_url, data):
        """dump some xml to a temporary file"""
        xml_tree = ET.ElementTree(data)
        tf = self.init_temp_file(jamf_url, suffix=".xml")
        xml_tree.write(tf)
        return tf

    def write_temp_file(self, jamf_url, data):
        """dump some text to a temporary file"""
        tf = self.init_temp_file(jamf_url, suffix=".txt")
        with open(tf, "w", encoding="utf-8") as fp:
            fp.write(data)
        return tf

    def make_tmp_dir(self, jamf_url, tmp_dir="/tmp/jamf_upload"):
        """make the tmp directory"""
        cust_id = self.get_netloc(jamf_url)
        if not self.env.get("jamfupload_tmp_dir"):
            os.makedirs(tmp_dir, exist_ok=True)
            self.env["jamfupload_tmp_dir"] = tempfile.mkdtemp(
                dir=tmp_dir, prefix=cust_id + "_"
            )
        return self.env["jamfupload_tmp_dir"]

    def get_netloc(self, jamf_url):
        """get the FQDN from any URL and replace dots with underscores"""
        # Parse the URL and extract the netloc (domain)
        netloc = urlparse(jamf_url).netloc
        # Replace non-alphanumeric characters with underscores
        instance_id = re.sub(r"\W+", "_", netloc).strip("_")
        return instance_id

    def init_temp_file(
        self,
        jamf_url,
        prefix=None,
        suffix=None,
        dir_name="/tmp/jamf_upload",
        text=True,
    ):
        """dump some text to a temporary file"""
        if self.env.get("jamfupload_tmp_dir"):
            dir_name = self.env.get("jamfupload_tmp_dir")
        if not os.path.exists(dir_name):
            dir_name = self.make_tmp_dir(jamf_url=jamf_url, tmp_dir=dir_name)
        return tempfile.mkstemp(
            prefix=prefix,
            suffix=suffix,
            dir=dir_name,
            text=text,
        )[1]

    def get_enc_creds(self, user, password):
        """encode the username and password into a b64-encoded string"""
        credentials = f"{user}:{password}"
        enc_creds = str(b64encode(credentials.encode("utf-8")), "utf-8")
        return enc_creds

    def check_api_token(self, jamf_url, jamf_user):
        """Check validity of an existing token"""
        tmp_dir = self.make_tmp_dir(jamf_url)
        token_file = os.path.join(tmp_dir, "token_from_jamf_upload.txt")
        token = ""

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

                                # Convert the strings to datetime objects with UTC timezone
                                expires_datetime = datetime.strptime(
                                    data["expires"], "%Y-%m-%dT%H:%M:%S.%fZ"
                                ).replace(tzinfo=timezone.utc)

                                now_datetime = datetime.now(timezone.utc)

                                if expires_datetime > now_datetime:
                                    self.output("Existing token is valid")
                                    token = data["token"]
                                else:
                                    self.output(
                                        f"Existing token expired - {data['expires']} "
                                        "vs {datetime.now(timezone.utc)}"
                                    )

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
                except KeyError as e:
                    self.output(
                        f"Some other error: {e}",
                        verbose_level=2,
                    )
        else:
            self.output("No existing valid token found", verbose_level=2)
        return token

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
            self.output(f"ERROR: No token received (HTTP response {r.status_code})")

    def handle_api_auth(
        self, jamf_url, jamf_user="", password="", client_id="", client_secret=""
    ):
        """obtain token using basic auth"""

        # first try to get the account and password from the Keychain
        user_from_kc, pass_from_kc = self.keychain_get_creds(
            jamf_url, jamf_user, client_id
        )
        if user_from_kc and pass_from_kc:
            if self.is_valid_uuid(user_from_kc):
                client_id = user_from_kc
                client_secret = pass_from_kc
                self.output(
                    "Using API client credentials found in keychain", verbose_level=2
                )
            else:
                jamf_user = user_from_kc
                password = pass_from_kc
                self.output(
                    "Using API account credentials found in keychain", verbose_level=2
                )
        else:
            self.output("Credentials not found in keychain", verbose_level=2)

        # check for existing token
        self.output("Checking for existing authentication token", verbose_level=2)
        if client_id and client_secret:
            token = self.check_api_token(jamf_url, client_id)
            # if no valid token, get one
            if not token:
                self.output(
                    "Getting an authentication token using OAuth", verbose_level=2
                )
                token = self.get_api_token_from_oauth(
                    jamf_url, client_id, client_secret
                )
            if not token:
                raise ProcessorError("No token found, cannot continue")
        elif jamf_user and password:
            token = self.check_api_token(jamf_url, jamf_user)
            # if no valid token, get one
            if not token:
                self.output(
                    "Getting an authentication token using Basic Auth", verbose_level=2
                )
                token = self.get_api_token_from_basic_auth(
                    jamf_url, jamf_user, password
                )
            if not token:
                raise ProcessorError("No token found, cannot continue")
        else:
            raise ProcessorError("Insufficient credentials provided, cannot continue")
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
        7. Jira Cloud issue requests (REST API)

        For the Jamf Pro API and Classic API, basic authentication is used to obtain a
        bearer token, which we write to a file along with its expiry datetime.
        Subsequent requests to the same URL use the bearer token until it expires.
        Jamf Pro versions older than 10.35 use basic auth for all Classic API requests.
        The dbfileupload endpoint also uses basic auth.
        The legacy/packages endpoint uses a session ID and separate authentication token.
        This is generated by the JamfPackageUploader processor.
        Authentication for the webhooks is achieved with a preconfigured token.
        """
        tmp_dir = self.make_tmp_dir(jamf_url=url)
        headers_file = os.path.join(tmp_dir, "curl_headers_from_jamf_upload.txt")
        output_file = self.init_temp_file(url, suffix=".txt")
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

        self.output(f"URL: {url}", verbose_level=3)

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

        elif request == "PATCH":
            curl_cmd.extend(["--header", "Content-type: application/merge-patch+json"])
            if data:
                # jamf data upload requires upload-file argument
                curl_cmd.extend(["--upload-file", data])

        # Content-Type for POST/PUT
        elif request == "POST" or request == "PUT":
            if (
                endpoint_type == "slack"
                or endpoint_type == "teams"
                or endpoint_type == "jira"
            ):
                # jira, slack and teams require a data argument
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
            elif ("/api/" in url and endpoint_type != "jira") or "/uapi/" in url:
                curl_cmd.extend(["--header", "Content-type: application/json"])
            # note: other endpoints should supply their headers via 'additional_curl_opts'

        # fail other request types
        elif request != "GET" and request != "DELETE" and request != "PATCH":
            self.output(f"WARNING: HTTP method {request} not supported")

        # direct output to a file
        curl_cmd.extend(["--output", output_file])
        self.output(f"Output file is: {output_file}", verbose_level=3)

        # write session for jamf API requests
        if (
            ("/api/" in url and endpoint_type != "jira")
            or "/uapi/" in url
            or "JSSResource" in url
            or endpoint_type == "package_upload"
            or endpoint_type == "jcds"
        ):
            curl_cmd.extend(["--cookie-jar", cookie_jar])

            # look for existing session
            if os.path.exists(cookie_jar):
                self.output("Existing cookie found", verbose_level=2)
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
        elif request == "PUT" or request == "PATCH":
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
            elif obj_name:
                self.output(f"{endpoint_type} '{obj_name}' {action} successful")
            else:
                self.output(f"{endpoint_type} {action} successful")
            return "break"
        else:
            self.output("API response:", verbose_level=2)
            if isinstance(r.output, (bytes, bytearray)):
                self.output(r.output.decode("utf-8"), verbose_level=2)
            else:
                self.output(r.output, verbose_level=2)

            if r.status_code >= 400:
                # extract the error message
                if isinstance(r.output, (bytes, bytearray)):
                    error_lines = re.findall(
                        r"<p>Error:(.*?)</p>", r.output.decode("utf-8")
                    )
                elif isinstance(r.output, str):
                    error_lines = re.findall(r"<p>Error:(.*?)</p>", r.output)
                else:
                    error_lines = []
                if error_lines:
                    error_message = error_lines[0].strip()
                    if obj_name:
                        raise ProcessorError(
                            f"ERROR: {endpoint_type} '{obj_name}' {action} failed - "
                            f"{error_message} (status code {r.status_code})"
                        )
                    else:
                        raise ProcessorError(
                            f"ERROR: {endpoint_type} {action} failed - "
                            f"{error_message} (status code {r.status_code})"
                        )
                else:
                    self.output(
                        f"ERROR: {endpoint_type} {action} failed - "
                        f"status code {r.status_code}"
                    )

    def get_jamf_pro_version(self, jamf_url, token):
        """get the Jamf Pro version so that we can figure out which auth method to use for the
        Classic API"""
        url = jamf_url + "/" + self.api_endpoints("jamf_pro_version_settings")
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

            if self.status_check(r, object_type, object_name, "GET") == "break":
                object_list = json.loads(r.output)
                self.output(
                    object_list,
                    verbose_level=4,
                )
                obj_id = 0
                if object_type == "account_user" or object_type == "account_group":
                    object_list = object_list["accounts"]
                for obj in object_list[self.object_list_types(object_type)]:
                    self.output(
                        obj,
                        verbose_level=4,
                    )
                    # we need to check for a case-insensitive match
                    if obj["name"].lower() == object_name.lower():
                        obj_id = obj["id"]
                        break
                return obj_id
            else:
                raise ProcessorError(
                    f"ERROR: Unable to get {object_type} list from server - "
                    f"status code {r.status_code}"
                )
        else:
            # do JSON stuff
            url_filter = (
                f"?page=0&page-size=1000&sort=id&filter={filter_name}"
                f"%3D%3D%22{quote(object_name)}%22"
            )
            url = jamf_url + "/" + self.api_endpoints(object_type) + url_filter
            r = self.curl(request="GET", url=url, token=token)
            if self.status_check(r, object_type, object_name, "GET") == "break":
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
            else:
                raise ProcessorError(
                    f"ERROR: Unable to get {object_type} list from server - "
                    f"status code {r.status_code}"
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
        matched_filepath = ""

        # first, look in the overrides directory
        self.output(f"Looking for {filename} in RECIPE_OVERRIDE_DIRS", verbose_level=3)
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
        else:
            self.output("No RECIPE_OVERRIDE_DIRS defined", verbose_level=3)

        # second, look in the same directory as the recipe or any sibling directories
        self.output(
            f"Looking for {filename} in {recipe_dir} or its siblings", verbose_level=3
        )
        # First check the recipe directory itself
        filepath = os.path.join(recipe_dir, filename)
        if os.path.exists(filepath):
            self.output(f"File found at: {filepath}")
            return filepath

        # Then check sibling directories
        self.output(
            f"Checking sibling directories of {recipe_dir_path}", verbose_level=3
        )
        for sibling in recipe_dir_path.parent.iterdir():
            if sibling.is_dir() and sibling != recipe_dir_path:
                self.output(
                    f"Looking for {filename} in sibling directory: {sibling}",
                    verbose_level=3,
                )
                filepath = os.path.join(sibling, filename)
                if os.path.exists(filepath):
                    self.output(f"File found at: {filepath}")
                    return filepath

        # third, try to match the recipe's dir with one of the recipe search dirs
        if self.env.get("RECIPE_SEARCH_DIRS"):
            matched_filepath = ""
            for d in self.env["RECIPE_SEARCH_DIRS"]:
                search_dir_path = Path(os.path.expanduser(d))
                self.output(
                    f"Recipe directory: {recipe_dir_path}",
                    verbose_level=3,
                )
                self.output(
                    f"Looking for {filename} in {search_dir_path}",
                    verbose_level=3,
                )
                if (
                    search_dir_path == recipe_dir_path
                    or search_dir_path.parent == recipe_dir_path.parent
                    or search_dir_path == recipe_dir_path.parent
                    or search_dir_path in recipe_dir_path.parent.parents
                ):
                    # matching search dir, look for file in here
                    self.output(f"Matching dir: {search_dir_path}", verbose_level=3)
                    for path in Path(os.path.expanduser(d)).rglob(filename):
                        matched_filepath = str(path)
                        break
                if matched_filepath:
                    self.output(f"File found at: {matched_filepath}")
                    return matched_filepath
            self.output(
                f"File {filename} not found in any RECIPE_SEARCH_DIRS", verbose_level=3
            )

        # fourth, look in the parent recipe's directory if we are an override
        if matched_override_dir:
            if self.env.get("PARENT_RECIPES"):
                self.output(
                    f"Looking for {filename} in parent recipe's repo",
                    verbose_level=3,
                )
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
        raise ProcessorError(f"File '{filename}' not found")

    def get_all_api_objects(
        self, jamf_url, object_type, uuid="", token="", namekey="name"
    ):
        """get a list of all objects of a particular type"""
        # Get all objects from Jamf Pro as JSON object
        self.output(f"Getting all {self.api_endpoints(object_type)} from {jamf_url}")

        # find the number of objects to get so that we can paginate properly
        if "JSSResource" in self.api_endpoints(object_type, uuid):
            # Classic API: no pagination, just get all objects at once
            url = f"{jamf_url}/{self.api_endpoints(object_type, uuid)}"
            r = self.curl(request="GET", url=url, token=token)
            if r.status_code != 200:
                raise ProcessorError(
                    f"ERROR: Unable to get list of {object_type} from {jamf_url}"
                )
            self.output(f"Output:\n{r.output}", verbose_level=4)
            object_list = json.loads(r.output)[self.object_list_types(object_type)]
        else:
            # Jamf Pro API: use pagination
            url_filter = "?page=0&page-size=1"
            url = f"{jamf_url}/{self.api_endpoints(object_type, uuid)}{url_filter}"
            r = self.curl(request="GET", url=url, token=token)
            self.output(f"Output:\n{r.output}", verbose_level=4)
            # check if there is a totalCount value in the output
            try:
                total_objects = int(r.output["totalCount"])
                self.output(f"Total objects: {total_objects}", verbose_level=2)
                # if total count is 0, return empty list
                if total_objects == 0:
                    return []
                # now get all objects in a loop, paginating per 100 objects
                object_list = []

                for page in range(0, total_objects, 100):
                    url_filter = (
                        f"?page={page}&page-size=100&sort={namekey}&sort-order=asc"
                    )
                    self.output(f"Getting page {page} of objects", verbose_level=2)
                    if page > 0:
                        time.sleep(0.5)  # be nice to the server
                    url = f"{jamf_url}/{self.api_endpoints(object_type, uuid)}{url_filter}"
                    r = self.curl(request="GET", url=url, token=token)
                    if r.status_code != 200:
                        raise ProcessorError(
                            f"ERROR: Unable to get list of {object_type} from {jamf_url}"
                        )
                    self.output(f"Output:\n{r.output}", verbose_level=4)
                    # parse the output to get the list of objects
                    if object_type == "managed_software_updates_available_updates":
                        object_list.extend(r.output["availableUpdates"])
                    elif object_type == "managed_software_updates_plans_events":
                        object_list.extend(r.output["events"])
                    else:
                        object_list.extend(r.output["results"])
            except (KeyError, TypeError):
                # if not, we're not dealing with a paginated endpoint, so just return the
                # results list
                object_list = r.output

        # ensure the list is sorted by namekey if possible
        try:
            object_list = sorted(object_list, key=lambda x: x.get(namekey, "").lower())
        except (KeyError, TypeError, AttributeError):
            # if not, just leave the list as is
            pass
        self.output(f"List of objects:\n{object_list}", verbose_level=3)

        return object_list

    def get_settings_object(self, jamf_url, object_type, token=""):
        """get the content of a settings-style endpoint"""
        # Get results from Jamf Pro as JSON object
        self.output(f"Getting {self.api_endpoints(object_type)} from {jamf_url}")

        # check for existing
        url = f"{jamf_url}/{self.api_endpoints(object_type)}"

        # for Classic API
        if "JSSResource" in url:
            r = self.curl(request="GET", url=url, token=token, accept_header="xml")
            # Parse response as xml
            try:
                obj_xml = ET.fromstring(r.output)
            except ET.ParseError as xml_error:
                raise ProcessorError from xml_error
            else:
                ET.indent(obj_xml)
                obj_content = ET.tostring(obj_xml, encoding="UTF-8").decode("UTF-8")
            self.output(
                obj_content,
                verbose_level=4,
            )

        # for Jamf Pro API
        else:
            r = self.curl(request="GET", url=url, token=token, accept_header="json")
            obj_content = r.output
            self.output(
                obj_content,
                verbose_level=4,
            )

        return obj_content

    def get_api_obj_contents_from_id(
        self, jamf_url, object_type, obj_id, obj_path="", token=""
    ):
        """get the full contents or the value of an item in a Classic or Jamf Pro API object"""
        # define the relationship between the object types and their URL
        if "JSSResource" in self.api_endpoints(object_type):
            # do XML stuff
            if object_type == "account_user":
                url = f"{jamf_url}/{self.api_endpoints(object_type)}/userid/{obj_id}"
            elif object_type == "account_group":
                url = f"{jamf_url}/{self.api_endpoints(object_type)}/groupid/{obj_id}"
            else:
                # for all other Classic API objects, we use the ID
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
                    obj_content = ET.tostring(obj_xml, encoding="UTF-8").decode("UTF-8")
                return obj_content
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

    def get_api_obj_value_from_id(self, jamf_url, object_type, obj_id, obj_path, token):
        """get the value of an item in a Classic or Jamf Pro API object"""
        # define the relationship between the object types and their URL
        # we could make this shorter with some regex but I think this way is clearer

        # if we find an object ID or it's an endpoint without IDs, we PUT or PATCH
        # if we're creating a new object, we POST
        value = ""
        if "JSSResource" in self.api_endpoints(object_type):
            # do XML stuff
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
            else:
                raise ProcessorError(f"ERROR: {object_type} of ID {obj_id} not found.")
        else:
            url = f"{jamf_url}/{self.api_endpoints(object_type)}/{obj_id}"
            request = "GET"
            r = self.curl(request=request, url=url, token=token)
            if r.status_code == 200:
                obj_content = r.output
                self.output(obj_content, verbose_level=4)

                # convert an xpath to json
                xpath_list = obj_path.split("/")
                value = obj_content

                for _, xpath in enumerate(xpath_list):
                    if xpath:
                        try:
                            value = value[xpath]
                            self.output(value, verbose_level=3)
                        except KeyError:
                            value = ""
                            break

            else:
                raise ProcessorError(f"ERROR: {object_type} of ID {obj_id} not found.")
        if value:
            self.output(f"Value of '{obj_path}': {value}", verbose_level=2)
        return value

    def delete_object(self, jamf_url, object_type, obj_id, token):
        """Delete API object"""

        self.output(f"Deleting {object_type}...")

        if "JSSResource" in self.api_endpoints(object_type):
            # do XML stuff
            url = f"{jamf_url}/{self.api_endpoints(object_type)}/id/{obj_id}"
        else:
            url = f"{jamf_url}/{self.api_endpoints(object_type)}/{obj_id}"

        count = 0
        while True:
            count += 1
            self.output(f"{object_type} delete attempt {count}", verbose_level=2)
            request = "DELETE"
            r = self.curl(request=request, url=url, token=token)

            # check HTTP response
            if self.status_check(r, object_type, obj_id, request) == "break":
                break
            if count > 5:
                self.output(
                    f"WARNING: {object_type} deletion did not succeed after 5 attempts"
                )
                self.output(f"\nHTTP POST Response Code: {r.status_code}")
                raise ProcessorError(f"ERROR: {object_type} deletion failed ")
            sleep(30)
        return r.status_code

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
        """substitutes all instances of an object from XML with a provided replacement value"""
        for parent in object_xml.findall(f".//{element}/.."):
            for elem in parent.findall(element):
                elem.text = replacement_value

    def replace_element(self, object_type, existing_object, element_path, new_value):
        """Replaces a specific element from XML or JSON using a path such as 'general/id'."""
        # Split the path into parts
        keys = element_path.split("/")
        if "JSSResource" in self.api_endpoints(object_type):
            # do XML stuff
            try:
                # load object
                parsed_xml = ""
                object_xml = ET.fromstring(existing_object)
                root = ET.ElementTree(object_xml).getroot()
                parent = root
                found = None

                # Traverse the XML tree to find the parent of the target element
                for key in keys:
                    found = parent.find(key)
                    if found is not None:
                        parent = found
                    else:
                        self.output(
                            f"Path '{element_path}' not found in template.",
                            verbose_level=3,
                        )

                # Find and replace the target element
                if found is not None:
                    parent.text = new_value

                    self.output(
                        f"Successfully replaced '{element_path}' with '{new_value}'.",
                        verbose_level=2,
                    )
                parsed_xml = ET.tostring(object_xml, encoding="UTF-8")
            except ET.ParseError as xml_error:
                raise ProcessorError("Could not extract XML") from xml_error
            return parsed_xml.decode("UTF-8")

        # do json stuff
        if not isinstance(existing_object, dict):
            existing_object = json.loads(existing_object)
            parent = existing_object

            # Traverse the JSON structure to find the target element
            for key in keys[:-1]:
                if key in parent and isinstance(parent[key], dict):
                    parent = parent[key]
                else:
                    raise KeyError(f"Path '{element_path}' not found.")

            # Replace the element's value with the new value
            last_key = keys[-1]
            if last_key in parent:
                parent[last_key] = new_value
            else:
                raise KeyError(f"Key '{last_key}' not found in path '{element_path}'.")
            self.output(
                f"Successfully replaced '{element_path}' with '{new_value}'.",
                verbose_level=2,
            )
            return json.dumps(existing_object, indent=4)

    def parse_downloaded_api_object(
        self, existing_object, object_type, elements_to_remove
    ):
        """Removes or replaces instance-specific items such as ID and computer objects"""
        # first determine if this object is using Classic API or Jamf Pro
        if "JSSResource" in self.api_endpoints(object_type):
            # do XML stuff
            # Parse response as xml
            parsed_xml = ""
            object_xml = ET.fromstring(existing_object)
            try:
                # # remove any id tags
                # self.remove_elements_from_xml(object_xml, "id")
                # # remove any self service icons
                # self.remove_elements_from_xml(object_xml, "self_service_icon")
                # optional array of other elements to remove
                if elements_to_remove:
                    for elem in elements_to_remove:
                        self.output(f"Deleting element {elem}...", verbose_level=2)
                        self.remove_elements_from_xml(object_xml, elem)

                # for profiles ensure that they are redeployed to all
                self.substitute_elements_in_xml(object_xml, "redeploy_on_update", "All")

                parsed_xml = ET.tostring(object_xml, encoding="UTF-8")
            except ET.ParseError as xml_error:
                raise ProcessorError("Could not extract XML") from xml_error
            return parsed_xml.decode("UTF-8")

        # do json stuff
        if existing_object:
            if not isinstance(existing_object, dict):
                existing_object = json.loads(existing_object)

            # remove any id-type tags
            # if "id" in existing_object:
            #     existing_object.pop("id")
            # if "categoryId" in existing_object:
            #     existing_object.pop("categoryId")
            # if "deviceEnrollmentProgramInstanceId" in existing_object:
            #     existing_object.pop("deviceEnrollmentProgramInstanceId")
            # now go one deep and look for more id keys. Hopefully we don't have to go deeper!
            if elements_to_remove:
                for elem in elements_to_remove:
                    for value in existing_object.values():
                        value_check = value
                        if isinstance(value_check, abc.Mapping):
                            if elem in value:
                                value.pop(elem)
            return json.dumps(existing_object, indent=4)
        return ""

    def substitute_existing_version_locks(
        self, jamf_url, object_type, obj_id, object_template, token
    ):
        """replace the existing version lock to ensure we don't change it"""
        # first grab the payload from the json object
        existing_object = self.get_api_obj_contents_from_id(
            jamf_url,
            object_type,
            obj_id,
            "",
            token=token,
        )

        # import template from file and replace any keys in the template
        if os.path.exists(object_template):
            with open(object_template, "r", encoding="utf-8") as file:
                template_contents = json.load(file)
        else:
            raise ProcessorError("Template does not exist!")

        self.output(f"Existing Object: {existing_object}", verbose_level=3)  # TEMP
        # now extract the main version lock from the existing object
        template_contents["versionLock"] = existing_object["versionLock"]
        self.output(
            f"Top level version lock: {existing_object['versionLock']}", verbose_level=2
        )
        template_contents["locationInformation"]["versionLock"] = existing_object[
            "locationInformation"
        ]["versionLock"]
        self.output(
            (
                "locationInformation version lock: "
                f"{existing_object['locationInformation']['versionLock']}"
            ),
            verbose_level=3,
        )
        template_contents["purchasingInformation"]["versionLock"] = existing_object[
            "purchasingInformation"
        ]["versionLock"]
        self.output(
            (
                "purchasingInformation version lock: "
                f"{existing_object['purchasingInformation']['versionLock']}"
            ),
            verbose_level=3,
        )
        template_contents["accountSettings"]["versionLock"] = existing_object[
            "accountSettings"
        ]["versionLock"]
        self.output(
            (
                "accountSettings version lock: "
                f"{existing_object['accountSettings']['versionLock']}"
            ),
            verbose_level=3,
        )

        self.output(f"Prestage: {template_contents}", verbose_level=3)  # TEMP

        with open(object_template, "w", encoding="utf-8") as file:
            json.dump(template_contents, file)

    def prepare_template(
        self,
        jamf_url,
        object_type,
        object_template,
        object_name=None,
        xml_escape=False,
        elements_to_remove=None,
        element_to_replace=None,
        replacement_value=None,
        namekey_path=None,
    ):
        """prepare the object contents"""
        # import template from file and replace any keys in the template
        if os.path.exists(object_template):
            with open(object_template, "r", encoding="utf-8") as file:
                template_contents = file.read()
        else:
            raise ProcessorError("Template does not exist!")

        # parse the template except for settings-style objects
        if "_settings" not in object_type:
            template_contents = self.parse_downloaded_api_object(
                template_contents, object_type, elements_to_remove
            )

        # substitute user-assignable keys
        if object_name:
            object_name = self.substitute_assignable_keys(object_name)

            # also update the name key to match the given name
            if namekey_path:
                template_contents = self.replace_element(
                    object_type, template_contents, namekey_path, object_name
                )
        template_contents = self.substitute_assignable_keys(
            template_contents, xml_escape
        )

        # replace specific element in the template
        if element_to_replace and replacement_value:
            template_contents = self.replace_element(
                object_type,
                template_contents,
                element_to_replace,
                replacement_value,
            )

        # PreStages need to iterate the versionLock value in order to replace them
        if object_type == "computer_prestage":
            template_contents = self.inject_version_lock(template_contents)

        self.output("object data:", verbose_level=2)
        self.output(template_contents, verbose_level=2)

        # write the template to temp file
        template_file = self.write_temp_file(jamf_url, template_contents)
        return object_name, template_file

    def remove_non_printable(self, text):
        """Remove non-printable characters.
        This is required when obtaining a password from the keychain
        """
        pattern = r"[\x00-\x1F\x7F-\x9F]"
        return re.sub(pattern, "", text)

    def is_valid_uuid(self, uuid_to_test):
        """Check if a string is a version 4 UUID"""
        try:
            UUID(str(uuid_to_test))
            self.output(f"{uuid_to_test} is a Client ID", verbose_level=3)
            return True
        except ValueError:
            self.output(f"{uuid_to_test} is an account name", verbose_level=3)
            return False

    def keychain_get_creds(self, service, jamf_user, client_id):
        """Get an account name and password from the keychain.

        Args:
            service: The service name (the Jamf Pro URL in this case)
            jamf_user: optional user if needed to specify between multiple
                keychain entries of the same server
            client_id: optional API Client ID if needed to specify between multiple
                keychain entries of the same server

        Returns:
            The account name and password, or `None` for both if not found.

        """
        if client_id:
            acct = client_id
        elif jamf_user:
            acct = jamf_user
        else:
            acct = None
        passw = None
        if acct:
            try:
                result = subprocess.run(
                    [
                        "/usr/bin/security",
                        "find-internet-password",
                        "-s",
                        service,
                        "-a",
                        acct,
                        "-w",
                        "-g",
                    ],
                    text=True,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                )
                # self.output(result.stdout, verbose_level=2)
                passw = self.remove_non_printable(result.stdout)
            except subprocess.CalledProcessError:
                pass
        else:
            try:
                result = subprocess.run(
                    [
                        "/usr/bin/security",
                        "find-internet-password",
                        "-s",
                        service,
                        "-g",
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                self.output(result.stdout, verbose_level=3)
                for line in result.stdout.splitlines():
                    if "acct" in line:
                        acct = line.split('"')[3]
            except subprocess.CalledProcessError:
                pass
            if acct:
                try:
                    result = subprocess.run(
                        [
                            "/usr/bin/security",
                            "find-internet-password",
                            "-s",
                            service,
                            "-a",
                            acct,
                            "-w",
                            "-g",
                        ],
                        text=True,
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                    )
                    # self.output(result.stdout, verbose_level=2)
                    passw = self.remove_non_printable(result.stdout)
                except subprocess.CalledProcessError:
                    pass

        return acct, passw


if __name__ == "__main__":
    PROCESSOR = JamfUploaderBase()
    PROCESSOR.execute_shell()
