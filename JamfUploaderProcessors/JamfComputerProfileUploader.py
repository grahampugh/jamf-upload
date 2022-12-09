#!/usr/local/autopkg/python

"""
JamfComputerProfileUploader processor for uploading computer configuration profiles
to Jamf Pro using AutoPkg
    by G Pugh
"""

import os
import sys
import plistlib
import subprocess
import uuid

from time import sleep
from autopkglib import ProcessorError  # pylint: disable=import-error  # noqa: E402

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfUploaderBase import JamfUploaderBase  # noqa: E402

__all__ = ["JamfComputerProfileUploader"]


class JamfComputerProfileUploader(JamfUploaderBase):
    description = (
        "A processor for AutoPkg that will upload a computer configuration "
        "profile to a Jamf Cloud or on-prem server."
    )
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
        "profile_name": {
            "required": False,
            "description": "Configuration Profile name",
            "default": "",
        },
        "payload": {
            "required": False,
            "description": "Path to Configuration Profile payload plist file",
        },
        "mobileconfig": {
            "required": False,
            "description": "Path to Configuration Profile mobileconfig file",
        },
        "identifier": {
            "required": False,
            "description": "Configuration Profile payload identifier",
        },
        "profile_template": {
            "required": False,
            "description": "Path to Configuration Profile XML template file",
        },
        "profile_category": {
            "required": False,
            "description": "a category to assign to the profile",
        },
        "organization": {
            "required": False,
            "description": "Organization to assign to the profile",
        },
        "profile_description": {
            "required": False,
            "description": "a description to assign to the profile",
        },
        "profile_computergroup": {
            "required": False,
            "description": "a computer group that will be scoped to the profile",
        },
        "unsign_profile": {
            "required": False,
            "description": (
                "Unsign a mobileconfig file prior to uploading "
                "if it is signed, if true."
            ),
            "default": False,
        },
        "replace_profile": {
            "required": False,
            "description": "overwrite an existing Configuration Profile if True.",
            "default": False,
        },
        "sleep": {
            "required": False,
            "description": "Pause after running this processor for specified seconds.",
            "default": "0",
        },
    }

    output_variables = {
        "jamfcomputerprofileuploader_summary_result": {
            "description": "Description of interesting results.",
        },
    }

    def get_existing_uuid_and_identifier(
        self, jamf_url, obj_id, enc_creds="", token=""
    ):
        """return the existing UUID to ensure we don't change it"""
        # first grab the payload from the xml object
        obj_type = "os_x_configuration_profile"
        existing_plist = self.get_api_obj_value_from_id(
            jamf_url,
            obj_type,
            obj_id,
            "general/payloads",
            enc_creds=enc_creds,
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

    def replace_uuid_and_identifier_in_mobileconfig(
        self, mobileconfig_contents, existing_uuid, existing_identifier
    ):
        mobileconfig_contents["PayloadIdentifier"] = existing_identifier
        mobileconfig_contents["PayloadUUID"] = existing_uuid
        with open(self.mobileconfig, "wb") as file:
            plistlib.dump(mobileconfig_contents, file)

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

    def unsign_signed_mobileconfig(self, mobileconfig_plist):
        """checks if profile is signed. This is necessary because Jamf cannot
        upload a signed profile, so we either need to unsign it, or bail"""
        output_path = os.path.join("/tmp", str(uuid.uuid4()))
        cmd = [
            "/usr/bin/security",
            "cms",
            "-D",
            "-i",
            mobileconfig_plist,
            "-o",
            output_path,
        ]
        self.output(cmd, verbose_level=1)

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        _, err = proc.communicate()
        if os.path.exists(output_path) and os.stat(output_path).st_size > 0:
            self.output(f"Profile is signed. Unsigned profile at {output_path}")
            return output_path
        elif err:
            self.output("Profile is not signed.")
            self.output(err, verbose_level=2)

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
        obj_id=0,
        enc_creds="",
        token="",
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

        self.output("Uploading Configuration Profile..")
        # write the template to temp file
        template_xml = self.write_temp_file(template_contents)

        # if we find an object ID we put, if not, we post
        object_type = "os_x_configuration_profile"
        url = "{}/{}/id/{}".format(jamf_url, self.api_endpoints(object_type), obj_id)

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
                enc_creds=enc_creds,
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
            if int(self.sleep) > 30:
                sleep(int(self.sleep))
            else:
                sleep(30)

        return r

    def main(self):
        """Do the main thing here"""
        self.jamf_url = self.env.get("JSS_URL")
        self.jamf_user = self.env.get("API_USERNAME")
        self.jamf_password = self.env.get("API_PASSWORD")
        self.profile_name = self.env.get("profile_name")
        self.payload = self.env.get("payload")
        self.mobileconfig = self.env.get("mobileconfig")
        self.identifier = self.env.get("identifier")
        self.template = self.env.get("profile_template")
        self.profile_category = self.env.get("profile_category")
        self.organization = self.env.get("organization")
        self.profile_description = self.env.get("profile_description")
        self.profile_computergroup = self.env.get("profile_computergroup")
        self.replace = self.env.get("replace_profile")
        self.sleep = self.env.get("sleep")
        self.unsign = self.env.get("unsign_profile")
        # handle setting unsign in overrides
        if not self.unsign or self.unsign == "False":
            self.unsign = False
        # handle setting replace in overrides
        if not self.replace or self.replace == "False":
            self.replace = False

        # clear any pre-existing summary result
        if "jamfcomputerprofileuploader_summary_result" in self.env:
            del self.env["jamfcomputerprofileuploader_summary_result"]

        profile_updated = False

        # handle files with no path
        if self.payload and "/" not in self.payload:
            found_payload = self.get_path_to_file(self.payload)
            if found_payload:
                self.payload = found_payload
            else:
                raise ProcessorError(f"ERROR: Payload file {self.payload} not found")
        if self.mobileconfig and "/" not in self.mobileconfig:
            found_mobileconfig = self.get_path_to_file(self.mobileconfig)
            if found_mobileconfig:
                self.mobileconfig = found_mobileconfig
            else:
                raise ProcessorError(
                    f"ERROR: mobileconfig file {self.mobileconfig} not found"
                )
        if self.template and "/" not in self.template:
            found_template = self.get_path_to_file(self.template)
            if found_template:
                self.template = found_template
            else:
                raise ProcessorError(
                    f"ERROR: XML template file {self.template} not found"
                )

        # if an unsigned mobileconfig file is supplied we can get the name, organization and
        # description from it, but allowing the values to be substituted by Input keys
        if self.mobileconfig:
            self.output(f"mobileconfig file supplied: {self.mobileconfig}")
            # check if the file is signed
            mobileconfig_file = self.unsign_signed_mobileconfig(self.mobileconfig)
            # quit if we get an unsigned profile back and we didn't select --unsign
            if mobileconfig_file and not self.unsign:
                raise ProcessorError(
                    "Signed profiles cannot be uploaded to Jamf Pro via the API. "
                    "Use the GUI to upload the signed profile, or use --unsign to upload "
                    "the profile with the signature removed."
                )

            # import mobileconfig
            with open(self.mobileconfig, "rb") as file:
                mobileconfig_plist = file.read()
                # substitute user-assignable keys (requires decode to string)
                mobileconfig_plist = str.encode(
                    self.substitute_assignable_keys(
                        (mobileconfig_plist.decode()), xml_escape=True
                    )
                )
                mobileconfig_contents = plistlib.loads(mobileconfig_plist)
            try:
                mobileconfig_name = mobileconfig_contents["PayloadDisplayName"]
                self.output(f"Configuration Profile name: {mobileconfig_name}")
                self.output("Mobileconfig contents:", verbose_level=2)
                self.output(mobileconfig_plist.decode("UTF-8"), verbose_level=2)
            except KeyError:
                raise ProcessorError(
                    "ERROR: Invalid mobileconfig file supplied - cannot import"
                )
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
            if not self.profile_name:
                raise ProcessorError("ERROR: No profile name supplied - cannot import")
            if not self.payload:
                raise ProcessorError(
                    "ERROR: No path to payload file supplied - cannot import"
                )
            if not self.identifier:
                raise ProcessorError(
                    "ERROR: No identifier for mobileconfig supplied - cannot import"
                )
            mobileconfig_name = self.profile_name
            description = ""
            organization = ""

        # we provide a default template which has no category or scope
        if not self.template:
            self.template = "Jamf_Templates/ProfileTemplate-no-scope.xml"

        # automatically provide a description and organisation from the mobileconfig
        # if not provided in the options
        if not self.profile_description:
            if description:
                self.profile_description = description
            else:
                self.profile_description = (
                    "Config profile created by AutoPkg and JamfComputerProfileUploader"
                )
        if not self.organization:
            if organization:
                self.organization = organization
            else:
                organization = "AutoPkg"
                self.organization = organization

        # import profile template
        with open(self.template, "r") as file:
            template_contents = file.read()

        # check for existing Configuration Profile
        self.output(f"Checking for existing '{mobileconfig_name}' on {self.jamf_url}")

        # obtain the relevant credentials
        token, send_creds, _ = self.handle_classic_auth(
            self.jamf_url, self.jamf_user, self.jamf_password
        )

        obj_type = "os_x_configuration_profile"
        obj_name = mobileconfig_name
        obj_id = self.get_api_obj_id_from_name(
            self.jamf_url,
            obj_name,
            obj_type,
            enc_creds=send_creds,
            token=token,
        )
        if obj_id:
            self.output(
                f"Configuration Profile '{mobileconfig_name}' already exists: ID {obj_id}"
            )
            if self.replace:
                # grab existing UUID from profile as it MUST match on the destination
                (
                    existing_uuid,
                    existing_identifier,
                ) = self.get_existing_uuid_and_identifier(
                    self.jamf_url, obj_id, enc_creds=send_creds, token=token
                )
                if self.mobileconfig:
                    # need to inject the existing payload identifier to prevent ghost profiles
                    self.replace_uuid_and_identifier_in_mobileconfig(
                        mobileconfig_contents, existing_uuid, existing_identifier
                    )
                    with open(self.mobileconfig, "rb") as file:
                        mobileconfig_plist = file.read()
                else:
                    # generate the mobileconfig from the supplied payload
                    mobileconfig_plist = self.make_mobileconfig_from_payload(
                        self.payload,
                        self.identifier,
                        mobileconfig_name,
                        self.organization,
                        self.profile_description,
                        existing_uuid,
                    )

                # now upload the mobileconfig by generating an XML template
                if mobileconfig_plist:
                    self.upload_mobileconfig(
                        self.jamf_url,
                        mobileconfig_name,
                        self.profile_description,
                        self.profile_category,
                        mobileconfig_plist,
                        self.profile_computergroup,
                        template_contents,
                        existing_uuid,
                        obj_id=obj_id,
                        enc_creds=send_creds,
                        token=token,
                    )
                    profile_updated = True
                else:
                    self.output("A mobileconfig was not generated so cannot upload.")
            else:
                self.output(
                    "Not replacing existing Configuration Profile. "
                    "Override the replace_profile key to True to enforce."
                )
        else:
            self.output(
                f"Configuration Profile '{mobileconfig_name}' not found - will create"
            )
            new_uuid = str(uuid.uuid4())

            if not self.mobileconfig:
                # generate the mobileconfig from the supplied payload
                mobileconfig_plist = self.make_mobileconfig_from_payload(
                    self.payload,
                    self.identifier,
                    mobileconfig_name,
                    self.organization,
                    self.profile_description,
                    new_uuid,
                )

            # now upload the mobileconfig by generating an XML template
            if mobileconfig_plist:
                self.upload_mobileconfig(
                    self.jamf_url,
                    mobileconfig_name,
                    self.profile_description,
                    self.profile_category,
                    mobileconfig_plist,
                    self.profile_computergroup,
                    template_contents,
                    new_uuid,
                    enc_creds=send_creds,
                    token=token,
                )
                profile_updated = True
            else:
                raise ProcessorError(
                    "A mobileconfig was not generated so cannot upload."
                )

        # output the summary
        self.env["profile_name"] = self.profile_name
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
                    "profile_category": self.profile_category,
                },
            }


if __name__ == "__main__":
    PROCESSOR = JamfComputerProfileUploader()
    PROCESSOR.execute_shell()
