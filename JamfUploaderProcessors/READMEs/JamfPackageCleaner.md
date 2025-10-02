# JamfPackageCleaner

## Description

A processor for AutoPkg that will remove packages matching a pattern from a Jamf Cloud or on-prem server. Requires Package delete permissions.

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
- **pkg_name_match**:
  - **required**: False
  - **description**: The name at the beginning of the package. This is used as a base for cleaning. If omitted, `%NAME%-`, e.g. `Google Chrome-`, or `%NAME%_`, e.g. =`Google Chrome_`, will be matched.
- **versions_to_keep**:
  - **required**: False
  - **description**: The number of `pkg_name_match` values to keep in Jamf Pro. This is based on the package ID.
  - **default**: 3
- **minimum_name_length**:
  - **required**: False
  - **description**: The minimum number of characters required in `pkg_name_match`. This is used as a failsafe.
  - **default**: 3
- **maximum_allowed_packages_to_delete**:
  - **required**: False
  - **description**: The maximum number of packages that can be deleted. This is used as a failsafe.
  - **default**: 20
- **dry_run**:
  - **required**: False
  - **description**: If set to True, nothing is deleted from Jamf Pro. Use together with `-vv` for detailed information. This is used for testing
  - **default**: False

## Output variables

- **jamfpackagecleaner_summary_result:**
  - **description:** Description of interesting results.
