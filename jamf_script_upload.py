#!/usr/bin/env python3

"""
** Jamf Script Upload Script
   by G Pugh

Credentials can be supplied from the command line as arguments, or inputted, or 
from an existing PLIST containing values for JSS_URL, API_USERNAME and API_PASSWORD, 
for example an AutoPkg preferences file which has been configured for use with 
JSSImporter: ~/Library/Preferences/com.github.autopkg

For usage, run jamf_script_upload.py --help
"""

import argparse
import json
import os.path
import re
import requests
from time import sleep
from requests_toolbelt.utils import dump

from jamf_upload_lib import actions, api_connect, api_get


def upload_script(
    jamf_url,
    script_name,
    script_path,
    category_id,
    category_name,
    script_info,
    script_notes,
    script_priority,
    script_parameter4,
    script_parameter5,
    script_parameter6,
    script_parameter7,
    script_parameter8,
    script_parameter9,
    script_parameter10,
    script_parameter11,
    script_os_requirements,
    verbosity,
    token,
    cli_custom_keys,
    obj_id=None,
):
    """Update script metadata."""

    # import script from file and replace any keys in the script
    # script_contents = Path(script_path).read_text()
    with open(script_path, "r") as file:
        script_contents = file.read()

    # substitute user-assignable keys
    script_contents = actions.substitute_assignable_keys(
        script_contents, cli_custom_keys, verbosity
    )

    # build the object
    script_data = {
        "name": script_name,
        "info": script_info,
        "notes": script_notes,
        "priority": script_priority,
        "categoryId": category_id,
        "categoryName": category_name,
        "parameter4": script_parameter4,
        "parameter5": script_parameter5,
        "parameter6": script_parameter6,
        "parameter7": script_parameter7,
        "parameter8": script_parameter8,
        "parameter9": script_parameter9,
        "parameter10": script_parameter10,
        "parameter11": script_parameter11,
        "osRequirements": script_os_requirements,
        "scriptContents": script_contents,
    }
    headers = {
        "authorization": "Bearer {}".format(token),
        "content-type": "application/json",
        "accept": "application/json",
    }
    # ideally we upload to the object ID but if we didn't get a good response
    # we fall back to the name
    if obj_id:
        url = "{}/uapi/v1/scripts/{}".format(jamf_url, obj_id)
        script_data["id"] = obj_id
    else:
        url = "{}/uapi/v1/scripts".format(jamf_url)

    http = requests.Session()
    if verbosity > 2:
        http.hooks["response"] = [api_connect.logging_hook]
        print("Script data:")
        print(script_data)

    print("Uploading script..")

    count = 0
    script_json = json.dumps(script_data)
    while True:
        count += 1
        if verbosity > 1:
            print("Script upload attempt {}".format(count))
        if obj_id:
            r = http.put(url, headers=headers, data=script_json, timeout=60)
        else:
            r = http.post(url, headers=headers, data=script_json, timeout=60)
        if r.status_code == 200 or r.status_code == 201:
            print("Script uploaded successfully")
            break
        if r.status_code == 409:
            print("ERROR: Script upload failed due to a conflict")
            break
        if count > 5:
            print("ERROR: Script upload did not succeed after 5 attempts")
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
        "script", nargs="+", help="Full path to the script(s) to upload",
    )
    parser.add_argument(
        "--replace", help="overwrite an existing script", action="store_true",
    )
    parser.add_argument(
        "--url", default="", help="the Jamf Pro Server URL",
    )
    parser.add_argument(
        "--user", default="", help="a user with the rights to upload a script",
    )
    parser.add_argument(
        "--password",
        default="",
        help="password of the user with the rights to upload a script",
    )
    parser.add_argument(
        "--category", default="", help="a category to assign to the script(s)",
    )
    parser.add_argument(
        "--priority",
        default="AFTER",
        help="priority to assign to the script(s) - BEFORE or AFTER",
    )
    parser.add_argument(
        "--osrequirements",
        default="",
        help="a value to assign to the OS requirements field of the script(s)",
    )
    parser.add_argument(
        "--info", default="", help="information to assign to the script(s)",
    )
    parser.add_argument(
        "--notes", default="", help="notes to assign to the script(s)",
    )
    parser.add_argument(
        "--parameter4",
        default="",
        help="a value to assign to parameter4 of the script(s)",
    )
    parser.add_argument(
        "--parameter5",
        default="",
        help="a value to assign to parameter5 of the script(s)",
    )
    parser.add_argument(
        "--parameter6",
        default="",
        help="a value to assign to parameter6 of the script(s)",
    )
    parser.add_argument(
        "--parameter7",
        default="",
        help="a value to assign to parameter7 of the script(s)",
    )
    parser.add_argument(
        "--parameter8",
        default="",
        help="a value to assign to parameter8 of the script(s)",
    )
    parser.add_argument(
        "--parameter9",
        default="",
        help="a value to assign to parameter9 of the script(s)",
    )
    parser.add_argument(
        "--parameter10",
        default="",
        help="a value to assign to parameter10 of the script(s)",
    )
    parser.add_argument(
        "--parameter11",
        default="",
        help="a value to assign to parameter11 of the script(s)",
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
    print("\n** Jamf script upload script")
    print("** Uploads script to Jamf Pro.")

    # parse the command line arguments
    args, cli_custom_keys = get_args()
    verbosity = args.verbose

    # grab values from a prefs file if supplied
    jamf_url, _, _, enc_creds = api_connect.get_creds_from_args(args)

    # now get the session token
    token = api_connect.get_uapi_token(jamf_url, enc_creds, verbosity)

    if not args.script:
        script = input("Enter the full path to the script to upload: ")
        args.script = script

    # get the id for a category if supplied
    if args.category:
        print("Checking categories for {}".format(args.category))
        category_id = api_get.get_uapi_obj_id_from_name(
            jamf_url, "categories", args.category, token, verbosity
        )
        if not category_id:
            print("WARNING: Category not found!")
            category_id = "-1"
        else:
            print("Category {} found: ID={}".format(args.category, category_id))
    else:
        args.category = ""

    # now process the list of scripts
    for script_path in args.script:
        script_name = os.path.basename(script_path)

        # check for existing script
        print("\nChecking '{}' on {}".format(script_name, jamf_url))
        if verbosity:
            print("Full path: {}".format(script_path))
        obj_id = api_get.get_uapi_obj_id_from_name(
            jamf_url, "scripts", script_name, token, verbosity
        )

        if obj_id and not args.replace:
            print("Not replacing existing script. Use --replace to enforce.")
            continue

        # post the script
        upload_script(
            jamf_url,
            script_name,
            script_path,
            category_id,
            args.category,
            args.info,
            args.notes,
            args.priority,
            args.parameter4,
            args.parameter5,
            args.parameter6,
            args.parameter7,
            args.parameter8,
            args.parameter9,
            args.parameter10,
            args.parameter11,
            args.osrequirements,
            verbosity,
            token,
            cli_custom_keys,
            obj_id,
        )

    print()


if __name__ == "__main__":
    main()
