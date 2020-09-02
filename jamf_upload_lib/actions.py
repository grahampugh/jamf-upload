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

