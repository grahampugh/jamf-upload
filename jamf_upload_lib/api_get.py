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


def check_api_obj_id_from_name(
    jamf_url, object_type, object_name, enc_creds, verbosity
):
    """check if a Classic API object with the same name exists on the server"""
    # define the relationship between the object types and their URL
    # we could make this shorter with some regex but I think this way is clearer
    object_types = {
        "package": "packages",
        "computer_group": "computergroups",
        "policy": "policies",
        "extension_attribute": "computerextensionattributes",
    }
    object_list_types = {
        "package": "packages",
        "computer_group": "computer_groups",
        "policy": "policies",
        "extension_attribute": "computer_extension_attributes",
    }
    headers = {
        "authorization": "Basic {}".format(enc_creds),
        "accept": "application/json",
    }
    url = "{}/JSSResource/{}".format(jamf_url, object_types[object_type])
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        object_list = json.loads(r.text)
        if verbosity > 2:
            print(object_list)
        obj_id = 0
        for obj in object_list[object_list_types[object_type]]:
            if verbosity > 2:
                print(obj)
            # we need to check for a case-insensitive match
            if obj["name"].lower() == object_name.lower():
                obj_id = obj["id"]
        return obj_id


def get_api_obj_value_from_id(
    jamf_url, object_type, obj_id, obj_path, enc_creds, verbosity
):
    """get the value of an item in a Classic API object"""
    # define the relationship between the object types and their URL
    # we could make this shorter with some regex but I think this way is clearer
    object_types = {
        "package": "packages",
        "computer_group": "computergroups",
        "policy": "policies",
        "extension_attribute": "computerextensionattributes",
    }
    headers = {
        "authorization": "Basic {}".format(enc_creds),
        "accept": "application/json",
    }
    url = "{}/JSSResource/{}/id/{}".format(jamf_url, object_types[object_type], obj_id)
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        obj_content = json.loads(r.text)
        if verbosity > 2:
            print(obj_content)

        # convert an xpath to json
        xpath_list = obj_path.split("/")
        value = obj_content[object_type]
        for i in range(0, len(xpath_list)):
            if xpath_list[i]:
                try:
                    value = value[xpath_list[i]]
                    if verbosity > 2:
                        print(value)
                except KeyError:
                    value = ""
                    break
        if value and verbosity > 2:
            print("Value of '{}': {}".format(obj_path, value))
        return value


def get_headers(r):
    print("\nHeaders:\n")
    print(r.headers)
    print("\nResponse:\n")
    if r.text:
        print(r.text)
    else:
        print("None")
