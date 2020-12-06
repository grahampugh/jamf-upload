#!/usr/bin/env python3

"""
** Jamf Category Upload Script
   by G Pugh

Credentials can be supplied from the command line as arguments, or inputted, or
from an existing PLIST containing values for JSS_URL, API_USERNAME and API_PASSWORD,
for example an AutoPkg preferences file which has been configured for use with
JSSImporter: ~/Library/Preferences/com.github.autopkg

For usage, run jamf_category_upload.py --help
"""


import argparse
import os
from time import sleep

from jamf_upload_lib import api_connect, api_get, curl


def upload_category(jamf_url, category_name, priority, verbosity, token, obj_id=0):
    """Update category metadata."""

    # build the object
    category_data = {"priority": priority, "name": category_name}
    if obj_id:
        url = "{}/uapi/v1/categories/{}".format(jamf_url, obj_id)
        category_data["name"] = category_name
    else:
        url = "{}/uapi/v1/categories".format(jamf_url)

    if verbosity > 2:
        print("Category data:")
        print(category_data)

    print("Uploading category..")

    count = 0

    # we cannot PUT a category of the same name due to a bug in Jamf Pro (PI-008157).
    # so we have to do a first pass with a temporary different name, then change it back...
    if obj_id:
        category_name_temp = category_name + "_TEMP"
        category_data_temp = {"priority": priority, "name": category_name_temp}
        category_json_temp = curl.write_json_file(category_data_temp)
        while True:
            count += 1
            if verbosity > 1:
                print("Category upload attempt {}".format(count))
            r = curl.request("PUT", url, token, verbosity, category_json_temp)
            # check HTTP response
            if curl.status_check(r, "Category", category_name_temp) == "break":
                break
            if count > 5:
                print(
                    "ERROR: Temporary category update did not succeed after 5 attempts"
                )
                print("\nHTTP POST Response Code: {}".format(r.status_code))
                break
            sleep(10)

    # write the category. If updating an existing category, this reverts the name to its original.
    category_json = curl.write_json_file(category_data)

    while True:
        count += 1
        if verbosity > 1:
            print("Category upload attempt {}".format(count))
        method = "PUT" if obj_id else "POST"
        r = curl.request(method, url, token, verbosity, category_json)
        # check HTTP response
        if curl.status_check(r, "Category", category_name) == "break":
            break
        if count > 5:
            print("ERROR: Category creation did not succeed after 5 attempts")
            print("\nHTTP POST Response Code: {}".format(r.status_code))
            break
        sleep(10)

    if verbosity > 1:
        api_get.get_headers(r)

    # clean up temp files
    for file in category_json, category_json_temp:
        if os.path.exists(file):
            os.remove(file)

    return r


def get_args():
    """Parse any command line arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "category", nargs="+", help="Category to create",
    )
    parser.add_argument(
        "--replace", help="overwrite an existing category", action="store_true",
    )
    parser.add_argument(
        "--priority", default="10", help="Category priority. Default value is 10",
    )
    parser.add_argument(
        "--url", default="", help="the Jamf Pro Server URL",
    )
    parser.add_argument(
        "--user",
        default="",
        help="a user with the rights to create and update a category",
    )
    parser.add_argument(
        "--password",
        default="",
        help="password of the user with the rights to create and update a category",
    )
    parser.add_argument(
        "--prefs",
        default="",
        help=(
            "full path to an AutoPkg prefs file containing "
            "JSS URL, API_USERNAME and API_PASSWORD, "
            "for example an AutoPkg preferences file which has been configured "
            "for use with JSSImporter (~/Library/Preferences/com.github.autopkg.plist) "
            "or a separate plist anywhere (e.g. ~/.com.company.jcds_upload.plist)"
        ),
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="print verbose output headers",
    )
    args = parser.parse_args()

    return args


def main():
    """Do the main thing here"""
    print("\n** Jamf category upload script")
    print("** Creates a category in Jamf Pro.")

    #  parse the command line arguments
    args = get_args()
    verbosity = args.verbose

    # grab values from a prefs file if supplied
    jamf_url, _, _, _, enc_creds = api_connect.get_creds_from_args(args)

    # now get the session token
    token = api_connect.get_uapi_token(jamf_url, enc_creds, verbosity)

    # now process the list of categories
    for category_name in args.category:
        # check for existing category
        print("\nChecking '{}' on {}".format(category_name, jamf_url))
        obj_id = api_get.get_uapi_obj_id_from_name(
            jamf_url, "categories", category_name, token, verbosity
        )
        if obj_id:
            print("Category '{}' already exists: ID {}".format(category_name, obj_id))
            if args.replace:
                upload_category(
                    jamf_url, category_name, args.priority, verbosity, token, obj_id
                )
            else:
                print("Not replacing existing category. Use --replace to enforce.")
        else:
            # post the category
            upload_category(jamf_url, category_name, args.priority, verbosity, token)

    print()


if __name__ == "__main__":
    main()
