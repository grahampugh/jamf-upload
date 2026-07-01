# JamfPkgMetadataUploader

## Description

A processor for AutoPkg that will upload package metadata to Jamf Pro.

## Input variables

- **JSS_URL:**
  - **required:** True
  - **description:** URL to a Jamf Pro server to which the API user has write access.
- **API_USERNAME:**
  - **required:** False
  - **description:** Username of account with appropriate access to jss, optionally set as a key in the com.github.autopkg preference file.
- **API_PASSWORD:**
  - **required:** False
  - **description:** Password of api user, optionally set as a key in the com.github.autopkg preference file.
- **CLIENT_ID:**
  - **required:** False
  - **description:** Client ID with access to access to jss, optionally set as a key in the com.github.autopkg preference file.
- **CLIENT_SECRET:**
  - **required:** False
  - **description:** Secret associated with the Client ID, optionally set as a key in the com.github.autopkg preference file.
- **BEARER_TOKEN:**
  - **required:** False
  - **description:** A pre-existing bearer token for the Jamf Pro API. If provided, the token will be validated and used directly, bypassing credential-based authentication.
- **JAMF_CLI_PROFILE:**
  - **required:** False
  - **description:** A jamf-cli profile to use to obtain a bearer token. Requires jamf-cli to be installed and in the PATH. Set to a profile name to enable.
  - **default:** ""
- **PLATFORM_API_REGION:**
  - **required:** False
  - **description:** Region for Jamf Platform API Gateway (e.g., 'us1', 'eu1', 'au1'). Required for Platform API authentication.
  - **default:** ""
- **PLATFORM_API_TENANT_ID:**
  - **required:** False
  - **description:** Tenant ID for Jamf Platform API Gateway. Required for Platform API authentication.
  - **default:** ""
- **CLOUD_DP:**
  - **required:** False
  - **description:** Indicates the presence of a Cloud Distribution Point. The default is deliberately blank. If no SMB DP is configured, the default setting assumes that the Cloud DP has been enabled. If at least one SMB DP is configured, the default setting assumes that no Cloud DP has been set. This can be overridden by setting `CLOUD_DP` to `True`, in which case packages will be uploaded to both a Cloud DP plus the SMB DP(s).
- **pkg_name:**
  - **required:** False
  - **description:** Package name. If supplied, will rename the package supplied in the pkg_path key when uploading it to the fileshare.
  - **default:** ""
- **pkg_display_name:**
  - **required:** False
  - **description:** Package display name, which may be different to the `pkg_name`. If not supplied, reverts to `pkg_name`.
  - **default:** ""
- **pkg_category:**
  - **required:** False
  - **description:** Package category.
  - **default:** ""
- **pkg_info:**
  - **required:** False
  - **description:** Package info field.
  - **default:** ""
- **pkg_notes:**
  - **required:** False
  - **description:** Package notes field.
  - **default:** ""
- **pkg_priority:**
  - **required:** False
  - **description:** Package priority.
  - **default:** "10"
- **reboot_required:**
  - **required:** False
  - **description:** Whether a package requires a reboot after installation.
  - **default:** ""
- **os_requirements:**
  - **required:** False
  - **description:** Package OS requirement.
  - **default:** ""
- **required_processor:**
  - **required:** False
  - **description:** Package required processor. Acceptable values are 'x86' or 'None'.
  - **default:** "None"
- **send_notification:**
  - **required:** False
  - **description:** Whether to send a notification when a package is installed.
  - **default:** ""
- **sleep:**
  - **required:** False
  - **description:** Pause after running this processor for specified seconds.
  - **default:** "0"
- **max_tries:**
  - **required:** False
  - **description:** Maximum number of attempts for uploading package metadata. Must be an integer between 1 and 10.
  - **default:** "5"
- **dry_run:**
  - **required:** False
  - **description:** If True, perform read-only checks and report what would change without making any writes.
  - **default:** False
- **skip_if:**
  - **required:** False
  - **description:** Skip the process if a supplied predicate is met.

## Output variables

- **pkg_name:**
  - **description:** The name of the uploaded package.
- **jamfpkgmetadatauploader_summary_result:**
  - **description:** Description of interesting results.
- **process_skipped:**
  - **description:** Boolean - True if the process was skipped due to skip_if predicate resolved to True.
- **dry_run_summary_result:**
  - **description:** Summary of what would have been changed (only set when dry_run is True).
