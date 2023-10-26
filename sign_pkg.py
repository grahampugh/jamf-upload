#!/usr/bin/env python3

"""
** Jamf Package Signing Script
   by G Pugh

This script can be used to sign a package. It will look for a valid
Apple Developer ID Application identity in the current keychain,
or you can supply one via the command line.

If no output path is supplied, the outputted file will have the same name
as the input file, but with .signed.pkg as the suffix instead of .pkg

For usage, run jamf_package_sign.py --help
"""

import argparse
import subprocess


def find_developer_id(verbosity):
    proc = subprocess.Popen(
        ["security", "find-identity", "-v"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    (output, error) = proc.communicate()
    if output:
        if verbosity:
            print(output)
            print()
        identities = output.split(b"\n")
        developer = ""
        for identity in identities:
            if b"Developer ID Installer" in identity:
                developer = identity.split(b'"')[1].decode("utf-8")
                break
        return developer
    if error:
        if verbosity:
            print(error)
            print()


def sign_package(unsigned_pkg, developer_id, output_path, verbosity):
    """Sign a package using a given developer id.
    You can usually find a valid codesigning identity by using the following command:
    security find-identity -p codesigning -v
    """
    if not output_path:
        output_path = unsigned_pkg.replace(".pkg", ".signed.pkg")
    cmd = [
        "/usr/bin/productsign",
        "--sign",
        developer_id,
        unsigned_pkg,
        output_path,
    ]
    if verbosity:
        print(cmd)
        print()
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    sout, serr = proc.communicate()
    if verbosity:
        if sout:
            print(f"Output of signing command: {sout.decode()}")
            print()
        elif serr:
            print("Error: Package was not signed:")
            print(serr.decode())
            print()
    return output_path


def get_args():
    """Parse any command line arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "pkg",
        nargs="+",
        help="Path to package .pkg file",
    )
    parser.add_argument(
        "--output_path",
        default="",
        help="Output path for signed package",
    )
    parser.add_argument(
        "--developer",
        default="",
        help="an Apple Developer ID with the rights to sign a Package (Installer)",
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
    print(
        "\n** Package signing script",
        "\n** WARNING: This is an experimental script! Using it may have "
        "unexpected results!",
        "\n",
    )
    print(
        "The first run of this script in a session will most likely trigger "
        "a keychain prompt.",
        "\n",
    )

    # parse the command line arguments
    args = get_args()
    verbosity = args.verbose

    developer = find_developer_id(verbosity)

    if developer:
        args.developer = developer

    # sign the package if a developer ID is supplied
    if args.developer:
        print(
            f"Signing package(s) using certificate for developer id '{args.developer}'."
        )
        n = 1
        for pkg_path in args.pkg:
            if n > 1 and args.output_path:
                args.output_path = args.output_path.replace(".pkg", f".{n}.pkg")

            # sign the package
            signed_pkg = sign_package(
                pkg_path, args.developer, args.output_path, verbosity
            )
            print(f"Path to signed package {n}: {signed_pkg}")
            n = n + 1
    else:
        print("No Developer ID provided")

    print()


if __name__ == "__main__":
    main()
