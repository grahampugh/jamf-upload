# JamfScopeAdjuster

## Description

A processor for AutoPkg that adds or removes a scopeable object (target, limitation, or exclusion) to or from a Jamf API object.

## Input variables

- **object_template:**  
  - **required:** False  
  - **description:** Full path of the object file to modify.
- **raw_object:**  
  - **required:** False  
  - **description:** XML object string to modify. Used if `object_template` is not supplied, e.g., when taking input from `JamfObjectReader`.
- **scoping_operation:**  
  - **required:** True  
  - **description:** Specify `add` or `remove`.
- **scoping_type:**  
  - **required:** True  
  - **description:** Type of scope. Specify `target`, `limitation`, or `exclusion`.
- **scopeable_type:**  
  - **required:** True  
  - **description:** Type of scopeable object. Specify `user_group`, `computer_group`, `mobile_device_group`, `network_segment`, `building`, or `department`.
- **scopeable_name:**  
  - **required:** True  
  - **description:** Name of the scopable object.
- **strict_mode:**  
  - **required:** False  
  - **description:** Raise a `ProcessorError` when adding a scopable object that already exists or removing one that does not exist in the raw object. If set to `False`, the processor continues without changing the raw object. Errors or oversights in specifying scopable object names may go unnoticed.  
  - **default:** True
- **strip_raw_xml:**  
  - **required:** False  
  - **description:** Strip all XML tags except for `scope`. Set to `True` if input is from a `JamfObjectReader` raw object, ensuring only the scope is written back to the Jamf API. Set to `False` if input is from an `object_template` file.  
  - **default:** True
- **output_dir:**  
  - **required:** False  
  - **description:** Directory to save the modified object file. Defaults to `RECIPE_CACHE_DIR`.

## Output variables

- **object_template:**  
  - **description:** Full path of the modified object file. Intended to be passed to `JamfObjectUploader`.
- **raw_object:**  
  - **description:** Raw processed XML object string. Can be used for chaining additional `JamfScopeAdjuster` processors.
