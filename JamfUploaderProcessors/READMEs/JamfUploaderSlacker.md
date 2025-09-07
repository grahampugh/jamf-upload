# JamfUploaderSlacker

## Description

A postprocessor for AutoPkg that will send details about a recipe run to a Slack webhook based on the output of a JamfPolicyUploader process.

Takes elements from [this gist](https://gist.github.com/devStepsize/b1b795309a217d24566dcc0ad136f784) and [Yo.py processor](https://github.com/autopkg/nmcspadden-recipes/blob/master/PostProcessors/Yo.py).

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
- **pkg_name:**
  - **required:** False
  - **description:** File name of the pkg being uploaded.
- **version:**
  - **required:** False
  - **description:** Package version.
- **policy_name:**
  - **required:** False
  - **description:** The uploaded policy name.
- **jamfpackageuploader_summary_result:**
  - **required:** False
  - **description:** Result of JamfPackageUploader.
- **jamfpolicyuploader_summary_result:**
  - **required:** False
  - **description:** Result of JamfPolicyUploader.
- **slack_webhook_url:**
  - **required:** True
  - **description:** Slack webhook URL to send the message to.
- **slack_username:**
  - **required:** False
  - **description:** Sets the display name shown in the message in Slack. Defaults to AutoPkg.
- **slack_icon_url:**
  - **required:** False
  - **description:** Sets the icon shown in the Slack notification.
- **slack_channel:**
  - **required:** False
  - **description:** Slack channel (for overriding the default).
- **slack_icon_emoji:**
  - **required:** False
  - **description:** Sets the icon shown in the Slack notification as an emoji.
