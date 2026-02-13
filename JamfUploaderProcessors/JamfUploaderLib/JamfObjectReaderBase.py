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
    """Class for functions used to read a generic API object in Jamf"""

    def write_output_file(
        self,
        object_type,
        output_dir,
        object_content,
        subdomain,
        object_subtype=None,
        n=None,
    ):
        """output the file"""

        # get api type
        api_type = self.api_type(object_type)

        # construct the filename
        if api_type == "classic":
            filetype = "xml"
        else:
            filetype = "json"

        if object_type == "account":
            if object_subtype == "users":
                object_type = "account_user"
            else:
                object_type = "account_group"
            output_filename = f"{subdomain}-accounts-{object_subtype}-{n}.{filetype}"
        elif n is not None and n != "":
            self.output(f"Object name is {n}", verbose_level=3)
            # escape slashes in the object name
            n = n.replace("/", "_").replace("\\", "_")
            n = n.replace(":", "_")  # also replace colons with underscores
            output_filename = (
                f"{subdomain}-{self.object_list_types(object_type)}-{n}.{filetype}"
            )
        else:
            output_filename = (
                f"{subdomain}-{self.object_list_types(object_type)}.{filetype}"
            )

        file_path = os.path.join(output_dir, output_filename)
        # check that parent folder exists
        if os.path.isdir(output_dir):
            try:
                if isinstance(object_content, dict):
                    # convert dict to JSON string
                    object_content = json.dumps(
                        object_content, indent=4, ensure_ascii=False
                    )
                elif isinstance(object_content, ET.Element):
                    # convert XML Element to pretty-printed string
                    object_content = self.pretty_print_xml(
                        ET.tostring(object_content)
                    ).decode("UTF-8")
                elif isinstance(object_content, str):
                    # ensure it's a string
                    object_content = str(object_content)
                with open(file_path, "w", encoding="utf-8") as fp:
                    fp.write(object_content)
                self.output(f"Wrote object to {file_path}")
                return output_filename, file_path
            except IOError as e:
                raise ProcessorError(
                    f"Could not write output to {file_path} - {str(e)}"
                ) from e
        else:
            raise ProcessorError(
                f"Cannot write to {output_dir} as the folder doesn't exist"
            )

    def get_payload_filetype(self, object_type, parsed_object):
        """Get the payload filetype based on the object type"""
        # for certain types we also want to extract the payload
        payload_filetype = "sh"
        payload = None
        if object_type == "computer_extension_attribute" or object_type == "script":
            payload = json.loads(parsed_object)["scriptContents"]
            if payload is not None:
                # determine the script type
                if "python" in payload.partition("\n")[0]:
                    payload_filetype = "py"
        elif (
            object_type == "os_x_configuration_profile"
            or object_type == "configuration_profile"
        ):
            try:
                object_xml = ET.fromstring(parsed_object)
            except ET.ParseError as xml_error:
                raise ProcessorError from xml_error
            payload_value = object_xml.find("general/payloads")
            payload = self.pretty_print_xml(payload_value.text.encode()).decode("UTF-8")
            payload_filetype = "mobileconfig"

        return payload, payload_filetype

    def write_payload_file(
        self, output_dir, payload, payload_filetype, subdomain, object_type, n=None
    ):
        """Write the payload to a file"""

        try:
            payload_output_filename = (
                f"{subdomain}-{self.object_list_types(object_type)}-{n}"
                f".{payload_filetype}".replace(".sh.sh", ".sh").replace(".py.py", ".py")
            )
            # ensure the filename is safe from slashes
            payload_output_filename = payload_output_filename.replace("/", "_").replace(
                "\\", "_"
            )
            # also replace colons with underscores
            payload_output_filename = payload_output_filename.replace(":", "_")
            payload_file_path = os.path.join(output_dir, payload_output_filename)
            with open(payload_file_path, "w", encoding="utf-8") as fp:
                fp.write(payload)
            self.output(f"Wrote {object_type} payload to {payload_file_path}")

        except IOError as e:
            raise ProcessorError(
                f"Could not write output to {payload_file_path} - {str(e)}"
            ) from e

        return payload_output_filename, payload_file_path

    def execute(self):
        """Upload an API object"""
        jamf_url = self.env.get("JSS_URL").rstrip("/")
        jamf_user = self.env.get("API_USERNAME")
        jamf_password = self.env.get("API_PASSWORD")
        client_id = self.env.get("CLIENT_ID")
        client_secret = self.env.get("CLIENT_SECRET")
        object_id = self.env.get("object_id")
        object_name = self.env.get("object_name")
        all_objects = self.to_bool(self.env.get("all_objects"))
        list_only = self.to_bool(self.env.get("list_only"))
        object_type = self.env.get("object_type")
        output_dir = self.env.get("output_dir")
        settings_key = self.env.get("settings_key")
        uuid = self.env.get("uuid")
        elements_to_remove = self.env.get("elements_to_remove")
        elements_to_remove = (
            [elements_to_remove] if isinstance(elements_to_remove, str) else []
        )
        elements_to_retain = self.env.get("elements_to_retain")
        elements_to_retain = (
            [elements_to_retain] if isinstance(elements_to_retain, str) else []
        )

        # check for required variables
        if not all_objects and not list_only and not "_settings" in object_type:
            if not object_name and not object_id:
                raise ProcessorError(
                    "ERROR: no object name or ID provided, and all_objects is False"
                )
        if not object_type:
            raise ProcessorError("ERROR: no object type provided")

        # clear any pre-existing summary result
        if "jamfobjectreader_summary_result" in self.env:
            del self.env["jamfobjectreader_summary_result"]

        # now start the process of reading the object
        # we need to substitute the values in the computer group name now to
        # account for version strings in the name
        # substitute user-assignable keys
        object_name = self.substitute_assignable_keys(object_name)

        # get token using oauth or basic auth depending on the credentials given
        if jamf_url:
            # determine which token we need based on object type. classic and jpapi types use handle_api_auth, platform type uses handle_platform_api_auth
            api_type = self.api_type(object_type)
            self.output(f"API type for {object_type} is {api_type}", verbose_level=3)
            if api_type == "platform":
                token = self.handle_platform_api_auth(
                    jamf_url,
                    client_id=client_id,
                    client_secret=client_secret,
                )
            else:
                token = self.handle_api_auth(
                    jamf_url,
                    jamf_user=jamf_user,
                    password=jamf_password,
                    client_id=client_id,
                    client_secret=client_secret,
                )
        else:
            raise ProcessorError("ERROR: Jamf Pro URL not supplied")

        # get instance name from URL
        host = jamf_url.partition("://")[2]
        subdomain = host.partition(".")[0]

        # declare object list
        object_list = []

        # declare some empty variables
        output_filename = ""
        file_path = ""
        settings_value = ""
        raw_object = ""
        parsed_object = ""
        payload = ""
        payload_output_filename = ""
        payload_file_path = ""

        # declare name key
        namekey = self.get_namekey(object_type)
        namekey_path = self.get_namekey_path(object_type, namekey)
        self.output(f"Name key for {object_type} is {namekey}", verbose_level=3)

        # if requesting all objects we need to generate a list of all to iterate through
        if all_objects or list_only:
            self.output(f"Getting all {object_type} objects from {jamf_url}")
            object_list = self.get_all_api_objects(
                jamf_url, object_type, uuid=uuid, token=token, namekey=namekey
            )
            if list_only:
                self.env["object_list"] = object_list
                if output_dir:
                    # write the list to a file
                    output_filename = (
                        f"{subdomain}-{self.object_list_types(object_type)}.json"
                    )
                    file_path = os.path.join(output_dir, output_filename)
                    try:
                        with open(file_path, "w", encoding="utf-8") as fp:
                            json.dump(object_list, fp, indent=4)
                        self.output(
                            f"Wrote object list to file {file_path}", verbose_level=1
                        )
                    except IOError:
                        # try to create the directory if it doesn't exist
                        if not os.path.isdir(output_dir):
                            try:
                                os.makedirs(output_dir)
                                self.output(
                                    f"Created output directory {output_dir}",
                                    verbose_level=1,
                                )
                                with open(file_path, "w", encoding="utf-8") as fp:
                                    json.dump(object_list, fp, indent=4)
                                self.output(
                                    f"Wrote object list to file {file_path}",
                                    verbose_level=1,
                                )
                            except OSError as dir_error:
                                raise ProcessorError(
                                    f"Could not create output directory {output_dir} - {str(dir_error)}"
                                ) from dir_error
            # we really need an output path for all_objects, so exit if not provided
            if not output_dir:
                raise ProcessorError("ERROR: no output path provided")

        elif object_id:
            if object_name:
                self.output(
                    f"Object ID {object_id} and name {object_name} provided, "
                    "using object ID to get object contents"
                )
            else:
                self.output(
                    f"Object ID {object_id} provided, using object ID to get object contents"
                )
                object_name = self.get_api_object_value_from_id(
                    jamf_url,
                    object_type=object_type,
                    object_id=object_id,
                    object_path=namekey_path,
                    token=token,
                )
            object_list = [{"id": object_id, namekey: object_name}]
            self.output(f"Name: {object_name}", verbose_level=3)

        elif object_name:
            # Check for existing item
            self.output(f"Checking for existing '{object_name}' on {jamf_url}")

            # exception for accounts
            if object_type == "account":
                # for accounts we need to split the object list into users and groups
                for object_subtype in ["users", "groups"]:

                    # get the object
                    if object_subtype == "users":
                        object_type = "account_user"
                    else:
                        object_type = "account_group"

                    object_id = self.get_api_object_id_from_name(
                        jamf_url,
                        object_type=object_type,
                        object_name=object_name,
                        token=token,
                        filter_name=namekey,
                    )
                    if object_id:
                        break
            else:
                # some group object types have a different ID key
                id_key = self.get_idkey(object_type)

                object_id = self.get_api_object_id_from_name(
                    jamf_url,
                    object_type=object_type,
                    object_name=object_name,
                    token=token,
                    filter_name=namekey,
                    id_key=id_key,
                )

            if object_id:
                self.output(
                    f"{object_type} '{object_name}' exists: ID {object_id}",
                    verbose_level=2,
                )
                object_list = [{"id": object_id, namekey: object_name}]
            else:
                self.output(f"{object_type} '{object_name}' not found on {jamf_url}")

        elif "_settings" in object_type:
            object_content = self.get_settings_object(jamf_url, object_type, token)
            if object_content:
                self.output(
                    f"{object_type} content on {jamf_url}: {object_content}",
                    verbose_level=3,
                )
                if settings_key:
                    try:
                        settings_value = object_content[settings_key]
                    except TypeError:
                        settings_object = ET.fromstring(object_content)
                        settings_value = settings_object.find(settings_key).text
                    except KeyError as e:
                        raise ProcessorError(
                            f"ERROR: Settings key '{settings_key}' not found in {object_type} content"
                        ) from e
                    if settings_value:
                        self.output(
                            f"Settings key '{settings_key}' value: {settings_value}",
                            verbose_level=1,
                        )
                    else:
                        self.output(
                            f"Settings key '{settings_key}' not found in {object_type} content",
                            verbose_level=1,
                        )
                # dump the object to file if output_dir is specified
                if output_dir:
                    object_content, file_path = self.write_output_file(
                        object_type,
                        output_dir,
                        object_content,
                        subdomain,
                    )

            else:
                self.output(f"{object_type} has no content on {jamf_url}")

        if not list_only:
            # now iterate through all the objects
            self.output(
                f"Iterating through {object_type} objects in {jamf_url}",
                verbose_level=1,
            )
            # exception for accounts
            if object_type == "account":
                # for accounts we need to split the object list into users and groups
                for object_subtype in ["users", "groups"]:
                    self.output(
                        f"Iterating through {object_subtype} in {object_type} object list",
                        verbose_level=1,
                    )
                    for obj in object_list[object_subtype]:
                        i = obj["id"]
                        n = obj["name"]
                        raw_object = ""
                        parsed_object = ""
                        payload = ""

                        # get the object
                        if object_subtype == "users":
                            object_type = "account_user"
                        else:
                            object_type = "account_group"
                        raw_object = self.get_api_object_contents_from_id(
                            jamf_url, object_type, i, object_path="", token=token
                        )

                        # parse the object
                        parsed_object = self.parse_downloaded_api_object(
                            raw_object,
                            object_type,
                            elements_to_remove,
                            elements_to_retain,
                        )

                        self.output(parsed_object, verbose_level=2)

                        # dump the object to file if output_dir is specified

                        if output_dir:
                            object_content, file_path = self.write_output_file(
                                object_type,
                                output_dir,
                                parsed_object,
                                subdomain,
                                object_subtype=object_subtype,
                                n=n,
                            )
            else:
                # for all other object types we can just iterate through the list
                # and get the object contents
                for obj in object_list:
                    i = obj["id"]
                    if object_name:
                        # if we have an object name, use that
                        n = object_name
                    elif object_id and len(object_list) == 1:
                        # if we have an object ID use the ID in the filename if only one object
                        n = object_id
                    else:
                        # otherwise use the name key from the object
                        if namekey not in obj:
                            raise ProcessorError(
                                f"ERROR: {namekey} not found in object {obj}"
                            )
                        n = obj[namekey]
                    raw_object = ""
                    parsed_object = ""
                    payload = ""

                    # get the object
                    raw_object = self.get_api_object_contents_from_id(
                        jamf_url, object_type, i, object_path="", token=token
                    )

                    # parse the object
                    parsed_object = self.parse_downloaded_api_object(
                        raw_object, object_type, elements_to_remove, elements_to_retain
                    )

                    self.output("Raw object:", verbose_level=3)
                    self.output(parsed_object, verbose_level=3)

                    # dump the object to file if output_dir is specified
                    if output_dir:
                        object_content, file_path = self.write_output_file(
                            object_type,
                            output_dir,
                            parsed_object,
                            subdomain,
                            object_subtype=None,
                            n=n,
                        )

                        payload, payload_filetype = self.get_payload_filetype(
                            object_type, parsed_object
                        )

                        if payload:
                            payload_output_filename, payload_file_path = (
                                self.write_payload_file(
                                    output_dir,
                                    payload,
                                    payload_filetype,
                                    subdomain,
                                    object_type,
                                    n=n,
                                )
                            )
                            self.env["payload_output_filename"] = (
                                payload_output_filename
                            )
                            self.env["payload_file_path"] = payload_file_path

        self.env["object_type"] = object_type
        self.env["output_dir"] = output_dir
        self.env["file_path"] = file_path
        if "_settings" in object_type and object_content:
            self.env["raw_object"] = str(object_content)
            self.env["settings_key"] = settings_key
            self.env["settings_value"] = str(settings_value)
            self.output(
                f"Settings key {settings_key} value {settings_value} exported to env",
                verbose_level=3,
            )
        elif not all_objects and not list_only:
            self.env["output_filename"] = output_filename
            self.env["output_path"] = file_path
            self.env["object_name"] = object_name
            self.env["object_id"] = str(object_id)
            self.env["raw_object"] = str(raw_object)
            self.env["parsed_object"] = str(parsed_object)

        # output the summary
        self.env["jamfobjectreader_summary_result"] = {
            "summary_text": "The following objects were outputted in Jamf Pro:",
            "report_fields": ["file_path"],
            "data": {
                "file_path": file_path,
            },
        }
