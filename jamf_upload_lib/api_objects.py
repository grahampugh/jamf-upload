#!/usr/bin/env python3


def object_types(object_type):
    """return a dictionary of jamf API objects and their corresponding URI names"""
    # define the relationship between the object types and their URL
    # we could make this shorter with some regex but I think this way is clearer
    object_types = {
        "package": "packages",
        "computer_group": "computergroups",
        "policy": "policies",
        "script": "scripts",
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
        "script": "scripts",
        "category": "categories",
        "extension_attribute": "computer_extension_attributes",
        "os_x_configuration_profile": "os_x_configuration_profiles",
        "computer": "computers",
        "patch_software_title": "patch_software_titles",
    }
    return object_list_types[object_type]


def uapi_object_versions(object_type):
    """Return the version for a Jamf UAPI object"""
    # UAPI objects go through different versions, this needs to be known to construct
    # a URL
    object_versions = {
        "categories": "v1",
        "computer-prestages": "v2",
        "scripts": "v1",
    }
    return object_versions[object_type]
