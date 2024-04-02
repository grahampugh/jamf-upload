#!/usr/bin/env python3

def api_endpoints(object_type):
    """Return the endpoint URL from the object type"""
    api_endpoints = {
        "account": "JSSResource/accounts",
        "advanced_computer_search": "JSSResource/advancedcomputersearches",
        "category": "api/v1/categories",
        "extension_attribute": "JSSResource/computerextensionattributes",
        "computer_group": "JSSResource/computergroups",
        "computer_prestage": "api/v2/computer-prestages",
        "computer": "JSSResource/computers",
        "configuration_profile": "JSSResource/mobiledeviceconfigurationprofiles",
        "dock_item": "JSSResource/dockitems",
        "failover": "api/v1/sso/failover",
        "icon": "api/v1/icon",
        "jamf_pro_version": "api/v1/jamf-pro-version",
        "jcds": "api/v1/jcds",
        "logflush": "JSSResource/logflush",
        "ldap_server": "JSSResource/ldapservers",
        "mac_application": "JSSResource/macapplications",
        "mobile_device_group": "JSSResource/mobiledevicegroups",
        "package": "JSSResource/packages",
        "package_upload": "dbfileupload",
        "patch_policy": "JSSResource/patchpolicies",
        "patch_software_title": "JSSResource/patchsoftwaretitles",
        "oauth": "api/oauth/token",
        "os_x_configuration_profile": "JSSResource/osxconfigurationprofiles",
        "policy": "JSSResource/policies",
        "policy_icon": "JSSResource/fileuploads/policies",
        "restricted_software": "JSSResource/restrictedsoftware",
        "script": "uapi/v1/scripts",
        "token": "api/v1/auth/token",
        "volume_purchasing_locations": "api/v1/volume-purchasing-locations",
    }
    return api_endpoints[object_type]


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

