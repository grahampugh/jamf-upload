#!/usr/local/autopkg/python
# pylint: disable=invalid-name
# pylint: disable=too-many-lines

"""
Copyright 2023 Graham Pugh

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

NOTES:
Requirements for uploading to the AWS S3 API endpoint:
- boto3

To resolve the dependencies, run: /usr/local/autopkg/python -m pip install boto3
"""

import hashlib
import json
import os.path
import shutil
import subprocess
import sys
import threading

from shutil import copyfile
from time import sleep
from urllib.parse import urlparse, quote
import xml.etree.ElementTree as ElementTree
from xml.sax.saxutils import escape

from autopkglib import ProcessorError, APLooseVersion  # pylint: disable=import-error

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderBase import (  # pylint: disable=import-error, wrong-import-position
    JamfUploaderBase,
)


class ProgressPercentage(object):
    """Class for displaying upload progress - used for jcds2_mode only"""

    def __init__(self, filename):
        self._filename = filename
        self._size = float(os.path.getsize(filename))
        self._seen_so_far = 0
        self._lock = threading.Lock()

    def __call__(self, bytes_amount):
        # To simplify, assume this is hooked up to a single filename
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = (self._seen_so_far / self._size) * 100
            sys.stdout.write(
                "\r%s  %s / %s  (%.2f%%)"  # pylint: disable=consider-using-f-string
                % (self._filename, self._seen_so_far, self._size, percentage)
            )
            sys.stdout.flush()


class JamfPackageUploaderBase(JamfUploaderBase):
    """Class for functions used to upload a package to Jamf"""

    def sha512sum(self, filename):
        """calculate the SHA512 hash of the package
        (see https://stackoverflow.com/a/44873382)"""
        h = hashlib.sha512()
        b = bytearray(128 * 1024)
        mv = memoryview(b)
        with open(filename, "rb", buffering=0) as f:
            for n in iter(lambda: f.readinto(mv), 0):
                h.update(mv[:n])
        return h.hexdigest()

    def sha3sum(self, pkg_path):
        """calculate the SHA-3 512 hash of the package"""
        h = hashlib.sha3_512()
        b = bytearray(128 * 1024)
        mv = memoryview(b)
        with open(pkg_path, "rb", buffering=0) as f:
            for n in iter(lambda: f.readinto(mv), 0):
                h.update(mv[:n])
        return h.hexdigest()

    def sha256sum(self, filename):
        """calculate the SHA256 hash of the package"""
        h = hashlib.sha256()
        b = bytearray(128 * 1024)
        mv = memoryview(b)
        with open(filename, "rb", buffering=0) as f:
            for n in iter(lambda: f.readinto(mv), 0):
                h.update(mv[:n])
        return h.hexdigest()

    def md5sum(self, filename):
        """calculate the MD5 hash of the package"""
        h = hashlib.md5()
        b = bytearray(128 * 1024)
        mv = memoryview(b)
        with open(filename, "rb", buffering=0) as f:
            for n in iter(lambda: f.readinto(mv), 0):
                h.update(mv[:n])
        return h.hexdigest()

    def zip_pkg_path(self, bundle_path, recipe_cache_dir):
        """Add files from path to a zip file handle.

        Args:
            path (str): Path to folder to zip.

        Returns:
            (str) name of resulting zip file.
        """

        zip_name = f"{bundle_path}.zip"

        if os.path.exists(zip_name):
            self.output("Package object is a bundle. Zipped archive already exists.")
            return zip_name

        # we need to create a zip that contains the package (not just the contents of the package)
        # to do this, me copy the package into it's own folder, and then zip that folder.
        self.output(
            f"Package object is a bundle. Converting to zip, will be placed at {recipe_cache_dir}"
        )
        pkg_basename = os.path.basename(bundle_path)
        # make a subdirectory
        pkg_dir = os.path.join(recipe_cache_dir, "temp", "pkg")
        os.makedirs(pkg_dir, mode=0o777)
        # copy the package into pkg_dir
        shutil.copytree(bundle_path, os.path.join(pkg_dir, pkg_basename))
        # now rename pkg_dir to the package name (I know, weird)
        temp_dir = os.path.join(recipe_cache_dir, "temp", pkg_basename)
        shutil.move(pkg_dir, temp_dir)
        # now make the zip archive
        zip_path = shutil.make_archive(
            temp_dir,
            "zip",
            temp_dir,
        )
        # move it to the recipe_cache_dir
        shutil.move(zip_path, zip_name)
        # clean up
        shutil.rmtree(os.path.join(recipe_cache_dir, "temp"))

        self.output(f"Zip file {zip_name} created.")
        return zip_name

    # ------------------------------------------------------------------------
    # Beginning of functions for uploading to Local Fileshare Distribution Points

    def check_local_pkg(self, mount_share, pkg_name):
        """Check local DP or mounted share for existing package"""
        dirname = f"/Volumes{urlparse(mount_share).path}"
        if os.path.isdir(dirname):
            existing_pkg_path = os.path.join(dirname, "Packages", pkg_name)
            if os.path.isfile(existing_pkg_path):
                self.output(f"Existing package found: {existing_pkg_path}")
                return existing_pkg_path
            else:
                self.output("No existing package found")
                self.output(
                    f"Expected path: {existing_pkg_path}",
                    verbose_level=2,
                )
                return None
        else:
            self.output(
                f"Expected path not found!: {dirname}",
                verbose_level=2,
            )
            return None

    def copy_pkg(self, mount_share, pkg_path, pkg_name):
        """Copy package from AutoPkg Cache to local or mounted Distribution Point"""
        if os.path.isfile(pkg_path):
            dirname = f"/Volumes{urlparse(mount_share).path}"
            destination_pkg_path = os.path.join(dirname, "Packages", pkg_name)
            self.output(f"Copying {pkg_name} to {destination_pkg_path}")
            copyfile(pkg_path, destination_pkg_path)
        if os.path.isfile(destination_pkg_path):
            self.output("Package copy successful")
        else:
            self.output("Package copy failed")

    # End of functions for upload to Local Fileshare Distribution Points
    # ------------------------------------------------------------------------
    # Beginning of functions for uploading to v1/packages endpoint

    def upload_pkg(
        self,
        api_url,
        pkg_path,
        pkg_name,
        pkg_id,
        sleep_time,
        token,
        max_tries,
        tenant_id="",
    ):
        """Upload a package to a Cloud Distribution Point using the v1/packages endpoint"""

        # if pkg_name does not match the package name in pkg_path we copy the package locally first
        pkg_dirname = os.path.dirname(pkg_path)
        pkg_basename = os.path.basename(pkg_path)
        tmp_pkg_path = ""
        if pkg_basename != pkg_name:
            tmp_pkg_path = os.path.join(pkg_dirname, pkg_name)
            shutil.copyfile(pkg_path, tmp_pkg_path)
            self.output(
                (
                    f"Package name does not match path, so package copied from {pkg_path} to",
                    f"{tmp_pkg_path}",
                ),
                verbose_level=2,
            )
            pkg_path = tmp_pkg_path

        object_type = "package_v1"
        endpoint = self.api_endpoints(object_type, tenant_id=tenant_id)
        url = f"{api_url}/{endpoint}/{pkg_id}/upload"
        count = 0
        while True:
            count += 1
            self.output(
                f"Package upload attempt {count}",
                verbose_level=2,
            )

            request = "POST"
            r = self.curl(
                api_type="jpapi",
                request=request,
                url=url,
                token=token,
                data=pkg_path,
                endpoint_type="package_v1",
            )

            # check HTTP response
            if self.status_check(r, "Package upload", pkg_name, request) == "break":
                break
            if count >= max_tries:
                self.output(
                    f"WARNING: Package upload did not succeed after {max_tries} attempts"
                )
                self.output(
                    f"HTTP POST Response Code: {r.status_code}",
                    verbose_level=1,
                )
                raise ProcessorError("ERROR: Package upload failed ")
            if int(sleep_time) > 10:
                sleep(int(sleep_time))
            else:
                sleep(10)

        self.output(f"HTTP response: {r.status_code}", verbose_level=1)

        # delete temp package
        if tmp_pkg_path:
            self.output(
                f"Removing temporary file {tmp_pkg_path}",
                verbose_level=2,
            )
            try:
                os.remove(tmp_pkg_path)
            except OSError:
                pass
        return r

    # End of function for uploading to v1/packages endpoint
    # ------------------------------------------------------------------------
    # Beginning of function for uploading to AWS CDP (not needed for 11.5+)

    def upload_to_aws_s3_bucket(self, pkg_path, pkg_name):
        """upload the package to an AWS CDP
        Note that this requires the installation of the aws-cli tools on your AutoPkg machine
        and you must set up the connection with 'aws configure'. Alternatively you can create
        the config file manually. See https://aws.amazon.com/cli/ for installation instructions.

        You must also specify the bucket name to the environment ('S3_BUCKET_NAME').
        """

        aws_cmd = [
            "/usr/local/bin/aws",
            "s3",
            "sync",
            os.path.dirname(pkg_path) + "/",
            "s3://" + self.env.get("S3_BUCKET_NAME") + "/",
            "--exclude",
            "*",
            "--include",
            pkg_name,
            "--output",
            "text",
        ]
        # now subprocess the aws cli
        try:
            aws_output = subprocess.check_output(aws_cmd)
        except subprocess.CalledProcessError as exc:
            raise ProcessorError(f"Error from aws: {exc}") from exc

        # if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
        #     with open(output_file, "rb") as file:
        #         aws_output = file.read()

        self.output(
            "AWS response: " + aws_output.decode("ascii"),
            verbose_level=2,
        )

    # End of function for uploading to AWS CDP
    # ------------------------------------------------------------------------
    # Begin function on uploading pkg metadata

    def check_pkg(self, pkg_name, api_url, token, tenant_id=""):
        """check if a package with the same name exists in the repo
        note that it is possible to have more than one with the same name
        which could mess things up"""

        object_type = "package_v1"
        filter_name = "packageName"
        object_id = self.get_api_object_id_from_name(
            api_url,
            object_type=object_type,
            object_name=pkg_name,
            token=token,
            filter_name=filter_name,
            tenant_id=tenant_id,
        )

        if object_id:
            return str(object_id)
        else:
            return "-1"

    def get_category_id(self, api_url, category_name, token="", tenant_id=""):
        """Get the category ID from the name, or abort if ID not found"""
        # check for existing category
        self.output(f"Checking for '{category_name}' on {api_url}")
        object_id = self.get_api_object_id_from_name(
            api_url,
            object_type="category",
            object_name=category_name,
            token=token,
            tenant_id=tenant_id,
        )

        if object_id:
            self.output(f"Category '{category_name}' exists: ID {object_id}")
            return object_id
        else:
            self.output(f"Category '{category_name}' not found")
            raise ProcessorError("Supplied package category does not exist")

    def update_pkg_metadata(  # pylint: disable=too-many-arguments, too-many-locals
        self,
        api_url,
        pkg_name,
        pkg_display_name,
        pkg_metadata,
        sha512string,
        md5string,
        sleep_time,
        token,
        max_tries,
        pkg_id=0,
        tenant_id="",
    ):
        """Update package metadata using v1/packages endpoint. Requires 11.5+"""

        # get category ID
        if pkg_metadata["category"]:
            category_id = self.get_category_id(
                api_url, pkg_metadata["category"], token, tenant_id
            )
        else:
            category_id = "-1"

        # build the package record JSON
        pkg_data = {
            "packageName": pkg_display_name,
            "fileName": pkg_name,
            "info": pkg_metadata["info"],
            "notes": pkg_metadata["notes"],
            "categoryId": category_id,
            "priority": pkg_metadata["priority"],
            "fillUserTemplate": 0,
            "uninstall": 0,
            "rebootRequired": pkg_metadata["reboot_required"],
            "osInstall": 0,
            "osRequirements": pkg_metadata["os_requirements"],
            "suppressUpdates": 0,
            "suppressFromDock": 0,
            "suppressEula": 0,
            "suppressRegistration": 0,
        }

        if md5string:
            hash_type = "MD5"
            pkg_data["hashType"] = hash_type
            pkg_data["hashValue"] = md5string
        elif sha512string:
            hash_type = "SHA_512"
            pkg_data["hashType"] = hash_type
            pkg_data["hashValue"] = sha512string

        self.output(
            "Package metadata:",
            verbose_level=2,
        )
        self.output(
            pkg_data,
            verbose_level=2,
        )

        pkg_json = self.write_json_file(api_url, pkg_data)

        # if we find a pkg ID we put, if not, we post
        object_type = "package_v1"
        endpoint = self.api_endpoints(object_type, tenant_id=tenant_id)
        if int(pkg_id) > 0:
            url = f"{api_url}/{endpoint}/{pkg_id}"
        else:
            url = f"{api_url}/{endpoint}"

        count = 0
        while True:
            count += 1
            self.output(
                f"Package metadata upload attempt {count}",
                verbose_level=2,
            )
            request = "PUT" if pkg_id else "POST"
            r = self.curl(
                api_type="jpapi", request=request, url=url, token=token, data=pkg_json
            )
            # check HTTP response
            if self.status_check(r, "Package Metadata", pkg_name, request) == "break":
                break
            if count >= max_tries:
                self.output(
                    f"Package metadata upload did not succeed after {max_tries} attempts"
                )
                self.output(f"\nHTTP POST Response Code: {r.status_code}")
                raise ProcessorError("ERROR: Package metadata upload failed ")
            if int(sleep_time) > 10:
                sleep(int(sleep_time))
            else:
                sleep(10)
        if r.status_code == 201:
            obj = json.loads(json.dumps(r.output))
            self.output(
                obj,
                verbose_level=4,
            )

            try:
                object_id = obj["id"]
            except KeyError:
                object_id = "-1"
        else:
            object_id = "-1"
        return object_id

    # End functions for uploading pkg metadata
    # ------------------------------------------------------------------------
    # Begin function for recalulating inventory on Cloud Distribution Point (for pkg_api_mode)

    def recalculate_packages(self, api_url, token, tenant_id=""):
        """Send a request to recalulate the Cloud Distribution Point inventory"""
        # get the Cloud Distribution Point file list
        object_type = "cloud_distribution_point"
        endpoint = self.api_endpoints(object_type, tenant_id=tenant_id)
        url = f"{api_url}/{endpoint}/refresh-inventory"

        request = "POST"
        r = self.curl(
            api_type="jpapi",
            request=request,
            url=url,
            token=token,
        )

        if r.status_code == 204:
            self.output(
                "Cloud Distribution Point inventory successfully recalculated",
                verbose_level=2,
            )
            packages_recalculated = True
        else:
            self.output(
                f"WARNING: Cloud Distribution Point inventory NOT successfully recalculated (response={r.status_code})",
                verbose_level=1,
            )
            packages_recalculated = False
        return packages_recalculated

    # End functions for recalulating inventory on Cloud Distribution Point
    # ------------------------------------------------------------------------

    # ------------------------------------------------------------------------
    # MAIN FUNCTION
    def execute(
        self,
    ):  # pylint: disable=too-many-branches, too-many-locals, too-many-statements
        """Perform the package upload"""

        pkg_path = self.env.get("pkg_path")
        if not pkg_path:
            try:
                pathname = self.env.get("pathname")
                if pathname.endswith(".pkg"):
                    pkg_path = pathname
            except KeyError:
                pass
        pkg_name = self.env.get("pkg_name")
        pkg_display_name = self.env.get("pkg_display_name")
        version = self.env.get("version")
        replace = self.to_bool(self.env.get("replace_pkg"))
        sleep_time = self.env.get("sleep")
        replace_metadata = self.to_bool(self.env.get("replace_pkg_metadata"))
        skip_metadata_upload = self.to_bool(self.env.get("skip_metadata_upload"))
        aws_cdp_mode = self.to_bool(self.env.get("aws_cdp_mode"))
        recalculate = self.to_bool(self.env.get("recalculate"))
        use_md5 = self.env.get("md5")
        jamf_url = (self.env.get("JSS_URL") or "").rstrip("/")
        jamf_user = self.env.get("API_USERNAME")
        jamf_password = self.env.get("API_PASSWORD")
        jamf_platform_gw_region = self.env.get("PLATFORM_API_REGION")
        jamf_platform_gw_tenant_id = self.env.get("PLATFORM_API_TENANT_ID")
        client_id = self.env.get("CLIENT_ID")
        client_secret = self.env.get("CLIENT_SECRET")
        bearer_token = self.env.get("BEARER_TOKEN")
        jamf_cli_profile = self.env.get("JAMF_CLI_PROFILE")
        cloud_dp = self.to_bool(self.env.get("CLOUD_DP"))
        recipe_cache_dir = self.env.get("RECIPE_CACHE_DIR")
        pkg_uploaded = False
        pkg_metadata_updated = False
        max_tries = self.env.get("max_tries")

        # verify that max_tries is an integer greater than zero and less than 10
        try:
            max_tries = int(max_tries)
            if max_tries < 1 or max_tries > 10:
                raise ValueError
        except (ValueError, TypeError):
            max_tries = 5

        # set pkg_name if not separately defined
        if not pkg_name:
            pkg_name = os.path.basename(pkg_path)

        # handle files with a relative path
        if not pkg_path.startswith("/"):
            found_pkg = self.get_path_to_file(pkg_path)
            if found_pkg:
                pkg_path = found_pkg
            else:
                raise ProcessorError(f"ERROR: pkg {pkg_path} not found")

        # Create a list of smb shares in tuples
        smb_shares = []
        if self.env.get("SMB_URL"):
            if not self.env.get("SMB_USERNAME") or not self.env.get("SMB_PASSWORD"):
                raise ProcessorError("SMB_URL defined but no credentials supplied.")
            self.output(
                (
                    "DP 1:",
                    self.env.get("SMB_URL"),
                    self.env.get("SMB_USERNAME"),
                    "pass len:",
                    len(self.env.get("SMB_PASSWORD")),
                ),
                verbose_level=2,
            )
            smb_shares.append(
                (
                    self.env.get("SMB_URL"),
                    self.env.get("SMB_USERNAME"),
                    self.env.get("SMB_PASSWORD"),
                )
            )
            n = 2
            while n > 0:
                if self.env.get(f"SMB{n}_URL"):
                    if not self.env.get(f"SMB{n}_USERNAME") or not self.env.get(
                        f"SMB{n}_PASSWORD"
                    ):
                        raise ProcessorError(
                            f"SMB{n}_URL defined but no credentials supplied."
                        )
                    self.output(
                        (
                            f"DP {n}:",
                            self.env.get(f"SMB{n}_URL"),
                            self.env.get(f"SMB{n}_USERNAME"),
                            "pass len:",
                            len(self.env.get(f"SMB{n}_PASSWORD")),
                        ),
                        verbose_level=2,
                    )
                    smb_shares.append(
                        (
                            self.env.get(f"SMB{n}_URL"),
                            self.env.get(f"SMB{n}_USERNAME"),
                            self.env.get(f"SMB{n}_PASSWORD"),
                        )
                    )
                    n = n + 1
                else:
                    self.output(f"DP {n}: not defined", verbose_level=3)
                    n = 0
        elif self.env.get("SMB_SHARES"):
            smb_share_array = self.env.get("SMB_SHARES")
            for share in smb_share_array:
                if (
                    not share["SMB_URL"]
                    or not share["SMB_USERNAME"]
                    or not share["SMB_PASSWORD"]
                ):
                    raise ProcessorError("Incorrect SMB credentials supplied.")
                smb_shares.append(
                    (
                        share["SMB_URL"],
                        share["SMB_USERNAME"],
                        share["SMB_PASSWORD"],
                    )
                )

        # create a dictionary of package metadata from the inputs
        pkg_category = self.env.get("pkg_category")

        # substitute values in the package category
        pkg_category = self.substitute_assignable_keys(pkg_category)

        reboot_required = self.env.get("reboot_required")
        if not reboot_required or reboot_required == "False":
            reboot_required = False
        send_notification = self.env.get("send_notification")
        if not send_notification or send_notification == "False":
            send_notification = False

        pkg_metadata = {
            "category": pkg_category,
            "info": self.env.get("pkg_info"),
            "notes": self.env.get("pkg_notes"),
            "reboot_required": reboot_required,
            "priority": self.env.get("pkg_priority"),
            "os_requirements": self.env.get("os_requirements"),
            "required_processor": self.env.get("required_processor"),
            "send_notification": send_notification,
        }

        # clear any pre-existing summary result
        if "jamfpackageuploader_summary_result" in self.env:
            del self.env["jamfpackageuploader_summary_result"]

        # See if the package is a bundle (directory).
        # If so, zip_pkg_path will look for an existing .zip
        # If that doesn't exist, it will create the zip and return the pkg_path with .zip added
        # In that case, we need to add .zip to the pkg_name key too, if we don't already have it
        if os.path.isdir(pkg_path):
            pkg_path = self.zip_pkg_path(pkg_path, recipe_cache_dir)
            if ".zip" not in pkg_name:
                pkg_name += ".zip"

        # we need to ensure that a zipped package's display name matches the new pkg_name for
        # comparison with an existing package
        if not pkg_display_name:
            pkg_display_name = pkg_name

        # calculate the SHA-512 hash of the package
        sha512string = self.sha512sum(pkg_path)

        # calculate the SHA-256 hash of the package
        # sha256string = self.sha256sum(pkg_path)

        # calculate the SHA-512 hash of the package
        md5string = self.md5sum(pkg_path) if use_md5 else None

        # now start the process of uploading the package
        self.output(f"Checking for existing package '{pkg_name}' on {jamf_url}")

        # get token using oauth or basic auth depending on the credentials given
        if jamf_url:
            token, jamf_url, jamf_platform_gw_region, jamf_platform_gw_tenant_id = self.auth(
                jamf_url=jamf_url,
                jamf_user=jamf_user,
                password=jamf_password,
                region=jamf_platform_gw_region,
                tenant_id=jamf_platform_gw_tenant_id,
                client_id=client_id,
                client_secret=client_secret,
                token=bearer_token,
                jamf_cli_profile=jamf_cli_profile,
            )
        else:
            raise ProcessorError("ERROR: Jamf Pro URL not supplied")

        # construct the api_url based on the API type
        api_url = self.construct_api_url(
            jamf_url=jamf_url, region=jamf_platform_gw_region
        )
        self.output(f"API URL is {api_url}", verbose_level=3)

        # get Jamf Pro version to determine default mode
        # Version 11.5+ will use the v1/packages endpoint
        # Version 11.4- is not supported any more
        jamf_pro_version = self.get_jamf_pro_version(api_url, token)

        if APLooseVersion(jamf_pro_version) < APLooseVersion("11.5"):
            raise ProcessorError(
                f"ERROR: Jamf Pro version {jamf_pro_version} does not support the v1/packages API endpoint required for this processor"
            )

        filter_name = "packageName"
        object_id = self.get_api_object_id_from_name(
            api_url,
            object_type="package_v1",
            object_name=pkg_name,
            token=token,
            filter_name=filter_name,
            tenant_id=jamf_platform_gw_tenant_id,
        )
        if object_id:
            self.output(f"Package '{pkg_name}' already exists: ID {object_id}")
            pkg_id = object_id  # assign pkg_id for smb runs - JCDS runs get it from the pkg upload
        else:
            self.output(f"Package '{pkg_name}' not found on server")
            pkg_id = 0
        self.output(f"Package ID: {object_id}", verbose_level=3)  # TEMP

        # Process for SMB shares if defined
        self.output(
            "Number of File Share DPs: " + str(len(smb_shares)), verbose_level=2
        )
        for smb_share in smb_shares:
            smb_url, smb_user, smb_password = smb_share[0], smb_share[1], smb_share[2]
            self.output(f"Begin upload to File Share DP {smb_url}", verbose_level=1)
            if "smb://" in smb_url:
                # mount the share
                self.mount_smb(smb_url, smb_user, smb_password)
            # check for existing package
            local_pkg = self.check_local_pkg(smb_url, pkg_name)
            if not local_pkg or replace:
                if replace:
                    self.output(
                        "Replacing existing package as 'replace_pkg' is set to True",
                        verbose_level=1,
                    )
                # copy the file
                self.copy_pkg(smb_url, pkg_path, pkg_name)
                if "smb://" in smb_url:
                    # unmount the share
                    self.umount_smb(smb_url)
                # Don't set this property if
                # 1. We need to upload to the cloud (cloud_dp == True)
                # 2. We have more SMB shares to process
                if not cloud_dp and (len(smb_shares) - 1) == smb_shares.index(
                    smb_share
                ):
                    pkg_uploaded = True
            else:
                self.output(
                    (
                        f"Not replacing existing {pkg_name} as 'replace_pkg' is set to "
                        "False. Use replace_pkg='True' to enforce."
                    ),
                    verbose_level=1,
                )
                if "smb://" in smb_url:
                    # unmount the share
                    self.umount_smb(smb_url)
                if smb_shares and not replace_metadata:
                    # even if we don't upload a package, we still need to pass it on so that a
                    # subsequent processor can use it
                    self.env["pkg_name"] = pkg_name
                    pkg_uploaded = False

        # otherwise process for cloud DP
        if cloud_dp or not smb_shares:
            self.output("Handling Cloud Distribution Point", verbose_level=2)
            if not pkg_id or replace:
                if replace:
                    self.output(
                        "Replacing existing package as 'replace_pkg' is set to True",
                        verbose_level=1,
                    )
                if aws_cdp_mode:
                    # upload the package - this uses sync so we don't need to check if it's changed
                    self.upload_to_aws_s3_bucket(pkg_path, pkg_name)

                    # fake that the package was replaced even if it wasn't
                    # so that the metadata gets replaced
                    pkg_uploaded = True

            else:
                self.output(
                    (
                        f"Not replacing existing {pkg_name} as 'replace_pkg' is set to "
                        f"{replace}. Use replace_pkg='True' to enforce."
                    ),
                    verbose_level=1,
                )
                pkg_uploaded = False

        # check token again using oauth or basic auth depending on the credentials given
        # as package upload may have taken some time
        # (not required for standard mode)
        if smb_shares or aws_cdp_mode:
            # get token using oauth or basic auth depending on the credentials given
            if jamf_url:
                token, jamf_url, jamf_platform_gw_region, jamf_platform_gw_tenant_id = self.auth(
                    jamf_url=jamf_url,
                    jamf_user=jamf_user,
                    password=jamf_password,
                    region=jamf_platform_gw_region,
                    tenant_id=jamf_platform_gw_tenant_id,
                    client_id=client_id,
                    client_secret=client_secret,
                    token=bearer_token,
                    jamf_cli_profile=jamf_cli_profile,
                )
            else:
                raise ProcessorError("ERROR: Jamf Pro URL not supplied")

        # now process the package metadata
        if (
            int(pkg_id) > 0
            and (pkg_uploaded or replace_metadata or replace)
            and not skip_metadata_upload
        ):
            # replace existing package metadata
            self.output(
                f"Updating package metadata for {pkg_id}",
                verbose_level=1,
            )
            self.update_pkg_metadata(
                api_url,
                pkg_name,
                pkg_display_name,
                pkg_metadata,
                sha512string,
                md5string,
                sleep_time,
                token=token,
                max_tries=max_tries,
                pkg_id=pkg_id,
                tenant_id=jamf_platform_gw_tenant_id,
            )
            pkg_metadata_updated = True
        elif int(pkg_id) <= 0 and (
            pkg_uploaded or replace_metadata or not aws_cdp_mode
        ):
            # create new package metadata object when no existing package found
            self.output(
                "Creating package metadata",
                verbose_level=1,
            )
            object_id = self.update_pkg_metadata(
                api_url,
                pkg_name,
                pkg_display_name,
                pkg_metadata,
                sha512string,
                md5string,
                sleep_time,
                token=token,
                max_tries=max_tries,
                pkg_id=pkg_id,
                tenant_id=jamf_platform_gw_tenant_id,
            )
            pkg_metadata_updated = True
        elif not skip_metadata_upload:
            self.output(
                "Not updating package metadata",
                verbose_level=1,
            )
            pkg_metadata_updated = False

        # upload package if the metadata was updated - has to be done last with v1/packages
        # (already done with smb_shares or aws_cdp_mode)
        if not aws_cdp_mode and (not smb_shares or cloud_dp) and pkg_metadata_updated:
            self.output(f"ID: {object_id}", verbose_level=3)  # TEMP
            if object_id != "-1":
                self.output(f"Package '{pkg_name}' metadata exists: ID {object_id}")
                pkg_id = object_id  # assign pkg_id for v1/packages runs
            else:
                raise ProcessorError(
                    "ERROR: Package ID not obtained so cannot upload package"
                )

            self.output(
                "Uploading package to Cloud DP",
                verbose_level=1,
            )
            self.upload_pkg(
                api_url=api_url,
                pkg_path=pkg_path,
                pkg_name=pkg_name,
                pkg_id=pkg_id,
                sleep_time=sleep_time,
                token=token,
                max_tries=max_tries,
                tenant_id=jamf_platform_gw_tenant_id,
            )
            # if we get this far then there was a 200 success response so the package was uploaded
            pkg_uploaded = True

        # recalculate packages on JCDS if the metadata was updated and recalculation requested
        # Jamf Pro 11.10+ only
        if (
            APLooseVersion(jamf_pro_version) >= APLooseVersion("11.10")
            and pkg_metadata_updated
            and recalculate
        ):
            # check token again using oauth or basic auth depending on the credentials given
            # as package upload may have taken some time
            # get token using oauth or basic auth depending on the credentials given
            if jamf_url:
                token, jamf_url, jamf_platform_gw_region, jamf_platform_gw_tenant_id = self.auth(
                    jamf_url=jamf_url,
                    jamf_user=jamf_user,
                    password=jamf_password,
                    region=jamf_platform_gw_region,
                    tenant_id=jamf_platform_gw_tenant_id,
                    client_id=client_id,
                    client_secret=client_secret,
                    token=bearer_token,
                    jamf_cli_profile=jamf_cli_profile,
                )
            else:
                raise ProcessorError("ERROR: Jamf Pro URL not supplied")

            # now send the recalculation request
            packages_recalculated = self.recalculate_packages(
                api_url, token, jamf_platform_gw_tenant_id
            )
        else:
            packages_recalculated = False

        # output the summary
        self.env["pkg_name"] = pkg_name
        self.env["pkg_display_name"] = pkg_display_name
        self.env["pkg_uploaded"] = pkg_uploaded
        self.env["pkg_metadata_updated"] = pkg_metadata_updated
        if pkg_metadata_updated or pkg_uploaded:
            self.env["jamfpackageuploader_summary_result"] = {
                "summary_text": "The following packages were uploaded to or updated in Jamf Pro:",
                "report_fields": [
                    "category",
                    "name",
                    "pkg_name",
                    "pkg_display_name",
                    "pkg_path",
                    "version",
                    "packages_recalculated",
                ],
                "data": {
                    "category": pkg_category,
                    "name": str(self.env.get("NAME")),
                    "pkg_name": pkg_name,
                    "pkg_display_name": pkg_display_name,
                    "pkg_path": pkg_path,
                    "version": version,
                    "packages_recalculated": str(packages_recalculated),
                },
            }
