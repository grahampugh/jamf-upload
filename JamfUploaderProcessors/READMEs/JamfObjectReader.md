# JamfObjectReader

## Description

A processor for AutoPkg to read an API object and optionally, output to file (XML or JSON depending on whether the Classic or Jamf Pro API is used). Optionally, all objects of a single type may be downloaded in one operation. Additionally, Scripts, Extension Attributes and Mobileconfig files are extracted from the XML and saved as separate files.

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
  - **description**: Path to the API object template file
- **object_type**:
  - **required**: True
  - **description**: The API object type. This is in the singular form - the name of the key in the XML template. See the [Object Reference](./Object%20Reference.md) for valid objects.
- **output_dir**:
  - **required**: False
  - **description**: Output directory to dump the xml or json file.
- **settings_key**:
  - **required**: False
  - **description**: For settings-style endpoints, specify a key from which to get the value.
- **uuid**:
  - **required**: False
  - **description**: For the managed software update events endpoint, specify a `uuid` value from which to get the events.
- **all_objects**:
  - **required**: False
  - **description**: Download all objects of the specific object type.
- **list_only**:
  - **required**: False
  - **description**: Only output a variable with a list of all objects - ID and name (depending on the endpoint, more keys may exist in the outputted list).
- **elements_to_remove**:
  - **required**: False
  - **description**: A list of XML or JSON elements that should be removed from the downloaded XML. Note that `id` and `self_service_icon` are removed automatically.
- **elements_to_retain**:
  - **required**: False
  - **description**: A list of XML or JSON elements that should be retained from the downloaded XML. Other keys will be removed if any value is set.

## Output variables

- **jamfobjectreader_summary_result:**
  - **description:** Description of interesting results.
- **object_name**:
  - **description**: The name of the API object
- **object_id**:
  - **description**: The ID of the API object
- **raw_object**:
  - **description**: String containing the complete raw downloaded XML
- **parsed_object**:
  - **description**: String containing parsed XML (removes IDs and computers)
- **output_dir**:
  - **description**: Directory the xml or json file was saved to.
