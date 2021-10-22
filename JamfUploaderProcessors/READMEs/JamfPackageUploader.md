# JamfPackageUploader

## Description

A processor for AutoPkg that will upload a package to a JCDS or
File Share Distribution Point.

Can be run as a post-processor for a pkg recipe or in a child recipe.
The pkg recipe must output pkg_path or this will fail.

## Input variables

- **pkg_name:**
  - **required:** False
  - **description:** Package name. If supplied, will rename the package supplied in the pkg_path key when uploading it to the fileshare.
- **pkg_path:**
  - **required:** False
  - **description:** Path to a pkg or dmg to import - \*\*provided by previous pkg recipe/processor.
- **version:**
  - **required:** False
  - **description:** Version string - \*\*provided by previous pkg recipe/processor.
- **pkg_category:**
  - **required:** False
  - **description:** Package category
- **pkg_info:**
  - **required:** False
  - **description:** Package info field
- **pkg_notes:**
  - **required:** False
  - **description:** Package notes field
- **pkg_priority:**
  - **required:** False
  - **description:** Package priority.
  - **default:** 10
- **reboot_required:**
  - **required:** False
  - **description:** Whether a package requires a reboot after installation.
  - **default:**
- **os_requirement:**
  - **required:** False
  - **description:** Package OS requirement
- **required_processor:**
  - **required:** False
  - **description:** Package required processor. Acceptable values are 'x86' or 'None'
  - **default:** None
- **send_notification:**
  - **required:** False
  - **description:** Whether to send a notification when a package is installed.
  - **default:** 'False'
- **replace_pkg:**
  - **required:** False
  - **description:** Overwrite an existing package if True.
  - **default:** False
- **replace_pkg_metadata:**
  - **required:** False
  - **description:** Overwrite existing package metadata and continue if True, even if the package object is not re-uploaded.
  - **default:** False
- **JSS_URL:**
  - **required:** True
  - **description:** URL to a Jamf Pro server that the API user has write access to, optionally set as a key in the com.github.autopkg preference file.
- **API_USERNAME:**
  - **required:** True
  - **description:** Username of account with appropriate access to jss, optionally set as a key in the com.github.autopkg preference file.
- **API_PASSWORD:**
  - **required:** True
  - **description:** Password of api user, optionally set as a key in the com.github.autopkg preference file.
- **SMB_URL:**
  - **required:** False
  - **description:** URL to a Jamf Pro fileshare distribution point which should be in the form `smb://server/share`.
- **SMB_USERNAME:**
  - **required:** False
  - **description:** Username of account with appropriate access to jss, optionally set as a key in the com.github.autopkg preference file.
- **SMB_PASSWORD:**
  - **required:** False
  - **description:** Password of api user, optionally set as a key in the com.github.autopkg preference file.

## Output variables

- **pkg_path:**
  - **description:** The path of the package as provided from the parent recipe.
- **pkg_name:**
  - **description:** The name of the uploaded package.
- **pkg_uploaded:**
  - **description:** True/False depending if a package was uploaded or not.
- **jamfpackageuploader_summary_result:**
  - **description:** Description of interesting results.
