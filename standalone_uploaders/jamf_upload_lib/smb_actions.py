#!/usr/bin/env python3

import os
import subprocess

from shutil import copyfile
from urllib.parse import urlparse


def mount_smb(mount_share, mount_user, mount_pass, verbosity):
    """Mount distribution point."""
    mount_cmd = [
        "/usr/bin/osascript",
        "-e",
        'mount volume "{}" as user name "{}" with password "{}"'.format(
            mount_share, mount_user, mount_pass
        ),
    ]
    if verbosity > 1:
        print(f"Mount command:\n{mount_cmd}")

    r = subprocess.check_output(mount_cmd)
    if verbosity > 1:
        print(f"Mount command response:\n{r.decode('UTF-8')}")


def umount_smb(mount_share):
    """Unmount distribution point."""
    path = f"/Volumes{urlparse(mount_share).path}"
    cmd = ["/usr/sbin/diskutil", "unmount", path]
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError:
        print("WARNING! Unmount failed.")


def copy_pkg(mount_share, pkg_path, pkg_name):
    """Copy package from AutoPkg Cache to local or mounted Distribution Point"""
    if os.path.isfile(pkg_path):
        path = f"/Volumes{urlparse(mount_share).path}"
        destination_pkg_path = os.path.join(path, "Packages", pkg_name)
        print(f"Copying {pkg_name} to {destination_pkg_path}")
        copyfile(pkg_path, destination_pkg_path)
        if os.path.isfile(destination_pkg_path):
            print("Package copy successful")
        else:
            print("Package copy failed")
    else:
        print("Package not found")


def delete_pkg(mount_share, pkg_name):
    """Delete a package from an SMB share"""
    path = f"/Volumes{urlparse(mount_share).path}"
    pkg_to_delete = os.path.join(path, "Packages", pkg_name)
    if os.path.isfile(pkg_to_delete):
        print(f"Deleting {pkg_name} from SMB share mounted at {path}")
        os.remove(pkg_to_delete)
    else:
        print(f"{pkg_name} not found on SMB share mounted at {path}")
    # double check the file is gone
    if os.path.isfile(pkg_to_delete):
        print(f"ERROR: Deleting {pkg_name} from SMB share mounted at {path} failed.")