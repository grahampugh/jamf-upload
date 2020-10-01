#!/usr/bin/env python3


def substitute_assignable_keys(data, cli_custom_keys, verbosity):
    """substitutes any key in the inputted text using the %MY_KEY% nomenclature"""
    # whenever %MY_KEY% is found in a template, it is replaced with the assigned value of MY_KEY
    for custom_key in cli_custom_keys:
        if verbosity:
            print(
                f"Replacing any instances of '{custom_key}' with",
                f"'{cli_custom_keys[custom_key]}'",
            )
        data = data.replace(f"%{custom_key}%", cli_custom_keys[custom_key])
    return data


def status_check(r, endpoint_type, obj_name):
    """Return a message dependent on the HTTP response"""
    if r.status_code == 200 or r.status_code == 201:
        print("{} '{}' uploaded successfully".format(endpoint_type, obj_name))
        return "break"
    elif r.status_code == 409:
        print("WARNING: {} upload failed due to a conflict".format(endpoint_type))
        return "break"
    elif r.status_code == 401:
        print("ERROR: {} upload failed due to permissions error".format(endpoint_type))
        return "break"

