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

import os.path
import sys

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
        object_type = self.env.get("object_type")
        output_path = self.env.get("output_path")

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

        # Check for existing item
        self.output(f"Checking for existing '{object_name}' on {jamf_url}")

        obj_id = self.get_api_obj_id_from_name(
            jamf_url,
            object_name,
            object_type,
            token=token,
        )

        if obj_id:
            self.output(f"{object_type} '{object_name}' exists: ID {obj_id}")
            # get the XML
            raw_object = self.get_api_obj_contents_from_id(
                jamf_url, object_type, obj_id, obj_path="", token=token
            )
            self.output(raw_object, verbose_level=2)  # TEMP

            # parse the XML
            parsed_object = self.parse_downloaded_api_object(raw_object, object_type)
            # self.output(parsed_object, verbose_level=2)  # TEMP

            # dump the XML to file is output_path is specified
            if output_path:
                # check that parent folder exists
                if os.path.exists(os.path.dirname(output_path)):
                    try:
                        with open(output_path, "w", encoding="utf-8") as fp:
                            fp.write(parsed_object)
                        self.output(f"Wrote parsed object to {output_path}")
                    except IOError as e:
                        raise ProcessorError(
                            f"Could not write XML to {output_path} - {str(e)}"
                        ) from e
                else:
                    self.output(f"Cannot write to {output_path} as it doesn't exist")
        else:
            self.output(f"{object_type} '{object_name}' not found on {jamf_url}")

        # output the summary
        self.env["object_name"] = object_name
        self.env["object_id"] = obj_id
        self.env["object_type"] = object_type
        self.env["raw_object"] = raw_object or None
        self.env["parsed_object"] = parsed_object or None
        self.env["output_path"] = output_path
