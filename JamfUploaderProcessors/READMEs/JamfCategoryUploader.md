# JamfCategoryUploader

## Description

A processor for AutoPkg that will upload a category to a Jamf Cloud or on-prem server.

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
- **category_name**:
  - **required**: False
  - **description**: Category
- **category_priority**:
  - **required**: False
  - **description**: Category priority
  - **default**: 10
- **replace_category**:
  - **required**: False
  - **description**: Overwrite an existing category if True.
  - **default**: False
- **sleep:**
  - **required:** False
  - **description:** Pause after running this processor for specified seconds.
  - **default:** "0"

## Output variables

- **category:**
  - **description:** The created/updated category.
- **jamfcategoryuploader_summary_result:**
  - **description:** Description of interesting results.
