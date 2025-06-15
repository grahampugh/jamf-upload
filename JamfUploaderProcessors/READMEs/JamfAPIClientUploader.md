# JamfAPIRoleUploader

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
- **api_client_name:**
  - **required:** True
  - **description:** API Client name.
- **api_client_id:**
  - **required:** False
  - **description:** API Client ID.
- **api_role_name:**
  - **required:** True
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

## Output variables

- **jamfapiclientuploader_summary_result:**
  - **description:** Description of interesting results.
- **api_client_name:**
  - **description:** API Client name.
- **api_client_id:**
  - **description:** API Client ID.
- **api_client_secret:**
  - **description:** API Client Secret.
- **api_client_updated:**
  - **description:** Boolean - True if the API Client was changed.
