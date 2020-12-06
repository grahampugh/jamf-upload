#!/usr/bin/env python3

import json
import subprocess
import sys  # temp
from urllib.parse import quote

from . import curl


def object_types(object_type):
    """return a dictionary of jamf API objects and their corresponding URI names"""
    # define the relationship between the object types and their URL
    # we could make this shorter with some regex but I think this way is clearer
    object_types = {
        "package": "packages",
        "computer_group": "computergroups",
        "policy": "policies",
        "category_all_items": "policies/category",        
        "category_all": "categories",
        "extension_attribute": "computerextensionattributes",
        "os_x_configuration_profile": "osxconfigurationprofiles",
        "computer": "computers",
    }
    return object_types[object_type]


def object_list_types(object_type):
    """return a dictionary of jamf API objects and their corresponding URI names"""
    # define the relationship between the object types and the xml key in a GET request of all objects
    # we could make this shorter with some regex but I think this way is clearer
    object_list_types = {
        "package": "packages",
        "computer_group": "computer_groups",
        "policy": "policies",
        "category_all_items": "policies/category",        
        "category_all": "categories",        
        "extension_attribute": "computer_extension_attributes",
        "os_x_configuration_profile": "os_x_configuration_profiles",
        "computer": "computers",
    }
    return object_list_types[object_type]


def get_uapi_obj_id_from_name(jamf_url, object_type, object_name, token, verbosity):
    """Get the UAPI object by name"""
    url = (
        f"{jamf_url}/uapi/v1/{object_type}?page=0&page-size=1000&sort=id"
        f"&filter=name%3D%3D%22{quote(object_name)}%22"
    )
    r = curl.request("GET", url, token, verbosity)
    if r.status_code == 200:
        obj_id = 0
        for obj in r.output["results"]:
            if verbosity > 2:
                print("\nAPI object:")
                print(obj)
            if obj["name"] == object_name:
                obj_id = obj["id"]
        return obj_id

# now there's a find all generic
def check_api_finds_all(
    jamf_url, object_type, enc_creds, verbosity
):
    """pass this string:policies to return all policies, pass string:categories_all for all categories"""

    url = "{}/JSSResource/{}".format(jamf_url, object_types(object_type))
    r = curl.request("GET", url, enc_creds, verbosity)

    if r.status_code == 200:
        object_list = json.loads(r.output)
        obj = object_list[object_types(object_type)]        
        if verbosity > 3:
            print("\nAPI object raw output:")
            print(object_list)

        if verbosity > 2:
            print("\nAPI object list:")
            print(obj)
        return obj


def check_api_category_policies_from_name(
    jamf_url, object_type, object_name, enc_creds, verbosity
):
    """return all policies in a category"""

    url = "{}/JSSResource/{}/{}".format(jamf_url, object_types(object_type), object_name)
    r = curl.request("GET", url, enc_creds, verbosity)

    if r.status_code == 200:
        object_list = json.loads(r.output)
        obj = object_list['policies']        
        if verbosity > 3:
            print("\nAPI object raw output:")
            print(object_list)

        if verbosity > 2:
            print("\nAPI object list:")
            print(obj)
        return obj


def get_api_obj_id_from_name(
    jamf_url, object_type, object_name, enc_creds, verbosity
):
    """returns an ID of a policy if it exists"""

    url = "{}/JSSResource/{}".format(jamf_url, object_types(object_type))        
    r = curl.request("GET", url, enc_creds, verbosity)

    if r.status_code == 200:
        object_list = json.loads(r.output)
        if verbosity > 3:
            print("\nAPI object raw output:")
            print(object_list)
        obj_id = 0
        if verbosity > 2:
            print("\nAPI object list:")
        for obj in object_list[object_list_types(object_type)]:
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

    url = "{}/JSSResource/{}/id/{}".format(jamf_url, object_types(object_type), obj_id)
    r = curl.request("GET", url, enc_creds, verbosity)
    if r.status_code == 200:
        obj_content = json.loads(r.output)
        if verbosity > 2:
            print("\nAPI object content:")
            print(obj_content)

        # convert an xpath to json
        xpath_list = obj_path.split("/")
        value = obj_content[object_type]

        for i in range(0, len(xpath_list)):
            if xpath_list[i]:
                try:
                    value = value[xpath_list[i]]
                    if verbosity > 2:
                        print("\nAPI object value:")
                        print(value)
                except KeyError:
                    value = ""
                    break
        if value and verbosity > 2:
            print("\nValue of '{}':\n{}".format(obj_path, value))
        return value


def get_headers(r):
    print("\nHeaders:\n")
    print(r.headers)
    print("\nResponse:\n")
    if r.output:
        print(r.output.decode("UTF-8"))
    else:
        print("None")
