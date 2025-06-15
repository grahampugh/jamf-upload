# JamfObjectUploader

## Description

A processor for AutoPkg that will create a Managed Software Update Plan. Currently restricted to the DOWNLOAD_INSTALL_SCHEDULE plan type (the only DDM plan available in Jamf Pro).

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
- **device_type**:
  - **required**: True
  - **description**: Device type, must be one of 'computer', 'mobile-device', 'apple-tv' (case-insensitive).
- **group_name**:
  - **required**: True
  - **description**: Name of the target computer group or mobile device group.
- **version**:
  - **required**: False
  - **description**: OS Version to deploy, must be one of 'latest-minor', 'latest-major', 'latest-any', or a valid specific version string for the OS to be applied.
- **days_until_force_install**:
  - **required**: False
  - **description**: Days until forced installation of planned managed software update.
  - **default**: 7
- **sleep:**
  - **required:** False
  - **description:** Pause after running this processor for specified seconds.
  - **default:** "0"

## Output variables

- **jamfmsuplanuploader_summary_result:**
  - **description:** Description of interesting results.
- **device_type**:
  - **description**:  Device type.
- **version_type**:
  - **description**: Version type, one of 'latest_minor', 'latest_major', 'latest_any', or 'specific_version'.
- **specific_version**:
  - **description**: Specific version, if 'version_type' is set to 'specific_version'.
- **object_updated**:
  - **description**: The date and time of the plan's forced installation deadline.
