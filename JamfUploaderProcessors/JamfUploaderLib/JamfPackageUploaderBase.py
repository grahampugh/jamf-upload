#!/usr/local/autopkg/python

"""
Base classes for uploading a package to Jamf Pro

Note the requirements for uploading to the JCDS2 API endpoint:
- boto3

To resolve the dependencies, run: /usr/local/autopkg/python -m pip install boto3
"""

# import boto3
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
            self.output("Package object is a bundle. "
                        "Zipped archive already exists.")
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

    def mount_smb(self, mount_share, mount_user, mount_pass):
        """Mount distribution point."""
        mount_cmd = [
            "/usr/bin/osascript",
            "-e",
            (
                f'mount volume "{mount_share}" as user name "{mount_user}" '
                f'with password "{mount_pass}"'
            ),
        ]
        self.output(
            f"Mount command: {' '.join(mount_cmd)}",
            verbose_level=4,
        )

        r = subprocess.check_output(mount_cmd)
        self.output(
            r.decode("ascii"),
            # r,
            verbose_level=4,
        )

    def umount_smb(self, mount_share):
        """Unmount distribution point."""
        path = f"/Volumes{urlparse(mount_share).path}"
        cmd = ["/usr/sbin/diskutil", "unmount", path]
        try:
            r = subprocess.check_output(cmd)
            self.output(
                r.decode("ascii"),
                verbose_level=2,
            )
        except subprocess.CalledProcessError:
            self.output("WARNING! Unmount failed.")

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
