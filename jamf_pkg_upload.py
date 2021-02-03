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
import hashlib
import os
import json
import re
import math
import io
import six
import xml.etree.ElementTree as ElementTree

from zipfile import ZipFile, ZIP_DEFLATED
from time import sleep
from urllib.parse import quote
from xml.sax.saxutils import escape

from jamf_upload_lib import api_connect, api_get, nscurl, curl, smb_actions

if six.PY2:
    input = raw_input  # pylint: disable=E0602  # noqa: F821
    from urlparse import urlparse  # pylint: disable=F0401
    from HTMLParser import HTMLParser  # pylint: disable=F0401

    html = HTMLParser()
else:
    from urllib.parse import urlparse
    import html


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
    r = curl.request("GET", url, enc_creds, verbosity)
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

    # look for existing session
    headers_file = "/tmp/curl_headers_from_jamf_upload.txt"
    try:
        with open(headers_file, "r") as file:
            headers = file.readlines()
        existing_headers = [x.strip() for x in headers]
        for header in existing_headers:
            if "APBALANCEID" in header:
                cookie = header.split()[1].rstrip(";")
                if verbosity > 1:
                    print("Existing cookie found: {}".format(cookie))
                cookies = cookie.split("=")
    except IOError:
        if verbosity > 1:
            print("No existing cookie found - starting new session")

    r = requests.post(
        url, data=files, headers=headers, cookies=cookies, timeout=r_timeout
    )
    return r


def curl_pkg(pkg_name, pkg_path, jamf_url, enc_creds, obj_id, r_timeout, verbosity):
    """uploads the package using curl"""
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
        "--connect-timeout",
        str("60"),
        "--max-time",
        str(r_timeout),
    ]
    r = curl.request("POST", url, enc_creds, verbosity, pkg_path, additional_headers)
    if verbosity:
        print("HTTP response: {}".format(r.status_code))
    return r.output


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
    jamf_url, enc_creds, pkg_name, pkg_metadata, hash_value, verbosity, pkg_id=None
):
    """Update package metadata. Currently only serves category"""

    if hash_value:
        hash_type = "SHA_512"
    else:
        hash_type = "MD5"

    # build the package record XML
    pkg_data = (
        "<package>"
        + f"<name>{pkg_name}</name>"
        + f"<filename>{pkg_name}</filename>"
        + f"<category>{escape(pkg_metadata['category'])}</category>"
        + f"<info>{escape(pkg_metadata['info'])}</info>"
        + f"<notes>{escape(pkg_metadata['notes'])}</notes>"
        + f"<priority>{pkg_metadata['priority']}</priority>"
        + f"<reboot_required>{pkg_metadata['reboot_required']}</reboot_required>"
        + f"<required_processor>{pkg_metadata['required_processor']}</required_processor>"
        + f"<os_requirement>{pkg_metadata['os_requirement']}</os_requirement>"
        + f"<hash_type>{hash_type}</hash_type>"
        + f"<hash_value>{hash_value}</hash_value>"
        + f"<send_notification>{pkg_metadata['send_notification']}</send_notification>"
        + "</package>"
    )

    #  ideally we upload to the package ID but if we didn't get a good response
    #  we fall back to the package name
    if pkg_id:
        method = "PUT"
        url = "{}/JSSResource/packages/id/{}".format(jamf_url, pkg_id)
    else:
        method = "POST"
        url = "{}/JSSResource/packages/name/{}".format(jamf_url, pkg_name)

    if verbosity > 2:
        print("Package data:")
        print(pkg_data)

    count = 0
    while True:
        count += 1
        if verbosity > 1:
            print(f"Package metadata upload attempt {count}")

        pkg_xml = curl.write_temp_file(pkg_data)
        r = curl.request(method, url, enc_creds, verbosity, pkg_xml)
        # check HTTP response
        if curl.status_check(r, "Package", pkg_name) == "break":
            break
        if count > 5:
            print("WARNING: Package metadata update did not succeed after 5 attempts")
            print(
                f"HTTP POST Response Code: {r.status_code}", verbose_level=1,
            )
            print("ERROR: Package metadata upload failed ")
            exit(-1)
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
    import requests  # pylint: disable=import-error

    http = requests.Session()
    r = http.post(jamf_url, data={"username": jamf_user, "password": jamf_password})
    return r, http


def scrape_upload_token(session, jamf_url, verbosity):
    """Retrieve the packages page from the web UI session to scrape the JCDS endpoint
    and data upload token for this session. Note that the JCDS endpoint varies by region."""
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

    import requests  # pylint: disable=import-error

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
    pkg_metadata,
    verbosity=0,
):
    """save the package using the web form, which should force JCDS into pending state."""
    # Create Package URL
    url = "{}/legacy/packages.html?id={}&o=c".format(jamf_url, str(obj_id))
    # TODO - not all metadata fields are represented here - need to find out if
    # they can be added and if we can add the hash. Also if we could upload a manifest file.
    r = session.post(
        url,
        data={
            "session-token": session_token,
            "lastTab": "General",
            "lastSideTab": "null",
            "lastSubTab": "null",
            "lastSubTabSet": "null",
            "name": pkg_name,
            "categoryID": str(pkg_metadata["category_id"]),
            "fileName": pkg_name,
            "resetFIELD_MANIFEST_INPUT": "",
            "info": pkg_metadata["info"],
            "notes": pkg_metadata["notes"],
            "priority": pkg_metadata["priority"],
            "uninstall_disabled": "true",
            "osRequirements": pkg_metadata["os_requirement"],
            "requiredProcessor": pkg_metadata["required_processor"],
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
        "--nscurl", help="use curl instead of curl", action="store_true",
    )
    parser.add_argument(
        "--requests", help="use requests instead of curl", action="store_true",
    )
    parser.add_argument(
        "--direct",
        help=(
            "use direct upload to JCDS (experimental, will not work if JCDS is not "
            "primary distribution point)"
        ),
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
        "--smb_url",
        default="",
        help=(
            "Path to an SMB FileShare Distribution Point, in the form "
            "smb://server/mountpoint"
        ),
    )
    parser.add_argument(
        "--smb_user",
        default="",
        help=(
            "a user with the rights to upload a package to the SMB FileShare "
            "Distribution Point"
        ),
    )
    parser.add_argument(
        "--smb_pass",
        default="",
        help=(
            "password of the user with the rights to upload a package to the SMB "
            "FileShare Distribution Point"
        ),
    )
    parser.add_argument(
        "--timeout",
        type=int,
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
            "or a separate plist anywhere (e.g. ~/.com.company.jamf_upload.plist)"
        ),
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="print verbose output headers",
    )
    # the following are for the package metadata
    parser.add_argument(
        "--category", default="", help="a category to assign to the package",
    )
    parser.add_argument(
        "--info", default="", help="an info string to assign to the package",
    )
    parser.add_argument(
        "--notes", default="", help="a notes string to assign to the package",
    )
    parser.add_argument(
        "--reboot_required",
        help="Set if the package requires a restart",
        action="store_true",
    )
    parser.add_argument(
        "--priority",
        type=int,
        choices=range(1, 21),
        default=10,
        help="a priority to assign to the package (default=10)",
    )
    parser.add_argument(
        "--os_requirement",
        default="",
        help="an OS requirements string to assign to the package",
    )
    parser.add_argument(
        "--required_processor",
        default="None",
        choices=["x86", "None"],
        help="a required processor to assign to the package. Acceptable values are 'x86' or 'None'",
    )
    parser.add_argument(
        "--send_notification",
        help="set to send a notification when the package is installed",
        action="store_true",
    )
    args = parser.parse_args()

    if (
        args.required_processor
        and args.required_processor != "x86"
        and args.required_processor != "None"
    ):
        args.required_processor = "None"
    if args.priority and args.priority < 1 or args.priority > 20:
        parser.error("Acceptable priority range is 1-20")

    return args


def sha512sum(filename):
    """calculate the SHA512 hash of the package
    (see https://stackoverflow.com/a/44873382)"""
    h = hashlib.sha512()
    b = bytearray(128 * 1024)
    mv = memoryview(b)
    with open(filename, "rb", buffering=0) as f:
        for n in iter(lambda: f.readinto(mv), 0):
            h.update(mv[:n])
    return h.hexdigest()


def main():
    """Do the main thing here"""
    print("\n** Jamf package upload script")
    print("** Uploads packages to Jamf Cloud or SMB Distribution Points.")

    #  parse the command line arguments
    args = get_args()
    verbosity = args.verbose

    #  create a dictionary of package metadata from the args
    pkg_metadata = {
        "category": args.category,
        "info": args.info,
        "notes": args.notes,
        "reboot_required": args.reboot_required,
        "priority": args.priority,
        "os_requirement": args.os_requirement,
        "required_processor": args.required_processor,
        "send_notification": args.send_notification,
    }

    # grab values from a prefs file if supplied
    (
        jamf_url,
        jamf_user,
        jamf_password,
        slack_webhook,
        enc_creds,
    ) = api_connect.get_creds_from_args(args)

    if args.prefs:
        smb_url, smb_user, smb_pass = api_connect.get_smb_credentials(args.prefs)
    else:
        smb_url = ""
        smb_user = ""
        smb_pass = ""

    # repeat for optional SMB share (but must supply a share path to invoke this)
    if args.smb_url:
        smb_url = args.smb_url
        if args.smb_user:
            smb_user = args.smb_user
        if not smb_user:
            smb_user = input(
                "Enter a user with read/write permissions to {} : ".format(smb_url)
            )
        if args.smb_pass:
            smb_pass = args.smb_pass
        if not smb_pass:
            if not smb_pass:
                smb_pass = getpass.getpass(
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
        # add to the pkg_metadata dictionary
        pkg_metadata["category_id"] = category_id

    # now process the list of packages
    for pkg_path in args.pkg:
        pkg_name = os.path.basename(pkg_path)

        # See if the package is non-flat (requires zipping prior to upload).
        if os.path.isdir(pkg_path):
            pkg_path = zip_pkg_path(pkg_path)
            pkg_name += ".zip"

        #  calculate the SHA-512 hash of the package
        sha512string = sha512sum(pkg_path)

        # check for existing package
        print("\nChecking '{}' on {}".format(pkg_name, jamf_url))
        if verbosity:
            print("Full path: {}".format(pkg_path))
        replace_pkg = True if args.replace else False
        obj_id = check_pkg(pkg_name, jamf_url, enc_creds, verbosity)
        if obj_id != "-1":
            print("Package '{}' already exists: ID {}".format(pkg_name, obj_id))
            pkg_id = obj_id  # assign pkg_id for smb runs - JCDS runs get it from the pkg upload
        else:
            pkg_id = ""

        # post the package (won't run if the pkg exists and replace_pkg is False)
        # process for SMB shares if defined
        if args.smb_url:
            # mount the share
            smb_actions.mount_smb(args.smb_url, args.smb_user, args.smb_pass, verbosity)
            # check for existing package
            local_pkg = check_local_pkg(args.smb_url, pkg_name, verbosity)
            if not local_pkg or replace_pkg:
                # copy the file
                smb_actions.copy_pkg(args.smb_url, pkg_path, pkg_name)
            # unmount the share
            smb_actions.umount_smb(args.smb_url)

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
                            pkg_metadata,
                            verbosity,
                        )
                # curl -> dbfileupload upload method option
                elif args.nscurl:
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
                # curl -> dbfileupload upload method option
                else:
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

        # now process the package metadata if a category is supplied,
        # or if we are dealing with an SMB share
        if not args.direct:
            if pkg_id:
                if verbosity:
                    print("Updating package metadata for {}".format(pkg_id))
                update_pkg_metadata(
                    jamf_url,
                    enc_creds,
                    pkg_name,
                    pkg_metadata,
                    sha512string,
                    verbosity,
                    pkg_id,
                )
            else:
                if verbosity:
                    print("Creating package metadata")
                update_pkg_metadata(
                    jamf_url, enc_creds, pkg_name, pkg_metadata, sha512string, verbosity
                )

    print()


if __name__ == "__main__":
    main()
