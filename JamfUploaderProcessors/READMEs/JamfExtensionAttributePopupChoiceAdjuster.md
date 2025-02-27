# JamfExtensionAttributePopupChoiceAdjuster

## Description

A processor for AutoPkg that adds or removes pop-up choices from a Jamf Pro Extension Attribute. It modifies XML or JSON files representing Jamf objects and can be used independently or as part of a larger workflow.

## Input variables

- **object_template**:
  - **required**: False
  - **description**: Full path of the object file to modify.
- **parsed_object**:
  - **required**: False
  - **description**: XML or JSON parsed object string to modify. Used if `object_template` is not supplied, e.g., if taking input from `JamfObjectReader`.
- **choice_operation**:
  - **required**: True
  - **description**: Specify `'add'` to add a choice or `'remove'` to remove a choice.
- **choice_value**:
  - **required**: True
  - **description**: Pop-up choice value to add or remove.
- **strict_mode**:
  - **required**: False
  - **description**: Raise a `ProcessorError` when adding a choice that already exists or removing a choice that does not exist in the parsed object. If set to `False`, continues without modifying the parsed object. This ensures no unintended changes are made to the Jamf API, but incorrect choice names may go unnoticed.
  - **default**: `True`
- **output_dir**:
  - **required**: False
  - **description**: Directory to save the modified XML or JSON file. Defaults to `RECIPE_CACHE_DIR`.

## Output variables

- **object_template**:
  - **description**: Full path of the modified object file. Intended to pass to `JamfObjectUploader`.
- **parsed_object**:
  - **description**: Parsed processed object string. For chaining additional `JamfExtensionAttributePopupChoiceAdjuster` processors.
