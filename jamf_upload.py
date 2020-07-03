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

Additional requests tools added based on:
https://findwork.dev/blog/advanced-usage-python-requests-timeouts-retries-hooks/
"""


import argparse
import getpass
import sys
import os
import json
from base64 import b64encode
from zipfile import ZipFile, ZIP_DEFLATED
import requests
from time import sleep
from requests_toolbelt.utils import dump
import plistlib
import subprocess
import xml.etree.ElementTree as ElementTree
import six

if six.PY2:
    input = raw_input


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

    jamf_url = prefs["JSS_URL"]
    jamf_user = prefs["API_USERNAME"]
    jamf_password = prefs["API_PASSWORD"]
    return jamf_url, jamf_user, jamf_password


def zip_pkg_path(path):
    """Add files from path to a zip file handle.

    Args:
        path (str): Path to folder to zip.

    Returns:
        (str) name of resulting zip file.
    """
    zip_name = "{}.zip".format(path)
    if os.path.exists(zip_name):
        print("Package object is a bundle. Zipped version already exists.")
        return zip_name

    print("Package object is a bundle. Converting to zip...")
    with ZipFile(zip_name, "w", ZIP_DEFLATED, allowZip64=True) as zip_handle:
        for root, _, files in os.walk(path):
            for member in files:
                zip_handle.write(os.path.join(root, member))
        print("Closing: {}".format(zip_name))
    return zip_name


def check_pkg(pkg_name, jamf_url, enc_creds):
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
        except KeyError:
            obj_id = "-1"
    else:
        obj_id = "-1"
    return obj_id


def post_pkg(pkg_name, pkg_path, jamf_url, enc_creds, obj_id, r_timeout, verbosity):
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

    http = requests.Session()
    if verbosity > 1:
        http.hooks["response"] = [logging_hook]

    r = http.post(url, files=files, headers=headers, timeout=r_timeout)
    return r


def curl_pkg(pkg_name, pkg_path, jamf_url, enc_creds, obj_id, r_timeout, verbosity):
    """sends the package"""
    url = "{}/dbfileupload".format(jamf_url)
    curl_cmd = [
        "/usr/bin/curl",
        "-X",
        "POST",
        "--header",
        "authorization: Basic {}".format(enc_creds),
        "--header",
        "DESTINATION: 0",
        "--header",
        "OBJECT_ID: {}".format(obj_id),
        "--header",
        "FILE_TYPE: 0",
        "--header",
        "FILE_NAME: {}".format(pkg_name),
        "--upload-file",
        pkg_path,
        "--connect-timeout",
        str("60"),
        "--max-time",
        str(r_timeout),
        url,
    ]
    if verbosity:
        print(curl_cmd)

    r = subprocess.check_output(curl_cmd)
    return r


def update_pkg_metadata(
    jamf_url, enc_creds, pkg_name, category, verbosity, pkg_id=None
):
    """Update package metadata. Currently only serves category"""

    # build the package record XML
    pkg_data = "<package>" + "<category>{}</category>".format(category) + "</package>"
    headers = {
        "authorization": "Basic {}".format(enc_creds),
        "Accept": "application/xml",
        "Content-type": "application/xml",
    }
    #  ideally we upload to the package ID but if we didn't get a good response
    #  we fall back to the package name
    if pkg_id:
        url = "{}/JSSResource/packages/id/{}".format(jamf_url, pkg_id)
    else:
        url = "{}/JSSResource/packages/name/{}".format(jamf_url, pkg_name)

    http = requests.Session()
    if verbosity > 1:
        http.hooks["response"] = [logging_hook]
        print(pkg_data)

    print("Updating package metadata...")

    count = 0
    while True:
        count += 1
        if verbosity > 1:
            print("Package update attempt {}".format(count))

        r = http.put(url, headers=headers, data=pkg_data, timeout=60)
        if r.status_code == 201:
            print("Package update successful")
            break
        if count > 5:
            print("\nHTTP POST Response Code: {}".format(r.status_code))
        sleep(30)

    if verbosity:
        print("\nHeaders:\n")
        print(r.headers)
        print("\nResponse:\n")
        if r.text:
            print(r.text)
        else:
            print("None")


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
        "--curl",
        help="use curl instead of requests (experimental)",
        action="store_true",
    )
    parser.add_argument(
        "--url", default="", help="the Jamf Pro Server URL",
    )
    parser.add_argument(
        "--user", default="", help="a user with the rights to upload a package",
    )
    parser.add_argument(
        "--timeout",
        default="3600",
        help="set timeout in seconds for HTTP request for problematic packages",
    )
    parser.add_argument(
        "--password",
        default="",
        help="password of the user with the rights to upload a package",
    )
    parser.add_argument(
        "--category",
        default="",
        help="a category to assign to the package (experimental)",
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

    # get HTTP request timeout
    r_timeout = float(args.timeout)

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
        pkg_name = os.path.basename(pkg_path)

        # See if the package is non-flat (requires zipping prior to upload).
        if os.path.isdir(pkg_path):
            pkg_path = zip_pkg_path(pkg_path)
            pkg_name += ".zip"

        # post the package
        print("\nChecking '{}' on {}".format(pkg_name, jamf_url))
        if args.verbose:
            print("Full path: {}'".format(pkg_path))

        # check for existing
        replace_pkg = True if args.replace else False
        obj_id = check_pkg(pkg_name, jamf_url, enc_creds)
        if obj_id == "-1" or replace_pkg:
            # post the package (won't run if the pkg exists and replace_pkg is False)
            if args.curl:
                r = curl_pkg(
                    pkg_name,
                    pkg_path,
                    jamf_url,
                    enc_creds,
                    obj_id,
                    r_timeout,
                    args.verbose,
                )
                try:
                    pkg_id = ElementTree.fromstring(r).findtext("id")
                    if pkg_id:
                        print("\nPackage uploaded successfully, ID={}".format(pkg_id))
                except ElementTree.ParseError:
                    print("Could not parse XML. Raw output:")
                    print(r.decode("ascii"))
                else:
                    if args.verbose:
                        if r:
                            print("\nResponse:\n")
                            print(r.decode("ascii"))
                        else:
                            print("No HTTP response")
            else:
                r = post_pkg(
                    pkg_name,
                    pkg_path,
                    jamf_url,
                    enc_creds,
                    obj_id,
                    r_timeout,
                    args.verbose,
                )
                # print result of the request
                if r.status_code == 200 or r.status_code == 201:
                    pkg_id = ElementTree.fromstring(r.text).findtext("id")
                    print("\nPackage uploaded successfully, ID={}".format(pkg_id))
                    if args.verbose:
                        print("HTTP POST Response Code: {}".format(r.status_code))
                else:
                    print("\nHTTP POST Response Code: {}".format(r.status_code))
                if args.verbose:
                    print("\nHeaders:\n")
                    print(r.headers)
                    print("\nResponse:\n")
                    if r.text:
                        print(r.text)
                    else:
                        print("None")

        #  now process the package metadata if specified
        if args.category:
            try:
                pkg_id
                update_pkg_metadata(
                    jamf_url, enc_creds, pkg_name, args.category, args.verbose, pkg_id
                )
            except UnboundLocalError:
                update_pkg_metadata(
                    jamf_url, enc_creds, pkg_name, args.category, args.verbose
                )

    print()


if __name__ == "__main__":
    main()
