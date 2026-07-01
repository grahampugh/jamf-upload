# JamfPatchUploader

## Description

A processor for AutoPkg that will upload a Patch Policy to a Jamf Cloud or on-prem server.

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
- **pkg_name**:
  - **required**: False
  - **description**: Name of package which should be used in the patch. Mostly provided by previous AutoPKG recipe/processor.
  - **default**: ""
- **version**:
  - **required**: False
  - **description**: Version string - provided by previous pkg recipe/processor.
  - **default**: ""
- **patch_softwaretitle**:
  - **required**: True
  - **description**: Name of the patch softwaretitle (e.g. 'Mozilla Firefox') used in Jamf. You need to create the patch softwaretitle by hand, since there is currently no way to create these via the API.
- **patch_name**:
  - **required**: False
  - **description**: Name of the patch policy (e.g. 'Mozilla Firefox - 93.02.10').
  - **default**: '%patch_softwaretitle% - %version%'
- **patch_template**:
  - **required**: False
  - **description**: XML-Template used for the patch policy. If none is provided, only the installer will be linked to the corresponding version and no patch policy will be created.
- **patch_icon_policy_name**:
  - **required**: False
  - **description**: Name of an already existing (!) policy (not a patch policy). The icon of this policy will be extracted and can be used in the patch template with the variable `%patch_icon_id%`. There is currently no reasonable way to upload a custom icon for patch policies.
- **replace_patch**:
  - **required**: False
  - **description**: Overwrite an existing patch policy if True.
  - **default**: False
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

- **patch:**
  - **description:** The patch policy object.
- **jamfpatchuploader_summary_result:**
  - **description:** Description of interesting results.
- **process_skipped:**
  - **description:** Boolean - True if the process was skipped due to skip_if predicate resolved to True.
- **dry_run_summary_result:**
  - **description:** Summary of what would have been changed (only set when dry_run is True).
