# JamfMobileDeviceStaticGroupUploader

## Description

A processor for AutoPkg that will upload a static mobile device group to a Jamf Cloud or on-prem server using the Jamf Pro API.

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
- **mobiledevicegroup_name**:
  - **required**: False
  - **description**: Mobile Device Group name
- **group_description**:
  - **required**: False
  - **description**: a description to assign to the Mobile Device Group
- **replace_group**:
  - **required**: False
  - **description**: overwrite an existing Mobile Device Group if True.
  - **default**: False
- **clear_assignments**:
  - **required**: False
  - **description**: clear members of an existing Mobile Device Group if True.
  - **default**: False
- **sleep:**
  - **required:** False
  - **description:** Pause after running this processor for specified seconds.
  - **default:** "0"
- **max_tries:**
  - **required:** False
  - **description:** Maximum number of attempts to upload the account. Must be an integer between 1 and 10.
  - **default:** "5"
- **skip_if:**
  - **required:** False
  - **description:** Skip the process if a supplied predicate is met.

## Output variables

- **jamfmobiledevicestaticgroupuploader_summary_result:**
  - **description:** Description of interesting results.
