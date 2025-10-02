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
import plistlib
import uuid

from time import sleep

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


class JamfComputerProfileUploaderBase(JamfUploaderBase):
    """Class for functions used to upload a computer configuration profile to Jamf"""

    def get_existing_uuid_and_identifier(self, jamf_url, obj_id, token):
        """return the existing UUID to ensure we don't change it"""
        # first grab the payload from the xml object
        obj_type = "os_x_configuration_profile"
        existing_plist = self.get_api_obj_value_from_id(
            jamf_url,
            obj_type,
            obj_id,
            "general/payloads",
            token=token,
        )

        # Jamf seems to sometimes export an empty key which plistlib considers invalid,
        # so let's remove this
        existing_plist = existing_plist.replace("<key/>", "")

        # make the xml pretty so we can see where the problem importing it is better
        existing_plist = self.pretty_print_xml(bytes(existing_plist, "utf-8"))

        self.output(
            f"Existing payload (type: {type(existing_plist)}):", verbose_level=2
        )
        self.output(existing_plist.decode("UTF-8"), verbose_level=2)

        # now extract the UUID from the existing payload
        existing_payload = plistlib.loads(existing_plist)
        self.output("Imported payload", verbose_level=2)
        self.output(existing_payload, verbose_level=2)
        existing_uuid = existing_payload["PayloadUUID"]
        self.output(f"Existing PayloadUUID found: {existing_uuid}")
        existing_identifier = existing_payload["PayloadIdentifier"]
        self.output(f"Existing PayloadIdentifier found: {existing_uuid}")

        return existing_uuid, existing_identifier

    def replace_identifiers_in_mobileconfig(
        self,
        mobileconfig_name,
        mobileconfig_contents,
        existing_uuid,
        existing_identifier,
    ):
        """replace UUID and identifier in mobileconfig"""
        self.output("Updating the UUIDs in the mobileconfig", verbose_level=2)
        mobileconfig_contents["PayloadDisplayName"] = mobileconfig_name
        mobileconfig_contents["PayloadIdentifier"] = existing_identifier
        mobileconfig_contents["PayloadUUID"] = existing_uuid
        return mobileconfig_contents

    def make_mobileconfig_from_payload(
        self,
        payload_path,
        payload_identifier,
        mobileconfig_name,
        organization,
        description,
        mobileconfig_uuid,
    ):
        """create a mobileconfig file using a payload file"""
        # import plist as text and replace any substitutable keys
        with open(payload_path, "rb") as file:
            payload_text = file.read()
        # substitute user-assignable keys (requires decode to string)
        payload_text = self.substitute_assignable_keys(
            (payload_text.decode()), xml_escape=True
        )
        # now convert to data (requires encode back to bytes...)
        mcx_preferences = plistlib.loads(str.encode(payload_text))

        self.output("Preferences contents:", verbose_level=2)
        self.output(mcx_preferences, verbose_level=2)

        # generate a random UUID for the payload
        payload_uuid = str(uuid.uuid4())

        # add the other keys required in the payload
        payload_contents = {
            "PayloadDisplayName": "Custom Settings",
            "PayloadIdentifier": payload_uuid,
            "PayloadOrganization": "JAMF Software",
            "PayloadType": "com.apple.ManagedClient.preferences",
            "PayloadUUID": payload_uuid,
            "PayloadVersion": 1,
            "PayloadContent": {
                payload_identifier: {
                    "Forced": [{"mcx_preference_settings": mcx_preferences}]
                }
            },
        }

        self.output("Payload contents:", verbose_level=2)
        self.output(payload_contents, verbose_level=2)

        # now write the mobileconfig file
        mobileconfig_data = {
            "PayloadDescription": description,
            "PayloadDisplayName": mobileconfig_name,
            "PayloadOrganization": organization,
            "PayloadRemovalDisallowed": True,
            "PayloadScope": "System",
            "PayloadType": "Configuration",
            "PayloadVersion": 1,
            "PayloadIdentifier": mobileconfig_uuid,
            "PayloadUUID": mobileconfig_uuid,
            "PayloadContent": [payload_contents],
        }

        self.output("Converting config data to plist")
        mobileconfig_plist = plistlib.dumps(mobileconfig_data)

        self.output("Mobileconfig contents:", verbose_level=2)
        self.output(mobileconfig_plist.decode("UTF-8"), verbose_level=2)

        return mobileconfig_plist

    def upload_mobileconfig(
        self,
        jamf_url,
        mobileconfig_name,
        description,
        category,
        mobileconfig_plist,
        computergroup_name,
        template_contents,
        profile_uuid,
        sleep_time,
        token,
        retain_scope=False,
        obj_id=0,
    ):
        """Update Configuration Profile metadata."""
        # remove newlines, tabs, leading spaces, and XML-escape the payload
        mobileconfig_plist = mobileconfig_plist.decode("UTF-8")
        mobileconfig_list = mobileconfig_plist.rsplit("\n")
        mobileconfig_list = [x.strip("\t") for x in mobileconfig_list]
        mobileconfig_list = [x.strip(" ") for x in mobileconfig_list]
        mobileconfig = "".join(mobileconfig_list)

        # substitute user-assignable keys
        replaceable_keys = {
            "mobileconfig_name": mobileconfig_name,
            "description": description,
            "category": category,
            "payload": mobileconfig,
            "computergroup_name": computergroup_name,
            "uuid": f"com.github.grahampugh.jamf-upload.{profile_uuid}",
        }

        # substitute user-assignable keys (escaping for XML)
        template_contents = self.substitute_limited_assignable_keys(
            template_contents, replaceable_keys, xml_escape=True
        )

        self.output(
            "Configuration Profile with intermediate substitution:", verbose_level=2
        )
        self.output(template_contents, verbose_level=2)

        # substitute user-assignable keys
        template_contents = self.substitute_assignable_keys(template_contents)

        self.output("Configuration Profile to be uploaded:", verbose_level=2)
        self.output(template_contents, verbose_level=2)

        # get existing scope if --retain-existing-scope is set
        object_type = "os_x_configuration_profile"
        if retain_scope and obj_id > 0:
            self.output("Substituting existing scope into template", verbose_level=1)
            existing_scope = self.get_existing_scope(
                jamf_url, object_type, obj_id, token
            )
            # substitute pre-existing scope
            template_contents = self.replace_scope(template_contents, existing_scope)

        self.output("Uploading Configuration Profile...")
        # write the template to temp file
        template_xml = self.write_temp_file(jamf_url, template_contents)

        # if we find an object ID we put, if not, we post
        url = f"{jamf_url}/{self.api_endpoints(object_type)}/id/{obj_id}"

        count = 0
        while True:
            count += 1
            self.output(
                f"Configuration Profile upload attempt {count}", verbose_level=1
            )
            request = "PUT" if obj_id else "POST"
            r = self.curl(
                request=request,
                url=url,
                token=token,
                data=template_xml,
            )

            # check HTTP response
            if (
                self.status_check(
                    r, "Configuration Profile", mobileconfig_name, request
                )
                == "break"
            ):
                break
            if count > 5:
                self.output(
                    "ERROR: Configuration Profile upload did not succeed after 5 attempts"
                )
                self.output(f"\nHTTP POST Response Code: {r.status_code}")
                break
            if int(sleep_time) > 30:
                sleep(int(sleep_time))
            else:
                sleep(30)

        return r

    def execute(self):
        """Upload a configuration profile"""
        jamf_url = self.env.get("JSS_URL").rstrip("/")
        jamf_user = self.env.get("API_USERNAME")
        jamf_password = self.env.get("API_PASSWORD")
        client_id = self.env.get("CLIENT_ID")
        client_secret = self.env.get("CLIENT_SECRET")
        profile_name = self.env.get("profile_name")
        payload = self.env.get("payload")
        mobileconfig = self.env.get("mobileconfig")
        identifier = self.env.get("identifier")
        template = self.env.get("profile_template")
        profile_category = self.env.get("profile_category")
        organization = self.env.get("organization")
        profile_description = self.env.get("profile_description")
        profile_computergroup = self.env.get("profile_computergroup")
        replace_profile = self.to_bool(self.env.get("replace_profile"))
        retain_scope = self.to_bool(self.env.get("retain_scope"))
        sleep_time = self.env.get("sleep")

        # clear any pre-existing summary result
        if "jamfcomputerprofileuploader_summary_result" in self.env:
            del self.env["jamfcomputerprofileuploader_summary_result"]

        profile_updated = False

        # substitute values in the profile name and category
        profile_name = self.substitute_assignable_keys(profile_name)
        profile_category = self.substitute_assignable_keys(profile_category)

        # handle files with no path
        if payload and "/" not in payload:
            found_payload = self.get_path_to_file(payload)
            if found_payload:
                payload = found_payload
            else:
                raise ProcessorError(f"ERROR: Payload file {payload} not found")
        if mobileconfig and "/" not in mobileconfig:
            found_mobileconfig = self.get_path_to_file(mobileconfig)
            if found_mobileconfig:
                mobileconfig = found_mobileconfig
            else:
                raise ProcessorError(
                    f"ERROR: mobileconfig file {mobileconfig} not found"
                )
        if template and "/" not in template:
            found_template = self.get_path_to_file(template)
            if found_template:
                template = found_template
            else:
                raise ProcessorError(f"ERROR: XML template file {template} not found")

        # if an unsigned mobileconfig file is supplied we can get the name, organization and
        # description from it, but allowing the values to be substituted by Input keys
        if mobileconfig:
            self.output(f"mobileconfig file supplied: {mobileconfig}")
            # check if the file is signed - COMMENTED OUT AS JAMF CURRENTLY STRIPS SIGNING VIA API
            # mobileconfig_file = self.unsign_signed_mobileconfig(mobileconfig)
            # quit if we get an unsigned profile back and we didn't select --unsign
            # if mobileconfig_file and not unsign:
            #     raise ProcessorError(
            #         "Signed profiles cannot be uploaded to Jamf Pro via the API. "
            #         "Use the GUI to upload the signed profile, or use --unsign to upload "
            #         "the profile with the signature removed."
            #     )

            # import mobileconfig
            with open(mobileconfig, "rb") as file:
                mobileconfig_plist = file.read()
                # substitute user-assignable keys (requires decode to string)
                mobileconfig_plist = str.encode(
                    self.substitute_assignable_keys(
                        (mobileconfig_plist.decode()), xml_escape=True
                    )
                )
                mobileconfig_contents = plistlib.loads(mobileconfig_plist)
            try:
                if profile_name:
                    mobileconfig_name = profile_name
                else:
                    mobileconfig_name = mobileconfig_contents["PayloadDisplayName"]
                self.output(f"Configuration Profile name: {mobileconfig_name}")
                self.output("Mobileconfig contents:", verbose_level=2)
                self.output(mobileconfig_plist.decode("UTF-8"), verbose_level=2)
            except KeyError as e:
                raise ProcessorError(
                    "ERROR: Invalid mobileconfig file supplied - cannot import"
                ) from e
            try:
                description = mobileconfig_contents["PayloadDescription"]
            except KeyError:
                description = ""
            try:
                organization = mobileconfig_contents["PayloadOrganization"]
            except KeyError:
                organization = ""

        # otherwise we are dealing with a payload plist and we need a few other bits of info
        else:
            if not profile_name:
                raise ProcessorError("ERROR: No profile name supplied - cannot import")
            if not payload:
                raise ProcessorError(
                    "ERROR: No path to payload file supplied - cannot import"
                )
            if not identifier:
                raise ProcessorError(
                    "ERROR: No identifier for mobileconfig supplied - cannot import"
                )
            mobileconfig_name = profile_name
            description = ""
            organization = ""

        # we provide a default template which has no category or scope
        if not template:
            template = "Jamf_Templates/ProfileTemplate-no-scope.xml"

        # automatically provide a description and organisation from the mobileconfig
        # if not provided in the options
        if not profile_description:
            if description:
                profile_description = description
            else:
                profile_description = (
                    "Config profile created by AutoPkg and JamfComputerProfileUploader"
                )
        if not organization:
            organization = "AutoPkg"

        # import profile template
        with open(template, "r", encoding="utf-8") as file:
            template_contents = file.read()

        # check for existing Configuration Profile
        self.output(f"Checking for existing '{mobileconfig_name}' on {jamf_url}")

        # get token using oauth or basic auth depending on the credentials given
        if jamf_url:
            token = self.handle_api_auth(
                jamf_url,
                jamf_user=jamf_user,
                password=jamf_password,
                client_id=client_id,
                client_secret=client_secret,
            )
        else:
            raise ProcessorError("ERROR: Jamf Pro URL not supplied")

        obj_type = "os_x_configuration_profile"
        obj_name = mobileconfig_name
        obj_id = self.get_api_obj_id_from_name(
            jamf_url,
            obj_name,
            obj_type,
            token=token,
        )
        if obj_id:
            self.output(
                f"Configuration Profile '{mobileconfig_name}' already exists: ID {obj_id}"
            )
            if replace_profile:
                self.output(
                    "Replacing existing Computer Profile as 'replace_profile' is set to True",
                    verbose_level=1,
                )
                # grab existing UUID from profile as it MUST match on the destination
                (
                    existing_uuid,
                    existing_identifier,
                ) = self.get_existing_uuid_and_identifier(jamf_url, obj_id, token)

                if mobileconfig:
                    # need to inject the existing payload identifier to prevent ghost profiles
                    mobileconfig_contents = self.replace_identifiers_in_mobileconfig(
                        mobileconfig_name,
                        mobileconfig_contents,
                        existing_uuid,
                        existing_identifier,
                    )
                    mobileconfig_plist = plistlib.dumps(mobileconfig_contents)
                else:
                    # generate the mobileconfig from the supplied payload
                    mobileconfig_plist = self.make_mobileconfig_from_payload(
                        payload,
                        identifier,
                        mobileconfig_name,
                        organization,
                        profile_description,
                        existing_uuid,
                    )

                # now upload the mobileconfig by generating an XML template
                if mobileconfig_plist:
                    self.upload_mobileconfig(
                        jamf_url,
                        mobileconfig_name,
                        profile_description,
                        profile_category,
                        mobileconfig_plist,
                        profile_computergroup,
                        template_contents,
                        existing_uuid,
                        sleep_time,
                        token,
                        retain_scope,
                        obj_id=obj_id,
                    )
                    profile_updated = True
                else:
                    self.output("A mobileconfig was not generated so cannot upload.")
            else:
                self.output(
                    (
                        "Not replacing existing Configuration Profile. "
                        "Override the replace_profile key to True to enforce."
                    ),
                    verbose_level=1,
                )
        else:
            self.output(
                f"Configuration Profile '{mobileconfig_name}' not found - will create"
            )
            new_uuid = str(uuid.uuid4())

            if not mobileconfig:
                # generate the mobileconfig from the supplied payload
                mobileconfig_plist = self.make_mobileconfig_from_payload(
                    payload,
                    identifier,
                    mobileconfig_name,
                    organization,
                    profile_description,
                    new_uuid,
                )

            # now upload the mobileconfig by generating an XML template
            if mobileconfig_plist:
                self.upload_mobileconfig(
                    jamf_url,
                    mobileconfig_name,
                    profile_description,
                    profile_category,
                    mobileconfig_plist,
                    profile_computergroup,
                    template_contents,
                    new_uuid,
                    sleep_time,
                    token,
                )
                profile_updated = True
            else:
                raise ProcessorError(
                    "A mobileconfig was not generated so cannot upload."
                )

        # output the summary
        self.env["profile_name"] = profile_name
        self.env["profile_updated"] = profile_updated
        if profile_updated:
            self.env["jamfcomputerprofileuploader_summary_result"] = {
                "summary_text": (
                    "The following configuration profiles were uploaded to "
                    "or updated in Jamf Pro:"
                ),
                "report_fields": ["mobileconfig_name", "profile_category"],
                "data": {
                    "mobileconfig_name": mobileconfig_name,
                    "profile_category": profile_category,
                },
            }
