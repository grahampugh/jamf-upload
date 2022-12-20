# JamfPolicyLogFlusher

## Description

A processor for AutoPkg that will flush logs for a policy on a Jamf Cloud or on-prem server.

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
  - **required:** True
  - **description:** Policy whose log is to be flushed
- **interval:**
  - **required:** False
  - **description:** Interval of log to flush
  - **default:** "Zero Days"

## Output variables

- **jamfpolicylogflusher_summary_result:**
  - **description:** Description of interesting results.
