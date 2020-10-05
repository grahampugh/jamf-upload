#!/usr/bin/env python3

"""
** Jamf Package Upload Script
   by G Pugh

Developed from an idea posted at
https://www.jamf.com/jamf-nation/discussions/27869#responseChild166021

Incorporates a method for uploading packages using the web UI's method thanks to @mosen

Credentials can be supplied from the command line as arguments, or inputted, or 
from an existing PLIST containing values for JSS_URL, API_USERNAME and API_PASSWORD, 
for example an AutoPkg preferences file which has been configured for use with 
JSSImporter: ~/Library/Preferences/com.github.autopkg

For usage, run jamf_pkg_upload.py --help
"""


import argparse
import getpass
import sys
import os
import json
import re
import math
import io
import plistlib
import six
import subprocess
import xml.etree.ElementTree as ElementTree

from base64 import b64encode
from zipfile import ZipFile, ZIP_DEFLATED
from time import sleep
from urllib.parse import quote
from shutil import copyfile

from jamf_upload_lib import api_connect, api_get, actions, nscurl

if six.PY2:
    input = raw_input  # pylint: disable=E0602
    from urlparse import urlparse  # pylint: disable=F0401
    from HTMLParser import HTMLParser  # pylint: disable=F0401

    html = HTMLParser()
else:
    from urllib.parse import urlparse
    import html


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


def check_pkg(pkg_name, jamf_url, enc_creds, verbosity):
    """check if a package with the same name exists in the repo
    note that it is possible to have more than one with the same name
    which could mess things up"""
    url = "{}/JSSResource/packages/name/{}".format(jamf_url, quote(pkg_name))
    r = nscurl.request("GET", url, enc_creds, verbosity)
    if r.status_code == 200:
        obj = json.loads(r.output)
        try:
            obj_id = str(obj["package"]["id"])
        except KeyError:
            obj_id = "-1"
    else:
        obj_id = "-1"
    return obj_id


def post_pkg(pkg_name, pkg_path, jamf_url, enc_creds, obj_id, r_timeout, verbosity):
    """sends the package using requests"""
    try:
        import requests
    except ImportError:
        print(
            "WARNING: could not import requests module. Use pip to install requests and try again."
        )
        sys.exit()

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

    r = http.post(url, data=files, headers=headers, timeout=r_timeout)
    return r


def curl_pkg(pkg_name, pkg_path, jamf_url, enc_creds, obj_id, r_timeout, verbosity):
    """uploads the package using curl"""
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


def nscurl_pkg(pkg_name, pkg_path, jamf_url, enc_creds, obj_id, r_timeout, verbosity):
    """uploads the package using nscurl"""
    url = "{}/dbfileupload".format(jamf_url)
    additional_headers = [
        "--header",
        "DESTINATION: 0",
        "--header",
        "OBJECT_ID: {}".format(obj_id),
        "--header",
        "FILE_TYPE: 0",
        "--header",
        "FILE_NAME: {}".format(pkg_name),
        "--payload-transmission-timeout",
        str(r_timeout),
    ]
    r = nscurl.request("POST", url, enc_creds, verbosity, pkg_path, additional_headers)
    if verbosity:
        print("HTTP response: {}".format(r.status_code))
    return r.output


def update_pkg_metadata(
    jamf_url, enc_creds, pkg_name, category, verbosity, pkg_id=None
):
    """Update package metadata. Currently only serves category"""

    # build the package record XML
    #  TODO add other package options
    pkg_data = (
        "<package>"
        + "<name>{}</name>".format(pkg_name)
        + "<filename>{}</filename>".format(pkg_name)
        + "<category>{}</category>".format(category)
        + "</package>"
    )

    #  ideally we upload to the package ID but if we didn't get a good response
    #  we fall back to the package name
    if pkg_id:
        url = "{}/JSSResource/packages/id/{}".format(jamf_url, pkg_id)
    else:
        url = "{}/JSSResource/packages/name/{}".format(jamf_url, pkg_name)

    if verbosity > 2:
        print("Package data:")
        print(pkg_data)

    print("Updating package metadata...")

    count = 0
    while True:
        count += 1
        if verbosity > 1:
            print("Package update attempt {}".format(count))

        pkg_xml = nscurl.write_temp_file(pkg_data)
        r = nscurl.request("PUT", url, enc_creds, verbosity, pkg_xml)
        # check HTTP response
        if nscurl.status_check(r, "Package", pkg_name) == "break":
            break
        if count > 5:
            print("WARNING: Package metadata update did not succeed after 5 attempts")
            print("\nHTTP POST Response Code: {}".format(r.status_code))
            break
        sleep(30)

    if verbosity:
        api_get.get_headers(r)

    # clean up temp files
    if os.path.exists(pkg_xml):
        os.remove(pkg_xml)


def login(
    jamf_url, jamf_user, jamf_password, verbosity
):  # type: (str, str, str, int) -> any
    """For creating a web UI Session, which is required to scrape JCDS information."""
    import requests

    http = requests.Session()
    r = http.post(jamf_url, data={"username": jamf_user, "password": jamf_password})
    return r, http


def scrape_upload_token(
    session, jamf_url, verbosity
):  # type: (requests.Session, str, int) -> any
    """Retrieve the packages page from the web UI session to scrape the JCDS endpoint and data upload token for this session. Note that the JCDS endpoint varies by region."""
    url = "{}/legacy/packages.html?id=-1&o=c".format(jamf_url)
    r = session.get(url)
    if six.PY2:
        text = r.content
    else:
        text = r.text

    if verbosity > 2:
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


def post_pkg_chunks(
    pkg_name,
    pkg_path,
    jcds_base_url,
    jcds_upload_token,
    obj_id,
    jcds_chunk_mb,
    verbosity=0,
):
    """sends the package in chunks"""

    import requests

    jcds_chunk_size = int(jcds_chunk_mb) * 1048576  # 1mb is the default
    file_size = os.stat(pkg_path).st_size
    total_chunks = int(math.ceil(file_size / jcds_chunk_size))
    resource = open(pkg_path, "rb")

    headers = {
        "X-Auth-Token": jcds_upload_token,
        "content-type": "application/xml",
    }
    http = requests.Session()

    for chunk in range(0, total_chunks):
        resource.seek(chunk * jcds_chunk_size)
        chunk_data = resource.read(jcds_chunk_size)
        chunk_reader = io.BytesIO(chunk_data)
        chunk_url = "{}/{}/part?chunk={}&chunks={}".format(
            jcds_base_url, html.escape(pkg_name), chunk, total_chunks
        )
        if verbosity > 1:
            print("URL to post chunks: {}".format(chunk_url))

        r = http.post(chunk_url, files={"file": chunk_reader}, headers=headers)
        print("Uploaded chunk {} of {}".format(chunk + 1, total_chunks))
        if verbosity > 2:
            print(r)

    resource.close()


def update_pkg_by_form(
    session,
    session_token,
    jamf_url,
    pkg_name,
    pkg_path,
    obj_id,
    category_id="-1",
    verbosity=0,
):
    """save the package using the web form, which should force JCDS into pending state."""
    # Create Package URL
    url = "{}/legacy/packages.html?id={}&o=c".format(jamf_url, str(obj_id))
    r = session.post(
        url,
        data={
            "session-token": session_token,
            "lastTab": "General",
            "lastSideTab": "null",
            "lastSubTab": "null",
            "lastSubTabSet": "null",
            "name": pkg_name,
            "categoryID": str(category_id),
            "fileName": pkg_name,
            "resetFIELD_MANIFEST_INPUT": "",
            "info": "",
            "notes": "",
            "priority": "10",
            "uninstall_disabled": "true",
            "osRequirements": "",
            "requiredProcessor": "None",
            "switchWithPackageID": "-1",
            "action": "Save",
        },
    )

    if verbosity > 1:
        print(r.content)

    if r.status_code == 200:
        print("Successfully created package")
        query = urlparse(r.url).query
        matches = re.search(r"id=([^&]*)", query)
        if matches is None:
            print("No package id in redirected url")
        else:
            pkg_id = matches.group(1)
            print("Package ID: {}".format(pkg_id))
            return pkg_id
    else:
        print("Package creation failed")


def get_args():
    """Parse any command line arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "pkg", nargs="+", help="Full path to the package(s) to upload",
    )
    parser.add_argument(
        "--replace", help="overwrite an existing uploaded package", action="store_true",
    )
    parser.add_argument(
        "--curl", help="use curl instead of nscurl", action="store_true",
    )
    parser.add_argument(
        "--requests", help="use requests instead of nscurl", action="store_true",
    )
    parser.add_argument(
        "--direct",
        help="use direct upload to JCDS (experimental, will not work if JCDS is not primary distribution point)",
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
        "--category", default="", help="a category to assign to the package",
    )
    parser.add_argument(
        "--timeout",
        default="3600",
        help="set timeout in seconds for HTTP request for problematic packages",
    )
    parser.add_argument(
        "--chunksize", default="1", help="set chunk size in megabytes",
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
    print("\n** Jamf package upload script")
    print("** Uploads packages to Jamf Cloud or SMB Distribution Points.")

    #  parse the command line arguments
    args = get_args()
    verbosity = args.verbose

    # grab values from a prefs file if supplied
    jamf_url, jamf_user, jamf_password, enc_creds = api_connect.get_creds_from_args(
        args
    )

    if args.prefs:
        smb_url, smb_user, smb_password = api_connect.get_smb_credentials(args.prefs)
    else:
        smb_url = ""
        smb_user = ""
        smb_password = ""

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

    if not args.pkg:
        pkg = input("Enter the full path to the package to upload: ")
        args.pkg = pkg

    # establish a web login session which is reusable for scraping tokens
    if args.direct:
        r, login_session = login(jamf_url, jamf_user, jamf_password, verbosity)
        if r.status_code != 200:
            print("Failed to log in to the Jamf instance at: {}".format(jamf_url))

    # get the id for a category if supplied
    if args.category:
        print("Checking ID for category '{}'".format(args.category))

        # now get the session token
        token = api_connect.get_uapi_token(jamf_url, enc_creds, verbosity)

        category_id = api_get.get_uapi_obj_id_from_name(
            jamf_url, "categories", args.category, token, verbosity
        )
        if not category_id:
            print("WARNING: Category not found!")
            category_id = "-1"

    # now process the list of packages
    for pkg_path in args.pkg:
        pkg_name = os.path.basename(pkg_path)

        # See if the package is non-flat (requires zipping prior to upload).
        if os.path.isdir(pkg_path):
            pkg_path = zip_pkg_path(pkg_path)
            pkg_name += ".zip"

        # check for existing package
        print("\nChecking '{}' on {}".format(pkg_name, jamf_url))
        if verbosity:
            print("Full path: {}".format(pkg_path))
        replace_pkg = True if args.replace else False
        obj_id = check_pkg(pkg_name, jamf_url, enc_creds, verbosity)

        # post the package (won't run if the pkg exists and replace_pkg is False)
        # process for SMB shares if defined
        if smb_url:
            # mount the share
            mount_smb(smb_url, smb_user, smb_password, verbosity)
            #  check for existing package
            local_pkg = check_local_pkg(args.share, pkg_name, verbosity)
            if not local_pkg or replace_pkg:
                # copy the file
                copy_pkg(smb_url, pkg_path, pkg_name)
            # unmount the share
            umount_smb(smb_url)

        # otherwise process for cloud DP
        else:
            if obj_id == "-1" or replace_pkg:
                # JCDS direct upload method option
                if args.direct:
                    jcds_url, jcds_token, session_token = scrape_upload_token(
                        login_session, jamf_url, verbosity
                    )
                    if jcds_url and jcds_token and session_token:
                        if verbosity:
                            print("JCDS URL: {}".format(jcds_url))
                            print("JCDS Upload token: {}".format(jcds_token))
                            print("Session token: {}".format(session_token))

                        #  post the package as chunks
                        post_pkg_chunks(
                            pkg_name,
                            pkg_path,
                            jcds_url,
                            jcds_token,
                            obj_id,
                            args.chunksize,
                            verbosity,
                        )

                        #  now create the package object and get the pkg ID
                        pkg_id = update_pkg_by_form(
                            login_session,
                            session_token,
                            jamf_url,
                            pkg_name,
                            pkg_path,
                            obj_id,
                            category_id,
                            verbosity,
                        )
                # curl -> dbfileupload upload method option
                elif args.curl:
                    r = curl_pkg(
                        pkg_name,
                        pkg_path,
                        jamf_url,
                        enc_creds,
                        obj_id,
                        r_timeout,
                        verbosity,
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
                        if verbosity:
                            if r:
                                print("\nResponse:\n")
                                print(r.decode("ascii"))
                            else:
                                print("No HTTP response")
                # requests -> dbfileupload upload method option
                elif args.requests:
                    r = post_pkg(
                        pkg_name,
                        pkg_path,
                        jamf_url,
                        enc_creds,
                        obj_id,
                        r_timeout,
                        verbosity,
                    )
                    # print result of the request
                    if r.status_code == 200 or r.status_code == 201:
                        pkg_id = ElementTree.fromstring(r.text).findtext("id")
                        print("\nPackage uploaded successfully, ID={}".format(pkg_id))
                        if verbosity:
                            print("HTTP POST Response Code: {}".format(r.status_code))
                    else:
                        print("\nHTTP POST Response Code: {}".format(r.status_code))
                    if verbosity:
                        api_get.get_headers(r)
                # nscurl -> dbfileupload upload method option
                else:
                    r = nscurl_pkg(
                        pkg_name,
                        pkg_path,
                        jamf_url,
                        enc_creds,
                        obj_id,
                        r_timeout,
                        verbosity,
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
                        if verbosity:
                            if r:
                                print("\nResponse:\n")
                                print(r.decode("ascii"))
                            else:
                                print("No HTTP response")

        # now process the package metadata if a category is supplied,
        # or if we are dealing with an SMB share
        if (args.category or smb_url) and not args.direct:
            try:
                pkg_id
                update_pkg_metadata(
                    jamf_url, enc_creds, pkg_name, args.category, verbosity, pkg_id
                )
            except UnboundLocalError:
                update_pkg_metadata(
                    jamf_url, enc_creds, pkg_name, args.category, verbosity
                )

    print()


if __name__ == "__main__":
    main()
