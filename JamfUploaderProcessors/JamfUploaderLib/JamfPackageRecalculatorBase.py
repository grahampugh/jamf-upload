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

    def recalculate_packages(self, api_url, token, tenant_id=""):
        """Send a request to recalulate the JCDS packages"""
        # get the JCDS file list
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

    # main function
    def execute(
        self,
    ):  # pylint: disable=too-many-branches, too-many-locals, too-many-statements
        """Perform the package recalculation"""

        jcds2_mode = self.to_bool(self.env.get("jcds2_mode"))
        pkg_api_mode = self.to_bool(self.env.get("pkg_api_mode"))
        jamf_url = (self.env.get("JSS_URL") or "").rstrip("/")
        jamf_user = self.env.get("API_USERNAME")
        jamf_password = self.env.get("API_PASSWORD")
        jamf_platform_gw_region = self.env.get("PLATFORM_API_REGION")
        jamf_platform_gw_tenant_id = self.env.get("PLATFORM_API_TENANT_ID")
        client_id = self.env.get("CLIENT_ID")
        client_secret = self.env.get("CLIENT_SECRET")
        bearer_token = self.env.get("BEARER_TOKEN")
        jamf_cli_profile = self.env.get("JAMF_CLI_PROFILE")
        skip_and_proceed = self.to_bool(self.env.get("skip_and_proceed"))

        process_skipped = False

        # skip the process if skip_and_proceed is True
        if skip_and_proceed:
            self.output(
                "Skipping package recalculator to next process as "
                "skip_and_proceed is set to True"
            )
            process_skipped = True
            self.env["process_skipped"] = process_skipped
            return

        # get a token
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

        # construct the api_url based on the API type
        api_url = self.construct_api_url(
            jamf_url=jamf_url, region=jamf_platform_gw_region
        )
        self.output(f"API URL is {api_url}", verbose_level=3)

        jamf_pro_version = self.get_jamf_pro_version(api_url, token, tenant_id=jamf_platform_gw_tenant_id)
        if APLooseVersion(jamf_pro_version) >= APLooseVersion("11.5"):
            # set default mode to pkg_api_mode if using Jamf Cloud / AWS
            if not self.env.get("SMB_URL") and not self.env.get("SMB_SHARES"):
                pkg_api_mode = True

        # clear any pre-existing summary result
        if "jamfpackagerecalculator_summary_result" in self.env:
            del self.env["jamfpackagerecalculator_summary_result"]

        # recalculate packages on Cloud Distribution Point if the metadata was updated and recalculation requested
        # (only works on Jamf Pro 11.10 or newer)
        if (pkg_api_mode or jcds2_mode) and APLooseVersion(
            jamf_pro_version
        ) >= APLooseVersion("11.10"):
            # check token using oauth or basic auth depending on the credentials given
            # as package upload may have taken some time
            # get a token
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

            # now send the recalculation request
            packages_recalculated = self.recalculate_packages(api_url, token, tenant_id=jamf_platform_gw_tenant_id)
        else:
            packages_recalculated = False

        # output the summary
        self.output(
            f"Cloud Distribution Point inventory recalculated? : {packages_recalculated}"
        )
        self.env["jamfpackagerecalculator_summary_result"] = {
            "summary_text": "Cloud Distribution Point inventory recalculation result.",
            "report_fields": ["packages_recalculated"],
            "data": {
                "packages_recalculated": str(packages_recalculated),
            },
        }
        self.env["process_skipped"] = process_skipped
