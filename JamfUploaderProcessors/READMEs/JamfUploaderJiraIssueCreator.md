# JamfUploaderJiraIssueCreator

## Description

A postprocessor for AutoPkg that will create a Jira issue based on the output of a JamfUploader process.

## Input variables

- **JSS_URL:**
  - **required:** True
  - **description:** URL to a Jamf Pro server. Used to display which JSS server the recipe was run against.
- **POLICY_CATEGORY:**
  - **required:** False
  - **description:** Category for the created/updated policy.
- **PKG_CATEGORY:**
  - **required:** False
  - **description:** Category for the created/updated pkg.
- **NAME:**
  - **required:** True
  - **description:** Name of the application being created/updated.
- **patch_name:**
  - **required:** False
  - **description:** Name of the Patch Policy being updated.
- **pkg_name:**
  - **required:** False
  - **description:** File name of the pkg being uploaded.
- **policy_name:**
  - **required:** False
  - **description:** The uploaded policy name.
- **jamfpackageuploader_summary_result:**
  - **required:** False
  - **description:** Result of JamfPackageUploader.
- **jamfpatchuploader_summary_result:**
  - **required:** False
  - **description:** Result of JamfPatchUploader.
- **jamfpolicyuploader_summary_result:**
  - **required:** False
  - **description:** Result of JamfPolicyUploader.
- **jira_url:**
  - **required:** True
  - **description:** Jira base URL to send the message to (e.g. <https://yourcompany.atlassian.net> - API endpoint not required).
- **jira_product_id:**
  - **required:** True
  - **description:** Jira Product ID
- **jira_username:**
  - **required:** True
  - **description:** Account name with access to Jira Issues.
- **jira_api_token:**
  - **required:** True
  - **description:** API Token created in the account supplied in jira_username.
- **jira_issuetype_id:**
  - **required:** False
  - **description:** Jira Issue Type. Default is 10001 ('Story'). See <https://support.atlassian.com/jira/kb/finding-the-id-for-issue-types-in-jira-server-or-data-center/>.
  - **default:** 10001
- **jira_priority_id:**
  - **required:** False
  - **description:** Jira Priority. Default is 5 (the lowest priority). See <https://support.atlassian.com/jira/kb/find-the-id-numbers-of-jira-priority-field-values-in-jira-cloud/>.
  - **default:** 5
