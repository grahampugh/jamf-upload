# JamfAPIRoleUploader

## Description

A processor for AutoPkg that will create or amend an API Role to a Jamf Pro server, with privileges supplied by a template json file.

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
- **api_role_name:**
  - **required:** True
  - **description:** API Role name
- **api_role_template:**
  - **required:** True
  - **description:** Full path to the JSON template
- **replace_api_role:**
  - **required:** False
  - **description:** Overwrite an existing API Role if True.
  - **default:** False
- **sleep:**
  - **required:** False
  - **description:** Pause after running this processor for specified seconds.
  - **default:** "0"

## Output variables

- **jamfapiroleuploader_summary_result:**
  - **description:** Description of interesting results.
- **api_role_name:**
  - **description:** API Role name.
- **api_role_updated:**
  - **description:** Boolean - True if the API Role was changed.
