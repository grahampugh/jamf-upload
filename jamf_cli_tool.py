#!/usr/bin/env python3

"""
** Jamf CLI Tool. List, Search, Clean 

Credentials can be supplied from the command line as arguments, or inputted, or 
from an existing PLIST containing values for JSS_URL, API_USERNAME and API_PASSWORD, 
for example an AutoPkg preferences file which has been configured for use with 
JSSImporter: ~/Library/Preferences/com.github.autopkg

For usage, run jamf_cli_tool.py --help
"""
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

import argparse
import json
import mimetypes
import os.path
import re
import xml.etree.ElementTree as ElementTree
import time
from time import sleep, gmtime, strftime
from datetime import datetime, timedelta

from jamf_upload_lib import actions, api_connect, api_get, curl


def delete(id, jamf_url, enc_creds, verbosity):
    """deletes a policy by obtained or set id"""
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

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--computers', action='store_true', dest='computer', default=[])
    group.add_argument('--policies', action='store_true')
    # TODO: group.add_argument('--group', action='store_false')
    # TODO: group.add_argument('--ea', action='store_false')
   
    parser.add_argument(
        "-n",
        "--name",
        action="append",
        dest="names",
        default=[],
        help=("Give a policy name to delete. Multiple allowed."),
    )
    parser.add_argument(
        "--computerversion",
        help=("Feed me a computer version please. Requires --computer")
    )
    parser.add_argument(
        "--search",
        action="append",
        dest="search",
        default=[],
        help=("List all policies that start with given query. Delete available in conjunction with --delete."),
    )
    parser.add_argument(
        "--category",
        action="append",
        dest="category",
        default=[],
        help="List all policies in given category. Delete available in conjunction with --delete.",
    )
    parser.add_argument(
        "--delete",
        help="Must be used with another search argument.",
        action="store_true",
    )
    parser.add_argument(
        "--all",
        help="All Policies will JUST be listed. This is meant for you to smoke test your JSS, nothing more.",
        action="store_true",
    )
    parser.add_argument(
        "--slack",
        help="Do a slack",
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
    print("\n** Jamf CLI Tool")
    print("** ...for Jamf Pro.")

    # parse the command line arguments
    args = get_args()
    verbosity = args.verbose

    # grab values from a prefs file if supplied
    jamf_url, _, _, slack_webhook, enc_creds = api_connect.get_creds_from_args(args)

    if args.slack:
        if not slack_webhook:
            print(f"slack_webhook value error set it in your prefs file please")
            exit()

    if args.computer:
        if not args.all:
            exit('which computers? did you mean to add --all')
        # TODO: make this feature
        #if search:
        #    pass

        recent_computers = [] # we'll need this later
        old_computers = []

        if args.all:

            obj = api_get.check_api_finds_all(jamf_url, 'computer', enc_creds, verbosity)

            try:
                computers = []
                for x in obj:
                    computers.append(x['id'])
            
            except:
                computer_id = '404 computers not found'

            print(f"We found {len(computers)} on that JSS")

        else:
            computers = args.computers

        computerversion = args.computerversion

        if computerversion:
            bad_computers = []

        for x in computers:

            print("checking computer {}".format(x))
            obj = api_get.get_api_obj_value_from_id(jamf_url, 'computer', x, '', enc_creds, verbosity)

            if obj:
                try:
                    macos = obj['hardware']['os_version']
                    name = obj['general']['name']                   
                    dep = obj['general']['management_status']['enrolled_via_dep']
                    seen = obj['general']['last_contact_time']
                    seen = datetime.strptime(seen, '%Y-%m-%d %H:%M:%S')
                    now = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
                    now = datetime.strptime(now, '%Y-%m-%d %H:%M:%S')
                    calc = now - seen
                except:
                    macos = 'unknown'
                    name = 'unknown'
                    dep = 'unknown'
                    seen = 'unknown'
                    now = 'unknown'
                    calc = 'we dunno'

            try:
                if now - seen < timedelta(days=10):  # if recent
                    recent_computers.append(f"{macos} {name} dep:{dep} seen:{calc}")

                    if computerversion: # still if recent

                        try: # make sure calculation runs
                            if macos < computerversion: # if bad
                                bad_computers.append(f"{macos} {name} dep:{dep} seen:{calc}")
                                recent_computers.remove(f"{macos} {name} dep:{dep} seen:{calc}")

                        except:
                            print('computerversion mode error..')

                else:
                    old_computers.append(f"{macos} {name} dep:{dep} seen:{calc}")


                        

            except:
                print('checkin age error')

        print(bcolors.OKCYAN + f"computers finished querying ------^ \n summary below -------v "+ bcolors.ENDC)
        
        if computerversion:
            print(f'{len(recent_computers)} are compliant and recent')        
        else:            
            print(f'{len(recent_computers)} are recent, try the --computerversion flag to gain more insight')            
            
        for x in recent_computers:
            print(bcolors.OKGREEN + x + bcolors.ENDC)

        print(f'{len(old_computers)} are stale')
        for x in old_computers:
            print(bcolors.FAIL + x + bcolors.ENDC)

        if computerversion:
            # you can slack api this number to a channel
            score = len(recent_computers) / (len(bad_computers) + len(recent_computers))
            score = "{:.2%}".format(score)
            slack_payload = str(f":hospital: update health: {score} - {len(bad_computers)} need to be fixed on {jamf_url} \n")
            print(slack_payload)

            data = { 'text': slack_payload }
            for x in bad_computers:
                print(bcolors.WARNING + x + bcolors.ENDC)
                if args.slack: # werk
                    slack_payload += str(f"{x}\n")

            if args.slack: # send to slack
                data = { 'text': slack_payload }
                url = slack_webhook
                request_type = "POST"
                r = curl.request(request_type, url, enc_creds, verbosity, data)

        else:
            print('hint to filter out by macos version try the --computerversion flag')
        
        exit()

    # LIST the policies
    if args.policies:
        if args.search and args.all:
            exit('syntax error use --search or --all not both')
        if args.search:
                query = args.search

                obj = api_get.check_api_finds_all(
                    jamf_url, "policy", enc_creds, verbosity
                )

                if obj:
                    # targets is the new list
                    targets = []
                    print("Searching {} Policies(s) on {}: To delete, obtain a matching query, then run with the delete flag".format(len(obj), jamf_url))
                        
                    for x in query:
                        for obj_item in obj:
                            # do the actual search
                            if x in obj_item["name"]:
                                targets.append(obj_item.copy())

                    if len(targets) > 0:
                        print("{} total matches".format(len(targets)))
                        for target in targets:
                            print("Alert: match found {}/{}".format(target["id"], target["name"]))                
                            if args.delete:
                                delete(target["id"], jamf_url, enc_creds, verbosity)
                    else:
                        for partial in query:
                            print("No match found: {}".format(partial))

        elif args.all:
            # assumes --policy flag due to prior exit on another style
            obj = api_get.check_api_finds_all(
                jamf_url, "category_all", enc_creds, verbosity
            )

            if obj:
                for x in obj:
                    # loop all the categories
                    print(bcolors.OKCYAN + "category {} --- {} ---------v".format(x["id"], x["name"]) + bcolors.ENDC)
                    obj = api_get.check_api_category_policies_from_name(
                    jamf_url, 
                    "category_all_items", 
                    x["id"], 
                    enc_creds, 
                    verbosity
                    )
                    if obj:
                        for x in obj:
                            # loop all the policies

                            # gather interesting info for each policy via API
                            # use a single call
                            # general/name
                            # scope/computer_groups  [0]['name']
                            generic_info = api_get.get_api_obj_value_from_id(
                                jamf_url,
                                "policy",
                                x["id"],
                                "",
                                enc_creds,
                                verbosity
                            )

                            name = generic_info['general']['name']


                            try:
                                groups = generic_info['scope']['computer_groups'][0]['name']
                            except:
                                groups = 'no scope assoc'
                            try:
                                pkg = generic_info['package_configuration']['packages'][0]['name']
                            except:
                                pkg = 'no pkg. assoc'

                            # now show all the policies as each category loops
                            print("policy {} --- {} ---- {} --------------->{}".format(x["id"], x["name"], pkg, groups))
            else:
                print("something went wrong: no categories found.")

            print(bcolors.OKGREEN + "all policies listed above.. program complete for {}".format(jamf_url)+ bcolors.ENDC)
            exit

        else:
            exit('syntax error: use --search or --all.')
    

    # set a list of names either from the CLI for Category erase all
    if args.category:
        categories = args.category
        print("categories to check are:\n{}\nTotal: {}".format(categories, len(categories)))
        # now process the list of categories
        for category_name in categories:
            category_name = category_name.replace(" ", "%20")
            # return all items found in each category
            print("\nChecking '{}' on {}".format(category_name, jamf_url))
            obj = api_get.check_api_category_policies_from_name(
                jamf_url, "category_all_items", category_name, enc_creds, verbosity
            )
            if obj:
                if not args.delete:
                    
                    print("Category '{}' exists with {} items: To delete them run this command again with the --delete flag".format(category_name, len(obj)))

                for obj_item in obj:
                    print("~^~ {} -~- {}".format(obj_item["id"], obj_item["name"]))

                    if args.delete:
                        delete(obj_item["id"], jamf_url, enc_creds, verbosity)
            else:
                print("Category '{}' not found".format(category_name))

    # process a name or list of names
    if args.names:
        names = args.names
        print("policy names to check are:\n{}\nTotal: {}".format(names, len(names)))

        for policy_name in names:

            print("\nChecking '{}' on {}".format(policy_name, jamf_url))

            
            obj_id = api_get.get_api_obj_id_from_name(
                jamf_url, 
                "policy", 
                policy_name, 
                enc_creds, 
                verbosity
            )

            if obj_id:
                # gather info from interesting parts of the policy API
                # use a single call
                # general/name
                # scope/computer_gropus  [0]['name']
                generic_info = api_get.get_api_obj_value_from_id(
                    jamf_url,
                    "policy",
                    obj_id,
                    "",
                    enc_creds,
                    verbosity
                )
                name = generic_info['general']['name']
                try:
                    groups = generic_info['scope']['computer_groups'][0]['name']
                except:
                    groups = ''

                print("We found '{}' ID: {} Group: {}".format(name, obj_id, groups))
                if args.delete:
                    delete(obj_id, jamf_url, enc_creds, verbosity)
            else:
                print("Policy '{}' not found".format(policy_name))

    print()


if __name__ == "__main__":
    main()
