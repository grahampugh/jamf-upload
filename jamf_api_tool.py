#!/usr/bin/env python3

"""
** Jamf API Tool: List, search and clean policies and computer objects

Credentials can be supplied from the command line as arguments, or inputted, or
from an existing PLIST containing values for JSS_URL, API_USERNAME and API_PASSWORD,
for example an AutoPkg preferences file which has been configured for use with
JSSImporter: ~/Library/Preferences/com.github.autopkg

For usage, run jamf_api_tool.py --help
"""


import argparse
import json

from datetime import datetime

from jamf_upload_lib import api_connect, api_get, api_delete, curl, actions


class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def get_policies_in_category(jamf_url, object_name, enc_creds, verbosity):
    """return all policies in a category"""

    url = f"{jamf_url}/JSSResource/policies/category/{object_name}"
    r = curl.request("GET", url, enc_creds, verbosity)

    if r.status_code == 200:
        object_list = json.loads(r.output)
        obj = object_list["policies"]
        if verbosity > 3:
            print("\nAPI object raw output:")
            print(object_list)

        if verbosity > 2:
            print("\nAPI object list:")
            print(obj)
        return obj


def get_packages_in_policies(jamf_url, enc_creds, verbosity):
    """get a list of all packages in all policies"""

    # get all policies
    policies = api_get.get_api_obj_list(jamf_url, "policy", enc_creds, verbosity)

    # get all package objects from policies and add to a list
    if policies:
        # define a new list
        packages_in_policies = []
        print(
            "Please wait while we gather a list of all packages in all policies "
            f"(total {len(policies)})..."
        )
        for policy in policies:
            generic_info = api_get.get_api_obj_value_from_id(
                jamf_url, "policy", policy["id"], "", enc_creds, verbosity
            )
            try:
                pkgs = generic_info["package_configuration"]["packages"]
                for x in pkgs:
                    pkg = x["name"]
                    packages_in_policies.append(pkg)
            except IndexError:
                pass
        return packages_in_policies


def get_packages_in_patch_titles(jamf_url, enc_creds, verbosity):
    """get a list of all packages in all patch software titles"""

    # get all patch software titles
    titles = api_get.get_api_obj_list(
        jamf_url, "patch_software_title", enc_creds, verbosity
    )

    # get all package objects from patch titles and add to a list
    if titles:
        # define a new list
        packages_in_titles = []
        print(
            "Please wait while we gather a list of all packages in all patch titles "
            f"(total {len(titles)})..."
        )
        for title in titles:
            versions = api_get.get_api_obj_value_from_id(
                jamf_url,
                "patch_software_title",
                title["id"],
                "versions",
                enc_creds,
                verbosity,
            )
            try:
                if len(versions) > 0:
                    for x in range(len(versions)):
                        try:
                            pkg = versions[x]["package"]["name"]
                            if pkg and pkg != "None":
                                packages_in_titles.append(pkg)
                        except IndexError:
                            pass
            except IndexError:
                pass
        return packages_in_titles


def get_packages_in_prestages(jamf_url, enc_creds, token, verbosity):
    """get a list of all packages in all PreStage Enrollments"""

    # get all prestages
    prestages = api_get.get_uapi_obj_list(
        jamf_url, "computer-prestages", token, verbosity
    )

    # get all package objects from prestages and add to a list
    if prestages:
        packages_in_prestages = []
        print(
            "Please wait while we gather a list of all packages in all PreStage Enrollments "
            f"(total {len(prestages)})..."
        )
        for x in range(len(prestages)):
            pkg_ids = prestages[x]["customPackageIds"]
            if len(pkg_ids) > 0:
                for pkg_id in pkg_ids:
                    pkg = api_get.get_api_obj_value_from_id(
                        jamf_url, "package", pkg_id, "name", enc_creds, verbosity,
                    )
                    if pkg:
                        packages_in_prestages.append(pkg)
        return packages_in_prestages


def get_args():
    """Parse any command line arguments"""
    parser = argparse.ArgumentParser()

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--computers", action="store_true", dest="computer", default=[])
    group.add_argument("--policies", action="store_true")
    group.add_argument("--packages", action="store_true")
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
        "--os", help=("Restrict computer search to an OS version. Requires --computer"),
    )
    parser.add_argument(
        "--search",
        action="append",
        dest="search",
        default=[],
        help=(
            "List all policies that start with given query. "
            "Delete available in conjunction with --delete."
        ),
    )
    parser.add_argument(
        "--category",
        action="append",
        dest="category",
        default=[],
        help=(
            "List all policies in given category. Delete available in "
            "conjunction with --delete."
        ),
    )
    parser.add_argument(
        "--details",
        help="Must be used with another search argument.",
        action="store_true",
    )
    parser.add_argument(
        "--unused",
        help="Must be used with another search argument.",
        action="store_true",
    )
    parser.add_argument(
        "--delete",
        help="Must be used with another search argument.",
        action="store_true",
    )
    parser.add_argument(
        "--all",
        help=(
            "All Policies will be listed but no action will be taken. "
            "This is only meant for you to browse your JSS."
        ),
        action="store_true",
    )
    parser.add_argument(
        "--slack", help="Post a slack webhook", action="store_true",
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
    print("\n** Jamf API Tool for Jamf Pro.\n")

    # parse the command line arguments
    args = get_args()
    verbosity = args.verbose

    # grab values from a prefs file if supplied
    jamf_url, _, _, slack_webhook, enc_creds = api_connect.get_creds_from_args(args)

    # now get the session token
    token = api_connect.get_uapi_token(jamf_url, enc_creds, verbosity)

    if args.slack:
        if not slack_webhook:
            print("slack_webhook value error. Please set it in your prefs file.")
            exit()

    # computers block ####
    if args.computer:
        if args.search and args.all:
            exit("syntax error: use either --search or --all, but not both")
        if not args.all:
            exit("syntax error: --computers requires --all as a minimum")

        recent_computers = []  # we'll need this later
        old_computers = []
        warning = []  # stores full detailed computer info
        compliant = []

        if args.all:
            """ fill up computers []"""
            obj = api_get.get_api_obj_list(jamf_url, "computer", enc_creds, verbosity)

            try:
                computers = []
                for x in obj:
                    computers.append(x["id"])

            except IndexError:
                computers = "404 computers not found"

            print(f"{len(computers)} computers found on {jamf_url}")

        for x in computers:
            """ load full computer info now """
            print(f"...loading info for computer {x}")
            obj = api_get.get_api_obj_value_from_id(
                jamf_url, "computer", x, "", enc_creds, verbosity
            )

            if obj:
                """ this is now computer object """
                try:
                    macos = obj["hardware"]["os_version"]
                    name = obj["general"]["name"]
                    dep = obj["general"]["management_status"]["enrolled_via_dep"]
                    seen = datetime.strptime(
                        obj["general"]["last_contact_time"], "%Y-%m-%d %H:%M:%S"
                    )
                    now = datetime.utcnow()

                except IndexError:
                    macos = "unknown"
                    name = "unknown"
                    dep = "unknown"
                    seen = "unknown"
                    now = "unknown"

                difference = (now - seen).days

            try:
                if (now - seen).days < 10 and not args.os:  # if recent
                    recent_computers.append(
                        f"{x} {macos}\t"
                        + f"name : {name}\n"
                        + f"\t\tDEP  : {dep}\n"
                        + f"\t\tseen : {difference} days ago"
                    )

                if (now - seen).days < 10 and args.os and (macos >= args.os):
                    compliant.append(
                        f"{x} {macos}\t"
                        + f"name : {name}\n"
                        + f"\t\tDEP  : {dep}\n"
                        + f"\t\tseen : {difference} days ago"
                    )
                elif (now - seen).days < 10 and args.os and (macos < args.os):
                    warning.append(
                        f"{x} {macos}\t"
                        + f"name : {name}\n"
                        + f"\t\tDEP  : {dep}\n"
                        + f"\t\tseen : {difference} days ago"
                    )

                if (now - seen).days > 10:
                    old_computers.append(
                        f"{x} {macos}\t"
                        + f"name : {name}\n"
                        + f"\t\tDEP  : {dep}\n"
                        + f"\t\tseen : {difference} days ago"
                    )

            except IndexError:
                print("checkin calc. error")

                # recent_computers.remove(f"{macos} {name} dep:{dep} seen:{calc}")

        # query is done
        print(bcolors.OKCYAN + "Loading complete...\n\nSummary:" + bcolors.ENDC)

        if args.os:
            """ summarise os """
            if compliant:
                print(f"{len(compliant)} compliant and recent:")
                for x in compliant:
                    print(bcolors.OKGREEN + x + bcolors.ENDC)
            if warning:
                print(f"{len(warning)} non-compliant:")
                for x in warning:
                    print(bcolors.WARNING + x + bcolors.ENDC)
            if old_computers:
                print(f"{len(old_computers)} stale - OS version not considered:")
                for x in old_computers:
                    print(bcolors.FAIL + x + bcolors.ENDC)
        else:
            """ regular summary """
            print(f"{len(recent_computers)} last check-in within the past 10 days")
            for x in recent_computers:
                print(bcolors.OKGREEN + x + bcolors.ENDC)
            print(f"{len(old_computers)} stale - last check-in more than 10 days")
            for x in old_computers:
                print(bcolors.FAIL + x + bcolors.ENDC)

        if args.slack:
            # end a slack api webhook with this number
            score = len(recent_computers) / (len(old_computers) + len(recent_computers))
            score = f"{score:.2%}"
            slack_payload = str(
                f":hospital: update health: {score} - {len(old_computers)} "
                f"need to be fixed on {jamf_url}\n"
            )
            print(slack_payload)

            data = {"text": slack_payload}
            for x in old_computers:
                print(bcolors.WARNING + x + bcolors.ENDC)
                if args.slack:  # werk
                    slack_payload += str(f"{x}\n")

            if args.slack:  # send to slack
                data = {"text": slack_payload}
                url = slack_webhook
                request_type = "POST"
                curl.request(request_type, url, enc_creds, verbosity, data)

        exit()

    # policy block #####
    if args.policies:
        if args.all:
            categories = api_get.get_api_obj_list(
                jamf_url, "category", enc_creds, verbosity
            )
            if categories:
                for category in categories:
                    # loop all the categories
                    print(
                        bcolors.OKCYAN
                        + f"category {category['id']}\t{category['name']}"
                        + bcolors.ENDC
                    )
                    policies = api_get.get_policies_in_category(
                        jamf_url,
                        "policies_in_category",
                        category["id"],
                        enc_creds,
                        verbosity,
                    )
                    if policies:
                        for policy in policies:
                            # loop all the policies
                            generic_info = api_get.get_api_obj_value_from_id(
                                jamf_url,
                                "policy",
                                policy["id"],
                                "",
                                enc_creds,
                                verbosity,
                            )

                            name = generic_info["general"]["name"]

                            try:
                                groups = generic_info["scope"]["computer_groups"][0][
                                    "name"
                                ]
                            except IndexError:
                                groups = "none"
                            try:
                                pkg = generic_info["package_configuration"]["packages"][
                                    0
                                ]["name"]
                            except IndexError:
                                pkg = "none"

                            # now show all the policies as each category loops
                            print(
                                bcolors.WARNING
                                + f"  policy {policy['id']}"
                                + f"\tname  : {policy['name']}\n"
                                + bcolors.ENDC
                                + f"\t\tpkg   : {pkg}\n"
                                + f"\t\tscope : {groups}"
                            )
            else:
                print("something went wrong: no categories found.")

            print(
                "\n"
                + bcolors.OKGREEN
                + f"All policies listed above... program complete for {jamf_url}"
                + bcolors.ENDC
            )
            exit

        elif args.search:
            query = args.search

            policies = api_get.get_api_obj_list(
                jamf_url, "policy", enc_creds, verbosity
            )

            if policies:
                # targets is the new list
                targets = []
                print(
                    f"Searching {len(policies)} policy/ies on {jamf_url}:\n"
                    "To delete policies, obtain a matching query, then run with the "
                    "--delete argument"
                )

                for x in query:
                    for policy in policies:
                        # do the actual search
                        if x in policy["name"]:
                            targets.append(policy.copy())

                if len(targets) > 0:
                    print("Policies found:")
                    for target in targets:
                        print(
                            bcolors.WARNING
                            + f"- policy {target['id']}"
                            + f"\tname  : {target['name']}"
                            + bcolors.ENDC
                        )
                        if args.delete:
                            api_delete.delete(
                                jamf_url, "policy", target["id"], enc_creds, verbosity
                            )
                    print(f"{len(targets)} total matches")
                else:
                    for partial in query:
                        print(f"No match found: {partial}")

        else:
            exit("syntax error: with --policies you must supply --search or --all.")

    # packages block #####
    if args.packages:
        unused_packages = {}
        used_packages = {}
        if args.unused:
            # get a list of packages
            packages_in_prestages = get_packages_in_prestages(
                jamf_url, enc_creds, token, verbosity
            )
            if verbosity > 1:
                print("\nPackages in PreStage Enrollments:")
                print(packages_in_prestages)

            packages_in_titles = get_packages_in_patch_titles(
                jamf_url, enc_creds, verbosity
            )
            if verbosity > 1:
                print("\nPackages in Patch Software Titles:")
                print(packages_in_titles)

            packages_in_policies = get_packages_in_policies(
                jamf_url, enc_creds, verbosity
            )
            if verbosity > 1:
                print("\nPackages in Policies:")
                print(packages_in_policies)

        else:
            packages_in_policies = []
            packages_in_titles = []
            packages_in_prestages = []

        if args.all or args.unused:
            packages = api_get.get_api_obj_list(
                jamf_url, "package", enc_creds, verbosity
            )
            if packages:
                for package in packages:
                    # loop all the packages
                    if args.unused:
                        # see if the package is in any policies
                        if (
                            package["name"] not in packages_in_policies
                            and package["name"] not in packages_in_titles
                            and package["name"] not in packages_in_prestages
                        ):
                            unused_packages[package["id"]] = package["name"]
                        elif package["name"] not in used_packages:
                            used_packages[package["id"]] = package["name"]
                    else:
                        print(
                            bcolors.WARNING
                            + f"  package {package['id']}\n"
                            + f"      name     : {package['name']}"
                            + bcolors.ENDC
                        )
                        if args.details:
                            # gather interesting info for each package via API
                            generic_info = api_get.get_api_obj_value_from_id(
                                jamf_url,
                                "package",
                                package["id"],
                                "",
                                enc_creds,
                                verbosity,
                            )

                            filename = generic_info["filename"]
                            print(f"      filename : {filename}")
                            category = generic_info["category"]
                            if category and "No category assigned" not in category:
                                print(f"      category : {category}")
                            info = generic_info["info"]
                            if info:
                                print(f"      info     : {info}")
                            notes = generic_info["notes"]
                            if notes:
                                print(f"      notes    : {notes}")
                if args.unused:
                    print(
                        "\nThe following packages are found in at least one policy, "
                        "PreStage Enrollment, and/or patch title:\n"
                    )
                    for pkg_name in used_packages.values():
                        print(bcolors.OKGREEN + pkg_name + bcolors.ENDC)

                    print(
                        "\nThe following packages are not used in any policies, "
                        "PreStage Enrollments, or patch titles:\n"
                    )
                    for pkg_name in unused_packages.values():
                        print(bcolors.FAIL + pkg_name + bcolors.ENDC)

                    if args.delete:
                        print("\nconfirm to delete items:")
                        if actions.confirm(
                            prompt=(
                                "Delete all unused policies"
                                "\n(press n to go on to confirm individually)?"
                            ),
                            default=False,
                        ):
                            delete_all = True
                        else:
                            delete_all = False
                        for pkg_id, pkg_name in unused_packages.items():
                            # prompt to delete each package in turn
                            if delete_all or actions.confirm(
                                prompt=(
                                    bcolors.OKBLUE
                                    + f"Delete {pkg_name} (id={pkg_id})?"
                                    + bcolors.ENDC
                                ),
                                default=False,
                            ):
                                print(f"Deleting {pkg_name}...")
                                api_delete.delete(
                                    jamf_url, "package", pkg_id, enc_creds, verbosity,
                                )
                                # TODO : delete package from SMB share too!

    # set a list of names either from the CLI for Category erase all
    if args.category:
        categories = args.category
        print(f"categories to check are:\n{categories}\nTotal: {len(categories)}")
        # now process the list of categories
        for category in categories:
            category = category.replace(" ", "%20")
            # return all items found in each category
            print(f"\nChecking '{category}' on {jamf_url}")
            obj = api_get.get_policies_in_category(
                jamf_url, "policies_in_category", category, enc_creds, verbosity
            )
            if obj:
                if not args.delete:

                    print(
                        f"Category '{category}' exists with {len(obj)} items: "
                        "To delete them run this command again with the --delete flag."
                    )

                for obj_item in obj:
                    print(f"~^~ {obj_item['id']} -~- {obj_item['name']}")

                    if args.delete:
                        api_delete.delete(
                            jamf_url, "policy", obj_item["id"], enc_creds, verbosity
                        )
            else:
                print(f"Category '{category}' not found")

    # process a name or list of names
    if args.names:
        policy_names = args.names
        print(f"policy names to check are:\n{policy_names}\nTotal: {len(policy_names)}")

        for policy_name in policy_names:
            print(f"\nChecking '{policy_name}' on {jamf_url}")

            obj_id = api_get.get_api_obj_id_from_name(
                jamf_url, "policy", policy_name, enc_creds, verbosity
            )

            if obj_id:
                # gather info from interesting parts of the policy API
                # use a single call
                # general/name
                # scope/computer_gropus  [0]['name']
                generic_info = api_get.get_api_obj_value_from_id(
                    jamf_url, "policy", obj_id, "", enc_creds, verbosity
                )
                name = generic_info["general"]["name"]
                try:
                    groups = generic_info["scope"]["computer_groups"][0]["name"]
                except IndexError:
                    groups = ""

                print(f"Match found: '{name}' ID: {obj_id} Group: {groups}")
                if args.delete:
                    api_delete.delete(jamf_url, "policy", obj_id, enc_creds, verbosity)
            else:
                print(f"Policy '{policy_name}' not found")

    print()


if __name__ == "__main__":
    main()
