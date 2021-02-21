#!/usr/bin/env python3


def object_types(object_type):
    """return a dictionary of jamf API objects and their corresponding URI names"""
    # define the relationship between the object types and their URL
    # we could make this shorter with some regex but I think this way is clearer
    object_types = {
        "advanced_computer_search": "advancedcomputersearches",
        "category": "categories",
        "computer": "computers",
        "computer_group": "computergroups",
        "extension_attribute": "computerextensionattributes",
        "mac_application": "macapplications",
        "os_x_configuration_profile": "osxconfigurationprofiles",
        "package": "packages",
        "patch_policy": "patchpolicies",
        "patch_software_title": "patchsoftwaretitles",
        "policy": "policies",
        "restricted_software": "restrictedsoftware",
        "script": "scripts",
    }
    return object_types[object_type]


def object_list_types(object_type):
    """return a dictionary of jamf API objects and their corresponding xml keys"""
    # define the relationship between the object types and the xml key in a GET request
    # of all objects we could make this shorter with some regex but I think this way is clearer
    object_list_types = {
        "advanced_computer_search": "advanced_computer_searches",
        "category": "categories",
        "computer": "computers",
        "computer_group": "computer_groups",
        "extension_attribute": "computer_extension_attributes",
        "mac_application": "mac_applications",
        "os_x_configuration_profile": "os_x_configuration_profiles",
        "package": "packages",
        "patch_policy": "patch_policies",
        "patch_software_title": "patch_software_titles",
        "policy": "policies",
        "restricted_software": "restricted_software",
        "script": "scripts",
    }
    return object_list_types[object_type]


def uapi_object_versions(object_type):
    """Return the version for a Jamf UAPI object"""
    # UAPI objects go through different versions, this needs to be known to construct
    # a URL
    object_versions = {"categories": "v1", "computer-prestages": "v2", "scripts": "v1"}
    return object_versions[object_type]
