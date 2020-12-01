#!/usr/bin/env python3

import re


def substitute_assignable_keys(data, cli_custom_keys, verbosity):
    """substitutes any key in the inputted text using the %MY_KEY% nomenclature"""
    # whenever %MY_KEY% is found in a template, it is replaced with the assigned value of MY_KEY
    # do a triple-pass to ensure that all keys are substituted
    loop = 5
    while loop > 0:
        loop = loop - 1
        found_keys = re.findall(r"\%\w+\%", data)
        if not found_keys:
            break
        found_keys = [i.replace("%", "") for i in found_keys]
        for found_key in found_keys:
            if cli_custom_keys[found_key]:
                if verbosity:
                    print(
                        (
                            f"Replacing any instances of '{found_key}' with",
                            f"'{str(cli_custom_keys[found_key])}'",
                        ),
                    )
                data = data.replace(f"%{found_key}%", cli_custom_keys[found_key])
            else:
                print(f"WARNING: '{found_key}' has no replacement object!",)
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
    else:
        print(
            f"WARNING: {endpoint_type} '{obj_name}' upload failed with status code {r.status_code}"
        )

