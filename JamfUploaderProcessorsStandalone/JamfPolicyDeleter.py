#!/usr/local/autopkg/python

"""
JamfPolicyDeleter processor for deleting policies from Jamf Pro using AutoPkg
    by G Pugh
"""

import json
import re
import os
import subprocess

from collections import namedtuple
from base64 import b64encode
from datetime import datetime
from shutil import rmtree
from time import sleep
from autopkglib import (
    APLooseVersion,
    Processor,
    ProcessorError,
)  # pylint: disable=import-error


class JamfPolicyDeleter(Processor):
    """A processor for AutoPkg that will delete a policy from a Jamf Cloud or
    on-prem server."""

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
            "required": True,
            "description": "Policy to delete",
            "default": "",
        },
    }

    output_variables = {
        "jamfpolicydeleter_summary_result": {
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
            "token": "api/v1/auth/tokens",
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
            self.output(f"{endpoint_type} '{obj_name}' was deleted successfully")
            return "break"
        elif r.status_code == 409:
            self.output(r.output, verbose_level=2)
            raise ProcessorError(
                f"WARNING: {endpoint_type} '{obj_name}' deletion failed due to a conflict"
            )
        elif r.status_code == 401:
            raise ProcessorError(
                f"ERROR: {endpoint_type} '{obj_name}' deletion failed due to permissions error"
            )
        else:
            self.output(f"WARNING: {endpoint_type} '{obj_name}' deletion failed")
            self.output(r.output, verbose_level=2)

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

    def delete_policy(self, jamf_url, enc_creds, obj_id):
        """Delete policy"""

        self.output("Deleting Policy...")

        object_type = "policy"
        url = "{}/{}/id/{}".format(jamf_url, self.api_endpoints(object_type), obj_id)

        count = 0
        while True:
            count += 1
            self.output("Policy delete attempt {}".format(count), verbose_level=2)
            request = "DELETE"
            r = self.curl(request=request, url=url, enc_creds=enc_creds)

            # check HTTP response
            if self.status_check(r, "Policy", obj_id) == "break":
                break
            if count > 5:
                self.output("WARNING: Policy deletion did not succeed after 5 attempts")
                self.output("\nHTTP POST Response Code: {}".format(r.status_code))
                raise ProcessorError("ERROR: Policy deletion failed ")
            sleep(30)

        # clean up temp files
        self.clear_tmp_dir()

        return r

    def main(self):
        """Do the main thing here"""
        self.jamf_url = self.env.get("JSS_URL")
        self.jamf_user = self.env.get("API_USERNAME")
        self.jamf_password = self.env.get("API_PASSWORD")
        self.policy_name = self.env.get("policy_name")

        # clear any pre-existing summary result
        if "jamfpolicydeleter_summary_result" in self.env:
            del self.env["jamfpolicydeleter_summary_result"]

        # now start the process of deleting the object
        self.output(f"Checking for existing '{self.policy_name}' on {self.jamf_url}")

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

        # check for existing - requires obj_name
        obj_type = "policy"
        obj_id = self.get_api_obj_id_from_name(
            self.jamf_url,
            obj_type,
            self.policy_name,
            enc_creds=send_creds,
            token=token,
        )

        if obj_id:
            self.output(f"Policy '{self.policy_name}' exists: ID {obj_id}")
            self.output(
                "Deleting existing policy",
                verbose_level=1,
            )
            self.delete_policy(
                self.jamf_url,
                obj_id,
                enc_creds=send_creds,
                token=token,
            )
        else:
            self.output(
                f"Policy '{self.policy_name}' not found on {self.jamf_url}.",
                verbose_level=1,
            )
            return

        # output the summary
        self.env["jamfpolicydeleter_summary_result"] = {
            "summary_text": "The following policies were deleted from Jamf Pro:",
            "report_fields": ["policy"],
            "data": {"policy": self.policy_name},
        }


if __name__ == "__main__":
    PROCESSOR = JamfPolicyDeleter()
    PROCESSOR.execute_shell()
