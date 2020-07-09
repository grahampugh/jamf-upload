#!/usr/bin/env python3

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
import re
import math
import io
from base64 import b64encode
from zipfile import ZipFile, ZIP_DEFLATED
import requests
from time import sleep
from requests_toolbelt.utils import dump
import plistlib
import subprocess
import xml.etree.ElementTree as ElementTree
from shutil import copyfile
import six

if six.PY2:
    input = raw_input
    from urlparse import urlparse
    from HTMLParser import HTMLParser
    html = HTMLParser()
else:
    from urllib.parse import urlparse
    import html

JCDS_CHUNK_SIZE = 52428800  # 50mb is the default


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
    try:
        smb_url = prefs["SMB_URL"]
    except KeyError:
        smb_url = ""
    try:
        smb_user = prefs["SMB_USERNAME"]
    except KeyError:
        smb_user = ""
    try:
        smb_password = prefs["SMB_PASSWORD"]
    except KeyError:
        smb_password = ""
    return jamf_url, jamf_user, jamf_password, smb_url, smb_user, smb_password


def mount_smb(mount_share, mount_user, mount_pass, verbosity):
    """Mount distribution point."""
    mount_cmd = [
        "/usr/bin/osascript",
        "-e",
        'mount volume "{}" as user name "{}" with password "{}"'.format(
            mount_share, mount_user, mount_pass
        ),
    ]
    if verbosity > 1:
        print("Mount command:\n{}".format(mount_cmd))

    r = subprocess.check_output(mount_cmd)
    if verbosity > 1:
        print("Mount command response:\n{}".format(r.decode("UTF-8")))


def umount_smb(mount_share):
    """Unmount distribution point."""
    path = "/Volumes{}".format(urlparse(mount_share).path)
    cmd = ["/usr/sbin/diskutil", "unmount", path]
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError:
        print("WARNING! Unmount failed.")


def check_local_pkg(mount_share, pkg_name, verbosity):
    """Check local DP or mounted share for existing package"""
    path = "/Volumes{}".format(urlparse(mount_share).path)
    if os.path.isdir(path):
        existing_pkg_path = os.path.join(path, "Packages", pkg_name)
        if os.path.isfile(existing_pkg_path):
            return existing_pkg_path
        else:
            print("No existing package found")
            if verbosity:
                print("Expected path: {}".format(existing_pkg_path))
    else:
        print("Expected path not found!: {}".format(path))


def copy_pkg(mount_share, pkg_path, pkg_name):
    """Copy package from AutoPkg Cache to local or mounted Distribution Point"""
    if os.path.isfile(pkg_path):
        path = "/Volumes{}".format(urlparse(mount_share).path)
        destination_pkg_path = os.path.join(path, "Packages", pkg_name)
        print("Copying {} to {}".format(pkg_name, destination_pkg_path))
        copyfile(pkg_path, destination_pkg_path)
    if os.path.isfile(destination_pkg_path):
        print("Package copy successful")
    else:
        print("Package copy failed")


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
    pkg_data = (
        "<package>"
        + "<name>{}</name>".format(pkg_name)
        + "<filename>{}</filename>".format(pkg_name)
        + "<category>{}</category>".format(category)
        + "</package>"
    )
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
        print("Package data:")
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
        if r.status_code == 409:
            print("WARNING: Package metadata update failed due to a conflict")
            break
        if count > 5:
            print("WARNING: Package metadata update did not succeed after 5 attempts")
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

def update_pkg_by_form(
    session, session_token, jamf_url, pkg_name, pkg_path, category=-1, verbosity=0
):
    """save the package using the web form, which should force JCDS into pending state."""
    url = "{}/legacy/packages.html?id=-1&o=c".format(jamf_url)  # Create Package URL
    r = session.post(url, data={
        'session-token': session_token,
        'lastTab': 'General',  # you dont really need these, but jamf does weird things with incomplete POJOs
        'lastSideTab': 'null',
        'lastSubTab': 'null',
        'lastSubTabSet': 'null',
        'name': pkg_name,
        'categoryID': str(category),
        'fileName': pkg_name,
        'resetFIELD_MANIFEST_INPUT': '',
        'info': '',
        'notes': '',
        'priority': '10',
        'uninstall_disabled': 'true',
        'osRequirements': '',
        'requiredProcessor': 'ppc',
        'switchWithPackageID': '-1',
        'action': 'Save',
    })

    if verbosity > 1:
        print(r.content)

    if r.status_code == 200:
        print("Successfully created package")
        query = urlparse(r.url).query
        matches = re.search(r'id=([^&]*)', query)
        if matches is None:
            print("No package id in redirected url")
        else:
            print("Package ID: {}".format(matches.group(1)))
    else:
        print("Package creation failed")


def login(jamf_url, jamf_user, jamf_password, verbosity):  # type: (str, str, str, int) -> any
    """create a web UI Session, required to scrape jcds information."""
    http = requests.Session()
    # if verbosity > 1:
    #     http.hooks["response"] = [logging_hook]

    r = http.post(jamf_url, data={'username': jamf_user, 'password': jamf_password})
    return r, http

def scrape_upload_token(session, jamf_url, verbosity):  # type: (requests.Session, str, int) -> any
    """retrieve the packages page to scrape the jcds endpoint and data upload token for this session."""
    url = '{}/legacy/packages.html?id=-1&o=c'.format(jamf_url)
    r = session.get(url)
    if six.PY3:
        text = r.text
    else:
        text = r.content

    if verbosity > 1:
        print("huge amount of html follows")
        print("------")
        print(text)
        print("------")

    matches = re.search(r'data-base-url="([^"]*)"', text)
    if matches is None:
        print("WARNING: No JCDS distribution point URL was found")
        print("- Are you sure that JCDS is your Primary distribution point?")

    jcds_base_url_urlencoded = matches.group(1)

    matches = re.search(r'data-upload-token="([^"]*)"', text)
    if matches is None:
        print("WARNING: No JCDS upload token was found")
        print("- Are you sure that JCDS is your Primary distribution point?")

    jcds_upload_token = matches.group(1)

    matches = re.search(r'id="session-token" value="([^"]*)"', text)
    if matches is None:
        print("WARNING: No package upload session token was found")

    session_token = matches.group(1)

    jcds_base_url = html.unescape(jcds_base_url_urlencoded)
    return jcds_base_url, jcds_upload_token, session_token

# def post_pkg(pkg_name, pkg_path, jamf_url, enc_creds, obj_id, r_timeout, verbosity):
def post_pkg_chunks(pkg_name, pkg_path, jcds_base_url, jcds_upload_token, obj_id, verbosity=0):
    fsize = os.stat(pkg_path).st_size
    total_chunks = int(math.ceil(fsize / JCDS_CHUNK_SIZE))
    resource = open(pkg_path, "rb")

    headers = {"X-Auth-Token": jcds_upload_token}
    http = requests.Session()

    chunks_json = []
    for chunk in range(0, total_chunks):
        resource.seek(chunk * JCDS_CHUNK_SIZE)
        chunk_data = resource.read(JCDS_CHUNK_SIZE)
        chunk_reader = io.BytesIO(chunk_data)
        chunk_url = "{}/{}/part?chunk={}&chunks={}".format(
            jcds_base_url, pkg_name, chunk, total_chunks)

        r = http.post(chunk_url, files={'file': chunk_reader}, headers=headers)
        print("uploaded chunk {} of {}".format(chunk + 1, total_chunks))
        if verbosity > 1:
            print(r.json())

        chunks_json.append(r.json())

    resource.close()
    return chunks_json

def get_args():
    """Parse any command line arguments"""
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
        "--direct",
        help="use direct upload to JCDS (experimental, will not work if JCDS is not primary distribution point)",
        action="store_true"
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
        "--share",
        default="",
        help=(
            "Path to an SMB FileShare Distribution Point, in the form "
            "smb://server/mountpoint"
        ),
    )
    parser.add_argument(
        "--shareuser",
        default="",
        help=(
            "a user with the rights to upload a package to the SMB FileShare "
            "Distribution Point"
        ),
    )
    parser.add_argument(
        "--sharepass",
        default="",
        help=(
            "password of the user with the rights to upload a package to the SMB "
            "FileShare Distribution Point"
        ),
    )
    parser.add_argument(
        "--category",
        default="",
        help="a category to assign to the package (experimental)",
    )
    parser.add_argument(
        "--timeout",
        default="3600",
        help="set timeout in seconds for HTTP request for problematic packages",
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
    print("\n** Jamf Cloud package upload script")
    print("** Uploads packages to Jamf Cloud Distribution Points.\n")

    #  parse the command line arguments
    args = get_args()

    # grab values from a prefs file if supplied
    if args.prefs:
        (
            jamf_url,
            jamf_user,
            jamf_password,
            smb_url,
            smb_user,
            smb_password,
        ) = get_credentials(args.prefs)
    else:
        jamf_url = ""
        jamf_user = ""
        jamf_password = ""
        smb_url = ""
        smb_user = ""
        smb_password = ""

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

    # repeat for optional SMB share (but must supply a share path to invoke this)
    if args.share:
        smb_url = args.share
    if smb_url:
        if args.shareuser:
            smb_user = args.shareuser
        elif not smb_user:
            smb_user = input(
                "Enter a user with read/write permissions to {} : ".format(smb_url)
            )
        if args.sharepass:
            smb_password = args.sharepass
        elif not smb_password:
            smb_password = getpass.getpass(
                "Enter the password for '{}' : ".format(smb_user)
            )

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

    if args.direct:  # establish a web login session which is reusable for scraping tokens
        r, login_session = login(
            jamf_url,
            jamf_user,
            jamf_password,
            args.verbose,
        )
        if r.status_code != 200:
            print("Failed to log in to the Jamf instance at: {}".format(jamf_url))

    # now process the list of packages
    for pkg_path in args.pkg:
        pkg_name = os.path.basename(pkg_path)

        # See if the package is non-flat (requires zipping prior to upload).
        if os.path.isdir(pkg_path):
            pkg_path = zip_pkg_path(pkg_path)
            pkg_name += ".zip"

        # check for existing package
        print("\nChecking '{}' on {}".format(pkg_name, jamf_url))
        if args.verbose:
            print("Full path: {}".format(pkg_path))
        replace_pkg = True if args.replace else False
        obj_id = check_pkg(pkg_name, jamf_url, enc_creds)

        # post the package (won't run if the pkg exists and replace_pkg is False)
        #  process for SMB shares if defined
        if smb_url:
            # mount the share
            mount_smb(smb_url, smb_user, smb_password, args.verbose)
            #  check for existing package
            local_pkg = check_local_pkg(args.share, pkg_name, args.verbose)
            if not local_pkg or replace_pkg:
                # copy the file
                copy_pkg(smb_url, pkg_path, pkg_name)
            # unmount the share
            umount_smb(smb_url)

        #  otherwise process for cloud DP
        else:
            if obj_id == "-1" or replace_pkg:
                if args.direct:
                    jcds_url, jcds_token, session_token = scrape_upload_token(login_session, jamf_url, args.verbose)
                    if jcds_url and jcds_token and session_token:
                        print("JCDS URL: {}".format(jcds_url))
                        print("JCDS Upload token: {}".format(jcds_token))
                        print("Session token: {}".format(session_token))

                        chunks_json = post_pkg_chunks(
                            pkg_name,
                            pkg_path,
                            jcds_url,
                            jcds_token,
                            obj_id,
                            args.verbose,
                        )

                        update_pkg_by_form(
                            login_session,
                            session_token,
                            jamf_url,
                            pkg_name,
                            pkg_path,
                        )

                        # TODO: need to save pkg again to force JCDS to recombine chunks

                elif args.curl:
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
                            print(
                                "\nPackage uploaded successfully, ID={}".format(pkg_id)
                            )
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

        # now process the package metadata if a category is supplied,
        # or if we are dealing with an SMB share
        if args.category or smb_url:
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
