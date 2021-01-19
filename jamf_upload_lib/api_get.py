#!/usr/bin/env python3

import json
from urllib.parse import quote
import xml.etree.ElementTree as ET

from . import curl, api_objects


def get_uapi_obj_list(jamf_url, object_type, token, verbosity):
    """Return all items of a UAPI object"""
    api_obj_version = api_objects.uapi_object_versions(object_type)
    url = (
        f"{jamf_url}/uapi/{api_obj_version}/{object_type}?page=0&page-size=1000&sort=id"
        "%3Adesc"
    )
    r = curl.request("GET", url, token, verbosity)
    if r.status_code == 200:
        obj = r.output["results"]
        if verbosity > 2:
            print("\nAPI object list:")
            print(obj)
        return obj


def get_uapi_obj_id_from_name(jamf_url, object_type, object_name, token, verbosity):
    """Get the UAPI object by name"""
    api_obj_version = api_objects.uapi_object_versions(object_type)
    url = (
        f"{jamf_url}/uapi/{api_obj_version}/{object_type}?page=0&page-size=1000&sort=id"
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


def get_api_obj_list(jamf_url, object_type, enc_creds, verbosity):
    """Return all items of an API object"""

    url = f"{jamf_url}/JSSResource/{api_objects.object_types(object_type)}"
    r = curl.request("GET", url, enc_creds, verbosity)

    if r.status_code == 200:
        object_list = json.loads(r.output)
        obj = object_list[api_objects.object_list_types(object_type)]
        if verbosity > 3:
            print("\nAPI object raw output:")
            print(object_list)

        if verbosity > 2:
            print("\nAPI object list:")
            print(obj)
        return obj


def get_api_obj_id_from_name(jamf_url, object_type, object_name, enc_creds, verbosity):
    """returns an ID of an API object if it exists"""

    url = f"{jamf_url}/JSSResource/{api_objects.object_types(object_type)}"
    r = curl.request("GET", url, enc_creds, verbosity)

    if r.status_code == 200:
        object_list = json.loads(r.output)
        if verbosity > 3:
            print("\nAPI object raw output:")
            print(object_list)
        obj_id = 0
        if verbosity > 2:
            print("\nAPI object list:")
        for obj in object_list[api_objects.object_list_types(object_type)]:
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
    if object_type == "patch_software_title":
        # the json returned from patchsoftwaretitles is broken so we need to get the xml
        xml = True
    else:
        xml = False
    url = f"{jamf_url}/JSSResource/{api_objects.object_types(object_type)}/id/{obj_id}"
    r = curl.request("GET", url, enc_creds, verbosity, xml=xml)

    if r.status_code == 200:
        if xml:
            # handle xml for patchsoftwaretitles
            # TODO : Convert xml to python array. The problem is the version keys
            if verbosity > 2:
                print("\nXML output:")
                print(r.output)
            obj_content = ET.fromstring(r.output)
        else:
            # handle json for everything else
            obj_content = json.loads(r.output)
        if verbosity > 2:
            print("\nAPI object content:")
            print(obj_content)

        if xml:
            # for patchsoftwaretitles use ElementTree
            if obj_path == "versions":
                value = {}
                record_id = 0
                for record in obj_content.findall("versions/version"):
                    software_version = record.findtext("software_version")
                    if verbosity > 2:  # TEMP
                        print("\nsoftware_version:")  # TEMP
                        print(software_version)  # TEMP
                    package = {}
                    package["id"] = record.findtext("package/id")
                    if verbosity > 2:  # TEMP
                        print("\npackage id:")  # TEMP
                        print(package["id"])  # TEMP
                    package["name"] = record.findtext("package/name")
                    if verbosity > 2:  # TEMP
                        print("\npackage name:")  # TEMP
                        print(package["name"])  # TEMP
                    value[record_id] = {}
                    value[record_id]["software_version"] = software_version
                    value[record_id]["package"] = package
                    record_id = record_id + 1
            else:
                value = obj_content.findtext(obj_path)
        else:
            # for everything else, convert an xpath to json
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
            print(f"\nValue of '{obj_path}':\n{value}")
        return value


def get_headers(r):
    print("\nHeaders:\n")
    print(r.headers)
    print("\nResponse:\n")
    if r.output:
        print(r.output.decode("UTF-8"))
    else:
        print("None")
