#!/usr/bin/env python3

from time import sleep

from . import curl, api_objects, api_get


def delete(jamf_url, object_type, obj_id, enc_creds, verbosity):
    """deletes an API object by obtained or set id"""
    url = f"{jamf_url}/JSSResource/{api_objects.object_types(object_type)}/id/{id}"

    count = 0
    while True:
        count += 1
        if verbosity > 1:
            print("Policy delete attempt {}".format(count))
        request_type = "DELETE"
        r = curl.request(request_type, url, enc_creds, verbosity)
        # check HTTP response
        if curl.status_check(r, "Policy", id, request_type) == "break":
            break
        if count > 5:
            print("WARNING: Policy delete did not succeed after 5 attempts")
            print("\nHTTP POST Response Code: {}".format(r.status_code))
            break
        sleep(30)

    if verbosity > 1:
        api_get.get_headers(r)
