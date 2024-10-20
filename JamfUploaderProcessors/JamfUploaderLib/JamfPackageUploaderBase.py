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

    def sha256sum(self, filename):
        """calculate the SHA256 hash of the package
        (see https://stackoverflow.com/a/44873382)"""
        h = hashlib.sha256()
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
    # Beginning of function for upload to deprecated dbfileupload endpoint

    def pkg_dbfileupload(self, pkg_name, pkg_path, jamf_url, enc_creds, obj_id=-1):
        """uploads the package using the legacy dbfileupload method.
        Note: endpoint removed in Jamf Pro 11.5."""

        object_type = "package_upload"
        url = f"{jamf_url}/{self.api_endpoints(object_type)}"
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

    # End of function for uploading to Local Fileshare Distribution Points
    # ------------------------------------------------------------------------
    # Beginning of functions for uploading to v1/packages endpoint

    def upload_pkg(self, pkg_path, pkg_name, pkg_id, jamf_url, token):
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
        url = f"{jamf_url}/{self.api_endpoints(object_type)}/{pkg_id}/upload"
        count = 0
        while True:
            count += 1
            self.output(
                f"Package upload attempt {count}",
                verbose_level=2,
            )

            request = "POST"
            r = self.curl(
                request=request,
                url=url,
                token=token,
                data=pkg_path,
                endpoint_type="package_v1",
            )

            # check HTTP response
            if self.status_check(r, "Package upload", pkg_name, request) == "break":
                break
            if count > 5:
                self.output("WARNING: Package upload did not succeed after 5 attempts")
                self.output(
                    f"HTTP POST Response Code: {r.status_code}",
                    verbose_level=1,
                )
                raise ProcessorError("ERROR: Package upload failed ")
            if int(self.sleep) > 30:
                sleep(int(self.sleep))
            else:
                sleep(30)

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
    # Beginning of functions for upload to JCDS2 endpoint (not needed for 11.5+)

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
        url = f"{jamf_url}/{self.api_endpoints(object_type)}/files"

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
        url = f"{jamf_url}/{self.api_endpoints(object_type)}/files/{pkg_name}"

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
        pkg_name,
        jamf_url,
        token,
    ):
        """get the credentials"""
        object_type = "jcds"
        url = f"{jamf_url}/{self.api_endpoints(object_type)}/files"

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

    def upload_to_jcds2_s3_bucket(
        self,
        pkg_path,
        pkg_name,
        credentials,
    ):
        """
        upload the package using the jcds API endpoint

        Note that this requires the boto3 python module
        To install this, run the following command

        /usr/local/autopkg/python -m pip install boto3

        See https://boto3.amazonaws.com/v1/documentation/api/latest/guide/quickstart.html
        and
        https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html#guide-configuration
        """

        try:
            import boto3  # pylint: disable=import-outside-toplevel
            from botocore.exceptions import (  # pylint: disable=import-outside-toplevel
                ClientError,
            )
        except ImportError:
            print(
                "WARNING: could not import boto3 module. Use pip to install boto3 and try again:",
                "/usr/local/autopkg/python -m pip install boto3",
            )
            sys.exit()

        self.output(
            (
                "JCDS credentials:",
                f"Access Key: {credentials['accessKeyID']}",
                f"Bucket Name: {credentials['bucketName']}",
                f"Path: {credentials['path']}",
                f"Region: {credentials['region']}",
            ),
            verbose_level=3,
        )  # TEMP

        # Upload File To AWS S3
        s3_client = boto3.client(
            "s3",
            credentials["region"],
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
            raise ProcessorError(f"Failure uploading to S3: {e}") from e

    # End of function for uploading to JCDS2 endpoint
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

    def check_pkg(self, pkg_name, jamf_url, token):
        """check if a package with the same name exists in the repo
        note that it is possible to have more than one with the same name
        which could mess things up"""

        object_type = "package"
        url = f"{jamf_url}/{self.api_endpoints(object_type)}/name/{quote(pkg_name)}"

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

    def get_category_id(self, jamf_url, category_name, token=""):
        """Get the category ID from the name, or abort if ID not found"""
        # check for existing category
        self.output(f"Checking for '{category_name}' on {jamf_url}")
        obj_type = "category"
        obj_name = category_name
        obj_id = self.get_uapi_obj_id_from_name(
            jamf_url,
            obj_type,
            obj_name,
            token,
        )

        if obj_id:
            self.output(f"Category '{category_name}' exists: ID {obj_id}")
            return obj_id
        else:
            self.output(f"Category '{category_name}' not found")
            raise ProcessorError("Supplied package category does not exist")

    def update_pkg_metadata_api(  # pylint: disable=too-many-arguments, too-many-locals
        self,
        jamf_url,
        pkg_name,
        pkg_display_name,
        pkg_metadata,
        hash_value,
        pkg_id=0,
        token="",
    ):
        """Update package metadata using v1/packages endpoint. Requires 11.5+"""

        # get category ID
        if pkg_metadata["category"]:
            category_id = self.get_category_id(
                jamf_url, pkg_metadata["category"], token
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

        if hash_value:
            hash_type = "SHA_512"
            pkg_data["hashType"] = hash_type
            pkg_data["hashValue"] = hash_value

        self.output(
            "Package metadata:",
            verbose_level=2,
        )
        self.output(
            pkg_data,
            verbose_level=2,
        )

        pkg_json = self.write_json_file(pkg_data)

        # if we find a pkg ID we put, if not, we post
        object_type = "package_v1"
        if int(pkg_id) > 0:
            url = "{}/{}/{}".format(jamf_url, self.api_endpoints(object_type), pkg_id)
        else:
            url = "{}/{}".format(jamf_url, self.api_endpoints(object_type))

        count = 0
        while True:
            count += 1
            self.output(
                "Package metadata upload attempt {}".format(count),
                verbose_level=2,
            )
            request = "PUT" if pkg_id else "POST"
            r = self.curl(request=request, url=url, token=token, data=pkg_json)
            # check HTTP response
            if self.status_check(r, "Package Metadata", pkg_name, request) == "break":
                break
            if count > 5:
                self.output("Package metadata upload did not succeed after 5 attempts")
                self.output("\nHTTP POST Response Code: {}".format(r.status_code))
                raise ProcessorError("ERROR: Package metadata upload failed ")
            if int(self.sleep) > 30:
                sleep(int(self.sleep))
            else:
                sleep(30)
        if r.status_code == 201:
            obj = json.loads(json.dumps(r.output))
            self.output(
                obj,
                verbose_level=4,
            )

            try:
                obj_id = obj["id"]
            except KeyError:
                obj_id = "-1"
        else:
            obj_id = "-1"
        return obj_id

    def update_pkg_metadata(  # pylint: disable=too-many-arguments, too-many-locals
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
        """Update package metadata - legacy for older than 11.5"""

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
        url = f"{jamf_url}/{self.api_endpoints(object_type)}/id/{pkg_id}"

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

    # End functions for uploading pkg metadata
    # ------------------------------------------------------------------------
    # Begin function for recalulating packages on JCDS

    def recalculate_packages(self, jamf_url, token):
        """Send a request to recalulate the JCDS packages"""
        # get the JCDS file list
        object_type = "jcds"
        url = f"{jamf_url}/{self.api_endpoints(object_type)}/refresh-inventory"

        request = "POST"
        r = self.curl(
            request=request,
            url=url,
            token=token,
        )

        if r.status_code == 204:
            self.output(
                "JCDS Packages successfully recalculated",
                verbose_level=2,
            )
            packages_recalculated = True
        else:
            self.output(
                f"WARNING: JCDS Packages NOT successfully recalculated (response={r.status_code})",
                verbose_level=1,
            )
            packages_recalculated = False
        return packages_recalculated

    # End functions for recalulating packages on JCDS
    # ------------------------------------------------------------------------

    # ------------------------------------------------------------------------
    # MAIN FUNCTION
    def execute(
        self,
    ):  # pylint: disable=too-many-branches, too-many-locals, too-many-statements
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
        self.jcds2_mode = self.env.get("jcds2_mode")
        self.aws_cdp_mode = self.env.get("aws_cdp_mode")
        self.recalculate = self.env.get("recalculate")
        self.jamf_url = self.env.get("JSS_URL").rstrip("/")
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
        if not self.jcds2_mode or self.jcds2_mode == "False":
            self.jcds2_mode = False
        if not self.aws_cdp_mode or self.aws_cdp_mode == "False":
            self.aws_cdp_mode = False
        if not self.recalculate or self.recalculate == "False":
            self.recalculate = False
        if not self.cloud_dp or self.cloud_dp == "False":
            self.cloud_dp = False

        # set pkg_name if not separately defined
        if not self.pkg_name:
            self.pkg_name = os.path.basename(self.pkg_path)

        # Create a list of smb shares in tuples
        self.smb_shares = []
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
                        (
                            f"DP {n}:",
                            self.env.get(f"SMB{n}_URL"),
                            self.env.get(f"SMB{n}_USERNAME"),
                            "pass len:",
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

        # calculate the SHA-256 hash of the package
        # self.sha256string = self.sha256sum(self.pkg_path)

        # now start the process of uploading the package
        self.output(
            f"Checking for existing package '{self.pkg_name}' on {self.jamf_url}"
        )

        # get token using oauth or basic auth depending on the credentials given
        # (dbfileupload requires basic auth)
        if self.jamf_url and self.client_id and self.client_secret:
            token = self.handle_oauth(self.jamf_url, self.client_id, self.client_secret)
        elif self.jamf_url and self.jamf_user and self.jamf_password:
            token = self.handle_api_auth(
                self.jamf_url, self.jamf_user, self.jamf_password
            )
        else:
            raise ProcessorError(
                "ERROR: Valid credentials not supplied (note that API Clients cannot "
                "be used on Jamf Pro versions older than 11.5)"
            )

        # get Jamf Pro version to determine default mode
        # Version 11.5+ will use the v1/packages endpoint
        # Version 11.4- will use JSSResource/packages and dbfileupload
        jamf_pro_version = self.get_jamf_pro_version(self.jamf_url, token)
        if APLooseVersion(jamf_pro_version) < APLooseVersion("11.5"):
            self.legacy_mode = True
        else:
            self.legacy_mode = False

        # check for existing pkg (use new API if 11.5+)
        if self.legacy_mode:
            obj_id = self.check_pkg(self.pkg_name, self.jamf_url, token=token)
            self.output(f"Package ID: {obj_id}", verbose_level=3)  # TEMP
            if obj_id and obj_id != "-1":
                self.output(f"Package '{self.pkg_name}' already exists: ID {obj_id}")
                pkg_id = obj_id  # assign pkg_id for smb runs - JCDS runs get it from the pkg upload
            else:
                self.output(f"Package '{self.pkg_name}' not found on server")
                pkg_id = 0
        else:
            filter_name = "packageName"
            obj_id = self.get_uapi_obj_id_from_name(
                self.jamf_url,
                "package_v1",
                self.pkg_name,
                token=token,
                filter_name=filter_name,
            )

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
                        "Replacing existing package as 'replace_pkg' is set to True",
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
        pkg_id = 0
        if self.cloud_dp or not self.smb_shares:
            self.output("Handling Cloud Distribution Point", verbose_level=2)
            if obj_id == "-1" or self.replace:
                if self.replace:
                    self.output(
                        "Replacing existing package as 'replace_pkg' is set to True",
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
                            self.pkg_name,
                            self.jamf_url,
                            token=token,
                        )

                        # upload the package
                        self.upload_to_jcds2_s3_bucket(
                            self.pkg_path,
                            self.pkg_name,
                            self.credentials,
                        )

                    # fake that the package was replaced even if it wasn't
                    # so that the metadata gets replaced
                    self.pkg_uploaded = True

                elif self.aws_cdp_mode:
                    # upload the package - this uses sync so we don't need to check if it's changed
                    self.upload_to_aws_s3_bucket(self.pkg_path, self.pkg_name)

                    # fake that the package was replaced even if it wasn't
                    # so that the metadata gets replaced
                    self.pkg_uploaded = True

                elif self.legacy_mode:  # dbfileupload mode
                    # generate enc_creds
                    enc_creds = self.get_enc_creds(self.jamf_user, self.jamf_password)

                    # post the package (won't run if the pkg exists and replace is False)
                    r = self.pkg_dbfileupload(
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
                                    f"Package uploaded successfully, ID={pkg_id}"
                                )
                                self.pkg_uploaded = True
                            else:
                                raise ProcessorError(
                                    "WARNING: Response reported 'Error uploading file to the JSS'"
                                )
                    except ElementTree.ParseError as exc:
                        self.output("Could not parse XML. Raw output:", verbose_level=2)
                        self.output(r.output.decode("ascii"), verbose_level=2)
                        raise ProcessorError(
                            "WARNING: Could not read HTTP response. The package was probably not "
                            "uploaded successfully"
                        ) from exc
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

        # check token again using oauth or basic auth depending on the credentials given
        # as package upload may have taken some time
        # (not required for standard mode)
        if (
            not self.smb_shares
            and not self.aws_cdp_mode
            and not self.jcds2_mode
            and not self.legacy_mode
        ):
            if self.jamf_url and self.client_id and self.client_secret:
                token = self.handle_oauth(
                    self.jamf_url, self.client_id, self.client_secret
                )
            elif self.jamf_url and self.jamf_user and self.jamf_password:
                token = self.handle_api_auth(
                    self.jamf_url, self.jamf_user, self.jamf_password
                )
            else:
                raise ProcessorError("ERROR: Valid credentials not supplied")

        # now process the package metadata
        if (
            int(pkg_id) > 0
            and (self.pkg_uploaded or self.replace_metadata or self.replace)
            and not self.skip_metadata_upload
        ):
            # replace existing package metadata
            self.output(
                f"Updating package metadata for {pkg_id}",
                verbose_level=1,
            )
            if self.legacy_mode:
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
            else:
                self.update_pkg_metadata_api(
                    self.jamf_url,
                    self.pkg_name,
                    self.pkg_display_name,
                    self.pkg_metadata,
                    self.sha512string,
                    pkg_id=pkg_id,
                    token=token,
                )
            self.pkg_metadata_updated = True
        elif int(pkg_id) <= 0 and (
            self.pkg_uploaded
            or (not self.legacy_mode and not self.jcds2_mode and not self.aws_cdp_mode)
        ):
            # create new package metadata object when no existing package found
            self.output(
                "Creating package metadata",
                verbose_level=1,
            )
            if APLooseVersion(jamf_pro_version) >= APLooseVersion("11.5"):
                obj_id = self.update_pkg_metadata_api(
                    self.jamf_url,
                    self.pkg_name,
                    self.pkg_display_name,
                    self.pkg_metadata,
                    self.sha512string,
                    pkg_id=pkg_id,
                    token=token,
                )
            else:
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

        # upload package if the metadata was updated - has to be done last with v1/packages
        # (already done with smb_shares, jcds2_mode and aws_cdp_mode)
        if (
            not self.jcds2_mode
            and not self.aws_cdp_mode
            and not self.legacy_mode
            and (not self.smb_shares or self.cloud_dp)
            and self.pkg_metadata_updated
        ):
            self.output(f"ID: {obj_id}", verbose_level=3)  # TEMP
            if obj_id != "-1":
                self.output(f"Package '{self.pkg_name}' metadata exists: ID {obj_id}")
                pkg_id = obj_id  # assign pkg_id for v1/packages runs
            else:
                raise ProcessorError(
                    "ERROR: Package ID not obtained so cannot upload package"
                )

            self.output(
                "Uploading package to Cloud DP",
                verbose_level=1,
            )
            r = self.upload_pkg(
                self.pkg_path, self.pkg_name, pkg_id, self.jamf_url, token
            )
            # if we get this far then there was a 200 success response so the package was uploaded
            self.pkg_uploaded = True

        # recalculate packages on JCDS if the metadata was updated and recalculation requested
        # Jamf Pro 11.10+ only
        if (
            APLooseVersion(jamf_pro_version) >= APLooseVersion("11.10")
            and self.pkg_metadata_updated
            and self.recalculate
        ):
            # check token again using oauth or basic auth depending on the credentials given
            # as package upload may have taken some time
            if self.client_id and self.client_secret:
                token = self.handle_oauth(
                    self.jamf_url, self.client_id, self.client_secret
                )
            elif self.jamf_user and self.jamf_password:
                token = self.handle_api_auth(
                    self.jamf_url, self.jamf_user, self.jamf_password
                )
            else:
                raise ProcessorError("ERROR: Valid credentials not supplied")

            # now send the recalculation request
            packages_recalculated = self.recalculate_packages(self.jamf_url, token)
        else:
            packages_recalculated = False

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
                    "packages_recalculated",
                ],
                "data": {
                    "category": self.pkg_category,
                    "name": str(self.env.get("NAME")),
                    "pkg_name": self.pkg_name,
                    "pkg_display_name": self.pkg_display_name,
                    "pkg_path": self.pkg_path,
                    "version": self.version,
                    "packages_recalculated": str(packages_recalculated),
                },
            }
