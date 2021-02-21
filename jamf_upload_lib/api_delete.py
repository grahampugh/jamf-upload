#!/usr/bin/env python3

from time import sleep

from . import curl, api_objects, api_get


def delete_api_object(jamf_url, object_type, obj_id, enc_creds, verbosity):
    """deletes an API object by obtained or set id"""
    url = f"{jamf_url}/JSSResource/{api_objects.object_types(object_type)}/id/{obj_id}"

    count = 0
    while True:
        count += 1
        if verbosity > 1:
            print(f"{object_type} delete attempt {count}")
        request_type = "DELETE"
        r = curl.request(request_type, url, enc_creds, verbosity)
        # check HTTP response
        if curl.status_check(r, object_type, obj_id, request_type) == "break":
            break
        if count > 5:
            print(f"WARNING: {object_type} delete did not succeed after 5 attempts")
            print(f"\nHTTP POST Response Code: {r.status_code}")
            break
        sleep(30)

    if verbosity > 1:
        api_get.get_headers(r)


def delete_uapi_object(jamf_url, object_type, obj_id, token, verbosity):
    """deletes an API object by obtained or set id"""
    api_obj_version = api_objects.uapi_object_versions(api_objects.object_list_types(object_type))
    url = (
        f"{jamf_url}/uapi/{api_obj_version}/{api_objects.object_list_types(object_type)}/{obj_id}"
    )

    count = 0
    while True:
        count += 1
        if verbosity > 1:
            print(f"{object_type} delete attempt {count}")
        request_type = "DELETE"
        r = curl.request(request_type, url, token, verbosity)
        # check HTTP response
        if curl.status_check(r, object_type, obj_id, request_type) == "break":
            break
        if count > 5:
            print(f"WARNING: {object_type} delete did not succeed after 5 attempts")
            print(f"\nHTTP POST Response Code: {r.status_code}")
            break
        sleep(30)

    if verbosity > 1:
        api_get.get_headers(r)
