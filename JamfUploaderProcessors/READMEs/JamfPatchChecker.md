# JamfPatchChecker

## Description

A processor for AutoPkg that will check and report whether a Patch Software Title has the version that AutoPkg has found or not. This can be used with a subsequent `StopProcessingIf` processor to prevent updating a Patch Policy with a version that does not yet exist in the Patch Software Title, allowing the recipe to run again on a subsequent recipe run.

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
- **patch_softwaretitle**:
  - **required**: True
  - **description**: Name of the patch softwaretitle (e.g. 'Mozilla Firefox') used in Jamf. You need to create the patch softwaretitle by hand, since there is currently no way to create these via the API.
- **pkg_name**:
  - **required**: False
  - **description**: Name of package which should be used in the patch. Mostly provided by previous AutoPKG recipe/processor.
- **version**:
  - **required**: False
  - **description**: Version string - provided by previous pkg recipe/processor.
- **sleep:**
  - **required:** False
  - **description:** Pause after running this processor for specified seconds.
  - **default:** "0"
- **max_tries:**
  - **required:** False
  - **description:** Maximum number of attempts to upload the account. Must be an integer between 1 and 10.
  - **default:** "5"
- **skip_if:**
  - **required:** False
  - **description:** Skip the process if a supplied predicate is met.

## Output variables

- **patch_version_found:**
  - **description:** Returns True if the specified version is found in the patch software title, False otherwise.
- **jamfpatchchecker_summary_result:**
  - **description:** Description of interesting results.
- **process_skipped:**
  - **description:** Boolean - True if the process was skipped due to skip_if predicate resolved to True.
