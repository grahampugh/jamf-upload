# JamfMacAppUploader

## Description

A processor for AutoPkg that will update or clone a Mac App Store app object on a Jamf Pro server. A new one cannot be created.

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
- **macapp_name:**
  - **required:** False
  - **description:** Mac App Store app name
  - **default:** ""
- **clone_from:**
  - **required:** False
  - **description:** Mac App Store app name from which to clone this entry
  - **default:** ""
- **selfservice_icon_uri:**
  - **required:** False
  - **description:** Mac App Store app icon URI
  - **default:** ""
- **macapp_template:**
  - **required:** False
  - **description:** Full path to the XML template
- **replace_macapp:**
  - **required:** False
  - **description:** Overwrite an existing Mac App Store app if True.
  - **default:** False
- **sleep:**
  - **required:** False
  - **description:** Pause after running this processor for specified seconds.
  - **default:** "0"

## Output variables

- **jamfmacappuploader_summary_result:**
  - **description:** Description of interesting results.
- **macapp_name:**
  - **description:** Jamf object name of the newly created or modified macapp.
- **macapp_updated:**
  - **description:** Boolean - True if the macapp was changed.
- **changed_macapp_id:**
  - **description:** Jamf object ID of the newly created or modified macapp.
