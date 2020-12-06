#!/usr/bin/env python3

import getpass
import json
import plistlib
import six
from base64 import b64encode

from . import curl


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


def get_uapi_token(jamf_url, enc_creds, verbosity):
    """get a token for the Jamf Pro API"""
    url = "{}/uapi/auth/tokens".format(jamf_url)
    r = curl.request("POST", url, enc_creds, verbosity)
    if r.status_code == 200:
        try:
            token = str(r.output["token"])
            print("Session token received")
            return token
        except KeyError:
            print("ERROR: No token received")
            return
    else:
        print("ERROR: No token received")
        return


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
