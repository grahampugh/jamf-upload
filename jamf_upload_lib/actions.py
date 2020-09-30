#!/usr/bin/env python3


import json
import os.path
import subprocess
import uuid
from collections import namedtuple


def substitute_assignable_keys(data, cli_custom_keys, verbosity):
    """substitutes any key in the inputted text using the %MY_KEY% nomenclature"""
    # whenever %MY_KEY% is found in a template, it is replaced with the assigned value of MY_KEY
    for custom_key in cli_custom_keys:
        if verbosity:
            print(
                f"Replacing any instances of '{custom_key}' with",
                f"'{cli_custom_keys[custom_key]}'",
            )
        data = data.replace(f"%{custom_key}%", cli_custom_keys[custom_key])
    return data


def nscurl(method, url, auth, verbosity, data="", additional_headers=""):
    """
    build an nscurl command based on method (GET, PUT, POST, DELETE)
    If the URL contains 'uapi' then token should be passed to the auth variable, 
    otherwise the enc_creds variable should be passed to the auth variable
    """
    headers_file = "/tmp/nscurl_headers_from_jamf_upload.txt"
    output_file = "/tmp/nscurl_output_from_jamf_upload.txt"

    # build the nscurl command
    nscurl_cmd = [
        "/usr/bin/nscurl",
        "-M",
        method,
        "-D",
        headers_file,
        "--output",
        output_file,
        url,
    ]

    # the authorisation is Basic unless we are using the uapi and already have a token
    if "uapi" in url and "tokens" not in url:
        nscurl_cmd.extend(["--header", "authorization: Bearer {}".format(auth)])
    else:
        nscurl_cmd.extend(["--header", "authorization: Basic {}".format(auth)])

    # set either Accept or Content-Type depending on method
    if method == "GET" or method == "DELETE":
        nscurl_cmd.extend(["--header", "Accept: application/json"])
    elif method == "POST" or method == "PUT":
        if data:
            nscurl_cmd.extend(["--upload", data])
        # uapi sends json, classic API must send xml
        if "uapi" in url:
            nscurl_cmd.extend(["--header", "Content-type: application/json"])
        else:
            nscurl_cmd.extend(["--header", "Content-type: application/xml"])
    else:
        print("WARNING: HTTP method {} not supported".format(method))

    # additional headers for advanced requests
    if additional_headers:
        nscurl_cmd.extend(additional_headers)

    # add verbose mode
    if verbosity > 1:
        nscurl_cmd.append("-v")

    if verbosity:
        print(nscurl_cmd)

    # now subprocess the nscurl command and build the r tuple which contains the
    # headers, status code and outputted data
    subprocess.check_output(nscurl_cmd)

    r = namedtuple("r", ["headers", "status_code", "output"])
    try:
        with open(headers_file, "r") as file:
            headers = file.readlines()
        r.headers = [x.strip() for x in headers]
        r.status_code = int(r.headers[0].split()[1])
        with open(output_file, "rb") as file:
            if "uapi" in url:
                r.output = json.load(file)
            else:
                r.output = file.read()
        return r
    except IOError:
        print("WARNING: {} not found".format(headers_file))


def write_json_file(data):
    """dump some json to a temporary file"""
    tf = os.path.join("/tmp", str(uuid.uuid4()))
    with open(tf, "w") as fp:
        json.dump(data, fp)
    return tf


def write_temp_file(data):
    """dump some text to a temporary file"""
    tf = os.path.join("/tmp", str(uuid.uuid4()))
    with open(tf, "w") as fp:
        fp.write(data)
    return tf


def status_check(r, endpoint_type, obj_name):
    """Return a message dependent on the HTTP response"""
    if r.status_code == 200 or r.status_code == 201:
        print("{} '{}' uploaded successfully".format(endpoint_type, obj_name))
        return "break"
    elif r.status_code == 409:
        print("WARNING: {} upload failed due to a conflict".format(endpoint_type))
        return "break"
    elif r.status_code == 401:
        print("ERROR: {} upload failed due to permissions error".format(endpoint_type))
        return "break"

