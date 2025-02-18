#!/usr/local/autopkg/python
# pylint: disable=invalid-name

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
import os.path
import sys
import xml.etree.ElementTree as ET

from xml.sax.saxutils import unescape

from autopkglib import (  # pylint: disable=import-error
    ProcessorError,
)

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderBase import (  # pylint: disable=import-error, wrong-import-position
    JamfUploaderBase,
)


class JamfObjectReaderBase(JamfUploaderBase):
    """Class for functions used to read a generic Classic API object in Jamf"""

    def execute(self):
        """Upload an API object"""
        jamf_url = self.env.get("JSS_URL").rstrip("/")
        jamf_user = self.env.get("API_USERNAME")
        jamf_password = self.env.get("API_PASSWORD")
        client_id = self.env.get("CLIENT_ID")
        client_secret = self.env.get("CLIENT_SECRET")
        object_name = self.env.get("object_name")
        all_objects = self.env.get("all_objects")
        object_type = self.env.get("object_type")
        output_path = self.env.get("output_path")

        # handle setting true/false variables in overrides
        if not all_objects or all_objects == "False":
            all_objects = False

        # clear any pre-existing summary result
        if "jamfclassicapiobjectreader_summary_result" in self.env:
            del self.env["jamfclassicapiobjectreader_summary_result"]

        # now start the process of reading the object

        # get token using oauth or basic auth depending on the credentials given
        if jamf_url and client_id and client_secret:
            token = self.handle_oauth(jamf_url, client_id, client_secret)
        elif jamf_url and jamf_user and jamf_password:
            token = self.handle_api_auth(jamf_url, jamf_user, jamf_password)
        else:
            raise ProcessorError("ERROR: Credentials not supplied")

        # declare object list
        object_list = []

        # declare name key
        name_key = "name"
        if (
            object_type == "computer_prestage"
            or object_type == "mobile_device_prestage"
        ):
            name_key = "displayName"

        # if requesting all objects we need to generate a list of all to iterate through
        if object_name:
            # Check for existing item
            self.output(f"Checking for existing '{object_name}' on {jamf_url}")

            obj_id = self.get_api_obj_id_from_name(
                jamf_url,
                object_name,
                object_type,
                token=token,
                filter_name=name_key,
            )

            if obj_id:
                self.output(
                    f"{object_type} '{object_name}' exists: ID {obj_id}",
                    verbose_level=2,
                )
                object_list = [{"id": obj_id, name_key: object_name}]
            else:
                self.output(f"{object_type} '{object_name}' not found on {jamf_url}")
                return
        elif all_objects:
            object_list = self.get_all_api_objects(jamf_url, object_type, token)
            # we really need an output path for all_objects, so exit if not provided
            if not output_path:
                self.output("ERROR: no output path provided")
                return

        # now iterate through all the objects
        for obj in object_list:
            i = obj["id"]
            n = obj[name_key]

            # get the object
            raw_object = self.get_api_obj_contents_from_id(
                jamf_url, object_type, i, obj_path="", token=token
            )

            # parse the object
            parsed_object = self.parse_downloaded_api_object(raw_object, object_type)

            # for certain types we also want to extract the payload
            payload = ""
            payload_filetype = "sh"
            if object_type == "computer_extension_attribute":
                payload = json.loads(parsed_object)["scriptContents"]
                # determine the script type
                if "python" in payload.partition("\n")[0]:
                    payload_filetype = "py"
            elif object_type == "script":
                payload = json.loads(parsed_object)["scriptContents"]
            elif (
                object_type == "os_x_configuration_profile"
                or object_type == "configuration_profile"
            ):
                try:
                    obj_xml = ET.fromstring(parsed_object)
                except ET.ParseError as xml_error:
                    raise ProcessorError from xml_error
                payload_value = obj_xml.find("general/payloads")
                payload = self.pretty_print_xml(payload_value.text.encode()).decode(
                    "UTF-8"
                )
                payload_filetype = "mobileconfig"

            # dump the object to file is output_path is specified
            if output_path:
                # construct the filename
                if "JSSResource" in self.api_endpoints(object_type):
                    filetype = "xml"
                else:
                    filetype = "json"
                # get instance name from URL
                host = jamf_url.partition("://")[2]
                subdomain = host.partition(".")[0]

                output_filename = (
                    f"{subdomain}-{self.object_list_types(object_type)}-{n}.{filetype}"
                )
                file_path = os.path.join(output_path, output_filename)
                # check that parent folder exists
                if os.path.isdir(output_path):
                    try:
                        with open(file_path, "w", encoding="utf-8") as fp:
                            fp.write(parsed_object)
                        self.output(f"Wrote parsed object to {file_path}")
                        # also output the payload if appropriate
                        if payload:
                            payload_output_filename = f"{subdomain}-{self.object_list_types(object_type)}-{n}.{payload_filetype}"
                            payload_file_path = os.path.join(
                                output_path, payload_output_filename
                            )
                            with open(payload_file_path, "w", encoding="utf-8") as fp:
                                fp.write(payload)
                            self.output(
                                f"Wrote {object_type} payload to {payload_file_path}"
                            )

                    except IOError as e:
                        raise ProcessorError(
                            f"Could not write output to {file_path} - {str(e)}"
                        ) from e
                else:
                    self.output(
                        f"Cannot write to {output_path} as the folder doesn't exist"
                    )

        # output the summary
        self.env["object_type"] = object_type
        self.env["output_path"] = output_path
        if not all_objects:
            self.env["object_name"] = object_name
            self.env["object_id"] = obj_id
            self.env["raw_object"] = str(raw_object) or None
            self.env["parsed_object"] = str(parsed_object) or None
