# JamfObjectReader

## Description

A processor for AutoPkg to read an API object and output to file (XML or JSON depending on whether the Classic or Jamf Pro API is used.)

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
  - **required:** True
  - **description:** Client ID with access to access to jss, optionally set as a key in the com.github.autopkg preference file.
- **CLIENT_SECRET:**
  - **required:** True
  - **description:** Secret associated with the Client ID, optionally set as a key in the com.github.autopkg preference file.
- **object_name**:
  - **required**: False
  - **description**: The name of the API object
- **object_template**:
  - **required**: True
  - **description**: Path to the API object template file
- **object_type**:
  - **required**: True
  - **description**: The API object type. This is in the singular form - the name of the key in the XML template.
- **output_path**:
  - **required**: False
  - **description**: Path to dump the xml or json file.

## Output variables

- **jamfclassicapiobjectuploader_summary_result:**
  - **description:** Description of interesting results.
- **object_name**:
  - **description**: The name of the API object
- **object_id**:
  - **description**: The ID of the API object
- **raw_object**:
  - **description**: String containing the complete raw downloaded XML
- **parsed_object**:
  - **description**: String containing parsed XML (removes IDs and computers)
- **output_path**:
  - **description**: Path the xml or json file was saved to.
