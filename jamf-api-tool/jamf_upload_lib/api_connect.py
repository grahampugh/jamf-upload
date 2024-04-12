#!/usr/bin/env python3

import csv
import getpass
import json
import plistlib
import six
import tempfile
import xml.etree.cElementTree as ET

from base64 import b64encode

from . import curl, api_objects


def write_json_file(data):
    """dump some json to a temporary file"""
    tf = init_temp_file(suffix=".json")
    with open(tf, "w") as fp:
        json.dump(data, fp)
    return tf


def write_token_to_json_file(url, jamf_user, data, jamfupload_token_file=""):
    """dump the token, expiry, url and user as json to a temporary token file"""
    data["url"] = url
    data["user"] = jamf_user
    if not jamfupload_token_file:
        jamfupload_token_file = init_temp_file(
            prefix="jamf_upload_token_"
        )
    with open(jamfupload_token_file, "w") as fp:
        json.dump(data, fp)


def write_temp_file(data):
    """dump some text to a temporary file"""
    tf = init_temp_file(suffix=".txt")
    with open(tf, "w") as fp:
        fp.write(data)
    return tf


def write_csv_file(file, fields, data):
    """dump some text to a file"""
    with open(file, "w") as csvfile:
        # creating a csv dict writer object
        writer = csv.DictWriter(csvfile, fieldnames=fields)
    
        # writing headers (field names)
        writer.writeheader()
    
        # writing data rows
        writer.writerows(data)
        

def make_tmp_dir(tmp_dir="/tmp/jamf_upload_"):
    """make the tmp directory"""
    base_dir, dir = tmp_dir.rsplit("/", 1)
    jamfupload_tmp_dir = tempfile.mkdtemp(prefix=dir, dir=base_dir)
    return jamfupload_tmp_dir


def init_temp_file(prefix="jamf_upload_", suffix=None, dir=None, text=True):
    """dump some text to a temporary file"""
    return tempfile.mkstemp(
        prefix=prefix,
        suffix=suffix,
        dir=make_tmp_dir() if dir is None else dir,
        text=text,
    )[1]


def get_credentials(prefs_file):
    """return credentials from a prefs_file"""
    if prefs_file.endswith(".plist"):
        with open(prefs_file, "rb") as pl:
            if six.PY2:
                prefs = plistlib.readPlist(pl)
            else:
                prefs = plistlib.load(pl)
    read_as_json = (".json", ".env")
    if list(filter(prefs_file.endswith, read_as_json)) != []:
        with open(prefs_file) as js:
            prefs = json.load(js)

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
        slack_webhook = prefs["SLACK_WEBHOOK"]
    except KeyError:
        slack_webhook = ""
    return jamf_url, jamf_user, jamf_password, slack_webhook


def get_smb_credentials(prefs_file):
    """get SMB credentials from an existing AutoPkg prefs file"""
    with open(prefs_file, "rb") as pl:
        if six.PY2:
            prefs = plistlib.readPlist(pl)
        else:
            prefs = plistlib.load(pl)

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
    return smb_url, smb_user, smb_password


def encode_creds(jamf_user, jamf_password):
    """encode the username and password into a basic auth b64 encoded string so that we can
    get the session token"""
    credentials = "{}:{}".format(jamf_user, jamf_password)
    if six.PY2:
        enc_creds = b64encode(credentials)
    else:
        enc_creds_bytes = b64encode(credentials.encode("utf-8"))
        enc_creds = str(enc_creds_bytes, "utf-8")

    return enc_creds


# def get_uapi_token(jamf_url, enc_creds, verbosity):
#     """get a token for the Jamf Pro API"""
#     url = jamf_url + "/" + api_objects.api_endpoints("token")
#     r = curl.request("POST", url, enc_creds, verbosity)
#     if r.status_code == 200:
#         try:
#             token = r.output["token"]
#             if verbosity:
#                 print("Session token received")
#             return token
#         except KeyError:
#             print("ERROR: No token received")
#             return
#     else:
#         print("ERROR: No token received")
#         return

def get_uapi_token(jamf_url, jamf_user, enc_creds="", verbosity=""):
    """get a token for the Jamf Pro API or Classic API using basic auth"""
    if enc_creds:
        url = jamf_url + "/" + api_objects.api_endpoints("token")
        r = curl.request(
            method="POST",
            url=url,
            auth=enc_creds,
            verbosity=verbosity
        )
        output = json.loads(r.output)
        if r.status_code == 200:
            try:
                # token = str(output["token"])
                # expires = str(output["expires"])
                token = output["token"]
                expires = output["expires"]

                # write the data to a file
                write_token_to_json_file(jamf_url, jamf_user, output)
                print("Session token received")
                if verbosity:
                    print(f"Token: {token}")
                    print(f"Expires: {expires}")
                return token
            except KeyError:
                print("ERROR: No token received")
        else:
            print("ERROR: No token received")
    else:
        print("ERROR: No credentials given")


def get_creds_from_args(args):
    """call me directly - I return the all the creds and a hash of necesary ones too"""
    if args.prefs:
        (jamf_url, jamf_user, jamf_password, slack_webhook) = get_credentials(
            args.prefs
        )
    else:
        jamf_url = ""
        jamf_user = ""
        jamf_password = ""
        slack_webhook = ""

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

    # encode the username and password into a basic auth b64 encoded string so that we can
    # get the session token
    enc_creds = encode_creds(jamf_user, jamf_password)

    return jamf_url, jamf_user, jamf_password, slack_webhook, enc_creds
