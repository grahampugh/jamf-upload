#!/usr/local/autopkg/python

"""
JamfPackageUploader processor for AutoPkg
    by G Pugh

Developed from an idea posted at
    https://www.jamf.com/jamf-nation/discussions/27869#responseChild166021

Note that most of the functions have now been moved into JamfUploaderLib/JamfPackageUploaderBase.py
"""

import os
import sys
import xml.etree.ElementTree as ElementTree

# from zipfile import ZipFile, ZIP_DEFLATED
from autopkglib import ProcessorError  # pylint: disable=import-error

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfPackageUploaderBase import (  # noqa: E402
    JamfPackageUploaderBase,
)

__all__ = ["JamfPackageUploader"]


class JamfPackageUploader(JamfPackageUploaderBase):
    description = (
        "A processor for AutoPkg that will upload a package to a JCDS or File "
        "Share Distribution Point."
        "Can be run as a post-processor for a pkg recipe or in a child recipe. "
        "The pkg recipe must output pkg_path or this will fail."
    )
    input_variables = {
        "JSS_URL": {
            "required": True,
            "description": "URL to a Jamf Pro server to which the API user has write access.",
        },
        "API_USERNAME": {
            "required": False,
            "description": "Username of account with appropriate access to "
            "jss, optionally set as a key in the com.github.autopkg "
            "preference file.",
        },
        "API_PASSWORD": {
            "required": False,
            "description": "Password of api user, optionally set as a key in "
            "the com.github.autopkg preference file.",
        },
        "CLIENT_ID": {
            "required": False,
            "description": "Client ID with access to "
            "jss, optionally set as a key in the com.github.autopkg "
            "preference file.",
        },
        "CLIENT_SECRET": {
            "required": False,
            "description": "Secret associated with the Client ID, optionally set as a key in "
            "the com.github.autopkg preference file.",
        },
        "CLOUD_DP": {
            "required": False,
            "description": "Indicates the presence of a Cloud Distribution Point. "
            "The default is deliberately blank. If no SMB DP is configured, "
            "the default setting assumes that the Cloud DP has been enabled. "
            "If at least one SMB DP is configured, the default setting assumes "
            "that no Cloud DP has been set. "
            "This can be overridden by setting CLOUD_DP to True, in which case "
            "packages will be uploaded to both a Cloud DP plus the SMB DP(s).",
            "default": False,
        },
        "SMB_URL": {
            "required": False,
            "description": "URL to a Jamf Pro file share distribution point "
            "which should be in the form smb://server/share "
            "or a local DP in the form file://path. "
            "Subsequent DPs can be configured using SMB2_URL, SMB3_URL etc. "
            "Accompanying username and password must be supplied for each DP, e.g. "
            "SMB2_USERNAME, SMB2_PASSWORD etc.",
            "default": "",
        },
        "SMB_USERNAME": {
            "required": False,
            "description": "Username of account with appropriate access to "
            "a Jamf Pro fileshare distribution point.",
            "default": "",
        },
        "SMB_PASSWORD": {
            "required": False,
            "description": "Password of account with appropriate access to "
            "a Jamf Pro fileshare distribution point.",
            "default": "",
        },
        "SMB_SHARES": {
            "required": False,
            "description": "An array of dictionaries containing SMB_URL, SMB_USERNAME and "
            "SMB_PASSWORD, as an alternative to individual keys. Any individual keys will "
            "override this complete array. The array can only be provided via the AutoPkg "
            "preferences file.",
        },
        "pkg_name": {
            "required": False,
            "description": "Package name. If supplied, will rename the package supplied "
            "in the pkg_path key when uploading it to the fileshare.",
            "default": "",
        },
        "pkg_display_name": {
            "required": False,
            "description": "Package display name.",
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
        "jcds2_mode": {
            "required": False,
            "description": "Use jcds2 endpoint if True.",
            "default": "False",
        },
        "replace_pkg_metadata": {
            "required": False,
            "description": "Overwrite existing package metadata and continue if True, "
            "even if the package object is not re-uploaded.",
            "default": "False",
        },
        "skip_metadata_upload": {
            "required": False,
            "description": "Skip processing package metadata and continue if True. "
            "Designed for organisations where amending packages is not allowed.",
            "default": "False",
        },
        "sleep": {
            "required": False,
            "description": "Pause after running this processor for specified seconds.",
            "default": "0",
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
        self.pkg_display_name = self.env.get("pkg_display_name")
        if not self.pkg_display_name:
            self.pkg_display_name = self.pkg_name
        self.version = self.env.get("version")
        self.replace = self.env.get("replace_pkg")
        self.sleep = self.env.get("sleep")
        # handle setting replace in overrides
        if not self.replace or self.replace == "False":
            self.replace = False
        self.replace_metadata = self.env.get("replace_pkg_metadata")
        # handle setting replace_metadata in overrides
        if not self.replace_metadata or self.replace_metadata == "False":
            self.replace_metadata = False
        self.skip_metadata_upload = self.env.get("skip_metadata_upload")
        # handle setting skip_metadata_upload in overrides
        if not self.skip_metadata_upload or self.skip_metadata_upload == "False":
            self.skip_metadata_upload = False
        self.jcds_mode = self.env.get("jcds_mode")
        # handle setting jcds_mode in overrides
        if not self.jcds_mode or self.jcds_mode == "False":
            self.jcds_mode = False
        self.jcds2_mode = self.env.get("jcds2_mode")
        # handle setting jcds_mode in overrides
        if not self.jcds2_mode or self.jcds2_mode == "False":
            self.jcds2_mode = False
        self.jamf_url = self.env.get("JSS_URL")
        self.jamf_user = self.env.get("API_USERNAME")
        self.jamf_password = self.env.get("API_PASSWORD")
        self.client_id = self.env.get("CLIENT_ID")
        self.client_secret = self.env.get("CLIENT_SECRET")
        self.cloud_dp = self.env.get("CLOUD_DP")
        # handle setting jcds_mode in overrides
        if not self.cloud_dp or self.cloud_dp == "False":
            self.cloud_dp = False
        self.recipe_cache_dir = self.env.get("RECIPE_CACHE_DIR")
        self.pkg_uploaded = False
        self.pkg_metadata_updated = False

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

        # calculate the SHA-512 hash of the package
        self.sha512string = self.sha512sum(self.pkg_path)

        # now start the process of uploading the package
        self.output(
            f"Checking for existing package '{self.pkg_name}' on {self.jamf_url}"
        )

        # get token using oauth or basic auth depending on the credentials given
        if self.jamf_url and self.client_id and self.client_secret:
            token = self.handle_oauth(self.jamf_url, self.client_id, self.client_secret)
        elif self.jamf_url and self.jamf_user and self.jamf_password:
            token = self.handle_api_auth(
                self.jamf_url, self.jamf_user, self.jamf_password
            )
        else:
            raise ProcessorError("ERROR: Credentials not supplied")

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
            if self.jcds_mode:
                pkg_id = -1
            else:
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

                elif self.jcds_mode:
                    # use direct upload method if jcds_mode is True
                    self.output(
                        "Uploading package using experimental JCDS mode",
                        verbose_level=1,
                    )
                    # 1. get the ID of a category
                    if self.pkg_category:
                        pkg_category_id = self.get_pkg_category_id(
                            self.jamf_url,
                            self.pkg_category,
                            token=token,
                        )
                    else:
                        pkg_category_id = -1

                    # 2. get the failover URL
                    failover_url = self.get_failover_url(self.jamf_url, token)

                    # 3. start the session
                    self.create_session(
                        failover_url, self.jamf_user, self.jamf_password
                    )

                    # 4. get the required tokens and URL
                    (
                        session_token,
                        x_auth_token,
                        pkg_upload_url,
                    ) = self.get_session_token(self.jamf_url, pkg_id)
                    # 5. upload the package
                    self.post_pkg(
                        self.jamf_url,
                        self.pkg_name,
                        self.pkg_path,
                        x_auth_token,
                        pkg_upload_url,
                    )
                    # 6. record the package in Jamf Pro
                    self.create_pkg_object(
                        self.jamf_url,
                        self.pkg_name,
                        self.pkg_display_name,
                        pkg_id,
                        session_token,
                        pkg_category_id,
                    )
                    self.pkg_uploaded = True  # TODO - needs to be validated
                    self.pkg_metadata_updated = True  # TODO - needs to be validated
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
            and not self.jcds_mode
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
                token=token,
            )
            self.pkg_metadata_updated = True
        elif not self.jcds_mode and not self.skip_metadata_upload:
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


if __name__ == "__main__":
    PROCESSOR = JamfPackageUploader()
    PROCESSOR.execute_shell()
