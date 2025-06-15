# JamfMobileDeviceAppUploader

## Description

A processor for AutoPkg that will update or clone a Mobile Device app object on a Jamf Pro server. A new one cannot be created.

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
- **mobiledeviceapp_name:**
  - **required:** False
  - **description:** Mobile Device app name
  - **default:** ""
- **clone_from:**
  - **required:** False
  - **description:** Mobile Device app name from which to clone this entry
  - **default:** ""
- **selfservice_icon_uri:**
  - **required:** False
  - **description:** Mobile Device app icon URI
  - **default:** ""
- **mobiledeviceapp_template:**
  - **required:** False
  - **description:** Full path to the XML template
- **appconfig_template:**
  - **required:** False
  - **description:** Full path to the AppConfig XML template
- **replace_mobiledeviceapp:**
  - **required:** False
  - **description:** Overwrite an existing Mobile Device app if True.
  - **default:** False
- **sleep:**
  - **required:** False
  - **description:** Pause after running this processor for specified seconds.
  - **default:** "0"

## Output variables

- **jamfmobiledeviceappuploader_summary_result:**
  - **description:** Description of interesting results.
- **mobiledeviceapp_name:**
  - **description:** Jamf object name of the newly created or modified mobiledeviceapp.
- **mobiledeviceapp_updated:**
  - **description:** Boolean - True if the mobiledeviceapp was changed.
- **changed_mobiledeviceapp_id:**
  - **description:** Jamf object ID of the newly created or modified mobiledeviceapp.
