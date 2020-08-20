#!/usr/bin/env python3

"""
** Jamf Computer Group Upload Script
   by G Pugh

Credentials can be supplied from the command line as arguments, or inputted, or 
from an existing PLIST containing values for JSS_URL, API_USERNAME and API_PASSWORD, 
for example an AutoPkg preferences file which has been configured for use with 
JSSImporter: ~/Library/Preferences/com.github.autopkg

Note that criteria containing dependent computer groups can only be set if those groups 
already exist. This script will not create them. Ensure you script in a logical order
to build up the dependencies in turn.

For usage, run jamf-computergroup-upload.py --help
"""


import argparse
import json
import re
import requests
from time import sleep
from requests_toolbelt.utils import dump

from jamf_upload_lib import actions, api_connect, api_get


def upload_computergroup(
    jamf_url,
    enc_creds,
    computergroup_name,
    template,
    cli_custom_keys,
    verbosity,
    obj_id=None,
):
    """Upload computer group"""
    # import computer group from file and replace any keys in the XML
    with open(template, "r") as file:
        template_contents = file.read()

    # substitute user-assignable keys
    template_contents = actions.substitute_assignable_keys(
        template_contents, cli_custom_keys, verbosity
    )

    # it's also essential to set the name in the XML template to match the one we are posting/putting
    # so we must overwrite that regardless
    if verbosity:
        print(f"Replacing smart group name '{computergroup_name}' in XML")
    regex_search = "<name>.*</name>"
    regex_replace = f"<name>{computergroup_name}</name>"
    template_contents = re.sub(regex_search, regex_replace, template_contents)

    headers = {
        "authorization": "Basic {}".format(enc_creds),
        "Accept": "application/xml",
        "Content-type": "application/xml",
    }
    # if we find an object ID we put, if not, we post
    if obj_id:
        url = "{}/JSSResource/computergroups/id/{}".format(jamf_url, obj_id)
    else:
        url = "{}/JSSResource/computergroups/id/0".format(jamf_url)

    http = requests.Session()
    if verbosity > 2:
        http.hooks["response"] = [api_connect.logging_hook]
        print("Computer Group data:")
        print(template_contents)

    print("Uploading Computer Group...")

    count = 0
    while True:
        count += 1
        if verbosity > 1:
            print("Computer Group upload attempt {}".format(count))
        if obj_id:
            r = http.put(url, headers=headers, data=template_contents, timeout=60)
        else:
            r = http.post(url, headers=headers, data=template_contents, timeout=60)
        if r.status_code == 201:
            print(f"Computer Group '{computergroup_name}' updated successfully")
            break
        if r.status_code == 200:
            print(f"Computer Group '{computergroup_name}' created successfully")
            break
        if r.status_code == 409:
            print("WARNING: Computer Group update failed due to a conflict")
            break
        if count > 5:
            print("WARNING: Computer Group update did not succeed after 5 attempts")
            print("\nHTTP POST Response Code: {}".format(r.status_code))
            break
        sleep(30)

    if verbosity:
        print("\nHeaders:\n")
        print(r.headers)
        print("\nResponse:\n")
        if r.text:
            print(r.text)
        else:
            print("None")


def get_args():
    """Parse any command line arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "name", nargs="+", help="Computer Group to create or update",
    )
    parser.add_argument(
        "--template", default="", help="Path to Computer Group XML template",
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
        "--url", default="", help="the Jamf Pro Server URL",
    )
    parser.add_argument(
        "--user", default="", help="a user with the rights to create a category",
    )
    parser.add_argument(
        "--password",
        default="",
        help="password of the user with the rights to create a category",
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
    print("\n** Jamf computer group upload script")
    print("** Creates a computer group in Jamf Pro.")

    # parse the command line arguments
    args, cli_custom_keys = get_args()

    # grab values from a prefs file if supplied
    jamf_url, _, _, enc_creds = api_connect.get_creds_from_args(args)

    # now process the list of categories
    for computergroup_name in args.name:
        # check for existing category
        print("\nChecking '{}' on {}".format(computergroup_name, jamf_url))
        obj_id = api_get.check_api_obj_id_from_name(
            jamf_url, "computer_group", computergroup_name, enc_creds, args.verbose
        )
        if obj_id:
            print(
                "Computer Group '{}' already exists: ID {}".format(
                    computergroup_name, obj_id
                )
            )
            upload_computergroup(
                jamf_url,
                enc_creds,
                computergroup_name,
                args.template,
                cli_custom_keys,
                args.verbose,
                obj_id,
            )
        else:
            upload_computergroup(
                jamf_url,
                enc_creds,
                computergroup_name,
                args.template,
                cli_custom_keys,
                args.verbose,
            )

    print()


if __name__ == "__main__":
    main()
