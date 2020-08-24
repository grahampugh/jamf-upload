#!/usr/bin/env python3

"""
** Jamf Extension Attribute Upload Script
   by G Pugh

Credentials can be supplied from the command line as arguments, or inputted, or 
from an existing PLIST containing values for JSS_URL, API_USERNAME and API_PASSWORD, 
for example an AutoPkg preferences file which has been configured for use with 
JSSImporter: ~/Library/Preferences/com.github.autopkg

Note: this currently will only upload a script-based Extension Attribute

For usage, run jamf-extatt-upload.py --help
"""

import argparse
import json
import os.path
import re
import requests
from time import sleep
from requests_toolbelt.utils import dump
from xml.sax.saxutils import escape

from jamf_upload_lib import actions, api_connect, api_get


def upload_extatt(
    jamf_url,
    enc_creds,
    extatt_name,
    script_path,
    verbosity,
    cli_custom_keys,
    obj_id=None,
):
    """Update extension attribute metadata."""

    # import script from file and replace any keys in the script
    with open(script_path, "r") as file:
        script_contents = file.read()

    # substitute user-assignable keys
    script_contents = actions.substitute_assignable_keys(
        script_contents, cli_custom_keys, verbosity
    )

    #  XML-escape the script
    script_contents_escaped = escape(script_contents)

    # build the object
    extatt_data = (
        "<computer_extension_attribute>"
        + "<name>{}</name>".format(extatt_name)
        + "<enabled>true</enabled>"
        + "<description/>"
        + "<data_type>String</data_type>"
        + "<input_type>"
        + "  <type>script</type>"
        + "  <platform>Mac</platform>"
        + "  <script>{}</script>".format(script_contents_escaped)
        + "</input_type>"
        + "<inventory_display>Extension Attributes</inventory_display>"
        + "<recon_display>Extension Attributes</recon_display>"
        + "</computer_extension_attribute>"
    )
    headers = {
        "authorization": "Basic {}".format(enc_creds),
        "Accept": "application/xml",
        "Content-type": "application/xml",
    }
    # if we find an object ID we put, if not, we post
    if obj_id:
        url = "{}/JSSResource/computerextensionattributes/id/{}".format(
            jamf_url, obj_id
        )
    else:
        url = "{}/JSSResource/computerextensionattributes/id/0".format(jamf_url)

    http = requests.Session()
    if verbosity > 2:
        http.hooks["response"] = [api_connect.logging_hook]
        print("Extension Attribute data:")
        print(extatt_data)

    print("Uploading Extension Attribute..")

    count = 0
    while True:
        count += 1
        if verbosity > 1:
            print("Extension Attribute upload attempt {}".format(count))
        if obj_id:
            r = http.put(url, headers=headers, data=extatt_data, timeout=60)
        else:
            r = http.post(url, headers=headers, data=extatt_data, timeout=60)
        if r.status_code == 200 or r.status_code == 201:
            print("Extension Attribute uploaded successfully")
            break
        if r.status_code == 409:
            print("ERROR: Extension Attribute upload failed due to a conflict")
            break
        if count > 5:
            print("ERROR: Extension Attribute upload did not succeed after 5 attempts")
            print("\nHTTP POST Response Code: {}".format(r.status_code))
            break
        sleep(10)

    if verbosity > 1:
        api_get.get_headers(r)

    return r


def get_args():
    """Parse any command line arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-n",
        "--name",
        action="append",
        dest="names",
        default=[],
        help=("Extension Attribute to create or update"),
    )
    parser.add_argument(
        "--script", default="", help="Full path to the template script to upload",
    )
    parser.add_argument(
        "--url", default="", help="the Jamf Pro Server URL",
    )
    parser.add_argument(
        "--user",
        default="",
        help="a user with the rights to create and update an extension attribute",
    )
    parser.add_argument(
        "--password", default="", help="password of the user",
    )
    parser.add_argument(
        "--prefs",
        default="",
        help=(
            "full path to an AutoPkg prefs file containing "
            "JSS URL, API_USERNAME and API_PASSWORD, "
            "for example an AutoPkg preferences file which has been configured "
            "for use with JSSImporter (~/Library/Preferences/com.github.autopkg.plist) "
            "or a separate plist anywhere (e.g. ~/.com.company.jcds_upload.plist)"
        ),
    )
    parser.add_argument(
        "-k",
        "--key",
        action="append",
        dest="variables",
        default=[],
        metavar="KEY=VALUE",
        help=("Provide key/value pairs for script value substitution. "),
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="print verbose output headers",
    )
    args = parser.parse_args()

    # Add variables from commandline. These might override those from
    # environment variables and recipe_list
    cli_custom_keys = {}
    for arg in args.variables:
        (key, sep, value) = arg.partition("=")
        if sep != "=":
            print(f"Invalid variable [key=value]: {arg}")
        cli_custom_keys[key] = value

    return args, cli_custom_keys


def main():
    """Do the main thing here"""
    print("\n** Jamf Extension Attribute upload script")
    print("** Uploads Extension Attribute to Jamf Pro.")

    # parse the command line arguments
    args, cli_custom_keys = get_args()
    verbosity = args.verbose

    # grab values from a prefs file if supplied
    jamf_url, _, _, enc_creds = api_connect.get_creds_from_args(args)

    if not args.script:
        script = input("Enter the full path to the script to upload: ")
        args.script = script

    # now process the list of scripts
    for extatt_name in args.names:
        # check for existing Extension Attribute
        print("\nChecking '{}' on {}".format(extatt_name, jamf_url))
        obj_id = api_get.check_api_obj_id_from_name(
            jamf_url, "extension_attribute", extatt_name, enc_creds, verbosity
        )
        if obj_id:
            print(
                "Extension Attribute '{}' already exists: ID {}".format(
                    extatt_name, obj_id
                )
            )
            upload_extatt(
                jamf_url,
                enc_creds,
                extatt_name,
                args.script,
                verbosity,
                cli_custom_keys,
                obj_id,
            )
        else:
            print(
                "Extension Attribute '{}' not found - will create".format(extatt_name)
            )
            upload_extatt(
                jamf_url,
                enc_creds,
                extatt_name,
                args.script,
                verbosity,
                cli_custom_keys,
            )

    print()


if __name__ == "__main__":
    main()
