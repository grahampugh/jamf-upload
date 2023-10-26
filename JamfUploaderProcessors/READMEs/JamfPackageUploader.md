# JamfPackageUploader

## Description

A processor for AutoPkg that will upload a package to a JCDS or File Share Distribution Point.

Can be run as a post-processor for a pkg recipe or in a child recipe. The parent (pkg) recipe must output pkg_path as this is a required key.

## Input variables

- **pkg_name:**
  - **required:** False
  - **description:** Package name. If supplied, will rename the package supplied in the pkg_path key when uploading it to the fileshare.
- **pkg_display_name:**
  - **required:** False
  - **description:** Package display name, which may be different to the `pkg_name`. If not supplied, reverts to `pkg_name`.
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
- **os_requirements:**
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
- **skip_metadata_upload:**
  - **required:** False
  - **description:** For Jamf Cloud customers, skip the upload of package metadata. This allows a new package to be uploaded but will not write any metadata such as SHA512 hash, category, info, etc. This allows upload of packages with just `create` and `read` privileges on package objects (otherwise `update` rights are also required). Not for use by self-hosted Jamf customers, and not relevant in conjunction with `jcds_mode`. Note that `replace_package` key is not functional if `skip_metadata_upload` is set.
  - **default:** False
- **jcds_mode:**
  - **required:** False
  - **description:** This option is no longer functional. A warning message is displayed if set.
  - **default:** False
- **jcds2_mode:**
  - **required:** False
  - **description:** Upload package using JCDS2 mode.
  - **default:** False
- **JSS_URL:**
  - **required:** True
  - **description:** URL to a Jamf Pro server to which the API user has write access.
- **API_USERNAME:**
  - **required:** True
  - **description:** Username of account with appropriate API access to the Jamf Pro Server.
- **API_PASSWORD:**
  - **required:** True
  - **description:** Password of account with appropriate API access to the Jamf Pro Server..
- **CLOUD_DP:**
  - **required:** False
  - **description:** Indicates the presence of a Cloud Distribution Point. The default is deliberately blank. If no SMB DP is configured, the default setting assumes that the Cloud DP has been enabled. If at least one SMB DP is configured, the default setting assumes that no Cloud DP has been set. This can be overridden by setting `CLOUD_DP` to `True`, in which case packages will be uploaded to both a Cloud DP plus the SMB DP(s)."
- **SMB_URL:**
  - **required:** False
  - **description:** URL to a Jamf Pro file share distribution point which should be in the form `smb://server/share` or a local DP in the form `file://path`. Subsequent DPs can be configured using `SMB2_URL`, `SMB3_URL` etc. Accompanying username and password must be supplied for each DP, e.g. `SMB2_USERNAME`, `SMB2_PASSWORD` etc.
- **SMB_USERNAME:**
  - **required:** False
  - **description:** Username of account with appropriate access to a Jamf Pro fileshare distribution point.
- **SMB_PASSWORD:**
  - **required:** False
  - **description:** Password of account with appropriate access to a Jamf Pro fileshare distribution point.
- **SMB_SHARES:**
  - **required:** False
  - **description:** An array of dictionaries containing `SMB_URL`, `SMB_USERNAME` and `SMB_PASSWORD`, as an alternative to individual keys. Any individual keys will override this complete array. The array can only be provided via the AutoPkg preferences file.
- **sleep:**
  - **required:** False
  - **description:** Pause after running this processor for specified seconds.
  - **default:** "0"

## Output variables

- **pkg_path:**
  - **description:** The path of the package as provided from the parent recipe.
- **pkg_name:**
  - **description:** The name of the uploaded package.
- **pkg_uploaded:**
  - **description:** True/False depending if a package was uploaded or not.
- **jamfpackageuploader_summary_result:**
  - **description:** Description of interesting results.
