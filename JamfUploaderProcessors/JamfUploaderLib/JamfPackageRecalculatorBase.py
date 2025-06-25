#!/usr/local/autopkg/python
# pylint: disable=invalid-name

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
"""

import os.path
import sys

from autopkglib import ProcessorError, APLooseVersion  # pylint: disable=import-error

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderBase import (  # pylint: disable=import-error, wrong-import-position
    JamfUploaderBase,
)


class JamfPackageRecalculatorBase(JamfUploaderBase):
    """Class for functions used to upload a package to Jamf"""

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

    # main function
    def execute(
        self,
    ):  # pylint: disable=too-many-branches, too-many-locals, too-many-statements
        """Perform the package recalculation"""

        jcds2_mode = self.to_bool(self.env.get("jcds2_mode"))
        pkg_api_mode = self.to_bool(self.env.get("pkg_api_mode"))
        jamf_url = self.env.get("JSS_URL").rstrip("/")
        jamf_user = self.env.get("API_USERNAME")
        jamf_password = self.env.get("API_PASSWORD")
        client_id = self.env.get("CLIENT_ID")
        client_secret = self.env.get("CLIENT_SECRET")

        # get token using oauth or basic auth depending on the credentials given
        if jamf_url:
            token = self.handle_api_auth(
                jamf_url,
                jamf_user=jamf_user,
                password=jamf_password,
                client_id=client_id,
                client_secret=client_secret,
            )
        else:
            raise ProcessorError("ERROR: Jamf Pro URL not supplied")

        jamf_pro_version = self.get_jamf_pro_version(jamf_url, token)
        if APLooseVersion(jamf_pro_version) >= APLooseVersion("11.5"):
            # set default mode to pkg_api_mode if using Jamf Cloud / AWS
            if not self.env.get("SMB_URL") and not self.env.get("SMB_SHARES"):
                pkg_api_mode = True

        # clear any pre-existing summary result
        if "jamfpackagerecalculator_summary_result" in self.env:
            del self.env["jamfpackagerecalculator_summary_result"]

        # recalculate packages on JCDS if the metadata was updated and recalculation requested
        # (only works on Jamf Pro 11.10 or newer)
        if (pkg_api_mode or jcds2_mode) and APLooseVersion(
            jamf_pro_version
        ) >= APLooseVersion("11.10"):
            # check token using oauth or basic auth depending on the credentials given
            # as package upload may have taken some time
            # get token using oauth or basic auth depending on the credentials given
            if jamf_url:
                token = self.handle_api_auth(
                    jamf_url,
                    jamf_user=jamf_user,
                    password=jamf_password,
                    client_id=client_id,
                    client_secret=client_secret,
                )
            else:
                raise ProcessorError("ERROR: Jamf Pro URL not supplied")

            # now send the recalculation request
            packages_recalculated = self.recalculate_packages(jamf_url, token)
        else:
            packages_recalculated = False

        # output the summary
        self.output(f"JCDS Package recalculated? : {packages_recalculated}")
        self.env["jamfpackagerecalculator_summary_result"] = {
            "summary_text": "JCDS package recalculation resuilt.",
            "report_fields": ["packages_recalculated"],
            "data": {
                "packages_recalculated": str(packages_recalculated),
            },
        }
