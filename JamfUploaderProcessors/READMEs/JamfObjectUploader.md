# JamfObjectUploader

## Description

A processor for AutoPkg that will upload various Classic API or Jamf Pro API objects to a Jamf Cloud or on-prem server. To be used when no specific processor is available for the required object type. Note that many objects may not work due to exceptions to the API object from "standard" - test first!

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
- **object_name**:
  - **required**: False
  - **description**: The name of the API object
- **object_id**:
  - **required**: False
  - **description**: ID of an object. May be used instead of supplying an object name.
- **object_template**:
  - **required**: False
  - **description**: Path to the API object template file. For Classic API endpoints this must be XML, for Jamf Pro API endpoints this must be JSON.
- **object_type**:
  - **required**: True
  - **description**: The API object type. This is in the singular form - for Classic API endpoints this is the name of the key in the XML template. For JSON objects it is a construction made interally for this project. See the [Object Reference](./Object%20Reference.md) for valid objects.
- **elements_to_remove**:
  - **required**: False
  - **description**: A list of XML or JSON elements that should be removed from the downloaded XML. Note that `id` and `self_service_icon` are removed automatically.
- **element_to_replace**:
  - **required**: False
  - **description**: Full path of an element to replace the value of, such as general/id.
- **replacement_value**:
  - **required**: False
  - **description**: The value of the element provided by the element_to_replace key.
- **replace_object**:
  - **required**: False
  - **description**: overwrite an existing Computer Group if True.
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

- **jamfobjectuploader_summary_result:**
  - **description:** Description of interesting results.
- **object_name**:
  - **description**: The name of the API object
- **object_updated**:
  - **description**: Boolean - True if the object was changed.
- **failover_url:**
  - **description:** Failover URL, if uploading failover_generate_command object.
- **process_skipped:**
  - **description:** Boolean - True if the process was skipped due to skip_if predicate resolved to True.
- **dry_run_summary_result:**
  - **description:** Summary of what would have been changed (only set when dry_run is True).
