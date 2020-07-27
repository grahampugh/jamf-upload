#!/usr/bin/env python3

import json
import requests

from . import api_connect


def get_uapi_obj_id_from_name(jamf_url, object_type, object_name, token, verbosity):
    """The UAPI doesn't have a name object, so we have to get the list of scripts 
    and parse the name to get the id """
    headers = {
        "authorization": "Bearer {}".format(token),
        "accept": "application/json",
    }
    url = "{}/uapi/v1/{}".format(jamf_url, object_type)
    http = requests.Session()
    if verbosity > 2:
        http.hooks["response"] = [api_connect.logging_hook]

    r = http.get(url, headers=headers)
    if r.status_code == 200:
        object_list = json.loads(r.text)
        obj_id = 0
        for obj in object_list["results"]:
            if verbosity > 2:
                print(obj)
            if obj["name"] == object_name:
                obj_id = obj["id"]
        return obj_id


def get_headers(r):
    print("\nHeaders:\n")
    print(r.headers)
    print("\nResponse:\n")
    if r.text:
        print(r.text)
    else:
        print("None")
