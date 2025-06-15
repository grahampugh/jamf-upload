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
- **object_name**:
  - **required**: False
  - **description**: The name of the API object
- **object_template**:
  - **required**: True
  - **description**: Path to the API object template file. For Classic API endpoints this must be XML, for Jamf Pro API endpoints this must be JSON.
- **object_type**:
  - **required**: True
  - **description**: The API object type. This is in the singular form - for Classic API endpoints this is the name of the key in the XML template. For JSON objects it is a construction made interally for this project. See the [Object Reference](./Object%20Reference.md) for valid objects.
- **elements_to_remove**:
  - **required**: False
  - **description**: A list of XML or JSON elements that should be removed from the downloaded XML. Note that `id` and `self_service_icon` are removed automatically.
- **replace_object**:
  - **required**: False
  - **description**: overwrite an existing Computer Group if True.
  - **default**: False
- **sleep:**
  - **required:** False
  - **description:** Pause after running this processor for specified seconds.
  - **default:** "0"

## Output variables

- **jamfobjectuploader_summary_result:**
  - **description:** Description of interesting results.
- **object_name**:
  - **description**: The name of the API object
- **object_type**:
  - **description**: This is in the singular form - for Classic API endpoints this is the name of the key in the XML template. For JSON objects it is a construction made interally for this project. See the [Object Reference](./Object%20Reference.md) for valid objects.
- **object_updated**:
  - **description**: Boolean - True if the object was changed.
