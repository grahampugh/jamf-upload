#!/usr/bin/env python3

import json
import os
import subprocess
import argparse
import getpass

from base64 import b64encode
from collections import namedtuple


def get_args():
    """Parse any command line arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="", help="the Jamf Pro Server URL")
    parser.add_argument(
        "--user", default="", help="a user with the rights to delete a policy"
    )
    parser.add_argument(
        "--password",
        default="",
        help="password of the user with the rights to delete a policy",
    )
    args = parser.parse_args()
    return args


def make_tmp_dir(tmp_dir="/tmp/jamf_upload"):
    """make the tmp directory"""
    if not os.path.exists(tmp_dir):
        os.mkdir(tmp_dir)
    return tmp_dir


def request(url, auth):
    tmp_dir = make_tmp_dir()
    headers_file = os.path.join(tmp_dir, "curl_headers_from_jamf_upload.txt")
    output_file = os.path.join(tmp_dir, "curl_output_from_jamf_upload.txt")
    # cookie_jar = os.path.join(tmp_dir, "curl_cookies_from_jamf_upload.txt")

    # build the curl command
    curl_cmd = [
        "/usr/bin/curl",
        "-X",
        "POST",
        "-D",
        headers_file,
        "--output",
        output_file,
        url,
    ]
    curl_cmd.extend(["--header", "authorization: Basic {}".format(auth)])
    curl_cmd.extend(["--header", "Content-type: application/json"])

    print("\ncurl command:\n{}".format(" ".join(curl_cmd)))
    print("(note this may omit essential quotation marks - do not copy-and-paste!")

    try:
        subprocess.check_output(curl_cmd)
    except subprocess.CalledProcessError:
        print(f"ERROR: possible URL error ({url}) or timeout.")
        exit()

    r = namedtuple("r", ["headers", "status_code", "output"])
    try:
        with open(headers_file, "r") as file:
            headers = file.readlines()
        r.headers = [x.strip() for x in headers]
        for header in r.headers:
            if "HTTP/1.1" in header and "Continue" not in header:
                r.status_code = int(header.split()[1])
    except IOError:
        print("WARNING: {} not found".format(headers_file))
    if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
        with open(output_file, "rb") as file:
            r.output = json.load(file)
    else:
        print(f"No output from request ({output_file} not found or empty)")

    return r


def encode_creds(jamf_user, jamf_password):
    """encode the username and password into a basic auth b64 encoded string so that we can
    get the session token"""
    credentials = f"{jamf_user}:{jamf_password}"
    enc_creds_bytes = b64encode(credentials.encode("utf-8"))
    enc_creds = str(enc_creds_bytes, "utf-8")
    print(enc_creds)

    return enc_creds


def get_creds_from_args(args):
    """call me directly - I return the all the creds and a hash of necesary ones too"""
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

    # encode the username and password into a basic auth b64 encoded string so that we can
    # get the session token
    enc_creds = encode_creds(jamf_user, jamf_password)

    return jamf_url, enc_creds


def get_uapi_token(jamf_url, enc_creds):
    """get a token for the Jamf Pro API"""
    url = "{}/uapi/auth/tokens".format(jamf_url)
    r = request(url, enc_creds)
    if r.status_code == 200:
        try:
            token = str(r.output["token"])
            print(f"Session token received (status code={r.status_code})")
            return token
        except KeyError:
            print(f"ERROR: No token received (status code={r.status_code})")
            return
    else:
        print(f"ERROR: No token received (status code={r.status_code})")
        return


def main():
    """Do the main thing here"""
    # parse the command line arguments
    args = get_args()

    # grab values from a prefs file if supplied
    jamf_url, enc_creds = get_creds_from_args(args)

    # now get the session token
    token = get_uapi_token(jamf_url, enc_creds)
    print(token)


if __name__ == "__main__":
    main()
