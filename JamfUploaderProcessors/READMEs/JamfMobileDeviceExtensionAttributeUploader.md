# JamfMobileDeviceExtensionAttributeUploader

## Description

A processor for AutoPkg that will upload a Mobile Device Extension Attribute item to a Jamf Cloud or on-prem server.

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
- **ea_name**:
  - **required**: False
  - **description**: Mobile Device Extension Attribute name
- **replace_ea**:
  - **required**: False
  - **description**: Overwrite an existing Mobile Device Extension Attribute if True.
  - **default**: False
- **ea_inventory_display:**
  - **required:** False
  - **description:** Inventory Display value for the Mobile Device Extension Attribute.
  - **default:** "Extension Attributes"
- **ea_data_type:**
  - **required:** False
  - **description:** Data type for the Mobile Device Extension Attribute. One of String, Integer or Date.
  - **default:** "String"
- **ea_popup_choices:**
  - **required:** False
  - **description:** Comma-separated list of popup choices for the Mobile Device Extension Attribute.
- **ea_input_type:**
  - **required:** False
  - **description:** Type of Mobile Device Extension Attribute. One of popup, text, or ldap.
  - **default:** "text"
- **ea_description:**
  - **required:** False
  - **description:** Description for the Mobile Device Extension Attribute.
- **ea_directory_service_attribute_mapping:**
  - **required:** False
  - **description:** Directory Service (LDAP) attribute mapping. Currently this must be manually set.
- **sleep:**
  - **required:** False
  - **description:** Pause after running this processor for specified seconds.
  - **default:** "0"

## Output variables

- **jamfmobiledeviceextensionattributeuploader_summary_result:**
  - **description:** Description of interesting results.
