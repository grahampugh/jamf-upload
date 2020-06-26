#!/usr/bin/python3

"""
** Jamf Cloud Package Upload Script
   by G Pugh

Developed from an idea posted at
https://www.jamf.com/jamf-nation/discussions/27869#responseChild166021

Credentials can be supplied from the command line as arguments, or inputted, or 
from an existing PLIST containing values for JSS_URL, API_USERNAME and API_PASSWORD, 
for example an AutoPkg preferences file which has been configured for use with 
JSSImporter: ~/Library/Preferences/com.github.autopkg

For usage, run jamf-upload.py --help
"""


import argparse
import getpass
import sys
import os
import json
from base64 import b64encode
import requests
import plistlib

import six

if six.PY2:
    input = raw_input


def get_credentials(prefs_file):
    """get credentials from an existing AutoPkg prefs file"""
    with open(prefs_file, "rb") as pl:
        if six.PY2:
            prefs = plistlib.readPlist(pl)
        else:
            prefs = plistlib.load(pl)

    jamf_url = prefs["JSS_URL"]
    jamf_user = prefs["API_USERNAME"]
    jamf_password = prefs["API_PASSWORD"]
    return jamf_url, jamf_user, jamf_password


def check_pkg(pkg_name, jamf_url, enc_creds, replace_pkg):
    """check if a package with the same name exists in the repo
    note that it is possible to have more than one with the same name
    which could mess things up"""
    headers = {
        "authorization": "Basic {}".format(enc_creds),
        "accept": "application/json",
    }
    url = "{}/JSSResource/packages/name/{}".format(jamf_url, pkg_name)
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        obj = json.loads(r.text)
        try:
            obj_id = str(obj["package"]["id"])
            print("\nExisting Package Object ID found: {}".format(obj_id))
            if not replace_pkg:
                print(
                    "\nNot replacing existing package. Set 'replace_pkg' to True to force upload attempt.\n"
                )
                return
            else:
                print("Replacing existing package.")
        except KeyError:
            obj_id = "-1"
        return obj_id
    else:
        obj_id = "-1"
        return obj_id


def post_pkg(pkg_name, pkg_path, jamf_url, enc_creds, obj_id):
    """sends the package"""
    files = {"file": open(pkg_path, "rb")}
    headers = {
        "authorization": "Basic {}".format(enc_creds),
        "content-type": "application/xml",
        "DESTINATION": "0",
        "OBJECT_ID": obj_id,
        "FILE_TYPE": "0",
        "FILE_NAME": pkg_name,
    }
    url = "{}/dbfileupload".format(jamf_url)
    r = requests.post(url, files=files, headers=headers)
    return r


def main():
    """Do the main thing here"""

    print("\n** Jamf Cloud package upload script")
    print("** Uploads packages to Jamf Cloud Distribution Points.\n")

    # get inputs from the CLI
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "pkg", nargs="+", help="Full path to the package(s) to upload",
    )
    parser.add_argument(
        "--replace",
        help="overwrite an existing uploaded package (experimental)",
        action="store_true",
    )
    parser.add_argument(
        "--url", default="", help="the Jamf Pro Server URL",
    )
    parser.add_argument(
        "--user", default="", help="a user with the rights to upload a package",
    )
    parser.add_argument(
        "--password",
        default="",
        help="password of the user with the rights to upload a package",
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
        "--verbose", action="store_true", help="print verbose output headers",
    )
    args = parser.parse_args()

    # grab values from a prefs file if supplied
    if args.prefs:
        jamf_url, jamf_user, jamf_password = get_credentials(args.prefs)
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
        jamf_password = getpass.getpass("Enter the password for '%s' : " % jamf_user)
    if args.verbose:
        verbose = True
    else:
        verbose = False

    # encode the username and password into a basic auth b64 encoded string
    credentials = "%s:%s" % (jamf_user, jamf_password)
    if six.PY2:
        enc_creds = b64encode(credentials)
    else:
        enc_creds_bytes = b64encode(credentials.encode("utf-8"))
        enc_creds = str(enc_creds_bytes, "utf-8")

    if not args.pkg:
        pkg = input("Enter the full path to the package to upload: ")
        args.pkg = pkg

    # now process the list of packages
    for pkg_path in args.pkg:
        # post the package
        pkg_name = os.path.basename(pkg_path)
        print("\nChecking '{}' on {}".format(pkg_name, jamf_url))
        # check for existing
        replace_pkg = True if args.replace else False
        obj_id = check_pkg(pkg_name, jamf_url, enc_creds, replace_pkg)
        if obj_id:
            # post the package (won't run if the pkg exists and replace_pkg is False)
            r = post_pkg(pkg_name, pkg_path, jamf_url, enc_creds, obj_id)
            # print result of the request
            if r.status_code == 200 or r.status_code == 201:
                print("\nPackage uploaded successfully")
                if verbose:
                    print("HTTP POST Response Code: {}".format(r.status_code))
            else:
                print("\nHTTP POST Response Code: {}".format(r.status_code))
            if verbose:
                print("\nHeaders:\n")
                print(r.headers)
                print("\nResponse:\n")
                if r.text:
                    print(r.text)
                else:
                    print("None")


if __name__ == "__main__":
    main()
