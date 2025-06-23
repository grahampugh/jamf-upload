# JamfPolicyUploader

## Description

A processor for AutoPkg that will upload a policy to a Jamf Cloud or on-prem server. Optionally, an icon can be uploaded and associated with the policy.

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
- **policy_name:**
  - **required:** True
  - **description:** Policy name
- **icon:**
  - **required:** False
  - **description:** Full path to Self Service icon
- **policy_template:**
  - **required:** True
  - **description:** Full path to the XML template
- **replace_policy:**
  - **required:** False
  - **description:** Overwrite an existing policy if True.
  - **default:** False
- **replace_icon:**
  - **required:** False
  - **description:** Overwrite an existing policy icon if True.
  - **default:** False
- **retain_scope**:
  - **required**: False
  - **description**: retain the existing scope of an existing policy if True.
  - **default**: False
- **sleep:**
  - **required:** False
  - **description:** Pause after running this processor for specified seconds.
  - **default:** "0"

## Output variables

- **jamfpolicyuploader_summary_result:**
  - **description:** Description of interesting results.
- **policy_name:**
  - **description:** Policy name.
- **policy_updated:**
  - **description:** Boolean - True if the policy was changed.
- **changed_policy_id:**
  - **description:** Jamf object ID of the newly created or modified policy.
