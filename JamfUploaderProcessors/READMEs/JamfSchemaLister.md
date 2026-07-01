# JamfSchemaLister

## Description

A processor for AutoPkg that will list all discoverable API endpoints from the Jamf Pro Classic API and JPAPI schemas.

## Input variables

- **JSS_URL:**
  - **required:** True
  - **description:** URL to a Jamf Pro server, optionally set as a key in the com.github.autopkg preference file.
- **api_filter:**
  - **required:** False
  - **description:** Filter endpoints by API type. One of 'all', 'classic', or 'jpapi'.
  - **default:** "all"
- **show_deprecated:**
  - **required:** False
  - **description:** Show deprecated endpoints in the output.
  - **default:** "False"
- **output_dir:**
  - **required:** False
  - **description:** Optional directory to write the schema listing to a file. Directory must exist.
- **skip_if:**
  - **required:** False
  - **description:** Skip the process if a supplied predicate is met.

## Output variables

- **jamfschemalister_summary_result:**
  - **description:** Description of interesting results.
- **schema_lister_output:**
  - **description:** Text listing of all discovered endpoints.
- **process_skipped:**
  - **description:** Boolean - True if the process was skipped due to skip_if predicate resolved to True.
