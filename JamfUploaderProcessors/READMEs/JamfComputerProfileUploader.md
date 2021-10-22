# JamfComputerProfileUploader

## Description

A processor for AutoPkg that will upload a computer configuration profile to a Jamf Cloud or on-prem server.

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
- **profile_name**:
  - **required**: False
  - **description**: Configuration Profile name
- **payload**:
  - **required**: False
  - **description**: Path to Configuration Profile payload plist file
- **mobileconfig**:
  - **required**: False
  - **description**: Path to Configuration Profile mobileconfig file
- **identifier**:
  - **required**: False
  - **description**: Configuration Profile payload identifier
- **profile_template**:
  - **required**: False
  - **description**: Path to Configuration Profile XML template file
- **profile_category**:
  - **required**: False
  - **description**: a category to assign to the profile
- **organization**:
  - **required**: False
  - **description**: Organization to assign to the profile
- **profile_description**:
  - **required**: False
  - **description**: a description to assign to the profile
- **profile_computergroup**:
  - **required**: False
  - **description**: a computer group that will be scoped to the profile
- **unsign_profile**:
  - **required**: False
  - **description**: Unsign a mobileconfig file prior to uploading if it is signed, if true.
  - **default**: False
- **replareplace_profilece_category**:
  - **required**: False
  - **description**: overwrite an existing Configuration Profile if True.
  - **default**: False

## Output variables

- **jamfcomputerprofileuploader_summary_result:**
  - **description:** Description of interesting results.
