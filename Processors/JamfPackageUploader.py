#!/usr/local/autopkg/python

"""
JamfPackageUploader processor for AutoPkg
    by G Pugh

Developed from an idea posted at
    https://www.jamf.com/jamf-nation/discussions/27869#responseChild166021
"""


import sys
import os
import json
import base64
from time import sleep
from zipfile import ZipFile, ZIP_DEFLATED
import requests
import plistlib
import subprocess
import xml.etree.ElementTree as ElementTree
from shutil import copyfile
from urllib.parse import urlparse
from autopkglib import Processor, ProcessorError  # pylint: disable=import-error


class JamfPackageUploader(Processor):
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
        "category": {
            "required": False,
            "description": "Package category",
            "default": "",
        },
        "replace_pkg": {
            "required": False,
            "description": "Overwrite an existing package if True.",
            "default": "False",
        },
        "curl": {
            "required": False,
            "description": "Use curl instead of requests to upload package if True.",
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
        "pkg_name": {"description": "The name of the uploaded package.",},
        "pkg_uploaded": {
            "description": "True/False depending if a package was uploaded or not.",
        },
        "jamfpackageuploader_summary_result": {
            "description": "Description of interesting results.",
        },
    }

    description = __doc__

    def mount_smb(self, mount_share, mount_user, mount_pass):
        """Mount distribution point."""
        mount_cmd = [
            "/usr/bin/osascript",
            "-e",
            f'mount volume "{mount_share}" as user name "{mount_user}" with password "{mount_pass}"',
        ]
        self.output(
            mount_cmd, verbose_level=2,
        )

        r = subprocess.check_output(mount_cmd)
        self.output(
            r, verbose_level=2,
        )

    def umount_smb(self, mount_share):
        """Unmount distribution point."""
        path = f"/Volumes{urlparse(mount_share).path}"
        cmd = ["/usr/sbin/diskutil", "unmount", path]
        try:
            subprocess.check_call(cmd)
        except subprocess.CalledProcessError:
            self.output("WARNING! Unmount failed.")

    def check_local_pkg(self, mount_share, pkg_name):
        """Check local DP or mounted share for existing package"""
        path = f"/Volumes{urlparse(mount_share).path}"
        if os.path.isdir(path):
            existing_pkg_path = os.path.join(path, "Packages", pkg_name)
            if os.path.isfile(existing_pkg_path):
                self.output(f"Existing package found: {existing_pkg_path}")
                return existing_pkg_path
            else:
                self.output("No existing package found")
                self.output(
                    f"Expected path: {existing_pkg_path}", verbose_level=2,
                )
        else:
            self.output(
                f"Expected path not found!: {path}", verbose_level=2,
            )

    def copy_pkg(self, mount_share, pkg_path, pkg_name):
        """Copy package from AutoPkg Cache to local or mounted Distribution Point"""
        if os.path.isfile(pkg_path):
            path = f"/Volumes{urlparse(mount_share).path}"
            destination_pkg_path = os.path.join(path, "Packages", pkg_name)
            self.output(f"Copying {pkg_name} to {destination_pkg_path}")
            copyfile(pkg_path, destination_pkg_path)
        if os.path.isfile(destination_pkg_path):
            self.output("Package copy successful")
        else:
            self.output("Package copy failed")

    def zip_pkg_path(self, path):
        """Add files from path to a zip file handle.

        Args:
            path (str): Path to folder to zip.

        Returns:
            (str) name of resulting zip file.
        """
        zip_name = f"{path}.zip"

        if os.path.exists(zip_name):
            self.output("Package object is a bundle. Zipped version already exists.")
            return zip_name

        self.output("Package object is a bundle. Converting to zip...")
        with ZipFile(zip_name, "w", ZIP_DEFLATED, allowZip64=True) as zip_handle:
            for root, _, files in os.walk(path):
                for member in files:
                    zip_handle.write(os.path.join(root, member))
            self.output(
                f"Closing: {zip_name}", verbose_level=2,
            )
        return zip_name

    def check_pkg(self, pkg_name, jamf_url, enc_creds):
        """check if a package with the same name exists in the repo
        note that it is possible to have more than one with the same name
        which could mess things up"""
        headers = {
            "authorization": f"Basic {enc_creds}",
            "accept": "application/json",
        }
        url = f"{jamf_url}/JSSResource/packages/name/{pkg_name}"
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            obj = json.loads(r.text)
            try:
                obj_id = str(obj["package"]["id"])
            except KeyError:
                obj_id = "-1"
        else:
            obj_id = "-1"
        return obj_id

    def post_pkg(self, pkg_name, pkg_path, jamf_url, enc_creds, obj_id):
        """sends the package"""
        files = {"file": open(pkg_path, "rb")}
        headers = {
            "authorization": f"Basic {enc_creds}",
            "content-type": "application/xml",
            "DESTINATION": "0",
            "OBJECT_ID": obj_id,
            "FILE_TYPE": "0",
            "FILE_NAME": pkg_name,
        }
        url = f"{jamf_url}/dbfileupload"

        http = requests.Session()
        r = http.post(url, data=files, headers=headers, timeout=3600)
        return r

    def curl_pkg(self, pkg_name, pkg_path, jamf_url, enc_creds, obj_id):
        """sends the package via curl instead of requests"""
        url = f"{jamf_url}/dbfileupload"
        curl_cmd = [
            "/usr/bin/curl",
            "-X",
            "POST",
            "--header",
            "authorization: Basic {}".format(enc_creds),
            "--header",
            "DESTINATION: 0",
            "--header",
            "OBJECT_ID: {}".format(obj_id),
            "--header",
            "FILE_TYPE: 0",
            "--header",
            "FILE_NAME: {}".format(pkg_name),
            "--upload-file",
            pkg_path,
            "--connect-timeout",
            str("60"),
            "--max-time",
            str("3600"),
            url,
        ]
        self.output(curl_cmd, verbose_level=2)

        r = subprocess.check_output(curl_cmd)
        return r

    def update_pkg_metadata(self, jamf_url, enc_creds, pkg_name, category, pkg_id=None):
        """Update package metadata. Currently only serves category"""

        # build the package record XML
        pkg_data = (
            "<package>"
            + f"<name>{pkg_name}</name>"
            + f"<filename>{pkg_name}</filename>"
            + f"<category>{category}</category>"
            + "</package>"
        )
        headers = {
            "authorization": f"Basic {enc_creds}",
            "Accept": "application/xml",
            "Content-type": "application/xml",
        }
        #  ideally we upload to the package ID but if we didn't get a good response
        #  we fall back to the package name
        if pkg_id:
            url = f"{jamf_url}/JSSResource/packages/id/{pkg_id}"
        else:
            url = f"{jamf_url}/JSSResource/packages/name/{pkg_name}"

        http = requests.Session()

        self.output("Updating package metadata...")
        self.output(
            pkg_data, verbose_level=2,
        )

        count = 0
        while True:
            count += 1
            self.output(
                f"Package update attempt {count}", verbose_level=2,
            )

            r = http.put(url, headers=headers, data=pkg_data, timeout=60)
            if r.status_code == 201:
                self.output("Package metadata update successful")
                break
            if r.status_code == 409:
                raise ProcessorError(
                    "WARNING: Package metadata update failed due to a conflict"
                )
            if count > 5:
                self.output(
                    "WARNING: Package metadata update did not succeed after 5 attempts"
                )
                self.output(
                    f"HTTP POST Response Code: {r.status_code}", verbose_level=2,
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
        self.category = self.env.get("category")
        self.replace = self.env.get("replace_pkg")
        # handle setting replace in overrides
        if not self.replace or self.replace == "False":
            self.replace = False
        self.curl = self.env.get("curl")
        # handle setting replace in overrides
        if not self.curl or self.curl == "False":
            self.curl = False
        self.jamf_url = self.env.get("JSS_URL")
        self.jamf_user = self.env.get("API_USERNAME")
        self.jamf_password = self.env.get("API_PASSWORD")
        self.smb_url = self.env.get("SMB_URL")
        self.smb_user = self.env.get("SMB_USERNAME")
        self.smb_password = self.env.get("SMB_PASSWORD")
        # clear any pre-existing summary result
        if "jamfpackageuploader_summary_result" in self.env:
            del self.env["jamfpackageuploader_summary_result"]

        # encode the username and password into a basic auth b64 encoded string
        credentials = f"{self.jamf_user}:{self.jamf_password}"
        enc_creds_bytes = base64.b64encode(credentials.encode("utf-8"))
        enc_creds = str(enc_creds_bytes, "utf-8")

        # See if the package is non-flat (requires zipping prior to upload).
        if os.path.isdir(self.pkg_path):
            self.pkg_path = self.zip_pkg_path(self.pkg_path)
            self.pkg_name += ".zip"

        # now start the process of uploading the package
        self.output(f"Checking for existing '{self.pkg_name}' on {self.jamf_url}")

        # check for existing
        obj_id = self.check_pkg(self.pkg_name, self.jamf_url, enc_creds)
        if obj_id != "-1":
            self.output(
                "Package '{}' already exists: ID {}".format(self.pkg_name, obj_id)
            )

        #  process for SMB shares if defined
        if self.smb_url:
            # mount the share
            self.mount_smb(self.smb_url, self.smb_user, self.smb_password)
            # check for existing package
            local_pkg = self.check_local_pkg(self.smb_url, self.pkg_name)
            if not local_pkg or self.replace:
                # copy the file
                self.copy_pkg(self.smb_url, self.pkg_path, self.pkg_name)
                # unmount the share
                self.umount_smb(self.smb_url)
            else:
                self.output(
                    f"Not updating existing '{self.pkg_name}' on {self.jamf_url}"
                )
                # unmount the share
                self.umount_smb(self.smb_url)
                # even if we don't upload a package, we still need to pass it on so that a policy processor can use it
                self.env["pkg_name"] = self.pkg_name
                self.env["pkg_uploaded"] = False
                return

        #  otherwise process for cloud DP
        else:
            if obj_id == "-1" or self.replace:
                if self.replace:
                    self.output(
                        "Replacing existing package as 'replace_pkg' is set to {}".format(
                            self.replace
                        ),
                        verbose_level=1,
                    )
                # post the package (won't run if the pkg exists and replace is False)
                if self.curl:
                    r = self.curl_pkg(
                        self.pkg_name, self.pkg_path, self.jamf_url, enc_creds, obj_id,
                    )
                    try:
                        pkg_id = ElementTree.fromstring(r).findtext("id")
                        if pkg_id:
                            self.output(
                                "Package uploaded successfully, ID={}".format(pkg_id)
                            )
                    except ElementTree.ParseError:
                        self.output("Could not parse XML. Raw output:", verbose_level=2)
                        self.output(r.decode("ascii"), verbose_level=2)
                    else:
                        if r:
                            self.output("\nResponse:\n", verbose_level=2)
                            self.output(r.decode("ascii"), verbose_level=2)
                        else:
                            self.output("No HTTP response", verbose_level=2)
                else:
                    r = self.post_pkg(
                        self.pkg_name, self.pkg_path, self.jamf_url, enc_creds, obj_id
                    )
                    # print result of the request
                    if r.status_code == 200 or r.status_code == 201:
                        pkg_id = ElementTree.fromstring(r.text).findtext("id")
                        self.output(f"Package uploaded successfully, ID={pkg_id}")
                        #  now process the package metadata if specified
                    else:
                        self.output(
                            f"HTTP POST Response Code: {r.status_code}",
                            verbose_level=2,
                        )
                        self.output(
                            "Headers:", verbose_level=2,
                        )
                        self.output(
                            r.headers, verbose_level=2,
                        )
                        self.output(
                            "Response:", verbose_level=2,
                        )
                        if r.text:
                            self.output(
                                r.text, verbose_level=2,
                            )
                        else:
                            self.output(
                                "None", verbose_level=2,
                            )
                        raise ProcessorError(
                            "An error occurred while attempting to upload the package"
                        )
            else:
                self.output(
                    "Not replacing existing package as 'replace_pkg' is set to {}. Use replace_pkg='True' to enforce.".format(
                        self.replace
                    ),
                    verbose_level=1,
                )
                # even if we don't upload a package, we still need to pass it on so that a policy processor can use it
                self.env["pkg_name"] = self.pkg_name
                self.env["pkg_uploaded"] = False
                return

        #  now process the package metadata if specified
        if self.category or self.smb_url:
            try:
                pkg_id
                self.update_pkg_metadata(
                    self.jamf_url, enc_creds, self.pkg_name, self.category, pkg_id
                )
            except UnboundLocalError:
                self.update_pkg_metadata(
                    self.jamf_url, enc_creds, self.pkg_name, self.category
                )

        # output the summary
        self.env["pkg_name"] = self.pkg_name
        self.env["pkg_uploaded"] = True
        self.env["jamfpackageuploader_summary_result"] = {
            "summary_text": "The following packages were uploaded to Jamf Pro:",
            "report_fields": ["pkg_path", "pkg_name", "version", "category"],
            "data": {
                "pkg_path": self.pkg_path,
                "pkg_name": self.pkg_name,
                "version": self.version,
                "category": self.category,
            },
        }


if __name__ == "__main__":
    PROCESSOR = JamfPackageUploader()
    PROCESSOR.execute_shell()
