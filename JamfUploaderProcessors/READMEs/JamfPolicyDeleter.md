# JamfPolicyDeleter

## Description

A processor for AutoPkg that will upload a policy to a Jamf Cloud or on-prem server. Optionally, an icon can be uploaded and associated with the policy.

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
- **policy_name:**
  - **required:** False
  - **description:** Policy name

## Output variables

- **jamfpolicydeleter_summary_result:**
  - **description:** Description of interesting results.
