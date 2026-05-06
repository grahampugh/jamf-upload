#!/usr/local/autopkg/python
# -*- coding: utf-8 -*-

# Copyright 2025 Graham Pugh
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Simple script to test an NSPredicate expression and output True or False."""

import argparse
import os
import re
import sys

try:
    from Foundation import NSPredicate
except ImportError:
    print(
        "ERROR: Foundation module not available. "
        "Run with /usr/local/autopkg/python.",
        file=sys.stderr,
    )
    sys.exit(1)


def substitute_env_vars(predicate_string):
    """Replace %VARIABLE% tokens with their environment variable values.

    Uses the AutoPkg-style %NAME% syntax. The name between percent signs
    is looked up in the environment (case-sensitive).
    Numeric values stay bare; string values are single-quoted for NSPredicate.
    """

    def _replace(match):
        name = match.group(1)
        value = os.environ.get(name)
        if value is None:
            print(
                f"WARNING: Variable '{name}' not found in environment.",
                file=sys.stderr,
            )
            return match.group(0)
        # If the value is numeric, leave it bare; otherwise quote it
        try:
            float(value)
            return value
        except ValueError:
            return f"'{value}'"

    return re.sub(r"%([A-Za-z_][A-Za-z0-9_]*)%", _replace, predicate_string)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate an NSPredicate expression. "
            "Environment variables referenced by name in the predicate "
            "are substituted automatically."
        ),
    )
    parser.add_argument(
        "-p",
        "--predicate",
        help="The predicate string to evaluate.",
    )
    args = parser.parse_args()

    predicate_string = args.predicate
    if not predicate_string:
        try:
            predicate_string = input("Enter predicate: ")
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.", file=sys.stderr)
            sys.exit(1)

    if not predicate_string.strip():
        print("ERROR: No predicate provided.", file=sys.stderr)
        sys.exit(1)

    predicate_string = substitute_env_vars(predicate_string)

    print(
        f"Evaluating predicate: {predicate_string}",
        file=sys.stderr,
    )

    try:
        predicate = NSPredicate.predicateWithFormat_(predicate_string)
    except Exception as e:
        print(f"ERROR: Invalid predicate: {e}", file=sys.stderr)
        sys.exit(1)

    result = predicate.evaluateWithObject_(None)
    print(result)


if __name__ == "__main__":
    main()
