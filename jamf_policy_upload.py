#!/usr/bin/env python3

"""
** Jamf Policy Upload Script
   by G Pugh

Credentials can be supplied from the command line as arguments, or inputted, or 
from an existing PLIST containing values for JSS_URL, API_USERNAME and API_PASSWORD, 
for example an AutoPkg preferences file which has been configured for use with 
JSSImporter: ~/Library/Preferences/com.github.autopkg

Note that a policy can only be uploaded if the dependencies within are present on the JSS. This includes categories (general and self-service), scripts and computer groups. Your workflow should ensure that these items have been uploaded before running this script.

For usage, run jamf_policy_upload.py --help
"""


import argparse
import json
import os.path
import re
import requests
from time import sleep
from requests_toolbelt.utils import dump

from jamf_upload_lib import actions, api_connect, api_get


def get_policy_name(template_contents, verbosity):
    """Determine group name from template - used when no name is supplied in CLI"""
    regex_search = "<name>.*</name>"
    result = re.search(regex_search, template_contents)[0]
    print(result)
    if result:
        policy_name = re.sub("<name>", "", result, 1)
        policy_name = re.sub("</name>", "", policy_name, 1)
    else:
        policy_name = ""

    return policy_name


def replace_policy_name(policy_name, template_contents, verbosity):
    """Write policy to template - used when name is supplied in CLI"""
    if verbosity:
        print("Replacing policy name '{}' in XML".format(policy_name))
    regex_search = "<name>.*</name>"
    regex_replace = "<name>{}</name>".format(policy_name)
    template_contents = re.sub(regex_search, regex_replace, template_contents, 1)
    return template_contents


def upload_policy(
    jamf_url,
    enc_creds,
    policy_name,
    template_contents,
    cli_custom_keys,
    verbosity,
    obj_id=None,
):
    """Upload policy"""
    headers = {
        "authorization": "Basic {}".format(enc_creds),
        "Accept": "application/xml",
        "Content-type": "application/xml",
    }
    # if we find an object ID we put, if not, we post
    if obj_id:
        url = "{}/JSSResource/policies/id/{}".format(jamf_url, obj_id)
    else:
        url = "{}/JSSResource/policies/id/0".format(jamf_url)

    http = requests.Session()
    if verbosity > 2:
        http.hooks["response"] = [api_connect.logging_hook]
        print("Policy data:")
        print(template_contents)

    print("Uploading Policy...")

    count = 0
    while True:
        count += 1
        if verbosity > 1:
            print("Policy upload attempt {}".format(count))
        if obj_id:
            r = http.put(url, headers=headers, data=template_contents, timeout=60)
        else:
            r = http.post(url, headers=headers, data=template_contents, timeout=60)
        if r.status_code == 200 or r.status_code == 201:
            print(f"Policy '{policy_name}' uploaded successfully")
            break
        if r.status_code == 409:
            # TODO when using verbose mode we could get the reason for the conflict from the output
            print("WARNING: Policy upload failed due to a conflict")
            break
        if count > 5:
            print("WARNING: CPolicy upload did not succeed after 5 attempts")
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
        "-n",
        "--name",
        action="append",
        dest="names",
        default=[],
        help=("Policy to create or update"),
    )
    parser.add_argument(
        "--template", default="", help="Path to Policy XML template",
    )
    parser.add_argument(
        "-k",
        "--key",
        action="append",
        dest="variables",
        default=[],
        metavar="KEY=VALUE",
        help=("Provide key/value pairs for template value substitution. "),
    )
    parser.add_argument(
        "--url", default="", help="the Jamf Pro Server URL",
    )
    parser.add_argument(
        "--user",
        default="",
        help="a user with the rights to create and update a policy",
    )
    parser.add_argument(
        "--password",
        default="",
        help="password of the user with the rights to create and update a policy",
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
    print("\n** Jamf policy upload script")
    print("** Creates a policy in Jamf Pro.")

    # parse the command line arguments
    args, cli_custom_keys = get_args()
    verbosity = args.verbose

    # grab values from a prefs file if supplied
    jamf_url, _, _, enc_creds = api_connect.get_creds_from_args(args)

    # import computer group from file and replace any keys in the XML
    with open(args.template, "r") as file:
        template_contents = file.read()

    # substitute user-assignable keys
    template_contents = actions.substitute_assignable_keys(
        template_contents, cli_custom_keys, verbosity
    )

    #  set a list of names either from the CLI args or from the template if no arg provided
    if args.names:
        names = args.names
    else:
        names = [get_policy_name(template_contents, verbosity)]

    # now process the list of names
    for policy_name in names:
        # where a policy name was supplied via CLI arg, replace this in the template
        if args.names:
            template_contents = replace_policy_name(
                policy_name, template_contents, verbosity
            )

        # check for existing group
        print("\nChecking '{}' on {}".format(policy_name, jamf_url))
        obj_id = api_get.check_api_obj_id_from_name(
            jamf_url, "policy", policy_name, enc_creds, verbosity
        )
        if obj_id:
            print("Policy '{}' already exists: ID {}".format(policy_name, obj_id))
            upload_policy(
                jamf_url,
                enc_creds,
                policy_name,
                template_contents,
                cli_custom_keys,
                verbosity,
                obj_id,
            )
        else:
            print("Policy '{}' not found - will create".format(policy_name))
            upload_policy(
                jamf_url,
                enc_creds,
                policy_name,
                template_contents,
                cli_custom_keys,
                verbosity,
            )

    print()


if __name__ == "__main__":
    main()
