#!/usr/bin/env python3

"""
** Jamf Policy Upload Script
   by G Pugh

Credentials can be supplied from the command line as arguments, or inputted, or
from an existing PLIST containing values for JSS_URL, API_USERNAME and API_PASSWORD,
for example an AutoPkg preferences file which has been configured for use with
JSSImporter: ~/Library/Preferences/com.github.autopkg

Note that a policy can only be uploaded if the dependencies within are present on the JSS.
This includes categories (general and self-service), scripts and computer groups.
Your workflow should ensure that these items have been uploaded before running this script.

For usage, run jamf_policy_upload.py --help
"""


import argparse
import os.path
import re
import xml.etree.ElementTree as ElementTree

from time import sleep
from xml.sax.saxutils import escape

from jamf_upload_lib import actions, api_connect, api_get, curl


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

    # if we find an object ID we put, if not, we post
    if obj_id:
        url = "{}/JSSResource/policies/id/{}".format(jamf_url, obj_id)
    else:
        url = "{}/JSSResource/policies/id/0".format(jamf_url)

    if verbosity > 2:
        print("Policy data:")
        print(template_contents)

    print("Uploading Policy...")

    # write the template to temp file
    template_xml = curl.write_temp_file(template_contents)

    count = 0
    while True:
        count += 1
        if verbosity > 1:
            print("Policy upload attempt {}".format(count))
        method = "PUT" if obj_id else "POST"
        r = curl.request(method, url, enc_creds, verbosity, template_xml)
        # check HTTP response
        if curl.status_check(r, "Policy", policy_name) == "break":
            break
        if count > 5:
            print("WARNING: Policy upload did not succeed after 5 attempts")
            print("\nHTTP POST Response Code: {}".format(r.status_code))
            break
        sleep(30)

    if verbosity > 1:
        api_get.get_headers(r)

    # clean up temp files
    if os.path.exists(template_xml):
        os.remove(template_xml)

    return r


def upload_policy_icon(
    jamf_url,
    enc_creds,
    policy_name,
    policy_icon_path,
    replace_icon,
    verbosity,
    obj_id=None,
):
    """Upload an icon to the policy that was just created"""
    # check that the policy exists.
    # Use the obj_id if we have it, or use name if we don't have it yet
    # We may need a wait loop here for new policies
    if not obj_id:
        # check for existing policy
        print("\nChecking '{}' on {}".format(policy_name, jamf_url))
        obj_id = api_get.get_api_obj_id_from_name(
            jamf_url, "policy", policy_name, enc_creds, verbosity
        )
        if not obj_id:
            print(
                "ERROR: could not locate ID for policy '{}' so cannot upload icon".format(
                    policy_name
                )
            )
            return

    # Now grab the name of the existing icon using the API
    existing_icon = api_get.get_api_obj_value_from_id(
        jamf_url,
        "policy",
        obj_id,
        "self_service/self_service_icon/filename",
        enc_creds,
        verbosity,
    )

    # If the icon naame matches that we already have, don't upload again
    # unless --replace-icon is set
    policy_icon_name = os.path.basename(policy_icon_path)
    if existing_icon != policy_icon_name or replace_icon:
        url = "{}/JSSResource/fileuploads/policies/id/{}".format(jamf_url, obj_id)

        print("Uploading icon...")

        count = 0
        while True:
            count += 1
            if verbosity > 1:
                print("Icon upload attempt {}".format(count))
            r = curl.request("POST", url, enc_creds, verbosity, policy_icon_path)
            # check HTTP response
            if curl.status_check(r, "Icon", policy_icon_name) == "break":
                break
            if count > 5:
                print("WARNING: Icon upload did not succeed after 5 attempts")
                print("\nHTTP POST Response Code: {}".format(r.status_code))
                break
            sleep(30)

        if verbosity > 1:
            api_get.get_headers(r)
    else:
        print("Existing icon matches local resource - skipping upload.")


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
        "--replace",
        help="overwrite an existing policy",
        action="store_true",
    )
    parser.add_argument(
        "--template",
        default="",
        help="Path to Policy XML template",
    )
    parser.add_argument(
        "--icon",
        default="",
        help="Path to Policy Self Service icon",
    )
    parser.add_argument(
        "--replace-icon",
        help="Replace icon even if the name is the same",
        action="store_true",
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
        "--url",
        default="",
        help="the Jamf Pro Server URL",
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
            print("Invalid variable [key=value]: {}".format(arg))
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
    jamf_url, _, _, _, enc_creds = api_connect.get_creds_from_args(args)

    # import policy template and replace any keys in the XML
    with open(args.template, "r") as file:
        template_contents = file.read()

    # substitute user-assignable keys
    # pylint is incorrectly stating that 'verbosity' has no value. So...
    # pylint: disable=no-value-for-parameter
    template_contents = actions.substitute_assignable_keys(
        template_contents, cli_custom_keys, verbosity, xml_escape=True
    )

    # set a list of names either from the CLI args or from the template if no arg provided
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

        # all template processing has now been done so escape it for xml special characters
        template_contents = escape(template_contents)

        # check for existing policy
        print("\nChecking '{}' on {}".format(policy_name, jamf_url))
        obj_id = api_get.get_api_obj_id_from_name(
            jamf_url, "policy", policy_name, enc_creds, verbosity
        )
        if obj_id:
            print("Policy '{}' already exists: ID {}".format(policy_name, obj_id))
            if args.replace:
                r = upload_policy(
                    jamf_url,
                    enc_creds,
                    policy_name,
                    template_contents,
                    cli_custom_keys,
                    verbosity,
                    obj_id,
                )
            else:
                print("Not replacing existing policy. Use --replace to enforce.")
        else:
            print("Policy '{}' not found - will create".format(policy_name))
            r = upload_policy(
                jamf_url,
                enc_creds,
                policy_name,
                template_contents,
                cli_custom_keys,
                verbosity,
            )

        # now upload the icon to the policy if specified in the args
        if args.icon:
            # get the policy_id returned from the HTTP response
            try:
                policy_id = ElementTree.fromstring(r.output).findtext("id")
                upload_policy_icon(
                    jamf_url,
                    enc_creds,
                    policy_name,
                    args.icon,
                    args.replace_icon,
                    verbosity,
                    policy_id,
                )
            except UnboundLocalError:
                upload_policy_icon(
                    jamf_url,
                    enc_creds,
                    policy_name,
                    args.icon,
                    args.replace_icon,
                    verbosity,
                )

    print()


if __name__ == "__main__":
    main()
