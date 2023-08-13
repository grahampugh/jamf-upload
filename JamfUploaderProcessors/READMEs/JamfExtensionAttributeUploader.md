# JamfExtensionAttributeUploader

## Description

A processor for AutoPkg that will upload an Extension Attribute item to a Jamf Cloud or on-prem server.

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
- **ea_inventory_display:**
  - **required:** False
  - **description:** Inventory Display value for the EA.
  - **default:** "Extension Attributes"
- **ea_data_type:**
  - **required:** False
  - **description:** Data type for the EA. One of String, Integer or Date.
  - **default:** "String"
- **sleep:**
  - **required:** False
  - **description:** Pause after running this processor for specified seconds.
  - **default:** "0"

## Output variables

- **jamfextensionattributeuploader_summary_result:**
  - **description:** Description of interesting results.
