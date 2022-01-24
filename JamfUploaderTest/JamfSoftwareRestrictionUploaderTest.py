#!/usr/local/autopkg/python

"""
JamfSoftwareRestrictionUploaderTest processor for uploading computer restrictions
to Jamf Pro using AutoPkg
    by G Pugh
"""

import re
import subprocess

from time import sleep
from xml.sax.saxutils import escape
from JamfUploaderLib.JamfUploaderBase import JamfUploaderBase
from autopkglib import (
    ProcessorError,
)  # pylint: disable=import-error


class JamfSoftwareRestrictionUploaderTest(JamfUploaderBase):
    """A processor for AutoPkg that will upload an item to a Jamf Cloud or on-prem server."""

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
        "restriction_name": {
            "required": True,
            "description": "Software Restriction name",
            "default": "",
        },
        "restriction_template": {
            "required": True,
            "description": "Path to Software Restriction XML template file",
            "default": "RestrictionTemplate-no-scope.xml",
        },
        "restriction_computergroup": {
            "required": False,
            "description": "A single computer group to add to the scope.",
            "default": "",
        },
        "process_name": {
            "required": False,
            "description": "Process name to restrict",
        },
        "display_message": {
            "required": False,
            "description": "Message to display to users when the restriction is invoked",
        },
        "match_exact_process_name": {
            "required": False,
            "description": "Match only the exact process name if True",
            "default": False,
        },
        "restriction_send_notification": {
            "required": False,
            "description": "Send a notification when the restriction is invoked if True",
            "default": False,
        },
        "kill_process": {
            "required": False,
            "description": "Kill the process when the restriction is invoked if True",
            "default": False,
        },
        "delete_executable": {
            "required": False,
            "description": "Delete the executable when the restriction is invoked if True",
            "default": False,
        },
        "replace_restriction": {
            "required": False,
            "description": "overwrite an existing Software Restriction if True",
            "default": False,
        },
    }

    output_variables = {
        "jamfsoftwarerestrictiontest_summary_result": {
            "description": "Description of interesting results.",
        },
    }

    def substitute_limited_assignable_keys(
        self, data, cli_custom_keys, xml_escape=False
    ):
        """substitutes any key in the inputted text using the %MY_KEY% nomenclature.
        Whenever %MY_KEY% is found in the provided data, it is replaced with the assigned
        value of MY_KEY. A five-times passa through is done to ensure that all keys are substituted.

        Optionally, if the xml_escape key is set, the value is escaped for XML special characters.
        This is designed primarily to account for ampersands in the substituted strings."""
        loop = 5
        while loop > 0:
            loop = loop - 1
            found_keys = re.findall(r"\%\w+\%", data)
            if not found_keys:
                break
            found_keys = [i.replace("%", "") for i in found_keys]
            for found_key in found_keys:
                if cli_custom_keys[found_key]:
                    self.output(
                        f"Replacing any instances of '{found_key}' with "
                        f"'{str(cli_custom_keys[found_key])}'",
                        verbose_level=2,
                    )
                    if xml_escape:
                        replacement_key = escape(cli_custom_keys[found_key])
                    else:
                        replacement_key = cli_custom_keys[found_key]
                    data = data.replace(f"%{found_key}%", replacement_key)
                else:
                    self.output(
                        f"WARNING: '{found_key}' has no replacement object!",
                    )
        return data

    def pretty_print_xml(self, xml):
        proc = subprocess.Popen(
            ["xmllint", "--format", "/dev/stdin"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        (output, _) = proc.communicate(xml)
        return output

    def upload_restriction(
        self,
        jamf_url,
        restriction_name,
        process_name,
        display_message,
        match_exact_process_name,
        send_notification,
        kill_process,
        delete_executable,
        computergroup_name,
        template_contents,
        obj_id=None,
        enc_creds="",
        token="",
    ):
        """Update Software Restriction metadata."""

        # substitute user-assignable keys
        replaceable_keys = {
            "restriction_name": restriction_name,
            "process_name": process_name,
            "display_message": display_message,
            "match_exact_process_name": match_exact_process_name,
            "send_notification": send_notification,
            "kill_process": kill_process,
            "delete_executable": delete_executable,
            "computergroup_name": computergroup_name,
        }

        # substitute user-assignable keys (escaping for XML)
        template_contents = self.substitute_limited_assignable_keys(
            template_contents, replaceable_keys, xml_escape=True
        )

        self.output("Software Restriction to be uploaded:", verbose_level=2)
        self.output(template_contents, verbose_level=2)

        self.output("Uploading Software Restriction...")

        # write the template to temp file
        template_xml = self.write_temp_file(template_contents)

        # if we find an object ID we put, if not, we post
        object_type = "restricted_software"
        if obj_id:
            url = "{}/{}/id/{}".format(
                jamf_url, self.api_endpoints(object_type), obj_id
            )
        else:
            url = "{}/{}/id/0".format(jamf_url, self.api_endpoints(object_type))

        count = 0
        while True:
            count += 1
            self.output(f"Software Restriction upload attempt {count}", verbose_level=1)
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
                self.status_check(r, "Software Restriction", restriction_name)
                == "break"
            ):
                break
            if count > 5:
                self.output(
                    "ERROR: Software Restriction upload did not succeed after 5 attempts"
                )
                self.output(f"\nHTTP POST Response Code: {r.status_code}")
                break
            sleep(10)

        return r

    def main(self):
        """Do the main thing here"""
        self.jamf_url = self.env.get("JSS_URL")
        self.jamf_user = self.env.get("API_USERNAME")
        self.jamf_password = self.env.get("API_PASSWORD")
        self.restriction_name = self.env.get("restriction_name")
        self.process_name = self.env.get("process_name")
        self.template = self.env.get("restriction_template")
        # handle setting display_message in overrides
        self.display_message = self.env.get("display_message")
        if not self.display_message:
            self.display_message = "False"
        # handle setting match_exact_process_name in overrides
        self.match_exact_process_name = self.env.get("match_exact_process_name")
        if not self.match_exact_process_name:
            self.match_exact_process_name = "False"
        # handle setting send_notification in overrides
        self.restriction_send_notification = self.env.get(
            "restriction_send_notification"
        )
        if not self.restriction_send_notification:
            self.restriction_send_notification = "false"
        # handle setting kill_process in overrides
        self.kill_process = self.env.get("kill_process")
        if not self.kill_process:
            self.kill_process = "false"
        # handle setting delete_executable in overrides
        self.delete_executable = self.env.get("delete_executable")
        if not self.delete_executable:
            self.delete_executable = "false"
        self.restriction_computergroup = self.env.get("restriction_computergroup")
        self.replace = self.env.get("replace_restriction")
        # handle setting replace in overrides
        if not self.replace or self.replace == "False":
            self.replace = False

        # clear any pre-existing summary result
        if "jamfsoftwarerestrictionuploader_summary_result" in self.env:
            del self.env["jamfsoftwarerestrictionuploader_summary_result"]

        restriction_updated = False

        # handle files with no path
        if self.template and "/" not in self.template:
            found_template = self.get_path_to_file(self.template)
            if found_template:
                self.template = found_template
            else:
                raise ProcessorError(
                    f"ERROR: XML template file {self.template} not found"
                )

        # exit if essential values are not supplied
        if not self.restriction_name:
            raise ProcessorError(
                "ERROR: No software restriction name supplied - cannot import"
            )

        # import restriction template
        with open(self.template, "r") as file:
            template_contents = file.read()

        # check for existing Software Restriction
        self.output(
            f"Checking for existing '{self.restriction_name}' on {self.jamf_url}"
        )

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

        obj_type = "restricted_software"
        obj_id = self.get_api_obj_id_from_name(
            self.jamf_url,
            self.restriction_name,
            obj_type,
            enc_creds=send_creds,
            token=token,
        )
        if obj_id:
            self.output(
                f"Software Restriction '{self.restriction_name}' already exists: ID {obj_id}"
            )
            if self.replace:
                self.upload_restriction(
                    self.jamf_url,
                    self.restriction_name,
                    self.process_name,
                    self.display_message,
                    self.match_exact_process_name,
                    self.restriction_send_notification,
                    self.kill_process,
                    self.delete_executable,
                    self.restriction_computergroup,
                    template_contents,
                    obj_id=obj_id,
                    enc_creds=send_creds,
                    token=token,
                )
                restriction_updated = True
            else:
                self.output(
                    "Not replacing existing Software Restriction. "
                    "Override the replace_restriction key to True to enforce."
                )
        else:
            self.output(
                f"Software Restriction '{self.restriction_name}' not found - will create"
            )
            # now upload the mobileconfig by generating an XML template
            self.upload_restriction(
                self.jamf_url,
                self.restriction_name,
                self.process_name,
                self.display_message,
                self.match_exact_process_name,
                self.restriction_send_notification,
                self.kill_process,
                self.delete_executable,
                self.restriction_computergroup,
                template_contents,
                enc_creds=send_creds,
                token=token,
            )
            restriction_updated = True

        # output the summary
        self.env["restriction_name"] = self.restriction_name
        self.env["restriction_updated"] = restriction_updated
        if restriction_updated:
            self.env["jamfsoftwarerestrictionuploadertest_summary_result"] = {
                "summary_text": (
                    "The following software restrictions were uploaded to "
                    "or updated in Jamf Pro:"
                ),
                "report_fields": ["restriction_name"],
                "data": {
                    "mobileconfig_name": self.restriction_name,
                },
            }


if __name__ == "__main__":
    PROCESSOR = JamfSoftwareRestrictionUploaderTest()
    PROCESSOR.execute_shell()
