#!/usr/local/autopkg/python

"""
JamfCategoryUploader processor for uploading a category to Jamf Pro using AutoPkg
    by G Pugh
"""

import json
import os
import re
import subprocess
import uuid

from collections import namedtuple
from base64 import b64encode
from shutil import rmtree
from time import sleep
from urllib.parse import quote
from autopkglib import Processor, ProcessorError  # pylint: disable=import-error


class JamfCategoryUploader(Processor):
    """A processor for AutoPkg that will upload a category to a Jamf Cloud or on-prem server."""

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
        "category_name": {"required": False, "description": "Category", "default": ""},
        "category_priority": {
            "required": False,
            "description": "Category priority",
            "default": "10",
        },
        "replace_category": {
            "required": False,
            "description": "Overwrite an existing category if True.",
            "default": False,
        },
    }

    output_variables = {
        "category": {"description": "The created/updated category."},
        "jamfcategoryuploader_summary_result": {
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

    def get_uapi_token(self, jamf_url, enc_creds):
        """get a token for the Jamf Pro API"""
        url = "{}/uapi/auth/tokens".format(jamf_url)

        r = self.curl("POST", url, enc_creds)
        if r.status_code == 200:
            try:
                token = str(r.output["token"])
                self.output("Session token received")
                return token
            except KeyError:
                self.output("ERROR: No token received")
                return
        else:
            self.output("ERROR: No token received")
            return

    def get_uapi_obj_id_from_name(self, jamf_url, object_type, object_name, token):
        """Get the UAPI object by name"""
        url = (
            f"{jamf_url}/uapi/v1/{object_type}?page=0&page-size=1000&sort=id"
            f"&filter=name%3D%3D%22{quote(object_name)}%22"
        )
        r = self.curl("GET", url, token)
        if r.status_code == 200:
            obj_id = 0
            for obj in r.output["results"]:
                self.output(f"ID: {obj['id']} NAME: {obj['name']}", verbose_level=2)
                if obj["name"].lower() == object_name.lower():
                    obj_id = obj["id"]
            return obj_id

    def upload_category(self, jamf_url, category_name, priority, token, obj_id=0):
        """Update category metadata."""

        # build the object
        category_data = {"priority": priority, "name": category_name}
        if obj_id:
            url = "{}/uapi/v1/categories/{}".format(jamf_url, obj_id)
            category_data["name"] = category_name
        else:
            url = "{}/uapi/v1/categories".format(jamf_url)

        self.output("Uploading category..")

        # we cannot PUT a category of the same name due to a bug in Jamf Pro (PI-008157).
        # so we have to do a first pass with a temporary different name, then change it back
        count = 0
        if obj_id:
            category_name_temp = category_name + "_TEMP"
            category_data_temp = {"priority": priority, "name": category_name_temp}
            category_json_temp = self.write_json_file(category_data_temp)
            while True:
                count += 1
                self.output(
                    f"Category upload attempt {count}",
                    verbose_level=2,
                )
                r = self.curl("PUT", url, token, category_json_temp)
                # check HTTP response
                if self.status_check(r, "Category", category_name_temp) == "break":
                    break
                if count > 5:
                    self.output(
                        "ERROR: Temporary category update did not succeed after 5 attempts"
                    )
                    self.output(f"\nHTTP POST Response Code: {r.status_code}")
                    raise ProcessorError("ERROR: Category upload failed ")
                sleep(10)

        # write the category. If updating an existing category, this reverts the name
        # to its original.
        category_json = self.write_json_file(category_data)
        while True:
            count += 1
            self.output(
                f"Category upload attempt {count}",
                verbose_level=2,
            )
            method = "PUT" if obj_id else "POST"
            r = self.curl(method, url, token, category_json)
            # check HTTP response
            if self.status_check(r, "Category", category_name) == "break":
                break
            if count > 5:
                self.output("ERROR: Category creation did not succeed after 5 attempts")
                self.output(f"\nHTTP POST Response Code: {r.status_code}")
                raise ProcessorError("ERROR: Category upload failed ")
            sleep(10)

        # clean up temp files
        self.clear_tmp_dir()

    def main(self):
        """Do the main thing here"""
        self.jamf_url = self.env.get("JSS_URL")
        self.jamf_user = self.env.get("API_USERNAME")
        self.jamf_password = self.env.get("API_PASSWORD")
        self.category_name = self.env.get("category_name")
        self.category_priority = self.env.get("category_priority")
        self.replace = self.env.get("replace_category")
        # handle setting replace_pkg in overrides
        if not self.replace or self.replace == "False":
            self.replace = False

        # clear any pre-existing summary result
        if "jamfcategoryuploader_summary_result" in self.env:
            del self.env["jamfcategoryuploader_summary_result"]

        # encode the username and password into a basic auth b64 encoded string
        credentials = f"{self.jamf_user}:{self.jamf_password}"
        enc_creds_bytes = b64encode(credentials.encode("utf-8"))
        enc_creds = str(enc_creds_bytes, "utf-8")

        # now get the session token
        token = self.get_uapi_token(self.jamf_url, enc_creds)

        # now process the category
        # check for existing category
        self.output(f"Checking for existing '{self.category_name}' on {self.jamf_url}")
        obj_id = self.get_uapi_obj_id_from_name(
            self.jamf_url, "categories", self.category_name, token
        )
        if obj_id:
            self.output(f"Category '{self.category_name}' already exists: ID {obj_id}")
            if self.replace:
                self.output(
                    f"Replacing existing category as 'replace_category' is set to {self.replace}",
                    verbose_level=1,
                )
                # PUT the category
                self.upload_category(
                    self.jamf_url,
                    self.category_name,
                    self.category_priority,
                    token,
                    obj_id,
                )
            else:
                self.output(
                    "Not replacing existing category. Use replace_category='True' to enforce.",
                    verbose_level=1,
                )
                return
        else:
            # POST the category
            self.upload_category(
                self.jamf_url, self.category_name, self.category_priority, token
            )

        # output the summary
        self.env["category"] = self.category_name
        self.env["jamfcategoryuploader_summary_result"] = {
            "summary_text": "The following categories were created or updated in Jamf Pro:",
            "report_fields": ["category", "priority"],
            "data": {
                "category": self.category_name,
                "priority": str(self.category_priority),
            },
        }


if __name__ == "__main__":
    PROCESSOR = JamfCategoryUploader()
    PROCESSOR.execute_shell()
