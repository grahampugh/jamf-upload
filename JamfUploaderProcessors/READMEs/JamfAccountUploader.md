# JamfAccountUploader

## Description

A processor for AutoPkg that will upload an account to a Jamf Cloud or on-prem server, with privileges supplied by a template xml file.

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
- **account_name:**
  - **required:** True
  - **description:** Account name
- **account_type:**
  - **required:** True
  - **description:** Account type; "user" or "group"
- **account_template:**
  - **required:** True
  - **description:** Full path to the XML template
- **replace_account:**
  - **required:** False
  - **description:** Overwrite an existing account if True.
  - **default:** False

## Output variables

- **jamfaccountuploader_summary_result:**
  - **description:** Description of interesting results.
- **account_name:**
  - **description:** Policy name.
- **account_updated:**
  - **description:** Boolean - True if the account was changed.
- **changed_account_id:**
  - **description:** Jamf object ID of the newly created or modified account.
