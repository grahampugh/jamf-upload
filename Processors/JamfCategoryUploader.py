#!/usr/local/autopkg/python

"""
JamfCategoryUploader processor for uploading a category to Jamf Pro using AutoPkg
    by G Pugh

"""

import json
import os.path
import subprocess
import uuid
from collections import namedtuple
from base64 import b64encode
from time import sleep
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
        "category_name": {"required": False, "description": "Category", "default": "",},
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
        "category": {"description": "The created/updated category.",},
        "jamfcategoryuploader_summary_result": {
            "description": "Description of interesting results.",
        },
    }

    def nscurl(self, method, url, auth, data="", additional_headers=""):
        """
        build an nscurl command based on method (GET, PUT, POST, DELETE)
        If the URL contains 'uapi' then token should be passed to the auth variable, 
        otherwise the enc_creds variable should be passed to the auth variable
        """
        headers_file = "/tmp/nscurl_headers_from_jamf_upload.txt"
        output_file = "/tmp/nscurl_output_from_jamf_upload.txt"

        # build the nscurl command
        nscurl_cmd = [
            "/usr/bin/nscurl",
            "-M",
            method,
            "-D",
            headers_file,
            "--output",
            output_file,
            url,
        ]

        # the authorisation is Basic unless we are using the uapi and already have a token
        if "uapi" in url and "tokens" not in url:
            nscurl_cmd.extend(["--header", f"authorization: Bearer {auth}"])
        else:
            nscurl_cmd.extend(["--header", f"authorization: Basic {auth}"])

        # set either Accept or Content-Type depending on method
        if method == "GET" or method == "DELETE":
            nscurl_cmd.extend(["--header", "Accept: application/json"])
        elif method == "POST" or method == "PUT":
            if data:
                nscurl_cmd.extend(["--upload", data])
            # uapi sends json, classic API must send xml
            if "uapi" in url:
                nscurl_cmd.extend(["--header", "Content-type: application/json"])
            else:
                nscurl_cmd.extend(["--header", "Content-type: application/xml"])
        else:
            self.output(f"WARNING: HTTP method {method} not supported")

        # additional headers for advanced requests
        if additional_headers:
            nscurl_cmd.extend(additional_headers)

        # now subprocess the nscurl command and build the r tuple which contains the
        # headers, status code and outputted data
        subprocess.check_output(nscurl_cmd)

        r = namedtuple("r", ["headers", "status_code", "output"])
        try:
            with open(headers_file, "r") as file:
                headers = file.readlines()
            r.headers = [x.strip() for x in headers]
            r.status_code = int(r.headers[0].split()[1])
            with open(output_file, "rb") as file:
                if "uapi" in url:
                    r.output = json.load(file)
                else:
                    r.output = file.read()
            return r
        except IOError:
            raise ProcessorError(f"WARNING: {headers_file} not found")

    def write_json_file(self, data):
        """dump some json to a temporary file"""
        tf = os.path.join("/tmp", str(uuid.uuid4()))
        with open(tf, "w") as fp:
            json.dump(data, fp)
        return tf

    def write_temp_file(self, data):
        """dump some text to a temporary file"""
        tf = os.path.join("/tmp", str(uuid.uuid4()))
        with open(tf, "w") as fp:
            fp.write(data)
        return tf

    def status_check(self, r, endpoint_type, obj_name):
        """Return a message dependent on the HTTP response"""
        if r.status_code == 200 or r.status_code == 201:
            self.output(f"{endpoint_type} '{obj_name}' uploaded successfully")
            return "break"
        elif r.status_code == 409:
            self.output(f"WARNING: {endpoint_type} upload failed due to a conflict")
            return "break"
        elif r.status_code == 401:
            self.output(
                f"ERROR: {endpoint_type} upload failed due to permissions error"
            )
            return "break"

    def get_uapi_token(self, jamf_url, enc_creds):
        """get a token for the Jamf Pro API"""
        url = "{}/uapi/auth/tokens".format(jamf_url)
        r = self.nscurl("POST", url, enc_creds)
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
        """The UAPI doesn't have a name object, so we have to get the list of scripts 
        and parse the name to get the id """
        url = "{}/uapi/v1/{}".format(jamf_url, object_type)
        r = self.nscurl("GET", url, token)
        if r.status_code == 200:
            obj_id = 0
            for obj in r.output["results"]:
                self.output(obj, verbose_level=2)
                if obj["name"] == object_name:
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
                    f"Category upload attempt {count}", verbose_level=2,
                )
                r = self.nscurl("PUT", url, token, category_json_temp)
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

        # write the category. If updating an existing category, this reverts the name to its original.
        category_json = self.write_json_file(category_data)
        while True:
            count += 1
            self.output(
                f"Category upload attempt {count}", verbose_level=2,
            )
            method = "PUT" if obj_id else "POST"
            r = self.nscurl(method, url, token, category_json)
            # check HTTP response
            if self.status_check(r, "Category", category_name) == "break":
                break
            if count > 5:
                self.output("ERROR: Category creation did not succeed after 5 attempts")
                self.output(f"\nHTTP POST Response Code: {r.status_code}")
                raise ProcessorError("ERROR: Category upload failed ")
            sleep(10)

        # clean up temp files
        for file in category_json, category_json_temp:
            if os.path.exists(file):
                os.remove(file)

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
