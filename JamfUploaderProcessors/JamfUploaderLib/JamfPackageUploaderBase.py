#!/usr/local/autopkg/python

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
Requirements for uploading to the JCDS2 API endpoint:
- boto3

To resolve the dependencies, run: /usr/local/autopkg/python -m pip install boto3
"""

import hashlib
import json
import os.path
import shutil
import sys
import threading

from shutil import copyfile
from time import sleep
from urllib.parse import urlparse, quote
import xml.etree.ElementTree as ElementTree
from xml.sax.saxutils import escape

from autopkglib import (
    ProcessorError,
)  # pylint: disable=import-error

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderBase import JamfUploaderBase  # noqa: E402


class ProgressPercentage(object):
    """Class for displaying upload progress"""

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
                "\r%s  %s / %s  (%.2f%%)"
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

    def zip_pkg_path(self, bundle_path, recipe_cache_dir):
        """Add files from path to a zip file handle.

        Args:
            path (str): Path to folder to zip.

        Returns:
            (str) name of resulting zip file.
        """

        zip_name = f"{bundle_path}.zip"

        if os.path.exists(zip_name):
            self.output("Package object is a bundle. " "Zipped archive already exists.")
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

    """Beginning of section for upload to Local Fileshare Distribution Points"""

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
        else:
            self.output(
                f"Expected path not found!: {dirname}",
                verbose_level=2,
            )

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

    def check_pkg(self, pkg_name, jamf_url, token):
        """check if a package with the same name exists in the repo
        note that it is possible to have more than one with the same name
        which could mess things up"""

        object_type = "package"
        url = "{}/{}/name/{}".format(
            jamf_url, self.api_endpoints(object_type), quote(pkg_name)
        )

        request = "GET"
        r = self.curl(
            request=request,
            url=url,
            token=token,
        )

        if r.status_code == 200:
            obj = json.loads(r.output)
            try:
                obj_id = str(obj["package"]["id"])
            except KeyError:
                obj_id = "-1"
        else:
            obj_id = "-1"
        return obj_id

    def curl_pkg(self, pkg_name, pkg_path, jamf_url, enc_creds, obj_id=-1):
        """uploads the package using curl (dbfileupload method)"""

        object_type = "package_upload"
        url = "{}/{}".format(jamf_url, self.api_endpoints(object_type))
        additional_curl_opts = [
            "--header",
            "Accept: application/xml",
            "--header",
            "DESTINATION: 0",
            "--header",
            f"OBJECT_ID: {obj_id}",
            "--header",
            "FILE_TYPE: 0",
            "--header",
            f"FILE_NAME: {pkg_name}",
            "--max-time",
            str("3600"),
        ]

        request = "POST"
        r = self.curl(
            request=request,
            url=url,
            enc_creds=enc_creds,
            additional_curl_opts=additional_curl_opts,
            data=pkg_path,
            endpoint_type="package_upload",
        )

        self.output(f"HTTP response: {r.status_code}", verbose_level=1)
        return r

    """End of section for upload to Local Fileshare Distribution Points"""

    """Beginning of section for upload to JCDS2 endpoint"""

    def sha3sum(self, pkg_path):
        """calculate the SHA-3 512 hash of the package
        (see https://stackoverflow.com/a/44873382)"""
        h = hashlib.sha3_512()
        b = bytearray(128 * 1024)
        mv = memoryview(b)
        with open(pkg_path, "rb", buffering=0) as f:
            for n in iter(lambda: f.readinto(mv), 0):
                h.update(mv[:n])
        return h.hexdigest()

    def check_jcds_for_pkg(self, pkg_path, pkg_name, jamf_url, token):
        """check if a package with the same name exists in the JCDS S3 bucket.
        We'll want to check the name and get the SHA3 of the file.
        If the name and SHA3 match, we can avoid uploading it again.
        If the SHA3 doesn't match we should delete the existing package and upload it again to
        avoid having multiples.
        """

        # calculate the SHA3-512 hash of the package
        pkg_sha3 = self.sha3sum(pkg_path)

        # get the JCDS file list
        object_type = "jcds"
        url = "{}/{}/files".format(jamf_url, self.api_endpoints(object_type))

        request = "GET"
        r = self.curl(
            request=request,
            url=url,
            token=token,
        )

        jcds_pkg_sha3 = 0  # assign empty value to avoid errors
        if r.status_code == 200:
            # the output is not valid JSON: the single quotes need to be converted to double quotes
            parsed_output = str(r.output).replace("'", '"')
            pkg_list = json.loads(parsed_output)
            self.output(pkg_list, verbose_level=3)
            try:
                for obj in pkg_list:
                    if obj["fileName"] == pkg_name:
                        jcds_pkg_sha3 = obj["sha3"]
                        break

            except KeyError:
                pass

        if pkg_sha3 == jcds_pkg_sha3:
            self.output("Package already exists in the S3 bucket.")
            pkg_match = "same"
        elif jcds_pkg_sha3:
            self.output(
                "Package name already exists in the S3 bucket but doesn't match."
            )
            pkg_match = "different"
        else:
            self.output("Package not found in the S3 bucket.")
            pkg_match = ""

        return pkg_match

    def delete_jcds_pkg(self, pkg_name, jamf_url, token):
        """check if a package with the same name exists in the JCDS S3 bucket.
        We'll want to check the name and get the SHA3 of the file.
        If the name and SHA3 match, we can avoid uploading it again.
        If the SHA3 doesn't match we should delete the existing package and upload it again to
        avoid having multiples.
        """

        object_type = "jcds"
        url = "{}/{}/files/{}".format(
            jamf_url, self.api_endpoints(object_type), pkg_name
        )

        request = "DELETE"
        r = self.curl(
            request=request,
            url=url,
            token=token,
        )

        if r.status_code == 204:
            self.output(
                f"Existing package '{pkg_name}' successfully deleted from JCDS",
                verbose_level=2,
            )
            pkg_deleted = 1
            return
        else:
            self.output(
                f"Existing package '{pkg_name}' was not successfully deleted from JCDS",
                verbose_level=2,
            )
            pkg_deleted = 0
        return pkg_deleted

    def initiate_jcds2_upload(
        self,
        pkg_path,
        pkg_name,
        jamf_url,
        token,
    ):
        """get the credentials"""
        object_type = "jcds"
        url = "{}/{}/files".format(jamf_url, self.api_endpoints(object_type))

        count = 0
        while True:
            count += 1
            self.output(
                f"JCDS credentials attempt {count}",
                verbose_level=2,
            )

            request = "POST"
            r = self.curl(
                request=request,
                url=url,
                token=token,
            )
            self.credentials = r.output

            # check HTTP response
            if self.status_check(r, "jcds", pkg_name, request) == "break":
                self.output(
                    "JCDS credentials received. Proceeding to upload the package...",
                    verbose_level=1,
                )
                break
            if count > 5:
                self.output(
                    "WARNING: JCDS2 credentials were not successfully received after 5 attempts"
                )
                self.output(
                    f"HTTP POST Response Code: {r.status_code}",
                    verbose_level=1,
                )
                raise ProcessorError(
                    "ERROR: JCDS2 credentials were not successfully received"
                )
            if int(self.sleep) > 30:
                sleep(int(self.sleep))
            else:
                sleep(30)

            # populate the credentials required for the JCDS upload
            self.output(
                f"HTTP output: {self.credentials}",
                verbose_level=2,
            )

    def upload_to_s3(
        self,
        pkg_path,
        pkg_name,
        credentials,
    ):
        """upload the package"""

        try:
            import boto3
            from botocore.exceptions import ClientError
        except ImportError:
            print(
                "WARNING: could not import boto3 module. Use pip to install requests and try again."
            )
            sys.exit()

        # Upload File To AWS S3
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=credentials["accessKeyID"],
            aws_secret_access_key=credentials["secretAccessKey"],
            aws_session_token=credentials["sessionToken"],
        )
        try:
            s3_client.upload_file(
                pkg_path,
                credentials["bucketName"],
                credentials["path"] + pkg_name,
                Callback=ProgressPercentage(pkg_path),
            )
            self.output("JCDS package upload complete", verbose_level=1)
        except ClientError as e:
            raise ProcessorError(f"Failure uploading to S3: {e}")

    """End of section for upload to JCDS2 endpoint"""

    def update_pkg_metadata(
        self,
        jamf_url,
        pkg_name,
        pkg_display_name,
        pkg_metadata,
        hash_value,
        jcds2_mode,
        pkg_id=0,
        token="",
    ):
        """Update package metadata."""

        if hash_value:
            hash_type = "SHA_512"
        else:
            hash_type = "MD5"

        # build the package record XML
        pkg_data = (
            "<package>"
            + f"<name>{pkg_display_name}</name>"
            + f"<filename>{pkg_name}</filename>"
            + f"<category>{escape(pkg_metadata['category'])}</category>"
            + f"<info>{escape(pkg_metadata['info'])}</info>"
            + f"<notes>{escape(pkg_metadata['notes'])}</notes>"
            + f"<priority>{pkg_metadata['priority']}</priority>"
            + f"<reboot_required>{pkg_metadata['reboot_required']}</reboot_required>"
            + f"<required_processor>{pkg_metadata['required_processor']}</required_processor>"
            + f"<os_requirements>{pkg_metadata['os_requirements']}</os_requirements>"
            + f"<send_notification>{pkg_metadata['send_notification']}</send_notification>"
        )
        if not jcds2_mode:
            pkg_data += (
                f"<hash_type>{hash_type}</hash_type>"
                + f"<hash_value>{hash_value}</hash_value>"
            )
        pkg_data += "</package>"

        object_type = "package"
        url = "{}/{}/id/{}".format(jamf_url, self.api_endpoints(object_type), pkg_id)

        self.output(
            pkg_data,
            verbose_level=2,
        )

        count = 0
        while True:
            count += 1
            self.output(
                f"Package metadata upload attempt {count}",
                verbose_level=2,
            )

            pkg_xml = self.write_temp_file(pkg_data)

            request = "PUT" if pkg_id else "POST"
            r = self.curl(
                request=request,
                url=url,
                token=token,
                data=pkg_xml,
            )

            # check HTTP response
            if self.status_check(r, "Package metadata", pkg_name, request) == "break":
                break
            if count > 5:
                self.output(
                    "WARNING: Package metadata update did not succeed after 5 attempts"
                )
                self.output(
                    f"HTTP POST Response Code: {r.status_code}",
                    verbose_level=1,
                )
                raise ProcessorError("ERROR: Package metadata upload failed ")
            if int(self.sleep) > 30:
                sleep(int(self.sleep))
            else:
                sleep(30)

    def execute(self):
        """Perform the package upload"""

        self.pkg_path = self.env.get("pkg_path")
        if not self.pkg_path:
            try:
                pathname = self.env.get("pathname")
                if pathname.endswith(".pkg"):
                    self.pkg_path = pathname
            except KeyError:
                pass
        self.pkg_name = self.env.get("pkg_name")
        self.pkg_display_name = self.env.get("pkg_display_name")
        self.version = self.env.get("version")
        self.replace = self.env.get("replace_pkg")
        self.sleep = self.env.get("sleep")
        self.replace_metadata = self.env.get("replace_pkg_metadata")
        self.skip_metadata_upload = self.env.get("skip_metadata_upload")
        self.jcds_mode = self.env.get("jcds_mode")
        self.jcds2_mode = self.env.get("jcds2_mode")
        self.jamf_url = self.env.get("JSS_URL")
        self.jamf_user = self.env.get("API_USERNAME")
        self.jamf_password = self.env.get("API_PASSWORD")
        self.client_id = self.env.get("CLIENT_ID")
        self.client_secret = self.env.get("CLIENT_SECRET")
        self.cloud_dp = self.env.get("CLOUD_DP")
        self.recipe_cache_dir = self.env.get("RECIPE_CACHE_DIR")
        self.pkg_uploaded = False
        self.pkg_metadata_updated = False

        # handle setting true/false variables in overrides
        if not self.replace or self.replace == "False":
            self.replace = False
        if not self.replace_metadata or self.replace_metadata == "False":
            self.replace_metadata = False
        if not self.skip_metadata_upload or self.skip_metadata_upload == "False":
            self.skip_metadata_upload = False
        if not self.jcds_mode or self.jcds_mode == "False":
            self.jcds_mode = False
        if not self.jcds2_mode or self.jcds2_mode == "False":
            self.jcds2_mode = False
        if not self.cloud_dp or self.cloud_dp == "False":
            self.cloud_dp = False

        # set pkg_name if not separately defined
        if not self.pkg_name:
            self.pkg_name = os.path.basename(self.pkg_path)

        # give out a warning if jcds_mode was set
        if self.jcds_mode:
            self.output(
                "WARNING: jcds_mode is no longer functional. "
                "This script will continue in normal mode."
            )

        # Create a list of smb shares in tuples
        self.smb_shares = []
        if self.env.get("SMB_URL"):
            if not self.env.get("SMB_USERNAME") or not self.env.get("SMB_PASSWORD"):
                raise ProcessorError("SMB_URL defined but no credentials supplied.")
            self.output(
                "DP 1: {}, {}, pass len: {}".format(
                    self.env.get("SMB_URL"),
                    self.env.get("SMB_USERNAME"),
                    len(self.env.get("SMB_PASSWORD")),
                ),
                verbose_level=2,
            )
            self.smb_shares.append(
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
                        "DP {}: {}, {}, pass len: {}".format(
                            n,
                            self.env.get(f"SMB{n}_URL"),
                            self.env.get(f"SMB{n}_USERNAME"),
                            len(self.env.get(f"SMB{n}_PASSWORD")),
                        ),
                        verbose_level=2,
                    )
                    self.smb_shares.append(
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
                self.smb_shares.append(
                    (
                        share["SMB_URL"],
                        share["SMB_USERNAME"],
                        share["SMB_PASSWORD"],
                    )
                )

        # create a dictionary of package metadata from the inputs
        self.pkg_category = self.env.get("pkg_category")
        self.reboot_required = self.env.get("reboot_required")
        if not self.reboot_required or self.reboot_required == "False":
            self.reboot_required = False
        self.send_notification = self.env.get("send_notification")
        if not self.send_notification or self.send_notification == "False":
            self.send_notification = False

        self.pkg_metadata = {
            "category": self.env.get("pkg_category"),
            "info": self.env.get("pkg_info"),
            "notes": self.env.get("pkg_notes"),
            "reboot_required": self.reboot_required,
            "priority": self.env.get("pkg_priority"),
            "os_requirements": self.env.get("os_requirements"),
            "required_processor": self.env.get("required_processor"),
            "send_notification": self.send_notification,
        }

        # clear any pre-existing summary result
        if "jamfpackageuploader_summary_result" in self.env:
            del self.env["jamfpackageuploader_summary_result"]

        # See if the package is a bundle (directory).
        # If so, zip_pkg_path will look for an existing .zip
        # If that doesn't exist, it will create the zip and return the pkg_path with .zip added
        # In that case, we need to add .zip to the pkg_name key too, if we don't already have it
        if os.path.isdir(self.pkg_path):
            self.pkg_path = self.zip_pkg_path(self.pkg_path, self.recipe_cache_dir)
            if ".zip" not in self.pkg_name:
                self.pkg_name += ".zip"

        # we need to ensure that a zipped package's display name matches the new pkg_name for
        # comparison with an existing package
        if not self.pkg_display_name:
            self.pkg_display_name = self.pkg_name

        # calculate the SHA-512 hash of the package
        self.sha512string = self.sha512sum(self.pkg_path)

        # now start the process of uploading the package
        self.output(
            f"Checking for existing package '{self.pkg_name}' on {self.jamf_url}"
        )

        # get token using oauth or basic auth depending on the credentials given
        # (dbfileupload requires basic auth)
        if self.jamf_url and self.client_id and self.client_secret and self.jcds2_mode:
            token = self.handle_oauth(self.jamf_url, self.client_id, self.client_secret)
        elif self.jamf_url and self.jamf_user and self.jamf_password:
            token = self.handle_api_auth(
                self.jamf_url, self.jamf_user, self.jamf_password
            )
        else:
            raise ProcessorError(
                "ERROR: Valid credentials not supplied (note that API Clients can "
                "only be used with jcds2_mode)"
            )

        # check for existing
        obj_id = self.check_pkg(self.pkg_name, self.jamf_url, token=token)
        self.output(f"ID: {obj_id}", verbose_level=3)  # TEMP
        if obj_id != "-1":
            self.output(
                "Package '{}' already exists: ID {}".format(self.pkg_name, obj_id)
            )
            pkg_id = obj_id  # assign pkg_id for smb runs - JCDS runs get it from the pkg upload
        else:
            self.output("Package '{}' not found on server".format(self.pkg_name))
            pkg_id = 0

        # Process for SMB shares if defined
        self.output(
            "Number of File Share DPs: " + str(len(self.smb_shares)), verbose_level=2
        )
        for smb_share in self.smb_shares:
            smb_url, smb_user, smb_password = smb_share[0], smb_share[1], smb_share[2]
            self.output(f"Begin upload to File Share DP {smb_url}", verbose_level=1)
            if "smb://" in smb_url:
                # mount the share
                self.mount_smb(smb_url, smb_user, smb_password)
            # check for existing package
            local_pkg = self.check_local_pkg(smb_url, self.pkg_name)
            if not local_pkg or self.replace:
                if self.replace:
                    self.output(
                        "Replacing existing package as 'replace_pkg' is set to {}".format(
                            self.replace
                        ),
                        verbose_level=1,
                    )
                # copy the file
                self.copy_pkg(smb_url, self.pkg_path, self.pkg_name)
                if "smb://" in smb_url:
                    # unmount the share
                    self.umount_smb(smb_url)
                # Don't set this property if
                # 1. We need to upload to the cloud (self.cloud_dp == True)
                # 2. We have more SMB shares to process
                if not self.cloud_dp and (
                    len(self.smb_shares) - 1
                ) == self.smb_shares.index(smb_share):
                    self.pkg_uploaded = True
            else:
                self.output(
                    f"Not replacing existing {self.pkg_name} as 'replace_pkg' is set to "
                    f"{self.replace}. Use replace_pkg='True' to enforce."
                )
                if "smb://" in smb_url:
                    # unmount the share
                    self.umount_smb(smb_url)
                if self.smb_shares and not self.replace_metadata:
                    # even if we don't upload a package, we still need to pass it on so that a
                    # subsequent processor can use it
                    self.env["pkg_name"] = self.pkg_name
                    self.pkg_uploaded = False

        # otherwise process for cloud DP
        if self.cloud_dp or not self.smb_shares:
            self.output("Handling Cloud Distribution Point", verbose_level=2)
            if obj_id == "-1" or self.replace:
                if self.replace:
                    self.output(
                        "Replacing existing package as 'replace_pkg' is set to {}".format(
                            self.replace
                        ),
                        verbose_level=1,
                    )
                if self.jcds2_mode:
                    # use jcds endpoint if jcds2_mode is True
                    self.output(
                        "Checking if the same package already exists in the JCDS",
                        verbose_level=1,
                    )
                    pkg_match = self.check_jcds_for_pkg(
                        self.pkg_path,
                        self.pkg_name,
                        self.jamf_url,
                        token=token,
                    )

                    # if package doesn't match, we need to delete the one in the JCDS
                    if pkg_match == "different":
                        pkg_deleted = self.delete_jcds_pkg(
                            self.pkg_name, self.jamf_url, token
                        )
                        if pkg_deleted != 1:
                            self.output(
                                (
                                    "WARNING: Existing package could not be deleted from the JCDS. "
                                    "This is likely to result in a duplicate package"
                                )
                            )

                    # there's really no point in replacing the package in the JCDS if the SHA3 hash
                    # is the same
                    if pkg_match != "same":
                        self.output(
                            "Uploading package using experimental JCDS2 mode",
                            verbose_level=1,
                        )
                        # obtain the session credentials to upload the package
                        self.initiate_jcds2_upload(
                            self.pkg_path,
                            self.pkg_name,
                            self.jamf_url,
                            token=token,
                        )

                        # upload the package
                        self.upload_to_s3(
                            self.pkg_path,
                            self.pkg_name,
                            self.credentials,
                        )

                    # fake that the package was replaced even if it wasn't
                    # so that the metadata gets replaced
                    self.pkg_uploaded = True
                else:
                    # generate enc_creds
                    enc_creds = self.get_enc_creds(self.jamf_user, self.jamf_password)

                    # post the package (won't run if the pkg exists and replace is False)
                    r = self.curl_pkg(
                        self.pkg_name, self.pkg_path, self.jamf_url, enc_creds, obj_id
                    )
                    try:
                        pkg_id = ElementTree.fromstring(r.output).findtext("id")
                        success = ElementTree.fromstring(r.output).findtext(
                            "successful"
                        )
                        if pkg_id:
                            if success == "true":
                                self.output(
                                    "Package uploaded successfully, ID={}".format(
                                        pkg_id
                                    )
                                )
                                self.pkg_uploaded = True
                            else:
                                raise ProcessorError(
                                    "WARNING: Response reported 'Error uploading file to the JSS'"
                                )
                    except ElementTree.ParseError:
                        self.output("Could not parse XML. Raw output:", verbose_level=2)
                        self.output(r.output.decode("ascii"), verbose_level=2)
                        raise ProcessorError(
                            "WARNING: Could not read HTTP response. The package was probably not "
                            "uploaded successfully"
                        )
                    else:
                        # check HTTP response
                        if (
                            not self.status_check(r, "Package", self.pkg_name, "POST")
                            == "break"
                        ):
                            raise ProcessorError("ERROR: Package upload failed.")
            else:
                self.output(
                    (
                        f"Not replacing existing {self.pkg_name} as 'replace_pkg' is set to "
                        f"{self.replace}. Use replace_pkg='True' to enforce."
                    ),
                    verbose_level=1,
                )
                self.pkg_uploaded = False

        # now process the package metadata if specified (not applicable with jcds mode)
        if (
            int(pkg_id) > 0
            and (self.pkg_uploaded or self.replace_metadata)
            and not self.skip_metadata_upload
        ):
            self.output(
                "Updating package metadata for {}".format(pkg_id),
                verbose_level=1,
            )
            self.update_pkg_metadata(
                self.jamf_url,
                self.pkg_name,
                self.pkg_display_name,
                self.pkg_metadata,
                self.sha512string,
                self.jcds2_mode,
                pkg_id=pkg_id,
                token=token,
            )
            self.pkg_metadata_updated = True
        elif (self.smb_shares or self.jcds2_mode) and not pkg_id:
            self.output(
                "Creating package metadata",
                verbose_level=1,
            )
            self.update_pkg_metadata(
                self.jamf_url,
                self.pkg_name,
                self.pkg_display_name,
                self.pkg_metadata,
                self.sha512string,
                self.jcds2_mode,
                pkg_id=pkg_id,
                token=token,
            )
            self.pkg_metadata_updated = True
        elif not self.skip_metadata_upload:
            self.output(
                "Not updating package metadata",
                verbose_level=1,
            )
            self.pkg_metadata_updated = False

        # output the summary
        self.env["pkg_name"] = self.pkg_name
        self.env["pkg_display_name"] = self.pkg_display_name
        self.env["pkg_uploaded"] = self.pkg_uploaded
        self.env["pkg_metadata_updated"] = self.pkg_metadata_updated
        if self.pkg_metadata_updated or self.pkg_uploaded:
            self.env["jamfpackageuploader_summary_result"] = {
                "summary_text": "The following packages were uploaded to or updated in Jamf Pro:",
                "report_fields": [
                    "category",
                    "name",
                    "pkg_name",
                    "pkg_display_name",
                    "pkg_path",
                    "version",
                ],
                "data": {
                    "category": self.pkg_category,
                    "name": str(self.env.get("NAME")),
                    "pkg_name": self.pkg_name,
                    "pkg_display_name": self.pkg_display_name,
                    "pkg_path": self.pkg_path,
                    "version": self.version,
                },
            }
