# JamfAPIClientUploader

## Description

A processor for AutoPkg that will create or amend an API Client to a Jamf Pro server. Only one API Role can be given to each API Client using this processor.

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
- **api_client_name:**
  - **required:** True
  - **description:** API Client name.
- **api_client_id:**
  - **required:** False
  - **description:** API Client ID.
- **api_role_name:**
  - **required:** False
  - **description:** API Role name that will be assigned to this API Client. Only one API Role can be given to each API Client using this processor.
- **access_token_lifetime:**
  - **required:** False
  - **description:** Access Token lifetime in seconds.
  - **default:** "300"
- **api_client_enabled:**
  - **required:** False
  - **description:** Set the API Client to enabled if True
  - **default:** False
- **replace_api_client:**
  - **required:** False
  - **description:** Overwrite an existing API Role if True.
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

- **jamfapiclientuploader_summary_result:**
  - **description:** Description of interesting results.
- **api_client_name:**
  - **description:** API Client name.
- **api_client_id:**
  - **description:** API Client ID.
- **api_client_secret:**
  - **description:** API Client Secret.
- **process_skipped:**
  - **description:** Boolean - True if the process was skipped due to skip_if predicate resolved to True.
- **dry_run_summary_result:**
  - **description:** Summary of what would have been changed (only set when dry_run is True).
