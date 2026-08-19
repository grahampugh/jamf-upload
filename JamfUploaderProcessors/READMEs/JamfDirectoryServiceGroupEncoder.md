# JamfDirectoryServiceGroupEncoder

## Description

A processor for AutoPkg that resolves a Directory Service group name to the base64-encoded value required by *directory service group* criteria in smart groups and advanced searches (Jamf Pro 11.29 and later).

These criteria do not take a group name as their value. They take a base64-encoded JSON object of the form `{"uuid":"E5EFCA3E-892C-4CCE-B2C1-6CA1A32E9153","serverId":"31"}`. This processor looks the group up via the `/api/v1/ldap/groups` endpoint, which searches every configured Directory Service, whether it is an LDAP server or a Cloud Identity Provider such as Okta or Entra ID. It then encodes the value and returns it as the `directory_service_group_value` output variable, for substitution into a template that is uploaded with `JamfComputerGroupUploader`, `JamfMobileDeviceGroupUploader` or `JamfObjectUploader`.

The criteria that take one of these values are documented by Jamf in [Directory Service Group Criteria](https://learn.jamf.com/r/en-US/jamf-pro-documentation-current/Directory_Service_Group_Criteria). Which of them are accepted depends on the object being uploaded:

- `Assigned User directory service group` - computer and mobile objects.
- `Username directory service group` - computer, mobile and user objects.
- `User last logged in - Computer directory service group` - computer objects only.
- `User last logged in - Self Service directory service group` - computer and mobile objects.
- `User last logged in - Mdm directory service group` - computer and mobile objects.

Here, computer objects are computer groups and advanced computer searches, mobile objects are mobile device groups and advanced mobile device searches, and user objects are user groups and advanced user searches.

The criterion names are case-sensitive, and the API rejects an unrecognised name with an empty HTTP 409 response, giving no indication of what was wrong. Note that two of the names above are cased differently to the Jamf documentation, which lists them as `User last logged in - MDM directory service group` and `Assigned user directory service group`. Both of those forms are rejected; the forms listed above are the ones the API accepts.

Membership is not immediate. Jamf Pro caches directory user information locally and syncs every 20 minutes, so a group uploaded by this processor may take some time to populate.

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
  - **description:** Client ID with access to jss, optionally set as a key in the com.github.autopkg preference file.
- **CLIENT_SECRET:**
  - **required:** False
  - **description:** Secret associated with the Client ID, optionally set as a key in the com.github.autopkg preference file.
- **BEARER_TOKEN:**
  - **required:** False
  - **description:** A pre-existing bearer token for the Jamf Pro API. If provided, the token will be validated and used directly, bypassing credential-based authentication.
- **JAMF_CLI_PROFILE:**
  - **required:** False
  - **description:** A jamf-cli profile to use to obtain a bearer token. Requires jamf-cli to be installed and in the PATH. Set to a profile name to enable.
- **PLATFORM_API_REGION:**
  - **required:** False
  - **description:** Region for Jamf Platform API Gateway (e.g. `us1`, `eu1`, `au1`). Required for Platform API authentication.
- **PLATFORM_API_TENANT_ID:**
  - **required:** False
  - **description:** Tenant ID for Jamf Platform API Gateway. Required for Platform API authentication.
- **directory_service_group_name:**
  - **required:** False
  - **description:** Name of the directory service group to resolve. Must match the group name in the directory exactly, including case. An already-encoded base64 value may also be supplied here, in which case it is validated and passed through unchanged. If the name exists on more than one Directory Service server the lookup is ambiguous and the processor fails, in which case supply `directory_service_group_uuid` and `directory_service_group_server_id` instead. Not required if those two are both supplied.
- **directory_service_group_uuid:**
  - **required:** False
  - **description:** UUID of the directory service group. Supply together with `directory_service_group_server_id` to encode the value offline, without an API lookup.
- **directory_service_group_server_id:**
  - **required:** False
  - **description:** ID of the Directory Service server the group belongs to, which is either an LDAP server or a Cloud Identity Provider. Supply together with `directory_service_group_uuid` to encode the value offline, without an API lookup.
- **output_variable_name:**
  - **required:** False
  - **description:** Name of an additional output variable to set to the encoded value, e.g. `DS_GROUP_VALUE` so that `%DS_GROUP_VALUE%` can be used in a template. Useful when encoding more than one group in a single recipe.
- **skip_if:**
  - **required:** False
  - **description:** Skip the process if a supplied predicate is met.

## Output variables

- **directory_service_group_value:**
  - **description:** The base64-encoded criterion value. Substitute this into the `value` key of the criterion in the template.
- **directory_service_group_name:**
  - **description:** The resolved directory service group name. Empty if an already-encoded value was supplied.
- **directory_service_group_uuid:**
  - **description:** The UUID of the resolved directory service group. A group whose Directory Service mappings return no UUID cannot be used, as Jamf Pro will not save a criterion without one, so the processor fails rather than uploading a value that the server rejects.
- **directory_service_group_server_id:**
  - **description:** The ID of the Directory Service server (LDAP server or Cloud Identity Provider) the resolved group belongs to.
- **process_skipped:**
  - **description:** Boolean - True if the process was skipped due to skip_if predicate resolved to True.
