# JamfComputerGroupUploader

## Description

A processor for AutoPkg that will upload various Classic API objects to a Jamf Cloud or on-prem server. To be used when no specific processor is available for the required object type. Note that many objects may not work due to exceptions to the API object from "standard" - test first!

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
- **replace_object**:
  - **required**: False
  - **description**: overwrite an existing Computer Group if True.
  - **default**: False
- **sleep:**
  - **required:** False
  - **description:** Pause after running this processor for specified seconds.
  - **default:** "0"

## Output variables

- **jamfclassicapiobjectuploader_summary_result:**
  - **description:** Description of interesting results.
- **object_name**:
  - **description**: The name of the API object
- **object_type**:
  - **description**: The API object type. This is in the singular form - the name of the key in the XML template.
- **object_updated**:
  - **description**: Boolean - True if the object was changed.
