# JamfPatchChecker

## Description

A processor for AutoPkg that will check and report whether a Patch Software Title has the version that AutoPkg has found or not. This can be used with a subsequent `StopProcessingIf` processor to prevent updating a Patch Policy with a version that does not yet exist in the Patch Software Title, allowing the recipe to run again on a subsequent recipe run.

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
- **pkg_name**:
  - **required**: True
  - **description**: Name of package which should be used in the patch. Mostly provided by previous AutoPKG recipe/processor.
- **version**:
  - **required**: True
  - **description**: Version string - provided by previous pkg recipe/processor.
- **sleep:**
  - **required:** False
  - **description:** Pause after running this processor for specified seconds.
  - **default:** "0"

## Output variables

- **jamfpatchuploader_summary_result:**
  - **description:** Description of interesting results.
