#!/usr/bin/env python3

"""
A script to upload a package to the Jamf Cloud Distribution Point S3 bucket (JCDS 2.0)

Requirements from pip
boto3
requests
"""

import boto3
from botocore.exceptions import ClientError
import os.path
import requests
from requests.exceptions import HTTPError
import sys
import threading


# REQUIRED AUTHENTICATION VARIABLES
jamfProUser = ""
jamfProPassword = ""
jamfProBaseURL = ""

# path to package - UPDATE AS APPROPRIATE
pkg_path = os.path.join(
    "/Users/gpugh/sourcecode",
    "erase-install/pkg/erase-install/build/erase-install-30.0.pkg",
)


class ProgressPercentage(object):
    """display upload progress"""

    def __init__(self, filename):
        self._filename = filename
        self._size = float(os.path.getsize(filename))
        self._seen_so_far = 0
        self._lock = threading.Lock()

    def __call__(self, bytes_amount):
        # To simplify, assume this is hooked up to a single filename
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = (self._seen_so_far / self._size) * 100
            sys.stdout.write(
                "\r%s  %s / %s  (%.2f%%)"
                % (self._filename, self._seen_so_far, self._size, percentage)
            )
            sys.stdout.flush()


try:
    pkg = os.path.basename(pkg_path)

    response = requests.post(
        jamfProBaseURL + "/api/v1/auth/token",
        auth=(jamfProUser, jamfProPassword),
        data="",
    )
    response.raise_for_status()

    jsonResponse = response.json()
    print("Retreived Token: ")
    jamfProToken = jsonResponse["token"]
    print(jamfProToken)

    # Initiate Upload via Jamf Pro API
    headers = {"Accept": "application/json", "Authorization": "Bearer " + jamfProToken}

    print(headers)

    response = requests.post(
        jamfProBaseURL + "/api/v1/jcds/files", headers=headers, data=""
    )
    response.raise_for_status()

    credentials = response.json()
    print("Retreived Credentials Object: ")
    print(credentials)


except HTTPError as http_err:
    print(f"HTTP error occurred: {http_err}")
except Exception as err:
    print(f"Other error occurred: {err}")


# Upload File To AWS S3
s3_client = boto3.client(
    "s3",
    aws_access_key_id=credentials["accessKeyID"],
    aws_secret_access_key=credentials["secretAccessKey"],
    aws_session_token=credentials["sessionToken"],
)
try:
    response = s3_client.upload_file(
        pkg_path,
        credentials["bucketName"],
        credentials["path"] + pkg,
        Callback=ProgressPercentage(pkg_path),
    )
    print(response)
except ClientError as e:
    print(f"Failure uploading to S3: {e}")
