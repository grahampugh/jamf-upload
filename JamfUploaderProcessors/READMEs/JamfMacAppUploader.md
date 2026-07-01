# JamfMacAppUploader

## Description

A processor for AutoPkg that will update or clone a Mac App Store app object on a Jamf Pro server. A new one cannot be created.

## Input variables

- **JSS_URL:**
  - **required:** True
  - **description:** URL to a Jamf Pro server that the API user has write access to, optionally set as a key in the com.github.autopkg preference file.
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
- **macapp_name:**
  - **required:** False
  - **description:** Mac App Store app name
  - **default:** ""
- **clone_from:**
  - **required:** False
  - **description:** Mac App Store app name from which to clone this entry
  - **default:** ""
- **selfservice_icon_uri:**
  - **required:** False
  - **description:** Mac App Store app icon URI
  - **default:** ""
- **macapp_template:**
  - **required:** False
  - **description:** Full path to the XML template
- **preferred_volume_purchase_location:**
  - **required:** False
  - **description:** Text to match within the Volume Purchasing Location name when prioritizing app content.
  - **default:** ""
- **replace_macapp:**
  - **required:** False
  - **description:** Overwrite an existing Mac App Store app if True.
  - **default:** False
- **sleep:**
  - **required:** False
  - **description:** Pause after running this processor for specified seconds.
  - **default:** "0"
- **max_tries:**
  - **required:** False
  - **description:** Maximum number of attempts to upload the account. Must be an integer between 1 and 10.
  - **default:** "5"
- **dry_run:**
  - **required:** False
  - **description:** If True, perform read-only checks and report what would change without making any writes.
  - **default:** False
- **skip_if:**
  - **required:** False
  - **description:** Skip the process if a supplied predicate is met.

## Output variables

- **jamfmacappuploader_summary_result:**
  - **description:** Description of interesting results.
- **macapp_name:**
  - **description:** Jamf object name of the newly created or modified macapp.
- **macapp_updated:**
  - **description:** Boolean - True if the macapp was changed.
- **changed_macapp_id:**
  - **description:** Jamf object ID of the newly created or modified macapp.
- **process_skipped:**
  - **description:** Boolean - True if the process was skipped due to skip_if predicate resolved to True.
- **dry_run_summary_result:**
  - **description:** Summary of what would have been changed (only set when dry_run is True).
