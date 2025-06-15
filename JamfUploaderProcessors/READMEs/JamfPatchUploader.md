# JamfPatchUploader

## Description

A processor for AutoPkg that will upload a Patch Policy to a Jamf Cloud or on-prem server.

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
- **patch_softwaretitle**:
  - **required**: True
  - **description**: Name of the patch softwaretitle (e.g. 'Mozilla Firefox') used in Jamf. You need to create the patch softwaretitle by hand, since there is currently no way to create these via the API.
- **patch_name**:
  - **required**: False
  - **description**: Name of the patch policy (e.g. 'Mozilla Firefox - 93.02.10').
  - **default**: '%patch_softwaretitle% - %version%'
- **patch_template**:
  - **required**: False
  - **description**: XML-Template used for the patch policy. If none is provided, only the installer will be linked to the corresponding version and no patch policy will be created.
- **patch_icon_policy_name**:
  - **required**: False
  - **description**: Name of an already existing (!) policy (not a patch policy). The icon of this policy will be extracted and can be used in the patch template with the variable `%patch_icon_id%`. There is currently no reasonable way to upload a custom icon for patch policies.
- **replace_patch**:
  - **required**: False
  - **description**: Overwrite an existing patch policy if True.
  - **default**: False
- **sleep:**
  - **required:** False
  - **description:** Pause after running this processor for specified seconds.
  - **default:** "0"

## Output variables

- **jamfpatchuploader_summary_result:**
  - **description:** Description of interesting results.
