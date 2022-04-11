#!/usr/local/autopkg/python

"""
JamfPackageUploader processor for AutoPkg
    by G Pugh

Developed from an idea posted at
    https://www.jamf.com/jamf-nation/discussions/27869#responseChild166021
"""


import os
import re
import sys
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ElementTree

from shutil import copyfile
from time import sleep
from zipfile import ZipFile, ZIP_DEFLATED
from urllib.parse import urlparse, quote, quote_plus
from xml.sax.saxutils import escape
from autopkglib import ProcessorError  # pylint: disable=import-error

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfUploaderBase import JamfUploaderBase  # noqa: E402

__all__ = ["JamfPackageUploader"]


class JamfPackageUploader(JamfUploaderBase):
    """A processor for AutoPkg that will upload a package to a JCDS or
    File Share Distribution Point.
    Can be run as a post-processor for a pkg recipe or in a child recipe.
    The pkg recipe must output pkg_path or this will fail."""

    input_variables = {
        "pkg_name": {
            "required": False,
            "description": "Package name. If supplied, will rename the package supplied "
            "in the pkg_path key when uploading it to the fileshare.",
            "default": "",
        },
        "pkg_path": {
            "required": False,
            "description": "Path to a pkg or dmg to import - provided by "
            "previous pkg recipe/processor.",
            "default": "",
        },
        "version": {
            "required": False,
            "description": "Version string - provided by "
            "previous pkg recipe/processor.",
            "default": "",
        },
        "pkg_category": {
            "required": False,
            "description": "Package category",
            "default": "",
        },
        "pkg_info": {
            "required": False,
            "description": "Package info field",
            "default": "",
        },
        "pkg_notes": {
            "required": False,
            "description": "Package notes field",
            "default": "",
        },
        "pkg_priority": {
            "required": False,
            "description": "Package priority. Default=10",
            "default": "10",
        },
        "reboot_required": {
            "required": False,
            "description": (
                "Whether a package requires a reboot after installation. "
                "Default='False'"
            ),
            "default": "",
        },
        "os_requirements": {
            "required": False,
            "description": "Package OS requirement",
            "default": "",
        },
        "required_processor": {
            "required": False,
            "description": "Package required processor. Acceptable values are 'x86' or 'None'",
            "default": "None",
        },
        "send_notification": {
            "required": False,
            "description": (
                "Whether to send a notification when a package is installed. "
                "Default='False'"
            ),
            "default": "",
        },
        "replace_pkg": {
            "required": False,
            "description": "Overwrite an existing package if True.",
            "default": "False",
        },
        "jcds_mode": {
            "required": False,
            "description": "Use private API jcds mode if True.",
            "default": "False",
        },
        "replace_pkg_metadata": {
            "required": False,
            "description": "Overwrite existing package metadata and continue if True, "
            "even if the package object is not re-uploaded.",
            "default": "False",
        },
        "JSS_URL": {
            "required": True,
            "description": "URL to a Jamf Pro server that the API user has write access "
            "to, optionally set as a key in the com.github.autopkg "
            "preference file.",
        },
        "API_USERNAME": {
            "required": True,
            "description": "Username of account with appropriate access to "
            "jss, optionally set as a key in the com.github.autopkg "
            "preference file.",
        },
        "API_PASSWORD": {
            "required": True,
            "description": "Password of api user, optionally set as a key in "
            "the com.github.autopkg preference file.",
        },
        "SMB_URL": {
            "required": False,
            "description": "URL to a Jamf Pro fileshare distribution point "
            "which should be in the form smb://server "
            "preference file.",
            "default": "",
        },
        "SMB_USERNAME": {
            "required": False,
            "description": "Username of account with appropriate access to "
            "jss, optionally set as a key in the com.github.autopkg "
            "preference file.",
            "default": "",
        },
        "SMB_PASSWORD": {
            "required": False,
            "description": "Password of api user, optionally set as a key in "
            "the com.github.autopkg preference file.",
            "default": "",
        },
    }

    output_variables = {
        "pkg_path": {
            "description": "The path of the package as provided from the parent recipe.",
        },
        "pkg_name": {"description": "The name of the uploaded package."},
        "pkg_uploaded": {
            "description": "True/False depending if a package was uploaded or not.",
        },
        "jamfpackageuploader_summary_result": {
            "description": "Description of interesting results.",
        },
    }

    description = __doc__

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
            verbose_level=3,
        )

        r = subprocess.check_output(mount_cmd)
        self.output(
            # r.decode("ascii"), verbose_level=2,
            r,
            verbose_level=2,
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

    def zip_pkg_path(self, bundle_path):
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

        self.output("Package object is a bundle. Converting to zip...")
        with ZipFile(zip_name, "w", ZIP_DEFLATED, allowZip64=True) as zip_handle:
            for root, _, files in os.walk(bundle_path):
                for member in files:
                    zip_handle.write(os.path.join(root, member))
            self.output(
                f"Closing: {zip_name}",
                verbose_level=2,
            )
        return zip_name

    def check_pkg(self, pkg_name, jamf_url, enc_creds="", token=""):
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
            enc_creds=enc_creds,
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
        """uploads the package using curl"""

        object_type = "package_upload"
        url = "{}/{}".format(jamf_url, self.api_endpoints(object_type))
        additional_headers = [
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
            additional_headers=additional_headers,
            data=pkg_path,
        )

        self.output(f"HTTP response: {r.status_code}", verbose_level=1)
        return r

    # Section for upload to Jamf Cloud using jcds endpoint

    def get_pkg_category_id(self, url, category, enc_creds="", token=""):
        """get the pkg category ID - required for API v3 uploads"""
        # check for existing category
        self.output(f"Checking for existing '{category}' on {url}")
        obj_type = "category"
        obj_name = category
        obj_id = self.get_uapi_obj_id_from_name(
            url,
            obj_type,
            obj_name,
            token,
        )
        self.output(f"ID for category {category}: {obj_id}", verbose_level=1)
        return obj_id

    def create_session(self, jamf_url, user, password):
        """create session cookies for the package upload endpoint"""
        url = jamf_url + "/?failover"
        tmp_dir = self.make_tmp_dir()
        cookie_jar = os.path.join(tmp_dir, "curl_cookies_from_jamf_upload.txt")
        additional_headers = [
            "--header",
            "Content-Type: application/x-www-form-urlencoded",
            "--data-urlencode",
            f"username={user}",
            "--data-urlencode",
            f"password={password}",
            "--cookie-jar",
            cookie_jar,
            "--location",
        ]
        request = "POST"
        r = self.curl(
            request=request,
            url=url,
            additional_headers=additional_headers,
        )

        self.output(f"HTTP response: {r.status_code}", verbose_level=1)
        self.output(f"Headers: {r.headers}", verbose_level=2)

    def get_session_token(self, jamf_url, pkg_id):
        """get a session token, x-auth token and pkg upload URL
        for the package upload endpoint"""
        url = f"{jamf_url}/legacy/packages.html?id={pkg_id}&o=c"
        additional_headers = [
            "--location",
        ]
        request = "GET"
        r = self.curl(
            request=request,
            url=url,
            additional_headers=additional_headers,
        )
        self.output(f"HTTP response: {r.status_code}", verbose_level=1)
        self.output(str(r.output), verbose_level=3)

        # session token
        matches = re.search(r'id="session-token" value="([^"]*)"', str(r.output))
        if matches:
            session_token = matches.group(1)
            self.output("Session Token: " + session_token, verbose_level=2)
        else:
            raise ProcessorError("WARNING: No package upload session token was found")
        matches = re.search(r'"X-Auth-Token", "([^"]*)"', str(r.output))

        # x-auth token
        if matches:
            x_auth_token = matches.group(1)
            self.output("X-Auth Token: " + x_auth_token, verbose_level=2)
        else:
            raise ProcessorError("WARNING: No x-auth token was found")
        matches = re.search(r'const url = "([^"]*)"', str(r.output))

        # pkg upload URL
        if matches:
            pkg_upload_url = matches.group(1)
            self.output("Pkg Upload URL: " + pkg_upload_url, verbose_level=2)
        else:
            raise ProcessorError("WARNING: No package upload URL was found")

        return session_token, x_auth_token, pkg_upload_url

    def post_pkg(self, jamf_url, pkg_name, pkg_path, x_auth_token, pkg_upload_url):
        """upload the package via the v3 endpoint"""
        url = f"{pkg_upload_url}/{quote(pkg_name)}"
        self.output(f"Pkg Upload URL: {url}", verbose_level=1)
        additional_headers = [
            "--header",
            f"x-auth-token: {x_auth_token}",
            "--header",
            "accept: */*",
            "--header",
            f"origin: {jamf_url}",
            "--header",
            f"referer: {jamf_url}",
            "--form",
            f"file=@{pkg_path};filename={pkg_name}",
            "--compressed",
        ]
        request = "POST"
        r = self.curl(
            request=request,
            url=url,
            additional_headers=additional_headers,
        )
        self.output(f"HTTP response: {r.status_code}", verbose_level=1)
        self.output(r.output, verbose_level=3)

    def create_pkg_object(
        self, jamf_url, pkg_name, pkg_id, session_token, pkg_category_id
    ):
        """record the package in in the jamf server"""
        url = f"{jamf_url}/legacy/packages.html?id={pkg_id}&o=c"
        self.output(f"Pkg Object URL: {url}", verbose_level=1)
        additional_headers = [
            "--header",
            f"origin: {jamf_url}",
            "--header",
            f"referer: {jamf_url}/legacy/packages.html?id={pkg_id}&o=c",
            "--header",
            "content-type: application/x-www-form-urlencoded",
            "--header",
            (
                "accept: text/html,application/xhtml+xml,application/xml;"
                + "q=0.9,image/avif,image/webp,image/apng,*/*;"
                + "q=0.8,application/signed-exchange;v=b3;q=0.9"
            ),
            "--data-raw",
            (
                f"session-token={session_token}"
                + "&lastTab=General"
                + "&lastSideTab=null"
                + "&lastSubTab=null"
                + "&lastSubTabSet=null"
                + f"&name={quote_plus(pkg_name)}"
                + f"&categoryID={pkg_category_id}"
                + f"&fileInputfileName={quote_plus(pkg_name)}"
                + f"&fileName={quote_plus(pkg_name)}"
                + "&resetFIELD_MANIFEST_INPUT="
                + "&info="
                + self.pkg_metadata["info"]
                + "&notes="
                + self.pkg_metadata["notes"]
                + "&priority="
                + self.pkg_metadata["priority"]
                + "&uninstall_disabled=false"
                + "&osRequirements="
                + "&action=Save"
            ),
            "--compressed",
        ]
        request = "POST"
        r = self.curl(
            request=request,
            url=url,
            additional_headers=additional_headers,
        )
        self.output("HTTP response: {}".format(r.status_code), verbose_level=1)
        self.output(r.output, verbose_level=3)

    # End of section for upload to Jamf Cloud using v3 endpoint

    def update_pkg_metadata(
        self,
        jamf_url,
        pkg_name,
        pkg_metadata,
        hash_value,
        pkg_id=0,
        enc_creds="",
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
            + f"<name>{pkg_name}</name>"
            + f"<filename>{pkg_name}</filename>"
            + f"<category>{escape(pkg_metadata['category'])}</category>"
            + f"<info>{escape(pkg_metadata['info'])}</info>"
            + f"<notes>{escape(pkg_metadata['notes'])}</notes>"
            + f"<priority>{pkg_metadata['priority']}</priority>"
            + f"<reboot_required>{pkg_metadata['reboot_required']}</reboot_required>"
            + f"<required_processor>{pkg_metadata['required_processor']}</required_processor>"
            + f"<os_requirements>{pkg_metadata['os_requirements']}</os_requirements>"
            + f"<hash_type>{hash_type}</hash_type>"
            + f"<hash_value>{hash_value}</hash_value>"
            + f"<send_notification>{pkg_metadata['send_notification']}</send_notification>"
            + "</package>"
        )

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
                enc_creds=enc_creds,
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
            sleep(30)

    def main(self):
        """Do the main thing here"""

        self.pkg_path = self.env.get("pkg_path")
        if not self.pkg_path:
            try:
                pathname = self.env.get("pathname")
                if pathname.endswith(".pkg"):
                    self.pkg_path = pathname
            except KeyError:
                pass
        self.pkg_name = self.env.get("pkg_name")
        if not self.pkg_name:
            self.pkg_name = os.path.basename(self.pkg_path)
        self.version = self.env.get("version")
        self.replace = self.env.get("replace_pkg")
        # handle setting replace in overrides
        if not self.replace or self.replace == "False":
            self.replace = False
        self.replace_metadata = self.env.get("replace_pkg_metadata")
        # handle setting replace_metadata in overrides
        if not self.replace_metadata or self.replace_metadata == "False":
            self.replace_metadata = False
        self.jcds_mode = self.env.get("jcds_mode")
        # handle setting jcds_mode in overrides
        if not self.jcds_mode or self.jcds_mode == "False":
            self.jcds_mode = False
        self.jamf_url = self.env.get("JSS_URL")
        self.jamf_user = self.env.get("API_USERNAME")
        self.jamf_password = self.env.get("API_PASSWORD")
        self.smb_url = self.env.get("SMB_URL")
        self.smb_user = self.env.get("SMB_USERNAME")
        self.smb_password = self.env.get("SMB_PASSWORD")
        self.pkg_uploaded = False
        self.pkg_metadata_updated = False

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
            self.pkg_path = self.zip_pkg_path(self.pkg_path)
            if ".zip" not in self.pkg_name:
                self.pkg_name += ".zip"

        # calculate the SHA-512 hash of the package
        self.sha512string = self.sha512sum(self.pkg_path)

        # now start the process of uploading the package
        self.output(
            f"Checking for existing package '{self.pkg_name}' on {self.jamf_url}"
        )

        # obtain the relevant credentials
        token, send_creds, enc_creds = self.handle_classic_auth(
            self.jamf_url, self.jamf_user, self.jamf_password
        )

        # check for existing
        obj_id = self.check_pkg(
            self.pkg_name, self.jamf_url, enc_creds=send_creds, token=token
        )
        self.output(f"ID: {obj_id}", verbose_level=3)  # TEMP
        if obj_id != "-1":
            self.output(
                "Package '{}' already exists: ID {}".format(self.pkg_name, obj_id)
            )
            pkg_id = obj_id  # assign pkg_id for smb runs - JCDS runs get it from the pkg upload
        else:
            self.output("Package '{}' not found on server".format(self.pkg_name))
            if self.jcds_mode:
                pkg_id = -1
            else:
                pkg_id = 0

        # process for SMB shares if defined
        if self.smb_url:
            # mount the share
            self.mount_smb(self.smb_url, self.smb_user, self.smb_password)
            # check for existing package
            local_pkg = self.check_local_pkg(self.smb_url, self.pkg_name)
            if not local_pkg or self.replace:
                if self.replace:
                    self.output(
                        "Replacing existing package as 'replace_pkg' is set to {}".format(
                            self.replace
                        ),
                        verbose_level=1,
                    )
                # copy the file
                self.copy_pkg(self.smb_url, self.pkg_path, self.pkg_name)
                # unmount the share
                self.umount_smb(self.smb_url)
                self.pkg_uploaded = True
            else:
                self.output(
                    f"Not replacing existing {self.pkg_name} as 'replace_pkg' is set to "
                    f"{self.replace}. Use replace_pkg='True' to enforce."
                )
                # unmount the share
                self.umount_smb(self.smb_url)
                if not self.replace_metadata:
                    # even if we don't upload a package, we still need to pass it on so that a
                    # policy processor can use it
                    self.env["pkg_name"] = self.pkg_name
                    self.pkg_uploaded = False

        # otherwise process for cloud DP
        else:
            if obj_id == "-1" or self.replace:
                if self.replace:
                    self.output(
                        "Replacing existing package as 'replace_pkg' is set to {}".format(
                            self.replace
                        ),
                        verbose_level=1,
                    )
                if self.jcds_mode:
                    # use direct upload method if jcds_mode is True
                    self.output(
                        "Uploading package using experimental JCDS mode",
                        verbose_level=1,
                    )
                    if self.pkg_category:
                        # 1. get the ID of a category
                        pkg_category_id = self.get_pkg_category_id(
                            self.jamf_url,
                            self.pkg_category,
                            enc_creds=enc_creds,
                            token=token,
                        )
                    else:
                        pkg_category_id = -1
                    # 2. start the session
                    self.create_session(
                        self.jamf_url, self.jamf_user, self.jamf_password
                    )
                    # 3. get the required tokens and URL
                    (
                        session_token,
                        x_auth_token,
                        pkg_upload_url,
                    ) = self.get_session_token(self.jamf_url, pkg_id)
                    # 4. upload the package
                    self.post_pkg(
                        self.jamf_url,
                        self.pkg_name,
                        self.pkg_path,
                        x_auth_token,
                        pkg_upload_url,
                    )
                    # 5. record the package in Jamf Pro
                    self.create_pkg_object(
                        self.jamf_url,
                        self.pkg_name,
                        pkg_id,
                        session_token,
                        pkg_category_id,
                    )
                    self.pkg_uploaded = True  # TODO - needs to be validated
                    self.pkg_metadata_updated = True  # TODO - needs to be validated
                else:
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
            and not self.jcds_mode
        ):
            self.output(
                "Updating package metadata for {}".format(pkg_id),
                verbose_level=1,
            )
            self.update_pkg_metadata(
                self.jamf_url,
                self.pkg_name,
                self.pkg_metadata,
                self.sha512string,
                pkg_id=pkg_id,
                enc_creds=send_creds,
                token=token,
            )
            self.pkg_metadata_updated = True
        elif self.smb_url and not pkg_id:
            self.output(
                "Creating package metadata",
                verbose_level=1,
            )
            self.update_pkg_metadata(
                self.jamf_url,
                self.pkg_name,
                self.pkg_metadata,
                self.sha512string,
                enc_creds=send_creds,
                token=token,
            )
            self.pkg_metadata_updated = True
        elif not self.jcds_mode:
            self.output(
                "Not updating package metadata",
                verbose_level=1,
            )
            self.pkg_metadata_updated = False

        # output the summary
        self.env["pkg_name"] = self.pkg_name
        self.env["pkg_uploaded"] = self.pkg_uploaded
        self.env["pkg_metadata_updated"] = self.pkg_metadata_updated
        if self.pkg_metadata_updated or self.pkg_uploaded:
            self.env["jamfpackageuploader_summary_result"] = {
                "summary_text": "The following packages were uploaded to or updated in Jamf Pro:",
                "report_fields": ["pkg_path", "pkg_name", "version", "category"],
                "data": {
                    "pkg_path": self.pkg_path,
                    "pkg_name": self.pkg_name,
                    "version": self.version,
                    "category": self.pkg_category,
                },
            }


if __name__ == "__main__":
    PROCESSOR = JamfPackageUploader()
    PROCESSOR.execute_shell()
