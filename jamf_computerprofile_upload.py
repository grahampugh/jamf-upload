#!/usr/bin/env python3

"""
** Jamf Computer Configuration Profile Upload Script
   by G Pugh

Credentials can be supplied from the command line as arguments, or inputted, or
from an existing PLIST containing values for JSS_URL, API_USERNAME and API_PASSWORD,
for example an AutoPkg preferences file which has been configured for use with
JSSImporter: ~/Library/Preferences/com.github.autopkg

For usage, run jamf_computerprofile_upload.py --help
"""

import argparse
import os.path
import plistlib
import subprocess
import uuid
from time import sleep
from xml.sax.saxutils import escape

from jamf_upload_lib import actions, api_connect, api_get, curl


def pretty_print_xml(xml):
    proc = subprocess.Popen(
        ["xmllint", "--format", "/dev/stdin"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    (output, _) = proc.communicate(xml)
    return output


def make_mobileconfig_from_payload(
    payload_path,
    payload_identifier,
    mobileconfig_name,
    organization,
    description,
    mobileconfig_uuid,
    verbosity,
):
    """create a mobileconfig file using a payload file"""
    # import plist and replace any substitutable keys
    with open(payload_path, "rb") as file:
        mcx_preferences = plistlib.load(file)

    if verbosity > 1:
        print("Preferences contents:")
        print(mcx_preferences)

    # generate a random UUID for the payload
    payload_uuid = generate_uuid()

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

    if verbosity > 2:
        print("\nPayload contents:")
        print(payload_contents)

    # now write the mobileconfig file
    mobileconfig_data = {
        "PayloadDescription": description,
        "PayloadDisplayName": mobileconfig_name,
        "PayloadEnabled": True,
        "PayloadOrganization": organization,
        "PayloadRemovalDisallowed": True,
        "PayloadScope": "System",
        "PayloadType": "Configuration",
        "PayloadVersion": 1,
        "PayloadIdentifier": mobileconfig_uuid,
        "PayloadUUID": mobileconfig_uuid,
        "PayloadContent": [payload_contents],
    }

    print("Converting config data to plist")
    mobileconfig_plist = plistlib.dumps(mobileconfig_data)

    if verbosity > 2:
        print("\nMobileconfig contents:")
        print(mobileconfig_plist.decode("UTF-8"))

    return mobileconfig_plist


def get_existing_uuid(jamf_url, obj_id, enc_creds, verbosity):
    """return the existing UUID to ensure we don't change it"""
    # first grab the payload from the xml object
    existing_plist = api_get.get_api_obj_value_from_id(
        jamf_url,
        "os_x_configuration_profile",
        obj_id,
        "general/payloads",
        enc_creds,
        verbosity,
    )

    # Jamf seems to sometimes export an empty key which plistlib considers invalid,
    # so let's remove this
    existing_plist = existing_plist.replace("<key/>", "")

    # make the xml pretty so we can see where the problem importing it is better
    existing_plist = pretty_print_xml(bytes(existing_plist, "utf-8"))

    if verbosity > 2:
        print("\nExisting payload (type: {}):".format(type(existing_plist)))
        print(existing_plist.decode("UTF-8"))

    # now extract the UUID from the existing payload
    existing_payload = plistlib.loads(existing_plist)
    if verbosity > 2:
        print("\nImported payload:")
        print(existing_payload)
    existing_uuid = existing_payload["PayloadUUID"]
    print("Existing UUID found: {}".format(existing_uuid))
    return existing_uuid


def generate_uuid():
    """generate a UUID for new profiles"""
    return str(uuid.uuid4())


def unsign_signed_mobileconfig(mobileconfig_plist, verbosity):
    """checks if profile is signed. This is necessary because Jamf cannot
    upload a signed profile, so we either need to unsign it, or bail """
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
    if verbosity:
        print(cmd)
        print()
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    _, err = proc.communicate()
    if os.path.exists(output_path):
        print(f"Profile is signed. Unsigned profile at {output_path}")
        return output_path
    elif err:
        print("Profile is not signed.")
        if verbosity > 2:
            print(err)
            print()


def upload_mobileconfig(
    jamf_url,
    enc_creds,
    mobileconfig_name,
    description,
    category,
    mobileconfig_plist,
    computergroup_name,
    template_contents,
    profile_uuid,
    verbosity,
    obj_id=None,
):
    """Update Configuration Profile metadata."""

    # if we find an object ID we put, if not, we post
    if obj_id:
        url = "{}/JSSResource/osxconfigurationprofiles/id/{}".format(jamf_url, obj_id)
    else:
        url = "{}/JSSResource/osxconfigurationprofiles/id/0".format(jamf_url)

    # remove newlines, tabs, leading spaces, and XML-escape the payload
    mobileconfig_plist = mobileconfig_plist.decode("UTF-8")
    mobileconfig_list = mobileconfig_plist.rsplit("\n")
    mobileconfig_list = [x.strip("\t") for x in mobileconfig_list]
    mobileconfig_list = [x.strip(" ") for x in mobileconfig_list]
    mobileconfig = "".join(mobileconfig_list)
    mobileconfig_plist_escaped = escape(mobileconfig)

    # substitute user-assignable keys
    replaceable_keys = {
        "mobileconfig_name": mobileconfig_name,
        "description": description,
        "category": category,
        "payload": mobileconfig_plist_escaped,
        "computergroup_name": computergroup_name,
        "uuid": "com.github.grahampugh.jamf-upload.{}".format(profile_uuid),
    }

    if verbosity > 2:
        print("Replacing the following keys in the profile template:")
        print(replaceable_keys)

    # substitute user-assignable keys
    template_contents = actions.substitute_assignable_keys(
        data=template_contents, cli_custom_keys=replaceable_keys, verbosity=verbosity
    )

    if verbosity > 2:
        print("Configuration Profile to be uploaded:")
        print(template_contents)

    print("Uploading Configuration Profile..")
    # write the template to temp file
    template_xml = curl.write_temp_file(template_contents)

    count = 0
    while True:
        count += 1
        if verbosity > 1:
            print("Configuration Profile upload attempt {}".format(count))
        method = "PUT" if obj_id else "POST"
        r = curl.request(method, url, enc_creds, verbosity, template_xml)
        # check HTTP response
        if curl.status_check(r, "Configuration Profile", mobileconfig_name) == "break":
            break
        if count > 5:
            print(
                "ERROR: Configuration Profile upload did not succeed after 5 attempts"
            )
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
        "--name", default="", help="Configuration Profile to create or update",
    )
    parser.add_argument(
        "--payload", default="", help="Path to Configuration Profile plist payload",
    )
    parser.add_argument(
        "--mobileconfig", default="", help="Path to Configuration Profile mobileconfig",
    )
    parser.add_argument(
        "--identifier", default="", help="Path to Configuration Profile plist payload",
    )
    parser.add_argument(
        "--template", default="", help="Path to Configuration Profile XML template",
    )
    parser.add_argument(
        "--category", default="", help="a category to assign to the profile",
    )
    parser.add_argument(
        "--organization", default="", help="Organization to assign to the profile",
    )
    parser.add_argument(
        "--description", default="", help="a description to assign to the profile",
    )
    parser.add_argument(
        "--computergroup_name",
        default="",
        help="a computer group which will be scoped to the profile",
    )
    parser.add_argument(
        "--replace",
        help="overwrite an existing Configuration Profile",
        action="store_true",
    )
    parser.add_argument(
        "--unsign",
        help="Unsign a mobileconfig file prior to uploading if it is signed",
        action="store_true",
    )
    parser.add_argument(
        "--url", default="", help="the Jamf Pro Server URL",
    )
    parser.add_argument(
        "--user",
        default="",
        help="a user with the rights to create and update an Configuration Profile",
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
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="print verbose output headers",
    )
    args = parser.parse_args()

    return args


def main():
    """Do the main thing here"""
    print(
        "\n** Jamf Configuration Profile upload script",
        "\n** Uploads Configuration Profile to Jamf Pro.",
        "\n** WARNING: This is an experimental script! Using it may have unexpected results!",
        "\n",
    )

    # parse the command line arguments
    args = get_args()
    verbosity = args.verbose

    # grab values from a prefs file if supplied
    jamf_url, jamf_user, jamf_pass, _, enc_creds = api_connect.get_creds_from_args(args)

    if verbosity > 1:
        print("URL: {}".format(jamf_url))
        print("User: {}".format(jamf_user))
    if verbosity > 2:
        print("Pass: {}".format(jamf_pass))

    # if an unsigned mobileconfig file is supplied we can get the name, organization and
    # description from it
    if args.mobileconfig:
        print("mobileconfig file supplied: {}".format(args.mobileconfig))
        # check if the file is signed
        mobileconfig_file = unsign_signed_mobileconfig(args.mobileconfig, verbosity)
        # quit if we get an unsigned profile back and we didn't select --unsign
        if mobileconfig_file and not args.unsign:
            print(
                "Signed profiles cannot be uploaded to Jamf Pro via the API. "
                "Use the GUI to upload the signed profile, or use --unsign to upload "
                "the profile with the signature removed."
            )
            exit()

        # import mobileconfig
        with open(mobileconfig_file, "rb") as file:
            mobileconfig_contents = plistlib.load(file)
        with open(mobileconfig_file, "rb") as file:
            mobileconfig_plist = file.read()
        try:
            mobileconfig_name = mobileconfig_contents["PayloadDisplayName"]
            print("Configuration Profile name: {}".format(mobileconfig_name))
            if verbosity > 2:
                print("\nMobileconfig contents:")
                print(mobileconfig_plist.decode("UTF-8"))
        except KeyError:
            exit("ERROR: Invalid mobileconfig file supplied - cannot import")
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
        if not args.name:
            name = input("Enter the name of the configuration profile to upload: ")
            args.name = name
        if not args.payload:
            payload = input("Enter the full path to the payload plist to upload: ")
            args.payload = payload
        if not args.identifier:
            identifier = input("Enter the identifier of the custom payload to upload: ")
            args.identifier = identifier
        mobileconfig_name = args.name
        description = ""
        organization = ""

    # we provide a default template which has no category or scope
    if not args.template:
        # template = input("Enter the full path to the template XML to upload: ")
        args.template = "Jamf_Templates_and_Scripts/ProfileTemplate-default.xml"

    # automatically provide a description and organisation if not provided in the options
    if not args.description:
        if description:
            args.description = description
        else:
            description = input("Enter the description of the profile to upload: ")
            args.description = description
    if not args.organization:
        if organization:
            args.organization = organization
        else:
            organization = input("Enter the organization of the profile to upload: ")
            args.organization = organization

    # import profile template
    with open(args.template, "r") as file:
        template_contents = file.read()

    # check for existing Configuration Profile
    print("\nChecking '{}' on {}".format(mobileconfig_name, jamf_url))
    obj_id = api_get.get_api_obj_id_from_name(
        jamf_url, "os_x_configuration_profile", mobileconfig_name, enc_creds, verbosity
    )
    if obj_id:
        print(
            "Configuration Profile '{}' already exists: ID {}".format(
                mobileconfig_name, obj_id
            )
        )
        if args.replace:
            # grab existing UUID from profile as it MUST match on the destination
            existing_uuid = get_existing_uuid(jamf_url, obj_id, enc_creds, verbosity)

            if not args.mobileconfig:
                # generate the mobileconfig from the supplied payload
                mobileconfig_plist = make_mobileconfig_from_payload(
                    args.payload,
                    args.identifier,
                    mobileconfig_name,
                    args.organization,
                    args.description,
                    existing_uuid,
                    verbosity,
                )

            # now upload the mobileconfig by generating an XML template
            if mobileconfig_plist:
                upload_mobileconfig(
                    jamf_url,
                    enc_creds,
                    mobileconfig_name,
                    args.description,
                    args.category,
                    mobileconfig_plist,
                    args.computergroup_name,
                    template_contents,
                    existing_uuid,
                    verbosity,
                    obj_id,
                )
            else:
                print("A mobileconfig was not generated so cannot upload.")
        else:
            print(
                "Not replacing existing Configuration Profile. Use --replace to enforce."
            )
    else:
        print(
            "Configuration Profile '{}' not found - will create".format(
                mobileconfig_name
            )
        )
        new_uuid = generate_uuid()

        if not args.mobileconfig:
            # generate the mobileconfig from the supplied payload
            mobileconfig_plist = make_mobileconfig_from_payload(
                args.payload,
                args.identifier,
                mobileconfig_name,
                args.organization,
                args.description,
                new_uuid,
                verbosity,
            )

        # now upload the mobileconfig by generating an XML template
        if mobileconfig_plist:
            upload_mobileconfig(
                jamf_url,
                enc_creds,
                mobileconfig_name,
                args.description,
                args.category,
                mobileconfig_plist,
                args.computergroup_name,
                template_contents,
                new_uuid,
                verbosity,
            )
        else:
            print("A mobileconfig was not generated so cannot upload.")

    print()


if __name__ == "__main__":
    main()
