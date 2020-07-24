#!/usr/bin/env python3

"""
** Jamf Script Upload Script
   by G Pugh

Credentials can be supplied from the command line as arguments, or inputted, or 
from an existing PLIST containing values for JSS_URL, API_USERNAME and API_PASSWORD, 
for example an AutoPkg preferences file which has been configured for use with 
JSSImporter: ~/Library/Preferences/com.github.autopkg

For usage, run jamf-script-upload.py --help
"""


import argparse
import getpass
import sys
import os
import json
import re
import math
import io
from base64 import b64encode
from zipfile import ZipFile, ZIP_DEFLATED
from pathlib import Path
import requests
from time import sleep
from requests_toolbelt.utils import dump
import plistlib
import subprocess
import xml.etree.ElementTree as ElementTree
from shutil import copyfile
import six

if six.PY2:
    input = raw_input  # pylint: disable=E0602
    from urlparse import urlparse  # pylint: disable=F0401
    from HTMLParser import HTMLParser  # pylint: disable=F0401

    html = HTMLParser()
else:
    from urllib.parse import urlparse
    import html


def logging_hook(response, *args, **kwargs):
    data = dump.dump_all(response)
    print(data)


def get_credentials(prefs_file):
    """get credentials from an existing AutoPkg prefs file"""
    with open(prefs_file, "rb") as pl:
        if six.PY2:
            prefs = plistlib.readPlist(pl)
        else:
            prefs = plistlib.load(pl)

    try:
        jamf_url = prefs["JSS_URL"]
    except KeyError:
        jamf_url = ""
    try:
        jamf_user = prefs["API_USERNAME"]
    except KeyError:
        jamf_user = ""
    try:
        jamf_password = prefs["API_PASSWORD"]
    except KeyError:
        jamf_password = ""
    return jamf_url, jamf_user, jamf_password


def get_uapi_token(jamf_url, enc_creds, verbosity):
    """get a token for the Jamf Pro API"""
    headers = {
        "authorization": "Basic {}".format(enc_creds),
        "content-type": "application/json",
        "accept": "application/json",
    }
    url = "{}/uapi/auth/tokens".format(jamf_url)
    http = requests.Session()
    if verbosity > 2:
        http.hooks["response"] = [logging_hook]

    r = http.post(url, headers=headers)
    if verbosity > 2:
        print(r.content)
    if r.status_code == 200:
        obj = json.loads(r.text)
        try:
            token = str(obj["token"])
            print("Session token received")
            return token
        except KeyError:
            print("ERROR: No token received")
            return
    else:
        print("ERROR: No token received")
        return


def get_object_id_from_name(jamf_url, object_type, object_name, token, verbosity):
    """The UAPI doesn't have a name object, so we have to get the list of scripts 
    and parse the name to get the id """
    headers = {
        "authorization": "Bearer {}".format(token),
        "accept": "application/json",
    }
    url = "{}/uapi/v1/{}".format(jamf_url, object_type)
    http = requests.Session()
    if verbosity > 2:
        http.hooks["response"] = [logging_hook]

    r = http.get(url, headers=headers)
    if r.status_code == 200:
        object_list = json.loads(r.text)
        obj_id = 0
        for obj in object_list["results"]:
            if verbosity > 2:
                print(obj)
            if obj["name"] == object_name:
                obj_id = obj["id"]
        return obj_id


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
    obj_id=None,
):
    """Update script metadata."""

    # TODO user assignable keys
    # we want to be able to replace values in scripts based on assigned keys
    # in the form --key MY_KEY=value
    # whenever %MY_KEY% is found in a script, it should be replaced with the assigned value

    # import script from file
    script_contents = Path(script_path).read_text()

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
    #  ideally we upload to the package ID but if we didn't get a good response
    #  we fall back to the package name
    if obj_id:
        url = "{}/uapi/v1/scripts/{}".format(jamf_url, obj_id)
        script_data["id"] = obj_id
    else:
        url = "{}/uapi/v1/scripts".format(jamf_url)

    http = requests.Session()
    if verbosity > 2:
        http.hooks["response"] = [logging_hook]
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
        if r.status_code == 201:
            print("Script created successfully")
            break
        if r.status_code == 200:
            print("Script update successful")
            break
        if r.status_code == 409:
            print("ERROR: Script update failed due to a conflict")
            break
        if count > 5:
            print("ERROR: Script update did not succeed after 5 attempts")
            print("\nHTTP POST Response Code: {}".format(r.status_code))
            break
        sleep(10)

    if verbosity > 1:
        print("\nHeaders:\n")
        print(r.headers)
        print("\nResponse:\n")
        if r.text:
            print(r.text)
        else:
            print("None")

    return r


def get_args():
    """Parse any command line arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "script", nargs="+", help="Full path to the script(s) to upload",
    )
    parser.add_argument(
        "--replace", help="overwrite an existing uploaded script", action="store_true",
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
    print("\n** Jamf script upload script")
    print("** Uploads script to Jamf Pro.")

    #  parse the command line arguments
    args = get_args()

    # grab values from a prefs file if supplied
    if args.prefs:
        (jamf_url, jamf_user, jamf_password) = get_credentials(args.prefs)
    else:
        jamf_url = ""
        jamf_user = ""
        jamf_password = ""

    # CLI arguments override any values from a prefs file
    if args.url:
        jamf_url = args.url
    elif not jamf_url:
        jamf_url = input("Enter Jamf Pro Server URL : ")
    if args.user:
        jamf_user = args.user
    elif not jamf_user:
        jamf_user = input(
            "Enter a Jamf Pro user with API rights to upload a package : "
        )
    if args.password:
        jamf_password = args.password
    elif not jamf_password:
        jamf_password = getpass.getpass(
            "Enter the password for '{}' : ".format(jamf_user)
        )

    # encode the username and password into a basic auth b64 encoded string so that we can get the session token
    credentials = "{}:{}".format(jamf_user, jamf_password)
    if six.PY2:
        enc_creds = b64encode(credentials)
    else:
        enc_creds_bytes = b64encode(credentials.encode("utf-8"))
        enc_creds = str(enc_creds_bytes, "utf-8")

    # now get the session token
    token = get_uapi_token(jamf_url, enc_creds, args.verbose)

    if not args.script:
        script = input("Enter the full path to the script to upload: ")
        args.script = script

    # get the id for a category if supplied
    if args.category:
        print("Checking categories for {}".format(args.category))
        category_id = get_object_id_from_name(
            jamf_url, "categories", args.category, token, args.verbose
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
        if args.verbose:
            print("Full path: {}".format(script_path))
        obj_id = get_object_id_from_name(
            jamf_url, "scripts", script_name, token, args.verbose
        )

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
            args.verbose,
            token,
            obj_id,
        )

    print()


if __name__ == "__main__":
    main()
