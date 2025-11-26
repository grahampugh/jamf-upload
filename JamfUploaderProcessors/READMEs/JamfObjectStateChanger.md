# JamfObjectStateChanger

## Description

A processor for AutoPkg that will change the state of an object on a Jamf Cloud or on-prem server.

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
- **object_name**:
  - **required**: False
  - **description**: The name of the API object
- **object_type**:
  - **required**: True
  - **description**: The API object type. This is in the singular form - for Classic API endpoints this is the name of the key in the XML template. For JSON objects it is a construction made interally for this project. See the [Object Reference](./Object%20Reference.md) for valid objects. Valid values are `policy`, `computer_extension_attribute`, `app_installers_deployment`. Note that only script-based extension attributes may be enabled or disabled.
  - **default:** "policy"
- **object_state:**
  - **required:** True
  - **description:** The desired state of the object, either `enable` or `disable`.
  - **default:** "disable"
- **max_tries:**
  - **required:** False
  - **description:** Maximum number of attempts to upload the account. Must be an integer between 1 and 10.
  - **default:** "5"

## Output variables

- **jamfobjectstatechanger_summary_result:**
  - **description:** Description of interesting results.
