#!/usr/bin/env python3

"""
** Jamf Policy List, Search, Delete Script

Credentials can be supplied from the command line as arguments, or inputted, or 
from an existing PLIST containing values for JSS_URL, API_USERNAME and API_PASSWORD, 
for example an AutoPkg preferences file which has been configured for use with 
JSSImporter: ~/Library/Preferences/com.github.autopkg

For usage, run jamf_policy_delete.py --help
"""


import argparse
import json
import mimetypes
import os.path
import re
import xml.etree.ElementTree as ElementTree
from time import sleep

from jamf_upload_lib import actions, api_connect, api_get, curl


def delete(id, jamf_url, enc_creds, verbosity):
    """check if a policy with the same name exists in the repo
    note that it is possible to have more than one with the same name
    which could mess things up"""
    url = "{}/JSSResource/policies/id/{}".format(jamf_url, id)

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

def for_partial():
    pass

def get_args():
    """Parse any command line arguments"""
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-n",
        "--name",
        action="append",
        dest="names",
        default=[],
        help=("Give a policy name to interact with. Multiple allowed"),
    )
    parser.add_argument(
        "-s",
        "--search",
        action="append",
        dest="search",
        default=[],
        help=("Return a list of partial policy name matches. Matches start of whatever you type."),
    )
    parser.add_argument(
        "-c",
        "--category",
        action="append",
        dest="categories",
        default=[],
        help="Provide a category name, policies belonging will just be listed unless delete flag is implicitly passed.",
    )
    parser.add_argument(
        "-d",
        "--delete",
        help="perform the delete(s) if policy(ies) found. Policies will just be listed without this argument and not deleted.",
        action="store_true",
    )
    parser.add_argument(
        "-l",
        "--list-policies",
        help="All Policies will JUST be listed.",
        action="store_true",
    )    
    parser.add_argument(
        "--url", default="", help="the Jamf Pro Server URL",
    )
    parser.add_argument(
        "--user", default="", help="a user with the rights to delete a policy",
    )
    parser.add_argument(
        "--password",
        default="",
        help="password of the user with the rights to delete a policy",
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
    print("\n** Jamf policy delete script")
    print("** Deletes or Shows a policy or policies in Jamf Pro.")

    # parse the command line arguments
    args = get_args()
    verbosity = args.verbose

    # grab values from a prefs file if supplied
    jamf_url, _, _, enc_creds = api_connect.get_creds_from_args(args)

    # QUERY all the policys 
    # todo loop in the categories for quick JSS checking easier
    if args.list_policies:
        obj = api_get.check_api_finds_all_policies(
            jamf_url, "policy", enc_creds, verbosity
        )

        if obj:
            all_policies = []
            show_msg = ("{} Policies exist(s) on {}: SHOWING THEM ONLY ^^^".format(len(obj), jamf_url))
                
            for obj_item in obj:
                all_policies.append("~^~ {} -~- {}".format(obj_item["id"], obj_item["name"]))
                # just show them all now that all_policies list is made
            for policy in all_policies:
                print(policy)
            print(show_msg)
            exit

    if args.search:
        partials = args.search

        obj = api_get.check_api_finds_all_policies(
            jamf_url, "policy", enc_creds, verbosity
        )

        if obj:
            # targets is the new list
            targets = []
            print("{} Total Policies exist(s) on {}: To delete, obtain a matching query, then run with the delete flag".format(len(obj), jamf_url))
                
            for partial in partials:
                for obj_item in obj:
                    # do the actual search
                    if obj_item["name"].startswith(partial):
                        targets.append(obj_item.copy())

            if len(targets) > 0:
                print("{} total hits".format(len(targets)))
                for target in targets:
                    print("Alert: match found {}/{}".format(target["id"], target["name"]))                
                    if args.delete:
                        delete(target["id"], jamf_url, enc_creds, verbosity)
            else:
                for partial in partials:
                    print("No match found: {}".format(partial))


    # set a list of names either from the CLI for Category erase all
    if args.categories:
        categories = args.categories
        print("categories to check are:\n{}\nTotal: {}".format(categories, len(categories)))
        # now process the list of categories
        for category_name in categories:
            category_name = category_name.replace(" ", "%20")
            # check for existing category
            print("\nChecking '{}' on {}".format(category_name, jamf_url))
            obj = api_get.check_api_category_policies_from_name(
                jamf_url, "category", category_name, enc_creds, verbosity
            )
            if obj:
                print("Category '{}' exists with {} items: To delete them run this command again with the delete flag".format(category_name, len(obj)))

                for obj_item in obj:
                    print("~^~ {} -~- {}".format(obj_item["id"], obj_item["name"]))
                    
                    if args.delete:
                        delete(obj_item["id"], jamf_url, enc_creds, verbosity)
            else:
                print("Category '{}' not found".format(category_name))

    # set a list of names either from the CLI args for policies
    if args.names:
        names = args.names
        print("policy names to check are:\n{}\nTotal: {}".format(names, len(names)))

        # now process the list of names
        for policy_name in names:

            # check for existing policy
            print("\nChecking '{}' on {}".format(policy_name, jamf_url))
            obj_id = api_get.check_api_obj_id_from_name(
                jamf_url, "policy", policy_name, enc_creds, verbosity
            )
            if obj_id:
                print("Policy '{}' exists: ID {}".format(policy_name, obj_id))
                if args.delete:
                    delete(obj_id, jamf_url, enc_creds, verbosity)
            else:
                print("Policy '{}' not found".format(policy_name))

    print()


if __name__ == "__main__":
    main()
