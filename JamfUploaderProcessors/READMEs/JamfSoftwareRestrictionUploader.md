# JamfSoftwareRestrictionUploader

## Description

A processor for AutoPkg that will upload a restricted software record to a Jamf Cloud or on-prem server.

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
- **restriction_name**:
  - **required**: False
  - **description**: Software Restriction name
- **restriction_template**:
  - **required**: False
  - **description**: Path to Software Restriction XML template file
- **restriction_computergroup**:
  - **required**: False
  - **description**: A single computer group to add to the scope.
- **process_name**:
  - **required**: False
  - **description**: Process name to restrict.
- **display_message**:
  - **required**: False
  - **description**: Message to display to users when the restriction is invoked.
- **match_exact_process_name**:
  - **required**: False
  - **description**: Match only the exact process name if True.
  - **default**: False
- **restriction_send_notification**:
  - **required**: False
  - **description**: Send a notification when the restriction is invoked if True.
  - **default**: False
- **kill_process**:
  - **required**: False
  - **description**: Kill the process when the restriction is invoked if True.
  - **default**: False
- **delete_executable**:
  - **required**: False
  - **description**: Delete the executable when the restriction is invoked if True.
  - **default**: False
- **replace_restriction**:
  - **required**: False
  - **description**: Overwrite an existing Software Restriction if True.
  - **default**: False
- **sleep:**
  - **required:** False
  - **description:** Pause after running this processor for specified seconds.
  - **default:** "0"

## Output variables

- **jamfsoftwarerestrictionuploader_summary_result:**
  - **description:** Description of interesting results.
