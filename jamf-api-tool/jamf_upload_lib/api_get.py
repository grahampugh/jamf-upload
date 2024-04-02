#!/usr/bin/env python3

import json
from urllib.parse import quote
import xml.etree.ElementTree as ET

from . import curl, api_objects


def get_uapi_obj_list(jamf_url, object_type, token, verbosity):
    """Return all items of a UAPI object"""
    url = jamf_url + "/" + api_objects.api_endpoints(object_type) + "?page=0&page-size=1000&sort=id%3Adesc"
    r = curl.request("GET", url, token, verbosity)
    if r.status_code == 200:
        output = json.loads(r.output)
        obj = output["results"]
        if verbosity > 2:
            print("\nAPI object list:")
            print(obj)
        return obj


def get_uapi_obj_from_id(jamf_url, object_type, obj_id, token, verbosity):
    """Return a UAPI object by ID"""
    url = jamf_url + "/" + api_objects.api_endpoints(object_type) + "/" + obj_id
    r = curl.request("GET", url, token, verbosity)
    if r.status_code == 200:
        output = json.loads(r.output)
        obj = output["results"]
        if verbosity > 2:
            print("\nAPI object list:")
            print(obj)
        return obj


def get_uapi_obj_id_from_name(jamf_url, object_type, object_name, token, verbosity):
    """Get the UAPI object by name"""
    url = jamf_url + "/" + api_objects.api_endpoints(object_type) + "?page=0&page-size=1000&sort=id" + f"&filter=name%3D%3D%22{quote(object_name)}%22"
    r = curl.request("GET", url, token, verbosity)
    if r.status_code == 200:
        output = json.loads(r.output)
        obj_id = 0
        for obj in output["results"]:
            if verbosity > 2:
                print("\nAPI object:")
                print(obj)
            if obj["name"] == object_name:
                obj_id = obj["id"]
        return obj_id


def get_api_obj_list(jamf_url, object_type, token, verbosity):
    """Return all items of an API object"""

    url = jamf_url + "/" + api_objects.api_endpoints(object_type)
    r = curl.request("GET", url, token, verbosity)

    if r.status_code == 200:
        try:
            output = json.loads(json.dumps(r.output))
            if verbosity:
                print("API object is json object")
        except TypeError:
            output = json.loads(r.output)
            if verbosity:
                print("API object is json text")
        if verbosity:
            print("\nAPI object raw output:")
            print(output)
        obj = output[api_objects.object_list_types(object_type)]
        if verbosity > 2:
            print("\nAPI object list:")
            print(obj)
        return obj


def get_api_obj_from_id(jamf_url, object_type, obj_id, token, verbosity):
    """Return an API object by ID"""
    url = jamf_url + "/" + api_objects.api_endpoints(object_type) + f"/id/{obj_id}"
    r = curl.request("GET", url, token, verbosity)
    if r.status_code == 200:
        output = json.loads(r.output)
        obj = output["results"]
        if verbosity > 2:
            print("\nAPI object list:")
            print(obj)
        return obj


def get_api_obj_id_from_name(jamf_url, object_type, object_name, token, verbosity):
    """returns an ID of an API object if it exists"""

    url = jamf_url + "/" + api_objects.api_endpoints(object_type)
    r = curl.request("GET", url, token, verbosity)

    if r.status_code == 200:
        output = json.loads(json.dumps(r.output))
        if verbosity > 3:
            print("\nAPI object raw output:")
            print(output)
        obj_id = 0
        if verbosity > 2:
            print("\nAPI object list:")
        for obj in output[api_objects.object_list_types(object_type)]:
            if verbosity > 2:
                print(obj)
            # we need to check for a case-insensitive match
            if obj["name"].lower() == object_name.lower():
                obj_id = obj["id"]
        return obj_id


def get_patch_obj_value_from_id(
    jamf_url, object_type, obj_id, obj_path, token, verbosity
):
    """get the value of an item in a Classic API object"""
    url = jamf_url + "/" + api_objects.api_endpoints(object_type) + f"/id/{obj_id}"
    r = curl.request("GET", url, token, verbosity, xml="xml")
    if r.status_code == 200:
        # handle xml for patch items
        # TODO : Convert xml to python array. The problem is the version keys
        if verbosity > 2:
            print("\nXML output:")
            print(r.output)
        obj_content = ET.fromstring(r.output)
        if verbosity > 2:
            print("\nAPI object content:")
            print(obj_content)

        # for patch items use ElementTree
        # section to get packages from patch software titles:
        if obj_path == "versions":
            value = {}
            record_id = 0
            for record in obj_content.findall("versions/version"):
                package = {}
                try:
                    package["id"] = record.findtext("package/id")
                    package["name"] = record.findtext("package/name")
                except KeyError:
                    package["id"] = ""
                    package["name"] = ""
                software_version = record.findtext("software_version")
                value[record_id] = {}
                value[record_id]["software_version"] = software_version
                value[record_id]["package"] = package
                record_id = record_id + 1
        # section to get groups from patch policies:
        elif obj_path == "scope":
            value = {}
            record_id = 0
            for record in obj_content.findall("scope/computer_groups/computer_group"):
                group = {}
                group["id"] = record.findtext("id")
                group["name"] = record.findtext("name")
                value[record_id] = {}
                value[record_id]["computer_group"] = group
                record_id = record_id + 1
            for record in obj_content.findall(
                "scope/exclusions/computer_groups/computer_group"
            ):
                ex_group = {}
                ex_group["id"] = record.findtext("id")
                ex_group["name"] = record.findtext("name")
                value[record_id] = {}
                value[record_id]["computer_group"] = ex_group
                record_id = record_id + 1
        else:
            value = obj_content.findtext(obj_path)
        if value and verbosity > 2:
            print(f"\nValue of '{obj_path}':\n{value}")
        return value


def get_api_obj_value_from_id(
    jamf_url, object_type, obj_id, obj_path, token, verbosity
):
    """get the value of an item in a Classic API object"""
    url = jamf_url + "/" + api_objects.api_endpoints(object_type) + f"/id/{obj_id}"
    r = curl.request("GET", url, token, verbosity)

    if r.status_code == 200:
        output = json.loads(r.output)
        if verbosity > 2:
            print("\nAPI object content:")
            print(output)

        # for everything else, convert an xpath to json
        xpath_list = obj_path.split("/")
        value = output[object_type]

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


def get_policies_in_category(jamf_url, object_name, token, verbosity):
    """return all policies in a category"""

    url = jamf_url + "/" + api_objects.api_endpoints("policy") + f"/category/{object_name}"
    r = curl.request("GET", url, token, verbosity)

    if r.status_code == 200:
        output = json.loads(r.output)
        obj = output["policies"]
        if verbosity > 3:
            print("\nAPI object raw output:")
            print(output)

        if verbosity > 2:
            print("\nAPI object list:")
            print(obj)
        return obj


def get_packages_in_policies(jamf_url, token, verbosity):
    """get a list of all packages in all policies"""

    # get all policies
    policies = get_api_obj_list(jamf_url, "policy", token, verbosity)

    # get all package objects from policies and add to a list
    if policies:
        # define a new list
        packages_in_policies = []
        print(
            "Please wait while we gather a list of all packages in all policies "
            f"(total {len(policies)})..."
        )
        for policy in policies:
            generic_info = get_api_obj_value_from_id(
                jamf_url, "policy", policy["id"], "", token, verbosity
            )
            try:
                pkgs = generic_info["package_configuration"]["packages"]
                for x in pkgs:
                    pkg = x["name"]
                    if pkg not in packages_in_policies:
                        packages_in_policies.append(pkg)
            except IndexError:
                pass
        return packages_in_policies


def get_packages_in_patch_titles(jamf_url, token, verbosity):
    """get a list of all packages in all patch software titles"""

    # get all patch software titles
    titles = get_api_obj_list(jamf_url, "patch_software_title", token, verbosity)

    # get all package objects from patch titles and add to a list
    if titles:
        # define a new list
        packages_in_titles = []
        print(
            "Please wait while we gather a list of all packages in all patch titles "
            f"(total {len(titles)})..."
        )
        for title in titles:
            versions = get_patch_obj_value_from_id(
                jamf_url,
                "patch_software_title",
                title["id"],
                "versions",
                token,
                verbosity,
            )
            try:
                if len(versions) > 0:
                    for x in range(len(versions)):
                        try:
                            pkg = versions[x]["package"]["name"]
                            if pkg:
                                if pkg != "None" and pkg not in packages_in_titles:
                                    packages_in_titles.append(pkg)
                        except IndexError:
                            pass
                        except KeyError:
                            pass
            except IndexError:
                pass
        return packages_in_titles


def get_packages_in_prestages(jamf_url, token, verbosity):
    """get a list of all packages in all PreStage Enrollments"""

    # get all prestages
    prestages = get_uapi_obj_list(jamf_url, "computer_prestage", token, verbosity)

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
                    pkg = get_api_obj_value_from_id(
                        jamf_url, "package", pkg_id, "name", token, verbosity
                    )
                    if pkg:
                        if pkg not in packages_in_prestages:
                            packages_in_prestages.append(pkg)
        return packages_in_prestages


def get_scripts_in_policies(jamf_url, token, verbosity):
    """get a list of all scripts in all policies"""

    # get all policies
    policies = get_api_obj_list(jamf_url, "policy", token, verbosity)

    # get all script objects from policies and add to a list
    if policies:
        # define a new list
        scripts_in_policies = []
        print(
            "Please wait while we gather a list of all scripts in all policies "
            f"(total {len(policies)})..."
        )
        for policy in policies:
            generic_info = get_api_obj_value_from_id(
                jamf_url, "policy", policy["id"], "", token, verbosity
            )
            try:
                scripts = generic_info["scripts"]
                for x in scripts:
                    script = x["name"]
                    if script not in scripts_in_policies:
                        scripts_in_policies.append(script)
            except IndexError:
                pass
        return scripts_in_policies


def get_criteria_in_computer_groups(jamf_url, token, verbosity):
    """get a list of all criteria in all smart groups"""

    # get all smart groups
    computer_groups = get_api_obj_list(jamf_url, "computer_group", token, verbosity)

    # get all EA objects from computer groups and add to a list
    if computer_groups:
        # define a new list
        criteria_in_computer_groups = []
        print(
            "Please wait while we gather a list of all criteria in all computer groups "
            f"(total {len(computer_groups)})..."
        )
        for computer_group in computer_groups:
            generic_info = get_api_obj_value_from_id(
                jamf_url,
                "computer_group",
                computer_group["id"],
                "",
                token,
                verbosity,
            )
            try:
                criteria = generic_info["criteria"]
                for x in criteria:
                    criterion = x["name"]
                    if criterion not in criteria_in_computer_groups:
                        criteria_in_computer_groups.append(criterion)
            except IndexError:
                pass
        return criteria_in_computer_groups


def get_names_in_advanced_searches(jamf_url, token, verbosity):
    """get a list of all criteria and display fields in all advanced searches.
    Note it's not possible to discern EAs from other criteria with this method."""

    # get all advanced searches
    advanced_searches = get_api_obj_list(
        jamf_url, "advanced_computer_search", token, verbosity
    )

    # get all EA objects from computer groups and add to a list
    if advanced_searches:
        # define a new list
        names_in_advanced_searches = []
        print(
            "Please wait while we gather a list of all criteria in all computer groups "
            f"(total {len(advanced_searches)})..."
        )
        for advanced_search in advanced_searches:
            generic_info = get_api_obj_value_from_id(
                jamf_url,
                "advanced_computer_search",
                advanced_search["id"],
                "",
                token,
                verbosity,
            )
            try:
                criteria = generic_info["criteria"]
                for x in criteria:
                    criterion = x["name"]
                    if criterion not in names_in_advanced_searches:
                        names_in_advanced_searches.append(criterion)
            except IndexError:
                pass
            try:
                fields = generic_info["display_fields"]
                for x in fields:
                    field = x["name"]
                    if field not in names_in_advanced_searches:
                        names_in_advanced_searches.append(field)
            except IndexError:
                pass
        return names_in_advanced_searches


def get_groups_in_patch_policies(jamf_url, token, verbosity):
    """get a list of all groups in all patch policies (targets or exclusions)."""

    # get all objects
    api_objects = get_api_obj_list(jamf_url, "patch_policy", token, verbosity)

    # get all groups from policies and add to a list
    if api_objects:
        # define a new list
        groups_in_api_objects = []
        print(
            f"Please wait while we gather a list of all groups in patch policies "
            f"(total {len(api_objects)})..."
        )
        for obj in api_objects:
            groups = get_patch_obj_value_from_id(
                jamf_url, "patch_policy", obj["id"], "scope", token, verbosity
            )
            for x in groups:
                group = groups[x]["computer_group"]["name"]
                if group not in groups_in_api_objects:
                    groups_in_api_objects.append(group)
        return groups_in_api_objects


def get_groups_in_api_objs(jamf_url, token, obj_type, verbosity):
    """get a list of all groups in all of a particular object type (targets or exclusions).
    Valid object types are: mac_application, os_x_configuration_profile,
    policy, restricted_software"""

    # get all objects
    api_objects = get_api_obj_list(jamf_url, obj_type, token, verbosity)

    # get all groups from policies and add to a list
    if api_objects:
        # define a new list
        groups_in_api_objects = []
        print(
            f"Please wait while we gather a list of all groups in {obj_type} objects "
            f"(total {len(api_objects)})..."
        )
        for obj in api_objects:
            generic_info = get_api_obj_value_from_id(
                jamf_url, obj_type, obj["id"], "", token, verbosity
            )
            if generic_info["scope"]["all_computers"] != "true":
                try:
                    # targetted groups
                    groups = generic_info["scope"]["computer_groups"]
                    for x in groups:
                        group = x["name"]
                        if group not in groups_in_api_objects:
                            groups_in_api_objects.append(group)
                except IndexError:
                    pass
                try:
                    # excluded groups
                    groups = generic_info["scope"]["exclusions"]["computer_groups"]
                    for x in groups:
                        group = x["name"]
                        if group not in groups_in_api_objects:
                            groups_in_api_objects.append(group)
                except IndexError:
                    pass
        return groups_in_api_objects


def get_headers(r):
    print("\nHeaders:\n")
    print(r.headers)
    print("\nResponse:\n")
    if r.output:
        print(r.output)
    else:
        print("None")
