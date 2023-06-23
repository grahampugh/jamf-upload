# CHANGELOG

| Date       | Notes                                                                                                  |
| ---------- | ------------------------------------------------------------------------------------------------------ |
| 2023-06-23 | Fix key substitution in `JamfComputerProfileUploader` to prevent it overwriting the original template. |
| 2023-06-10 | Check for token for every package processed by `JamfPackageCleaner`.                                   |
| 2023-06-10 | Add `pkg_display_name` key to `JamfPackageUploader`.                                                   |
| 2023-06-10 | Add `dry_run` key to `JamfPackageCleaner`.                                                             |
| 2023-04-26 | Add `skip_script_key_substitution` key to `JamfScriptUploader`.                                        |
| 2023-04-25 | Add `JamfPackageCleaner`.                                                                              |
| 2023-04-12 | Allow randomised failover URL for `jcds_mode` in `JamfPackageUploader`.                                |
| 2022-12-20 | Allow relative paths to templates.                                                                     |
| 2022-12-20 | Allow skip template in `JamfPatchUploader`.                                                            |
| 2022-11-14 | All shebangs updated to use the AutoPkg python distribution.                                           |
| 2022-10-15 | Allow multiple SMB repos plus SMB + Cloud in `JamfPackageUploader`.                                    |
| 2022-10-08 | Fail properly for unsubstitutable variables.                                                           |
| 2022-10-08 | Fail properly if cannot detemine the Jamf Pro version.                                                 |
| 2022-09-21 | Allow empty values for substitutable variables.                                                        |
| 2022-08-25 | Add `sleep` to all relevant processors.                                                                |
| 2022-06-24 | skip_metadata_upload in `JamfPackageUploader`.                                                         |
| 2022-02-25 | add `jcds_mode` in `JamfPackageUploader`.                                                              |
| 2022-01-31 | fix script url and add 405 error.                                                                      |
| 2021-10-22 | Switch to token auth for Jamf Classic API, and move common functions into `JamfUploaderBase.py`.       |
| 2021-10-22 | url fixes.                                                                                             |
| 2021-10-21 | Fixes for variable substitution.                                                                       |
| 2021-09-01 | Limit file search within repos.                                                                        |
| 2021-08-24 | Add AWS cookie checks.                                                                                 |
| 2021-08-22 | Remove case-sensitivity of object name check.                                                          |
| 2021-05-04 | Add `JamfComputerProfileUploader` processor, plus fix for #52.                                         |
| 2021-04-06 | Enable HTTP/2 transfer.                                                                                |
