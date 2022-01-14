#!/usr/local/autopkg/python

"""
JamfDockItemUploader processor for uploading a dock item to Jamf Pro using AutoPkg
    by Marcel Keßler based on G Pugh's great work
"""

import json
import os
import re
import subprocess
import uuid

import xml.etree.cElementTree as ET  # Everybody loves working with the classic api

from collections import namedtuple
from base64 import b64encode
from shutil import rmtree
from time import sleep
from urllib.parse import quote
from autopkglib import Processor, ProcessorError  # pylint: disable=import-error


class JamfDockItemUploader(Processor):
    """A processor for AutoPkg that will upload a dock item to a Jamf Cloud or on-prem server."""

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
        "dock_item_name": {
            "required": True,
            "description": "Name of Dock Item",
            "default": "",
        },
        "dock_item_type": {
            "required": True,
            "description": "Type of Dock Item - either 'App', 'File' or 'Folder'",
            "default": "App",
        },
        "dock_item_path": {
            "required": True,
            "description": "Path of Dock Item - e.g. 'file:///Applications/Safari.app/'",
            "default": "",
        },
        "replace_dock_item": {
            "required": False,
            "description": "Overwrite an existing dock item if True.",
            "default": False,
        },
    }

    output_variables = {
        "dock_item": {"description": "The created/updated dock item."},
        "jamfdockitemuploader_summary_result": {
            "description": "Description of interesting results.",
        },
    }

    # modified 'write_json_file'
    def write_xml_file(self, data, tmp_dir="/tmp/jamf_upload"):
        """dump some xml to a temporary file"""
        self.make_tmp_dir(tmp_dir)
        xml_tree = ET.ElementTree(data)
        tf = os.path.join(tmp_dir, f"jamf_upload_{str(uuid.uuid4())}.xml")
        xml_tree.write(tf)
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
            "--silent",
            "--show-error",
            "-X",
            method,
            "-D",
            headers_file,
            "--output",
            output_file,
            url,
        ]

        # authorisation if using Jamf Pro API or Classic API
        # if using uapi and we already have a token then we use the token for authorization
        if "uapi" in url and "tokens" not in url:
            curl_cmd.extend(["--header", f"authorization: Bearer {auth}"])
        # basic auth to obtain a token, or for classic API
        elif "uapi" in url or "JSSResource" in url or "dbfileupload" in url:
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
                if "uapi" in url or "JSSResource" in url or "dbfileupload" in url:
                    # jamf data upload requires upload-file argument
                    curl_cmd.extend(["--upload-file", data])
                else:
                    # slack requires data argument
                    curl_cmd.extend(["--data", data])
            # uapi and slack accepts json, classic API only accepts xml
            if "JSSResource" in url:
                curl_cmd.extend(["--header", "Content-type: application/xml"])
            else:
                curl_cmd.extend(["--header", "Content-type: application/json"])
        else:
            self.output(f"WARNING: HTTP method {method} not supported")

        # write session for jamf requests
        if "uapi" in url or "JSSResource" in url or "dbfileupload" in url:
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
            self.output(f"WARNING: {endpoint_type} '{obj_name}' upload failed")
            self.output(r.output, verbose_level=2)

    def get_api_obj_id_from_name(
        self, jamf_url, object_type, object_result_type, object_name, creds
    ):
        """Get the (classic) API object by name"""
        url = f"{jamf_url}/JSSResource/{object_type}/name/{quote(object_name)}"
        r = self.curl("GET", url, creds)
        if r.status_code == 200:
            obj_id = 0
            # Need to parse response, since curl function doesn't parse json on Classic API
            r_json = json.loads(r.output)
            if r_json[object_result_type]["name"] == object_name:
                obj_id = r_json[object_result_type]["id"]
            return obj_id

    def get_api_free_obj_id(self, jamf_url, object_type, object_result_type, creds):
        """
        Finds free id of given object_type by querying for all objects and iterate over the results...
        """
        url = f"{jamf_url}/JSSResource/{object_type}"
        r = self.curl("GET", url, creds)
        if r.status_code == 200:
            obj_id_list = []
            for obj in json.loads(r.output)[object_result_type]:
                obj_id_list.append(obj["id"])
            if not len(obj_id_list):
                # List of objects is empty -> use id 1
                return 1
            return max(obj_id_list) + 1

    def upload_dock_item(
        self,
        jamf_url,
        dock_item_name,
        dock_item_type,
        dock_item_path,
        obj_root,
        creds,
        obj_id,
        method,
    ):
        """Update dock item metadata."""

        # Build the xml (!) object
        # The classic api only supports xml requests
        dock_item_xml_root = ET.Element(obj_root)
        # Converted integer to text, to avoid TypeError while xml dumping
        ET.SubElement(dock_item_xml_root, "id").text = str(obj_id)
        ET.SubElement(dock_item_xml_root, "name").text = dock_item_name
        ET.SubElement(dock_item_xml_root, "type").text = dock_item_type
        ET.SubElement(dock_item_xml_root, "path").text = dock_item_path

        dock_item_xml = self.write_xml_file(dock_item_xml_root)

        url = "{}/JSSResource/dockitems/id/{}".format(jamf_url, obj_id)

        self.output("Uploading dock item..")

        count = 0
        while True:
            count += 1
            self.output(
                f"Dock Item upload attempt {count}",
                verbose_level=2,
            )
            r = self.curl(method, url, creds, dock_item_xml)
            # check HTTP response
            if self.status_check(r, "Dock Item", dock_item_name) == "break":
                break
            if count > 5:
                self.output(
                    "ERROR: Temporary dock item update did not succeed after 5 attempts"
                )
                self.output(f"\nHTTP POST Response Code: {r.status_code}")
                raise ProcessorError("ERROR: dock item upload failed ")
            sleep(10)

    def main(self):
        """Do the main thing here"""
        self.jamf_url = self.env.get("JSS_URL")
        self.jamf_user = self.env.get("API_USERNAME")
        self.jamf_password = self.env.get("API_PASSWORD")
        self.dock_item_name = self.env.get("dock_item_name")
        self.dock_item_type = self.env.get("dock_item_type")
        self.dock_item_path = self.env.get("dock_item_path")
        self.replace = self.env.get("replace_dock_item")
        # handle setting replace_pkg in overrides
        if not self.replace or self.replace == "False":
            self.replace = False

        # clear any pre-existing summary result
        if "jamfdockitemuploader_summary_result" in self.env:
            del self.env["jamfdockitemuploader_summary_result"]

        # encode the username and password into a basic auth b64 encoded string
        credentials = f"{self.jamf_user}:{self.jamf_password}"
        enc_creds_bytes = b64encode(credentials.encode("utf-8"))
        enc_creds = str(enc_creds_bytes, "utf-8")

        # Now process the dock item
        obj_id = 0
        method = "POST"

        # Check for existing dock item
        self.output(f"Checking for existing '{self.dock_item_name}' on {self.jamf_url}")
        obj_id = self.get_api_obj_id_from_name(
            self.jamf_url, "dockitems", "dock_item", self.dock_item_name, enc_creds
        )

        if obj_id and not self.replace:
            self.output(
                f"Dock Item '{self.dock_item_name}' already exists: ID {obj_id}"
            )
            self.output(
                "Not replacing existing dock item. Use replace_dock_item='True' to enforce."
            )
            return
        elif obj_id and self.replace:
            method = "PUT"
            self.output(
                f"Replacing existing dock item as 'replace_dock_item' is set to {self.replace}"
            )
        else:
            # Find a free obj_id...
            self.output(
                f"Found no existing dock item with given name '{self.dock_item_name}'. \
                Trying to find a free object id to create a new dock item...",
                verbose_level=1,
            )
            obj_id = self.get_api_free_obj_id(
                self.jamf_url, "dockitems", "dock_items", enc_creds
            )
            self.output(
                f"Found free id: {obj_id}",
                verbose_level=1,
            )

        # Upload dock item
        self.upload_dock_item(
            self.jamf_url,
            self.dock_item_name,
            self.dock_item_type,
            self.dock_item_path,
            "dock_item",
            enc_creds,
            obj_id,
            method,
        )

        # output the summary
        self.env["dock_item"] = self.dock_item_name
        self.env["jamfdockitemuploader_summary_result"] = {
            "summary_text": "The following dock items were created or updated in Jamf Pro:",
            "report_fields": [
                "dock_item_id",
                "dock_item_name",
                "dock_item_type",
                "dock_item_path",
            ],
            "data": {
                "dock_item_id": str(obj_id),
                "dock_item_name": self.dock_item_name,
                "dock_item_type": self.dock_item_type,
                "dock_item_path": self.dock_item_path,
            },
        }


if __name__ == "__main__":
    PROCESSOR = JamfDockItemUploader()
    PROCESSOR.execute_shell()