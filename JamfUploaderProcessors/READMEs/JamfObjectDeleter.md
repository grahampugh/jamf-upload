# JamfObjectDeleter

## Description

A processor for AutoPkg to delete an API object.

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
  - **description**: The API object type. This is in the singular form - the name of the key in the XML template. See the [Object Reference](./Object%20Reference.md) for valid objects.

## Output variables

- **jamfobjectdeleter_summary_result:**
  - **description:** Description of interesting results.
- **object_name**:
  - **description**: The name of the API object
