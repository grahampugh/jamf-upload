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

For usage, run jamf_computergroup_upload.py --help
"""


import argparse
import os
import re
from time import sleep

from jamf_upload_lib import actions, api_connect, api_get, curl


def get_computergroup_name(template_contents, verbosity):
    """Determine group name from template - used when no name is supplied in CLI"""
    regex_search = "<name>.*</name>"
    result = re.search(regex_search, template_contents)[0]
    print(result)
    if result:
        computergroup_name = re.sub("<name>", "", result, 1)
        computergroup_name = re.sub("</name>", "", computergroup_name, 1)
    else:
        computergroup_name = ""

    return computergroup_name


def replace_computergroup_name(computergroup_name, template_contents, verbosity):
    """Write group name to template - used when name is supplied in CLI"""
    if verbosity:
        print("Replacing smart group name '{}' in XML".format(computergroup_name))
    regex_search = "<name>.*</name>"
    regex_replace = "<name>{}</name>".format(computergroup_name)
    template_contents = re.sub(regex_search, regex_replace, template_contents, 1)
    return template_contents


def upload_computergroup(
    jamf_url,
    enc_creds,
    computergroup_name,
    template_contents,
    cli_custom_keys,
    verbosity,
    obj_id=None,
):
    """Upload computer group"""

    # if we find an object ID we put, if not, we post
    if obj_id:
        url = "{}/JSSResource/computergroups/id/{}".format(jamf_url, obj_id)
    else:
        url = "{}/JSSResource/computergroups/id/0".format(jamf_url)

    if verbosity > 2:
        print("Computer Group data:")
        print(template_contents)

    print("Uploading Computer Group...")

    # write the template to temp file
    template_xml = curl.write_temp_file(template_contents)

    count = 0
    while True:
        count += 1
        if verbosity > 1:
            print("Computer Group upload attempt {}".format(count))
        method = "PUT" if obj_id else "POST"
        r = curl.request(method, url, enc_creds, verbosity, template_xml)
        # check HTTP response
        if curl.status_check(r, "Computer Group", computergroup_name) == "break":
            break
        if count > 5:
            print("WARNING: Computer Group upload did not succeed after 5 attempts")
            print("\nHTTP POST Response Code: {}".format(r.status_code))
            break
        sleep(30)

    if verbosity > 1:
        api_get.get_headers(r)

    # clean up temp files
    if os.path.exists(template_xml):
        os.remove(template_xml)


def get_args():
    """Parse any command line arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-n",
        "--name",
        action="append",
        dest="names",
        default=[],
        help=("Computer Group to create or update"),
    )
    parser.add_argument(
        "--replace", help="overwrite an existing Computer Group", action="store_true",
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
        help=("Provide key/value pairs for template value substitution. "),
    )
    parser.add_argument(
        "--url", default="", help="the Jamf Pro Server URL",
    )
    parser.add_argument(
        "--user",
        default="",
        help="a user with the rights to create and update a computer group",
    )
    parser.add_argument(
        "--password",
        default="",
        help="password of the user with the rights to create and update a computer group",
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
            print("Invalid variable [key=value]: {}".format(arg))
        cli_custom_keys[key] = value

    return args, cli_custom_keys


def main():
    """Do the main thing here"""
    print("\n** Jamf computer group upload script")
    print("** Creates a computer group in Jamf Pro.")

    # parse the command line arguments
    args, cli_custom_keys = get_args()
    verbosity = args.verbose

    # grab values from a prefs file if supplied
    jamf_url, _, _, _, enc_creds = api_connect.get_creds_from_args(args)

    # import computer group from file and replace any keys in the XML
    with open(args.template, "r") as file:
        template_contents = file.read()

    # substitute user-assignable keys
    # pylint is incorrectly stating that 'verbosity' has no value. So...
    # pylint: disable=no-value-for-parameter
    template_contents = actions.substitute_assignable_keys(
        template_contents, cli_custom_keys, verbosity
    )

    #  set a list of names either from the CLI args or from the template if no arg provided
    if args.names:
        names = args.names
    else:
        names = [get_computergroup_name(template_contents, verbosity)]

    # now process the list of names
    for computergroup_name in names:
        # where a group name was supplied via CLI arg, replace this in the template
        if args.names:
            template_contents = replace_computergroup_name(
                computergroup_name, template_contents, verbosity
            )

        # check for existing group
        print("\nChecking '{}' on {}".format(computergroup_name, jamf_url))
        obj_id = api_get.get_api_obj_id_from_name(
            jamf_url, "computer_group", computergroup_name, enc_creds, verbosity
        )
        if obj_id:
            print(
                "Computer Group '{}' already exists: ID {}".format(
                    computergroup_name, obj_id
                )
            )
            if args.replace:
                upload_computergroup(
                    jamf_url,
                    enc_creds,
                    computergroup_name,
                    template_contents,
                    cli_custom_keys,
                    verbosity,
                    obj_id,
                )
            else:
                print(
                    "Not replacing existing Computer Group. Use --replace to enforce."
                )
        else:
            print(
                "Computer Group '{}' not found - will create".format(computergroup_name)
            )
            upload_computergroup(
                jamf_url,
                enc_creds,
                computergroup_name,
                template_contents,
                cli_custom_keys,
                verbosity,
            )

    print()


if __name__ == "__main__":
    main()
