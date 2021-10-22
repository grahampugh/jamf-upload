# JamfExtensionAttributeUploader

## Description

A processor for AutoPkg that will upload an item to a Jamf Cloud or on-prem server.

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
- **ea_name**:
  - **required**: False
  - **description**: Extension Attribute name
- **ea_script_path**:
  - **required**: False
  - **description**: Full path to the script to be uploaded
- **replace_ea**:
  - **required**: False
  - **description**: Overwrite an existing Extension Attribute if True.
  - **default**: False

## Output variables

- **jamfextensionattributeuploader_summary_result:**
  - **description:** Description of interesting results.
