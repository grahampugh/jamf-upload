# CHANGELOG

| Date       | Notes                                                                                            |
| ---------- | ------------------------------------------------------------------------------------------------ |
| 2022-10-08 | Fail properly for unsubstitutable variables.                                                     |
| 2022-10-08 | Fail properly if cannot detemine the Jamf Pro version.                                           |
| 2022-09-21 | Allow empty values for substitutable variables.                                                  |
| 2022-08-25 | Add `sleep` to all relevant processors.                                                          |
| 2022-06-24 | skip_metadata_upload in `JamfPackageUploader`.                                                   |
| 2022-01-31 | fix script url and add 405 error.                                                                |
| 2021-10-22 | Switch to token auth for Jamf Classic API, and move common functions into `JamfUploaderBase.py`. |
| 2021-10-22 | url fixes.                                                                                       |
| 2021-10-21 | Fixes for variable substitution.                                                                 |
| 2021-09-01 | Limit file search within repos.                                                                  |
| 2021-08-24 | Add AWS cookie checks.                                                                           |
| 2021-08-22 | Remove case-sensitivity of object name check.                                                    |
| 2021-05-04 | Add `JamfComputerProfileUploader` processor, plus fix for #52.                                   |
| 2021-04-06 | Enable HTTP/2 transfer.                                                                          |
