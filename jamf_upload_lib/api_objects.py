#!/usr/bin/env python3


def object_types(object_type):
    """return a dictionary of jamf API objects and their corresponding URI names"""
    # define the relationship between the object types and their URL
    # we could make this shorter with some regex but I think this way is clearer
    object_types = {
        "package": "packages",
        "computer_group": "computergroups",
        "policy": "policies",
        "category": "categories",
        "extension_attribute": "computerextensionattributes",
        "os_x_configuration_profile": "osxconfigurationprofiles",
        "computer": "computers",
        "patch_software_title": "patchsoftwaretitles",
    }
    return object_types[object_type]


def object_list_types(object_type):
    """return a dictionary of jamf API objects and their corresponding URI names"""
    # define the relationship between the object types and the xml key in a GET request
    # of all objects we could make this shorter with some regex but I think this way is clearer
    object_list_types = {
        "package": "packages",
        "computer_group": "computer_groups",
        "policy": "policies",
        "category": "categories",
        "extension_attribute": "computer_extension_attributes",
        "os_x_configuration_profile": "os_x_configuration_profiles",
        "computer": "computers",
        "patch_software_title": "patch_software_titles",
    }
    return object_list_types[object_type]
