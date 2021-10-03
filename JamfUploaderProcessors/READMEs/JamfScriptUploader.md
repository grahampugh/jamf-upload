# JamfScriptUploader

## Description

A processor for AutoPkg that will upload a script to a Jamf Cloud or on-prem server.

## Input variables

- **JSS_URL:**
  - **required:** True
  - **description:** URL to a Jamf Pro server that the API user has write access to, optionally set as a key in the com.github.autopkg preference file.
- **API_USERNAME:**
  - **required:** True
  - **description:** Username of account with appropriate access to jss, optionally set as a key in the com.github.autopkg preference file.
- **API_PASSWORD:**
  - **required:** True
  - **description:** Password of api user, optionally set as a key in the com.github.autopkg preference file.
- **script_path**:
  - **required**: False
  - **description**: Full path to the script to be uploaded
- **script_name**:
  - **required**: False
  - **description**: Name of the script in Jamf
- **script_category**:
  - **required**: False
  - **description**: Script category
- **script_priority**:
  - **required**: False
  - **description**: Script priority (BEFORE or AFTER)
  - **default**: AFTER
- **osrequirements**:
  - **required**: False
  - **description**: Script OS requirements
- **script_info**:
  - **required**: False
  - **description**: Script info field
- **script_notes**:
  - **required**: False
  - **description**: Script notes field
- **script_parameter4**:
  - **required**: False
  - **description**: Script parameter 4 title
- **script_parameter5**:
  - **required**: False
  - **description**: Script parameter 5 title
- **script_parameter6**:
  - **required**: False
  - **description**: Script parameter 6 title
- **script_parameter7**:
  - **required**: False
  - **description**: Script parameter 7 title
- **script_parameter8**:
  - **required**: False
  - **description**: Script parameter 8 title
- **script_parameter9**:
  - **required**: False
  - **description**: Script parameter 9 title
- **script_parameter10**:
  - **required**: False
  - **description**: Script parameter 10 title
- **script_parameter11**:
  - **required**: False
  - **description**: Script parameter 11 title
- **replace_script**:
  - **required**: False
  - **description**: Overwrite an existing script if True.
  - **default**: False

## Output variables

- **script_name**:
  - **description:** Name of the uploaded script
- **jamfscriptuploader_summary_result:**
  - **description:** Description of interesting results.
